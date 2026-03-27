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
    "messages": [],            # Chat history
    "uploaded_filename": "",
    "doc_title": "Study Booklet",
}

for k, v in defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v


# ─────────────────────────────────────────────
# SIDEBAR NAVIGATION
# ─────────────────────────────────────────────

with st.sidebar:
    st.markdown("## 📘 BOOKLET AI")
    st.markdown("---")

    page = st.radio(
        "Navigation",
        ["📤 Upload & Process", "📘 Booklet Generator", "💬 RAG Chatbot", "📊 PPT Generator"],
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
    lines = text.split("\n")
    for line in lines:
        raw = line.strip()
        if raw.startswith("![IMAGE:"):
            img_path = raw[8:-1]
            if os.path.exists(img_path):
                st.image(img_path, use_container_width=True)
        else:
            st.markdown(line)


# ─────────────────────────────────────────────
# LAZY IMPORTS (avoid import errors on startup)
# ─────────────────────────────────────────────

@st.cache_resource(show_spinner=False)
def load_modules():
    from modules.member2_input_extraction import extract
    from modules.member3_clean_simplify import clean_and_simplify
    from modules.member1_ai_logic import build_structure
    from modules.member4_booklet_generator import generate_booklet
    from modules.ppt_generator import generate_ppt
    from modules.rag_engine import build_rag_store, retrieve_top_k
    from modules.llm_gateway import generate_answer
    return {
        "extract": extract,
        "clean": clean_and_simplify,
        "structure": build_structure,
        "gen_booklet": generate_booklet,
        "gen_ppt": generate_ppt,
        "build_rag": build_rag_store,
        "retrieve": retrieve_top_k,
        "llm": generate_answer,
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
            type=["pdf", "pptx", "txt"],
            help="Supports PDF (text + images), PPTX (text + images), and TXT files.",
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

        if raw_text:
            with st.spinner("🧹 Cleaning text..."):
                clean = M["clean"](raw_text)

            with st.spinner("📐 Structuring content..."):
                structured = M["structure"](clean)

            with st.spinner("🧠 Building RAG index (embedding chunks)..."):
                rag_store = M["build_rag"](clean)

            # Persist to session state
            st.session_state.pipeline_done = True
            st.session_state.raw_text = raw_text
            st.session_state.clean_text = clean
            st.session_state.structured_text = structured
            st.session_state.images = images
            st.session_state.rag_store = rag_store
            st.session_state.uploaded_filename = file_name
            st.session_state.doc_title = doc_title
            st.session_state.messages = []  # Reset chat on new upload

            st.success(f"✅ Processed **{file_name}** — {len(images)} image(s) extracted, {len(rag_store['chunks'])} chunks indexed.")

            with st.expander("📄 Content Preview (Text + Inline Images)", expanded=True):
                render_inline_content(st.session_state.structured_text)
        else:
            st.error("Please upload a file or paste some text first.")


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

elif page == "💬 RAG Chatbot":
    st.markdown("## 💬 RAG Chatbot")
    st.caption("Answers **strictly from your uploaded document**. If not found → *'Not in document.'*")

    if not st.session_state.pipeline_done:
        st.warning("⚠️ No document processed yet. Go to **Upload & Process** first.")
        st.stop()

    col_chat, col_ctx = st.columns([2.2, 1])

    with col_chat:
        # Mode selector
        mode = st.radio("Notes style:", ["Study", "Exam"], horizontal=True)

        # Chat history display — text only
        for msg in st.session_state.messages:
            with st.chat_message(msg["role"]):
                st.markdown(msg["content"])

        # Chat input
        prompt = st.chat_input("Ask something about your document...")

        if prompt:
            # User message
            st.session_state.messages.append({"role": "user", "content": prompt})
            with st.chat_message("user"):
                st.markdown(prompt)

            # RAG: retrieve relevant chunks
            rag = st.session_state.rag_store
            relevant_chunks = []

            if rag and rag.get("index") is not None:
                with st.spinner("🔍 Searching document..."):
                    relevant_chunks = M["retrieve"](
                        prompt,
                        rag["chunks"],
                        rag["index"],
                        k=5,
                    )

            # Generate answer (strict RAG — text only)
            with st.spinner("💭 Generating answer..."):
                answer = M["llm"](
                    user_query=prompt,
                    context_chunks=relevant_chunks,
                    mode=mode,
                    strict_rag=True,
                )

            st.session_state.messages.append({"role": "assistant", "content": answer})
            with st.chat_message("assistant"):
                st.markdown(answer)

    with col_ctx:
        st.markdown("### 📚 Retrieved Context")
        st.caption("Top chunks used for the last answer.")

        if st.session_state.messages:
            last_user = next(
                (m["content"] for m in reversed(st.session_state.messages)
                 if m["role"] == "user"),
                None,
            )
            rag = st.session_state.rag_store
            if last_user and rag and rag.get("index") is not None:
                ctx_chunks = M["retrieve"](
                    last_user,
                    rag["chunks"],
                    rag["index"],
                    k=3,
                )
                for i, chunk in enumerate(ctx_chunks):
                    with st.expander(f"Chunk {i + 1}"):
                        st.write(chunk[:500] + ("..." if len(chunk) > 500 else ""))

    # Clear chat
    if st.session_state.messages:
        if st.button("🗑️ Clear Chat"):
            st.session_state.messages = []
            st.rerun()


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