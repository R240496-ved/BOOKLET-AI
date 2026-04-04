"""
BOOKLET AI — Main Application
Unified pipeline: upload once → use everywhere.
Pages: Upload | Booklet Generator | RAG Chatbot | PPT Generator
"""

import streamlit as st
import os
import dotenv

# Load env vars
dotenv.load_dotenv(override=True)

# ─────────────────────────────────────────────
# PAGE CONFIG
# ─────────────────────────────────────────────

st.set_page_config(
    page_title="BOOKLET AI",
    page_icon="📘",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─────────────────────────────────────────────
# CUSTOM CSS
# ─────────────────────────────────────────────

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

html, body, [class*="css"] {
    font-family: 'Inter', sans-serif;
}

/* Sidebar */
[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #1A1A2E 0%, #16213E 100%);
    border-right: 2px solid #E94F37;
}
[data-testid="stSidebar"] * {
    color: #F5F5F5 !important;
}
[data-testid="stSidebar"] .stRadio label {
    font-size: 15px;
    padding: 6px 4px;
}

/* Main area dark */
.main { background-color: #0F1726; color: #F0F0F0; }

/* Cards */
.card {
    background: linear-gradient(135deg, #16213E 0%, #1A1A2E 100%);
    border: 1px solid #2C3E6B;
    border-radius: 12px;
    padding: 24px;
    margin-bottom: 16px;
}
.card-accent { border-left: 4px solid #E94F37; }

/* Status badges */
.badge-ok { color: #2ECC71; font-weight: 600; }
.badge-warn { color: #F39C12; font-weight: 600; }
.badge-err { color: #E74C3C; font-weight: 600; }

/* Big title */
.hero-title {
    font-size: 2.8rem;
    font-weight: 700;
    background: linear-gradient(90deg, #E94F37, #F5A623);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    margin-bottom: 4px;
}
.hero-subtitle {
    color: #A0A0B8;
    font-size: 1.05rem;
    margin-bottom: 24px;
}

/* Step indicators */
.step {
    display: inline-flex;
    align-items: center;
    gap: 8px;
    background: #1A1A2E;
    border: 1px solid #2C3E6B;
    border-radius: 8px;
    padding: 8px 16px;
    margin: 4px;
    font-size: 13px;
    color: #A0A0B8;
}
.step.done { border-color: #2ECC71; color: #2ECC71; }

/* Image gallery */
.img-grid { display: flex; flex-wrap: wrap; gap: 12px; margin-top: 12px; }
.img-thumb { border-radius: 8px; border: 2px solid #2C3E6B; max-height: 180px; }
</style>
""", unsafe_allow_html=True)


# ─────────────────────────────────────────────
# SESSION STATE INIT
# ─────────────────────────────────────────────

defaults = {
    "pipeline_done": False,    # Has the file been processed?
    "raw_text": "",
    "clean_text": "",
    "structured_text": "",
    "images": [],              # List of image metadata dicts
    "rag_store": None,         # {"chunks": [], "embeddings": ..., "index": ...}
    "messages": [],
    "uploaded_filename": "",
    "doc_title": "Study Booklet",
    "context_text": "",        # Shared context for RAG and MCQ from both Upload and OCR
    "ocr_text": "",            # Extracted OCR text
    "router_mode": "RAG",      # Current mode
    "mcq_quiz": [],            # To store generated quiz questions
    "user_answers": {},        # To store user quiz answers
    "quiz_submitted": False,   # Whether quiz was submitted
    "ocr_generated_notes": "", # Store generated notes from OCR for download features
}

for k, v in defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v

# Legacy rollback to flat list
if "chats" in st.session_state and isinstance(st.session_state.chats, dict):
    # Try to rescue messages if any exist
    all_msgs = []
    for chat_data in st.session_state.chats.values():
        if isinstance(chat_data, dict) and "messages" in chat_data:
            all_msgs.extend(chat_data["messages"])
        elif isinstance(chat_data, list):
            all_msgs.extend(chat_data)
    if all_msgs:
        st.session_state.messages = all_msgs
    del st.session_state.chats


# ─────────────────────────────────────────────
# SIDEBAR NAVIGATION
# ─────────────────────────────────────────────

with st.sidebar:
    st.markdown("## 📘 BOOKLET AI")
    st.markdown("---")

    page = st.radio(
        "Navigation",
        [
            "📤 Upload & Process",
            "💬 Chat & Solve",
            "✨ Generate (GEN)",
            "📸 OCR Upload",
            "📘 Booklet Generator",
            "📊 PPT Generator"
        ],
        label_visibility="collapsed",
    )

    st.markdown("---")

    # Pipeline status
    st.markdown("### Pipeline Status")
    if st.session_state.pipeline_done:
        fname = st.session_state.uploaded_filename
        n_img = len(st.session_state.images)
        n_chunks = len(st.session_state.rag_store["chunks"]) if st.session_state.rag_store else 0
        st.markdown(f"""
        <div class="step done">✅ File: {fname}</div><br>
        <div class="step done">✅ {n_chunks} chunks indexed</div><br>
        <div class="step done">✅ {n_img} image(s) extracted</div>
        """, unsafe_allow_html=True)
    else:
        st.markdown('<div class="step">⬆️ No file processed yet</div>', unsafe_allow_html=True)

    st.markdown("---")



    # LLM Mode
    llm_mode = os.getenv("LLM_MODE", "api").upper()
    llm_model = os.getenv("LLM_API_MODEL", "llama-3.1-8b-instant")
    st.markdown(f"**LLM Mode:** `{llm_mode}`")
    st.markdown(f"**Model:** `{llm_model}`")

def render_inline_content(text):
    """Helper to render text + inline image markers in Streamlit."""
    import re
    # Split the text by exactly matching the ![IMAGE:xxx] markdown pattern
    parts = re.split(r'(!\[IMAGE:.*?\])', text)
    
    for part in parts:
        if not part:
            continue
            
        if part.startswith("![IMAGE:") and part.endswith("]"):
            img_path = part[8:-1].strip()
            if os.path.exists(img_path):
                st.image(img_path, use_container_width=True)
            else:
                st.markdown(f"*(Image not found: {img_path})*")
        else:
            if part.strip():
                st.markdown(part)


# ─────────────────────────────────────────────
# LAZY IMPORTS (avoid import errors on startup)
# ─────────────────────────────────────────────

def load_modules():
    from modules.member2_input_extraction import extract
    from modules.member3_clean_simplify import clean_and_simplify
    from modules.member1_ai_logic import build_structure
    from modules.member4_booklet_generator import generate_booklet
    from modules.ppt_generator import generate_ppt
    from modules.rag_engine import build_rag_store, retrieve_top_k
    from modules.llm_gateway import generate_answer
    
    # New modules
    from modules.ocr_module import extract_text_from_image
    from modules.router import route_query
    from modules.generator import generate_academic_content, generate_step_by_step_solution, generate_mcq_quiz

    return {
        "extract": extract,
        "clean": clean_and_simplify,
        "structure": build_structure,
        "gen_booklet": generate_booklet,
        "gen_ppt": generate_ppt,
        "build_rag": build_rag_store,
        "retrieve": retrieve_top_k,
        "llm": generate_answer,
        "ocr_ext": extract_text_from_image,
        "route": route_query,
        "gen_academic": generate_academic_content,
        "gen_solve": generate_step_by_step_solution,
        "gen_mcq": generate_mcq_quiz,
    }

M = load_modules()


# ══════════════════════════════════════════════
# PAGE: UPLOAD & PROCESS
# ══════════════════════════════════════════════

if page == "📤 Upload & Process":
    st.markdown('<div class="hero-title">BOOKLET AI</div>', unsafe_allow_html=True)
    st.markdown('<div class="hero-subtitle">Upload your study material once. Get Booklet • Chatbot • Slides.</div>', unsafe_allow_html=True)

    col1, col2 = st.columns([1.6, 1])

    with col1:
        st.markdown('<div class="card card-accent">', unsafe_allow_html=True)
        uploaded_file = st.file_uploader(
            "Upload your document",
            type=["pdf", "pptx", "txt", "png", "jpg", "jpeg"],
            help="Supports PDF, PPTX, TXT, and Images (handwritten notes via OCR).",
        )

        input_method = st.radio(
            "Or paste text directly:",
            ["File Upload", "Paste Text"],
            horizontal=True,
        )

        pasted_text = ""
        if input_method == "Paste Text":
            pasted_text = st.text_area("Paste your content here:", height=200)

        doc_title = st.text_input("Document title (used in Booklet & PPT):", value="Study Booklet")

        process_btn = st.button("🚀 Process Document", type="primary", use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)

    with col2:
        st.markdown("### How it works")
        st.markdown("""
        <div class="card">
        <ol style="color:#A0A0B8; line-height:2;">
          <li>📤 <b>Upload once</b></li>
          <li>🔍 <b>Text + Image extraction</b></li>
          <li>🧹 <b>Cleaning & Structuring</b></li>
          <li>🧠 <b>RAG Index built (FAISS)</b></li>
          <li>📘 <b>Generate Booklet PDF</b></li>
          <li>🖼️ <b>Generate PPT Slides</b></li>
          <li>💬 <b>Ask the AI Chatbot</b></li>
        </ol>
        </div>
        """, unsafe_allow_html=True)

    # ── PROCESS ──
    if process_btn:
        raw_text = None
        images = []
        file_name = "pasted_text"

        if input_method == "File Upload" and uploaded_file:
            os.makedirs("data/input", exist_ok=True)
            os.makedirs("data/extracted_images", exist_ok=True)

            file_path = os.path.join("data", "input", uploaded_file.name)
            with open(file_path, "wb") as f:
                f.write(uploaded_file.getbuffer())

            file_name = uploaded_file.name

            with st.spinner("📂 Extracting text and images..."):
                result = M["extract"](file_path, image_output_dir="data/extracted_images")
                raw_text = result["text"]
                images = result["images"]

        elif input_method == "Paste Text" and pasted_text.strip():
            raw_text = pasted_text.strip()
            images = []

        if not raw_text or len(raw_text.strip()) < 5:
            st.error("❌ No readable text found. Please upload a clearer document or image.")
            st.stop()

        with st.spinner("🧹 Cleaning text..."):
            clean = M["clean"](raw_text)
            if not clean:
                st.error("❌ Text cleaning resulted in empty data. Parsing stopped.")
                st.stop()

        with st.spinner("📐 Structuring content..."):
            structured = M["structure"](clean)
            if not structured:
                st.error("❌ Structuring failed. Parsing stopped.")
                st.stop()

        with st.spinner("🧠 Building RAG index (embedding chunks)..."):
            rag_store = M["build_rag"](clean)
            if not rag_store or not rag_store.get("chunks"):
                st.error("❌ RAG Indexing failed. Document might be too small to extract data.")
                st.stop()

        # Persist to session state
        st.session_state.pipeline_done = True
        st.session_state.context_text = clean
        st.session_state.raw_text = raw_text
        st.session_state.clean_text = clean
        st.session_state.structured_text = structured
        st.session_state.images = images
        st.session_state.rag_store = rag_store
        st.session_state.uploaded_filename = file_name
        st.session_state.doc_title = doc_title

        st.success(f"✅ Processed **{file_name}** — {len(images)} image(s) extracted, {len(rag_store['chunks'])} chunks indexed.")

        with st.expander("📄 Content Preview (Text + Inline Images)", expanded=True):
            render_inline_content(st.session_state.structured_text)


# ══════════════════════════════════════════════
# PAGE: BOOKLET GENERATOR
# ══════════════════════════════════════════════

elif page == "📘 Booklet Generator":
    st.markdown("## 📘 Booklet Generator")

    if not st.session_state.pipeline_done:
        st.warning("⚠️ No document processed yet. Go to **Upload & Process** first.")
        st.stop()

    tab1, tab2, tab3 = st.tabs(["📄 Raw Extraction", "🧹 Cleaned Text", "📐 Structured Markdown"])

    with tab1:
        st.text_area("Raw Text", st.session_state.raw_text, height=280)

    with tab2:
        st.text_area("Cleaned Text", st.session_state.clean_text, height=280)

    with tab3:
        render_inline_content(st.session_state.structured_text)
        st.info("This is the structured outline with inline images used for generation.")

    st.divider()

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("### 📄 PDF Booklet")
        st.caption("Optimized for clean study notes (Text-only).")

        if st.button("Generate PDF Booklet", type="primary", use_container_width=True):
            with st.spinner("Generating PDF..."):
                success = M["gen_booklet"](
                    st.session_state.structured_text,
                    images=[], # Images removed for PDF
                    title=st.session_state.doc_title,
                    output_path="data/output/booklet.pdf",
                )

            if success and os.path.exists("data/output/booklet.pdf"):
                st.success("PDF generated!")
                with open("data/output/booklet.pdf", "rb") as f:
                    st.download_button(
                        "📥 Download PDF Booklet",
                        data=f,
                        file_name=f"{st.session_state.doc_title}.pdf",
                        mime="application/pdf",
                        use_container_width=True,
                    )
            else:
                st.error("PDF generation failed. Check console logs.")


# ══════════════════════════════════════════════
# PAGE: RAG CHATBOT
# ══════════════════════════════════════════════

elif page == "💬 Chat & Solve":
    st.markdown("## 💬 Chat & Solve")
    st.caption("Intelligent chatbot: Ask a question (RAG), generate notes (GEN), or solve problems (SOLVE) automatically.")

    if not st.session_state.pipeline_done:
        st.warning("⚠️ No document processed yet. Go to **Upload & Process** first, or use generic problem solving.")

    col_chat, col_ctx = st.columns([2.2, 1])

    with col_chat:
        tab_chat, tab_mcq = st.tabs(["💬 Regular Chat", "🎯 MCQ Quiz"])
        
        with tab_chat:
            mode = st.radio("Notes style (for RAG):", ["Study", "Exam"], horizontal=True)

            for msg in st.session_state.messages:
                with st.chat_message(msg["role"]):
                    render_inline_content(msg["content"])

            prompt = st.chat_input("Ask a question, say 'generate notes on...', or 'solve...'")



            if prompt:
                st.session_state.messages.append({"role": "user", "content": prompt})
                with st.chat_message("user"):
                    render_inline_content(prompt)

                # Route the prompt
                route = M["route"](prompt, from_image=False)
                
                with st.spinner(f"Intelligent Routing: **{route}** Mode - processing..."):
                    if route == "GEN":
                        answer = M["gen_academic"](prompt, is_syllabus=False, context=st.session_state.context_text)
                    elif route == "SOLVE":
                        answer = M["gen_solve"](prompt, context=st.session_state.context_text)
                    else:
                        # RAG Mode
                        rag = st.session_state.rag_store
                        relevant_chunks = []
                        if rag and rag.get("index") is not None:
                            relevant_chunks = M["retrieve"](prompt, rag["chunks"], rag["index"], k=5)
                        answer = M["llm"](user_query=prompt, context_chunks=relevant_chunks, mode=mode, strict_rag=True)

                st.session_state.messages.append({"role": "assistant", "content": answer})
                with st.chat_message("assistant"):
                    render_inline_content(answer)
                    
        with tab_mcq:
            st.markdown("### 🎯 Generate MCQ Quiz")
            st.caption("Test your understanding based on the uploaded document.")
            
            # Determine dynamic question count based on document length
            text_length = len(st.session_state.context_text.split()) if st.session_state.context_text else 0
            if text_length > 0:
                if text_length < 500:
                    num_questions = 6
                elif text_length < 1500:
                    num_questions = 7
                else:
                    num_questions = 9
                btn_text = f"Generate {num_questions}-Question Quiz"
            else:
                num_questions = 5
                btn_text = "Generate Quiz"
            
            if st.button(btn_text):
                if not st.session_state.context_text:
                    st.error("No content available for quiz generation")
                else:
                    with st.spinner(f"Generating a {num_questions}-Question Quiz using AI..."):
                        quiz = M["gen_mcq"](st.session_state.context_text, num_questions)
                        if quiz:
                            st.session_state.mcq_quiz = quiz
                            st.session_state.user_answers = {}
                            st.session_state.quiz_submitted = False
                        else:
                            st.error("Failed to generate quiz. Verify LLM connection.")
                            
            if st.session_state.mcq_quiz:
                st.markdown("---")
                quiz = st.session_state.mcq_quiz
                
                for i, q in enumerate(quiz):
                    st.markdown(f"**Q{i+1}: {q.get('question', '')}**")
                    options = q.get('options', [])
                    ans = st.radio("Options:", options, key=f"q_{i}", index=None, label_visibility="collapsed")
                    if ans:
                        st.session_state.user_answers[i] = ans
                
                st.markdown("---")
                if st.button("Submit Quiz", type="primary"):
                    st.session_state.quiz_submitted = True
                    
                if st.session_state.quiz_submitted:
                    score = 0
                    st.markdown("## 📊 Quiz Results")
                    for i, q in enumerate(quiz):
                        user_ans = st.session_state.user_answers.get(i)
                        correct_ans = q.get('answer', '')
                        if user_ans and user_ans.strip().lower() == correct_ans.strip().lower():
                            score += 1
                            st.success(f"**Q{i+1}: Correct!** ✅")
                        else:
                            st.error(f"**Q{i+1}: Incorrect ❌**\n\nYour answer: {user_ans}\n\nCorrect answer: {correct_ans}")
                            
                    st.markdown(f"### 🎉 Final Score: {score} / {len(quiz)}")

    with col_ctx:
        st.markdown("### 📚 Details")
        st.caption("Context used for your last query.")

        if st.session_state.messages:
            last_user = next(
                (m["content"] for m in reversed(st.session_state.messages) if m["role"] == "user"),
                None,
            )
            
            if last_user:
                route = M["route"](last_user, from_image=False)
                st.info(f"Last Mode: **{route}**")
                
                if route == "RAG":
                    rag = st.session_state.rag_store
                    if rag and rag.get("index") is not None:
                        ctx_chunks = M["retrieve"](last_user, rag["chunks"], rag["index"], k=3)
                        for i, chunk in enumerate(ctx_chunks):
                            with st.expander(f"Chunk {i + 1}"):
                                st.write(chunk[:500] + ("..." if len(chunk) > 500 else ""))
                elif route == "GEN":
                    st.success("Generated structured academic notes across definitions, examples, and summaries.")
                elif route == "SOLVE":
                    st.success("Generated step-by-step mathematical/analytical solution.")

    # Clear chat
    if st.session_state.messages:
        if st.button("🗑️ Clear Chat"):
            st.session_state.messages = []
            st.rerun()

# ══════════════════════════════════════════════
# PAGE: GENERATE (GEN)
# ══════════════════════════════════════════════

elif page == "✨ Generate (GEN)":
    st.markdown("## ✨ Generate Academic Content")
    st.caption("Generate natural, flowing study notes from a topic or an entire syllabus. Always includes practical Examples.")

    is_syllabus = st.checkbox("This is a syllabus/outline with multiple topics", value=False)
    topic_input = st.text_area("Enter Topic or Syllabus:")
    
    # Use a form or standard layout to generate content
    if st.button("Generate Notes", type="primary"):
        if topic_input.strip():
            with st.spinner("Generating academic notes..."):
                generated_content = M["gen_academic"](topic_input, is_syllabus=is_syllabus, context=st.session_state.clean_text)
                
            st.session_state.structured_text = generated_content
            st.session_state.pipeline_done = True 
            # Provide instant success and display
            st.success("✅ Content generated! Ready for export.")
        else:
            st.error("Please enter a topic or syllabus.")
            
    if st.session_state.structured_text and page == "✨ Generate (GEN)":
        st.markdown("### 📝 Output")
        render_inline_content(st.session_state.structured_text)
        st.markdown("---")
        
        st.markdown("### 📥 Quick Exports")
        c1, c2 = st.columns(2)
        
        with c1:
            if st.button("Export to PDF", use_container_width=True):
                with st.spinner("Generating Booklet PDF..."):
                    pdf_path = "data/output/generated_notes.pdf"
                    success = M["gen_booklet"](st.session_state.structured_text, [], "Generated Study Notes", pdf_path)
                    if success and os.path.exists(pdf_path):
                        with open(pdf_path, "rb") as pdf_file:
                            pdf_bytes = pdf_file.read()
                        st.download_button(label="📄 Download PDF", data=pdf_bytes, file_name="study_notes.pdf", mime="application/pdf", use_container_width=True)
                    else:
                        st.error("❌ PDF Generation Failed.")
                        
        with c2:
            if st.button("Export to PPT", use_container_width=True):
                with st.spinner("Generating Presentation..."):
                    ppt_path = "data/output/generated_slides.pptx"
                    success = M["gen_ppt"](st.session_state.structured_text, [], "Generated Topic", ppt_path)
                    if success and os.path.exists(ppt_path):
                        with open(ppt_path, "rb") as pptx_file:
                            ppt_bytes = pptx_file.read()
                        st.download_button(label="📊 Download PPT", data=ppt_bytes, file_name="study_presentation.pptx", mime="application/vnd.openxmlformats-officedocument.presentationml.presentation", use_container_width=True)
                    else:
                        st.error("❌ PPT Generation Failed.")

# ══════════════════════════════════════════════
# PAGE: OCR UPLOAD
# ══════════════════════════════════════════════

elif page == "📸 OCR Upload":
    st.markdown("## 📸 OCR Image & PDF Upload")
    st.caption("Upload images or scanned PDFs (handwritten/notes). Extract text and send it to RAG, GEN, SOLVE, or Explain it.")
    
    uploaded_file_ocr = st.file_uploader("Upload Image or PDF", type=["png", "jpg", "jpeg", "pdf"])
    
    if uploaded_file_ocr:
        os.makedirs("data/input", exist_ok=True)
        file_path = os.path.join("data", "input", uploaded_file_ocr.name)
        with open(file_path, "wb") as f:
            f.write(uploaded_file_ocr.getbuffer())
            
        # PDF Multipage logic vs Single Image
        if uploaded_file_ocr.name.lower().endswith('.pdf'):
            import fitz
            doc = fitz.open(file_path)
            st.info(f"**PDF Detected** ({len(doc)} pages). Preparing to run OCR extraction on all pages.")
            
            if st.button("🔍 Extract Text from All Pages", use_container_width=True):
                extracted_text_all = []
                with st.spinner("Processing PDF pages via OCR (This might take a while)..."):
                    for page_num in range(len(doc)):
                        page = doc[page_num]
                        pix = page.get_pixmap(dpi=150)
                        page_img_path = f"{file_path}_p{page_num}.png"
                        pix.save(page_img_path)
                        
                        st.image(page_img_path, caption=f"Page {page_num+1}", width=350)
                        extracted_text = M["ocr_ext"](page_img_path)
                        if extracted_text:
                            extracted_text_all.append(f"--- Page {page_num + 1} ---\n{extracted_text}")
                            
                st.session_state.ocr_text = "\n\n".join(extracted_text_all)
                doc.close()
        else:
            st.image(file_path, caption="Uploaded Image", use_container_width=True)
            if st.button("🔍 Extract Text", use_container_width=True):
                with st.spinner("Processing image via EasyOCR..."):
                    extracted_text = M["ocr_ext"](file_path)
                    st.session_state.ocr_text = extracted_text
                
        if st.session_state.ocr_text:
            st.warning("⚠️ **Note:** OCR on handwritten text may contain spelling errors. Please correct them below before passing to AI.")
            edited_text = st.text_area("Extracted Text (Editable):", value=st.session_state.ocr_text, height=250)
            
            if st.button("💾 Save as Context (Enables Chat & MCQ Quiz)", type="primary"):
                with st.spinner("Cleaning & Saving OCR Context..."):
                    clean_text = M["clean"](edited_text)
                    st.session_state.context_text = clean_text
                    rag_store = M["build_rag"](clean_text)
                    st.session_state.rag_store = rag_store
                    st.session_state.pipeline_done = True
                    st.success("✅ Context Saved! You can now use the Chat & Solve or MCQ Quiz tabs.")
            
            col1, col2, col3 = st.columns(3)
            
            # Variables to store output so it renders outside the columns
            ocr_output_header = None
            ocr_output_content = None
            show_downloads = False
            
            with col1:
                if st.button("💬 Ask (RAG)", use_container_width=True):
                    with st.spinner("Asking RAG..."):
                        rag = st.session_state.rag_store
                        relevant_chunks = []
                        if rag and rag.get("index") is not None:
                            relevant_chunks = M["retrieve"](edited_text, rag["chunks"], rag["index"], k=5)
                        ans = M["llm"](user_query=edited_text, context_chunks=relevant_chunks)
                        
                        if "messages" not in st.session_state:
                            st.session_state.messages = []
                        st.session_state.messages.append({"role": "user", "content": f"[Image OCR]\n{edited_text}"})
                        st.session_state.messages.append({"role": "assistant", "content": ans})
                        st.success("Sent to chat! Check 'Chat & Solve' page.")
            with col2:
                if st.button("✨ Generate Notes", use_container_width=True):
                    with st.spinner("Generating Notes..."):
                        ans = M["gen_academic"](edited_text, is_syllabus=False, context=st.session_state.context_text)
                        st.session_state.ocr_generated_notes = ans
                        
            with col3:
                if st.button("💡 Explain Concept", use_container_width=True):
                    with st.spinner("Analyzing Concept..."):
                        # Custom straightforward explanation prompt
                        prompt = f"Please interpret and clearly explain the concepts mentioned in this OCR-extracted text. Format using concise paragraphs and bullet points where helpful:\n\n{edited_text}"
                        ans = M["llm"](user_query=prompt, context_chunks=[])
                        ocr_output_header = "### 💡 Explanation"
                        ocr_output_content = ans
                        
            # Immediate pass-through of session state for notes
            if st.session_state.ocr_generated_notes and not ocr_output_content:
                ocr_output_header = "### 📝 Notes Output"
                ocr_output_content = st.session_state.ocr_generated_notes
                show_downloads = True

            if ocr_output_content:
                st.markdown("---")
                st.markdown(ocr_output_header)
                st.markdown(ocr_output_content)
                
                # Dynamic rendering of downloads if in Notes mode
                if show_downloads:
                    st.markdown("### 📥 Download Notes")
                    c1, c2 = st.columns(2)
                    with c1:
                        if st.button("Export to PDF", key="ocr_pdf_btn", use_container_width=True):
                            with st.spinner("Generating Booklet PDF..."):
                                pdf_path = "data/output/ocr_notes.pdf"
                                success = M["gen_booklet"](st.session_state.ocr_generated_notes, [], "Generated Study Notes", pdf_path)
                                if success and os.path.exists(pdf_path):
                                    with open(pdf_path, "rb") as pdf_file:
                                        pdf_bytes = pdf_file.read()
                                    st.download_button(label="📄 Download PDF", data=pdf_bytes, file_name="ocr_notes.pdf", mime="application/pdf", use_container_width=True)
                                else:
                                    st.error("❌ PDF Generation Failed.")
                    with c2:
                        if st.button("Export to PPT", key="ocr_ppt_btn", use_container_width=True):
                            with st.spinner("Generating Presentation..."):
                                ppt_path = "data/output/ocr_slides.pptx"
                                success = M["gen_ppt"](st.session_state.ocr_generated_notes, [], "Generated Topic", ppt_path)
                                if success and os.path.exists(ppt_path):
                                    with open(ppt_path, "rb") as pptx_file:
                                        ppt_bytes = pptx_file.read()
                                    st.download_button(label="📊 Download PPT", data=ppt_bytes, file_name="ocr_presentation.pptx", mime="application/vnd.openxmlformats-officedocument.presentationml.presentation", use_container_width=True)
                                else:
                                    st.error("❌ PPT Generation Failed.")


# ══════════════════════════════════════════════
# PAGE: PPT GENERATOR
# ══════════════════════════════════════════════

elif page == "📊 PPT Generator":
    st.markdown("## 📊 PPT Generator")
    st.caption("Generate a presentation from your uploaded study material.")

    if not st.session_state.pipeline_done:
        st.warning("⚠️ No document processed yet. Go to **Upload & Process** first.")
        st.stop()

    col1, col2 = st.columns([1.2, 1])

    with col1:
        st.markdown("### Preview Slide Structure")
        # Parse headings for preview
        headings = [
            line[2:].strip()
            for line in st.session_state.structured_text.split("\n")
            if line.startswith("# ")
        ]
        st.markdown(f"**{len(headings) + 1} slides** will be generated:")
        st.markdown("- 🎯 Title Slide")
        for h in headings[:15]:
            st.markdown(f"- 📄 {h}")
        if len(headings) > 15:
            st.caption(f"...and {len(headings) - 15} more slides")

    with col2:
        st.markdown("### Generate")
        include_imgs = st.checkbox("Include extracted images in slides", value=True)

        custom_title = st.text_input("Presentation title:", value=st.session_state.doc_title)

        if st.button("Generate PPT", type="primary", use_container_width=True):
            with st.spinner("Building slides..."):
                success = M["gen_ppt"](
                    st.session_state.structured_text,
                    images=st.session_state.images if include_imgs else [],
                    title=custom_title,
                    output_path="data/output/booklet.pptx",
                )

            if success and os.path.exists("data/output/booklet.pptx"):
                st.success(f"✅ PPT generated with {len(headings) + 1} slides!")
                with open("data/output/booklet.pptx", "rb") as f:
                    st.download_button(
                        "📥 Download PowerPoint",
                        data=f,
                        file_name=f"{custom_title}.pptx",
                        mime="application/vnd.openxmlformats-officedocument.presentationml.presentation",
                        use_container_width=True,
                    )
            else:
                st.error("PPT generation failed. Check console logs.")

        # Preview extracted images
        if st.session_state.images:
            st.markdown("#### 🖼️ Images to be embedded")
            img_cols = st.columns(2)
            for i, img in enumerate(st.session_state.images[:4]):
                if os.path.exists(img["path"]):
                    img_cols[i % 2].image(img["path"], caption=f"Page {img['page']}", use_container_width=True)