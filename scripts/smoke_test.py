import argparse
import json
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


def send_request(
    base_url: str,
    method: str,
    path: str,
    body: dict[str, Any] | None = None,
) -> tuple[int, Any]:
    data = None if body is None else json.dumps(body).encode("utf-8")
    request = Request(
        f"{base_url.rstrip('/')}{path}",
        data=data,
        method=method,
        headers={"Content-Type": "application/json"},
    )
    try:
        response = urlopen(request, timeout=5)
    except HTTPError as error:
        response = error
    except URLError as error:
        raise RuntimeError(f"Could not reach {base_url}: {error.reason}") from error

    with response:
        content = response.read()
        payload = json.loads(content) if content else None
        return response.status, payload


def expect_status(
    actual_status: int,
    expected_status: int,
    method: str,
    path: str,
) -> None:
    if actual_status != expected_status:
        raise AssertionError(
            f"{method} {path}: expected HTTP {expected_status}, "
            f"received HTTP {actual_status}"
        )
    print(f"PASS {method} {path} -> HTTP {actual_status}")


def run_smoke_tests(base_url: str) -> None:
    status_code, health = send_request(base_url, "GET", "/")
    expect_status(status_code, 200, "GET", "/")
    assert health["message"] == "Welcome to the ShopEase Product Service"

    product = {
        "name": "Smoke Test Headphones",
        "description": "Created by the API smoke test",
        "price": 25.5,
        "stock_quantity": 3,
        "category": "Smoke Test",
        "status": "Active",
    }

    invalid_products = (
        {**product, "name": "   "},
        {**product, "price": -1},
        {**product, "price": 0},
        {**product, "stock_quantity": -1},
        {**product, "status": "Pending"},
        {key: value for key, value in product.items() if key != "name"},
    )
    for invalid_product in invalid_products:
        status_code, _ = send_request(
            base_url, "POST", "/api/products/", invalid_product
        )
        expect_status(status_code, 422, "POST", "/api/products/")

    status_code, created = send_request(
        base_url, "POST", "/api/products/", product
    )
    expect_status(status_code, 201, "POST", "/api/products/")
    product_id = created["id"]

    status_code, retrieved = send_request(
        base_url, "GET", f"/api/products/{product_id}"
    )
    expect_status(status_code, 200, "GET", f"/api/products/{product_id}")
    assert retrieved["id"] == product_id

    status_code, filtered = send_request(
        base_url, "GET", "/api/products/?category=smoke%20test"
    )
    expect_status(status_code, 200, "GET", "/api/products/?category=smoke%20test")
    assert any(item["id"] == product_id for item in filtered)

    status_code, paginated = send_request(
        base_url, "GET", "/api/products/?skip=0&limit=1"
    )
    expect_status(status_code, 200, "GET", "/api/products/?skip=0&limit=1")
    assert len(paginated) <= 1

    updated_product = {**product, "name": "Updated Smoke Test Headphones"}
    status_code, updated = send_request(
        base_url, "PUT", f"/api/products/{product_id}", updated_product
    )
    expect_status(status_code, 200, "PUT", f"/api/products/{product_id}")
    assert updated["name"] == updated_product["name"]
    assert updated["created_at"] == created["created_at"]

    for invalid_path in ("/api/products/not-an-id", "/api/products/0"):
        status_code, _ = send_request(base_url, "GET", invalid_path)
        expect_status(status_code, 422, "GET", invalid_path)

    missing_product_path = "/api/products/9223372036854775807"
    status_code, _ = send_request(base_url, "GET", missing_product_path)
    expect_status(status_code, 404, "GET", missing_product_path)

    status_code, _ = send_request(
        base_url, "DELETE", f"/api/products/{product_id}"
    )
    expect_status(status_code, 204, "DELETE", f"/api/products/{product_id}")

    status_code, _ = send_request(
        base_url, "GET", f"/api/products/{product_id}"
    )
    expect_status(status_code, 404, "GET", f"/api/products/{product_id}")

    print(f"All product API smoke tests passed against {base_url.rstrip('/')}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Exercise the ShopEase Product Service API."
    )
    parser.add_argument(
        "--base-url",
        default="http://127.0.0.1:8003",
        help="Service origin, for example http://localhost:8003",
    )
    args = parser.parse_args()
    run_smoke_tests(args.base_url)


if __name__ == "__main__":
    main()
