import streamlit as st
import requests
import io
import time

# --- CONFIGURATION & CONSTANTS ---
API_BASE_URL = "http://127.0.0.1:8000/api/v1/preprocessing"
DOC_API_URL = "http://127.0.0.1:8000/api/v1/documents"

AVAILABLE_PROFILES = {
    "original": "Original (No Preprocessing)",
    "basic": "Basic (Denoise & Grayscale)",
    "low_light": "Low Light (CLAHE & Adaptive)",
    "overexposed": "Overexposed (Gamma Fix)",
    "skewed": "Skewed (Deskew & Rotate)",
    "noisy_scan": "Noisy Scan (Median Filter)",
    "small_text": "Small Text (Upscale 2x & Sharpen)"
}


def apply_custom_theme():
    """Injects global CSS for dark glassmorphism, ambient gradients, and UI polish."""
    st.markdown("""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&display=swap');

        :root {
            --bg-dark: #07090e;
            --surface: rgba(18, 24, 38, 0.55);
            --surface-soft: rgba(255, 255, 255, 0.03);
            --border: rgba(255, 255, 255, 0.08);
            --border-hover: rgba(99, 102, 241, 0.6);
            --primary: #6366f1;
            --accent: #38bdf8;
            --text-main: #f8fafc;
            --text-muted: #a3b0c7;
            --danger: #ef4444;
            --success: #34d399;
            --warning: #fb923c;
        }

        html, body, [class*="css"], .stApp {
            font-family: 'Plus Jakarta Sans', sans-serif !important;
            background-color: var(--bg-dark) !important;
            color: var(--text-main) !important;
        }

        /* Ambient Gradient Highlights + Grid */
        .stApp {
            background-image:
                radial-gradient(circle at 15% 10%, rgba(99, 102, 241, 0.18) 0%, transparent 42%),
                radial-gradient(circle at 85% 85%, rgba(56, 189, 248, 0.14) 0%, transparent 45%),
                radial-gradient(circle at 85% 5%, rgba(52, 211, 153, 0.08) 0%, transparent 35%),
                linear-gradient(to right, rgba(255, 255, 255, 0.03) 1px, transparent 1px),
                linear-gradient(to bottom, rgba(255, 255, 255, 0.03) 1px, transparent 1px) !important;
            background-size: auto, auto, auto, 40px 40px, 40px 40px !important;
        }

        /* Glassmorphic Sidebar */
        section[data-testid="stSidebar"] {
            background: rgba(9, 12, 20, 0.78) !important;
            background-image: radial-gradient(circle at 30% 0%, rgba(99, 102, 241, 0.14) 0%, transparent 55%) !important;
            backdrop-filter: blur(22px) saturate(150%) !important;
            -webkit-backdrop-filter: blur(22px) saturate(150%) !important;
            border-right: 1px solid var(--border) !important;
        }

        /* Glass Cards for Document Pages */
        div[data-testid="stVerticalBlockBorderWrapper"] {
            background: var(--surface) !important;
            background-image: radial-gradient(circle at 10% 10%, rgba(99, 102, 241, 0.08) 0%, transparent 40%) !important;
            backdrop-filter: blur(20px) saturate(140%) !important;
            -webkit-backdrop-filter: blur(20px) saturate(140%) !important;
            border: 1px solid var(--border) !important;
            border-radius: 16px !important;
            padding: 20px !important;
            margin-bottom: 20px !important;
            transition: border-color 0.2s ease, box-shadow 0.2s ease !important;
        }
        div[data-testid="stVerticalBlockBorderWrapper"]:hover {
            border-color: rgba(255, 255, 255, 0.16) !important;
            box-shadow: 0 10px 30px -10px rgba(0, 0, 0, 0.5) !important;
        }

        /* Metrics Glass Container */
        .metric-container {
            background: var(--surface-soft);
            backdrop-filter: blur(12px);
            -webkit-backdrop-filter: blur(12px);
            border: 1px solid var(--border);
            border-radius: 12px;
            padding: 16px;
            height: 100%;
        }
        
        .metric-row {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 7px 0;
            border-bottom: 1px solid rgba(255, 255, 255, 0.04);
            font-size: 0.85rem;
        }
        .metric-row:last-child {
            border-bottom: none;
        }
        .metric-label {
            color: var(--text-muted);
            font-weight: 500;
        }
        .metric-value {
            color: var(--text-main);
            font-weight: 700;
            font-family: monospace;
        }

        /* Quality Badges */
        .badge {
            padding: 4px 10px;
            border-radius: 12px;
            font-size: 0.72rem;
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: 0.04em;
            border: 1px solid transparent;
            display: inline-block;
        }
        .badge-good { background: rgba(52, 211, 153, 0.14); color: #34d399; border-color: rgba(52, 211, 153, 0.35); }
        .badge-warning { background: rgba(251, 146, 60, 0.14); color: #fb923c; border-color: rgba(251, 146, 60, 0.35); }
        .badge-critical { background: rgba(239, 68, 68, 0.14); color: #ef4444; border-color: rgba(239, 68, 68, 0.35); }
        .badge-info { background: rgba(56, 189, 248, 0.14); color: #38bdf8; border-color: rgba(56, 189, 248, 0.35); }

        /* Glass Image Cards */
        div[data-testid="stImage"] {
            border-radius: 10px !important;
            overflow: hidden !important;
            border: 1px solid var(--border) !important;
            transition: border-color 0.2s ease, transform 0.2s ease !important;
            background: rgba(0, 0, 0, 0.25) !important;
        }
        div[data-testid="stImage"]:hover {
            border-color: var(--border-hover) !important;
            transform: scale(1.005);
        }

        /* Primary Buttons */
        div.stButton > button[kind="primary"] {
            width: 100% !important;
            background: linear-gradient(135deg, var(--primary) 0%, #4338ca 100%) !important;
            color: white !important;
            border: 1px solid rgba(255, 255, 255, 0.12) !important;
            border-radius: 8px !important;
            font-weight: 600 !important;
            box-shadow: 0 10px 25px -10px rgba(99, 102, 241, 0.6) !important;
            transition: all 0.2s ease !important;
        }
        div.stButton > button[kind="primary"]:hover {
            transform: translateY(-1px);
            box-shadow: 0 12px 30px -8px rgba(99, 102, 241, 0.8) !important;
        }

        /* Secondary Buttons */
        div.stButton > button[kind="secondary"] {
            background: rgba(255, 255, 255, 0.04) !important;
            border: 1px solid var(--border) !important;
            color: var(--text-main) !important;
            border-radius: 8px !important;
            font-weight: 500 !important;
            transition: all 0.2s ease !important;
        }
        div.stButton > button[kind="secondary"]:hover {
            background: rgba(99, 102, 241, 0.15) !important;
            border-color: rgba(99, 102, 241, 0.4) !important;
            color: #eef0ff !important;
        }

        /* Dropdowns / Selectboxes */
        div[data-baseweb="select"] > div {
            background: rgba(12, 16, 26, 0.75) !important;
            border-color: var(--border) !important;
            color: var(--text-main) !important;
            border-radius: 8px !important;
        }
        div[data-baseweb="select"]:hover > div {
            border-color: var(--border-hover) !important;
        }
    </style>
    """, unsafe_allow_html=True)


