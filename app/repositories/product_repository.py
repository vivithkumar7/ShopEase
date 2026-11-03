from datetime import datetime, timezone
from threading import Lock
from typing import Literal, Protocol

from app.models.product_model import Product


class ProductRepository(Protocol):
    def list_products(
        self,
        *,
        category: str | None,
        skip: int,
        limit: int,
    ) -> list[Product]: ...

    def get_product(self, product_id: int) -> Product | None: ...

    def create_product(
        self,
        *,
        name: str,
        description: str | None,
        price: float,
        stock_quantity: int,
        category: str,
        status: Literal["Active", "Inactive"],
    ) -> Product: ...

    def update_product(
        self,
        product_id: int,
        *,
        name: str,
        description: str | None,
        price: float,
        stock_quantity: int,
        category: str,
        status: Literal["Active", "Inactive"],
    ) -> Product | None: ...

    def delete_product(self, product_id: int) -> bool: ...


class InMemoryProductRepository:
    def __init__(self) -> None:
        self._products: dict[int, Product] = {}
        self._next_id = 1
        self._lock = Lock()

    def list_products(
        self,
        *,
        category: str | None = None,
        skip: int = 0,
        limit: int = 100,
    ) -> list[Product]:
        with self._lock:
            products = list(self._products.values())
        if category is not None:
            normalized_category = category.strip().casefold()
            products = [
                product
                for product in products
                if product.category.casefold() == normalized_category
            ]
        return products[skip : skip + limit]

    def get_product(self, product_id: int) -> Product | None:
        with self._lock:
            return self._products.get(product_id)

    def create_product(
        self,
        *,
        name: str,
        description: str | None,
        price: float,
        stock_quantity: int,
        category: str,
        status: Literal["Active", "Inactive"],
    ) -> Product:
        with self._lock:
            product = Product(
                id=self._next_id,
                name=name,
                description=description,
                price=price,
                stock_quantity=stock_quantity,
                category=category,
                status=status,
                created_at=datetime.now(timezone.utc),
            )
            self._products[product.id] = product
            self._next_id += 1
            return product

    def update_product(
        self,
        product_id: int,
        *,
        name: str,
        description: str | None,
        price: float,
        stock_quantity: int,
        category: str,
        status: Literal["Active", "Inactive"],
    ) -> Product | None:
        with self._lock:
            existing_product = self._products.get(product_id)
            if existing_product is None:
                return None

            product = Product(
                id=product_id,
                name=name,
                description=description,
                price=price,
                stock_quantity=stock_quantity,
                category=category,
                status=status,
                created_at=existing_product.created_at,
            )
            self._products[product_id] = product
            return product

    def delete_product(self, product_id: int) -> bool:
        with self._lock:
            return self._products.pop(product_id, None) is not None
