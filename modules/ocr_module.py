"""
OCR Module
Handles image text extraction using EasyOCR with image preprocessing
and LLM-powered correction for handwritten notes.
"""

import os
import streamlit as st
from PIL import Image, ImageEnhance, ImageFilter
import numpy as np
import cv2
import torch

# Lazy load models
_reader = None

def _classify_layout(image_path: str) -> dict:
    """
    Intelligently classifies the image into Table, Math, or General Text.
    Uses OpenCV to find grids or math-specific features.
    """
    import cv2
    import numpy as np

    img = cv2.imread(image_path)
    if img is None:
        return {"type": "Text", "features": {}}

    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    
    # 1. Check for Tables (Grid Detection)
    # Binary inverse for line detection
    _, binary = cv2.threshold(gray, 200, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
    
    # Detect horizontal lines
    h_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (40, 1))
    h_lines = cv2.morphologyEx(binary, cv2.MORPH_OPEN, h_kernel)
    
    # Detect vertical lines
    v_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (1, 40))
    v_lines = cv2.morphologyEx(binary, cv2.MORPH_OPEN, v_kernel)
    
    # Combine to find a grid
    grid = cv2.add(h_lines, v_lines)
    n_h = np.sum(h_lines > 0)
    n_v = np.sum(v_lines > 0)
    
    # Decision Logic
    # High density of both horizontal and vertical lines strongly indicates a table
    if n_h > 5000 and n_v > 5000:
        return {"type": "TABLE DOCUMENT", "features": {"grid": True}}

    # 2. Check for Math (Isolated bars)
    # We only check for math IF it's not a table
    lines_p = cv2.HoughLinesP(binary, 1, np.pi/180, 100, minLineLength=50, maxLineGap=10)
    has_isolated_bars = False
    if lines_p is not None:
        img_w = img.shape[1]
        for line in lines_p:
            x1, y1, x2, y2 = line[0]
            line_w = abs(x1 - x2)
            # Math bars are usually in the middle, not spanning whole width
            if abs(y1 - y2) < 5 and (img_w * 0.1 < line_w < img_w * 0.7):
                has_isolated_bars = True
                break

    if has_isolated_bars:
        return {"type": "MATH", "features": {"bar_y": True}}
    else:
        return {"type": "GENERAL DOCUMENT", "features": {}}

@st.cache_resource
def get_reader():
    import easyocr
    import torch
    use_gpu = torch.cuda.is_available()
    return easyocr.Reader(['en'], gpu=use_gpu)


def _validate_extraction(text: str, detected_type: str) -> bool:
    """
    Strictly validates the OCR result.
    If it's a table, it MUST have multiple rows and logical content.
    """
    if not text or len(text.strip()) < 10:
        return False
        
    if detected_type == "TABLE DOCUMENT":
        lines = [l for l in text.split("\n") if "|" in l]
        # Must have at least 3 rows (Header, Separator, and at least 1-2 data rows)
        if len(lines) < 3:
            return False
        # Syllabus specific check: headers should be present
        headers = ["sr no", "module", "content", "hours", "lo"]
        text_lower = text.lower()
        match_count = sum(1 for h in headers if h in text_lower)
        if match_count < 2 and len(text.split()) < 30:
            return False
            
    return True

def _preprocess_image(image_path: str, pass_num: int = 1) -> dict:
    """
    Preprocess image with varying intensities based on pass number.
    Pass 2: 2x Upscale + Stronger Sharpening
    """
    import cv2
    import numpy as np

    img = cv2.imread(image_path)
    if img is None:
        return {"main": image_path, "layout": "standard"}
        
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    # Adaptive Preprocessing based on pass
    if pass_num == 2:
        # Pass 2: Upscale, denoise heavily, and use Otsu to completely erase light notebook lines
        gray = cv2.resize(gray, None, fx=2, fy=2, interpolation=cv2.INTER_CUBIC)
        denoised = cv2.fastNlMeansDenoising(gray, h=25)
        _, enhanced = cv2.threshold(denoised, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    else:
        # Pass 1: Standard CLAHE for structured documents
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8,8))
        enhanced = clahe.apply(gray)
    
    # Grid detection for Table Document classification
    _, binary = cv2.threshold(enhanced, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
    h_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (40, 1))
    h_lines = cv2.morphologyEx(binary, cv2.MORPH_OPEN, h_kernel)
    v_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (1, 40))
    v_lines = cv2.morphologyEx(binary, cv2.MORPH_OPEN, v_kernel)
    
    n_h = np.sum(h_lines > 0)
    n_v = np.sum(v_lines > 0)
    
    # Save processed
    preprocessed_path = image_path.rsplit(".", 1)[0] + f"_p{pass_num}.png"
    cv2.imwrite(preprocessed_path, enhanced)
    
    return {
        "main": preprocessed_path,
        "layout": "TABLE DOCUMENT" if (n_h > 3000 and n_v > 3000) else "GENERAL DOCUMENT",
        "h": enhanced.shape[0],
        "w": enhanced.shape[1]
    }


