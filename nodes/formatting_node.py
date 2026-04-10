from pathlib import Path
import os
import re
from typing import Dict, Any, List

from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    PageBreak,
)
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont


def register_font() -> str:
    candidates = [
        "/System/Library/Fonts/Supplemental/AppleGothic.ttf",
        "/Library/Fonts/AppleGothic.ttf",
        "/System/Library/Fonts/Supplemental/NanumGothic.ttf",
    ]

    for font_path in candidates:
        if os.path.exists(font_path):
            try:
                pdfmetrics.registerFont(TTFont("CustomFont", font_path))
                return "CustomFont"
            except Exception:
                continue

    return "Helvetica"


def build_styles(font_name: str):
    styles = getSampleStyleSheet()

    styles.add(
        ParagraphStyle(
            name="ReportTitle",
            parent=styles["Title"],
            fontName=font_name,
            fontSize=20,
            leading=26,
            spaceAfter=10,
            alignment=TA_LEFT,
            textColor=colors.HexColor("#17324D"),
        )
    )

    styles.add(
        ParagraphStyle(
            name="ReportMeta",
            parent=styles["Normal"],
            fontName=font_name,
            fontSize=9.5,
            leading=13,
            textColor=colors.HexColor("#666666"),
            spaceAfter=16,
        )
    )

    styles.add(
        ParagraphStyle(
            name="SectionHeading",
            parent=styles["Heading1"],
            fontName=font_name,
            fontSize=14.5,
            leading=20,
            spaceBefore=14,
            spaceAfter=8,
            textColor=colors.HexColor("#17324D"),
        )
    )

    styles.add(
        ParagraphStyle(
            name="SubHeading",
            parent=styles["Heading2"],
            fontName=font_name,
            fontSize=11.5,
            leading=16,
            spaceBefore=10,
            spaceAfter=5,
            textColor=colors.HexColor("#234E70"),
        )
    )

    styles.add(
        ParagraphStyle(
            name="Body",
            parent=styles["BodyText"],
            fontName=font_name,
            fontSize=10.2,
            leading=15.5,
            spaceBefore=2,
            spaceAfter=7,
        )
    )

    styles.add(
        ParagraphStyle(
            name="Small",
            parent=styles["BodyText"],
            fontName=font_name,
            fontSize=9,
            leading=13,
            spaceBefore=1,
            spaceAfter=4,
            textColor=colors.HexColor("#555555"),
        )
    )

    return styles


def _safe_text(value: Any) -> str:
    if value is None:
        return "확인 필요"
    text = str(value).strip()
    return text if text else "확인 필요"


def _normalize_inline_markdown(text: str) -> str:
    if not text:
        return ""

    # markdown bold -> reportlab bold
    text = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", text)
    text = re.sub(r"__(.+?)__", r"<b>\1</b>", text)

    return text


def _make_paragraph(text: str, style):
    if text is None:
        text = ""

    text = _normalize_inline_markdown(str(text))

    # 허용할 태그만 임시 치환
    text = text.replace("<br/>", "___BR___")
    text = text.replace("<br />", "___BR___")
    text = text.replace("<b>", "___B_OPEN___")
    text = text.replace("</b>", "___B_CLOSE___")

    # 나머지 문자 escape
    text = (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )

    # 허용 태그 복원
    text = text.replace("___BR___", "<br/>")
    text = text.replace("___B_OPEN___", "<b>")
    text = text.replace("___B_CLOSE___", "</b>")

    return Paragraph(text, style)


def _build_cover(story: List, styles, state: Dict[str, Any]) -> None:
    target_technologies = ", ".join(state.get("target_technologies", [])) or "확인 필요"
    selected_competitors = ", ".join(state.get("selected_competitors", [])) or "확인 필요"
    validation_result = state.get("validation_result")

    validation_label = "PASS" if validation_result else "FAIL"
    validation_text = f"최종 검증 결과: {validation_label}"

    story.append(_make_paragraph("반도체 기술 전략 분석 보고서", styles["ReportTitle"]))
    story.append(
        _make_paragraph(
            f"분석 대상 기술: {target_technologies}<br/>"
            f"주요 경쟁사: {selected_competitors}<br/>"
            f"{validation_text}",
            styles["ReportMeta"],
        )
    )
    story.append(Spacer(1, 6))


