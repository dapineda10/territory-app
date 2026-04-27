import os
import streamlit as st
from supabase import create_client, Client


def _get_credentials() -> tuple[str, str]:
    try:
        return st.secrets["supabase"]["url"], st.secrets["supabase"]["key"]
    except Exception:
        return os.environ["SUPABASE_URL"], os.environ["SUPABASE_KEY"]


@st.cache_resource
def get_supabase() -> Client:
    url, key = _get_credentials()
    return create_client(url, key)
