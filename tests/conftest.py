import os
from collections.abc import Generator
from pathlib import Path

import pytest
from bson import json_util
from pymongo import MongoClient
from pymongo.collection import Collection
from pymongo.database import Database

DEFAULT_MONGO_URI = "mongodb://root:example@localhost:27017"
MONGO_URI = os.environ.get("MONGO_URI", DEFAULT_MONGO_URI)

SAMPLE_MFLIX_DATA_DIR = Path(__file__).parent / "data"
SAMPLE_MFLIX_COLLECTIONS = ["movies", "comments", "theaters", "users", "sessions"]


@pytest.fixture(scope="session")
def mongo_client() -> Generator[MongoClient, None, None]:
    client: MongoClient = MongoClient(MONGO_URI)
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
