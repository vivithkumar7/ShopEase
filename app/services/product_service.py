from typing import Literal

from app.models.product_model import Product
from app.repositories.product_repository import (
    InMemoryProductRepository,
    ProductRepository,
)


class ProductService:
    def __init__(self, repository: ProductRepository | None = None) -> None:
        self._repository = repository or InMemoryProductRepository()

    def list_products(
        self,
        *,
        category: str | None = None,
        skip: int = 0,
        limit: int = 100,
    ) -> list[Product]:
        return self._repository.list_products(
            category=category,
            skip=skip,
            limit=limit,
        )

    def get_product(self, product_id: int) -> Product | None:
        return self._repository.get_product(product_id)

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
        return self._repository.create_product(
            name=name,
            description=description,
            price=price,
            stock_quantity=stock_quantity,
            category=category,
            status=status,
        )

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
        return self._repository.update_product(
            product_id,
            name=name,
            description=description,
            price=price,
            stock_quantity=stock_quantity,
            category=category,
            status=status,
        )

    def delete_product(self, product_id: int) -> bool:
        return self._repository.delete_product(product_id)


product_service = ProductService()
