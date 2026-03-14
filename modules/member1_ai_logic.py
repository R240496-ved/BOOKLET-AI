

import re
import os
from openai import OpenAI

def call_openai_api(prompt: str, context: str = "") -> str:
    """
    Calls Groq API to generate a response based on the prompt and optional context.
    Returns the structured markdown response.
    """
    api_key = os.getenv("LLM_API_KEY")
    if not api_key:
        return "Error: LLM_API_KEY not found in environment variables."

    client = OpenAI(
        api_key=api_key,
        base_url="https://api.groq.com/openai/v1"
    )

    system_msg = "You are a helpful study assistant. Format your output in clean Markdown (headings #, ##, bullets -, bold **). "
    if context:
        system_msg += f"Use the following document content as context for your answers:\n\n{context[:20000]}" # Limit context to avoid token limits if too large

    try:
        response = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[
                {"role": "system", "content": system_msg},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"Error calling OpenAI API: {str(e)}"

def build_structure(text: str) -> str:
    """
    Structuring logic to convert cleaned text into Markdown with:
    - Headings (#, ##)
    - Bullet points (-)
    - Definitions (**Term**: Def)
    """
    lines = text.split('\n')
    structured_lines = []
    
    for line in lines:
        line = line.strip()
        if not line:
            # Preserve paragraph breaks
            structured_lines.append("") 
            continue

        # 1. Detect HEADING (All INTRO, OUTRO, or short all-caps lines)
        #    Also check if it looks like a slide title or chapter start
        is_upper = line.isupper() and len(line) > 3
        is_short_title = len(line.split()) <= 6 and not line.endswith('.') and line[0].isupper()
        
        if is_upper:
            # Main Heading
            structured_lines.append(f"\n# {line.title()}\n")
            continue
        elif is_short_title:
             # Sub Heading
            structured_lines.append(f"\n## {line}\n")
            continue

        # 2. Detect LISTS (Numbered or Bulleted in raw text)
        #    Regex for "1.", "1)", "•", "-", "*"
        if re.match(r'^(\d+[\.\)]|\*|-|•)\s+', line):
            # Clean the marker and treat as bullet
            content = re.sub(r'^(\d+[\.\)]|\*|-|•)\s+', '', line)
            structured_lines.append(f"- {content}")
            continue

        # 3. Detect DEFINITIONS (Pattern: "Term: Definition" or "Term - Definition")
        #    We look for a colon/hyphen appearing early in the line
        match_def = re.match(r'^([A-Z][a-zA-Z\s]+?)(:| - )\s*(.+)', line)
        if match_def:
            term, sep, definition = match_def.groups()
            if len(term.split()) <= 5: # prevent long sentences being treated as definitions
                structured_lines.append(f"- **{term.strip()}**: {definition.strip()}")
                continue
        
        # 4. Fallback: Analyze paragraph structure
        #    If it's a long text block with multiple sentences, break it down.
        #    Otherwise, treat as a single bullet point.
        
        # Split by period/question mark/exclamation followed by space
        # This regex looks for sentence endings while trying to avoid common abbreviations
        # (It's a heuristic, not perfect without NLP libraries)
        sentences = re.split(r'(?<=[.!?])\s+(?=[A-Z])', line)
        
        if len(sentences) > 1:
            for sent in sentences:
                sent = sent.strip()
                if sent:
                    structured_lines.append(f"- {sent}")
        else:
            structured_lines.append(f"- {line}")

    return "\n".join(structured_lines)
