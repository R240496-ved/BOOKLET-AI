
import os
import dotenv
from openai import OpenAI

# Force reload
dotenv.load_dotenv(override=True)

api_key = os.getenv("LLM_API_KEY")

print(f"DEBUG: Loaded API Key length: {len(api_key) if api_key else 'None'}")
print(f"DEBUG: API Key starts with: {api_key[:10] if api_key else 'None'}...")

if not api_key:
    print("❌ ERROR: No API Key found in environment.")
else:
    try:
        client = OpenAI(
            api_key=api_key,
            base_url="https://api.groq.com/openai/v1"
        )
        client.models.list()
        print("✅ SUCCESS: API Key is valid and can connect to Groq.")
    except Exception as e:
        print(f"❌ ERROR: API Key failed validation.\n{e}")
