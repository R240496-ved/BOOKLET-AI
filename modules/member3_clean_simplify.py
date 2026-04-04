import re
import os

# -------------------------------
# 🔧 LOW-LEVEL FIXES
# -------------------------------

def fix_broken_words(text):
    """
    Fix words split by spaces due to PDF extraction safely.
    Example: c alled → called
    Only targets single non-vowel letters preceding a long word to avoid breaking "a cat", "I am".
    """
    # Fix cases like "c alled" -> "called", "s tops" -> "stops"
    # Consonant followed by a space and then 3+ letters.
    text = re.sub(r'\b([b-df-hj-np-tv-zB-DF-HJ-NP-TV-Z])\s+([a-zA-Z]{3,})\b', r'\1\2', text)
    return text

def fix_hyphens(text):
    """
    Fix spaced hyphens Example: single -seater → single-seater
    """
    return re.sub(r'\s*-\s*', '-', text)

def normalize_spacing(text):
    """
    Normalize spaces and punctuation
    """
    text = re.sub(r'\s+', ' ', text)
    text = re.sub(r'\s+([.,!?])', r'\1', text)
    return text.strip()

def clean_text_heuristics(text):
    """
    Apply safe low-level cleaning fixes
    """
    text = fix_broken_words(text)
    text = fix_hyphens(text)
    text = normalize_spacing(text)
    return text

# -------------------------------
# 🧠 LLM TEXT CLEANING
# -------------------------------

def _llm_clean_chunk(text_chunk: str) -> str:
    """Uses LLM to cleanly restructure the text chunk without adding extra information."""
    from openai import OpenAI
    api_key = os.getenv("LLM_API_KEY", "")
    base_url = os.getenv("LLM_API_BASE", "https://api.groq.com/openai/v1")
    model_name = os.getenv("LLM_API_MODEL", "llama-3.1-8b-instant")
    
    if not api_key:
        return text_chunk
        
    try:
        client = OpenAI(api_key=api_key, base_url=base_url)
        response = client.chat.completions.create(
            model=model_name,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are a STRICT document cleaning spell-checker.\n"
                        "Your ONLY job is to fix broken words (e.g. 'c alled' -> 'called'), weird spacing, and obvious typos.\n"
                        "RULES:\n"
                        "1. Return ONLY the exact original text with formatting/spelling fixed.\n"
                        "2. DO NOT ADD ANY NEW OR UNRELATED INFORMATION. DO NOT SUMMARIZE AND DO NOT REPHRASE.\n"
                        "3. NEVER add conversational remarks or prefixes.\n"
                        "4. Preserve bullet points, headings, and line breaks exactly."
                    )
                },
                {"role": "user", "content": f"Raw text:\n\n{text_chunk}"}
            ],
            temperature=0.0
        )
        cleaned = response.choices[0].message.content.strip()
        # Fallback if the LLM yaps too much or hallucinated a completely different length
        if "Here is" in cleaned and len(cleaned.split("\n")) <= 2:
            return text_chunk
        
        # Additional safety: if response is drastically shorter or longer, fallback to original
        if len(cleaned) < len(text_chunk) * 0.3 or len(cleaned) > len(text_chunk) * 1.5:
            return text_chunk
            
        return cleaned if cleaned else text_chunk
    except Exception as e:
        print(f"[Clean] LLM Error: {e}")
        return text_chunk

# -------------------------------
# 🧠 MAIN CLEAN + STRUCTURE
# -------------------------------

def clean_and_simplify(text: str) -> str:
    """
    Full pipeline with IMAGE PROTECTION.
    We apply heuristic cleanup and structure it accurately.
    For very messy structures, we also chunk and optionally LLM clean if necessary,
    but here we handle paragraph cohesion intelligently.
    """
    if not text:
        return ""

    lines = text.split("\n")
    processed_lines = []

    for line in lines:
        raw = line.strip()
        if raw.startswith("![IMAGE:"):
            processed_lines.append(raw)
        else:
            cleaned = clean_text_heuristics(raw)
            if cleaned:
                processed_lines.append(cleaned)
            elif not raw: # keep empty lines for paragraph splits
                processed_lines.append("")

    # Now group into paragraphs, but treat IMAGE markers as hard breaks
    final_lines = []
    buffer = ""

    for line in processed_lines:
        if line.startswith("![IMAGE:"):
            if buffer:
                final_lines.append(buffer)
                buffer = ""
            final_lines.append(line)
            final_lines.append("")
            continue

        if not line:
            if buffer:
                final_lines.append(buffer)
                buffer = ""
            if final_lines and final_lines[-1] != "":
                final_lines.append("")
            continue

        # Is it a heading or list?
        words = line.split()
        is_struct = (
            re.match(r'^\s*(\d+[\.\)]|\*|-|•)\s+', line) or
            (line.isupper() and len(words) <= 8) or
            (len(words) <= 8 and not line.endswith(".") and line[0].isupper())
        )

        if is_struct:
            if buffer:
                final_lines.append(buffer)
                buffer = ""
            final_lines.append(line)
        else:
            if buffer:
                buffer += " " + line
            else:
                buffer = line

    if buffer:
        final_lines.append(buffer)
        
    combined_text = "\n".join(final_lines).strip()
    
    # If the text is manageable, use LLM to ensure no unwanted information and perfect cohesion.
    # Otherwise just return the heuristically cleaned text. We chunk it if it's too large,
    # but to save time & tokens in a primary run, the heuristic text is vastly improved now. (No "isthe").
    
    return combined_text