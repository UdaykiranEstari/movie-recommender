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

def get_movie_details(movie_id):
    """Get detailed information about a movie including cast and external ratings."""
    # Get movie details
    response = requests.get(
        f"{BASE_URL}/movie/{movie_id}",
        params={"api_key": TMDB_API_KEY, "language": "en-US"}
    )
    if not response.ok:
        return None
    
    movie_details = response.json()
    
    # Get credits (cast information)
    credits_response = requests.get(
        f"{BASE_URL}/movie/{movie_id}/credits",
        params={"api_key": TMDB_API_KEY}
    )
    if credits_response.ok:
        credits = credits_response.json()
        # Get top 5 cast members
        movie_details['cast'] = credits.get('cast', [])[:5]
    
    # Get external IDs (for IMDb)
    ext_ids_response = requests.get(
        f"{BASE_URL}/movie/{movie_id}/external_ids",
        params={"api_key": TMDB_API_KEY}
    )
    if ext_ids_response.ok:
        movie_details['external_ids'] = ext_ids_response.json()
    
    return movie_details

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
            
            # Create expander for movie details
            with st.expander("More Info"):
                # Get detailed movie information
                movie_details = get_movie_details(movie['id'])
                if movie_details:
                    # Display external ratings if available
                    if 'external_ids' in movie_details and movie_details['external_ids'].get('imdb_id'):
                        imdb_id = movie_details['external_ids']['imdb_id']
                        st.write(f"🎬 [IMDb](https://www.imdb.com/title/{imdb_id})")
                    
                    # Display release date and runtime
                    release_date = movie_details.get('release_date', 'N/A')
                    runtime = movie_details.get('runtime', 0)
                    st.write(f"📅 Release Date: {release_date}")
                    if runtime:
                        st.write(f"⏱️ Runtime: {runtime} minutes")
                    
                    # Display genres
                    movie_genres = [genre['name'] for genre in movie_details.get('genres', [])]
                    if movie_genres:
                        st.write("🎭 Genres: " + ", ".join(movie_genres))
                    
                    # Display cast
                    if 'cast' in movie_details and movie_details['cast']:
                        st.write("👥 Cast:")
                        cast_text = ", ".join([actor['name'] for actor in movie_details['cast']])
                        st.write(cast_text)
                    
                    # Display overview
                    st.write("📝 Overview:")
                    st.write(movie_details.get('overview', 'No overview available.'))
                    
                    # Display additional information
                    col1, col2 = st.columns(2)
                    with col1:
                        st.write(f"💰 Budget: ${movie_details.get('budget', 0):,}")
                    with col2:
                        st.write(f"💵 Revenue: ${movie_details.get('revenue', 0):,}")
                    
                    # Display production companies
                    companies = [comp['name'] for comp in movie_details.get('production_companies', [])]
                    if companies:
                        st.write("🏢 Production: " + ", ".join(companies))

if __name__ == "__main__":
    main()
