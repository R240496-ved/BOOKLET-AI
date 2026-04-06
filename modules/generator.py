"""
Generator Module
Handles the generation of structured academic content (Definitions, Key Points, Examples, Summary)
from either a single topic keyword or syllabus content.
Uses the same LLM config from .env as the rest of the app.
"""

import os
from openai import OpenAI


def _get_client():
    """Get OpenAI-compatible client using .env config."""
    api_key = os.getenv("LLM_API_KEY", "")
    base_url = os.getenv("LLM_API_BASE", "https://api.groq.com/openai/v1")
    model_name = os.getenv("LLM_API_MODEL", "llama-3.1-8b-instant")

    if not api_key:
        return None, model_name, "LLM_API_KEY is not set in .env"

    try:
        client = OpenAI(api_key=api_key, base_url=base_url)
        return client, model_name, None
    except Exception as e:
        return None, model_name, str(e)


def generate_academic_content(input_text: str, is_syllabus: bool = False, context: str = "") -> str:
    """
    Generate structured academic content from a topic or an entire syllabus.
    Includes Definition, Key Points, Examples, and Summary.
    """
    client, model_name, init_error = _get_client()

    if init_error:
        return f"⚠️ **LLM Connection Error:** `{init_error}`\n\n{_fallback_content(input_text, is_syllabus)}"

    try:
        if is_syllabus:
            system_prompt = (
                "You are an expert academic professor.\n"
                "The user will provide a syllabus course outline or topics. "
                "Your task is to generate comprehensive, structured lecture notes covering all listed topics.\n"
                "For EACH topic in the syllabus, strictly include:\n"
                "1. **Definition / Overview**\n"
                "2. **Key Points** (bullet points)\n"
                "3. **Examples / Case Studies**\n"
                "4. **Summary**\n\n"
                "Format your entire response strictly in clean Markdown with appropriate headings (#, ##) and bullet lists (-).\n"
                "CRUCIAL INSTRUCTION: You MUST aggressively highlight all important keywords, terms, and concepts in **bold** text."
            )
            user_msg = f"Syllabus / Outline:\n{input_text}"
        else:
            system_prompt = (
                "You are an expert academic tutor.\n"
                "The user will provide a specific topic or keyword. "
                "Your task is to generate natural, easy-to-read academic study notes for that topic.\n"
                "Do not use a rigid format, let the content flow naturally, but you MUST end your response with an '## Examples' section containing practical examples or case studies.\n"
                "Format using clean Markdown with bullet lists where appropriate.\n"
                "CRUCIAL INSTRUCTION: You MUST aggressively highlight all important keywords, terms, and concepts in **bold** text."
            )
            user_msg = f"Topic: {input_text}"

        if context:
            user_msg += f"\n\nContext to help (Reference this if useful):\n{context[:15000]}"

        response = client.chat.completions.create(
            model=model_name,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_msg}
            ],
            temperature=0.6
        )

        return response.choices[0].message.content.strip()

    except Exception as e:
        error_str = str(e)
        print(f"[Generator Module] API ERROR: {error_str}")
        return (
            f"⚠️ **API Error (Model: `{model_name}`):**\n\n"
            f"`{error_str}`\n\n"
            f"**Possible fixes:**\n"
            f"- Check if your API key is valid/active\n"
            f"- Try changing `LLM_API_MODEL` in `.env` (e.g. `grok-2`, `grok-3-mini`, `llama-3.1-8b-instant`)\n"
            f"- Verify `LLM_API_BASE` matches your provider\n\n"
            f"---\n\n"
            f"{_fallback_content(input_text, is_syllabus)}"
        )


def generate_step_by_step_solution(question: str, context: str = "") -> str:
    """
    Generates a step-by-step solution for a given problem/question.
    """
    client, model_name, init_error = _get_client()

    if init_error:
        return f"⚠️ **LLM Connection Error:** `{init_error}`"

    try:
        system_prompt = (
            "You are an expert academic solver and tutor. "
            "The user will provide a question, problem statement, or image-extracted question text.\n"
            "Your task is to provide a clear, logical, step-by-step solution to the problem.\n"
            "End with a final, clearly highlighted answer.\n"
            "Structure:\n"
            "## Problem Analysis\n"
            "## Step-by-Step Solution\n"
            "## Final Answer"
        )

        user_msg = f"Question:\n{question}"
        if context:
            user_msg += f"\n\nReference Material/Context:\n{context[:15000]}"

        response = client.chat.completions.create(
            model=model_name,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_msg}
            ],
            temperature=0.3
        )

        return response.choices[0].message.content.strip()

    except Exception as e:
        error_str = str(e)
        print(f"[Solve Module] API ERROR: {error_str}")
        return (
            f"⚠️ **Failed to solve — API Error (Model: `{model_name}`):**\n\n"
            f"`{error_str}`\n\n"
            f"**Try:** Change `LLM_API_MODEL` in `.env` to a supported model name."
        )


import json

def generate_mcq_quiz(context: str, num_questions: int = 5) -> list:
    """
    Generates a multiple-choice quiz based on the provided context.
    Returns a list of dictionaries with keys: 'question', 'options', 'answer'.
    """
    client, model_name, init_error = _get_client()

    if init_error:
        print(f"LLM Connection Error: {init_error}")
        return []

    try:
        system_prompt = (
            f"You are an expert quiz generator. Your task is to generate {num_questions} multiple-choice questions "
            "based exclusively on the provided context.\n"
            "CRITICAL RULES:\n"
            "1. NO REPETITION: Every question must test a unique concept or fact.\n"
            "2. Ensure proper topic coverage across the entire text.\n"
            "Format your output strictly as a JSON array of objects. Each object must have the following keys:\n"
            "- 'question': a string containing the question text.\n"
            "- 'options': an array of exactly 4 strings representing the possible choices.\n"
            "- 'answer': a string containing the exact text of the correct option.\n"
            "Do not output markdown formatting blocks like ```json, just the raw JSON array."
        )

        user_msg = f"Context:\n{context[:15000]}"

        response = client.chat.completions.create(
            model=model_name,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_msg}
            ],
            temperature=0.3
        )

        content = response.choices[0].message.content.strip()
        # Clean potential markdown wrapping
        if content.startswith("```json"):
            content = content[7:-3]
        elif content.startswith("```"):
            content = content[3:-3]
            
        return json.loads(content.strip())

    except Exception as e:
        print(f"[Generator Module] API ERROR for MCQ: {e}")
        return []

def _fallback_content(text: str, is_syllabus: bool) -> str:
    """Fallback generator when API is down or keys missing."""
    kind = "Syllabus Notes" if is_syllabus else "Topic Notes"
    return f"""
# {kind}: Offline Mode

## Definition
- (Fallback Content) The API is unavailable to generate full definitions for: *{text[:200]}*

## Key Points
- Offline mode engaged.
- Check your `.env` file for correct `LLM_API_KEY`, `LLM_API_BASE`, and `LLM_API_MODEL`.

## Examples
- N/A in offline mode.

## Summary
Cannot generate complete academic notes without a working LLM backend.
"""
