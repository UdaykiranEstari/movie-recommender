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
        'sort_by': st.session_state.filter_sort[0],
        'include_adult': False,
        'include_video': False,
        'page': page,
        'vote_count.gte': 20
    }
    
    if genre_id and genre_id != "":
        params['with_genres'] = genre_id
    
    # Add rating filter if set
    if st.session_state.filter_rating > 0:
        params['vote_average.gte'] = st.session_state.filter_rating
    
    # Add year filter if set
    if hasattr(st.session_state, 'filter_year'):
        year_range = st.session_state.filter_year
        params['primary_release_date.gte'] = f"{year_range[0]}-01-01"
        params['primary_release_date.lte'] = f"{year_range[1]}-12-31"
    
    # Add language filter if set
    if st.session_state.filter_language[0] != "":
        params['with_original_language'] = st.session_state.filter_language[0]
    
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
        'sort_by': st.session_state.filter_sort[0],
        'page': page,
        'include_adult': False,
        'vote_count.gte': 20
    }
    
    if genre_id and genre_id != "":
        params['with_genres'] = genre_id
    
    # Add rating filter if set
    if st.session_state.filter_rating > 0:
        params['vote_average.gte'] = st.session_state.filter_rating
    
    # Add year filter if set
    if hasattr(st.session_state, 'filter_year'):
        year_range = st.session_state.filter_year
        params['first_air_date.gte'] = f"{year_range[0]}-01-01"
        params['first_air_date.lte'] = f"{year_range[1]}-12-31"
    
    # Add language filter if set
    if st.session_state.filter_language[0] != "":
        params['with_original_language'] = st.session_state.filter_language[0]
    
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
        'sort_by': 'popularity.desc'  # Sort by popularity by default
    }
    
    # Only add rating filter if explicitly set by user
    if hasattr(st.session_state, 'filter_rating') and st.session_state.filter_rating > 0:
        params['vote_average.gte'] = st.session_state.filter_rating
        # Add minimum vote count only when filtering by rating to ensure quality
        params['vote_count.gte'] = 20
    
    response = requests.get(f"{BASE_URL}/search/{content_type}", params=params)
    if response.ok:
        data = response.json()
        results = data.get('results', [])
        # Sort results by relevance (exact title matches first) and then by popularity
        results.sort(key=lambda x: (
            not x.get('title', x.get('name', '')).lower().startswith(query.lower()),
            -x.get('popularity', 0)
        ))
        return results, data.get('total_pages', 0)
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
        return data.get("results", [])[:10]  # Get more items initially to filter
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
        
        # Filter cast members with profile photos
        cast_with_photos = [member for member in item["credits"]["cast"] if member.get("profile_path")]
        
        if cast_with_photos:
            # Display up to 10 cast members with photos
            cast = cast_with_photos[:10]
            num_cols = min(5, len(cast))  # Adjust number of columns based on cast size
            cast_cols = st.columns(num_cols)
            
            for i, member in enumerate(cast):
                with cast_cols[i % num_cols]:
                    profile_path = member.get("profile_path")
                    image_url = f"{PROFILE_BASE_URL}{profile_path}"
                    st.markdown(f"""
                        <div class="cast-card">
                            <img src="{image_url}" alt="{member['name']}">
                            <p class="cast-name">{member['name']}</p>
                            <p class="cast-character">as {member['character']}</p>
                        </div>
                        <style>
                        .cast-card {{
                            background: rgba(255, 255, 255, 0.05);
                            border-radius: 10px;
                            padding: 10px;
                            margin-bottom: 15px;
                            transition: transform 0.2s;
                            text-align: center;
                        }}
                        .cast-card:hover {{
                            transform: translateY(-5px);
                        }}
                        .cast-card img {{
                            width: 100%;
                            border-radius: 8px;
                            margin-bottom: 8px;
                        }}
                        .cast-name {{
                            font-weight: 600;
                            font-size: 0.9rem;
                            color: var(--text-color);
                            margin: 5px 0 2px 0;
                            padding: 0;
                        }}
                        .cast-character {{
                            font-size: 0.8rem;
                            color: rgba(255, 255, 255, 0.7);
                            font-style: italic;
                            margin: 0;
                            padding: 0;
                        }}
                        </style>
                    """, unsafe_allow_html=True)
        else:
            st.info("No cast photos available for this title.")
    
    # Similar content section
    similar_items = []
    if content_type == 'movie':
        similar_items = get_similar_movies(item_id)
    elif item.get('similar', {}).get('results'):
        similar_items = item['similar']['results'][:10]  # Get more items initially to filter
    
    # Filter similar items to only include those with posters
    similar_items_with_posters = [item for item in similar_items if item.get('poster_path')]
    
    if similar_items_with_posters:
        st.markdown('<hr class="section-divider">', unsafe_allow_html=True)
        st.markdown(f'<h3 class="section-header">🎬 More Like This</h3>', unsafe_allow_html=True)
        
        similar_cols = st.columns(5)
        # Display only the first 5 items with posters
        for i, similar_item in enumerate(similar_items_with_posters[:5]):
            with similar_cols[i % 5]:
                poster_path = similar_item['poster_path']
                image_url = f"{POSTER_BASE_URL}{poster_path}"
                title = similar_item.get('title', '') if content_type == 'movie' else similar_item.get('name', '')
                st.markdown(f"""
                    <div class="movie-card">
                        <div class="poster-container">
                            <img src="{image_url}" class="poster-image">
                            <div class="movie-rating">⭐ {similar_item.get('vote_average', 0):.1f}</div>
                            <div class="movie-info-overlay">
                                <div class="movie-title">{title}</div>
                                <div class="movie-year">{similar_item.get('release_date', '')[:4] if similar_item.get('release_date') else 'N/A'}</div>
                            </div>
                        </div>
                    </div>
                    <style>
                    .movie-card {{
                        margin-bottom: 20px;
                        transition: transform 0.2s;
                        height: 100%;
                        display: flex;
                        flex-direction: column;
                    }}
                    .movie-card:hover {{
                        transform: scale(1.02);
                    }}
                    .poster-container {{
                        position: relative;
                        width: 100%;
                        padding-top: 150%; /* 2:3 aspect ratio */
                        overflow: hidden;
                        border-radius: 10px;
                    }}
                    .poster-image {{
                        position: absolute;
                        top: 0;
                        left: 0;
                        width: 100%;
                        height: 100%;
                        object-fit: cover;
                    }}
                    .movie-rating {{
                        position: absolute;
                        top: 10px;
                        right: 10px;
                        background: rgba(0, 0, 0, 0.6);
                        color: #fff;
                        padding: 4px 8px;
                        border-radius: 4px;
                        font-size: 0.9em;
                        backdrop-filter: blur(4px);
                        -webkit-backdrop-filter: blur(4px);
                    }}
                    .movie-info-overlay {{
                        position: absolute;
                        bottom: 0;
                        left: 0;
                        right: 0;
                        padding: 15px;
                        background: linear-gradient(to bottom, transparent, rgba(0,0,0,0.8));
                        color: white;
                    }}
                    .movie-title {{
                        font-weight: 600;
                        font-size: 1rem;
                        margin-bottom: 5px;
                        overflow: hidden;
                        text-overflow: ellipsis;
                        white-space: nowrap;
                    }}
                    .movie-year {{
                        font-size: 0.9rem;
                        opacity: 0.9;
                    }}
                    </style>
                """, unsafe_allow_html=True)
                
                if st.button("More Info", key=f"similar_{similar_item['id']}", use_container_width=True):
                    st.session_state.selected_movie = similar_item['id']
                    st.session_state.view = 'details'
                    st.rerun()

