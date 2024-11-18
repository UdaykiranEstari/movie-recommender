import streamlit as st
import requests
import pandas as pd
from datetime import datetime
import streamlit.components.v1 as components

# Configure the app
st.set_page_config(
    page_title="Movie Recommender",
    page_icon="🎬",
    layout="wide"
)

# Initialize session state
if 'view' not in st.session_state:
    st.session_state.view = 'search'
if 'selected_movie' not in st.session_state:
    st.session_state.selected_movie = None
if 'content_type' not in st.session_state:
    st.session_state.content_type = 'Movies'
if 'filter_rating' not in st.session_state:
    st.session_state.filter_rating = 0.0
if 'temp_rating' not in st.session_state:
    st.session_state.temp_rating = 0.0

# TMDb API configuration
try:
    TMDB_API_KEY = st.secrets["TMDB_API_KEY"]
    OMDB_API_KEY = st.secrets["OMDB_API_KEY"]
except Exception as e:
    st.error(f"Error loading API keys: {str(e)}")
    st.stop()

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

def get_tv_genres():
    """Get TV show genres"""
    response = requests.get(
        f"{BASE_URL}/genre/tv/list",
        params={"api_key": TMDB_API_KEY, "language": "en-US"}
    )
    if response.ok:
        return {str(genre['id']): genre['name'] 
                for genre in response.json().get('genres', [])}
    return {}

def get_recommendations(genre_id=None, page=1):
    """Get movie recommendations"""
    params = {
        'api_key': TMDB_API_KEY,
        'language': 'en-US',
        'page': page,
        'sort_by': 'primary_release_date.desc',  # Sort by release date, newest first
        'include_adult': False,
        'vote_count.gte': 50  # Lower threshold to get more movies
    }
    
    # Add vote average filter if set
    if hasattr(st.session_state, 'filter_rating') and st.session_state.filter_rating > 0:
        params['vote_average.gte'] = st.session_state.filter_rating
        params['vote_count.gte'] = 20  # Lower threshold when using rating filter
    
    if genre_id:
        params['with_genres'] = genre_id
        
    response = requests.get(f"{BASE_URL}/discover/movie", params=params)
    if response.ok:
        data = response.json()
        return data.get('results', []), data.get('total_pages', 0)
    return [], 0

def get_tv_shows(genre_id=None, page=1):
    """Get TV show recommendations"""
    params = {
        'api_key': TMDB_API_KEY,
        'language': 'en-US',
        'page': page,
        'sort_by': 'first_air_date.desc',  # Sort by first air date, newest first
        'include_null_first_air_dates': False,  # Exclude shows without air dates
        'vote_count.gte': 50  # Lower threshold to get more shows
    }
    
    # Add vote average filter if set
    if hasattr(st.session_state, 'filter_rating') and st.session_state.filter_rating > 0:
        params['vote_average.gte'] = st.session_state.filter_rating
        params['vote_count.gte'] = 20  # Lower threshold when filtering by rating
    
    if genre_id:
        params['with_genres'] = genre_id
        
    response = requests.get(f"{BASE_URL}/discover/tv", params=params)
    if response.ok:
        data = response.json()
        return data.get('results', []), data.get('total_pages', 0)
    return [], 0

def search_content(query, page=1, content_type='movie'):
    """Search for movies or TV shows"""
    params = {
        'api_key': TMDB_API_KEY,
        'language': 'en-US',
        'query': query,
        'page': page,
        'include_adult': False,
        'vote_count.gte': 20,  # Add minimum vote count for search results
        'sort_by': 'primary_release_date.desc' if content_type == 'movie' else 'first_air_date.desc'
    }
    
    # Add vote average filter if set
    if hasattr(st.session_state, 'filter_rating') and st.session_state.filter_rating > 0:
        params['vote_average.gte'] = st.session_state.filter_rating
    
    response = requests.get(f"{BASE_URL}/search/{content_type}", params=params)
    if response.ok:
        data = response.json()
        return data.get('results', []), data.get('total_pages', 0)
    return [], 0