def _build_summary_table(styles, state: Dict[str, Any]) -> Table:
    validation_result = "PASS" if state.get("validation_result") else "FAIL"
    revision_points = state.get("revision_points", [])
    revision_summary = "<br/>".join(revision_points[:3]) if revision_points else "-"

    data = [
        [
            _make_paragraph("<b>항목</b>", styles["Body"]),
            _make_paragraph("<b>내용</b>", styles["Body"]),
        ],
        [
            _make_paragraph("분석 대상 기술", styles["Body"]),
            _make_paragraph(", ".join(state.get("target_technologies", [])) or "확인 필요", styles["Body"]),
        ],
        [
            _make_paragraph("주요 경쟁사", styles["Body"]),
            _make_paragraph(", ".join(state.get("selected_competitors", [])) or "확인 필요", styles["Body"]),
        ],
        [
            _make_paragraph("문서 기반 기술 커버리지", styles["Body"]),
            _make_paragraph(", ".join(state.get("available_document_technologies", [])) or "확인 필요", styles["Body"]),
        ],
        [
            _make_paragraph("웹 근거 수", styles["Body"]),
            _make_paragraph(str(len(state.get("web_findings", []))), styles["Body"]),
        ],
        [
            _make_paragraph("최종 검증 결과", styles["Body"]),
            _make_paragraph(validation_result, styles["Body"]),
        ],
        [
            _make_paragraph("주요 보완 포인트", styles["Body"]),
            _make_paragraph(revision_summary, styles["Body"]),
        ],
    ]

    table = Table(data, colWidths=[48 * mm, 122 * mm], repeatRows=1)
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#DCEAF7")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.HexColor("#17324D")),
                ("FONTNAME", (0, 0), (-1, -1), styles["Body"].fontName),
                ("FONTSIZE", (0, 0), (-1, -1), 9.5),
                ("LEADING", (0, 0), (-1, -1), 12),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#B8C7D9")),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("LEFTPADDING", (0, 0), (-1, -1), 8),
                ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                ("TOPPADDING", (0, 0), (-1, -1), 7),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
                ("BACKGROUND", (0, 1), (-1, -1), colors.white),
            ]
        )
    )
    return table


def _build_technology_comparison_table(styles, state: Dict[str, Any]) -> Table:
    analysis_by_technology = state.get("analysis_by_technology", {})
    web_findings = state.get("web_findings", [])

    rows = [[
        _make_paragraph("<b>기술</b>", styles["Body"]),
        _make_paragraph("<b>문서 근거 수</b>", styles["Body"]),
        _make_paragraph("<b>웹 근거 수</b>", styles["Body"]),
        _make_paragraph("<b>기술 성숙도 요약</b>", styles["Body"]),
        _make_paragraph("<b>비고</b>", styles["Body"]),
    ]]

    for tech in state.get("target_technologies", []):
        tech_analysis = analysis_by_technology.get(tech, {})
        tech_docs = tech_analysis.get("documents", [])
        tech_web = [item for item in web_findings if item.get("technology") == tech]
        tech_json = tech_analysis.get("analysis_json", {})

        maturity_summary = (
            tech_json.get("technology_maturity")
            or tech_json.get("maturity")
            or tech_json.get("summary")
            or "확인 필요"
        )

        note = "문서/웹 근거 기반 정리"
        if not tech_docs and not tech_web:
            note = "근거 부족"
        elif not tech_docs:
            note = "문서 근거 부족"
        elif not tech_web:
            note = "웹 근거 부족"

        rows.append([
            _make_paragraph(tech, styles["Body"]),
            _make_paragraph(str(len(tech_docs)), styles["Body"]),
            _make_paragraph(str(len(tech_web)), styles["Body"]),
            _make_paragraph(_safe_text(maturity_summary), styles["Body"]),
            _make_paragraph(note, styles["Body"]),
        ])

    table = Table(
        rows,
        colWidths=[24 * mm, 22 * mm, 22 * mm, 88 * mm, 24 * mm],
        repeatRows=1,
    )
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#17324D")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, -1), styles["Body"].fontName),
                ("FONTSIZE", (0, 0), (-1, -1), 9.2),
                ("LEADING", (0, 0), (-1, -1), 11.5),
                ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#B7C4CF")),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("LEFTPADDING", (0, 0), (-1, -1), 7),
                ("RIGHTPADDING", (0, 0), (-1, -1), 7),
                ("TOPPADDING", (0, 0), (-1, -1), 7),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
                ("BACKGROUND", (0, 1), (-1, -1), colors.HexColor("#F8FBFD")),
            ]
        )
    )
    return table


