# Product Service: Step-by-Step Guide

This guide explains the project files, request flow, validation, persistence,
migrations, Docker setup, and API testing. Product data is stored in Azure SQL
Database and survives application/container restarts.

## 1. Project structure

```text
shopease-product-service/
|-- app/
|   |-- main.py
|   |-- config/
|   |   |-- __init__.py
|   |   `-- settings.py
|   |-- db/
|   |   |-- connection.py
|   |   `-- migrations/
|   |       `-- versions/
|   |           `-- v001_products.py
|   |-- models/
|   |   |-- __init__.py
|   |   `-- product_model.py
|   |-- routers/
|   |   |-- __init__.py
|   |   `-- product_routes.py
|   |-- schemas/
|   |   |-- __init__.py
|   |   `-- product_schema.py
|   |-- repositories/
|   |   `-- product_repository.py
|   `-- services/
|       |-- __init__.py
|       `-- product_service.py
|-- scripts/
|   `-- smoke_test.py
|-- tests/
|   |-- test_database_safety.py
|   `-- test_product_api.py
|-- .dockerignore
|-- .env.example
|-- .env
|-- .gitignore
|-- compose.yaml
|-- Dockerfile
|-- README.md
|-- PROJECT_GUIDE.md
|-- requirements-dev.txt
|-- requirements.txt
```

The `__init__.py` files mark component folders as Python packages. `main.py`
assembles the application; routers define HTTP endpoints; schemas validate
input/output; models represent products; repositories access SQL; services
coordinate catalog operations; migrations manage schema changes; and settings
load environment configuration.

## 2. How a request moves through the application

1. Uvicorn listens for HTTP traffic and serves the FastAPI `app` object.
2. FastAPI matches the URL and method to a registered route.
3. FastAPI and Pydantic validate request parameters and JSON bodies against
   the declared types and schemas.
4. The route calls `product_service` with validated values.
5. The service calls the SQL repository, which opens a database connection
   and executes parameterized statements against `[shopease].[products]`.
6. FastAPI converts the returned product to the response schema and JSON.
7. FastAPI returns the endpoint's declared status code.

## 3. Source walkthrough

### `app/main.py`

- `import logging` provides the application logger.
- `FastAPI`, `Request`, and `JSONResponse` are used to create the app and
  implement a consistent response for unexpected server errors.
- The settings and product router imports connect configuration and API
  endpoints to the application.
- `logger = logging.getLogger(__name__)` creates a module-specific logger.
- `app = FastAPI(...)` creates the app. Its title and version come from
  settings; the description appears in generated API documentation.
- `app.include_router(product_router)` registers all product endpoints.
- `@app.exception_handler(Exception)` registers a handler for otherwise
  unhandled exceptions. The handler logs request method/path and exception
  details on the server, but returns only a generic message to the client.
- `@app.get("/", tags=["health"])` adds a small root/health endpoint. Its
  function returns a JSON welcome message.

### `app/config/settings.py`

- `Path` locates the project-level `.env` file regardless of the current
  working directory.
- `BaseSettings` and `SettingsConfigDict` come from Pydantic Settings.
- `Settings` defines the application name and version defaults.
- `model_config` tells Pydantic Settings to load UTF-8 values from `.env` and
  ignore unrelated environment variables.
- `settings = Settings()` creates the shared settings instance at import time.
  Environment variables can override the default values.

### `app/models/product_model.py`

- `dataclass` generates a convenient initializer for the product record.
- `datetime` represents the creation timestamp.
- `Literal` restricts the model's status type to the two supported values.
- `Product` holds an ID, name, optional description, price, stock quantity,
  category, status, and creation timestamp. It is the service data object
  corresponding to `[shopease].[products]`.

### `app/schemas/product_schema.py`

- `BaseModel`, `Field`, and `ConfigDict` define Pydantic schemas and field
  constraints; `field_validator` adds custom text validation.
- `ProductCreate` is the input schema used for new products.
- `extra="forbid"` rejects unexpected keys instead of silently accepting them.
- `name` and `category` must be strings of 1–100 characters.
- `description` is optional and may contain at most 1000 characters.
- `price` must be a strict numeric value greater than zero, below
  `1000000000000000`, and have no more than four decimal places; these limits
  match the persisted `DECIMAL(19,4)` range and avoid silent rounding.
  Infinity and NaN are rejected.
