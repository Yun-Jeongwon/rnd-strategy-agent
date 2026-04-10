import os
from typing import Dict, Any, List

from dotenv import load_dotenv
from tavily import TavilyClient

load_dotenv()


BLOCKED_DOMAINS = [
    "blog.naver.com",
    "m.blog.naver.com",
    "naver.me",
    "cafe.naver.com",
    "post.naver.com",
    "tistory.com",
    "velog.io",
    "brunch.co.kr",
    "cafe.naver.com"
]


TECH_QUERY_MAP = {
    "HBM4": [
        "HBM4 latest semiconductor memory news",
        "HBM4 AI memory bandwidth power latest",
        "HBM4 mass production roadmap latest",
    ],
    "PIM": [
        "PIM semiconductor memory latest",
        "processing in memory semiconductor latest",
        "PIM AI memory roadmap latest",
    ],
    "CXL": [
        "CXL memory latest semiconductor news",
        "Compute Express Link memory expansion latest",
        "CXL memory roadmap latest",
    ],
}

TECH_RELEVANCE_KEYWORDS = {
    "HBM4": [
        "hbm4",
        "high bandwidth memory 4",
    ],
    "PIM": [
        " pim ",
        "processing in memory",
        "processing-in-memory",
        "in-memory computing",
    ],
    "CXL": [
        " cxl ",
        "compute express link",
        "cxl memory",
    ],
}

SEMICONDUCTOR_CONTEXT_KEYWORDS = [
    "semiconductor",
    "memory",
    "dram",
    "chip",
    "ai",
    "bandwidth",
    "power",
    "roadmap",
    "package",
    "server",
    "datacenter",
]

BLOCKED_KEYWORDS = [
    "one ui",
    "galaxy",
    "smartphone",
    "tablet",
    "wearable",
    "camera",
    "android",
    "beta program",
    "phone",
]


def _build_queries(state: Dict[str, Any]) -> List[Dict[str, str]]:
    selected_competitors = state.get("selected_competitors", [])
    target_technologies = state.get("target_technologies", [])

    query_items: List[Dict[str, str]] = []

    for tech in target_technologies:
        base_queries = TECH_QUERY_MAP.get(tech, [])

        for q in base_queries:
            query_items.append({"technology": tech, "query": q})

        for company in selected_competitors:
            for q in base_queries:
                company_query = f"{company} {q}"
                query_items.append({"technology": tech, "query": company_query})

    deduped: List[Dict[str, str]] = []
    seen = set()

    for item in query_items:
        key = (item["technology"], item["query"])
        if key not in seen:
            seen.add(key)
            deduped.append(item)

    return deduped


def _extract_domain(url: str) -> str:
    if not url:
        return ""

    try:
        return url.split("/")[2].lower()
    except Exception:
        return ""


def _normalize_results(technology: str, query: str, response: Dict[str, Any]) -> List[Dict[str, Any]]:
    items: List[Dict[str, Any]] = []

    for r in response.get("results", []):
        url = r.get("url", "")
        domain = _extract_domain(url)

        items.append({
            "technology": technology,
            "query": query,
            "title": r.get("title", ""),
            "url": url,
            "content": r.get("content", ""),
            "score": r.get("score"),
            "published_date": r.get("published_date", ""),
            "source_domain": domain,
        })

    return items


