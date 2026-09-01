import requests
import streamlit as st

API_BASE_URL = "http://127.0.0.1:8000/api/v1"

def get_auth_headers(is_json: bool = True) -> dict:
    """Retrieves Bearer token from session state for API authentication."""
    headers = {}
    token = st.session_state.get("access_token")
    if token:
        headers["Authorization"] = f"Bearer {token}"
    if is_json:
        headers["Content-Type"] = "application/json"
    return headers

def authenticate_user(endpoint: str, username: str, password: str) -> tuple[bool, dict | str]:
    """Issues login or registration requests to FastAPI auth endpoints."""
    url = f"{API_BASE_URL}{endpoint}"
    payload = {"username": username, "password": password}
    
    try:
        response = requests.post(url, json=payload, timeout=10)
        data = response.json()
        if response.ok:
            return True, data
        return False, data.get("detail", "Authentication failed.")
    except requests.RequestException as err:
        return False, f"Server connection error: {str(err)}"