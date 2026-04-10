from typing import Dict, Any, List


def run(state: Dict[str, Any]) -> Dict[str, Any]:
    target_technologies = state.get("target_technologies", [])

    competitor_map = {
        "HBM4": ["SK hynix", "Samsung Electronics", "Micron"],
        "PIM": ["Samsung Electronics", "SK hynix", "UPMEM"],
        "CXL": ["Samsung Electronics", "SK hynix", "Micron", "Astera Labs"],
    }

    competitor_candidates: List[str] = []
    selection_reasons = []

    for tech in target_technologies:
        for company in competitor_map.get(tech, []):
            if company not in competitor_candidates:
                competitor_candidates.append(company)
                selection_reasons.append({
                    "technology": tech,
                    "company": company,
                    "reason": f"{tech} 관련 주요 경쟁사 후보"
                })

    state["competitor_candidates"] = competitor_candidates
    state["selected_competitors"] = competitor_candidates[:3]
    state["competitor_selection_reasons"] = selection_reasons
    state["status"] = "competitor_discovery_done"
    return state