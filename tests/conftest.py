import os
from collections.abc import Generator
from pathlib import Path

import pytest
from bson import json_util
from dotenv import load_dotenv
from hypothesis import settings
from pymongo import MongoClient
from pymongo.collection import Collection
from pymongo.database import Database

DEFAULT_MONGO_URI = "mongodb://root:example@localhost:27017"

SAMPLE_MFLIX_DATA_DIR = Path(__file__).parent / "data"

# Maps collection name (used in the DB) → JSON file stem (in tests/data/).
# All collections are prefixed with "test_" so they never clash with the
# original Atlas sample_mflix collections when running against a real cluster.
SAMPLE_MFLIX_COLLECTIONS: dict[str, str] = {
    "test_movies": "movies",
    "test_comments": "comments",
    "test_theaters": "theaters",
    "test_users": "users",
    "test_sessions": "sessions",
}

# Hypothesis profiles: select one with `pytest --hypothesis-profile=<name>`
# (or the HYPOTHESIS_PROFILE env var) to control fuzzing parameters such as
# the number of examples generated per test.
settings.register_profile("default", max_examples=100)
settings.register_profile("dev", max_examples=10, deadline=None)
settings.register_profile("thorough", max_examples=1000, deadline=None)
settings.register_profile("ci", max_examples=200, deadline=None)
settings.load_profile(os.environ.get("HYPOTHESIS_PROFILE", "default"))


def pytest_addoption(parser: pytest.Parser) -> None:
    parser.addoption(
        "--env-file",
        action="store",
        default=None,
        help="Path to a .env file containing MONGO_URI. Not loaded by default; "
        "pass this explicitly to point tests at a different MongoDB instance "
        "(e.g. a MongoDB Atlas cluster).",
    )


@pytest.fixture(scope="session")
def mongo_uri(request: pytest.FixtureRequest) -> str:
    env_file = request.config.getoption("--env-file")
    if env_file:
        load_dotenv(env_file)

    return os.environ.get("MONGO_URI", DEFAULT_MONGO_URI)


@pytest.fixture(scope="session")
def mongo_client(mongo_uri: str) -> Generator[MongoClient, None, None]:
    client: MongoClient = MongoClient(mongo_uri)
    yield client
    client.close()


@pytest.fixture()
def collection(mongo_client: MongoClient) -> Generator[Collection, None, None]:
    coll: Collection = mongo_client["test_db"]["test_collection"]
    coll.delete_many({})
    yield coll
    coll.delete_many({})


@pytest.fixture(scope="session")
def sample_mflix_db(mongo_client: MongoClient) -> Generator[Database, None, None]:
    db: Database = mongo_client["sample_mflix"]

    for coll_name, json_stem in SAMPLE_MFLIX_COLLECTIONS.items():
        documents = json_util.loads(
            (SAMPLE_MFLIX_DATA_DIR / f"{json_stem}.json").read_text()
        )
        coll = db[coll_name]
        coll.delete_many({})
        coll.insert_many(documents)

    # Indexes for collections queried by tests.
    db["test_movies"].create_index("year")
    db["test_movies"].create_index("imdb.rating")

    yield db

    for coll_name in SAMPLE_MFLIX_COLLECTIONS:
        db[coll_name].delete_many({})


@pytest.fixture(scope="session")
def movies(sample_mflix_db: Database) -> Collection:
    return sample_mflix_db["test_movies"]