def get_movie_trailer(movie_id):
    """Get the official trailer or teaser for a movie"""
    response = requests.get(
        f"{BASE_URL}/movie/{movie_id}/videos",
        params={"api_key": TMDB_API_KEY, "language": "en-US"}
    )
    
    if not response.ok:
        return None
        
    videos = response.json().get("results", [])
    
    # First try to find the official trailer
    trailer = next(
        (video for video in videos 
         if video["site"] == "YouTube" and 
         video["type"] == "Trailer" and 
         "official" in video["name"].lower()),
        None
    )
    
    # If no official trailer, try any trailer
    if not trailer:
        trailer = next(
            (video for video in videos 
             if video["site"] == "YouTube" and 
             video["type"] == "Trailer"),
            None
        )
    
    # If still no trailer, try a teaser
    if not trailer:
        trailer = next(
            (video for video in videos 
             if video["site"] == "YouTube" and 
             video["type"] == "Teaser"),
            None
        )
    
    return trailer

def get_tv_trailer(tv_id):
    """Get the official trailer for a TV show"""
    response = requests.get(
        f"{BASE_URL}/tv/{tv_id}/videos",
        params={"api_key": TMDB_API_KEY, "language": "en-US"}
    )
    
    if not response.ok:
        return None
        
    videos = response.json().get("results", [])
    
    # First try to find the official trailer
    trailer = next(
        (video for video in videos 
         if video["site"] == "YouTube" and 
         video["type"] == "Trailer" and 
         "official" in video["name"].lower()),
        None
    )
    
    # If no official trailer, try any trailer
    if not trailer:
        trailer = next(
            (video for video in videos 
             if video["site"] == "YouTube" and 
             video["type"] == "Trailer"),
            None
        )
    
    return trailer

def get_similar_movies(movie_id):
    """Get similar movies recommendations"""
    response = requests.get(
        f"{BASE_URL}/movie/{movie_id}/similar",
        params={"api_key": TMDB_API_KEY, "language": "en-US", "page": 1}
    )
    
    if response.ok:
        data = response.json()
        return data.get("results", [])[:5]  # Get exactly 5 similar movies
    return []

def get_tv_details(tv_id):
    """Get TV show details including cast and similar shows"""
    response = requests.get(
        f"{BASE_URL}/tv/{tv_id}",
        params={"api_key": TMDB_API_KEY, "language": "en-US", "append_to_response": "credits,videos,similar"}
    )
    if response.ok:
        return response.json()
    return None

def get_movie_details(movie_id):
    """Get movie details"""
    response = requests.get(
        f"{BASE_URL}/movie/{movie_id}",
        params={"api_key": TMDB_API_KEY, "language": "en-US", "append_to_response": "credits"}
    )
    if response.ok:
        return response.json()
    return None

def get_omdb_ratings(title, year=None):
    """Get OMDB ratings"""
    params = {
        "apikey": OMDB_API_KEY,
        "t": title
    }
    if year:
        params["y"] = year
    
    response = requests.get("http://www.omdbapi.com/", params=params)
    if response.ok:
        return response.json()
    return None

