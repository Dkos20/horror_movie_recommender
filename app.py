from flask import Flask, render_template, jsonify, request
import mysql.connector
import requests

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


def get_movies_by_genre(genre):
    conn = db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute('SELECT * FROM movies WHERE genre LIKE %s;', ('%' + genre + '%',))
    movies = cursor.fetchall()
    conn.close()
    return movies

def get_movies_by_director(director):
    conn = db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute('SELECT * FROM movies WHERE director LIKE %s;', ('%' + director + '%',))
    movies = cursor.fetchall()
    conn.close()
    return movies


from sklearn.feature_extraction.text import TfidfVectorizer

def generate_tfidf_vectors(movies):
    descriptions = [movie['genre'] for movie in movies]
    vectorizer = TfidfVectorizer(stop_words='english')
    tfidf_matrix = vectorizer.fit_transform(descriptions)
    return tfidf_matrix

from sklearn.metrics.pairwise import cosine_similarity

def get_similar_movies_by_name(movie_name, tfidf_matrix, movies):
    movie_index = next((index for index, m in enumerate(movies) if m['movie_title'].lower() == movie_name.lower()), None)
    if movie_index is None:
        return []
    
    cosine_sim = cosine_similarity(tfidf_matrix[movie_index], tfidf_matrix)
    similar_indices = cosine_sim[0].argsort()[-10:][::-1]
    return [movies[i] for i in similar_indices if i != movie_index]


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
    cursor.execute('SELECT * FROM movies LIMIT 10;')
    movies = cursor.fetchall()
    conn.close()

    for movie in movies:
        tmdb_data = get_tmdb_movie_data(movie['movie_title'])
        if tmdb_data:
            movie['tmdb_overview'] = tmdb_data['overview']
            movie['tmdb_release_date'] = tmdb_data['release_date']
            movie['tmdb_poster_url'] = tmdb_data['poster_url']
        else:
            movie['tmdb_overview'] = 'No details available'
            movie['tmdb_release_date'] = 'N/A'
            movie['tmdb_poster_url'] = None

    stats = get_statistics()
    most_common_genres = get_most_common_genres()
    genre_labels = [genre['genre'] for genre in most_common_genres]
    genre_counts = [genre['count'] for genre in most_common_genres]

    return render_template('index.html', movies=movies, stats=stats, genre_labels=genre_labels, genre_counts=genre_counts)



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
    movie_name = request.form.get('movie_name')
    genres = request.form.get('genres')
    director = request.form.get('director')
    rating = request.form.get('rating')

    conn = db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute('SELECT * FROM movies;')
    movies = cursor.fetchall()
    conn.close()

    tfidf_matrix = generate_tfidf_vectors(movies)

    similar_movies = get_similar_movies_by_name(movie_name, tfidf_matrix, movies)

    if genres:
        similar_movies = [m for m in similar_movies if genres.lower() in m['genre'].lower()]
    if director:
        similar_movies = [m for m in similar_movies if director.lower() in m['director'].lower()]
    if rating:
        similar_movies = [m for m in similar_movies if m['rating'] and float(m['rating']) >= float(rating)]

    for movie in similar_movies:
        tmdb_data = get_tmdb_movie_data(movie['movie_title'])
        if tmdb_data:
            movie['tmdb_overview'] = tmdb_data.get('overview', 'No overview available')
            movie['tmdb_release_date'] = tmdb_data.get('release_date', 'N/A')
            movie['tmdb_poster_url'] = tmdb_data.get('poster_url', None)
        else:
            movie['tmdb_overview'] = 'No overview available'
            movie['tmdb_release_date'] = 'N/A'
            movie['tmdb_poster_url'] = None

    return render_template(
        'recommendations.html',
        movies=similar_movies,
        movie_name=movie_name
    )




@app.route('/genre/<genre_name>')
def movies_by_genre(genre_name):
    conn = db_connection()
    cursor = conn.cursor(dictionary=True)
    query = '''
    SELECT * FROM movies WHERE genre LIKE %s;
    '''
    cursor.execute(query, ('%' + genre_name + '%',))
    movies = cursor.fetchall()
    conn.close()

    return render_template('movies_by_genre.html', genre_name=genre_name, movies=movies)


if __name__ == '__main__':
    app.run(debug=True)
