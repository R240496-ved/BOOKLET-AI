import os
from openai import OpenAI

def generate_notes(prompt: str, mode: str, context: str = ""):
    """
    Generate notes using Groq API
    """
    api_key = os.getenv("LLM_API_KEY")
    
    if not api_key:
        return fallback_notes(prompt, mode)
        
    try:
        client = OpenAI(
            api_key=api_key,
            base_url="https://api.groq.com/openai/v1"
        )

        # Mode-specific system instruction
        if mode == "Exam":
            system_instruction = (
                "You are an academic assistant.\n"
                "Generate short exam-oriented notes.\n"
                "Use bullet points.\n"
                "Highlight important keywords in **bold**.\n"
                "Keep content concise for quick revision."
            )
        else:
            system_instruction = (
                "You are an academic assistant.\n"
                "Generate detailed and well-structured study notes.\n"
                "Explain clearly with examples.\n"
                "Use headings and bullet points."
            )

        # Format user content based on whether context exists
        if context:
            user_content = f"Context:\n{context}\n\nTask/Question:\n{prompt}"
        else:
            user_content = prompt

        response = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[
                {"role": "system", "content": system_instruction},
                {"role": "user", "content": user_content}
            ],
            temperature=0.7
        )

        return response.choices[0].message.content.strip()

    except Exception as e:
        print("❌ OPENAI API ERROR:", e)
        return fallback_notes(prompt, mode)


def fallback_notes(prompt: str, mode: str):
    """
    Fallback notes if API fails
    """
    return "I am operating in fallback mode because there was an issue connecting to the OpenAI API. Please check your API key!"