def display_ratings(tmdb_rating, imdb_rating=None, rt_rating=None):
    """Display ratings in a single row with 3 columns"""
    st.markdown("""
        <style>
        .rating-container {
            display: flex;
            flex-direction: row;
            justify-content: flex-start;
            align-items: center;
            gap: 20px;
            margin: 10px 0;
        }
        .rating-item {
            display: flex;
            align-items: center;
            gap: 5px;
            padding: 5px 10px;
            border-radius: 4px;
            background-color: rgba(128, 128, 128, 0.1);
        }
        .rating-source {
            font-weight: bold;
            margin-right: 5px;
        }
        </style>
    """, unsafe_allow_html=True)
    
    # Create columns for ratings
    col1, col2, col3 = st.columns(3)
    
    # TMDb Rating
    with col1:
        if tmdb_rating:
            st.markdown(f"""
                <div class="rating-item">
                    <span class="rating-source">TMDb:</span>
                    <span>{tmdb_rating}/10</span>
                </div>
            """, unsafe_allow_html=True)
    
    # IMDb Rating
    with col2:
        if imdb_rating:
            st.markdown(f"""
                <div class="rating-item">
                    <span class="rating-source">IMDb:</span>
                    <span>{imdb_rating}</span>
                </div>
            """, unsafe_allow_html=True)
    
    # Rotten Tomatoes Rating
    with col3:
        if rt_rating:
            st.markdown(f"""
                <div class="rating-item">
                    <span class="rating-source">Rotten Tomatoes:</span>
                    <span>{rt_rating}</span>
                </div>
            """, unsafe_allow_html=True)

