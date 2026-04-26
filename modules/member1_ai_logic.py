

# import re
# import os
# from openai import OpenAI

# def call_openai_api(prompt: str, context: str = "") -> str:
#     """
#     Calls Groq API to generate a response based on the prompt and optional context.
#     Returns the structured markdown response.
#     """
#     api_key = os.getenv("LLM_API_KEY")
#     if not api_key:
#         return "Error: LLM_API_KEY not found in environment variables."

#     client = OpenAI(
#         api_key=api_key,
#         base_url="https://api.groq.com/openai/v1"
#     )

#     system_msg = "You are a helpful study assistant. Format your output in clean Markdown (headings #, ##, bullets -, bold **). "
#     if context:
#         system_msg += f"Use the following document content as context for your answers:\n\n{context[:20000]}" # Limit context to avoid token limits if too large

#     try:
#         response = client.chat.completions.create(
#             model="llama-3.1-8b-instant",
#             messages=[
#                 {"role": "system", "content": system_msg},
#                 {"role": "user", "content": prompt}
#             ],
#             temperature=0.7
#         )
#         return response.choices[0].message.content
#     except Exception as e:
#         return f"Error calling OpenAI API: {str(e)}"

# def build_structure(text: str) -> str:
#     """
#     Structuring logic to convert cleaned text into Markdown with:
#     - Headings (#, ##)
#     - Bullet points (-)
#     - Definitions (**Term**: Def)
#     """
#     lines = text.split('\n')
#     structured_lines = []
    
#     for line in lines:
#         line = line.strip()
#         if not line:
#             # Preserve paragraph breaks
#             structured_lines.append("") 
#             continue

#         # 1. Detect HEADING (All INTRO, OUTRO, or short all-caps lines)
#         #    Also check if it looks like a slide title or chapter start
#         is_upper = line.isupper() and len(line) > 3
#         is_short_title = len(line.split()) <= 6 and not line.endswith('.') and line[0].isupper()
        
#         if is_upper:
#             # Main Heading
#             structured_lines.append(f"\n# {line.title()}\n")
#             continue
#         elif is_short_title:
#              # Sub Heading
#             structured_lines.append(f"\n## {line}\n")
#             continue

#         # 2. Detect LISTS (Numbered or Bulleted in raw text)
#         #    Regex for "1.", "1)", "•", "-", "*"
#         if re.match(r'^(\d+[\.\)]|\*|-|•)\s+', line):
#             # Clean the marker and treat as bullet
#             content = re.sub(r'^(\d+[\.\)]|\*|-|•)\s+', '', line)
#             structured_lines.append(f"- {content}")
#             continue

#         # 3. Detect DEFINITIONS (Pattern: "Term: Definition" or "Term - Definition")
#         #    We look for a colon/hyphen appearing early in the line
#         match_def = re.match(r'^([A-Z][a-zA-Z\s]+?)(:| - )\s*(.+)', line)
#         if match_def:
#             term, sep, definition = match_def.groups()
#             if len(term.split()) <= 5: # prevent long sentences being treated as definitions
#                 structured_lines.append(f"- **{term.strip()}**: {definition.strip()}")
#                 continue
        
#         # 4. Fallback: Analyze paragraph structure
#         #    If it's a long text block with multiple sentences, break it down.
#         #    Otherwise, treat as a single bullet point.
        
#         # Split by period/question mark/exclamation followed by space
#         # This regex looks for sentence endings while trying to avoid common abbreviations
#         # (It's a heuristic, not perfect without NLP libraries)
#         sentences = re.split(r'(?<=[.!?])\s+(?=[A-Z])', line)
        
#         if len(sentences) > 1:
#             for sent in sentences:
#                 sent = sent.strip()
#                 if sent:
#                     structured_lines.append(f"- {sent}")
#         else:
#             structured_lines.append(f"- {line}")

#     return "\n".join(structured_lines)
import re
import os
from openai import OpenAI


# ==========================
# LLM CALL FUNCTION
# ==========================

def call_openai_api(prompt: str, context: str = "") -> str:
    """
    Calls Groq/OpenAI-compatible API to generate a response.
    Returns Markdown formatted output.
    """

    api_key = os.getenv("LLM_API_KEY")

    if not api_key:
        return "Error: LLM_API_KEY not found in environment variables."

    client = OpenAI(
        api_key=api_key,
        base_url="https://api.groq.com/openai/v1"
    )

    system_message = (
        "You are a helpful study assistant. "
        "Always format output in clean Markdown using headings (#, ##), "
        "bullet points (-), and bold definitions (**term**). "
        "IMPORTANT: If the input text contains lines starting with '![IMAGE:', YOU MUST PRESERVE THEM EXACTLY. "
        "Never alter, translate, or remove ![IMAGE:path] lines. Keep them in their original relative positions."
    )

    if context:
        context = context[:7000]
        system_message += f"\n\nUse this document as reference:\n{context}"

    try:
        response = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[
                {"role": "system", "content": system_message},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7
        )

        return response.choices[0].message.content

    except Exception as e:
        return f"API Error: {str(e)}"


