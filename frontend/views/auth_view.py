import streamlit as st

from frontend.utils.api import authenticate_user

def apply_custom_theme():
    st.markdown("""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&display=swap');

        :root {
            --bg-dark: #07090e;
            --surface: rgba(18, 24, 38, 0.55);
            --surface-hover: rgba(24, 30, 48, 0.7);
            --border: rgba(255, 255, 255, 0.08);
            --border-hover: rgba(99, 102, 241, 0.6);
            --primary: #6366f1;
            --primary-hover: #4f46e5;
            --accent: #38bdf8;
            --text-main: #f8fafc;
            --text-muted: #a3b0c7;
        }

        /* Prevent Page Overflow */
        html, body, [class*="css"], .stApp {
            font-family: 'Plus Jakarta Sans', sans-serif !important;
            background-color: var(--bg-dark) !important;
            color: var(--text-main) !important;
            font-size: 17px !important;
            overflow: hidden !important;
        }
        
        /* Glassmorphic Sidebar — matches the same blur/saturate/gradient language as the rest of the app */
                section[data-testid="stSidebar"] {
                    background: rgba(9, 12, 20, 0.78) !important;
                    background-image: radial-gradient(circle at 30% 0%, rgba(99, 102, 241, 0.14) 0%, transparent 55%) !important;
                    backdrop-filter: blur(22px) saturate(150%) !important;
                    -webkit-backdrop-filter: blur(22px) saturate(150%) !important;
                    border-right: 1px solid var(--border) !important;
                }

        /* Ambient Background Grid + Soft Glow Blobs */
        .stApp {
            background-image: 
                radial-gradient(circle at 20% 15%, rgba(99, 102, 241, 0.16) 0%, transparent 45%),
                radial-gradient(circle at 82% 78%, rgba(56, 189, 248, 0.14) 0%, transparent 45%),
                linear-gradient(to right, rgba(255, 255, 255, 0.03) 1px, transparent 1px),
                linear-gradient(to bottom, rgba(255, 255, 255, 0.03) 1px, transparent 1px) !important;
            background-size: auto, auto, 40px 40px, 40px 40px !important;
        }

        /* Hide Default Header, Footer & Form Instructions */
        header[data-testid="stHeader"], 
        footer, 
        [data-testid="InputInstructions"] { 
            display: none !important; 
        }

        div[data-testid="stBlock"] {
            padding-top: 0rem !important;
        }

        /* Trim Streamlit's default page padding so everything fits in view */
        .main .block-container {
            padding-top: 1.5rem !important;
            padding-bottom: 0.5rem !important;
            max-width: 100% !important;
        }

        /* Tighten default vertical gaps between stacked widgets */
        div[data-testid="stVerticalBlock"] {
            gap: 0.6rem !important;
        }

        /* Card & Input Styles */
        div[data-testid="stForm"] {
            background: var(--surface) !important;
            backdrop-filter: blur(24px) saturate(150%) !important;
            -webkit-backdrop-filter: blur(24px) saturate(150%) !important;
            border: 1px solid var(--border) !important;
            border-radius: 18px !important;
            padding: 1.4rem 1.75rem !important;
            box-shadow:
                0 25px 50px -12px rgba(0, 0, 0, 0.75),
                inset 0 1px 0 rgba(255, 255, 255, 0.06) !important;
            position: relative !important;
        }

        /* Input Labels */
        div[data-testid="stForm"] label p {
            font-size: 0.95rem !important;
            font-weight: 500 !important;
            color: var(--text-muted) !important;
        }

        div[data-baseweb="input"] input {
            font-size: 1.05rem !important;
            outline: none !important;
            box-shadow: none !important;
        }

        /* Neutralize BaseWeb's default red invalid/focus border */
        div[data-baseweb="input"],
        div[data-baseweb="base-input"],
        div[data-baseweb="input"][aria-invalid="true"],
        div[data-baseweb="input"]:focus-within[aria-invalid="true"] {
            border-color: var(--border) !important;
        }

        /* Glassy Inputs with Glow-on-Click */
        div[data-baseweb="input"] {
            background: rgba(7, 9, 14, 0.55) !important;
            backdrop-filter: blur(8px) !important;
            border: 1px solid var(--border) !important;
            border-radius: 10px !important;
            outline: none !important;
            transition: border-color 0.25s ease, box-shadow 0.25s ease, background 0.25s ease !important;
        }

        div[data-baseweb="input"]:hover {
            border-color: rgba(255, 255, 255, 0.18) !important;
        }

        /* Glow behind the field when active/clicked — no colored border */
        div[data-baseweb="input"]:focus-within,
        div[data-baseweb="input"]:active,
        div[data-baseweb="input"]:focus {
            border-color: var(--border-hover) !important;
            background: rgba(7, 9, 14, 0.75) !important;
            outline: none !important;
            box-shadow:
                0 0 18px 4px rgba(99, 102, 241, 0.35),
                0 0 34px 10px rgba(56, 189, 248, 0.14) !important;
        }

        /* Form Button */
        div[data-testid="stForm"] div.stFormSubmitButton > button {
            width: 100% !important;
            padding: 0.85rem !important;
            background: linear-gradient(135deg, var(--primary) 0%, #4338ca 100%) !important;
            color: white !important;
            border: 1px solid rgba(255, 255, 255, 0.12) !important;
            border-radius: 10px !important;
            font-weight: 700 !important;
            font-size: 1.05rem !important;
            margin-top: 0.3rem !important;
            box-shadow: 0 10px 25px -8px rgba(99, 102, 241, 0.55) !important;
            transition: transform 0.15s ease, box-shadow 0.15s ease !important;
        }

        div[data-testid="stForm"] div.stFormSubmitButton > button:hover {
            transform: translateY(-1px) !important;
            box-shadow: 0 14px 30px -8px rgba(99, 102, 241, 0.7) !important;
        }

        /* Bottom Link Row */
        .auth-links-row {
            display: flex !important;
            align-items: center !important;
            justify-content: center !important;
            gap: 14px !important;
            margin-top: 0.4rem !important;
        }

        .auth-links-divider {
            width: 1px;
            height: 14px;
            background: rgba(255, 255, 255, 0.14);
        }

        /* Tertiary Link Buttons - centered & consistent */
        div.stButton {
            display: flex !important;
            justify-content: center !important;
        }

        div.stButton > button[kind="tertiary"],
        div.stButton > button[data-testid="stBaseButton-tertiary"] {
            background: none !important;
            border: none !important;
            color: var(--accent) !important;
            font-size: 0.9rem !important;
            font-weight: 600 !important;
            padding: 4px 6px !important;
            box-shadow: none !important;
            white-space: nowrap !important;
        }
        
        div.stButton > button[kind="tertiary"]:hover {
            color: var(--text-main) !important;
            text-decoration: underline !important;
        }

        .brand-accent { color: var(--primary); font-weight: 700; }
        .version-badge {
            background: rgba(99, 102, 241, 0.15);
            backdrop-filter: blur(6px);
            color: var(--accent);
            border: 1px solid rgba(56, 189, 248, 0.25);
            font-size: 0.75rem;
            padding: 3px 10px;
            border-radius: 12px;
            font-weight: 600;
        }
    </style>
    """, unsafe_allow_html=True)