def show_movie_details(item_id):
    """Display detailed movie or TV show information"""
    content_type = 'movie' if st.session_state.filter_content_type == "Movies" else 'tv'
    
    # Get content details
    if content_type == 'movie':
        response = requests.get(
            f"{BASE_URL}/movie/{item_id}",
            params={"api_key": TMDB_API_KEY, "language": "en-US", "append_to_response": "credits"}
        )
        if not response.ok:
            st.error("Failed to fetch movie details")
            return
        item = response.json()
        title = item['title']
        release_date = item.get('release_date', 'N/A')
        duration = f"⏱️ Runtime: {item.get('runtime')} minutes" if item.get('runtime') else None
    else:
        item = get_tv_details(item_id)
        if not item:
            st.error("Failed to fetch TV show details")
            return
        title = item['name']
        release_date = item.get('first_air_date', 'N/A')
        duration = f"⏱️ Episodes: {item.get('number_of_episodes')} ({item.get('number_of_seasons')} seasons)" if item.get('number_of_episodes') else None
    
    # Create two columns for layout
    col1, col2 = st.columns([1, 2], gap="large")
    
    with col1:
        # Display poster
        if item.get('poster_path'):
            st.image(f"{POSTER_BASE_URL}{item['poster_path']}", use_column_width=True)
        else:
            st.image("https://via.placeholder.com/500x750?text=No+Poster", use_column_width=True)
    
    with col2:
        # Title and basic info
        st.title(title)
        if item.get('tagline'):
            st.markdown(f"*{item['tagline']}*")
        
        # Release date and duration
        st.write(f"📅 Release Date: {release_date}")
        if duration:
            st.write(duration)
        
        # Genres
        genres = ", ".join([genre['name'] for genre in item.get('genres', [])])
        st.write(f"🎭 Genres: {genres}")
        
        # Overview
        st.subheader("📝 Overview")
        st.write(item.get('overview', 'No overview available.'))
        
        # Ratings
        st.subheader("⭐ Ratings")
        
        # Create three columns for ratings
        rating_col1, rating_col2, rating_col3 = st.columns(3)
        
        with rating_col1:
            if item.get('vote_average'):
                st.metric("TMDb", f"{item['vote_average']:.1f}/10")
        
        if content_type == 'movie':
            # Get IMDb and Rotten Tomatoes ratings for movies
            ext_ids_response = requests.get(
                f"{BASE_URL}/movie/{item_id}/external_ids",
                params={"api_key": TMDB_API_KEY}
            )
            if ext_ids_response.ok:
                imdb_id = ext_ids_response.json().get('imdb_id')
                if imdb_id:
                    ratings = get_movie_ratings(imdb_id)
                    if ratings:
                        with rating_col2:
                            st.metric("IMDb", ratings.get('imdb', 'N/A'))
                        with rating_col3:
                            st.metric("Rotten Tomatoes", ratings.get('rotten_tomatoes', 'N/A'))
    
    # Display trailer if available
    trailer = get_movie_trailer(item_id) if content_type == 'movie' else get_tv_trailer(item_id)
    if trailer:
        st.markdown('<hr class="section-divider">', unsafe_allow_html=True)
        st.markdown('<h3 class="section-header">🎬 Official Trailer</h3>', unsafe_allow_html=True)
        st.markdown(f"""
            <style>
            .video-container {{
                position: relative;
                width: 100%;
                padding-bottom: 56.25%;
                margin-bottom: 20px;
            }}
            .video-container iframe {{
                position: absolute;
                top: 0;
                left: 0;
                width: 100%;
                height: 100%;
            }}
            </style>
            <div class="video-container">
                <iframe
                    src="https://www.youtube.com/embed/{trailer['key']}"
                    frameborder="0"
                    allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
                    allowfullscreen
                ></iframe>
            </div>
        """, unsafe_allow_html=True)
    
    # Cast section
    if "credits" in item and item["credits"].get("cast"):
        st.markdown('<hr class="section-divider">', unsafe_allow_html=True)
        st.markdown('<h3 class="section-header">👥 Main Cast</h3>', unsafe_allow_html=True)
        
        cast = item["credits"]["cast"][:10]
        cast_cols = st.columns(5)
        for i, member in enumerate(cast):
            with cast_cols[i % 5]:
                profile_path = member.get("profile_path")
                image_url = f"{PROFILE_BASE_URL}{profile_path}" if profile_path else "https://via.placeholder.com/300x450?text=No+Image"
                st.markdown(f"""
                    <div class="cast-card">
                        <img src="{image_url}">
                        <div style="text-align: center;">
                            <div class="cast-name">
                                {member['name']}
                            </div>
                            <div class="cast-character">
                                {member['character']}
                            </div>
                        </div>
                    </div>
                """, unsafe_allow_html=True)
    
    # Similar content section
    similar_items = []
    if content_type == 'movie':
        similar_items = get_similar_movies(item_id)
    elif item.get('similar', {}).get('results'):
        similar_items = item['similar']['results'][:5]
    
    if similar_items:
        st.markdown('<hr class="section-divider">', unsafe_allow_html=True)
        st.markdown(f'<h3 class="section-header">🎬 More Like This</h3>', unsafe_allow_html=True)
        
        similar_cols = st.columns(5)
        for i, similar_item in enumerate(similar_items):
            with similar_cols[i % 5]:
                poster_path = similar_item.get('poster_path')
                image_url = f"{POSTER_BASE_URL}{poster_path}" if poster_path else "https://via.placeholder.com/300x450?text=No+Poster"
                title = similar_item.get('title') if content_type == 'movie' else similar_item.get('name')
                st.markdown(f"""
                    <div class="similar-movie-card">
                        <img src="{image_url}" style="width: 100%; border-radius: 10px; margin-bottom: 0.5rem;">
                        <div style="text-align: center;">
                            <div style="font-weight: 600; font-size: 1rem; color: var(--text-color);">
                                {title}
                            </div>
                        </div>
                    </div>
                """, unsafe_allow_html=True)
                if st.button("More Info", key=f"similar_{similar_item['id']}", use_container_width=True):
                    st.session_state.selected_movie = similar_item['id']
                    st.rerun()
    
    # Back button
    if st.button(f"← Back to {st.session_state.filter_content_type}"):
        st.session_state.view = 'main'
        st.rerun()

