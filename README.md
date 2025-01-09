# horror_movie_recommender

This project is a Flask-based web application that provides personalized horror movie recommendations. The application uses data from Kaggle datasets and the TMDb (The Movie Database) API to deliver tailored movie suggestions based on user preferences.

Features

User Input: Users can search for movies or select their preferences.

Recommendation Engine: Utilizes Kaggle datasets to generate personalized movie recommendations.

Dynamic Data: Fetches additional movie details such as posters, descriptions, and ratings via the TMDb API.

Interactive UI: A responsive and user-friendly web interface built using Flask and Bootstrap.

Prerequisites

Before running the application, ensure you have the following installed:

Python 3.7+

Flask

Requests

Pandas

Numpy

Any additional libraries specified in requirements.txt

You will also need:

Kaggle account and access to relevant datasets (e.g., "Movies Dataset").

TMDb API key (you can sign up at TMDb).

Installation

Clone this repository:

git clone https://github.com/yourusername/flask-movie-recommender.git
cd flask-movie-recommender

Set up a virtual environment:

python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

Install dependencies:

pip install -r requirements.txt

Add your API keys:

Place your Kaggle datasets in the datasets/ directory.

Create a .env file in the root directory and add your TMDb API key:

TMDB_API_KEY=your_tmdb_api_key

Usage

Preprocess the data:

Run the preprocessing script to clean and prepare the Kaggle data for recommendations.

python preprocess.py

Start the Flask application:

flask run

Open your browser and navigate to:

http://127.0.0.1:5000

Search for movies and explore recommendations.