def display_content_grid(movies, content_type):
    """Display a grid of movie or TV show posters"""
    if not movies:
        st.info("No content found matching your filters. Try adjusting your criteria.")
        return

    # Filter out movies without posters
    movies_with_posters = [movie for movie in movies if movie.get('poster_path')]
    
    if not movies_with_posters:
        st.info("No content with posters found matching your filters. Try adjusting your criteria.")
        return
    
    # Create columns for the grid
    cols = st.columns(5)
    
    # Display movies in a grid
    for idx, movie in enumerate(movies_with_posters):
        with cols[idx % 5]:
            poster_path = movie['poster_path']
            title = movie.get('title', '') if content_type == 'movie' else movie.get('name', '')
            release_date = movie.get('release_date', '') if content_type == 'movie' else movie.get('first_air_date', '')
            year = release_date[:4] if release_date else 'N/A'
            rating = movie.get('vote_average', 0)
            
            # Create a clickable container
            container = st.container()
            with container:
                st.markdown(f"""
                    <div class="movie-card">
                        <div class="poster-container">
                            <img src="{POSTER_BASE_URL}{poster_path}" alt="{title}" class="poster-image">
                        </div>
                        <div class="movie-info">
                            <h3>{title}</h3>
                            <div class="movie-details">
                                <span>{year}</span>
                                <span>⭐ {rating:.1f}</span>
                            </div>
                        </div>
                    </div>
                    <style>
                    .movie-card {{
                        margin-bottom: 20px;
                        transition: transform 0.2s;
                        height: 100%;
                        display: flex;
                        flex-direction: column;
                    }}
                    .movie-card:hover {{
                        transform: scale(1.02);
                    }}
                    .poster-container {{
                        position: relative;
                        width: 100%;
                        padding-top: 150%; /* 2:3 aspect ratio */
                        overflow: hidden;
                        border-radius: 10px;
                    }}
                    .poster-image {{
                        position: absolute;
                        top: 0;
                        left: 0;
                        width: 100%;
                        height: 100%;
                        object-fit: cover;
                    }}
                    .movie-info {{
                        padding: 10px 5px;
                        flex-grow: 1;
                        display: flex;
                        flex-direction: column;
                    }}
                    .movie-info h3 {{
                        margin: 0;
                        font-size: 1rem;
                        font-weight: 600;
                        overflow: hidden;
                        text-overflow: ellipsis;
                        white-space: nowrap;
                    }}
                    .movie-details {{
                        display: flex;
                        justify-content: space-between;
                        margin-top: 5px;
                        color: var(--text-color);
                        font-size: 0.9rem;
                    }}
                    </style>
                """, unsafe_allow_html=True)
                
                # Make the entire card clickable
                if st.button("More Info", key=f"movie_{movie['id']}", use_container_width=True):
                    st.session_state.selected_movie = movie['id']
                    st.session_state.view = 'details'  # Add this line to set the view to details
                    st.rerun()

