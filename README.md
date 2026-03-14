BOOKLET AI – Study Material & Handbooks in Minutes

This project converts PDF, PPT, or text notes into structured study booklets.

Each module is owned by one team member.

## Setup Instructions

1. Clone the repository:
   ```
   git clone <your-repo-url>
   cd Updated_BOOKLET_AI
   ```

2. Install dependencies:
   ```
   pip install -r requirements.txt
   ```

3. Set up environment variables:
   - Copy `.env.example` to `.env`:
     ```
     cp .env.example .env
     ```
   - Edit `.env` and add your Groq API key:
     ```
     LLM_API_KEY=your_actual_groq_api_key_here
     ```
     Get your API key from [Groq Console](https://console.groq.com/).

4. Run the app:
   ```
   streamlit run app.py
   ```

## Notes
- The `.env` file is ignored by Git for security. Never commit it.
- For deployment, use platform-specific secrets (e.g., Streamlit Cloud secrets).