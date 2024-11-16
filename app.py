import streamlit as st
import requests

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

def get_tv_shows(genre_id=None, page=1):
    """Get TV show recommendations"""
    params = {
        "api_key": TMDB_API_KEY,
        "language": "en-US",
        "page": page,
        "sort_by": "popularity.desc"
    }
    if genre_id:
        params["with_genres"] = genre_id
    
    response = requests.get(
        f"{BASE_URL}/discover/tv",
        params=params
    )
    
    if response.ok:
        data = response.json()
        return data.get("results", []), data.get("total_pages", 1)
    return [], 0

def search_content(query, page=1, content_type='movie'):
    """Search for movies or TV shows"""
    response = requests.get(
        f"{BASE_URL}/search/{content_type}",
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

def show_movie_details(movie_id):
    """Display detailed movie information"""
    # Get basic movie details
    response = requests.get(
        f"{BASE_URL}/movie/{movie_id}",
        params={"api_key": TMDB_API_KEY, "language": "en-US", "append_to_response": "credits"}
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
    
    # Display trailer if available
    trailer = get_movie_trailer(movie_id)
    if trailer:
        st.markdown("""
            <div style="margin: 40px 0;">
                <hr style="border: none; height: 1px; background-color: #e0e0e0; margin: 30px 0;">
                <h3 style="margin-bottom: 20px;">🎬 Trailer</h3>
            </div>
        """, unsafe_allow_html=True)
        st.markdown(f"""
            <style>
            .video-container {{
                position: relative;
                width: 100%;
                padding-bottom: 56.25%; /* 16:9 Aspect Ratio */
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
    
    # Cast section with modern cards
    if "credits" in movie and movie["credits"].get("cast"):
        st.markdown("""
            <style>
            .section-header {
                color: var(--text-color);
                font-size: 1.5rem;
                font-weight: 600;
                margin-bottom: 20px;
            }
            .section-divider {
                border: none;
                height: 1px;
                background: linear-gradient(to right, transparent, var(--text-color), transparent);
                opacity: 0.3;
                margin: 30px 0;
            }
            </style>
        """, unsafe_allow_html=True)
        
        st.markdown('<hr class="section-divider">', unsafe_allow_html=True)
        st.markdown('<h3 class="section-header">👥 Cast</h3>', unsafe_allow_html=True)
        
        cast = movie["credits"]["cast"][:10]
        cast_cols = st.columns(5)
        for i, member in enumerate(cast):
            with cast_cols[i % 5]:
                profile_path = member.get("profile_path")
                image_url = f"{PROFILE_BASE_URL}{profile_path}" if profile_path else "https://via.placeholder.com/300x450?text=No+Image"
                st.markdown(f"""
                    <div class="cast-card">
                        <img src="{image_url}" style="width: 100%; border-radius: 10px; margin-bottom: 0.5rem;">
                        <div style="text-align: center;">
                            <div style="font-weight: 600; font-size: 1rem; margin-bottom: 0.25rem; color: var(--text-color);">
                                {member['name']}
                            </div>
                            <div style="font-size: 0.9rem; opacity: 0.7;">
                                {member['character']}
                            </div>
                        </div>
                    </div>
                """, unsafe_allow_html=True)
    
    # Similar movies section with modern grid
    similar_movies = get_similar_movies(movie_id)
    if similar_movies:
        st.markdown('<hr class="section-divider">', unsafe_allow_html=True)
        st.markdown('<h3 class="section-header">🎬 Similar Movies You Might Like</h3>', unsafe_allow_html=True)
        
        similar_cols = st.columns(5)
        for i, movie in enumerate(similar_movies[:10]):
            with similar_cols[i % 5]:
                poster_path = movie.get('poster_path')
                image_url = f"{POSTER_BASE_URL}{poster_path}" if poster_path else "https://via.placeholder.com/300x450?text=No+Poster"
                st.markdown(f"""
                    <div class="similar-movie-card">
                        <img src="{image_url}" style="width: 100%; border-radius: 10px; margin-bottom: 0.5rem;">
                        <div style="text-align: center;">
                            <div style="font-weight: 600; font-size: 1rem; color: var(--text-color);">
                                {movie['title']}
                            </div>
                        </div>
                    </div>
                """, unsafe_allow_html=True)
                if st.button("More Info", key=f"similar_{movie['id']}", use_container_width=True):
                    st.session_state.selected_movie = movie['id']
                    st.rerun()
    
    # Get and display streaming information
    providers = get_watch_providers(movie_id)
    if providers and providers.get('stream'):
        st.markdown("""
            <div style="margin: 40px 0;">
                <hr style="border: none; height: 1px; background-color: #e0e0e0; margin: 30px 0;">
                <h3 style="margin-bottom: 20px;">🎬 Where to Watch</h3>
            </div>
        """, unsafe_allow_html=True)
        # Only show streaming providers
        for provider in providers['stream']:
            st.write(f"- {provider['provider_name']}")
    else:
        st.markdown("""
            <div style="margin: 40px 0;">
                <hr style="border: none; height: 1px; background-color: #e0e0e0; margin: 30px 0;">
            </div>
        """, unsafe_allow_html=True)
        st.write("No streaming information available.")
    
    # Back button
    if st.button("← Back to Movies"):
        st.session_state.view = 'main'
        st.rerun()

def show_main_view():
    """Display the main view"""
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
            # st.markdown("### 🎯 Filters")
            
            # Content Type Selection
            st.radio(
                "Content Type",
                options=["Movies", "TV Shows"],
                horizontal=True,
                key="temp_content_type",
                index=0 if st.session_state.filter_content_type == "Movies" else 1
            )
            
            filter_col1, filter_col2 = st.columns(2)
            
            with filter_col1:
                # Get appropriate genres based on content type
                content_type = 'movie' if st.session_state.temp_content_type == "Movies" else 'tv'
                genres = get_genres() if content_type == 'movie' else get_tv_genres()
                
                # Genre Selection
                st.selectbox(
                    "Genre",
                    options=[("", "All Genres")] + [(id, name) for id, name in genres.items()],
                    format_func=lambda x: x[1],
                    key="temp_genre"
                )
                
                # Year filter
                st.slider(
                    "Year",
                    1900,
                    2024,
                    st.session_state.filter_year,
                    step=1,
                    key="temp_year"
                )
                
            with filter_col2:
                # Language filter
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
                    "Language",
                    options=list(languages.items()),
                    format_func=lambda x: x[1],
                    key="temp_language"
                )
                
                # Rating filter
                st.slider(
                    "Minimum Rating",
                    0.0,
                    10.0,
                    st.session_state.filter_rating,
                    step=0.5,
                    key="temp_rating"
                )
            
            # Apply Filters Button
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
    cols = st.columns(5)
    for i, movie in enumerate(items):
        with cols[i % 5]:
            poster_path = movie.get('poster_path')
            title = movie.get('title') if content_type == 'movie' else movie.get('name')
            
            st.markdown(f"""
                <div class="poster-wrapper">
                    <img src="{POSTER_BASE_URL}{poster_path}" alt="{title}" onerror="this.src='https://via.placeholder.com/185x278?text=No+Poster'">
                </div>
                <div class="movie-info">
                    <h3 class="movie-title">{title}</h3>
                </div>
                <div class="button-container">
            """, unsafe_allow_html=True)
            
            if st.button("More Info", key=f"{content_type}_{movie['id']}", use_container_width=True):
                st.session_state.view = 'details'
                st.session_state.selected_movie = movie['id']
                st.rerun()
            
            st.markdown("</div>", unsafe_allow_html=True)
    
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
