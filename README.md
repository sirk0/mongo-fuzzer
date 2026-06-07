# mongo-fuzzer

A small Python playground for testing MongoDB: CRUD tests against a local
MongoDB instance, fixtures that load a representative `sample_mflix`-style
dataset, and Hypothesis-based property/fuzz tests for querying it. The suite
can also be pointed at a real MongoDB Atlas cluster, with a `--read-only`
safety switch to guarantee shared/sample data is never modified.

## Project overview

- `docker-compose.yml` — runs `mongo:7` locally on `localhost:27017`
  (root/example credentials) for development and CI.
- `tests/conftest.py` — shared fixtures:
  - `mongo_uri` / `mongo_client` — resolve and open the MongoDB connection.
  - `collection` — an isolated, function-scoped `test_db.test_collection`
    used by the CRUD tests; it is created empty and cleaned up after itself.
  - `sample_mflix_db` / `movies` — a session-scoped `sample_mflix` database,
    seeded from the small representative datasets in `tests/data/*.json`
    (skippable via `--read-only`, see below).
- `tests/test_crud.py` — a full create/read/update/delete flow as one test
  using native pytest 9 subtests.
- `tests/test_movies.py` — simple queries against the seeded `movies`
  collection.
- `tests/test_fuzz_movies.py` — [Hypothesis](https://hypothesis.readthedocs.io/)
  property-based fuzz tests that generate random queries (including dynamic
  comparison/logical-operator combinations) and assert MongoDB's results match
  a manually computed expectation. Uses [Faker](https://faker.readthedocs.io/)
  to generate guaranteed-fake values where appropriate.
- `tests/data/*.json` — small, representative `sample_mflix`-shaped datasets
  (Extended JSON, parsed via `bson.json_util`) used to seed the local
  `sample_mflix` database for tests.

## Setup

Requires Python 3.11+ and Docker (for running MongoDB locally).

```bash
python -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/pre-commit install
```

## Running MongoDB locally

```bash
make up      # docker compose up -d --wait — starts mongo:7 on localhost:27017
make down    # docker compose down         — stops and removes the container
```

Or directly: `docker compose up -d --wait` / `docker compose down`.

## Running tests against a local MongoDB

With the local container running (`make up`), just run:

```bash
make test
# or directly:
.venv/bin/python -m pytest tests/ -v
```

This connects to `mongodb://root:example@localhost:27017` by default (see
`DEFAULT_MONGO_URI` in `tests/conftest.py`), seeds a local `sample_mflix`
database from `tests/data/*.json`, runs the full suite (CRUD + movie queries +
fuzz tests), and cleans up after itself.

You can override the connection target with the `MONGO_URI` environment
variable:

```bash
MONGO_URI="mongodb://root:example@localhost:27017" pytest tests/ -v
```

## Running tests against MongoDB Atlas

⚠️ **Always use `--read-only` when pointing at a shared or real Atlas
cluster.** Without it, the suite will seed/clean up the `sample_mflix`
database — which means it will **delete whatever is currently there**,
including the original sample dataset.

1. Keep your Atlas connection string out of source control. Copy
   `.env.example` to e.g. `atlas.env` (already covered by `.gitignore` via the
   `*.env` pattern) and fill in `MONGO_URI`:

   ```
   MONGO_URI=mongodb+srv://<username>:<password>@<cluster-host>/?retryWrites=true&w=majority
   ```

2. Run pytest, pointing it at that file with `--env-file` **and** passing
   `--read-only`:

   ```bash
   .venv/bin/python -m pytest tests/ -v --env-file atlas.env --read-only
   ```

   Alternatively, export `MONGO_URI` directly instead of using a file:

   ```bash
   MONGO_URI="mongodb+srv://..." pytest tests/ -v --read-only
   ```

What `--read-only` does:

- The `sample_mflix_db` fixture **skips seeding and cleanup entirely** — it
  uses the existing database as-is and never calls `delete_many`/`insert_many`
  against it. This is what protects a real Atlas `sample_mflix` cluster from
  being overwritten or wiped.
- It does **not** affect the CRUD tests — those run against their own
  isolated `test_db.test_collection` (created and torn down per-test), which
  is safe to exercise even against an Atlas cluster.

If you forget `--read-only` against a cluster you care about, the seed/cleanup
cycle **will delete existing data** in `sample_mflix`. If that happens, Atlas
can usually restore the official sample dataset for you (cluster menu → "Load
Sample Dataset", or `atlas clusters loadSampleData <clusterName>` via the
Atlas CLI), or restore from a cloud backup snapshot if your tier has one.

## Tuning Hypothesis (number of examples, deadlines, etc.) from the CLI

The fuzz tests in `tests/test_fuzz_movies.py` use
[Hypothesis](https://hypothesis.readthedocs.io/) to generate randomized
inputs. 

Other useful Hypothesis CLI flags (also provided by the plugin):

```bash
# reproduce a specific run
pytest tests/test_fuzz_movies.py --hypothesis-seed=12345

# print example/shrink statistics
pytest tests/test_fuzz_movies.py --hypothesis-show-statistics
```

## Other Makefile targets

```bash
make help    # list available targets
make lint    # run pre-commit hooks (ruff, mypy, hadolint, etc.) over all files
```
