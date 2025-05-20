import json

MOVIE_FILE = 'data/movies.json'

def load_movies():
    try:
        with open(MOVIE_FILE, 'r', encoding='utf-8') as f:
            data = f.read().strip()
            if not data:
                return []
            return json.loads(data)
    except FileNotFoundError:
        return []

def save_movies(movies):
    with open(MOVIE_FILE, 'w', encoding='utf-8') as f:
        json.dump(movies, f, ensure_ascii=False, indent=2)

def update_session(title, index, new_date, new_time):
    movies = load_movies()
    for movie in movies:
        if movie['title'].lower() == title.lower():
            if 0 <= index < len(movie.get('sessions', [])):
                movie['sessions'][index]['date'] = new_date
                movie['sessions'][index]['time'] = new_time
                save_movies(movies)
                return True
            break
    return False
