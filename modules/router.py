"""
Router Module
Analyzes the user's text query to determine the processing mode:
- GEN: Notes, lecture generation
- SOLVE: Math, step-by-step problems (especially from images)
- RAG: Standard document question answering
"""

import re

def route_query(query: str, from_image: bool = False) -> str:
    """
    Intelligently route the query to one of three modes: 'GEN', 'SOLVE', or 'RAG'.
    """
    query_lower = query.lower()

    # 1. Check for Generation keywords
    gen_keywords = ["generate notes", "create notes", "make notes", "summarize", "summary", "create a ppt", "generate a ppt", "make a ppt", "create a pdf", "generate a pdf", "make a pdf", "create booklet", "generate booklet"]
    for kw in gen_keywords:
        if kw in query_lower:
            return "GEN"

    # 2. Check for Solving step-by-step
    # If it comes from an image and has a question mark or solving keywords
    solve_keywords = ["+", "=", "-", "*", "/", "equation", "calculate", "evaluate", "prove that"]
    is_question = "?" in query

    if from_image:
        if any(kw in query_lower for kw in solve_keywords):
            return "SOLVE"
            
    if any(kw in query_lower for kw in solve_keywords):
        return "SOLVE"

    # 3. Default to RAG (Chatbot Q&A based on document)
    return "RAG"