# --- API HELPERS ---
@st.cache_data(show_spinner=False, ttl=300)
def fetch_image_bytes(url: str) -> io.BytesIO:
    """Fetches image bytes safely."""
    try:
        res = requests.get(url)
        if res.status_code == 200:
            return io.BytesIO(res.content)
    except Exception:
        pass
    return None

def trigger_batch_preprocessing():
    """Runs batch assessment for newly queued documents."""
    for doc in st.session_state.queued_documents:
        doc_id = doc["document_id"]
        if doc_id not in st.session_state.prep_results:
            with st.spinner(f"Analyzing & Preprocessing: {doc.get('filename', doc_id)}..."):
                res = requests.post(f"{API_BASE_URL}/documents/{doc_id}")
                if res.status_code == 200:
                    data = res.json()
                    st.session_state.prep_results[doc_id] = {
                        idx: page for idx, page in enumerate(data.get("processed_pages", []), start=1)
                    }
                else:
                    st.error(f"Failed to preprocess {doc_id}")

def update_manual_profile(doc_id: str, page_num: int, new_profile: str):
    """Executes single-page manual profile override."""
    payload = {"override_profile": new_profile}
    with st.spinner("Applying custom pipeline..."):
        res = requests.post(f"{API_BASE_URL}/documents/{doc_id}/pages/{page_num}", json=payload)
        if res.status_code == 200:
            updated_data = res.json()
            updated_data["_timestamp"] = time.time() 
            st.session_state.prep_results[doc_id][page_num] = updated_data
            st.rerun()
        else:
            st.error("Failed to apply override.")

