from typing import Dict, Any, List

from config import get_prompt_path
from llm_runner import run_chat, parse_json_response


def load_prompt(prompt_name: str) -> str:
    prompt_path = get_prompt_path(prompt_name)
    with open(prompt_path, "r", encoding="utf-8") as f:
        return f.read()


def _safe_int(value, default=0) -> int:
    try:
        return int(value)
    except Exception:
        return default


def _safe_float(value, default=0.0) -> float:
    try:
        return float(value)
    except Exception:
        return default


def _calc_validation_metrics(state: Dict[str, Any], report_text: str) -> Dict[str, Any]:
    target_technologies = state.get("target_technologies", [])
    selected_competitors = state.get("selected_competitors", [])
    web_findings = state.get("web_findings", [])
    analysis_by_technology = state.get("analysis_by_technology", {})
    revision_loops = _safe_int(state.get("reflection_count", 0), 0)

    report_lower = report_text.lower()

    # 1. 경쟁사 커버리지
    competitor_coverage = len(selected_competitors)
    competitor_coverage_pass = competitor_coverage >= 2

    # 2. TRL 적용률
    trl_applied_count = 0
    trl_total = len(target_technologies)

    for tech in target_technologies:
        tech_analysis = analysis_by_technology.get(tech, {})
        tech_json = tech_analysis.get("analysis_json", {}) if isinstance(tech_analysis, dict) else {}

        trl_value = (
            tech_json.get("trl")
            or tech_json.get("TRL")
            or tech_json.get("technology_trl")
            or tech_json.get("maturity_trl")
        )
        if trl_value not in [None, "", "확인 필요"]:
            trl_applied_count += 1

    trl_coverage = (trl_applied_count / trl_total) if trl_total > 0 else 0.0
    trl_coverage_pass = trl_coverage >= 0.8

    # 3. 근거 포함 비율(간이 측정)
    key_claim_lines = []
    for line in report_text.splitlines():
        s = line.strip()
        if not s:
            continue

        if any(
            keyword in s
            for keyword in [
                "기술 수준",
                "기술 성숙도",
                "위협",
                "경쟁사",
                "전략",
                "시사점",
                "TRL",
                "투자",
                "대응",
            ]
        ):
            key_claim_lines.append(s)

    evidence_markers = [
        "출처",
        "reference",
        "근거",
        "발표",
        "보고서",
        "논문",
        "news",
        "press release",
        "공식",
        "기사",
        "발행",
    ]

    evidenced_count = 0
    for line in key_claim_lines:
        lower = line.lower()
        if any(marker in lower for marker in evidence_markers):
            evidenced_count += 1

    evidence_ratio = (
        evidenced_count / len(key_claim_lines)
        if len(key_claim_lines) > 0
        else 1.0
    )
    evidence_ratio_pass = evidence_ratio >= 0.9

    # 4. 최신성(간이 측정: 웹 근거 존재 비율로 대체)
    freshness_ratio = 1.0 if len(web_findings) > 0 else 0.0
    freshness_pass = freshness_ratio >= 0.7

    # 5. 구조 완성도
    required_sections = [
        "0. SUMMARY",
        "1. 분석 배경",
        "2. 분석 대상 및 범위",
        "3. 기술 현황",
        "4. 경쟁사",
        "5. 전략적 시사점",
        "6. REFERENCE",
    ]
    section_hits = sum(1 for s in required_sections if s.lower() in report_lower)
    structure_ratio = section_hits / len(required_sections)
    structure_pass = structure_ratio == 1.0

    # 6. Reflection 수행 여부
    reflection_performed = revision_loops >= 1

    # 7. Retrieval 부족 판단
    retrieval_insufficient = False
    if len(web_findings) < max(3, len(target_technologies)):
        retrieval_insufficient = True

    for tech in target_technologies:
        tech_analysis = analysis_by_technology.get(tech, {})
        tech_docs = tech_analysis.get("documents", []) if isinstance(tech_analysis, dict) else []
        tech_web = [item for item in web_findings if item.get("technology") == tech]
        if len(tech_docs) == 0 and len(tech_web) == 0:
            retrieval_insufficient = True

    # 8. TRL 4~6 구간 처리
    trl_46_requires_estimation_note = False
    trl_46_note_present = True

    for tech in target_technologies:
        tech_analysis = analysis_by_technology.get(tech, {})
        tech_json = tech_analysis.get("analysis_json", {}) if isinstance(tech_analysis, dict) else {}
        trl_value = (
            tech_json.get("trl")
            or tech_json.get("TRL")
            or tech_json.get("technology_trl")
            or tech_json.get("maturity_trl")
        )

        try:
            trl_num = int(str(trl_value).strip())
            if 4 <= trl_num <= 6:
                trl_46_requires_estimation_note = True
        except Exception:
            continue

    if trl_46_requires_estimation_note:
        if ("추정" not in report_text) or ("간접 지표" not in report_text):
            trl_46_note_present = False

    # 9. 분석 오류 / 전략 부족
    analysis_error = not trl_coverage_pass
    strategy_insufficient = ("전략적 시사점" not in report_text) or ("투자" not in report_text and "대응" not in report_text)

    return {
        "competitor_coverage": competitor_coverage,
        "competitor_coverage_pass": competitor_coverage_pass,
        "trl_coverage": round(trl_coverage, 4),
        "trl_coverage_pass": trl_coverage_pass,
        "evidence_ratio": round(evidence_ratio, 4),
        "evidence_ratio_pass": evidence_ratio_pass,
        "freshness_ratio": round(freshness_ratio, 4),
        "freshness_pass": freshness_pass,
        "structure_ratio": round(structure_ratio, 4),
        "structure_pass": structure_pass,
        "reflection_performed": reflection_performed,
        "retrieval_insufficient": retrieval_insufficient,
        "trl_46_requires_estimation_note": trl_46_requires_estimation_note,
        "trl_46_note_present": trl_46_note_present,
        "analysis_error": analysis_error,
        "strategy_insufficient": strategy_insufficient,
    }


