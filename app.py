from flask import Flask, render_template, jsonify, request
import mysql.connector
import requests
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

app = Flask(__name__)


def db_connection():
    conn = mysql.connector.connect(
        host='localhost',
        user='root',
        password='root',
        database='horror_movies'
    )
    return conn
    
def get_most_common_genres():
    conn = db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute('SELECT genre, COUNT(*) as count FROM movies GROUP BY genre ORDER BY count DESC LIMIT 10;')
    genres = cursor.fetchall()
    conn.close()
    return genres


TMDB_API_KEY = '4074ff9dd873e0f5c4d75a77f36632b7'
TMDB_API_URL = 'https://api.themoviedb.org/3'

def get_tmdb_movie_data(movie_title):
    url = f'{TMDB_API_URL}/search/movie?api_key={TMDB_API_KEY}&query={movie_title}'
    response = requests.get(url)
    data = response.json()

    if data['results']:
        movie_data = data['results'][0]
        return {
            'title': movie_data['title'],
            'overview': movie_data['overview'],
            'description': movie_data['overview'],
            'release_date': movie_data['release_date'],
            'poster_url': f"https://image.tmdb.org/t/p/w500/{movie_data['poster_path']}" if movie_data['poster_path'] else None,
            'tmdb_id': movie_data['id'],
            'genre_ids': movie_data.get('genre_ids', []) 
        }
    return None


def get_movies_by_director(director):
    conn = db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute('SELECT * FROM movies WHERE director LIKE %s;', ('%' + director + '%',))
    movies = cursor.fetchall()
    conn.close()
    return movies


class MovieRecommender:
    def __init__(self, movies_data):
        self.movies = movies_data
        self.prepare_features()
    
    def prepare_features(self):
        self.text_features = [
            f"{movie['movie_title']} {movie['genre']} {movie['director']}"
            for movie in self.movies
        ]
        
        self.ratings = np.array([float(movie['rating']) if movie['rating'] else 0 
                               for movie in self.movies])
        
        self.tfidf = TfidfVectorizer(stop_words='english')
        self.tfidf_matrix = self.tfidf.fit_transform(self.text_features)
    
    def get_recommendations(self, query_params, weights={'content': 0.2, 'genre': 0.4, 
                                                       'director': 0.2, 'rating': 0.2}):
        
        scores = np.zeros(len(self.movies))
        
        if query_params['movie_name']:
            query_vector = self.tfidf.transform([query_params['movie_name']])
            content_similarity = cosine_similarity(query_vector, self.tfidf_matrix)[0]
            scores += weights['content'] * content_similarity
        
        if query_params['genres']:
            genre_scores = np.array([
                1.0 if query_params['genres'].lower() in movie['genre'].lower() else 0.0
                for movie in self.movies
            ])
            scores += weights['genre'] * genre_scores
        
        if query_params['director']:
            director_scores = np.array([
                1.0 if query_params['director'].lower() in movie['director'].lower() else 0.0
                for movie in self.movies
            ])
            scores += weights['director'] * director_scores
        
        if query_params['rating']:
            rating_threshold = float(query_params['rating'])
            rating_scores = np.array([
                1.0 if (movie['rating'] and float(movie['rating']) >= rating_threshold) else 0.0
                for movie in self.movies
            ])
            scores += weights['rating'] * rating_scores
        
        top_indices = np.argsort(scores)[::-1][:10]
        return [self.movies[i] for i in top_indices if scores[i] > 0]


def get_statistics():
    conn = db_connection()
    cursor = conn.cursor(dictionary=True)
    
    cursor.execute('SELECT AVG(rating) as avg_rating FROM movies;')
    avg_rating = cursor.fetchone()['avg_rating']
    cursor.execute('SELECT genre, COUNT(*) as count FROM movies GROUP BY genre ORDER BY count DESC LIMIT 1;')
    most_common_genre = cursor.fetchone()
    
    cursor.execute('SELECT director, COUNT(*) as count FROM movies GROUP BY director ORDER BY count DESC LIMIT 1;')
    most_common_director = cursor.fetchone()
    
    conn.close()
    
    return {
        'avg_rating': round(avg_rating, 2) if avg_rating else None,
        'most_common_genre': most_common_genre['genre'] if most_common_genre else 'N/A',
        'most_common_director': most_common_director['director'] if most_common_director else 'N/A'
    }

@app.route('/')
def index():
    conn = db_connection()
    cursor = conn.cursor(dictionary=True)
    
    cursor.execute('''
        SELECT * FROM movies 
        WHERE rating IS NOT NULL 
        ORDER BY rating DESC 
        LIMIT 10
    ''')
    movies = cursor.fetchall()
    
    cursor.execute('SELECT * FROM movies')
    all_movies = cursor.fetchall()
    conn.close()
    
    for movie in movies:
        tmdb_data = get_tmdb_movie_data(movie['movie_title'])
        if tmdb_data:
            movie.update({
                'tmdb_overview': tmdb_data['overview'],
                'tmdb_release_date': tmdb_data['release_date'],
                'tmdb_poster_url': tmdb_data['poster_url']
            })
    
    stats = get_statistics()
    most_common_genres = get_most_common_genres()
    genre_labels = [genre['genre'] for genre in most_common_genres]
    genre_counts = [genre['count'] for genre in most_common_genres]
    
    return render_template('index.html', 
                         movies=movies,
                         all_movies=all_movies,
                         stats=stats,
                         genre_labels=genre_labels,
                         genre_counts=genre_counts)




@app.route('/director/<director_name>')
def movies_by_director(director_name):
    conn = db_connection()
    cursor = conn.cursor(dictionary=True)
    query = '''
    SELECT * FROM movies WHERE director = %s;
    '''
    cursor.execute(query, (director_name,))
    movies = cursor.fetchall()
    conn.close()

    return render_template('movies_by_director.html', director_name=director_name, movies=movies)


@app.route('/advanced_recommendations', methods=['POST'])
def advanced_recommendations():
    """Handle advanced movie recommendations"""
    query_params = {
        'movie_name': request.form.get('movie_name'),
        'genres': request.form.get('genres'),
        'director': request.form.get('director'),
        'rating': request.form.get('rating')
    }
    
    conn = db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute('SELECT * FROM movies')
    movies = cursor.fetchall()
    conn.close()
    
    recommender = MovieRecommender(movies)
    recommended_movies = recommender.get_recommendations(query_params)
    
    for movie in recommended_movies:
        tmdb_data = get_tmdb_movie_data(movie['movie_title'])
        if tmdb_data:
            movie.update({
                'tmdb_overview': tmdb_data.get('overview', 'No overview available'),
                'tmdb_release_date': tmdb_data.get('release_date', 'N/A'),
                'tmdb_poster_url': tmdb_data.get('poster_url', None)
            })
    
    return render_template(
        'recommendations.html',
        movies=recommended_movies,
        query=query_params
    )


if __name__ == '__main__':
    app.run(debug=True)
