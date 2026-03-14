
import re

def clean_and_simplify(text: str) -> str:
    """
    Cleans raw extracted text by removing artifacts, fixing hyphenation,
    and normalizing whitespace. Also unwraps text broken by PDF line endings.
    """
    if not text:
        return ""

    # 1. Normalize line endings
    text = text.replace('\r', '\n')

    # 2. Fix hyphenated words at line ends (e.g., "infor-\nmation" -> "information")
    text = re.sub(r'-\s*\n\s*', '', text)

    # 3. Replace non-breaking spaces
    text = text.replace('\u00a0', ' ')

    # 4. Remove control characters
    text = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]', '', text)

    lines = text.split('\n')
    cleaned_lines = []
    buffer = ""

    for line in lines:
        line = line.strip()
        
        # Empty line -> Flush buffer and add empty line (paragraph break)
        if not line:
            if buffer:
                cleaned_lines.append(buffer)
                buffer = ""
            cleaned_lines.append("")
            continue

        # Check if line is a Heading or List Item
        is_list_item = re.match(r'^(\d+[\.\)]|\*|-|•)\s+', line)
        is_heading = (line.isupper() and len(line) < 50) or line.startswith('#')

        if is_list_item or is_heading:
            if buffer:
                cleaned_lines.append(buffer)
                buffer = ""
            cleaned_lines.append(line)
        else:
            # It's a normal text line. Merge with buffer if it exists.
            if buffer:
                # Heuristic: If buffer ends with hyphen, join directly (already handled by regex above mostly, but good safety)
                if buffer.endswith('-'):
                    buffer = buffer[:-1] + line
                # If line starts with lowercase, definitely merge with space
                elif line and line[0].islower():
                    buffer += " " + line
                # If buffer doesn't end with sentence punctuation, mostly merge
                elif not re.search(r'[.!?:]$', buffer):
                   buffer += " " + line
                else:
                    # Buffer ends with punctuation, Start with upper. 
                    # Use a space to keep them in same paragraph block
                    buffer += " " + line
            else:
                buffer = line

    if buffer:
        cleaned_lines.append(buffer)

    return "\n".join(cleaned_lines).strip()
