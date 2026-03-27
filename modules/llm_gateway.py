"""
LLM Gateway - Hybrid LLM Abstraction Layer
Supports:
  - API Mode: Groq / OpenAI-compatible endpoints
  - Local Mode: Ollama (Mistral or any local model)

Controls:
  - Set LLM_MODE=api or LLM_MODE=local in .env
  - If API key missing and local Ollama unreachable → rule-based fallback
"""

import os

# ─────────────────────────────────────────────
# CONFIG
# ─────────────────────────────────────────────

LLM_MODE = os.getenv("LLM_MODE", "api").lower()          # "api" or "local"
LLM_API_KEY = os.getenv("LLM_API_KEY", "")
LLM_API_BASE = os.getenv("LLM_API_BASE", "https://api.groq.com/openai/v1")
LLM_API_MODEL = os.getenv("LLM_API_MODEL", "llama-3.1-8b-instant")
LLM_LOCAL_MODEL = os.getenv("LLM_LOCAL_MODEL", "mistral")
LLM_LOCAL_BASE = os.getenv("LLM_LOCAL_BASE", "http://localhost:11434")


# ─────────────────────────────────────────────
# STRICT RAG PROMPT BUILDER
# ─────────────────────────────────────────────

def build_rag_prompt(user_query: str, context_chunks: list[str], mode: str = "Study") -> tuple[str, str]:
    """
    Build a strict document-only RAG prompt.
    Returns (system_message, user_message).
    """
    context_text = "\n\n---\n\n".join(context_chunks) if context_chunks else ""

    if mode == "Exam":
        style = (
            "Generate concise exam-ready bullet points. "
            "Highlight key terms in **bold**. Keep it short."
        )
    else:
        style = (
            "Generate clear, structured study notes with headings and bullet points. "
            "Explain concepts in simple language."
        )

    system_msg = (
        "You are a strict document-based study assistant.\n"
        "RULES:\n"
        "1. Answer ONLY using the provided document context below.\n"
        "2. If the answer is NOT in the document, respond EXACTLY: 'Not in document.'\n"
        "3. Do NOT use any general knowledge or outside information.\n"
        f"4. {style}\n\n"
        f"DOCUMENT CONTEXT:\n{context_text}"
    )

    user_msg = user_query
    return system_msg, user_msg


def build_general_prompt(user_query: str, mode: str = "Study") -> tuple[str, str]:
    """
    Build a general study notes prompt (no document context).
    """
    if mode == "Exam":
        style = "Concise exam notes with **bold** keywords and bullet points."
    else:
        style = "Detailed study notes with headings, bullets, and examples."

    system_msg = (
        f"You are a helpful academic study assistant. {style}"
    )
    return system_msg, user_query


# ─────────────────────────────────────────────
# API MODE (Groq / OpenAI-compatible)
# ─────────────────────────────────────────────

def _call_api(system_msg: str, user_msg: str) -> str:
    """Call API-based LLM (Groq / OpenAI)."""
    if not LLM_API_KEY:
        raise ValueError("LLM_API_KEY not set in .env")

    from openai import OpenAI

    client = OpenAI(api_key=LLM_API_KEY, base_url=LLM_API_BASE)

    response = client.chat.completions.create(
        model=LLM_API_MODEL,
        messages=[
            {"role": "system", "content": system_msg},
            {"role": "user", "content": user_msg},
        ],
        temperature=0.5,
    )
    return response.choices[0].message.content.strip()


# ─────────────────────────────────────────────
# LOCAL MODE (Ollama)
# ─────────────────────────────────────────────

def _call_ollama(system_msg: str, user_msg: str) -> str:
    """Call local Ollama instance."""
    import requests

    payload = {
        "model": LLM_LOCAL_MODEL,
        "messages": [
            {"role": "system", "content": system_msg},
            {"role": "user", "content": user_msg},
        ],
        "stream": False,
    }

    resp = requests.post(
        f"{LLM_LOCAL_BASE}/api/chat",
        json=payload,
        timeout=120,
    )
    resp.raise_for_status()
    return resp.json()["message"]["content"].strip()


# ─────────────────────────────────────────────
# FALLBACK (Rule-based)
# ─────────────────────────────────────────────

def _rule_based_fallback(user_msg: str, context_chunks: list[str]) -> str:
    """
    When both API and local LLM are unavailable.
    Returns the top retrieved context as formatted notes.
    """
    if context_chunks:
        content = "\n\n".join(context_chunks[:3])
        return (
            f"## Notes (Offline Fallback)\n\n"
            f"*LLM unavailable — showing most relevant document sections:*\n\n"
            f"{content}"
        )
    return (
        "**LLM unavailable and no document context found.**\n\n"
        "Please upload a document first, or check your API key / Ollama connection."
    )


# ─────────────────────────────────────────────
# MAIN ENTRY POINT
# ─────────────────────────────────────────────

def generate_answer(
    user_query: str,
    context_chunks: list[str] = None,
    mode: str = "Study",
    strict_rag: bool = True,
) -> str:
    """
    Unified LLM call. Switches between API, Local, and Fallback.

    Args:
        user_query: The user's question or topic.
        context_chunks: Retrieved chunks from RAG (empty list if no document).
        mode: 'Study' or 'Exam'
        strict_rag: If True, enforce document-only answering.

    Returns:
        Response string (Markdown).
    """
    context_chunks = context_chunks or []

    # Build prompts
    if strict_rag and context_chunks:
        system_msg, user_msg = build_rag_prompt(user_query, context_chunks, mode)
    else:
        system_msg, user_msg = build_general_prompt(user_query, mode)

    # Try primary mode
    try:
        if LLM_MODE == "local":
            return _call_ollama(system_msg, user_msg)
        else:
            return _call_api(system_msg, user_msg)

    except Exception as primary_err:
        print(f"[LLM Gateway] Primary mode '{LLM_MODE}' failed: {primary_err}")

    # Try fallback mode
    try:
        if LLM_MODE == "local":
            # If local failed, try API
            return _call_api(system_msg, user_msg)
        else:
            # If API failed, try local Ollama
            return _call_ollama(system_msg, user_msg)

    except Exception as fallback_err:
        print(f"[LLM Gateway] Fallback mode also failed: {fallback_err}")

    # Last resort: rule-based
    return _rule_based_fallback(user_query, context_chunks)
