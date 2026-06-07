import os
from collections.abc import Generator

import pytest
from pymongo import MongoClient
from pymongo.collection import Collection

DEFAULT_MONGO_URI = "mongodb://root:example@localhost:27017"
MONGO_URI = os.environ.get("MONGO_URI", DEFAULT_MONGO_URI)


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
