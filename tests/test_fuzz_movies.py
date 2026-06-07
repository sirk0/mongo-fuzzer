import re

from faker import Faker
from hypothesis import given
from hypothesis import strategies as st
from pymongo.collection import Collection

fake = Faker()


QUERYABLE_FIELDS = [
    "year",
    "runtime",
    "rated",
    "type",
    "title",
    "imdb.rating",
    "imdb.votes",
]
COMPARISON_OPS = ["$eq", "$gt", "$lt", "$gte", "$lte", "$ne"]
LOGICAL_OPS = ["$and", "$or"]
VALUES = [0, 1, -1, None, "", "active", "inactive", 99999, True, False]


@st.composite
def comparison_clause(draw: st.DrawFn) -> dict:
    field = draw(st.sampled_from(QUERYABLE_FIELDS))
    op = draw(st.sampled_from(COMPARISON_OPS))
    value = draw(st.sampled_from(VALUES))
    return {field: {op: value}}


@st.composite
def logical_query(draw: st.DrawFn) -> tuple[str, list[dict]]:
    op = draw(st.sampled_from(LOGICAL_OPS))
    clauses = draw(st.lists(comparison_clause(), min_size=2, max_size=3))
    return op, clauses


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


@given(threshold=st.floats(min_value=0, max_value=10, allow_nan=False))
def test_rating_threshold_query_matches_manual_filter(
    movies: Collection, threshold: float
) -> None:
    results = list(movies.find({"imdb.rating": {"$gte": threshold}}))
    expected_count = sum(1 for m in movies.find() if m["imdb"]["rating"] >= threshold)

    assert len(results) == expected_count
    assert all(m["imdb"]["rating"] >= threshold for m in results)


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


@given(direction=st.sampled_from([1, -1]))
def test_sort_by_year_returns_ordered_results(
    movies: Collection, direction: int
) -> None:
    results = list(movies.find().sort("year", direction))
    years = [m["year"] for m in results]

    assert years == sorted(years, reverse=(direction == -1))


@given(st.data())
def test_query_for_fake_title_returns_no_results(
    movies: Collection, data: st.DataObject
) -> None:
    fake_title = f"{fake.sentence()} {fake.uuid4()}"

    assert movies.find_one({"title": fake_title}) is None
    assert movies.count_documents({"title": fake_title}) == 0


@given(limit=st.integers(min_value=1, max_value=20))
def test_projection_returns_only_requested_fields(
    movies: Collection, limit: int
) -> None:
    results = list(movies.find({}, {"_id": 0, "title": 1, "year": 1}).limit(limit))

    assert len(results) == min(limit, movies.count_documents({}))
    assert all(set(m.keys()) == {"title", "year"} for m in results)


@given(query=comparison_clause())
def test_dynamic_comparison_query_executes_consistently(
    movies: Collection, query: dict
) -> None:
    results = list(movies.find(query))
    all_ids = {m["_id"] for m in movies.find()}

    assert movies.count_documents(query) == len(results)
    assert {m["_id"] for m in results} <= all_ids


@given(generated=logical_query())
def test_logical_query_matches_set_combination_of_clauses(
    movies: Collection, generated: tuple[str, list[dict]]
) -> None:
    op, clauses = generated

    combined_ids = {m["_id"] for m in movies.find({op: clauses})}
    clause_id_sets = [{m["_id"] for m in movies.find(clause)} for clause in clauses]

    expected_ids = (
        set.intersection(*clause_id_sets)
        if op == "$and"
        else set.union(*clause_id_sets)
    )

    assert combined_ids == expected_ids
