import streamlit as st
import requests
import os
from dotenv import load_dotenv
import pandas as pd

# Load environment variables
load_dotenv()

# Configure the app
st.set_page_config(
    page_title="Movie Recommender for Ammu",
    page_icon="🎬",
    layout="wide"
)

# Initialize session state for view management
if 'view' not in st.session_state:
    st.session_state.view = 'main'
if 'selected_movie' not in st.session_state:
    st.session_state.selected_movie = None

# TMDb API configuration
TMDB_API_KEY = os.getenv('TMDB_API_KEY')
OMDB_API_KEY = os.getenv('OMDB_API_KEY')
BASE_URL = "https://api.themoviedb.org/3"
POSTER_BASE_URL = "https://image.tmdb.org/t/p/w500"
PROFILE_BASE_URL = "https://image.tmdb.org/t/p/w185"

@st.cache_data
def get_movie_ratings(imdb_id):
    """Get IMDb and Rotten Tomatoes ratings using OMDB API"""
    if not OMDB_API_KEY:
        return None
    
    response = requests.get(
        f"http://www.omdbapi.com/?i={imdb_id}&apikey={OMDB_API_KEY}"
    )
    if response.ok:
        data = response.json()
        ratings = {}
        for rating in data.get('Ratings', []):
            if rating['Source'] == 'Internet Movie Database':
                ratings['imdb'] = rating['Value']
            elif rating['Source'] == 'Rotten Tomatoes':
                ratings['rotten_tomatoes'] = rating['Value']
        return ratings
    return None

def get_watch_providers(movie_id):
    """Get streaming platforms for the movie"""
    response = requests.get(
        f"{BASE_URL}/movie/{movie_id}/watch/providers",
        params={"api_key": TMDB_API_KEY}
    )
    if response.ok:
        data = response.json()
        # Get US streaming options
        us_data = data.get('results', {}).get('US', {})
        return {
            'stream': us_data.get('flatrate', []),
            'rent': us_data.get('rent', []),
            'buy': us_data.get('buy', [])
        }
    return None

def get_cast_details(movie_id):
    """Get cast details with profile images"""
    response = requests.get(
        f"{BASE_URL}/movie/{movie_id}/credits",
        params={"api_key": TMDB_API_KEY}
    )
    if response.ok:
        data = response.json()
        return [
            {
                'name': cast['name'],
                'character': cast['character'],
                'profile_path': f"{PROFILE_BASE_URL}{cast['profile_path']}" if cast['profile_path'] else None
            }
            for cast in data.get('cast', [])[:5]  # Get top 5 cast members
        ]
    return []

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
        return [], 0
    
    data = response.json()
    return data.get("results", []), data.get("total_pages", 1)

def show_movie_details(movie_id):
    """Display detailed movie information"""
    # Get basic movie details
    response = requests.get(
        f"{BASE_URL}/movie/{movie_id}",
        params={"api_key": TMDB_API_KEY, "language": "en-US"}
    )
    if not response.ok:
        st.error("Failed to fetch movie details")
        return
    
    movie = response.json()
    
    # Create two columns for layout
    col1, col2 = st.columns([1, 2])
    
    with col1:
        # Display poster
        if movie.get('poster_path'):
            st.image(f"{POSTER_BASE_URL}{movie['poster_path']}", use_column_width=True)
        else:
            st.image("https://via.placeholder.com/500x750?text=No+Poster", use_column_width=True)
    
    with col2:
        # Movie title and basic info
        st.title(movie['title'])
        if movie.get('tagline'):
            st.write(f"*{movie['tagline']}*")
        
        # Release date, runtime, and genres
        st.write(f"📅 Release Date: {movie.get('release_date', 'N/A')}")
        if movie.get('runtime'):
            st.write(f"⏱️ Runtime: {movie['runtime']} minutes")
        genres = ", ".join([genre['name'] for genre in movie.get('genres', [])])
        st.write(f"🎭 Genres: {genres}")
        
        # Ratings
        st.subheader("Ratings")
        ratings_col1, ratings_col2, ratings_col3 = st.columns(3)
        
        # TMDb Rating
        with ratings_col1:
            st.metric("TMDb", f"{movie['vote_average']:.1f}/10")
        
        # Get IMDb and Rotten Tomatoes ratings
        ext_ids_response = requests.get(
            f"{BASE_URL}/movie/{movie_id}/external_ids",
            params={"api_key": TMDB_API_KEY}
        )
        if ext_ids_response.ok:
            imdb_id = ext_ids_response.json().get('imdb_id')
            if imdb_id:
                ratings = get_movie_ratings(imdb_id)
                if ratings:
                    with ratings_col2:
                        st.metric("IMDb", ratings.get('imdb', 'N/A'))
                    with ratings_col3:
                        st.metric("Rotten Tomatoes", ratings.get('rotten_tomatoes', 'N/A'))
        
        # Overview
        st.subheader("Overview")
        st.write(movie.get('overview', 'No overview available.'))
    
    # Cast section
    st.subheader("Top Cast")
    cast = get_cast_details(movie_id)
    cast_cols = st.columns(5)
    for idx, member in enumerate(cast):
        with cast_cols[idx]:
            if member['profile_path']:
                st.image(member['profile_path'])
            else:
                st.image("https://via.placeholder.com/185x278?text=No+Photo")
            st.write(f"**{member['name']}**")
            st.write(f"*as {member['character']}*")
    
    # Where to watch section
    st.subheader("Where to Watch")
    providers = get_watch_providers(movie_id)
    if providers:
        watch_cols = st.columns(3)
        
        with watch_cols[0]:
            if providers['stream']:
                st.write("**🎬 Stream on:**")
                for provider in providers['stream']:
                    st.write(f"- {provider['provider_name']}")
        
        with watch_cols[1]:
            if providers['rent']:
                st.write("**💰 Rent on:**")
                for provider in providers['rent']:
                    st.write(f"- {provider['provider_name']}")
        
        with watch_cols[2]:
            if providers['buy']:
                st.write("**🛒 Buy on:**")
                for provider in providers['buy']:
                    st.write(f"- {provider['provider_name']}")
    else:
        st.write("No streaming information available.")
    
    # Back button
    if st.button("← Back to Movies"):
        st.session_state.view = 'main'
        st.rerun()

def show_main_view():
    """Display the main movie grid view"""
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
            # Make the poster clickable
            if poster_path:
                poster = f"{POSTER_BASE_URL}{poster_path}"
            else:
                poster = "https://via.placeholder.com/500x750?text=No+Poster"
            
            # Using a container to make the whole card clickable
            with st.container():
                st.image(poster, use_column_width=True)
                st.write(f"**{movie['title']}**")
                st.write(f"⭐ {movie['vote_average']:.1f}")
                if st.button("View Details", key=f"view_{movie['id']}"):
                    st.session_state.view = 'details'
                    st.session_state.selected_movie = movie['id']
                    st.rerun()

def main():
    if st.session_state.view == 'details':
        show_movie_details(st.session_state.selected_movie)
    else:
        show_main_view()

if __name__ == "__main__":
    main()
