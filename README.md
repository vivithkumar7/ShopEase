# ShopEase Product Service

A Docker-ready FastAPI application implementing all five product CRUD
operations with **in-memory storage**. This practical assignment does not use
MySQL or any other database. Data is kept in the running process and resets
when the container restarts.

## Technology

- Python 3.11+
- FastAPI, Uvicorn, Pydantic
- Docker and Docker Compose
- pytest, Swagger UI, and Postman
- Git and GitHub

## Project structure

```text
app/
  config/settings.py
  models/product_model.py
  repositories/product_repository.py
  routers/product_routes.py
  schemas/product_schema.py
  services/product_service.py
  main.py
scripts/smoke_test.py
tests/test_product_api.py
Dockerfile
compose.yaml
requirements.txt
requirements-dev.txt
README.md
PROJECT_GUIDE.md
```

Routes, schemas, business logic, and storage are separate. See
[PROJECT_GUIDE.md](PROJECT_GUIDE.md) for a file-by-file explanation, test
procedure, and team discussion questions.

## Product API

Base URL when running Docker: `http://localhost:8003`

| Method | Path | Purpose | Success |
|---|---|---|---|
| POST | `/api/products/` | Create a product | 201 |
| GET | `/api/products/` | List, filter, and paginate | 200 |
| GET | `/api/products/{product_id}` | Get one product | 200 |
| PUT | `/api/products/{product_id}` | Replace product details | 200 |
| DELETE | `/api/products/{product_id}` | Delete a product | 204 |

Category filtering is case-insensitive. List pagination accepts `skip` and
`limit`. Unknown IDs return 404; invalid request data or non-positive IDs
return 422.

Example request for POST and PUT:

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

Price must be positive with at most four decimal places; stock must be a
non-negative integer; status must be `Active` or `Inactive`. Names and
categories cannot be blank. Extra request fields are rejected.

## Run and test in Docker

From PowerShell in this project folder, with Docker Desktop running:

```powershell
docker compose up -d --build
docker compose ps
```

Open Swagger UI at <http://localhost:8003/docs>. To exercise **all five CRUD
endpoints on the Docker-hosted application** (not just in an in-process test),
run from the project folder:

```powershell
.\.venv\Scripts\python.exe scripts\smoke_test.py --base-url http://localhost:8003
```

The script sends real HTTP requests to the published container port and checks
health, create, list/filter/pagination, read, update, delete, invalid inputs,
and not-found responses. It exits with an error if a connection or assertion
fails. You can also use Postman with `http://localhost:8003` as the base URL.

Useful checks:

```powershell
curl.exe -i http://localhost:8003/
curl.exe -i http://localhost:8003/api/products/
docker compose logs --tail 50 product-service
```

Stop the service with `docker compose down`. Since storage is in memory, data
is intentionally temporary and is cleared when the application process
restarts.

## Run automated tests

```powershell
python -m pip install -r requirements-dev.txt
python -m pytest -q
```

These tests verify API validation and behavior. The smoke-test script above
separately verifies the API over HTTP through Docker.

## GitHub submission

The source repository should include application code, tests, Docker files,
documentation, and sanitized evidence. Never commit `.env`, passwords, access
tokens, `.venv`, or caches. Capture your own Docker and Swagger screenshots
after running the container, then add only those non-secret evidence files.

```powershell
git status
git add README.md PROJECT_GUIDE.md app scripts tests Dockerfile compose.yaml requirements.txt requirements-dev.txt evidence reports
git commit -m "Complete in-memory Docker product CRUD"
git push
```
