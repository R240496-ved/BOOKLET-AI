"""
Booklet Generator (Final Polish)
Generates a structured PDF booklet from Markdown text using ReportLab.
Optimised for clean typography and perfect bullet alignment.
IMAGE-FREE as per user request.
"""

import os
import re
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, PageBreak, HRFlowable
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib.pagesizes import A4
from reportlab.lib.enums import TA_JUSTIFY, TA_CENTER, TA_LEFT
from reportlab.lib import colors


# ─────────────────────────────────────────────
# STYLES
# ─────────────────────────────────────────────

def _build_styles():
    styles = getSampleStyleSheet()

    # Title
    title_style = ParagraphStyle(
        "BookTitle",
        parent=styles["Title"],
        fontSize=28,
        spaceAfter=30,
        spaceBefore=10,
        alignment=TA_CENTER,
        textColor=colors.HexColor("#1A1A2E"),
        fontName="Helvetica-Bold",
        leading=34,
    )

    # H1 (Main Sections)
    h1_style = ParagraphStyle(
        "H1",
        parent=styles["Heading1"],
        fontSize=20,
        spaceAfter=12,
        spaceBefore=22,
        textColor=colors.HexColor("#E94F37"),
        fontName="Helvetica-Bold",
        leftIndent=0,
    )

    # H2 (Sub Sections)
    h2_style = ParagraphStyle(
        "H2",
        parent=styles["Heading2"],
        fontSize=15,
        spaceAfter=8,
        spaceBefore=14,
        textColor=colors.HexColor("#0F3A60"),
        fontName="Helvetica-Bold",
        leftIndent=0,
    )

    # Normal Body Text
    normal_style = ParagraphStyle(
        "Body",
        parent=styles["Normal"],
        fontSize=11,
        spaceAfter=6,
        spaceBefore=4,
        alignment=TA_JUSTIFY,
        leading=16, # Better readability
        textColor=colors.HexColor("#333333"),
    )

    # Bullet Style (Perfectly Aligned)
    bullet_style = ParagraphStyle(
        "Bullet",
        parent=styles["Normal"],
        fontSize=11,
        leftIndent=24,      # Space from margin to text start
        bulletIndent=12,    # Space from margin to bullet start
        spaceAfter=5,
        spaceBefore=3,
        leading=16,
        alignment=TA_LEFT,
    )

    return {
        "title": title_style,
        "h1": h1_style,
        "h2": h2_style,
        "normal": normal_style,
        "bullet": bullet_style,
    }


# ─────────────────────────────────────────────
# MARKDOWN BOLD → REPORTLAB
# ─────────────────────────────────────────────

def _convert_bold(text: str) -> str:
    """Convert **bold** markdown to ReportLab XML bold tags."""
    # Clean up markers and use XML <b>
    text = re.sub(r"\*\*(.*?)\*\*", r"<b>\1</b>", text)
    # Handle possible artifacts from extraction
    text = text.replace("▪", "•")
    return text


# ─────────────────────────────────────────────
# MAIN GENERATOR
# ─────────────────────────────────────────────

def generate_booklet(
    text: str,
    images: list[dict] = None, # Left for backward combat, but IGNORING as per request
    title: str = "Study Booklet",
    output_path: str = "data/output/booklet.pdf"
) -> bool:
    """
    Generate a styled PDF booklet.
    Images are EXCLUDED as per final user update.
    """
    try:
        os.makedirs(os.path.dirname(output_path), exist_ok=True)

        doc = SimpleDocTemplate(
            output_path,
            pagesize=A4,
            leftMargin=65, # Wide margins for premium feel
            rightMargin=65,
            topMargin=60,
            bottomMargin=60,
        )

        styles = _build_styles()
        elements = []

        # --- Title Page ---
        elements.append(Spacer(1, 0.5 * inch))
        elements.append(Paragraph(title, styles["title"]))
        elements.append(HRFlowable(width="100%", thickness=2, color=colors.HexColor("#E94F37")))
        elements.append(Spacer(1, 0.4 * inch))

        # --- Parse markdown lines ---
        lines = text.split("\n")

        for line in lines:
            raw = line.strip()
            if not raw or raw.startswith("![IMAGE:"):
                # Skip markers and empty lines
                if not raw:
                    elements.append(Spacer(1, 0.08 * inch))
                continue

            converted = _convert_bold(raw)

            if raw.startswith("# "):
                elements.append(Spacer(1, 0.1 * inch))
                elements.append(Paragraph(converted[2:], styles["h1"]))
                elements.append(HRFlowable(width="100%", thickness=1,
                                            color=colors.HexColor("#E94F37"), spaceAfter=6))

            elif raw.startswith("## "):
                elements.append(Paragraph(converted[3:], styles["h2"]))

            elif raw.startswith("- ") or raw.startswith("• "):
                # Support both markdown and extracted bullet markers
                content = converted[2:] if raw.startswith("- ") else converted[2:]
                elements.append(Paragraph(content, styles["bullet"], bulletText="•"))

            else:
                # Regular paragraph
                elements.append(Paragraph(converted, styles["normal"]))

        doc.build(elements)
        return True

    except Exception as e:
        print(f"[Booklet Generator] Error: {e}")
        return False