def handle_override_change(doc_id: str, page_num: int):
    """on_change handler for the override selectbox."""
    new_profile = st.session_state[f"override_{doc_id}_{page_num}"]
    update_manual_profile(doc_id, page_num, new_profile)

# --- UI COMPONENTS ---
def render_quality_badge(label: str) -> str:
    """Renders quality status badge."""
    label_lower = label.lower()
    if "good" in label_lower or "original" in label_lower:
        badge_class = "badge-good"
    elif "warning" in label_lower or "light" in label_lower or "noise" in label_lower:
        badge_class = "badge-warning"
    elif "critical" in label_lower or "skew" in label_lower or "overexposed" in label_lower:
        badge_class = "badge-critical"
    else:
        badge_class = "badge-info"
    
    return f'<span class="badge {badge_class}">{label}</span>'

def render_metrics_panel(q_data: dict):
    """Renders the assessment metrics HTML structure."""
    blur = round(q_data.get("blur_score", 0), 1)
    bright = round(q_data.get("brightness_score", 0), 1)
    contrast = round(q_data.get("contrast_score", 0), 1)
    skew = round(q_data.get("skew_angle", 0), 2)
    dpi = q_data.get("estimated_dpi", "N/A")
    boundary = "Detected" if q_data.get("has_document_boundary") else "None"

    html = f"""
    <div class="metric-container">
        <div style="font-weight: 600; color: #f8fafc; margin-bottom: 10px; font-size: 0.95rem;">Assessment Metrics</div>
        <div class="metric-row"><span class="metric-label">Blur Score</span> <span class="metric-value">{blur}</span></div>
        <div class="metric-row"><span class="metric-label">Brightness</span> <span class="metric-value">{bright}</span></div>
        <div class="metric-row"><span class="metric-label">Contrast</span> <span class="metric-value">{contrast}</span></div>
        <div class="metric-row"><span class="metric-label">Skew Angle</span> <span class="metric-value">{skew}°</span></div>
        <div class="metric-row"><span class="metric-label">Estimated DPI</span> <span class="metric-value">{dpi}</span></div>
        <div class="metric-row"><span class="metric-label">Boundary</span> <span class="metric-value">{boundary}</span></div>
    </div>
    """
    st.markdown(html, unsafe_allow_html=True)

@st.dialog("Side-by-Side Lightbox", width="large")
def image_lightbox(doc_id: str, page_num: int, timestamp: float):
    """Lightbox modal to view high-res side-by-side comparison."""
    orig_url = f"{DOC_API_URL}/{doc_id}/pages/{page_num}/image"
    proc_url = f"{API_BASE_URL}/documents/{doc_id}/pages/{page_num}/processed-image?t={timestamp}"
    
    st.markdown("### High-Resolution Comparison")
    c1, c2 = st.columns(2)
    
    with c1:
        st.caption("Original Scan")
        orig_img = fetch_image_bytes(orig_url)
        if orig_img: 
            st.image(orig_img, width="stretch")
            
    with c2:
        st.caption("Preprocessed Output")
        proc_img = fetch_image_bytes(proc_url)
        if proc_img: 
            st.image(proc_img, width="stretch")

