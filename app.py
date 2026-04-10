import json

from config import ensure_output_dir, get_output_path
from agents.competitor_discovery_agent import run as run_competitor_discovery
from agents.web_search_agent import run as run_web_search
from agents.rag_agent import run as run_rag
from agents.draft_generation_agent import run as run_draft_generation
from agents.review_validation_agent import run as run_review_validation
from nodes.formatting_node import run as run_formatting


def save_text(path, content: str) -> None:
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)


def save_json(path, content: dict) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(content, f, ensure_ascii=False, indent=2)


def main() -> None:
    ensure_output_dir()

    analysis_output_path = get_output_path("analysis_result.txt")
    analysis_json_path = get_output_path("analysis_result.json")
    draft_output_path = get_output_path("draft_report.md")
    validation_output_path = get_output_path("validation_result.json")
    revised_draft_output_path = get_output_path("revised_draft_report.md")
    final_output_path = get_output_path("final_report.md")
    final_pdf_path = get_output_path("final_report.pdf")

    state = {
        "user_query": "HBM4, PIM, CXL 등의 관련 최신 반도체 R&D 정보 수집 및 기술 전략 분석 보고서 생성",
        "target_technologies": ["HBM4", "PIM", "CXL"],
        "documents": [],
        "combined_text": "",
        "analysis_text": "",
        "analysis_json": {},
        "draft_text": "",
        "validation_text": "",
        "validation_json": {},
        "revised_draft_text": "",
        "final_report_text": "",
        "competitor_candidates": [],
        "selected_competitors": [],
        "web_search_queries": [],
        "web_evidence": [],
        "web_findings": [],
        "rag_evidence": [],
        "revision_points": [],
        "validation_result": None,
        "status": "start",
        "retry_count": {},
        "output_dir": str(get_output_path("dummy.txt").parent),
        "reflection_count": 0,
        "validation_metrics": {},
        "next_action": None,
        "retrieval_insufficient": False,
        "evidence_insufficient": False,
        "analysis_error": False,
        "strategy_insufficient": False,
    }

    print("\n[1] Competitor Discovery 시작")
    state = run_competitor_discovery(state)
    print(f"status: {state['status']}")
    print(f"selected_competitors: {state.get('selected_competitors', [])}")

    print("\n[2] Web Search 시작")
    state = run_web_search(state)
    print(f"status: {state['status']}")
    print(f"web_search_queries: {len(state.get('web_search_queries', []))}개")
    print(f"web_search_query_breakdown: {state.get('web_search_query_breakdown', {})}")
    print(f"web_evidence 수집 건수: {len(state.get('web_evidence', []))}개")
    print(f"web_findings 건수: {len(state.get('web_findings', []))}개")
    print(
        f"web_findings 기술 분포: "
        f"{[item.get('technology', '') for item in state.get('web_findings', [])]}"
    )
    print(
        f"web_findings 상위 5건 title: "
        f"{[item.get('title', '') for item in state.get('web_findings', [])[:5]]}"
    )

    print("\n[3] RAG 시작")
    state = run_rag(state)
    print(f"status: {state['status']}")
    print(f"documents: {len(state.get('documents', []))}개")
    print(f"analysis_json keys: {list(state.get('analysis_json', {}).keys())}")

    save_text(analysis_output_path, state.get("analysis_text", ""))
    save_json(analysis_json_path, state.get("analysis_json", {}))

    print("\n[4] Draft Generation 시작")
    state = run_draft_generation(state)
    print(f"status: {state['status']}")
    print(f"draft 길이: {len(state.get('draft_text', ''))}")

    save_text(draft_output_path, state.get("draft_text", ""))

    print("\n[5] Validation 시작")
    state = run_review_validation(state)
    print(f"status: {state['status']}")
    print(f"validated_report_stage: {state.get('validated_report_stage', 'draft')}")
    print(f"validation_result: {state.get('validation_result')}")
    print(f"revision_points: {state.get('revision_points', [])}")

    save_json(validation_output_path, state.get("validation_json", {}))

    if not state.get("validation_result"):
        print("\n[6] Reflection / Re-run 시작")
        state["reflection_count"] = state.get("reflection_count", 0) + 1

        next_action = state.get("next_action")
        print(f"next_action: {next_action}")

        if next_action == "rerun_retrieval":
            print("\n[6-1] Retrieval 부족 -> Web Search 재실행")
            state = run_web_search(state)
            print(f"status: {state['status']}")
            print(f"web_evidence 수집 건수: {len(state.get('web_evidence', []))}개")
            print(f"web_findings 건수: {len(state.get('web_findings', []))}개")

            print("\n[6-2] Retrieval 부족 -> RAG 재실행")
            state = run_rag(state)
            print(f"status: {state['status']}")
            print(f"documents: {len(state.get('documents', []))}개")

            print("\n[6-3] Retrieval 보강 후 Draft 재생성")
            state = run_draft_generation(state)
            print(f"status: {state['status']}")
            print(f"revised_draft 길이: {len(state.get('revised_draft_text', '') or state.get('draft_text', ''))}")

        elif next_action == "rerun_draft":
            print("\n[6-1] 근거 부족 -> Draft 재생성")
            state = run_draft_generation(state)
            print(f"status: {state['status']}")
            print(f"revised_draft 길이: {len(state.get('revised_draft_text', '') or state.get('draft_text', ''))}")

        elif next_action == "rerun_analysis":
            print("\n[6-1] 분석 오류 -> RAG 재실행")
            state = run_rag(state)
            print(f"status: {state['status']}")
            print(f"documents: {len(state.get('documents', []))}개")

            print("\n[6-2] 분석 보강 후 Draft 재생성")
            state = run_draft_generation(state)
            print(f"status: {state['status']}")
            print(f"revised_draft 길이: {len(state.get('revised_draft_text', '') or state.get('draft_text', ''))}")

        elif next_action == "rerun_finalize":
            print("\n[6-1] 전략 부족 -> Draft/Finalize 보강")
            state = run_draft_generation(state)
            print(f"status: {state['status']}")
            print(f"revised_draft 길이: {len(state.get('revised_draft_text', '') or state.get('draft_text', ''))}")

        else:
            print("\n[6-1] 기본 재작성 수행")
            state = run_draft_generation(state)
            print(f"status: {state['status']}")
            print(f"revised_draft 길이: {len(state.get('revised_draft_text', '') or state.get('draft_text', ''))}")

        revised_text = state.get("revised_draft_text") or state.get("draft_text", "")
        save_text(revised_draft_output_path, revised_text)

        print("\n[7] Re-Validation 시작")
        state = run_review_validation(state)
        print(f"status: {state['status']}")
        print(f"validated_report_stage: {state.get('validated_report_stage', 'draft')}")
        print(f"validation_result: {state.get('validation_result')}")
        print(f"next_action: {state.get('next_action')}")
        print(f"validation_metrics: {state.get('validation_metrics', {})}")
        print(f"revision_points: {state.get('revision_points', [])}")

        save_json(validation_output_path, state.get("validation_json", {}))

    print("\n[8] Finalize 시작")
    state = run_draft_generation(state)
    print(f"status: {state['status']}")
    print(f"revised_draft 길이: {len(state.get('revised_draft_text', ''))}")
    print(f"final_report 길이: {len(state.get('final_report_text', ''))}")

    final_text = (
        state.get("final_report_text")
        or state.get("revised_draft_text")
        or state.get("draft_text", "")
    )
    save_text(final_output_path, final_text)

    print("\n[9] Formatting Node 시작")
    state = run_formatting(state)
    print(f"status: {state['status']}")
    print(f"Markdown 저장 완료: {state.get('formatted_markdown_path')}")
    print(f"PDF 저장 완료: {state.get('formatted_pdf_path')}")

    print("\n===== 전체 workflow 완료 =====")
    print(f"[저장 완료] {analysis_output_path}")
    print(f"[저장 완료] {analysis_json_path}")
    print(f"[저장 완료] {draft_output_path}")
    print(f"[저장 완료] {validation_output_path}")
    print(f"[저장 완료] {revised_draft_output_path}")
    print(f"[저장 완료] {final_output_path}")
    print(f"[저장 완료] {final_pdf_path}")
    print(f"[최종 validation_result] {state.get('validation_result')}")
    print(f"[최종 revision_points] {state.get('revision_points', [])}")


if __name__ == "__main__":
    main()