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
            for cast in data.get('cast', [])[:10]  # Get top 10 cast members
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

def search_movies(query, page=1):
    """Search for movies by title"""
    response = requests.get(
        f"{BASE_URL}/search/movie",
        params={
            "api_key": TMDB_API_KEY,
            "query": query,
            "page": page,
            "language": "en-US"
        }
    )
    if response.ok:
        data = response.json()
        return data.get('results', []), data.get('total_pages', 0)
    return [], 0

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
    
    # Create two columns for layout with better ratio
    col1, col2 = st.columns([1, 2], gap="large")
    
    with col1:
        # Display poster with consistent width
        if movie.get('poster_path'):
            st.image(f"{POSTER_BASE_URL}{movie['poster_path']}", use_column_width=True)
        else:
            st.image("https://via.placeholder.com/500x750?text=No+Poster", use_column_width=True)
    
    with col2:
        # Movie title and basic info
        st.title(movie['title'])
        if movie.get('tagline'):
            st.markdown(f"*{movie['tagline']}*")
        
        # Release date, runtime, and genres
        st.write(f"📅 Release Date: {movie.get('release_date', 'N/A')}")
        if movie.get('runtime'):
            st.write(f"⏱️ Runtime: {movie['runtime']} minutes")
        genres = ", ".join([genre['name'] for genre in movie.get('genres', [])])
        st.write(f"🎭 Genres: {genres}")
        
        # Overview
        st.subheader("📝 Overview")
        st.write(movie.get('overview', 'No overview available.'))
        
        # Additional movie info
        if movie.get('budget'):
            st.write(f"💰 Budget: ${movie['budget']:,}")
        if movie.get('revenue'):
            st.write(f"💵 Revenue: ${movie['revenue']:,}")
        
        # Ratings
        st.subheader("⭐ Ratings")
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
    
    # Cast section
    st.markdown("### 👥 Top Cast")
    cast = get_cast_details(movie_id)
    
    # First row of cast
    cast_row1 = st.columns(5)
    for idx, member in enumerate(cast[:5]):
        with cast_row1[idx]:
            if member['profile_path']:
                st.image(member['profile_path'])
            else:
                st.image("https://via.placeholder.com/185x278?text=No+Photo")
            st.markdown(f"**{member['name']}**")
            st.markdown(f"*as {member['character']}*")
    
    # Second row of cast
    if len(cast) > 5:
        cast_row2 = st.columns(5)
        for idx, member in enumerate(cast[5:10]):
            with cast_row2[idx]:
                if member['profile_path']:
                    st.image(member['profile_path'])
                else:
                    st.image("https://via.placeholder.com/185x278?text=No+Photo")
                st.markdown(f"**{member['name']}**")
                st.markdown(f"*as {member['character']}*")
    
    # Where to watch section
    st.markdown("### 🎬 Where to Watch")
    providers = get_watch_providers(movie_id)
    if providers:
        watch_cols = st.columns(3)
        
        with watch_cols[0]:
            if providers['stream']:
                st.markdown("**Stream on:**")
                for provider in providers['stream']:
                    st.write(f"- {provider['provider_name']}")
        
        with watch_cols[1]:
            if providers['rent']:
                st.markdown("**Rent on:**")
                for provider in providers['rent']:
                    st.write(f"- {provider['provider_name']}")
        
        with watch_cols[2]:
            if providers['buy']:
                st.markdown("**Buy on:**")
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
    st.title("🎬 Movie Recommender for Ammu")
    st.write("Discover movies based on genres!")

    # Add CSS for consistent movie card heights
    st.markdown("""
        <style>
        .movie-card {
            display: flex;
            flex-direction: column;
            height: 100%;
            padding: 10px;
            box-sizing: border-box;
        }
        .movie-poster {
            aspect-ratio: 2/3;
            width: 100%;
            object-fit: cover;
            border-radius: 5px;
        }
        .movie-info {
            padding: 10px 0;
        }
        </style>
    """, unsafe_allow_html=True)
    
    # Create two columns for search and genre filter
    search_col, genre_col = st.columns([2, 1])
    
    with search_col:
        search_query = st.text_input("🔍 Search movies...", key="search_input")
    
    with genre_col:
        # Get genres for the filter
        genres = get_genres()
        selected_genre = st.selectbox(
            "Select a genre",
            options=[("", "All Genres")] + [(id, name) for id, name in genres.items()],
            format_func=lambda x: x[1]
        )

    # Get the genre ID from the selection
    genre_id = selected_genre[0] if selected_genre else None
    
    # Add pagination
    page = st.number_input("Page", min_value=1, value=1)
    
    # Show loading spinner while fetching data
    with st.spinner("Loading movies..."):
        if search_query:
            movies, total_pages = search_movies(search_query, page)
        else:
            movies, total_pages = get_recommendations(genre_id=genre_id, page=page)
    
    if not movies:
        st.info("No movies found. Try a different search or genre!")
        return
        
    st.write(f"Page {page} of {total_pages}")
    
    # Display movies in a grid
    cols = st.columns(4)
    for idx, movie in enumerate(movies):
        with cols[idx % 4]:
            poster_path = movie.get("poster_path")
            
            # Create a container with consistent height
            st.markdown('<div class="movie-card">', unsafe_allow_html=True)
            
            # Display poster
            if poster_path:
                st.markdown(
                    f'<img src="{POSTER_BASE_URL}{poster_path}" class="movie-poster">',
                    unsafe_allow_html=True
                )
            else:
                st.markdown(
                    '<img src="https://via.placeholder.com/500x750?text=No+Poster" class="movie-poster">',
                    unsafe_allow_html=True
                )
            
            # Movie info section
            st.markdown('<div class="movie-info">', unsafe_allow_html=True)
            st.markdown(f"**{movie['title']}**")
            st.write(f"⭐ {movie['vote_average']:.1f}")
            
            # More Info button
            if st.button("More Info", key=f"movie_{movie['id']}", use_container_width=True):
                st.session_state.view = 'details'
                st.session_state.selected_movie = movie['id']
                st.rerun()
            
            st.markdown('</div></div>', unsafe_allow_html=True)

def main():
    if st.session_state.view == 'details':
        show_movie_details(st.session_state.selected_movie)
    else:
        show_main_view()

if __name__ == "__main__":
    main()
