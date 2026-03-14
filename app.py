
import streamlit as st
import os
import dotenv

# Load environment variables
dotenv.load_dotenv(override=True)

from modules.member2_input_extraction import extract_text
from modules.member1_ai_logic import build_structure, call_openai_api
from modules.member3_clean_simplify import clean_and_simplify
from modules.member4_booklet_generator import generate_booklet
from modules.member5_notes_generator import generate_notes

# ---------- Streamlit Page Setup ----------
st.set_page_config(page_title="BOOKLET AI", layout="centered")

# ---------- Session State Initialization ----------
if "raw_text" not in st.session_state:
    st.session_state.raw_text = ""
if "clean_text" not in st.session_state:
    st.session_state.clean_text = ""
if "structured_text" not in st.session_state:
    st.session_state.structured_text = ""
if "messages" not in st.session_state:
    st.session_state.messages = []

# ---------- Sidebar Navigation ----------
st.sidebar.title("Navigation")
page = st.sidebar.radio(
    "Go to",
    ["📘 Booklet Generator", "💬 Chatbot"]
)

# ==========================================
# PAGE 1: BOOKLET GENERATOR
# ==========================================
if page == "📘 Booklet Generator":
    st.title("📘 Booklet Generator")
    st.write("Convert PDF / PPT / TXT into study booklets")
    
    # Ensure folders exist
    os.makedirs("data/input", exist_ok=True)
    os.makedirs("data/output", exist_ok=True)

    # Input Selection
    input_method = st.radio("Choose Input Method:", ["File Upload", "Paste Text"], horizontal=True)

    raw_text = None

    if input_method == "File Upload":
        # File Upload
        uploaded_file = st.file_uploader(
            "Upload your file",
            type=["pdf", "pptx", "txt"]
        )

        if uploaded_file is not None:
            # Save file
            file_path = os.path.join("data", "input", uploaded_file.name)
            with open(file_path, "wb") as f:
                f.write(uploaded_file.getbuffer())

            if st.button("Process File"):
                with st.spinner("Extracting..."):
                    raw_text = extract_text(file_path)

    elif input_method == "Paste Text":
        # Direct Text Input
        manual_text = st.text_area("Paste your text here:", height=200)
        
        if manual_text and st.button("Process Text"):
            raw_text = manual_text

    if raw_text is not None:
        with st.spinner("Processing Content..."):
            # 1. Store Raw
            st.session_state.raw_text = raw_text
            # 2. Cleaning
            clean = clean_and_simplify(raw_text)
            st.session_state.clean_text = clean
            
            # 3. Structuring (Rule-based)
            cols = build_structure(clean) # Returns markdown string
            st.session_state.structured_text = cols
            
            st.success("File processed! Review the output below.")

    # Verification & Output UI
    if st.session_state.structured_text:
        st.divider()
        st.header("� Review & Download")
        
        # Tabs for different stages
        tab1, tab2, tab3 = st.tabs(["Raw Extraction", "Cleaned Text", "Final Structure"])
        
        with tab1:
            st.text_area("Raw Output", st.session_state.raw_text, height=200)
        
        with tab2:
            st.text_area("Cleaned Output", st.session_state.clean_text, height=200)
            
        with tab3:
            st.markdown(st.session_state.structured_text)
            st.info("This is how the content will be structured in the PDF.")

        # PDF Generation Button
        st.write("---")
        if st.button("📄 Generate PDF Booklet"):
            with st.spinner("Generating PDF..."):
                success = generate_booklet(st.session_state.structured_text)
                
                if success:
                    st.success("PDF Generated Successfully!")
                    
                    pdf_path = "data/output/booklet.pdf"
                    if os.path.exists(pdf_path):
                        with open(pdf_path, "rb") as f:
                            st.download_button(
                                label="📥 Download Booklet PDF",
                                data=f,
                                file_name="Booklet_AI_Notes.pdf",
                                mime="application/pdf"
                            )
                else:
                    st.error("Failed to generate PDF. Check structure.")

# ==========================================
# PAGE 2: CHATBOT
# ==========================================
elif page == "💬 Chatbot":
    st.title("📝 Notes Generator")
    st.caption("Generate notes in Exam Mode or Normal Mode")

    # Mode selection
    mode = st.radio(
        "Select Notes Mode:",
        ["Normal", "Exam"],
        horizontal=True
    )

    # Display chat history
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    # Chat Input
    prompt = st.chat_input("Enter topic or question...")



    if prompt:
        # Add user message
        st.session_state.messages.append(
            {"role": "user", "content": prompt}
        )

        with st.chat_message("user"):
            st.markdown(prompt)

        # Generate notes using Member-5 (DeepSeek or any API inside it)
        with st.spinner("Generating Answer to your query..."):

            context = st.session_state.clean_text if "clean_text" in st.session_state else ""

            response_text = generate_notes(
                prompt=prompt,
                mode=mode,
                context=context
            )

            # Add assistant message
            st.session_state.messages.append(
                {"role": "assistant", "content": response_text}
            )

            with st.chat_message("assistant"):
                st.markdown(response_text)