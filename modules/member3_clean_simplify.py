import re


# -------------------------------
# 🔧 LOW-LEVEL FIXES
# -------------------------------

def fix_broken_words(text):
    """
    Fix words split by spaces due to PDF extraction
    Example:
    c alled → called
    sto ps → stops
    """

    # Join small fragments (most common PDF issue)
    text = re.sub(r'\b([a-zA-Z]{1,3})\s+([a-zA-Z]{1,3})\b', r'\1\2', text)

    # Fix cases like "c alled"
    text = re.sub(r'\b([a-zA-Z])\s+([a-zA-Z]{2,})\b', r'\1\2', text)

    return text


def fix_hyphens(text):
    """
    Fix spaced hyphens
    Example:
    single -seater → single-seater
    1.6 -liter → 1.6-liter
    """
    return re.sub(r'\s*-\s*', '-', text)


def normalize_spacing(text):
    """
    Normalize spaces and punctuation
    """
    text = re.sub(r'\s+', ' ', text)
    text = re.sub(r'\s+([.,!?])', r'\1', text)
    return text.strip()


def clean_text(text):
    """
    Apply all low-level cleaning fixes
    """
    text = fix_broken_words(text)
    text = fix_hyphens(text)
    text = normalize_spacing(text)
    return text


# -------------------------------
# 🧠 MAIN CLEAN + STRUCTURE
# -------------------------------

def clean_and_simplify(text: str) -> str:
    """
    Full pipeline with IMAGE PROTECTION.
    """
    if not text:
        return ""

    # Split into lines to protect markers first
    lines = text.split("\n")
    processed_lines = []

    for line in lines:
        raw = line.strip()
        if raw.startswith("![IMAGE:"):
            processed_lines.append(raw)
        else:
            # Only clean non-image lines
            cleaned = clean_text(raw)
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
            final_lines.append("") # space after image
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

    return "\n".join(final_lines).strip()