"""
OCR Module
Handles image text extraction using EasyOCR with image preprocessing
and LLM-powered correction for handwritten notes.
"""

import os
from PIL import Image, ImageEnhance, ImageFilter
import numpy as np
import streamlit as st

# Lazy load the reader to avoid startup overhead
_reader = None

@st.cache_resource
def get_reader():
    import easyocr
    return easyocr.Reader(['en'], gpu=False)


def _preprocess_image(image_path: str) -> str:
    """
    Preprocess an image for optimal OCR speed and accuracy.
    Steps: resize (clamp boundaries), grayscale, contrast boost, sharpen.
    """
    img = Image.open(image_path)

    # 1. Grayscale
    img = img.convert("L")

    # 2. Resize intelligently to balance speed and accuracy
    w, h = img.size
    max_w = 1200
    min_w = 800

    if w > max_w:
        scale = max_w / w
        img = img.resize((int(w * scale), int(h * scale)), Image.LANCZOS)
    elif w < min_w:
        scale = 1000 / w
        img = img.resize((int(w * scale), int(h * scale)), Image.LANCZOS)

    # 3. Boost contrast
    enhancer = ImageEnhance.Contrast(img)
    img = enhancer.enhance(1.8)

    # 4. Sharpen
    img = img.filter(ImageFilter.SHARPEN)
    
    # Notice: We skip active binarization because EasyOCR does it internally better
    # and aggressive numpy thresholds delete handwritten characters.

    preprocessed_path = image_path.rsplit(".", 1)[0] + "_ocr_preprocessed.png"
    img.save(preprocessed_path)
    return preprocessed_path


def _llm_correct_ocr(raw_text: str) -> str:
    """
    Use the configured LLM to correct garbled OCR text from handwritten notes.
    Returns cleaned text. If LLM fails, returns the raw text as-is.
    """
    from openai import OpenAI

    api_key = os.getenv("LLM_API_KEY", "")
    base_url = os.getenv("LLM_API_BASE", "https://api.groq.com/openai/v1")
    model_name = os.getenv("LLM_API_MODEL", "llama-3.1-8b-instant")

    if not api_key:
        return raw_text

    try:
        client = OpenAI(api_key=api_key, base_url=base_url)

        response = client.chat.completions.create(
            model=model_name,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are a strict, objective OCR spellchecker.\n"
                        "Your ONLY job is to fix spelling and grammar errors in the user's raw OCR text.\n"
                        "RULES:\n"
                        "1. Output ONLY the original text, corrected for obvious typos and flow.\n"
                        "2. NEVER add conversational remarks like 'Here is the cleaned text'.\n"
                        "3. NEVER summarize, invent, or add new information that is not in the text.\n"
                        "4. Preserve formatting (bullet points, headings, numbering) as perfectly as possible.\n"
                        "5. If a word is completely unrecognizable, replace it with [unclear].\n"
                        "6. CRITICAL: If the provided text consists entirely of random symbols or gibberish, return an empty string.\n"
                        "7. DO NOT guess entirely missing concepts. Give exactly the text provided, smoothed out."
                    )
                },
                {
                    "role": "user",
                    "content": f"Raw OCR extracted text:\n\n{raw_text}"
                }
            ],
            temperature=0.0
        )

        corrected = response.choices[0].message.content.strip()
        
        # Stop hallucinated conversational wrappers or massive word-count explosions
        if "Here is" in corrected or len(corrected) > len(raw_text) * 3:
            return raw_text
            
        return corrected if corrected else raw_text

    except Exception as e:
        print(f"[OCR] LLM correction failed: {e}")
        return raw_text


def extract_text_from_image(image_path: str) -> str:
    """
    Extract text from an image file with preprocessing and LLM correction.
    Returns the extracted and corrected text as a clean string.
    """
    if not os.path.exists(image_path):
        raise FileNotFoundError(f"Image not found at {image_path}")

    # Preprocess image for better OCR
    try:
        preprocessed_path = _preprocess_image(image_path)
    except Exception as e:
        print(f"[OCR] Preprocessing failed, using original: {e}")
        preprocessed_path = image_path

    reader = get_reader()

    # Run OCR with optimized parameters for handwriting
    results = reader.readtext(
        preprocessed_path, 
        detail=1, 
        paragraph=False, 
        width_ths=0.7, 
        mag_ratio=1.5
    )

    # Keep more text for LLM correction (but filter absolute garbage)
    filtered_lines = []
    for (bbox, text, confidence) in results:
        if confidence >= 0.15 and text.strip():
            filtered_lines.append(text.strip())

    # Clean up temp file
    if preprocessed_path != image_path and os.path.exists(preprocessed_path):
        try:
            os.remove(preprocessed_path)
        except:
            pass

    extracted = "\n".join(filtered_lines).strip()

    if not extracted:
        return ""

    # Use LLM to correct garbled handwriting OCR
    corrected = _llm_correct_ocr(extracted)
    return corrected
