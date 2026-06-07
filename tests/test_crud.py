import pytest
from pymongo.collection import Collection


def test_full_crud_flow(collection: Collection, subtests: pytest.Subtests) -> None:
    document = {"name": "Alice", "age": 30}

    with subtests.test("create"):
        insert_result = collection.insert_one(document)
        assert insert_result.inserted_id is not None
        assert collection.count_documents({}) == 1

    with subtests.test("read"):
        found = collection.find_one({"name": "Alice"})
        assert found is not None
        assert found["age"] == 30

    with subtests.test("update"):
        update_result = collection.update_one({"name": "Alice"}, {"$set": {"age": 31}})
        assert update_result.modified_count == 1

        updated = collection.find_one({"name": "Alice"})
        assert updated is not None
        assert updated["age"] == 31

    with subtests.test("delete"):
        delete_result = collection.delete_one({"name": "Alice"})
        assert delete_result.deleted_count == 1
        assert collection.find_one({"name": "Alice"}) is None
