import streamlit as st
import requests
import io

# --- CONFIGURATION ---
API_BASE_URL = "http://127.0.0.1:8000/api/v1"
ALLOWED_EXTENSIONS = ["jpg", "jpeg", "png", "pdf"]
MAX_FILE_SIZE_MB = 10
MAX_BATCH_SIZE = 10

# Placeholder nav map — wire real routing/click handlers in once page-switching lands.
NAV_ITEMS = [
    {"icon": "📤", "label": "Document Ingestion"},
    {"icon": "⚙️", "label": "Quality Preprocessing"},
    {"icon": "🔍", "label": "Engine Results"},
    {"icon": "📚", "label": "History Vault"},
]

# Colorized file-type tag styling, keyed by lowercased extension.
FILE_TYPE_STYLES = {
    "pdf": {"color": "#fb923c", "bg": "rgba(251, 146, 60, 0.14)", "border": "rgba(251, 146, 60, 0.35)"},
    "jpg": {"color": "#38bdf8", "bg": "rgba(56, 189, 248, 0.14)", "border": "rgba(56, 189, 248, 0.35)"},
    "jpeg": {"color": "#38bdf8", "bg": "rgba(56, 189, 248, 0.14)", "border": "rgba(56, 189, 248, 0.35)"},
    "png": {"color": "#34d399", "bg": "rgba(52, 211, 153, 0.14)", "border": "rgba(52, 211, 153, 0.35)"},
    "default": {"color": "#a3b0c7", "bg": "rgba(255, 255, 255, 0.05)", "border": "rgba(255, 255, 255, 0.14)"},
}