def run(state: Dict[str, Any]) -> Dict[str, Any]:
    report_text = state.get("revised_draft_text") or state.get("draft_text", "")

    validation_prompt_template = load_prompt("validation_prompt.txt")
    validation_prompt = validation_prompt_template.format(draft_report=report_text)

    validation_text = run_chat(
        validation_prompt,
        (
            "당신은 반도체 기술 전략 보고서 검토자입니다. "
            "주어진 초안만 기준으로 검토하고, 근거가 부족하면 명확히 지적하세요. "
            "반드시 JSON으로 응답하세요. "
            "키: pass, revision_points, retrieval_insufficient, evidence_insufficient, "
            "analysis_error, strategy_insufficient, missing_sections, hallucination_risk"
        )
    )
    validation_json = parse_json_response(validation_text)

    metrics = _calc_validation_metrics(state, report_text)

    revision_points: List[str] = []
    llm_pass = False
    llm_retrieval_insufficient = False
    llm_evidence_insufficient = False
    llm_analysis_error = False
    llm_strategy_insufficient = False

    if isinstance(validation_json, dict):
        llm_pass = bool(validation_json.get("pass", False))
        revision_points = validation_json.get("revision_points", []) or []
        llm_retrieval_insufficient = bool(validation_json.get("retrieval_insufficient", False))
        llm_evidence_insufficient = bool(validation_json.get("evidence_insufficient", False))
        llm_analysis_error = bool(validation_json.get("analysis_error", False))
        llm_strategy_insufficient = bool(validation_json.get("strategy_insufficient", False))

    # 규칙 기반 보정
    if not metrics["competitor_coverage_pass"]:
        revision_points.append("주요 경쟁사 최소 2개 이상 포함 필요")
    if not metrics["trl_coverage_pass"]:
        revision_points.append("분석 대상 기술/기업에 대한 TRL 적용률 80% 이상 필요")
    if not metrics["evidence_ratio_pass"]:
        revision_points.append("핵심 주장 대비 근거 포함 비율 90% 이상 필요")
    if not metrics["freshness_pass"]:
        revision_points.append("최신성 기준(최근 자료 중심) 보강 필요")
    if not metrics["structure_pass"]:
        revision_points.append("보고서 템플릿(SUMMARY~REFERENCE) 완전 충족 필요")
    if metrics["trl_46_requires_estimation_note"] and not metrics["trl_46_note_present"]:
        revision_points.append("TRL 4~6 구간은 '추정 + 간접 지표 기반' 명시 필요")
    if not metrics["reflection_performed"]:
        revision_points.append("최소 1회 이상 검증 및 수정 루프 수행 필요")

    retrieval_insufficient = metrics["retrieval_insufficient"] or llm_retrieval_insufficient
    evidence_insufficient = (not metrics["evidence_ratio_pass"]) or llm_evidence_insufficient
    analysis_error = metrics["analysis_error"] or llm_analysis_error
    strategy_insufficient = metrics["strategy_insufficient"] or llm_strategy_insufficient

    # 다음 액션 결정
    if retrieval_insufficient:
        next_action = "rerun_retrieval"
    elif evidence_insufficient:
        next_action = "rerun_draft"
    elif analysis_error:
        next_action = "rerun_analysis"
    elif strategy_insufficient:
        next_action = "rerun_finalize"
    else:
        next_action = "pass"

    validation_result = (
        llm_pass
        and metrics["competitor_coverage_pass"]
        and metrics["trl_coverage_pass"]
        and metrics["evidence_ratio_pass"]
        and metrics["freshness_pass"]
        and metrics["structure_pass"]
        and (metrics["trl_46_note_present"] or not metrics["trl_46_requires_estimation_note"])
        and metrics["reflection_performed"]
    )

    state["validation_text"] = validation_text
    state["validation_json"] = validation_json if isinstance(validation_json, dict) else {}
    state["validation_metrics"] = metrics
    state["validation_result"] = validation_result
    state["revision_points"] = list(dict.fromkeys(revision_points))
    state["validated_report_stage"] = "revised_draft" if state.get("revised_draft_text") else "draft"
    state["next_action"] = next_action
    state["retrieval_insufficient"] = retrieval_insufficient
    state["evidence_insufficient"] = evidence_insufficient
    state["analysis_error"] = analysis_error
    state["strategy_insufficient"] = strategy_insufficient
    state["status"] = "validation_done"
    return state