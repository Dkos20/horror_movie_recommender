import mysql.connector
import json
import re


conn = mysql.connector.connect(
    host="localhost",
    user="root",
    password="root",
    database="horror_movies"
)

cursor = conn.cursor()

with open('horror_movies.json', 'r') as file:
    horror_movies = json.load(file)

def clean_gross(gross):
    if gross:
        gross = gross.replace('$', '').replace('M', '').strip()
        return float(gross) if gross else 0.0
    return 0.0

def clean_votes(votes):
    if votes:
        return int(votes.replace(',', ''))
    return 0

for movie in horror_movies:
    movie_title = movie['Movie Title']
    movie_year = movie['Movie Year']
    runtime = movie['Runtime']
    genre = movie['Genre']
    rating = movie['Rating']
    director = movie['Director']
    votes = clean_votes(movie['Votes'])
    gross = clean_gross(movie['Gross'])
    
    cursor.execute("""
        INSERT INTO movies (movie_title, movie_year, runtime, genre, rating, director, votes, gross)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
    """, (movie_title, movie_year, runtime, genre, rating, director, votes, gross))

conn.commit()
cursor.close()
conn.close()

print("Data imported successfully!")
