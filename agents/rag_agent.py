from typing import Dict, Any

from config import get_prompt_path
from document_loader import (
    load_documents_for_technologies,
    build_combined_text,
    build_rag_evidence,
)
from llm_runner import run_chat, parse_json_response


def load_prompt(prompt_name: str) -> str:
    prompt_path = get_prompt_path(prompt_name)
    with open(prompt_path, "r", encoding="utf-8") as f:
        return f.read()


def collect_available_document_technologies(documents: list[dict]) -> list[str]:
    technologies = set()

    for doc in documents:
        technology_value = doc.get("technology")
        if isinstance(technology_value, list):
            technologies.update(str(item) for item in technology_value if item)
        elif technology_value:
            technologies.add(str(technology_value))

    return sorted(technologies)


def filter_documents_by_technology(documents: list[dict], technology: str) -> list[dict]:
    filtered_docs = []

    for doc in documents:
        technology_value = doc.get("technology")

        if isinstance(technology_value, list):
            normalized = [str(item).strip().lower() for item in technology_value if item]
            if technology.strip().lower() in normalized:
                filtered_docs.append(doc)
        elif technology_value:
            if str(technology_value).strip().lower() == technology.strip().lower():
                filtered_docs.append(doc)

    return filtered_docs


def run_single_technology_analysis(
    technology: str,
    documents: list[dict],
    selected_competitors: list[str],
) -> dict:
    combined_text = build_combined_text(documents)
    rag_evidence = build_rag_evidence(documents)

    analysis_prompt_template = load_prompt("analysis_prompt.txt")
    analysis_prompt = analysis_prompt_template.format(
        target_technologies=technology,
        selected_competitors=", ".join(selected_competitors) or "확인 필요",
        missing_document_technologies="없음" if documents else technology,
        combined_text=combined_text or "[문서 근거 없음]",
    )

    analysis_text = run_chat(
        analysis_prompt,
        "당신은 반도체 R&D 기술 전략 분석 전문가입니다. 제공된 문서 근거만 바탕으로 판단하고, 근거가 부족하면 반드시 '확인 필요'라고 명시하세요."
    )
    analysis_json = parse_json_response(analysis_text)

    return {
        "technology": technology,
        "documents": documents,
        "combined_text": combined_text,
        "rag_evidence": rag_evidence,
        "analysis_text": analysis_text,
        "analysis_json": analysis_json,
    }


def run(state: Dict[str, Any]) -> Dict[str, Any]:
    target_technologies = state.get("target_technologies", [])
    selected_competitors = state.get("selected_competitors", [])

    documents, missing_document_technologies = load_documents_for_technologies(target_technologies)

    # 전체 문서 기준 정보
    combined_text = build_combined_text(documents)
    rag_evidence = build_rag_evidence(documents)
    available_document_technologies = collect_available_document_technologies(documents)

    # 기술별 분석 결과 저장
    analysis_by_technology: dict[str, dict[str, Any]] = {}
    technology_documents: dict[str, list[dict]] = {}
    technology_combined_text: dict[str, str] = {}
    technology_rag_evidence: dict[str, list[dict]] = {}

    for technology in target_technologies:
        tech_docs = filter_documents_by_technology(documents, technology)
        technology_documents[technology] = tech_docs
        technology_combined_text[technology] = build_combined_text(tech_docs)
        technology_rag_evidence[technology] = build_rag_evidence(tech_docs)

        analysis_by_technology[technology] = run_single_technology_analysis(
            technology=technology,
            documents=tech_docs,
            selected_competitors=selected_competitors,
        )

    # 전체 통합 분석
    analysis_prompt_template = load_prompt("analysis_prompt.txt")
    analysis_prompt = analysis_prompt_template.format(
        target_technologies=", ".join(target_technologies) or "확인 필요",
        selected_competitors=", ".join(selected_competitors) or "확인 필요",
        missing_document_technologies=", ".join(missing_document_technologies) or "없음",
        combined_text=combined_text or "[문서 근거 없음]",
    )

    analysis_text = run_chat(
        analysis_prompt,
        "당신은 반도체 R&D 기술 전략 분석 전문가입니다. 제공된 문서 근거만 바탕으로 판단하고, 근거가 부족하면 반드시 '확인 필요'라고 명시하세요."
    )
    analysis_json = parse_json_response(analysis_text)

    state["documents"] = documents
    state["combined_text"] = combined_text
    state["rag_evidence"] = rag_evidence
    state["available_document_technologies"] = available_document_technologies
    state["missing_document_technologies"] = missing_document_technologies

    # 기술별 상태 추가
    state["technology_documents"] = technology_documents
    state["technology_combined_text"] = technology_combined_text
    state["technology_rag_evidence"] = technology_rag_evidence
    state["analysis_by_technology"] = analysis_by_technology

    # 전체 분석 유지
    state["analysis_text"] = analysis_text
    state["analysis_json"] = analysis_json
    state["status"] = "rag_done"
    return state