import streamlit as st
from views.auth_view import render_auth_page
from views.sidebar_view import render_sidebar

# Configure Page Defaults
st.set_page_config(
    page_title="OCR Document Intelligence",
    page_icon="📄",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Initialize Authentication State Variables
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False
if "is_guest" not in st.session_state:
    st.session_state.is_guest = False
if "username" not in st.session_state:
    st.session_state.username = None
if "access_token" not in st.session_state:
    st.session_state.access_token = None

# Auth View Switcher
if not st.session_state.authenticated:
    render_auth_page()
else:
    # Render the dedicated sidebar component
    render_sidebar()
    
    # Page Route Setup via Navigation
    pages = {
        "Pipelines": [
            st.Page("views/ingestion_view.py", title="Document Ingestion", icon="📥"),
            st.Page("views/preprocessing_view.py", title="Preprocessing & Quality", icon="⚙️"),
        ]
    }
    
    # Restrict Document History in Guest Mode
    if not st.session_state.is_guest:
        pages["Pipelines"].append(st.Page("views/history_view.py", title="Document History", icon="📜"))

    pg = st.navigation(pages)
    pg.run()