def _dedupe_evidence(evidence: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    deduped = []
    seen_urls = set()

    for item in evidence:
        url = item.get("url", "").strip()
        if not url or url in seen_urls:
            continue
        seen_urls.add(url)
        deduped.append(item)

    return deduped


def _is_blocked_domain(url: str) -> bool:
    domain = _extract_domain(url)
    if not domain:
        return True

    for blocked in BLOCKED_DOMAINS:
        if domain == blocked or domain.endswith(f".{blocked}"):
            return True

    return False


def _filter_blocked_domains(evidence: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    filtered = []

    for item in evidence:
        url = item.get("url", "").strip()
        if _is_blocked_domain(url):
            continue
        filtered.append(item)

    return filtered


def _is_relevant(item: Dict[str, Any]) -> bool:
    technology = item.get("technology", "")
    title = item.get("title", "").lower()
    content = item.get("content", "").lower()
    text = f" {title} {content} "

    if any(keyword in text for keyword in BLOCKED_KEYWORDS):
        return False

    tech_keywords = TECH_RELEVANCE_KEYWORDS.get(technology, [])
    has_direct_tech_keyword = any(keyword in text for keyword in tech_keywords)

    if not has_direct_tech_keyword:
        return False

    has_context_keyword = any(keyword in text for keyword in SEMICONDUCTOR_CONTEXT_KEYWORDS)
    if not has_context_keyword:
        return False

    generic_blocked = [
        "shares",
        "stock",
        "revenue",
        "profit",
        "earnings",
        "smartphone",
        "foundry partnership",
        "wafer shortage",
        "megaconference",
        "in-house ai chips",
    ]
    if any(keyword in text for keyword in generic_blocked):
        return False

    return True


def _rank_evidence(evidence: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    def score(item: Dict[str, Any]):
        text = f" {item.get('title', '').lower()} {item.get('content', '').lower()} "
        domain = item.get("source_domain", "")
        technology = item.get("technology", "")

        base_score = item.get("score") or 0
        bonus = 0

        if domain in [
            "reuters.com",
            "news.samsung.com",
            "samsung.com",
            "skhynix.com",
            "micron.com",
        ]:
            bonus += 2
        elif domain in [
            "trendforce.com",
            "digitimes.com",
            "anandtech.com",
            "tomshardware.com",
            "servethehome.com",
            "blocksandfiles.com",
            "eetimes.com",
            "eejournal.com",
        ]:
            bonus += 2

        for kw in TECH_RELEVANCE_KEYWORDS.get(technology, []):
            if kw in text:
                bonus += 4

        for kw in [
            "bandwidth",
            "power",
            "dram",
            "memory",
            "roadmap",
            "mass production",
            "server",
            "datacenter",
        ]:
            if kw in text:
                bonus += 1

        return base_score + bonus

    return sorted(evidence, key=score, reverse=True)


def _select_balanced_findings(evidence: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    findings = []
    tech_buckets = {"HBM4": [], "PIM": [], "CXL": []}

    for item in evidence:
        tech = item.get("technology")
        if tech in tech_buckets:
            tech_buckets[tech].append(item)

    # 기술별 최대 3건 우선 확보
    for tech in ["HBM4", "PIM", "CXL"]:
        findings.extend(tech_buckets[tech][:3])

    # 부족하면 전체 상위 결과에서 추가
    if len(findings) < 10:
        selected_urls = {item["url"] for item in findings}
        for item in evidence:
            if item["url"] not in selected_urls:
                findings.append(item)
                selected_urls.add(item["url"])
            if len(findings) >= 10:
                break

    return findings[:10]


def _build_web_findings(evidence: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    findings = []

    for item in evidence:
        findings.append({
            "technology": item.get("technology", ""),
            "title": item.get("title", ""),
            "url": item.get("url", ""),
            "published_date": item.get("published_date", ""),
            "source_domain": item.get("source_domain", ""),
            "key_finding": item.get("content", ""),
            "query": item.get("query", ""),
        })

    return findings


def _build_query_breakdown(query_items: List[Dict[str, str]]) -> Dict[str, int]:
    breakdown: Dict[str, int] = {}

    for item in query_items:
        tech = item["technology"]
        breakdown[tech] = breakdown.get(tech, 0) + 1

    return breakdown


def run(state: Dict[str, Any]) -> Dict[str, Any]:
    api_key = os.getenv("TAVILY_API_KEY")
    if not api_key:
        raise ValueError("TAVILY_API_KEY가 설정되지 않았습니다. .env 파일을 확인하세요.")

    client = TavilyClient(api_key=api_key)

    max_results = int(os.getenv("WEB_SEARCH_MAX_RESULTS", "4"))
    topic = os.getenv("WEB_SEARCH_TOPIC", "news")
    time_range = os.getenv("WEB_SEARCH_TIME_RANGE", "month")

    query_items = _build_queries(state)

    # 너무 많아지지 않게 우선 일부 사용
    selected_query_items = query_items[:15]

    web_evidence: List[Dict[str, Any]] = []

    for item in selected_query_items:
        technology = item["technology"]
        query = item["query"]

        try:
            response = client.search(
                query=query,
                topic=topic,
                time_range=time_range,
                search_depth="advanced",
                max_results=max_results,
                include_raw_content=False,
            )
            web_evidence.extend(_normalize_results(technology, query, response))
        except Exception as e:
            web_evidence.append({
                "technology": technology,
                "query": query,
                "title": "",
                "url": "",
                "content": f"[검색 실패] {str(e)}",
                "score": None,
                "published_date": "",
                "source_domain": "",
            })

    web_evidence = _dedupe_evidence(web_evidence)
    web_evidence = _filter_blocked_domains(web_evidence)
    web_evidence = [item for item in web_evidence if _is_relevant(item)]
    web_evidence = _rank_evidence(web_evidence)

    balanced_evidence = _select_balanced_findings(web_evidence)
    web_findings = _build_web_findings(balanced_evidence)

    state["web_search_queries"] = [item["query"] for item in selected_query_items]
    state["web_search_query_breakdown"] = _build_query_breakdown(selected_query_items)
    state["web_evidence"] = web_evidence
    state["web_findings"] = web_findings
    state["status"] = "web_search_done"
    return state