def apply_custom_theme():
    """Injects global CSS for dark glassmorphism, gradient highlights, and component styling."""
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
        }

        html, body, [class*="css"], .stApp {
            font-family: 'Plus Jakarta Sans', sans-serif !important;
            background-color: var(--bg-dark) !important;
            color: var(--text-main) !important;
        }

        /* Ambient Gradient Highlights + Grid — actual light sources, not a flat fill */
        .stApp {
            background-image:
                radial-gradient(circle at 15% 10%, rgba(99, 102, 241, 0.18) 0%, transparent 42%),
                radial-gradient(circle at 85% 85%, rgba(56, 189, 248, 0.14) 0%, transparent 45%),
                radial-gradient(circle at 85% 5%, rgba(52, 211, 153, 0.08) 0%, transparent 35%),
                linear-gradient(to right, rgba(255, 255, 255, 0.03) 1px, transparent 1px),
                linear-gradient(to bottom, rgba(255, 255, 255, 0.03) 1px, transparent 1px) !important;
            background-size: auto, auto, auto, 40px 40px, 40px 40px !important;
        }

        /* Glassmorphic Sidebar — matches the same blur/saturate/gradient language as the rest of the app */
        section[data-testid="stSidebar"] {
            background: rgba(9, 12, 20, 0.78) !important;
            background-image: radial-gradient(circle at 30% 0%, rgba(99, 102, 241, 0.14) 0%, transparent 55%) !important;
            backdrop-filter: blur(22px) saturate(150%) !important;
            -webkit-backdrop-filter: blur(22px) saturate(150%) !important;
            border-right: 1px solid var(--border) !important;
        }

        
        .nav-item:hover {
            background: rgba(255, 255, 255, 0.06);
            border-color: var(--border);
        }
        .nav-item.active {
            background: rgba(99, 102, 241, 0.15);
            color: #eef0ff;
            border: 1px solid rgba(99, 102, 241, 0.35);
            font-weight: 600;
            box-shadow: 0 0 20px 2px rgba(99, 102, 241, 0.18);
        }

        /* Dropzone Styling */
        div[data-testid="stFileUploader"] {
            background: var(--surface) !important;
            background-image: radial-gradient(circle at 25% 20%, rgba(99, 102, 241, 0.12) 0%, transparent 55%) !important;
            backdrop-filter: blur(22px) saturate(150%) !important;
            -webkit-backdrop-filter: blur(22px) saturate(150%) !important;
            border: 2px dashed var(--border) !important;
            border-radius: 16px !important;
            padding: 20px !important;
            transition: border-color 0.2s ease !important;
        }
        div[data-testid="stFileUploader"]:hover {
            border-color: var(--border-hover) !important;
        }

        /* Hide ONLY the file list container below the dropzone.
           Leaves section[data-testid="stFileUploaderDropzone"] and the Browse button visible. */
        div[data-testid="stFileUploader"] [data-testid="stFileUploaderFileLayout"],
        div[data-testid="stFileUploader"] [data-testid*="FileLayout"],
        div[data-testid="stFileUploader"] ul {
            display: none !important;
        }

        /* Queue Card Container styling for Streamlit Columns */
        div[data-testid="stHorizontalBlock"]:has(> div[data-testid="stColumn"] div[data-testid="stImage"]) {
            background: var(--surface-soft);
            backdrop-filter: blur(10px);
            border: 1px solid var(--border);
            border-radius: 12px;
            padding: 8px 10px;
            align-items: center;
            transition: border-color 0.2s ease, background 0.2s ease;
        }
        div[data-testid="stHorizontalBlock"]:has(> div[data-testid="stColumn"] div[data-testid="stImage"]):hover {
            border-color: rgba(255, 255, 255, 0.16);
            background: rgba(255, 255, 255, 0.035);
        }

        /* Small, uniform, cropped thumbnails */
        div[data-testid="stImage"] img {
            width: 44px !important;
            height: 44px !important;
            object-fit: cover !important;
            border-radius: 8px !important;
            border: 1px solid var(--border) !important;
        }

        /* Buttons Styling */
        div.stButton > button[kind="primary"] {
            width: 100% !important;
            background: linear-gradient(135deg, var(--primary) 0%, #4338ca 100%) !important;
            color: white !important;
            border: 1px solid rgba(255, 255, 255, 0.12) !important;
            border-radius: 8px !important;
            font-weight: 600 !important;
            box-shadow: 0 10px 25px -10px rgba(99, 102, 241, 0.6) !important;
        }

        /* Secondary/Delete Button */
        div.stButton > button[kind="secondary"] {
            background: rgba(239, 68, 68, 0.1) !important;
            border: 1px solid rgba(239, 68, 68, 0.3) !important;
            color: var(--danger) !important;
        }
        div.stButton > button[kind="secondary"]:hover {
            background: rgba(239, 68, 68, 0.2) !important;
        }

        /* Top-right "Clear All" ghost button */
        div.stButton > button[kind="tertiary"] {
            background: rgba(255, 255, 255, 0.04) !important;
            border: 1px solid var(--border) !important;
            color: var(--text-muted) !important;
            font-weight: 500 !important;
            font-size: 0.85rem !important;
        }
        div.stButton > button[kind="tertiary"]:hover {
            color: var(--text-main) !important;
            border-color: rgba(239, 68, 68, 0.4) !important;
        }

        .badge-format {
            padding: 2px 9px;
            border-radius: 12px;
            font-size: 0.72rem;
            font-weight: 600;
            border: 1px solid;
            text-transform: uppercase;
            letter-spacing: 0.02em;
        }
    </style>
    """, unsafe_allow_html=True)





def render_type_badge(file_type: str) -> str:
    """Returns a colorized HTML tag for a file extension/type."""
    key = (file_type or "").lower().lstrip(".")
    style = FILE_TYPE_STYLES.get(key, FILE_TYPE_STYLES["default"])
    return (
        f'<span class="badge-format" style="color:{style["color"]}; '
        f'background:{style["bg"]}; border-color:{style["border"]};">{key}</span>'
    )


def upload_to_backend(file):
    """Executes POST /upload and returns the document schema."""
    user_id = st.session_state.get("username", None)
    params = {"user_id": user_id} if user_id != "Guest User" else {}
    
    files = {"file": (file.name, file.getvalue(), file.type)}
    response = requests.post(f"{API_BASE_URL}/documents/upload", files=files, params=params)
    
    if response.status_code == 201:
        return response.json()
    else:
        st.error(f"Failed to upload {file.name}: {response.text}")
        return None

def delete_from_backend(document_id):
    """Executes DELETE /documents/{document_id} to clear storage."""
    response = requests.delete(f"{API_BASE_URL}/documents/{document_id}")
    if response.status_code != 200:
        st.error("Failed to delete document from backend.")

def render_ingestion_page():
    apply_custom_theme()
    
    
    if "queued_documents" not in st.session_state:
        st.session_state.queued_documents = []
    # Tracks (filename, size) pairs already handed to the backend, so a file the user
    # removed from the Batch Queue doesn't silently get re-added — the file_uploader
    # widget keeps returning every file it's holding on every rerun, not just new ones.
    if "seen_upload_keys" not in st.session_state:
        st.session_state.seen_upload_keys = set()
    # Bumped on "Clear All" to remount the uploader with a fresh key, fully detaching
    # it from any previously selected files instead of just hiding them.
    if "uploader_key" not in st.session_state:
        st.session_state.uploader_key = 0

    st.markdown("## Document Ingestion")
    st.caption("Upload batch documents for multi-engine OCR extraction and dynamic preprocessing.")
    st.markdown("<br>", unsafe_allow_html=True)

    queue = st.session_state.queued_documents
    col_left, col_right = st.columns([1, 1.4], gap="large")

    # --- Left: Drag & Drop Zone ---
    with col_left:
        uploaded_files = st.file_uploader(
            "Drop files here to upload to database & storage",
            type=ALLOWED_EXTENSIONS,
            accept_multiple_files=True,
            key=f"file_uploader_{st.session_state.uploader_key}",
        )

        if uploaded_files:
            new_files = [
                f for f in uploaded_files
                if (f.name, f.size) not in st.session_state.seen_upload_keys
            ]
            
            if new_files:
                current_count = len(st.session_state.queued_documents)
                if current_count + len(new_files) > MAX_BATCH_SIZE:
                    st.error(f"Cannot exceed maximum batch limit of {MAX_BATCH_SIZE} files.")
                    # Prevent widget from constantly re-triggering this error
                    st.session_state.seen_upload_keys.update([(f.name, f.size) for f in new_files])
                else:
                    success = False
                    for file in new_files:
                        size_mb = file.size / (1024 * 1024)
                        if size_mb > MAX_FILE_SIZE_MB:
                            st.error(f"'{file.name}' exceeds {MAX_FILE_SIZE_MB}MB limit.")
                            st.session_state.seen_upload_keys.add((file.name, file.size))
                            continue

                        with st.spinner(f"Uploading {file.name}..."):
                            doc_data = upload_to_backend(file)
                            st.session_state.seen_upload_keys.add((file.name, file.size))
                            if doc_data:
                                doc_data["size"] = file.size
                                doc_data["size_mb"] = size_mb
                                st.session_state.queued_documents.append(doc_data)
                                success = True
                    
                    # If at least one file succeeded, unmount the uploader to clear its internal cache
                    if success:
                        st.session_state.uploader_key += 1
                        st.rerun()
            current_count = len(st.session_state.queued_documents)
            if current_count + len(new_files) > MAX_BATCH_SIZE:
                st.error(f"Cannot exceed maximum batch limit of {MAX_BATCH_SIZE} files.")
            else:
                for file in new_files:
                    size_mb = file.size / (1024 * 1024)
                    if size_mb > MAX_FILE_SIZE_MB:
                        st.error(f"'{file.name}' exceeds {MAX_FILE_SIZE_MB}MB limit.")
                        st.session_state.seen_upload_keys.add((file.name, file.size))
                        continue

                    with st.spinner(f"Uploading {file.name}..."):
                        doc_data = upload_to_backend(file)
                        st.session_state.seen_upload_keys.add((file.name, file.size))
                        if doc_data:
                            # Append custom frontend tracking fields to backend response schema
                            doc_data["size"] = file.size
                            doc_data["size_mb"] = size_mb
                            st.session_state.queued_documents.append(doc_data)
                            queue = st.session_state.queued_documents

        st.caption(f"Max {MAX_BATCH_SIZE} files per batch • {MAX_FILE_SIZE_MB}MB per file")

    # --- Right: Queue List ---
    with col_right:
        col_header, col_action = st.columns([3, 1])
        with col_header:
            st.markdown(f"#### Batch Queue ({len(queue)}/{MAX_BATCH_SIZE})")
        with col_action:
            if st.button("🗑 Clear All", type="tertiary", disabled=len(queue) == 0, use_container_width=True):
                for doc in queue:
                    delete_from_backend(doc['document_id'])
                st.session_state.queued_documents = []
                st.session_state.seen_upload_keys = set()
                st.session_state.uploader_key += 1  # remounts file_uploader, fully detached
                st.rerun()

        if not queue:
            st.info("📁 No documents queued for processing. Upload files to begin.")
        else:
            for idx, doc in enumerate(queue):
                col_thumb, col_info, col_del = st.columns([0.6, 3.4, 1])

                # Thumbnail Fetching
                with col_thumb:
                    try:
                        thumb_res = requests.get(f"{API_BASE_URL}/documents/{doc['document_id']}/pages/1/image")
                        if thumb_res.status_code == 200:
                            st.image(io.BytesIO(thumb_res.content), width=44)
                        else:
                            st.markdown("📄")
                    except Exception:
                        st.markdown("📄")

                # Document Metadata Details
                with col_info:
                    st.markdown(f"**{doc['filename']}**")
                    st.markdown(f"""
                        {render_type_badge(doc['file_type'])}
                        <span style="color: var(--text-muted); font-size: 0.85rem; margin-left: 8px;">
                            {doc.get('size_mb', 0):.2f} MB • {doc.get('page_count', 1)} Pages
                        </span>
                    """, unsafe_allow_html=True)

                # Deletion Action
                with col_del:
                    if st.button("✖", key=f"del_{doc['document_id']}", type="secondary", use_container_width=True):
                        delete_from_backend(doc['document_id'])
                        
                        # Remove from tracking set so the user can re-upload this exact file
                        file_key = (doc['filename'], doc.get('size', 0))
                        if file_key in st.session_state.seen_upload_keys:
                            st.session_state.seen_upload_keys.remove(file_key)
                            
                        st.session_state.queued_documents.pop(idx)
                        st.rerun()

        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("Proceed to Preprocessing", type="primary", disabled=len(queue) == 0, use_container_width=True):
            st.switch_page("views/preprocessing_view.py")

if __name__ == "__main__":
    st.set_page_config(layout="wide", initial_sidebar_state="expanded")
    render_ingestion_page()