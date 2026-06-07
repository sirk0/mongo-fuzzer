import re

from faker import Faker
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st
from pymongo.collection import Collection

fake = Faker()

fuzz = settings(
    suppress_health_check=[HealthCheck.function_scoped_fixture], deadline=None
)


@fuzz
@given(
    lo=st.integers(min_value=1880, max_value=2030),
    hi=st.integers(min_value=1880, max_value=2030),
)
def test_year_range_query_matches_manual_filter(
    movies: Collection, lo: int, hi: int
) -> None:
    low, high = sorted((lo, hi))

    results = list(movies.find({"year": {"$gte": low, "$lte": high}}))
    expected = [m for m in movies.find() if low <= m["year"] <= high]

    assert {m["_id"] for m in results} == {m["_id"] for m in expected}
    assert all(low <= m["year"] <= high for m in results)


@fuzz
@given(threshold=st.floats(min_value=0, max_value=10, allow_nan=False))
def test_rating_threshold_query_matches_manual_filter(
    movies: Collection, threshold: float
) -> None:
    results = list(movies.find({"imdb.rating": {"$gte": threshold}}))
    expected_count = sum(1 for m in movies.find() if m["imdb"]["rating"] >= threshold)

    assert len(results) == expected_count
    assert all(m["imdb"]["rating"] >= threshold for m in results)


@fuzz
@given(data=st.data())
def test_genre_query_returns_only_matching_movies(
    movies: Collection, data: st.DataObject
) -> None:
    all_genres = sorted({genre for m in movies.find() for genre in m["genres"]})
    genre = data.draw(st.sampled_from(all_genres))

    results = list(movies.find({"genres": genre}))
    expected_count = movies.count_documents({"genres": genre})

    assert len(results) == expected_count
    assert all(genre in m["genres"] for m in results)
    assert len(results) > 0


@fuzz
@given(data=st.data())
def test_title_regex_query_matches_substring_case_insensitively(
    movies: Collection, data: st.DataObject
) -> None:
    titles = [m["title"] for m in movies.find()]
    title = data.draw(st.sampled_from(titles))

    start = data.draw(st.integers(min_value=0, max_value=len(title) - 1))
    end = data.draw(st.integers(min_value=start + 1, max_value=len(title)))
    substring = title[start:end]
    pattern = re.escape(substring)

    results = list(movies.find({"title": {"$regex": pattern, "$options": "i"}}))

    assert any(m["title"] == title for m in results)
    assert all(re.search(pattern, m["title"], re.IGNORECASE) for m in results)


@fuzz
@given(direction=st.sampled_from([1, -1]))
def test_sort_by_year_returns_ordered_results(
    movies: Collection, direction: int
) -> None:
    results = list(movies.find().sort("year", direction))
    years = [m["year"] for m in results]

    assert years == sorted(years, reverse=(direction == -1))


@fuzz
@given(st.data())
def test_query_for_fake_title_returns_no_results(
    movies: Collection, data: st.DataObject
) -> None:
    fake_title = f"{fake.sentence()} {fake.uuid4()}"

    assert movies.find_one({"title": fake_title}) is None
    assert movies.count_documents({"title": fake_title}) == 0


@fuzz
@given(limit=st.integers(min_value=1, max_value=20))
def test_projection_returns_only_requested_fields(
    movies: Collection, limit: int
) -> None:
    results = list(movies.find({}, {"_id": 0, "title": 1, "year": 1}).limit(limit))

    assert len(results) == min(limit, movies.count_documents({}))
    assert all(set(m.keys()) == {"title", "year"} for m in results)