- `stock_quantity` must be a strict integer greater than or equal to zero.
- `status` accepts only `"Active"` or `"Inactive"`.
- `value_must_not_be_blank` trims leading/trailing whitespace and rejects
  empty or whitespace-only name/category values. A missing description remains
  `None`; if supplied, a whitespace-only description is rejected.
- `ProductUpdate` reuses the create schema, so `PUT` requires the full product
  representation rather than a partial patch.
- `ProductResponse` defines the public output fields. `from_attributes=True`
  lets Pydantic create a response from the `Product` dataclass.

### `app/services/product_service.py`

- `ProductService` delegates create, list, get, update, and delete operations
  through the `ProductRepository` protocol.
- `InMemoryProductRepository` is used when tests create `ProductService()`;
  this keeps API unit tests isolated from a live database.
- The application singleton injects `SqlProductRepository`, so live API
  requests use the database-backed store.

### `app/repositories/product_repository.py`

- `ProductRepository` specifies the operations the service needs, without
  coupling it to a particular storage implementation.
- `SqlProductRepository` binds all values as parameters; user text and IDs are
  never interpolated into SQL.
- `list_products` applies category filtering, stable ID ordering, and SQL
  Server `OFFSET/FETCH` pagination in the database.
- `create_product` relies on the database identity and UTC timestamp default,
  then reads the inserted row in the same connection/transaction.
- `update_product` replaces editable columns without changing the product ID
  or creation timestamp.
- `delete_product` returns whether the database deleted a row.
- Reads and writes close their cursor and connection; writes commit only after
  the SQL statement and returned row/count have been validated.

### `app/db/connection.py`

- Connection details are loaded from `SQL_HOST`, `SQL_DATABASE`,
  `SQL_AUTHENTICATION`, `SQL_USER`, and `SQL_PASSWORD`.
- It rejects missing targets and `master`, escapes ODBC values, keeps Azure
  TLS certificate validation enabled, and never logs credentials.
- New database connections retry only documented transient connection errors
  with bounded exponential delay. Query and transaction failures are surfaced
  rather than replayed on an uncertain connection.
- Microsoft driver's process-local connection pool is configured once, before
  the first connection, with a maximum of 25 connections and a five-minute
  idle timeout; account for this per worker/replica.
- Microsoft `mssql-python` bundles its own ODBC driver; the Docker image does
  not need an OS-level ODBC driver installation.

### `app/db/migrate.py` and `app/db/migrations/versions/`

- `v001_products.py` is the first ordered, forward-only migration. It creates
  the product table with bounded Unicode fields, a decimal price, UTC creation
  timestamp, primary key, validated checks, and category index.
- The schema, migration history, and migration lock table are all under
  `[shopease]`; migration state is not placed in `dbo`.
- The command requires `--database`, and it must equal `SQL_DATABASE`. Before
  DDL it verifies `DB_NAME()` and `SERVERPROPERTY('EngineEdition') = 5`.
- A database-scoped, transaction-owned application lock serializes runners;
  `[shopease].[__migration_lock]` also holds a row lock inside the same
  transaction.
- All migrations, schema checks, and history rows are one transaction. Each
  migration is checksum-verified and its postcondition is checked before its
  history record is inserted. Exceptions roll back and propagate; app startup
  never runs migrations.
- On every run, applied checksums are verified and the latest migration's
  postcondition is re-checked against the live schema. Changed migration files,
  missing versions, a wrong database, or failed postconditions stop the
  command with a non-zero exit.

### `app/routers/product_routes.py`

- `APIRouter` groups related endpoints under the `/api/products` prefix.
- `create_product` accepts a validated `ProductCreate`, sends its fields to
  the service, and returns a `ProductResponse` with HTTP `201`.
- `list_products` accepts optional category filtering and bounded pagination
  (`skip >= 0`, `1 <= limit <= 500`) and returns a list.