def show_main_view():
    """Display the main view"""
    st.markdown('<h1 class="main-title">🎬 Movie Recommender</h1>', unsafe_allow_html=True)

    # Initialize session state variables if they don't exist
    if 'filter_content_type' not in st.session_state:
        st.session_state.filter_content_type = "Movies"
    if 'filter_genre' not in st.session_state:
        st.session_state.filter_genre = ("", "All Genres")
    if 'filter_year' not in st.session_state:
        st.session_state.filter_year = (2000, 2024)
    if 'filter_rating' not in st.session_state:
        st.session_state.filter_rating = 0.0
    if 'filter_language' not in st.session_state:
        st.session_state.filter_language = ("", "All Languages")
    if 'filter_sort' not in st.session_state:
        st.session_state.filter_sort = ("popularity.desc", "Most Popular")
    if 'current_page' not in st.session_state:
        st.session_state.current_page = 1
    if 'show_filter_ui' not in st.session_state:
        st.session_state.show_filter_ui = False
        
    # Initialize temporary filter state
    if 'temp_content_type' not in st.session_state:
        st.session_state.temp_content_type = st.session_state.filter_content_type
    if 'temp_genre' not in st.session_state:
        st.session_state.temp_genre = st.session_state.filter_genre
    if 'temp_year' not in st.session_state:
        st.session_state.temp_year = st.session_state.filter_year
    if 'temp_rating' not in st.session_state:
        st.session_state.temp_rating = st.session_state.filter_rating
    if 'temp_language' not in st.session_state:
        st.session_state.temp_language = st.session_state.filter_language
    if 'temp_sort' not in st.session_state:
        st.session_state.temp_sort = st.session_state.filter_sort

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
        show_filters = st.button("⚯ Filters", use_container_width=True)
    
    # Toggle filter UI visibility
    if show_filters:
        st.session_state.show_filter_ui = not st.session_state.show_filter_ui

    # Show filters if button is clicked
    if st.session_state.show_filter_ui:
        # Add CSS for filter titles
        st.markdown("""
            <style>
            .filter-title {
                font-weight: 600;
                margin-bottom: 5px;
            }
            </style>
        """, unsafe_allow_html=True)
        
        st.markdown('<p class="filter-title">Content Type</p>', unsafe_allow_html=True)
        content_type = st.radio(
            label="",
            options=["Movies", "TV Shows"],
            horizontal=True,
            label_visibility="collapsed",
            key="temp_content_type"
        )
        
        col1, col2 = st.columns(2)
        with col1:
            # Genre Selection
            st.markdown('<p class="filter-title">Genre</p>', unsafe_allow_html=True)
            genres = get_genres() if st.session_state.temp_content_type == "Movies" else get_tv_genres()
            genre = st.selectbox(
                label="",
                options=[("", "All Genres")] + [(str(id), name) for id, name in genres.items()],
                format_func=lambda x: x[1],
                key="temp_genre",
                label_visibility="collapsed"
            )
            
            # Year filter
            st.markdown('<p class="filter-title">Year Range</p>', unsafe_allow_html=True)
            year_range = st.slider(
                label="",
                min_value=1900,
                max_value=2024,
                value=st.session_state.temp_year,
                key="temp_year",
                label_visibility="collapsed"
            )
            
            # Rating filter
            st.markdown('<p class="filter-title">Minimum Rating</p>', unsafe_allow_html=True)
            rating = st.slider(
                label="",
                min_value=0.0,
                max_value=10.0,
                value=st.session_state.temp_rating,
                step=0.5,
                key="temp_rating",
                label_visibility="collapsed"
            )
        
        with col2:
            # Language filter
            st.markdown('<p class="filter-title">Language</p>', unsafe_allow_html=True)
            languages = {
                "": "All Languages",
                "en": "English",
                "hi": "Hindi",
                "ja": "Japanese",
                "ko": "Korean",
                "fr": "French",
                "es": "Spanish",
                "de": "German",
                "it": "Italian",
                "zh": "Chinese"
            }
            language = st.selectbox(
                label="",
                options=list(languages.items()),
                format_func=lambda x: x[1],
                key="temp_language",
                label_visibility="collapsed"
            )
            
            # Sort By filter
            st.markdown('<p class="filter-title">Sort By</p>', unsafe_allow_html=True)
            sort_options = {
                "popularity.desc": "Most Popular",
                "vote_average.desc": "Highest Rated",
                "primary_release_date.desc": "Latest Release",
                "revenue.desc": "Highest Revenue"
            }
            sort_by = st.selectbox(
                label="",
                options=list(sort_options.items()),
                format_func=lambda x: x[1],
                key="temp_sort",
                label_visibility="collapsed"
            )

        # Add Apply and Reset buttons
        button_col1, button_col2 = st.columns(2)
        with button_col1:
            if st.button("Reset Filters", use_container_width=True):
                # Reset all temp filters to default values
                st.session_state.temp_content_type = "Movies"
                st.session_state.temp_genre = ("", "All Genres")
                st.session_state.temp_year = (2000, 2024)
                st.session_state.temp_rating = 0.0
                st.session_state.temp_language = ("", "All Languages")
                st.session_state.temp_sort = ("popularity.desc", "Most Popular")
                st.rerun()
        with button_col2:
            if st.button("Apply Filters", use_container_width=True, type="primary"):
                # Apply temp filters to actual filters
                st.session_state.filter_content_type = st.session_state.temp_content_type
                st.session_state.filter_genre = st.session_state.temp_genre
                st.session_state.filter_year = st.session_state.temp_year
                st.session_state.filter_rating = st.session_state.temp_rating
                st.session_state.filter_language = st.session_state.temp_language
                st.session_state.filter_sort = st.session_state.temp_sort
                st.session_state.current_page = 1
                st.rerun()
    
    # Convert content type for API calls
    content_type = 'movie' if st.session_state.filter_content_type == "Movies" else 'tv'
    
    # Show loading spinner while fetching data
    with st.spinner("Loading content..."):
        if search_query:
            items, total_pages = search_content(
                search_query,
                page=st.session_state.current_page,
                content_type=content_type
            )
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
    
    # Display content grid
    if items:
        display_content_grid(items, content_type)
        
        # Pagination
        col1, col2, col3 = st.columns([2,3,2])
        with col2:
            cols = st.columns(3)
            with cols[0]:
                if st.button("← Previous", disabled=st.session_state.current_page <= 1):
                    st.session_state.current_page -= 1
                    st.rerun()
            
            with cols[1]:
                st.markdown(f"<div style='text-align: center; padding: 5px;'>Page {st.session_state.current_page} of {total_pages}</div>", unsafe_allow_html=True)
            
            with cols[2]:
                if st.button("Next →", disabled=st.session_state.current_page >= total_pages):
                    st.session_state.current_page += 1
                    st.rerun()
    else:
        st.info("No content found. Try different search terms or filters!")

def main():
    """Main application entry point"""
    if st.session_state.view == 'details':
        show_movie_details(st.session_state.selected_movie)
        if st.button("← Back to Browse"):
            st.session_state.view = 'search'
            st.rerun()
    else:
        show_main_view()

if __name__ == "__main__":
    main()