def display_content_grid(movies, content_type):
    """Display a grid of movie or TV show posters"""
    if not movies:
        st.info("No content found matching your filters. Try adjusting your criteria.")
        return

    st.markdown("""
        <style>
        .movie-card-container {
            position: relative;
            margin-bottom: 30px;
            display: block;
        }

        .movie-card {
            position: relative;
            border-radius: 10px;
            overflow: hidden;
            background: transparent;
            cursor: pointer;
            margin-bottom: 8px;
        }

        .poster-container {
            position: relative;
            width: 100%;
            padding-top: 150%; /* 2:3 aspect ratio */
            overflow: hidden;
        }

        .poster-container img {
            position: absolute;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            object-fit: cover;
            border-radius: 10px;
            transition: transform 0.3s ease;
        }

        .movie-card:hover img {
            transform: scale(1.05);
        }

        .movie-rating {
            position: absolute;
            top: 10px;
            right: 10px;
            background: rgba(0, 0, 0, 0.6);
            color: #fff;
            padding: 4px 8px;
            border-radius: 4px;
            font-size: 0.9em;
            z-index: 2;
            backdrop-filter: blur(4px);
            -webkit-backdrop-filter: blur(4px);
        }

        .movie-info-overlay {
            position: absolute;
            bottom: 0;
            left: 0;
            right: 0;
            padding: 20px 15px;
            background: linear-gradient(
                to bottom,
                transparent,
                rgba(0, 0, 0, 0.3) 20%,
                rgba(0, 0, 0, 0.65)
            );
            color: white;
            opacity: 1;
            transition: all 0.3s ease;
            backdrop-filter: blur(3px);
            -webkit-backdrop-filter: blur(3px);
        }

        .movie-card:hover .movie-info-overlay {
            background: linear-gradient(
                to bottom,
                transparent,
                rgba(0, 0, 0, 0.4) 20%,
                rgba(0, 0, 0, 0.75)
            );
            backdrop-filter: blur(5px);
            -webkit-backdrop-filter: blur(5px);
        }

        .movie-title {
            font-weight: 600;
            margin-bottom: 6px;
            font-size: 1em;
            text-shadow: 1px 1px 2px rgba(0, 0, 0, 0.7);
            letter-spacing: 0.2px;
            line-height: 1.4;
        }

        .movie-year {
            font-size: 0.9em;
            opacity: 0.95;
            text-shadow: 1px 1px 2px rgba(0, 0, 0, 0.7);
            font-weight: 500;
        }

        /* Button styling */
        .stButton > button {
            width: 100% !important;
            background: transparent !important;
            border: 1px solid rgba(128, 128, 128, 0.2) !important;
            box-shadow: none !important;
            color: inherit !important;
            padding: 0.5rem !important;
            margin: 0 !important;
            height: auto !important;
            border-radius: 5px !important;
        }

        .stButton > button:hover {
            background: rgba(128, 128, 128, 0.2) !important;
            border-color: rgba(128, 128, 128, 0.3) !important;
        }

        .stButton > button:focus {
            box-shadow: none !important;
        }

        /* Ensure proper spacing between rows */
        .row-widget.stVerticalBlock {
            margin-bottom: 0;
        }
        </style>
    """, unsafe_allow_html=True)
    
    cols = st.columns(5)
    for i, movie in enumerate(movies):
        with cols[i % 5]:
            # Get release year
            release_date = movie.get('release_date' if content_type == 'movie' else 'first_air_date', '')
            year = release_date[:4] if release_date else 'N/A'
            
            # Get title
            title = movie.get('title' if content_type == 'movie' else 'name', 'Unknown Title')
            
            # Get rating
            rating = movie.get('vote_average', 0)
            
            # Create a container for the movie card and button
            st.markdown('<div class="movie-card-container">', unsafe_allow_html=True)
            
            # Display unified movie card
            st.markdown(f"""
                <div class="movie-card">
                    <div class="poster-container">
                        <img src="{POSTER_BASE_URL}{movie['poster_path'] if movie.get('poster_path') else '/placeholder.jpg'}">
                        <div class="movie-rating">⭐ {rating:.1f}</div>
                        <div class="movie-info-overlay">
                            <div class="movie-title">{title}</div>
                            <div class="movie-year">{year}</div>
                        </div>
                    </div>
                </div>
            """, unsafe_allow_html=True)
            
            # More Info button
            if st.button("More Info", key=f"{content_type}_{movie['id']}", help="Click for more details", use_container_width=True):
                st.session_state.view = 'details'
                st.session_state.selected_movie = movie['id']
                st.rerun()
            
            # Close the container
            st.markdown('</div>', unsafe_allow_html=True)