- `get_product` requires a positive integer ID. It returns the product or
  raises HTTP `404` when that ID is absent.
- `update_product` accepts a complete validated `ProductUpdate`, replaces the
  product, and returns `404` if no product has that ID.
- `delete_product` returns an empty HTTP `204` response after a successful
  removal and HTTP `404` for an unknown ID.
- FastAPI automatically returns HTTP `422` for invalid request data, including
  malformed/non-positive IDs and invalid JSON fields.

### Dependencies and container files

- `requirements.txt` lists FastAPI, Pydantic Settings, and Uvicorn with
  compatible version ranges plus Microsoft's `mssql-python` driver.
  `pip install -r requirements.txt` installs them into the active virtual
  environment or Docker image.
- `Dockerfile` starts from the small Python 3.12 image, sets `/service` as
  the working directory, copies and installs requirements before copying app
  source (so Docker can reuse the dependency layer), documents port 8003,
  and runs Uvicorn on `0.0.0.0:8003` so the container port can be published.
- `.dockerignore` keeps local environment files, secret-like files, virtual
  environments, caches, Git data, and temporary files out of the Docker build
  context. The image only needs the dependencies and `app` package.
- `.gitignore` excludes local `.env`, Python environments, bytecode, and test
  caches from Git.
- `compose.yaml` defines the Compose service, requires a target host/database,
  passes authentication from environment variables, publishes port 8003, and
  restarts the container unless it is stopped.

### `scripts/smoke_test.py`

- The imports use only Python's standard library: `argparse` parses the
  service URL, `json` handles request/response bodies, and `urllib` sends HTTP
  requests without adding a test dependency.
- `send_request` builds the URL and JSON request, captures both successful and
  HTTP error responses, and raises a clear error if the service cannot be
  reached.
- `expect_status` stops the test with a useful message when a response has an
  unexpected HTTP status.
- `run_smoke_tests` first checks the health route, then confirms invalid
  inputs are rejected, creates a product, tests read/filter/pagination/update,
  checks invalid and missing IDs, and finally deletes the created item and
  confirms it can no longer be fetched.
- `main` accepts `--base-url`, defaulting to Docker's local published port.
  The `if __name__ == "__main__"` guard lets the file be run as a script
  without running tests merely by importing it.

### `tests/test_product_api.py`

- The `client` fixture gives each test a fresh `ProductService`, preventing
  products from leaking between tests, and wraps the FastAPI app in its test
  client.
- The `product_payload` fixture provides a valid example product.
- The tests exercise health, successful create/read/update/delete operations,
  category filtering, pagination, missing fields, extra fields, invalid
  values and IDs, not-found responses, and preservation of `created_at`.
- `pytest.mark.parametrize` runs the same validation/ID checks against several
  invalid inputs.
- These are in-process API tests and do not require a running Uvicorn or Docker
  container. Use `scripts/smoke_test.py` to test an independently running app.

## 4. Set up and run locally

Run these commands from the project directory in PowerShell. Install Python
3.11 or newer first:

```powershell
py --version
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m pip check
Copy-Item .env.example .env
# Edit .env with your Azure SQL target and authentication details.
python -m app.db.migrate --database ShopEase
uvicorn app.main:app --reload --port 8000
```

For SQL authentication, fill in `SQL_HOST`, `SQL_DATABASE`,
`SQL_AUTHENTICATION=SqlPassword`, `SQL_USER`, and `SQL_PASSWORD` in the
untracked `.env`. For a local developer authenticated with Azure CLI, set
`SQL_AUTHENTICATION=ActiveDirectoryDefault` and omit SQL username/password.
Use the actual configured application database name in the migration command.
The runner refuses `master`, checks the live database name and Azure SQL engine
edition, and never runs on API startup.

For the automated API test suite, install its development dependencies and
run pytest:

```powershell
python -m pip install -r requirements-dev.txt
python -m pytest -q
```

Open <http://127.0.0.1:8000/docs> for Swagger UI. Open a second PowerShell
window in the project directory to run the smoke test against the local
server:

```powershell
.\.venv\Scripts\python.exe scripts\smoke_test.py --base-url http://127.0.0.1:8000
```