def render_auth_page():
    apply_custom_theme()
    
    if "auth_mode" not in st.session_state:
        st.session_state.auth_mode = "login"

    is_login = st.session_state.auth_mode == "login"

    # Top Brand Header
    st.markdown("""
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.4rem;">
            <div style="display: flex; align-items: center; gap: 10px;">
                <span style="font-size: 1.4rem; color: #38bdf8;">📑</span>
                <span style="font-weight: 800; font-size: 1.3rem; color: #f8fafc;">
                    OCR <span class="brand-accent">Document Intelligence</span>
                </span>
                <span class="version-badge">v1</span>
            </div>
        </div>
    """, unsafe_allow_html=True)

    # Center Layout
    col1, col2, col3 = st.columns([1, 1.3, 1])
    
    with col2:
        icon_symbol = "🔐" if is_login else "📝"
        header_title = "Welcome Back" if is_login else "Create Account"
        header_sub = (
            "Multi-engine OCR platform utilizing dynamic preprocessing pipelines and parallel execution" 
            if is_login else 
            "Register an account to store and manage OCR history"
        )

        st.markdown(f"""
            <div style="text-align: center; margin-bottom: 0.6rem;">
                <div style="width: 38px; height: 38px; background: rgba(255, 255, 255, 0.05); 
                            backdrop-filter: blur(10px);
                            border: 1px solid rgba(255, 255, 255, 0.1); border-radius: 12px; 
                            display: inline-flex; align-items: center; justify-content: center; margin-bottom: 0.4rem;
                            box-shadow: 0 8px 20px -6px rgba(99, 102, 241, 0.4);">
                    <span style="font-size: 1.15rem;">{icon_symbol}</span>
                </div>
                <h3 style="font-size: 1.45rem; font-weight: 800; margin: 0; color: #f8fafc;">{header_title}</h3>
                <p style="color: #a3b0c7; font-size: 0.85rem; margin-top: 2px;">{header_sub}</p>
            </div>
        """, unsafe_allow_html=True)
        
        # Main Auth Card
        with st.form("auth_form", clear_on_submit=False):
            username = st.text_input("Username", placeholder="Enter your username")
            password = st.text_input("Password", type="password", placeholder="••••••••")
            
            submit_label = "Sign In" if is_login else "Register Account"
            submitted = st.form_submit_button(submit_label, use_container_width=True)
            
            if submitted:
                if not username.strip() or not password:
                    st.error("Please provide both a username and password.")
                else:
                    endpoint = "/auth/login" if is_login else "/auth/register"
                    success, result = authenticate_user(endpoint, username.strip(), password)
                    
                    if success:
                        if is_login:
                            st.session_state.authenticated = True
                            st.session_state.is_guest = False
                            st.session_state.username = result.get("username", username)
                            st.session_state.access_token = result.get("access_token") or result.get("token")
                            st.rerun()
                        else:
                            st.session_state.auth_mode = "login"
                            st.success("Account created! Please sign in.")
                            st.rerun()
                    else:
                        st.error(result)

        # Bottom Link Actions — single centered row, evenly balanced
        st.markdown('<div class="auth-links-row">', unsafe_allow_html=True)
        l_col, div_col, r_col = st.columns([1, 0.15, 1])

        with l_col:
            toggle_prompt = "New User? Register" if is_login else "Existing user? Sign In"
            if st.button(toggle_prompt, type="tertiary", use_container_width=True):
                st.session_state.auth_mode = "register" if is_login else "login"
                st.rerun()

        with div_col:
            st.markdown('<div class="auth-links-divider" style="margin: 8px auto 0;"></div>', unsafe_allow_html=True)

        with r_col:
            if st.button("Continue as Guest", type="tertiary", use_container_width=True):
                st.session_state.authenticated = True
                st.session_state.is_guest = True
                st.session_state.username = "Guest User"
                st.session_state.access_token = None
                st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)