# ==========================
# TEXT STRUCTURING LOGIC
# ==========================

def build_structure(text: str) -> str:
    """
    Converts cleaned raw text into structured Markdown.

    Output format:
    - # Heading
    - ## Subheading
    - Bullet points
    - Definitions
    """

    lines = text.split("\n")
    structured_lines = []

    append = structured_lines.append

    for line in lines:

        line = line.strip()

        # --------------------------
        # IMAGE MARKER DETECTION
        # --------------------------
        if line.startswith("![IMAGE:"):
            append(line)
            continue

        # --------------------------
        # Skip excessive empty lines
        # --------------------------

        if not line:
            if structured_lines and structured_lines[-1] != "":
                append("")
            continue

        # --------------------------
        # HEADING DETECTION
        # --------------------------

        words = line.split()

        is_all_caps = line.isupper() and len(words) <= 8
        is_title_case = (
            len(words) <= 8
            and not line.endswith(".")
            and line[0].isupper()
        )

        if is_all_caps:
            append(f"\n# {line.title()}\n")
            continue

        if is_title_case:
            append(f"\n## {line}\n")
            continue

        # --------------------------
        # BULLET / NUMBER LISTS
        # --------------------------

        bullet_match = re.match(r'^\s*(\d+[\.\)]|\*|-|•)\s+(.*)', line)

        if bullet_match:
            content = bullet_match.group(2)
            append(f"- {content}")
            continue

        # --------------------------
        # DEFINITION DETECTION
        # Example:
        # Momentum: product of mass and velocity
        # --------------------------

        definition_match = re.match(
            r'^([A-Z][a-zA-Z\s]{1,40})(:| - )(.+)',
            line
        )

        if definition_match:

            term, sep, definition = definition_match.groups()

            if len(term.split()) <= 5:
                append(f"- **{term.strip()}**: {definition.strip()}")
                continue

        # --------------------------
        # LONG PARAGRAPH SPLITTING
        # --------------------------

        if len(line) > 120:

            sentences = re.split(r'(?<=[.!?])\s+', line)

            for sent in sentences:
                sent = sent.strip()

                if sent:
                    append(f"- {sent}")

        else:
            append(f"- {line}")

    return "\n".join(structured_lines).strip()

# ==========================
# 🧠 SMART NOTES GENERATOR (MAGIC LAYER)
# ==========================

def split_sentences(text):
    return re.split(r'(?<=[.!?])\s+', text)


def categorize_sentence(sentence):
    s = sentence.lower()

    if "championship" in s:
        return "championship"

    elif "includes" in s:
        return "process"

    elif "engine" in s or "hybrid" in s:
        return "technical"

    elif "important" in s or "strategy" in s:
        return "factors"

    elif "regulation" in s:
        return "rules"

    else:
        return "general"


def generate_smart_notes(text):

    lines = text.split("\n")

    output = []
    current_section = None

    for line in lines:

        line = line.strip()

        if not line:
            continue

        words = line.split()

        # --------------------------
        # IMAGE MARKER DETECTION
        # --------------------------
        if line.startswith("![IMAGE:"):
            output.append(line)
            continue

        # --------------------------
        # 🔥 Detect HEADINGS
        # --------------------------

        if len(words) <= 8 and line[0].isupper() and not line.endswith("."):
            current_section = line
            output.append(f"\n# {line}\n")
            continue

        # --------------------------
        # 🔥 Detect BULLETS inside text
        # --------------------------

        if "•" in line:
            parts = line.split("•")

            for part in parts:
                part = part.strip()
                if part:
                    output.append(f"- {part}")

            continue

        # --------------------------
        # 🔥 Detect numbered data
        # --------------------------

        if re.search(r'\d+(st|nd|rd|th)', line):
            items = re.split(r'•', line)

            for item in items:
                item = item.strip()
                if item:
                    output.append(f"- {item}")

            continue

        # --------------------------
        # 🔥 Split long sentences
        # --------------------------

        if len(line) > 100:
            sentences = re.split(r'(?<=[.!?])\s+', line)

            for s in sentences:
                if s:
                    output.append(f"- {s}")

        else:
            output.append(f"- {line}")

    return "\n".join(output)# ==========================
# 🚀 FINAL ENTRY FUNCTION
# ==========================

def generate_notes(text, use_llm=False):
    """
    Final function to be used in your project
    """

    # Step 1: Smart notes (magic)
    smart_output = generate_smart_notes(text)

    # Step 2: Fallback if output is weak
    if len(smart_output.strip()) < 50:
        smart_output = build_structure(text)

    # Step 3: Optional LLM enhancement
    if use_llm:
        llm_output = call_openai_api(
            "Convert this into clean structured study notes:\n\n" + smart_output
        )

        if "Error" not in llm_output and "API" not in llm_output:
            return llm_output

    return smart_output
    