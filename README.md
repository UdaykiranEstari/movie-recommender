# Movie Recommender

A Streamlit-based movie recommendation app that uses The Movie Database (TMDb) API to help users discover movies based on genres.

## Features

- Browse movies by genre
- Pagination support for viewing more results
- Movie details including:
  - Title
  - Poster
  - Rating
  - Overview

## Setup

1. Clone the repository
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Create a `.env` file with your TMDb API key:
   ```
   TMDB_API_KEY=your_api_key_here
   ```
4. Run the app:
   ```bash
   streamlit run app.py
   ```

## Technologies Used

- Python
- Streamlit
- TMDb API
- python-dotenv
- requests

## Note

Make sure to get your API key from [The Movie Database (TMDb)](https://www.themoviedb.org/) and add it to the `.env` file before running the app.
