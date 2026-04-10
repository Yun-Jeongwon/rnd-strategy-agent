import json
from pathlib import Path
import fitz

from config import BASE_PATH, get_data_path


def load_documents_metadata(technology: str = "hbm4") -> list[dict]:
    metadata_path = get_data_path("metadata", technology, "documents.json")
    if not metadata_path.exists():
        return []

    with open(metadata_path, "r", encoding="utf-8") as f:
        return json.load(f)


def _normalize_technology_values(value: str | list[str] | None) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(item).upper() for item in value]
    return [str(value).upper()]


def _matches_target_technology(doc: dict, technology: str) -> bool:
    target = technology.upper()
    tech_values = _normalize_technology_values(doc.get("technology"))
    return target in tech_values


def _get_document_identity(doc: dict, fallback_index: int) -> str:
    for key in ["doc_id", "url", "title"]:
        value = doc.get(key)
        if value:
            return str(value)
    return f"document-{fallback_index}"


def load_documents_for_technologies(technologies: list[str]) -> tuple[list[dict], list[str]]:
    documents: list[dict] = []
    missing_technologies: list[str] = []
    seen_doc_ids = set()

    for tech_index, technology in enumerate(technologies, start=1):
        normalized = technology.lower()
        tech_documents = load_documents_metadata(normalized)

        if not tech_documents:
            missing_technologies.append(technology)
            continue

        matched_documents = [doc for doc in tech_documents if _matches_target_technology(doc, technology)]
        if not matched_documents:
            missing_technologies.append(technology)
            continue

        for doc_index, doc in enumerate(matched_documents, start=1):
            doc_identity = _get_document_identity(doc, fallback_index=(tech_index * 1000) + doc_index)
            if doc_identity in seen_doc_ids:
                continue

            seen_doc_ids.add(doc_identity)
            documents.append(doc)

    return documents, missing_technologies


def read_file(path: Path) -> str:
    if path.suffix.lower() == ".pdf":
        try:
            doc = fitz.open(path)
            text = ""
            for page in doc:
                text += page.get_text()
            return text.strip()
        except Exception as e:
            return f"[PDF 읽기 오류: {e}]"

    if path.suffix.lower() in [".txt", ".html"]:
        with open(path, "r", encoding="utf-8") as f:
            return f.read()

    return "[지원하지 않는 파일 형식]"


def resolve_raw_path(raw_path: str) -> Path:
    return (BASE_PATH / raw_path).resolve()


def build_combined_text(documents: list[dict]) -> str:
    doc_texts = []

    for index, doc in enumerate(documents, start=1):
        raw_path_value = doc.get("raw_path")
        url = doc.get("url", "")
        doc_id = doc.get("doc_id") or f"metadata_{index}"
        technology = doc.get("technology", "확인 필요")
        if isinstance(technology, list):
            technology = ", ".join(technology)

        source = doc.get("source") or doc.get("source_type") or "확인 필요"
        published_at = doc.get("published_at") or doc.get("published_date") or "확인 필요"

        if raw_path_value:
            raw_path = resolve_raw_path(raw_path_value)
            text = read_file(raw_path)
        else:
            text_lines = [
                "[원문 파일 없음: 메타데이터 기반 요약만 사용]",
                f"document_type: {doc.get('document_type', '확인 필요')}",
            ]
            if doc.get("notes"):
                text_lines.append(f"notes: {doc['notes']}")
            if doc.get("author"):
                text_lines.append(f"author: {doc['author']}")
            if doc.get("authors"):
                text_lines.append(f"authors: {', '.join(doc['authors'])}")
            if url:
                text_lines.append(f"url: {url}")
            text = "\n".join(text_lines)

        doc_texts.append(
            f"[DOC_ID] {doc_id}\n"
            f"[TECHNOLOGY] {technology}\n"
            f"[COMPANY] {doc.get('company', '확인 필요')}\n"
            f"[TITLE] {doc.get('title', '확인 필요')}\n"
            f"[SOURCE] {source}\n"
            f"[PUBLISHED_AT] {published_at}\n"
            f"[TEXT]\n{text}"
        )

    return "\n\n".join(doc_texts)


def build_rag_evidence(documents: list[dict]) -> list[dict]:
    rag_evidence = []

    for doc in documents:
        rag_evidence.append(
            {
                "doc_id": doc.get("doc_id") or doc.get("url") or doc.get("title", ""),
                "technology": doc.get("technology", ""),
                "company": doc.get("company", ""),
                "title": doc.get("title", ""),
                "source": doc.get("source") or doc.get("source_type", ""),
                "published_at": doc.get("published_at") or doc.get("published_date", ""),
                "document_type": doc.get("document_type", ""),
                "notes": doc.get("notes", ""),
                "url": doc.get("url", ""),
                "has_raw_path": bool(doc.get("raw_path")),
            }
        )

    return rag_evidence