def apply_custom_css():
    """Apply custom CSS styling"""
    st.markdown("""
        <style>
        /* Remove white outline in dark mode and improve button styling */
        .stButton>button {
            border: none !important;
            box-shadow: none !important;
            color: inherit !important;
            background-color: transparent !important;
        }
        
        .stButton>button:hover {
            background-color: rgba(128, 128, 128, 0.2) !important;
        }
        
        .stButton>button:focus {
            box-shadow: none !important;
        }
        
        /* Style select boxes to match theme */
        .stSelectbox [data-baseweb="select"] {
            box-shadow: none !important;
        }
        
        /* Remove white outline from selectbox in dark mode */
        .stSelectbox [data-baseweb="select"]:focus {
            box-shadow: none !important;
        }

        /* Improve dark mode contrast */
        [data-testid="stMarkdownContainer"] {
            color: inherit !important;
        }
        
        /* Improve button text contrast */
        .stButton>button span {
            color: inherit !important;
        }
        </style>
    """, unsafe_allow_html=True)

def show_main_view():
    """Display the main view"""
    # Apply custom CSS first
    apply_custom_css()
    
    # Add CSS for styling
    st.markdown("""
        <style>
        /* Poster styling */
        .poster-wrapper {
            width: 100%;
            aspect-ratio: 2/3;
            position: relative;
            overflow: hidden;
            margin-bottom: 10px;
            border-radius: 8px;
            box-shadow: 0 4px 8px rgba(0,0,0,0.1);
        }
        .poster-wrapper img {
            width: 100%;
            height: 100%;
            object-fit: cover;
            border-radius: 8px;
            transition: transform 0.3s ease;
        }
        .poster-wrapper:hover img {
            transform: scale(1.05);
        }
        
        /* Title styling */
        .movie-info {
            padding: 10px 0;
            height: 60px;
            overflow: hidden;
            text-align: center;
        }
        .movie-title {
            font-size: 16px;
            font-weight: 600;
            margin: 0;
            line-height: 1.4;
            color: var(--text-color, inherit);
            overflow: hidden;
            text-overflow: ellipsis;
            display: -webkit-box;
            -webkit-line-clamp: 2;
            -webkit-box-orient: vertical;
        }
        
        /* Button styling */
        .button-container {
            width: 100%;
            position: absolute;
            bottom: 10px;
            left: 0;
            padding: 0 10px;
        }
        .stButton > button {
            width: 100%;
            padding: 10px;
            background-color: #0d47a1;
            color: white;
            border: none;
            border-radius: 8px;
            font-weight: 500;
            text-transform: uppercase;
            font-size: 14px;
            letter-spacing: 0.5px;
            transition: all 0.2s ease;
        }
        .stButton > button:hover {
            background-color: #1565c0;
            transform: translateY(-2px);
            box-shadow: 0 4px 8px rgba(13, 71, 161, 0.2);
        }
        
        /* Movie card button specific styling */
        .movie-card .stButton > button {
            border-radius: 0 0 10px 10px !important;
            margin: 0 !important;
        }
        
        /* Main title */
        .main-title {
            text-align: center;
            font-size: 4rem;
            font-weight: 700;
            color: var(--text-color, inherit);
            margin: 2rem 0;
            padding: 0;
            letter-spacing: -1px;
        }
        
        /* Search and filter styling */
        div[data-testid="stTextInput"] {
            margin-top: -1px;
        }
        .stTextInput > div > div > input {
            padding: 0.5rem 0.75rem !important;
            height: 36px !important;
            max-height: 36px !important;
            margin-top: 0 !important;
            margin-bottom: 0 !important;
        }
        
        div[data-testid="stButton"] {
            margin-top: -1px;
        }
        div[data-testid="stButton"] button {
            padding: 0.5rem 0.75rem !important;
            height: 36px !important;
            max-height: 36px !important;
            margin-top: 0 !important;
            margin-bottom: 0 !important;
            color: #666 !important;
            background: none !important;
            border: 1px solid #ddd !important;
            transition: all 0.2s ease !important;
        }
        div[data-testid="stButton"] button:hover {
            border-color: #666 !important;
            color: #333 !important;
        }
        .stButton {
            margin: 0 !important;
        }
        </style>
    """, unsafe_allow_html=True)

    st.markdown('<h1 class="main-title">🎬 Movie Recommender</h1>', unsafe_allow_html=True)

    # Search and filter section
    col1, col2 = st.columns([6, 1])
    
    with col1:
        search_query = st.text_input(
            label="",
            placeholder="Search for movies or TV shows...",
            key="search_input",
            label_visibility="collapsed"
        )
    
    with col2:
        show_filters = st.button("⚯ Filters", use_container_width=True, key="filter_button")
    
    # Initialize filter states in session state if not exists
    if 'view' not in st.session_state:
        st.session_state.view = 'search'
    if 'selected_movie' not in st.session_state:
        st.session_state.selected_movie = None
    if 'filter_content_type' not in st.session_state:
        st.session_state.filter_content_type = "Movies"
    if 'filter_genre' not in st.session_state:
        st.session_state.filter_genre = ""
    if 'filter_year' not in st.session_state:
        st.session_state.filter_year = (2000, 2024)
    if 'filter_language' not in st.session_state:
        st.session_state.filter_language = ""
    if 'filter_rating' not in st.session_state:
        st.session_state.filter_rating = 0.0
    if 'temp_rating' not in st.session_state:
        st.session_state.temp_rating = 0.0
    if 'show_filter_ui' not in st.session_state:
        st.session_state.show_filter_ui = False
    if 'current_page' not in st.session_state:
        st.session_state.current_page = 1

    # Toggle filter UI visibility
    if show_filters:
        st.session_state.show_filter_ui = not st.session_state.show_filter_ui

    # Show filters if button is clicked
    if st.session_state.show_filter_ui:
        with st.container():
            st.markdown("""
                <style>
                .filter-label {
                    font-size: 1.2rem;
                    font-weight: 600;
                    margin-bottom: 0.5rem;
                    color: var(--text-color);
                }
                </style>
            """, unsafe_allow_html=True)
            
            # Content Type Selection
            st.markdown('<p class="filter-label">Content Type</p>', unsafe_allow_html=True)
            st.radio(
                label="",
                options=["Movies", "TV Shows"],
                horizontal=True,
                key="temp_content_type",
                index=0 if st.session_state.filter_content_type == "Movies" else 1,
                label_visibility="collapsed"
            )
            
            filter_col1, filter_col2 = st.columns(2)
            
            with filter_col1:
                # Get appropriate genres based on content type
                content_type = 'movie' if st.session_state.temp_content_type == "Movies" else 'tv'
                genres = get_genres() if content_type == 'movie' else get_tv_genres()
                
                # Genre Selection
                st.markdown('<p class="filter-label">Genre</p>', unsafe_allow_html=True)
                st.selectbox(
                    label="",
                    options=[("", "All Genres")] + [(id, name) for id, name in genres.items()],
                    format_func=lambda x: x[1],
                    key="temp_genre",
                    label_visibility="collapsed"
                )
                
                # Year filter
                st.markdown('<p class="filter-label">Year</p>', unsafe_allow_html=True)
                st.slider(
                    label="",
                    min_value=1900,
                    max_value=2024,
                    value=st.session_state.filter_year,
                    step=1,
                    key="temp_year",
                    label_visibility="collapsed"
                )
                
            with filter_col2:
                # Language filter
                st.markdown('<p class="filter-label">Language</p>', unsafe_allow_html=True)
                languages = {
                    "": "All Languages",
                    "en": "English",
                    "es": "Spanish",
                    "fr": "French",
                    "de": "German",
                    "hi": "Hindi",
                    "ja": "Japanese",
                    "ko": "Korean",
                    "zh": "Chinese"
                }
                st.selectbox(
                    label="",
                    options=list(languages.items()),
                    format_func=lambda x: x[1],
                    key="temp_language",
                    label_visibility="collapsed"
                )
                
                # Rating filter
                st.markdown('<p class="filter-label">Minimum Rating</p>', unsafe_allow_html=True)
                st.slider(
                    label="",
                    min_value=0.0,
                    max_value=10.0,
                    value=st.session_state.filter_rating,
                    step=0.5,
                    key="temp_rating",
                    label_visibility="collapsed"
                )
            
            # Filter Buttons
            col1, col2 = st.columns(2)
            with col1:
                if st.button("Reset Filters", use_container_width=True):
                    # Only reset the permanent states
                    st.session_state.filter_rating = 0.0
                    st.session_state.filter_content_type = "Movies"
                    st.session_state.filter_genre = ""
                    st.session_state.filter_year = (2000, 2024)
                    st.session_state.filter_language = ""
                    st.session_state.current_page = 1
                    st.session_state.show_filter_ui = False
                    st.rerun()
            with col2:
                if st.button("Apply Filters", type="primary", use_container_width=True):
                    st.session_state.filter_content_type = st.session_state.temp_content_type
                    st.session_state.filter_genre = st.session_state.temp_genre
                    st.session_state.filter_year = st.session_state.temp_year
                    st.session_state.filter_language = st.session_state.temp_language
                    st.session_state.filter_rating = st.session_state.temp_rating
                    st.session_state.show_filter_ui = False
                    st.rerun()
    
    # Convert content type for API calls
    content_type = 'movie' if st.session_state.filter_content_type == "Movies" else 'tv'
    
    # Show loading spinner while fetching data
    with st.spinner("Loading content..."):
        if search_query:
            items, total_pages = search_content(search_query, page=st.session_state.current_page, content_type=content_type)
        else:
            if content_type == 'movie':
                items, total_pages = get_recommendations(
                    genre_id=st.session_state.filter_genre[0] if st.session_state.filter_genre else None,
                    page=st.session_state.current_page
                )
            else:
                items, total_pages = get_tv_shows(
                    genre_id=st.session_state.filter_genre[0] if st.session_state.filter_genre else None,
                    page=st.session_state.current_page
                )
    
    if not items:
        st.info("No content found. Try different search terms or filters!")
        return
    
    # Display content in a grid
    display_content_grid(items, content_type)
    
    # Pagination controls
    st.markdown("""
        <style>
        .pagination {
            display: flex;
            justify-content: center;
            align-items: center;
            margin-top: 2rem;
            gap: 1rem;
        }
        .page-button {
            padding: 0.5rem 1rem;
            border: 1px solid #ddd;
            border-radius: 4px;
            background: none;
            cursor: pointer;
            transition: all 0.2s ease;
        }
        .page-button:hover {
            border-color: #666;
            color: #333;
        }
        .page-info {
            text-align: center;
            min-width: 80px;
            padding: 0.5rem;
            font-size: 1rem;
            color: var(--text-color);
        }
        </style>
    """, unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([2,3,2])
    with col2:
        pagination_cols = st.columns([1,2,1])
        with pagination_cols[0]:
            if st.button("← Previous", disabled=st.session_state.current_page <= 1, use_container_width=True):
                st.session_state.current_page -= 1
                st.rerun()
        
        with pagination_cols[1]:
            st.markdown(f'<div class="page-info">{st.session_state.current_page} / {total_pages}</div>', unsafe_allow_html=True)
        
        with pagination_cols[2]:
            if st.button("Next →", disabled=st.session_state.current_page >= total_pages, use_container_width=True):
                st.session_state.current_page += 1
                st.rerun()

def main():
    if st.session_state.view == 'details':
        show_movie_details(st.session_state.selected_movie)
    else:
        show_main_view()

if __name__ == "__main__":
    main()
