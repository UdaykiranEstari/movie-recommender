import os
import streamlit as st
from dotenv import load_dotenv

# Load environment variables from .env file for local development
load_dotenv()

def get_api_keys():
    """Get API keys from either Streamlit secrets or environment variables"""
    # Try to get from Streamlit secrets first (for production/cloud)
    try:
        tmdb_key = st.secrets["TMDB_API_KEY"]
        omdb_key = st.secrets["OMDB_API_KEY"]
    except:
        # Fallback to environment variables (for local development)
        tmdb_key = os.getenv("TMDB_API_KEY")
        omdb_key = os.getenv("OMDB_API_KEY")
    
    if not tmdb_key or not omdb_key:
        st.error("API keys not found. Please check your configuration.")
        st.stop()
    
    return tmdb_key, omdb_key

# Constants
POSTER_BASE_URL = "https://image.tmdb.org/t/p/w500"
TMDB_BASE_URL = "https://api.themoviedb.org/3"
