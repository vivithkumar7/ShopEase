# ShopEase Product Service — Implementation Guide

## 1. Assignment scope

This project is a practical FastAPI product catalog with five working CRUD
endpoints. It uses Python in-memory storage and runs in Docker. **It does not
use MySQL, Azure SQL, or any database.** Products exist only while the
application process is running; restarting the container clears them.

## 2. Project structure

```text
app/
  main.py                         creates the FastAPI application
  config/settings.py              app name/version settings
  models/product_model.py          Product data class
  schemas/product_schema.py        validated API input/output
  repositories/product_repository.py
                                  repository protocol and in-memory storage
  services/product_service.py       product business operations
  routers/product_routes.py         HTTP endpoint definitions
scripts/smoke_test.py               tests the live Docker-hosted API
tests/test_product_api.py           automated API behavior tests
Dockerfile                          builds the application image
compose.yaml                        starts the service on port 8003
requirements.txt                    runtime dependencies
requirements-dev.txt                test dependencies
```

## 3. Application startup and request flow

`app/main.py` creates the FastAPI app, registers the product router, and
provides a root health route. Uvicorn runs this app inside the container.

For a product request:

1. Uvicorn receives HTTP traffic.
2. FastAPI matches the HTTP method and URL to a route.
3. Pydantic validates the path, query, or JSON body.
4. The route calls `ProductService`.
5. The service calls the in-memory `ProductRepository`.
6. FastAPI serializes the result as JSON and returns the route's status code.

The route layer does not store data itself. The service layer does not parse
HTTP. The repository owns the product collection.

## 4. Product model and validation

`app/models/product_model.py` defines a product with:

- `id`: generated integer ID
- `name`: required product name
- `description`: optional text
- `price`: positive number with at most four decimal places
- `stock_quantity`: non-negative integer
- `category`: required category name
- `status`: `Active` or `Inactive`
- `created_at`: UTC creation timestamp

`app/schemas/product_schema.py` defines `ProductCreate`, `ProductUpdate`, and
`ProductResponse`. Input schemas reject blank names/categories, invalid
prices, negative stock, unsupported statuses, missing fields, and unexpected
extra fields. A PUT is a full replacement of editable product fields, not a
partial PATCH.

## 5. Repository and business logic

`app/repositories/product_repository.py` defines the operations expected by
the service and implements them with `InMemoryProductRepository`. A
threading lock protects reads and writes to the shared dictionary. The
repository assigns IDs, filters categories without case sensitivity,
applies pagination, preserves `created_at` when updating, and reports whether
an item was deleted.

`app/services/product_service.py` delegates create, list, get, update, and
delete operations through the repository protocol. The application singleton
uses the default in-memory repository. Tests can create a new service to get
an isolated product collection.

## 6. Five REST endpoints

All product routes use `/api/products/`.

| Method | Path | Behavior | Success |
|---|---|---|---|
| POST | `/api/products/` | Create from a JSON body | 201 Created |
| GET | `/api/products/` | List; optional category/skip/limit | 200 OK |
| GET | `/api/products/{product_id}` | Get one product | 200 OK |
| PUT | `/api/products/{product_id}` | Replace editable fields | 200 OK |
| DELETE | `/api/products/{product_id}` | Delete one product | 204 No Content |

A valid product JSON body is:

```json
{
  "name": "Headphones",
  "description": "Wireless headphones",
  "price": 25.5,
  "stock_quantity": 20,
  "category": "Accessories",
  "status": "Active"
}
```

Invalid bodies and non-positive or malformed IDs return 422. A valid but
unknown ID returns 404. Unexpected server errors are logged and return a
generic 500 response.

## 7. Build and run with Docker

Start Docker Desktop and open PowerShell in the project directory:

```powershell
docker compose up -d --build
docker compose ps
docker compose logs --tail 30 product-service
```

The Compose file builds the local Dockerfile, publishes host port 8003 to
container port 8003, and starts Uvicorn on `0.0.0.0:8003`. No database
environment variables or database container are required.

Open <http://localhost:8003/docs> for Swagger UI. The service root is
<http://localhost:8003/>.

To stop the container:

```powershell
docker compose down
```

## 8. Required Docker-hosted CRUD test

The pytest API tests run in-process, so they are not the only evidence. Run
the smoke script from the host against the published Docker port:

```powershell
.\.venv\Scripts\python.exe scripts\smoke_test.py --base-url http://localhost:8003
```

The script sends HTTP requests to the running container. It tests:

1. Health response.
2. Rejection of invalid product bodies.
3. POST create and generated ID.
4. GET one product.
5. GET list, case-insensitive category filter, and pagination.
6. PUT update and preservation of the creation timestamp.
7. Malformed, non-positive, and unknown IDs.
8. DELETE and confirmation that the product is gone.

Each successful assertion prints a `PASS` line with the method, path, and
status code. A failed connection, unexpected response, or failed assertion
raises an error and exits non-zero.

An equivalent curl check for the health route is:

```powershell
curl.exe -i http://localhost:8003/
```

Use Swagger or Postman for manual checks. In Postman set the base URL to
`http://localhost:8003`, choose raw JSON for POST/PUT, and use the ID returned
by POST in subsequent requests.

## 9. Automated tests and expected behavior

Install development dependencies and run:

```powershell
python -m pip install -r requirements-dev.txt
python -m pytest -q
```

The test suite checks health, all CRUD operations, validation, filtering,
pagination, not-found behavior, and timestamps. The Docker smoke test
independently checks the live HTTP application. To inspect Docker logs:

```powershell
docker compose logs --tail 50 product-service
```

An empty list is a valid response when no products have been created.
Products are intentionally temporary and disappear when the container is
recreated or the Python process restarts.

## 10. Team walkthrough and GitHub submission

Each team member should be able to explain, without only reading this guide:

- How `ProductCreate` validates a POST request.
- How `product_routes.py` delegates to `ProductService`.
- How the repository assigns IDs and stores products.
- Why a deleted or unknown ID returns 404.
- How the smoke script tests the Docker-hosted API over HTTP.
- Why restarting this in-memory service clears its catalog.

Recommended group exercise: one member starts Docker, another creates and
updates a product with Swagger, and another explains the repository and
verifies the delete with a GET.

For GitHub, include source, tests, Docker files, documentation, the report,
and sanitized evidence. The `evidence/` folder contains the actual Swagger
screenshot, Docker-hosted HTTP smoke-test output, container status, and access
logs. Never add `.env`, passwords, GitHub tokens, `.venv`, or caches.

```powershell
git status
git add README.md PROJECT_GUIDE.md app scripts tests Dockerfile compose.yaml requirements.txt requirements-dev.txt evidence reports
git commit -m "Complete in-memory Docker product CRUD"
git push
```
