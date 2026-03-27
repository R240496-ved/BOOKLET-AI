# import os
# from openai import OpenAI

# def generate_notes(prompt: str, mode: str, context: str = ""):
#     """
#     Generate notes using Groq API
#     """
#     api_key = os.getenv("LLM_API_KEY")
    
#     if not api_key:
#         return fallback_notes(prompt, mode)
        
#     try:
#         client = OpenAI(
#             api_key=api_key,
#             base_url="https://api.groq.com/openai/v1"
#         )

#         # Mode-specific system instruction
#         if mode == "Exam":
#             system_instruction = (
#                 "You are an academic assistant.\n"
#                 "Generate short exam-oriented notes.\n"
#                 "Use bullet points.\n"
#                 "Highlight important keywords in **bold**.\n"
#                 "Keep content concise for quick revision."
#             )
#         else:
#             system_instruction = (
#                 "You are an academic assistant.\n"
#                 "Generate detailed and well-structured study notes.\n"
#                 "Explain clearly with examples.\n"
#                 "Use headings and bullet points."
#             )

#         # Format user content based on whether context exists
#         if context:
#             user_content = f"Context:\n{context}\n\nTask/Question:\n{prompt}"
#         else:
#             user_content = prompt

#         response = client.chat.completions.create(
#             model="llama-3.1-8b-instant",
#             messages=[
#                 {"role": "system", "content": system_instruction},
#                 {"role": "user", "content": user_content}
#             ],
#             temperature=0.7
#         )

#         return response.choices[0].message.content.strip()

#     except Exception as e:
#         print("❌ OPENAI API ERROR:", e)
#         return fallback_notes(prompt, mode)


# def fallback_notes(prompt: str, mode: str):
#     """
#     Fallback notes if API fails
#     """
#     return "I am operating in fallback mode because there was an issue connecting to the OpenAI API. Please check your API key!"
import os
from openai import OpenAI


def generate_notes(prompt: str, mode: str = "Study", context: str = "") -> str:
    """
    Generate study notes using Groq/OpenAI compatible API.

    mode:
        "Exam"  -> concise revision notes
        "Study" -> detailed learning notes
    """

    api_key = os.getenv("LLM_API_KEY")

    if not api_key:
        return fallback_notes(prompt, mode)

    try:
        client = OpenAI(
            api_key=api_key,
            base_url="https://api.groq.com/openai/v1"
        )

        # Limit context to avoid token overflow
        if context:
            context = context[:15000]

        # Mode-based instructions
        if mode == "Exam":
            system_prompt = (
                "You are an academic revision assistant.\n"
                "Generate concise exam-ready notes.\n"
                "Rules:\n"
                "- Use bullet points\n"
                "- Highlight key terms using **bold**\n"
                "- Keep sentences short\n"
                "- Focus on definitions, formulas, and key facts"
            )

        else:
            system_prompt = (
                "You are a study assistant helping students understand topics.\n"
                "Generate structured study notes.\n"
                "Rules:\n"
                "- Use headings and bullet points\n"
                "- Explain concepts clearly\n"
                "- Give short examples where useful\n"
                "- Highlight important terms using **bold**"
            )

        # Construct user message
        if context:
            user_prompt = f"""
Document Context:
{context}

Student Request:
{prompt}
"""
        else:
            user_prompt = prompt

        response = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.6
        )

        return response.choices[0].message.content.strip()

    except Exception as e:
        print("API ERROR:", e)
        return fallback_notes(prompt, mode)


def fallback_notes(prompt: str, mode: str) -> str:
    """
    Basic fallback notes generator when API is unavailable.
    """

    if mode == "Exam":
        return f"""
### Quick Revision Notes

- **Topic:** {prompt}
- Review the key definitions related to this topic.
- Identify important formulas and concepts.
- Focus on understanding the core idea.

(API unavailable — fallback mode)
"""

    else:
        return f"""
## Study Notes

Topic: **{prompt}**

- This section normally generates AI-powered explanations.
- Currently operating in fallback mode.
- Please check your API key or internet connection.

(API unavailable)
"""