def _build_competitor_table(styles, state: Dict[str, Any]) -> Table:
    selected_competitors = state.get("selected_competitors", [])
    web_findings = state.get("web_findings", [])

    rows = [[
        _make_paragraph("<b>경쟁사</b>", styles["Body"]),
        _make_paragraph("<b>관련 기술</b>", styles["Body"]),
        _make_paragraph("<b>최근 웹 근거 요약</b>", styles["Body"]),
    ]]

    for competitor in selected_competitors:
        related = []
        findings = []

        for item in web_findings:
            text = f"{item.get('title', '')} {item.get('key_finding', '')}".lower()
            if competitor.lower() in text:
                tech = item.get("technology", "확인 필요")
                if tech not in related:
                    related.append(tech)
                findings.append(item)

        related_text = ", ".join(related) if related else "확인 필요"

        if findings:
            summary = []
            for item in findings[:2]:
                title = _safe_text(item.get("title"))
                date = _safe_text(item.get("published_date"))
                summary.append(f"- {title} ({date})")
            findings_text = "<br/>".join(summary)
        else:
            findings_text = "직접 매핑된 최신 웹 근거 부족"

        rows.append([
            _make_paragraph(competitor, styles["Body"]),
            _make_paragraph(related_text, styles["Body"]),
            _make_paragraph(findings_text, styles["Body"]),
        ])

    table = Table(rows, colWidths=[36 * mm, 30 * mm, 90 * mm], repeatRows=1)
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#DCEAF7")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.HexColor("#17324D")),
                ("FONTNAME", (0, 0), (-1, -1), styles["Body"].fontName),
                ("FONTSIZE", (0, 0), (-1, -1), 9.2),
                ("LEADING", (0, 0), (-1, -1), 11.5),
                ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#B7C4CF")),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("LEFTPADDING", (0, 0), (-1, -1), 7),
                ("RIGHTPADDING", (0, 0), (-1, -1), 7),
                ("TOPPADDING", (0, 0), (-1, -1), 7),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
            ]
        )
    )
    return table


def _append_body_from_final_report(story: List, styles, state: Dict[str, Any]) -> None:
    final_text = (
        state.get("final_report_text")
        or state.get("revised_draft_text")
        or state.get("draft_text", "")
    ).strip()

    if not final_text:
        story.append(_make_paragraph("최종 보고서 본문이 비어 있습니다.", styles["Body"]))
        return

    for raw_line in final_text.splitlines():
        line = raw_line.strip()
        if not line:
            story.append(Spacer(1, 3))
            continue

        if line.startswith("# "):
            story.append(_make_paragraph(line[2:].strip(), styles["ReportTitle"]))
        elif line.startswith("## "):
            story.append(_make_paragraph(line[3:].strip(), styles["SectionHeading"]))
        elif line.startswith("### "):
            story.append(_make_paragraph(line[4:].strip(), styles["SubHeading"]))
        elif line.startswith("- "):
            story.append(_make_paragraph(f"• {line[2:].strip()}", styles["Body"]))
        else:
            story.append(_make_paragraph(line, styles["Body"]))


def _build_pdf(state: Dict[str, Any], pdf_path: str) -> None:
    font_name = register_font()
    styles = build_styles(font_name)

    doc = SimpleDocTemplate(
        pdf_path,
        pagesize=A4,
        leftMargin=18 * mm,
        rightMargin=18 * mm,
        topMargin=16 * mm,
        bottomMargin=16 * mm,
        title="반도체 기술 전략 분석 보고서",
        author="AI Agent",
    )

    story: List = []

    _build_cover(story, styles, state)

    story.append(_make_paragraph("0. 보고서 요약", styles["SectionHeading"]))
    story.append(_build_summary_table(styles, state))
    story.append(Spacer(1, 10))

    story.append(_make_paragraph("1. 기술 성숙도 비교", styles["SectionHeading"]))
    story.append(_build_technology_comparison_table(styles, state))
    story.append(Spacer(1, 10))

    story.append(_make_paragraph("2. 경쟁사 비교", styles["SectionHeading"]))
    story.append(_build_competitor_table(styles, state))

    story.append(PageBreak())

    story.append(_make_paragraph("3. 본문 보고서", styles["SectionHeading"]))
    _append_body_from_final_report(story, styles, state)

    doc.build(story)


def run(state: Dict[str, Any]) -> Dict[str, Any]:
    output_dir = state.get("output_dir")
    if not output_dir:
        raise ValueError("Formatting Node 실행을 위해 state['output_dir']가 필요합니다.")

    pdf_path = str(Path(output_dir) / "final_report.pdf")
    md_path = str(Path(output_dir) / "final_report.md")

    final_text = (
        state.get("final_report_text")
        or state.get("revised_draft_text")
        or state.get("draft_text", "")
    ).strip()

    if not final_text:
        raise ValueError("포맷팅할 최종 보고서 텍스트가 비어 있습니다.")

    with open(md_path, "w", encoding="utf-8") as f:
        f.write(final_text)

    _build_pdf(state, pdf_path)

    state["formatted_markdown_path"] = md_path
    state["formatted_pdf_path"] = pdf_path
    state["status"] = "formatting_done"
    return state