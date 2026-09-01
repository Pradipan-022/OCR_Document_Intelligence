import streamlit as st
import requests
import io

# --- CONFIGURATION ---
API_HOST = "http://127.0.0.1:8000"
HISTORY_API_URL = f"{API_HOST}/api/v1/history"
DOC_API_URL = f"{API_HOST}/api/v1/documents"

FILE_TYPE_STYLES = {
    "pdf": {"color": "#fb923c", "bg": "rgba(251, 146, 60, 0.14)", "border": "rgba(251, 146, 60, 0.35)"},
    "jpg": {"color": "#38bdf8", "bg": "rgba(56, 189, 248, 0.14)", "border": "rgba(56, 189, 248, 0.35)"},
    "jpeg": {"color": "#38bdf8", "bg": "rgba(56, 189, 248, 0.14)", "border": "rgba(56, 189, 248, 0.35)"},
    "png": {"color": "#34d399", "bg": "rgba(52, 211, 153, 0.14)", "border": "rgba(52, 211, 153, 0.35)"},
    "default": {"color": "#a3b0c7", "bg": "rgba(255, 255, 255, 0.05)", "border": "rgba(255, 255, 255, 0.14)"},
}


def apply_custom_theme():
    """Injects dark glassmorphism CSS, ambient gradients, and UI styles."""
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
            --danger-bg: rgba(239, 68, 68, 0.12);
            --danger-border: rgba(239, 68, 68, 0.35);
            --success: #34d399;
        }

        html, body, [class*="css"], .stApp {
            font-family: 'Plus Jakarta Sans', sans-serif !important;
            background-color: var(--bg-dark) !important;
            color: var(--text-main) !important;
        }

        /* Ambient Background Gradients */
        .stApp {
            background-image:
                radial-gradient(circle at 15% 10%, rgba(99, 102, 241, 0.18) 0%, transparent 42%),
                radial-gradient(circle at 85% 85%, rgba(56, 189, 248, 0.14) 0%, transparent 45%),
                radial-gradient(circle at 85% 5%, rgba(52, 211, 153, 0.08) 0%, transparent 35%),
                linear-gradient(to right, rgba(255, 255, 255, 0.03) 1px, transparent 1px),
                linear-gradient(to bottom, rgba(255, 255, 255, 0.03) 1px, transparent 1px) !important;
            background-size: auto, auto, auto, 40px 40px, 40px 40px !important;
        }

        /* Standard Glassmorphic Document Card Container */
        div[data-testid="stVerticalBlockBorderWrapper"] {
            background: var(--surface) !important;
            background-image: radial-gradient(circle at 10% 10%, rgba(99, 102, 241, 0.08) 0%, transparent 40%) !important;
            backdrop-filter: blur(20px) saturate(140%) !important;
            -webkit-backdrop-filter: blur(20px) saturate(140%) !important;
            border: 1px solid var(--border) !important;
            border-radius: 16px !important;
            padding: 18px !important;
            margin-bottom: 16px !important;
            transition: all 0.25s ease-in-out !important;
        }
        div[data-testid="stVerticalBlockBorderWrapper"]:hover {
            border-color: rgba(255, 255, 255, 0.18) !important;
            box-shadow: 0 10px 30px -10px rgba(0, 0, 0, 0.5) !important;
        }

        /* Dynamic Selected Highlight Card Backdrop */
        div[data-testid="stVerticalBlockBorderWrapper"]:has(.card-selected-marker) {
            background: rgba(99, 102, 241, 0.12) !important;
            background-image: radial-gradient(circle at 50% 0%, rgba(99, 102, 241, 0.28) 0%, transparent 75%) !important;
            border: 1px solid rgba(99, 102, 241, 0.65) !important;
            box-shadow: 0 0 25px rgba(99, 102, 241, 0.25), inset 0 0 15px rgba(99, 102, 241, 0.1) !important;
        }

        /* Thumbnail Frames */
        div[data-testid="stImage"] {
            border-radius: 10px !important;
            overflow: hidden !important;
            border: 1px solid var(--border) !important;
            background: rgba(0, 0, 0, 0.3) !important;
            transition: border-color 0.2s ease, transform 0.2s ease !important;
        }
        div[data-testid="stImage"]:hover {
            border-color: var(--border-hover) !important;
            transform: scale(1.02);
        }

        /* Badges */
        .badge-format {
            padding: 2px 9px;
            border-radius: 12px;
            font-size: 0.72rem;
            font-weight: 600;
            border: 1px solid;
            text-transform: uppercase;
            letter-spacing: 0.02em;
        }

        .status-badge {
            padding: 3px 10px;
            border-radius: 12px;
            font-size: 0.75rem;
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: 0.04em;
            border: 1px solid transparent;
            display: inline-block;
        }
        .status-processed { background: rgba(52, 211, 153, 0.14); color: #34d399; border-color: rgba(52, 211, 153, 0.35); }
        .status-uploaded { background: rgba(56, 189, 248, 0.14); color: #38bdf8; border-color: rgba(56, 189, 248, 0.35); }

        /* Standard Primary Buttons */
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

        /* Standard Secondary Buttons */
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

        /* Vertical alignment fix for action buttons */
        div[data-testid="stHorizontalBlock"] {
            align-items: center !important;
        }

        /* Queue File Button with Soft Blue Glass Backdrop Glow */
        div[data-testid="stElementContainer"]:has(.queue-button-marker) + div[data-testid="stElementContainer"] div.stButton > button[kind="secondary"] {
            background: rgba(56, 189, 248, 0.08) !important;
            border: 1px solid rgba(56, 189, 248, 0.3) !important;
            color: #38bdf8 !important;
            font-weight: 600 !important;
            backdrop-filter: blur(10px) !important;
            -webkit-backdrop-filter: blur(10px) !important;
            box-shadow: 0 0 15px rgba(56, 189, 248, 0.2) !important;
            transition: all 0.2s ease-in-out !important;
        }

        div[data-testid="stElementContainer"]:has(.queue-button-marker) + div[data-testid="stElementContainer"] div.stButton > button[kind="secondary"]:hover {
            background: rgba(56, 189, 248, 0.2) !important;
            border-color: rgba(56, 189, 248, 0.6) !important;
            color: #ffffff !important;
            box-shadow: 0 0 22px rgba(56, 189, 248, 0.45) !important;
            transform: translateY(-1px);
        }

        /* Glassmorphic Red Delete Button */
        div[data-testid="stElementContainer"]:has(.delete-button-marker) + div[data-testid="stElementContainer"] div.stButton > button {
            background: rgba(239, 68, 68, 0.12) !important;
            border: 1px solid rgba(239, 68, 68, 0.35) !important;
            color: #fca5a5 !important;
            font-weight: 600 !important;
            backdrop-filter: blur(12px) saturate(150%) !important;
            -webkit-backdrop-filter: blur(12px) saturate(150%) !important;
            box-shadow: 0 0 12px rgba(239, 68, 68, 0.15) !important;
            transition: all 0.2s ease-in-out !important;
        }

        div[data-testid="stElementContainer"]:has(.delete-button-marker) + div[data-testid="stElementContainer"] div.stButton > button:hover {
            background: rgba(239, 68, 68, 0.28) !important;
            border-color: rgba(239, 68, 68, 0.75) !important;
            color: #ffffff !important;
            box-shadow: 0 4px 20px rgba(239, 68, 68, 0.45) !important;
            transform: translateY(-1px);
        }
    </style>
    """, unsafe_allow_html=True)


# --- HELPERS ---
@st.cache_data(show_spinner=False, ttl=120)
def fetch_history(user_id: str = None) -> list:
    """Fetches document history from backend API."""
    params = {"user_id": user_id} if user_id and user_id != "Guest User" else {}
    try:
        res = requests.get(HISTORY_API_URL, params=params)
        if res.status_code == 200:
            return res.json()
    except Exception as e:
        st.error(f"Error connecting to backend history API: {e}")
    return []

@st.cache_data(show_spinner=False, ttl=300)
def fetch_image_bytes(relative_url: str) -> io.BytesIO:
    """Fetches image thumbnail bytes from backend."""
    if not relative_url:
        return None
    full_url = f"{API_HOST}{relative_url}" if relative_url.startswith("/") else relative_url
    try:
        res = requests.get(full_url)
        if res.status_code == 200:
            return io.BytesIO(res.content)
    except Exception:
        pass
    return None

def delete_document_api(document_id: str) -> bool:
    """Sends DELETE request to wipe document and its storage directory."""
    try:
        res = requests.delete(f"{DOC_API_URL}/{document_id}")
        return res.status_code == 200
    except Exception as e:
        st.error(f"Failed to communicate with server: {e}")
        return False

def render_type_badge(file_type: str) -> str:
    key = (file_type or "").lower().lstrip(".")
    style = FILE_TYPE_STYLES.get(key, FILE_TYPE_STYLES["default"])
    return f'<span class="badge-format" style="color:{style["color"]}; background:{style["bg"]}; border-color:{style["border"]};">{key}</span>'

def render_status_badge(status: str) -> str:
    st_clean = (status or "UPLOADED").upper()
    badge_class = "status-processed" if "PROC" in st_clean else "status-uploaded"
    return f'<span class="status-badge {badge_class}">{st_clean}</span>'


# --- MAIN VIEW ---
def render_history_page():
    apply_custom_theme()

    if "queued_documents" not in st.session_state:
        st.session_state.queued_documents = []

    st.markdown("## Document History Vault")
    st.caption("Browse past document sessions, inspect raw vs. preprocessed page thumbnails, queue files, or purge entries.")
    st.markdown("<br>", unsafe_allow_html=True)

    current_user = st.session_state.get("username", None)
    history = fetch_history(user_id=current_user)

    # Top Toolbar Controls
    col_search, col_spacer, col_action = st.columns([3, 2, 3])
    
    with col_search:
        search_query = st.text_input("🔍 Search History", placeholder="Filter by filename...", label_visibility="collapsed")
    
    with col_action:
        queued_count = len(st.session_state.queued_documents)
        btn_label = f"Proceed to Preprocessing ({queued_count}) 🚀"
        
        if st.button(btn_label, type="primary", disabled=(queued_count == 0), use_container_width=True):
            st.switch_page("views/preprocessing_view.py")

    st.markdown("<br>", unsafe_allow_html=True)

    filtered_history = [
        d for d in history if search_query.lower() in d["filename"].lower()
    ] if search_query else history

    if not filtered_history:
        st.info("📜 No history records found matching your criteria.")
        return

    # Render History Cards
    for doc in filtered_history:
        doc_id = doc["document_id"]
        filename = doc["filename"]
        file_type = doc["file_type"]
        pages = doc.get("pages", [])
        created_at = doc.get("created_at", "").replace("T", " ")[:19]
        status_str = doc.get("status", "UPLOADED")

        is_queued = any(d["document_id"] == doc_id for d in st.session_state.queued_documents)

        with st.container(border=True):
            if is_queued:
                st.markdown('<div class="card-selected-marker" style="display:none;"></div>', unsafe_allow_html=True)

            col_title, col_meta = st.columns([4.8, 3.2], vertical_alignment="center")

            with col_title:
                st.markdown(f"""
                    <div style="display: flex; align-items: center; gap: 10px;">
                        <strong style="font-size: 1.05rem; color: #f8fafc;">{filename}</strong>
                        {render_type_badge(file_type)}
                        {render_status_badge(status_str)}
                    </div>
                """, unsafe_allow_html=True)
                st.caption(f"ID: `{doc_id}` • Created: {created_at} • Pages: {len(pages)}")

            with col_meta:
                btn_col1, btn_col2 = st.columns([1.8, 1.2], vertical_alignment="center")

                # Queue Toggle Button
                with btn_col1:
                    st.markdown(
                        '<div class="queue-button-marker" style="display:none;"></div>',
                        unsafe_allow_html=True
                    )

                    button_label = "✓ Queued" if is_queued else "➕ Queue File"
                    button_type = "primary" if is_queued else "secondary"

                    if st.button(button_label, key=f"queue_btn_{doc_id}", type=button_type, use_container_width=True):
                        if is_queued:
                            st.session_state.queued_documents = [
                                d for d in st.session_state.queued_documents if d["document_id"] != doc_id
                            ]
                            st.toast(f"Removed {filename} from queue", icon="🗑️")
                        else:
                            formatted_item = {
                                "document_id": doc_id,
                                "filename": filename,
                                "file_type": file_type,
                                "page_count": len(pages),
                                "status": status_str
                            }
                            st.session_state.queued_documents.append(formatted_item)
                            st.toast(f"Added {filename} to queue!", icon="📥")
                        st.rerun()

                # Clean Glassmorphic Red Delete Button
                with btn_col2:
                    st.markdown(
                        '<div class="delete-button-marker" style="display:none;"></div>',
                        unsafe_allow_html=True
                    )

                    if st.button(
                        "Delete",
                        key=f"del_btn_{doc_id}",
                        type="secondary",
                        help="Permanently delete document",
                        use_container_width=True
                    ):
                        if delete_document_api(doc_id):
                            st.session_state.queued_documents = [
                                d for d in st.session_state.queued_documents if d["document_id"] != doc_id
                            ]
                            fetch_history.clear()
                            st.toast(f"Deleted {filename}", icon="✅")
                            st.rerun()
                        else:
                            st.error("Failed to delete document")

            # Page Thumbnails Grid
            if pages:
                with st.expander(f"View Page Thumbnails ({len(pages)} Pages)", expanded=False):
                    for page in pages:
                        p_num = page.get("page_number", 1)
                        raw_url = page.get("image_url")
                        proc_url = page.get("processed_image_url")
                        profile = page.get("applied_profile") or "Original"
                        quality = page.get("quality_label", "Pending")

                        st.markdown(f"**Page {p_num}** — Quality: `{quality}` | Profile: `{profile}`")
                        
                        c_raw, c_proc = st.columns(2)
                        with c_raw:
                            st.caption("🖼️ Raw Scan")
                            raw_bytes = fetch_image_bytes(raw_url)
                            if raw_bytes:
                                st.image(raw_bytes, width=180)
                            else:
                                st.info("Raw preview unavailable")

                        with c_proc:
                            st.caption("✨ Preprocessed")
                            if proc_url:
                                proc_bytes = fetch_image_bytes(proc_url)
                                if proc_bytes:
                                    st.image(proc_bytes, width=180)
                                else:
                                    st.info("Processed preview unavailable")
                            else:
                                st.caption("*(Not preprocessed yet)*")
                        st.divider()


if __name__ == "__main__":
    st.set_page_config(layout="wide")
    render_history_page()