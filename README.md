# mongo-fuzzer

A small Python playground for testing MongoDB: CRUD tests against a local
MongoDB instance, fixtures that load a representative `sample_mflix`-style
dataset, and Hypothesis-based property/fuzz tests for querying it. The suite
can also be pointed at a real MongoDB Atlas cluster safely — all seeded
collections use a `test_` prefix so they never overwrite original Atlas data.

## Project overview

- `docker-compose.yml` — runs `mongo:7` locally on `localhost:27017`
  (root/example credentials) for development and CI.
- `tests/conftest.py` — shared fixtures:
  - `mongo_uri` / `mongo_client` — resolve and open the MongoDB connection.
  - `collection` — an isolated, function-scoped `test_db.test_collection`
    used by the CRUD tests; it is created empty and cleaned up after itself.
  - `sample_mflix_db` / `movies` — a session-scoped `sample_mflix` database,
    seeded from the small representative datasets in `tests/data/*.json` into
    `test_`-prefixed collections (e.g. `test_movies`, `test_comments`, …).
    The fixture creates indexes on queried fields after seeding and cleans up
    after the session.
- `tests/test_crud.py` — a full create/read/update/delete flow as one test
  using native pytest 9 subtests.
- `tests/test_movies.py` — simple queries against the seeded `test_movies`
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

Requires Python (see `.python-version` for the exact version used by this
project) and Docker (for running MongoDB locally).

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
database from `tests/data/*.json` into `test_`-prefixed collections, runs the
full suite (CRUD + movie queries + fuzz tests), and cleans up after itself.

You can override the connection target with the `MONGO_URI` environment
variable:

```bash
MONGO_URI="mongodb://root:example@localhost:27017" pytest tests/ -v
```

## Running tests against MongoDB Atlas

The test suite is safe to run against a real Atlas cluster without any extra
flags. All seeded collections use a `test_` prefix (`test_movies`,
`test_comments`, etc.), so they never touch the original Atlas `sample_mflix`
collections. The CRUD test always runs against `test_db.test_collection`.

1. Keep your Atlas connection string out of source control. Copy `.env.example`
   to e.g. `atlas.env` (already covered by `.gitignore` via `*.env`) and fill
   in `MONGO_URI`:

   ```
   MONGO_URI=mongodb+srv://<username>:<password>@<cluster-host>/?retryWrites=true&w=majority
   ```

2. Run pytest, pointing it at that file with `--env-file`:

   ```bash
   .venv/bin/python -m pytest tests/ -v --env-file atlas.env
   ```

   Alternatively, export `MONGO_URI` directly instead of using a file:

   ```bash
   MONGO_URI="mongodb+srv://..." pytest tests/ -v
   ```

## Tuning Hypothesis (number of examples, deadlines, etc.) from the CLI

The fuzz tests in `tests/test_fuzz_movies.py` use
[Hypothesis](https://hypothesis.readthedocs.io/) to generate randomized
inputs. `tests/conftest.py` registers a few named profiles that control things
like how many examples are generated per test:

| Profile    | `max_examples` | Notes                              |
|------------|---------------:|------------------------------------|
| `default`  | 100            | used when nothing else is selected |
| `dev`      | 10             | fast feedback while iterating      |
| `ci`       | 200            | more thorough, no deadline         |
| `thorough` | 1000           | deep fuzzing run, no deadline      |

Select a profile from the command line with the `--hypothesis-profile` flag
(provided automatically by the Hypothesis pytest plugin):

```bash
.venv/bin/python -m pytest tests/test_fuzz_movies.py -v --hypothesis-profile=dev
.venv/bin/python -m pytest tests/test_fuzz_movies.py -v --hypothesis-profile=thorough
```

Or via the `HYPOTHESIS_PROFILE` environment variable:

```bash
HYPOTHESIS_PROFILE=thorough pytest tests/test_fuzz_movies.py -v
```

Other useful Hypothesis CLI flags (also provided by the plugin):

```bash
# pin a specific seed for reproducible runs (CI prints the seed it used)
pytest tests/test_fuzz_movies.py --hypothesis-seed=12345

# print per-test example/shrink statistics (always enabled in CI)
pytest tests/test_fuzz_movies.py --hypothesis-show-statistics
```

In CI, a random seed is generated at the start of each run and passed via
`--hypothesis-seed`. The seed value is visible in the CI logs, so a failing
run can be reproduced locally with `--hypothesis-seed=<value>`.

## Other Makefile targets

```bash
make help    # list available targets
make lint    # run pre-commit hooks (ruff, mypy, hadolint, etc.) over all files
make format  # run ruff formatter
```
