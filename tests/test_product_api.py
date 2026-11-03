import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.routers import product_routes
from app.services.product_service import ProductService


@pytest.fixture
def client(monkeypatch: pytest.MonkeyPatch) -> TestClient:
    monkeypatch.setattr(product_routes, "product_service", ProductService())
    return TestClient(app)


@pytest.fixture
def product_payload() -> dict[str, object]:
    return {
        "name": "Headphones",
        "description": "Wireless headphones",
        "price": 25.5,
        "stock_quantity": 20,
        "category": "Accessories",
        "status": "Active",
    }


def test_health_endpoint(client: TestClient) -> None:
    response = client.get("/")

    assert response.status_code == 200
    assert response.json() == {"message": "Welcome to the ShopEase Product Service"}


def test_default_product_service_uses_in_memory_repository() -> None:
    service = ProductService()

    created = service.create_product(
        name="In-memory item",
        description=None,
        price=1,
        stock_quantity=0,
        category="Test",
        status="Active",
    )

    assert service.get_product(created.id) == created


def test_create_product_returns_created_product(
    client: TestClient,
    product_payload: dict[str, object],
) -> None:
    response = client.post("/api/products/", json=product_payload)

    assert response.status_code == 201
    created = response.json()
    assert created["id"] == 1
    assert created["name"] == product_payload["name"]
    assert created["price"] == product_payload["price"]
    assert created["created_at"]


@pytest.mark.parametrize(
    "changes",
    [
        {"name": "   "},
        {"price": 0},
        {"price": -1},
        {"price": 0.00001},
        {"price": 1_000_000_000_000_000},
        {"stock_quantity": -1},
        {"status": "Pending"},
    ],
)
def test_create_product_rejects_invalid_fields(
    client: TestClient,
    product_payload: dict[str, object],
    changes: dict[str, object],
) -> None:
    response = client.post(
        "/api/products/",
        json={**product_payload, **changes},
    )

    assert response.status_code == 422


def test_create_product_rejects_missing_and_extra_fields(
    client: TestClient,
    product_payload: dict[str, object],
) -> None:
    missing_name = {key: value for key, value in product_payload.items() if key != "name"}

    assert client.post("/api/products/", json=missing_name).status_code == 422
    assert (
        client.post(
            "/api/products/",
            json={**product_payload, "unexpected": True},
        ).status_code
        == 422
    )


def test_list_products_filters_category_and_paginates(
    client: TestClient,
    product_payload: dict[str, object],
) -> None:
    client.post("/api/products/", json=product_payload)
    client.post(
        "/api/products/",
        json={**product_payload, "name": "Mouse", "category": "Electronics"},
    )
    client.post(
        "/api/products/",
        json={**product_payload, "name": "Keyboard"},
    )

    response = client.get("/api/products/?category=accessories&skip=1&limit=1")

    assert response.status_code == 200
    assert len(response.json()) == 1
    assert response.json()[0]["name"] == "Keyboard"


def test_get_product_returns_404_for_unknown_id(client: TestClient) -> None:
    assert client.get("/api/products/999").status_code == 404


@pytest.mark.parametrize("product_id", ["not-an-id", "0", "-1"])
def test_get_product_rejects_malformed_or_non_positive_id(
    client: TestClient,
    product_id: str,
) -> None:
    assert client.get(f"/api/products/{product_id}").status_code == 422


def test_update_product_preserves_creation_date(
    client: TestClient,
    product_payload: dict[str, object],
) -> None:
    created = client.post("/api/products/", json=product_payload).json()
    updated_payload = {**product_payload, "name": "Updated Headphones"}

    response = client.put(
        f"/api/products/{created['id']}",
        json=updated_payload,
    )

    assert response.status_code == 200
    assert response.json()["name"] == "Updated Headphones"
    assert response.json()["created_at"] == created["created_at"]
    assert client.put("/api/products/999", json=updated_payload).status_code == 404


def test_delete_product_returns_no_content_and_removes_product(
    client: TestClient,
    product_payload: dict[str, object],
) -> None:
    created = client.post("/api/products/", json=product_payload).json()

    response = client.delete(f"/api/products/{created['id']}")

    assert response.status_code == 204
    assert response.content == b""
    assert client.get(f"/api/products/{created['id']}").status_code == 404
    assert client.delete("/api/products/999").status_code == 404
