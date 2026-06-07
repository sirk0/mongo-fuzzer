from pymongo.collection import Collection


def test_find_movie_by_title(movies: Collection) -> None:
    movie = movies.find_one({"title": "Nosferatu"})

    assert movie is not None
    assert movie["year"] == 1922
    assert "F.W. Murnau" in movie["directors"]


def test_count_movies_by_genre(movies: Collection) -> None:
    short_count = movies.count_documents({"genres": "Short"})

    assert short_count == 12


def test_find_movies_released_after_year(movies: Collection) -> None:
    titles = {movie["title"] for movie in movies.find({"year": {"$gt": 1920}})}

    assert len(titles) == 21
    assert "The Kid" in titles
    assert "Nosferatu" in titles


def test_find_highest_rated_movie(movies: Collection) -> None:
    top_movie = movies.find_one(sort=[("imdb.rating", -1)])

    assert top_movie is not None
    assert top_movie["title"] == "The Kid"
    assert top_movie["imdb"]["rating"] == 8.4
