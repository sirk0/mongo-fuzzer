import os
from collections.abc import Generator
from pathlib import Path

import pytest
from bson import json_util
from dotenv import load_dotenv
from pymongo import MongoClient
from pymongo.collection import Collection
from pymongo.database import Database

DEFAULT_MONGO_URI = "mongodb://root:example@localhost:27017"

SAMPLE_MFLIX_DATA_DIR = Path(__file__).parent / "data"
SAMPLE_MFLIX_COLLECTIONS = ["movies", "comments", "theaters", "users", "sessions"]


def pytest_addoption(parser: pytest.Parser) -> None:
    parser.addoption(
        "--env-file",
        action="store",
        default=None,
        help="Path to a .env file containing MONGO_URI. Not loaded by default; "
        "pass this explicitly to point tests at a different MongoDB instance "
        "(e.g. a MongoDB Atlas cluster).",
    )
    parser.addoption(
        "--read-only",
        action="store_true",
        default=False,
        help="Never seed or clean up the sample_mflix dataset. Use this when "
        "pointing MONGO_URI at a shared dataset (e.g. a real Atlas sample_mflix "
        "cluster) to guarantee the original data is left untouched. CRUD tests "
        "still run normally against their own separate test_db/test_collection.",
    )


@pytest.fixture(scope="session")
def mongo_uri(request: pytest.FixtureRequest) -> str:
    env_file = request.config.getoption("--env-file")
    if env_file:
        load_dotenv(env_file)

    return os.environ.get("MONGO_URI", DEFAULT_MONGO_URI)


@pytest.fixture(scope="session")
def read_only(request: pytest.FixtureRequest) -> bool:
    return bool(request.config.getoption("--read-only"))


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
def sample_mflix_db(
    mongo_client: MongoClient, read_only: bool
) -> Generator[Database, None, None]:
    db: Database = mongo_client["sample_mflix"]

    if read_only:
        # Use the dataset as-is (e.g. a real Atlas sample_mflix cluster) without
        # ever writing to or deleting from it.
        yield db
        return

    for name in SAMPLE_MFLIX_COLLECTIONS:
        documents = json_util.loads(
            (SAMPLE_MFLIX_DATA_DIR / f"{name}.json").read_text()
        )
        coll = db[name]
        coll.delete_many({})
        coll.insert_many(documents)

    yield db

    for name in SAMPLE_MFLIX_COLLECTIONS:
        db[name].delete_many({})


@pytest.fixture(scope="session")
def movies(sample_mflix_db: Database) -> Collection:
    return sample_mflix_db["movies"]
