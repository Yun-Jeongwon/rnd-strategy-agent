import json
from typing import Dict, Any

from config import get_prompt_path
from llm_runner import run_chat


def load_prompt(prompt_name: str) -> str:
    prompt_path = get_prompt_path(prompt_name)
    with open(prompt_path, "r", encoding="utf-8") as f:
        return f.read()


def run(state: Dict[str, Any]) -> Dict[str, Any]:
    analysis_json = state.get("analysis_json", {})
    validation_json = state.get("validation_json", {})
    validation_result = state.get("validation_result")
    web_findings = state.get("web_findings", [])
    draft_text = state.get("draft_text", "")
    revised_draft_text = state.get("revised_draft_text", "")

    if not draft_text:
        draft_prompt_template = load_prompt("draft_prompt.txt")
        draft_prompt = draft_prompt_template.format(
            analysis_json=json.dumps(analysis_json, ensure_ascii=False, indent=2),
            web_findings=json.dumps(web_findings, ensure_ascii=False, indent=2),
        )

        draft_text = run_chat(
            draft_prompt,
            "당신은 반도체 기술 전략 분석 보고서를 작성하는 전문가입니다. 제공된 문서 분석 결과와 최신 웹 근거만 사용하세요. 최신 기사에서 확인된 사실은 본문과 REFERENCE에 구체적으로 반영하세요."
        )
        state["draft_text"] = draft_text

    if validation_json and validation_result is False:
        revision_prompt_template = load_prompt("revision_prompt.txt")
        revision_prompt = revision_prompt_template.format(
            draft_report=draft_text,
            validation_result=json.dumps(validation_json, ensure_ascii=False, indent=2)
        )

        revised_draft_text = run_chat(
            revision_prompt,
            "당신은 반도체 기술 전략 보고서 편집자입니다. 검토 결과를 반영해 보고서를 개선하세요. 근거가 약한 부분은 더 보수적으로 수정하세요."
        )
        state["revised_draft_text"] = revised_draft_text

        state["revised_draft_text"] = revised_draft_text
        state["final_report_text"] = ""
        state["status"] = "draft_revised"
        return state

    if validation_json and validation_result is True:
        source_report = revised_draft_text or draft_text

        finalize_prompt_template = load_prompt("finalize_prompt.txt")
        finalize_prompt = finalize_prompt_template.format(
            revised_draft_report=source_report
        )

        final_report_text = run_chat(
            finalize_prompt,
            "당신은 반도체 기술 전략 분석 보고서를 최종 정리하는 편집자입니다. 출처 표현이 구체적이도록 정리하세요."
        )
        state["final_report_text"] = final_report_text

    state["status"] = "draft_generation_done"
    return state