# --- MAIN PAGE RENDERER ---
def render_preprocessing_page():
    apply_custom_theme()

    # Session State Initialization
    if "queued_documents" not in st.session_state:
        st.session_state.queued_documents = []
    if "prep_results" not in st.session_state:
        st.session_state.prep_results = {}

    st.markdown("## Quality Preprocessing")
    st.caption("Review automated quality assessments, inspect side-by-side enhancements, and apply manual pipeline overrides.")
    st.markdown("<br>", unsafe_allow_html=True)

    if not st.session_state.queued_documents:
        st.info("📁 No documents queued. Please upload documents in the Ingestion tab first.")
        if st.button("← Back to Ingestion", type="secondary"):
            st.switch_page("views/ingestion_view.py")
        return

    # Trigger batch API logic automatically for new files
    trigger_batch_preprocessing()

    # Top Control Toolbar
    col_preset, col_spacer, col_ocr = st.columns([2.5, 4.5, 2.5])
    with col_preset:
        batch_preset = st.selectbox(
            "Apply Pipeline to All Pages:",
            options=[""] + list(AVAILABLE_PROFILES.keys()),
            format_func=lambda x: "Select preset for batch..." if x == "" else AVAILABLE_PROFILES[x],
            key="batch_preset_selector"
        )
        if batch_preset:
            if st.button("Apply to Batch", type="secondary", width="stretch"):
                for doc in st.session_state.queued_documents:
                    doc_id = doc["document_id"]
                    for page_num in st.session_state.prep_results.get(doc_id, {}).keys():
                        update_manual_profile(doc_id, page_num, batch_preset)
                st.toast("Batch profile applied successfully!", icon="✅")

    with col_ocr:
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("Proceed to OCR Engine", type="primary", width="stretch"):
            st.switch_page("views/ocr_engine_view.py")

    st.markdown("<br>", unsafe_allow_html=True)

    # Render Document Pages
    for doc in st.session_state.queued_documents:
        doc_id = doc["document_id"]
        filename = doc.get("filename", f"Doc {doc_id}")
        doc_pages = st.session_state.prep_results.get(doc_id, {})
        
        for page_num, q_data in doc_pages.items():
            # Card Container
            with st.container(border=True):
                # Header
                st.markdown(f"""
                    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 14px;">
                        <div>
                            <strong style="font-size: 1.05rem; color: #f8fafc;">{filename}</strong> 
                            <span style="color: #a3b0c7; margin-left: 8px; font-size: 0.9rem;">— Page {page_num}</span>
                        </div>
                        {render_quality_badge(q_data.get('quality_label', 'Pending'))}
                    </div>
                """, unsafe_allow_html=True)

                # Body Columns: Thumbnail 1 | Thumbnail 2 | Metrics
                c1, c2, c3 = st.columns([1.2, 1.2, 1])
                
                ts = q_data.get("_timestamp", time.time())
                orig_url = f"{DOC_API_URL}/{doc_id}/pages/{page_num}/image"
                proc_url = f"{API_BASE_URL}/documents/{doc_id}/pages/{page_num}/processed-image?t={ts}"

                with c1:
                    st.caption("Original")
                    orig_bytes = fetch_image_bytes(orig_url)
                    if orig_bytes:
                        st.image(orig_bytes, width="stretch")
                    
                with c2:
                    st.caption("Enhanced Output")
                    proc_bytes = fetch_image_bytes(proc_url)
                    if proc_bytes:
                        st.image(proc_bytes, width="stretch")
                        
                with c3:
                    render_metrics_panel(q_data)
                    st.markdown("<br>", unsafe_allow_html=True)
                    if st.button("🔍 Expand Images", key=f"expand_{doc_id}_{page_num}", type="secondary", width="stretch"):
                        image_lightbox(doc_id, page_num, ts)

                # Footer Override Control
                applied = q_data.get("applied_profile") or q_data.get("recommended_profile") or "original"
                rec_label = AVAILABLE_PROFILES.get(q_data.get("recommended_profile"), "Pending")
                
                f1, f2 = st.columns([2.5, 2.5])
                with f1:
                    st.selectbox(
                        "Selected Profile Override:",
                        options=list(AVAILABLE_PROFILES.keys()),
                        format_func=lambda x: AVAILABLE_PROFILES[x],
                        index=list(AVAILABLE_PROFILES.keys()).index(applied) if applied in AVAILABLE_PROFILES else 0,
                        key=f"override_{doc_id}_{page_num}",
                        on_change=handle_override_change,
                        args=(doc_id, page_num)
                    )
                with f2:
                    st.markdown(f"""
                        <div style="margin-top: 30px; font-size: 0.88rem; color: #a3b0c7;">
                            Auto-Suggested: <strong style="color: #6366f1;">{rec_label}</strong>
                        </div>
                    """, unsafe_allow_html=True)

if __name__ == "__main__":
    st.set_page_config(layout="wide")
    render_preprocessing_page()