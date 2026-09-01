import streamlit as st

def render_sidebar():
    """Renders the common sidebar elements for authenticated users."""
    st.sidebar.title("OCR Workspace")
    
    # User Profile Label
    user_label = f"👤 {st.session_state.username}"
    if st.session_state.is_guest:
        user_label += " (Guest)"
    st.sidebar.info(user_label)
    
    # Sign Out Action
    if st.sidebar.button("Sign Out", type="secondary"):
        st.session_state.authenticated = False
        st.session_state.is_guest = False
        st.session_state.username = None
        st.session_state.access_token = None
        st.rerun()

    st.sidebar.markdown("---")