## 5. Build and run with Docker

Make sure Docker Desktop is running with its Linux container engine. Copy
`.env.example` to `.env` only if no `.env` exists, configure the database
connection without overwriting existing secrets, then from the project
directory:

```powershell
if (-not (Test-Path .env)) { Copy-Item .env.example .env }
docker build -t shopease-product-service .
docker image ls shopease-product-service
docker run --rm --env-file .env shopease-product-service python -m app.db.migrate --database ShopEase
docker run -d --name shopease-product-container --env-file .env -p 8003:8003 shopease-product-service
docker ps
docker logs shopease-product-container
```

The migration command must finish successfully before starting the API
container. It runs only against the database named by both `SQL_DATABASE` and
`--database`.

The `-p 8003:8003` option maps host port 8003 to container port 8003. Visit
<http://localhost:8003/docs> to use the container-hosted Swagger UI. Verify
the API against the running container with:

```powershell
.\.venv\Scripts\python.exe scripts\smoke_test.py --base-url http://localhost:8003
```

The smoke test checks successful creation, retrieval, update, and deletion;
case-insensitive category filtering; pagination; invalid payloads; invalid
IDs; and missing/deleted products. It uses only Python's standard library and
does not add project dependencies.

To operate the container:

```powershell
docker stop shopease-product-container
docker start shopease-product-container
docker rm -f shopease-product-container
```

To use Docker Compose instead, run `docker compose build`,
`docker compose run --rm product-service python -m app.db.migrate --database ShopEase`,
`docker compose up -d`, `docker compose ps`, `docker compose logs`, and
`docker compose down`. Do not run the standalone and Compose versions
simultaneously unless you change the container name or host port.

## 6. Test with Swagger UI or Postman

For Postman, use `http://localhost:8003` as the base URL when testing Docker.
For local Uvicorn, use `http://127.0.0.1:8000`. For `POST` and `PUT`, select
**Body > raw > JSON** and send:

```json
{
  "name": "Headphones",
  "description": "Wireless headphones",
  "price": 2500,
  "stock_quantity": 20,
  "category": "Accessories",
  "status": "Active"
}
```

Suggested test order:

1. `POST /api/products/` with the valid body. Expect `201`; note the returned
   `id`.
2. Repeat the POST with `"name": "   "`, `"price": -1`, and
   `"stock_quantity": -1`. Each request should return `422`.
3. `GET /api/products/`; expect a JSON list.
4. `GET /api/products/?category=accessories&skip=0&limit=10`; category
   filtering is case-insensitive.
5. `GET /api/products/{id}` using the returned ID; expect `200`.
6. `GET /api/products/999999` or a non-integer ID; expect `404` for a valid
   but unknown integer and `422` for a malformed ID.
7. `PUT /api/products/{id}` with the complete valid body; expect `200`.
8. `DELETE /api/products/{id}`; expect `204` and an empty response body.
9. `GET /api/products/{id}` again; expect `404`.

## 7. Git and GitHub

The project directory can be initialized as a Git repository and published to
a GitHub repository named `shopease-product-service`. First create an empty
repository on GitHub, then use:

```powershell
git init
git add .
git commit -m "Build ShopEase product service"
git branch -M main
git remote add origin https://github.com/<your-user>/shopease-product-service.git
git push -u origin main
```

Replace `<your-user>` with your GitHub username. `.gitignore` excludes `.env`
and Python environments; `.dockerignore` excludes local configuration,
secrets, caches, and Git metadata from Docker build context. Never commit
credentials. GitHub authentication may require the GitHub CLI, a browser
sign-in, or a personal access token configured through Git Credential Manager;
do not put a token in the remote URL.

## 8. Screenshots and submission evidence

After running the Docker commands, capture your own screenshots of:

- `docker ps` showing the running product-service container.
- Swagger UI at `http://localhost:8003/docs`.
- Successful create/read/update/delete requests and validation errors.
- `docker logs shopease-product-container`.
- The GitHub repository page after the push completes.

Screenshots, a published GitHub repository, and a running Docker container
must be produced from your own Docker/GitHub environment; they are not
generated by this source project.