def _llm_correct_ocr(raw_text: str, detected_type: str = "Text") -> str:
    """
    Universal Academic Parser.
    Reconstructs content based on detected layout type.
    """
    from openai import OpenAI

    api_key = os.getenv("LLM_API_KEY", "")
    base_url = os.getenv("LLM_API_BASE", "https://api.groq.com/openai/v1")
    model_name = os.getenv("LLM_API_MODEL", "llama-3.1-8b-instant")

    if not api_key:
        return raw_text

    try:
        client = OpenAI(api_key=api_key, base_url=base_url)

        system_prompt = (
            f"You are a Smart Multi-Purpose Document Recognition System.\n"
            f"Detected Content Type: {detected_type}\n\n"
            "YOUR MISSION:\n"
            "Extract and format the content perfectly according to its type.\n\n"
            "STRICT RULES:\n"
            "1. TABLE DOCUMENT: If detected as a table, RECONSTRUCT THE TABLE accurately. Use Markdown '| Column |' format. Ensure Sr No, Module, and Content are preserved. NEVER treat a table as a math equation.\n"
            "2. MATH: Reconstruct algebraic expressions and solve them. \n"
            "   [CRITICAL HANDWRITING DICTIONARY]\n"
            "   - '9' or '4' or 'g' is almost always a handwritten 'y' or 'x'.\n"
            "   - '_1' or 'z' or '2_' is almost always a superscript '^2'.\n"
            "   - '9-1' is handwritten 'y-1'.\n"
            "   - '4_1' or 'y_1' is handwritten 'y^2'.\n"
            "   - '-?' or '?' is handwritten '=?'.\n"
            "   - Look at the full string: if you see '4_1 -4 9-1 9-?', use your mathematical intuition to reconstruct the classic algebraic fraction: '(y^2 - 1) / (y - 1) = 4'.\n"
            "3. NOTES: Clean up paragraphs and bullet points.\n\n"
            "OUTPUT FORMAT:\n"
            "Detected Type: <Type>\n\n"
            "Extracted Content:\n"
            "<The result>\n\n"
            "If Math:\n"
            "Solution: <stepwise>\n"
            "Final Answer: <result>\n\n"
            "NO CHAT. NO GARBAGE. NO MISTAKING TABLES FOR MATH."
        )

        response = client.chat.completions.create(
            model=model_name,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"OCR Data:\n{raw_text}"}
            ],
            temperature=0.0
        )

        return response.choices[0].message.content.strip()

    except Exception as e:
        print(f"[OCR] Reconstruct failed: {e}")
        return raw_text


def extract_text_from_image(image_path: str) -> str:
    """
    High-Accuracy Multi-Stage OCR System with Validation and Auto-Retry.
    """
    if not os.path.exists(image_path):
        return ""

    reader = get_reader()
    final_output = ""
    
    # STAGE 1: CLASSIFICATION
    layout_info = _classify_layout(image_path)
    detected_type = layout_info["type"]
    
    # MULTI-PASS RETRY LOOP
    for pass_num in [1, 2]:
        with st.spinner(f"OCR Pass {pass_num}: Processing as {detected_type}..."):
            prep = _preprocess_image(image_path, pass_num=pass_num)
            preprocessed_path = prep["main"]
            
            # Split page if it's a large document
            if prep["h"] > prep["w"] * 1.5:
                # Top Half
                t_img = cv2.imread(preprocessed_path)[:prep["h"]//2, :]
                b_img = cv2.imread(preprocessed_path)[prep["h"]//2:, :]
                
                t_path = preprocessed_path.replace(".png", "_top.png")
                b_path = preprocessed_path.replace(".png", "_bot.png")
                cv2.imwrite(t_path, t_img)
                cv2.imwrite(b_path, b_img)
                
                t_res = reader.readtext(t_path, detail=0, paragraph=True)
                b_res = reader.readtext(b_path, detail=0, paragraph=True)
                raw_text = "\n".join(t_res + b_res)
                
                # Cleanup splits
                try: os.remove(t_path); os.remove(b_path)
                except: pass
            else:
                res = reader.readtext(preprocessed_path, detail=0, paragraph=True)
                raw_text = "\n".join(res)

            if preprocessed_path != image_path:
                try: os.remove(preprocessed_path)
                except: pass

            if not raw_text.strip():
                continue

            # LLM RECONSTRUCTION
            reconstructed = _llm_correct_ocr(raw_text, detected_type=detected_type)
            
            # VALIDATION
            if _validate_extraction(reconstructed, detected_type):
                return reconstructed
            else:
                print(f"[OCR] Pass {pass_num} failed validation. Retrying...")
                st.warning(f"Pass {pass_num} result was low quality. Retrying with enhancement...")
                final_output = reconstructed # Keep as fallback

    return final_output if final_output else "OCR extraction failed. Please provide a clearer image."
