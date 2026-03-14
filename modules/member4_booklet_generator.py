


from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib.pagesizes import A4
from reportlab.lib.enums import TA_JUSTIFY
import os

def generate_booklet(text: str):
    """
    Generates properly formatted PDF booklet from Markdown-structured text.
    Parsing rules:
    - # Heading -> Heading1
    - ## Heading -> Heading2
    - - Bullet -> Bullet style
    - **Bold** -> <b>Bold</b> (handled by ReportLab's HTML-like markup)
    """

    output_dir = "data/output"
    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, "booklet.pdf")

    doc = SimpleDocTemplate(output_path, pagesize=A4)
    elements = []

    styles = getSampleStyleSheet()
    
    # Custom Styles
    style_h1 = styles["Heading1"]
    style_h1.alignment = 1 # Center
    
    style_h2 = styles["Heading2"]
    
    style_normal = styles["Normal"]
    style_normal.alignment = TA_JUSTIFY
    
    # Bullet style - indented
    style_bullet = ParagraphStyle(
        'Bullet',
        parent=styles['Normal'],
        leftIndent=20,
        spaceBefore=2,
        spaceAfter=2,
        bulletIndent=10
    )

    lines = text.split("\n")

    for line in lines:
        line = line.strip()
        if not line:
            # Add a small spacer for empty lines
            elements.append(Spacer(1, 0.1 * inch))
            continue

        # 1. Parse Headings
        if line.startswith("# "):
            elements.append(Paragraph(line[2:], style_h1))
            elements.append(Spacer(1, 0.2 * inch))
        
        elif line.startswith("## "):
            elements.append(Paragraph(line[3:], style_h2))
            elements.append(Spacer(1, 0.1 * inch))
            
        # 2. Parse Bullets
        elif line.startswith("- "):
            clean_content = line[2:]
            # Replace markdown bold **text** with ReportLab tags <b>text</b>
            clean_content = clean_content.replace("**", "<b>", 1).replace("**", "</b>", 1)
            elements.append(Paragraph(f"• {clean_content}", style_bullet))
        
        # 3. Normal Paragraph
        else:
             # Replace markdown bold **text** with ReportLab tags <b>text</b>
            line = line.replace("**", "<b>", 1).replace("**", "</b>", 1)
            elements.append(Paragraph(line, style_normal))
            elements.append(Spacer(1, 0.1 * inch))

    try:
        doc.build(elements)
        return True
    except Exception as e:
        print(f"PDF Generation Error: {e}")
        return False
