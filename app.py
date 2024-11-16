import streamlit as st
import requests
import os
from dotenv import load_dotenv
import pandas as pd

# Load environment variables
load_dotenv()

# Configure the app
st.set_page_config(
    page_title="Movie Recommender",
    page_icon="🎬",
    layout="wide"
)

# TMDb API configuration
TMDB_API_KEY = os.getenv('TMDB_API_KEY')
BASE_URL = "https://api.themoviedb.org/3"
POSTER_BASE_URL = "https://image.tmdb.org/t/p/w500"

# Cache the genres
@st.cache_data
def get_genres():
    response = requests.get(
        f"{BASE_URL}/genre/movie/list",
        params={"api_key": TMDB_API_KEY, "language": "en-US"}
    )
    if not response.ok:
        st.error(f"Error fetching genres: {response.status_code} - {response.text}")
        return {}
    
    json_response = response.json()
    if "genres" not in json_response:
        st.error(f"Unexpected API response: {json_response}")
        return {}
        
    return {genre["id"]: genre["name"] for genre in json_response["genres"]}

def get_recommendations(genre_id=None, page=1):
    params = {
        "api_key": TMDB_API_KEY,
        "language": "en-US",
        "sort_by": "popularity.desc",
        "include_adult": False,
        "page": page
    }
    
    if genre_id:
        params["with_genres"] = genre_id
    
    response = requests.get(f"{BASE_URL}/discover/movie", params=params)
    if not response.ok:
        st.error(f"Error fetching recommendations: {response.status_code} - {response.text}")
        return []
    
    data = response.json()
    return data.get("results", []), data.get("total_pages", 1)

def main():
    st.title("🎬 Movie Recommender")
    st.write("Discover movies based on genres!")

    # Get genres for the filter
    genres = get_genres()
    
    # Create genre filter
    selected_genre = st.selectbox(
        "Select a genre",
        options=[("", "All Genres")] + [(id, name) for id, name in genres.items()],
        format_func=lambda x: x[1]
    )

    # Get the genre ID from the selection
    genre_id = selected_genre[0] if selected_genre else None
    
    # Add pagination
    page = st.number_input("Page", min_value=1, value=1)
    
    # Get movie recommendations
    movies, total_pages = get_recommendations(genre_id=genre_id, page=page)
    
    st.write(f"Page {page} of {total_pages}")
    
    # Display movies in a grid
    cols = st.columns(4)
    for idx, movie in enumerate(movies):
        with cols[idx % 4]:
            poster_path = movie.get("poster_path")
            if poster_path:
                st.image(
                    f"{POSTER_BASE_URL}{poster_path}",
                    caption=movie["title"],
                    use_column_width=True
                )
            else:
                st.image(
                    "https://via.placeholder.com/500x750?text=No+Poster",
                    caption=movie["title"],
                    use_column_width=True
                )
            st.write(f"⭐ {movie['vote_average']:.1f}")
            with st.expander("Overview"):
                st.write(movie["overview"])

if __name__ == "__main__":
    main()
