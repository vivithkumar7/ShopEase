from datetime import datetime, timezone
from threading import Lock
from typing import Literal, Protocol, cast

import mssql_python

from app.db.connection import connect_database
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


def _product_from_row(row: tuple[object, ...]) -> Product:
    created_at = row[7]
    if not isinstance(created_at, datetime):
        raise TypeError("Database returned an invalid product creation timestamp")
    if created_at.tzinfo is None:
        created_at = created_at.replace(tzinfo=timezone.utc)

    return Product(
        id=int(row[0]),
        name=str(row[1]),
        description=None if row[2] is None else str(row[2]),
        price=float(row[3]),
        stock_quantity=int(row[4]),
        category=str(row[5]),
        status=cast(Literal["Active", "Inactive"], row[6]),
        created_at=created_at,
    )


_PRODUCT_COLUMNS = """
    [id], [name], [description], [price], [stock_quantity],
    [category], [status], [created_at]
"""


class SqlProductRepository:
    def __init__(self, connection_factory=connect_database) -> None:
        self._connection_factory = connection_factory

    def list_products(
        self,
        *,
        category: str | None = None,
        skip: int = 0,
        limit: int = 100,
    ) -> list[Product]:
        connection = self._connection_factory()
        cursor = connection.cursor()
        try:
            if category is None:
                cursor.execute(
                    f"""
                    SELECT {_PRODUCT_COLUMNS}
                    FROM [shopease].[products]
                    ORDER BY [id]
                    OFFSET ? ROWS FETCH NEXT ? ROWS ONLY
                    """,
                    skip,
                    limit,
                )
            else:
                cursor.execute(
                    f"""
                    SELECT {_PRODUCT_COLUMNS}
                    FROM [shopease].[products]
                    WHERE [category] = ?
                    ORDER BY [id]
                    OFFSET ? ROWS FETCH NEXT ? ROWS ONLY
                    """,
                    category.strip(),
                    skip,
                    limit,
                )
            return [_product_from_row(row) for row in cursor.fetchall()]
        finally:
            cursor.close()
            connection.close()

    def get_product(self, product_id: int) -> Product | None:
        connection = self._connection_factory()
        cursor = connection.cursor()
        try:
            cursor.execute(
                f"""
                SELECT {_PRODUCT_COLUMNS}
                FROM [shopease].[products]
                WHERE [id] = ?
                """,
                product_id,
            )
            row = cursor.fetchone()
            return None if row is None else _product_from_row(row)
        finally:
            cursor.close()
            connection.close()

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
        connection = self._connection_factory()
        cursor = connection.cursor()
        try:
            cursor.execute(
                f"""
                SET NOCOUNT ON;
                INSERT INTO [shopease].[products]
                    ([name], [description], [price], [stock_quantity],
                     [category], [status])
                VALUES (?, ?, ?, ?, ?, ?);
                SELECT {_PRODUCT_COLUMNS}
                FROM [shopease].[products]
                WHERE [id] = CONVERT(int, SCOPE_IDENTITY());
                """,
                name,
                description,
                price,
                stock_quantity,
                category,
                status,
            )
            row = cursor.fetchone()
            if row is None:
                raise RuntimeError("Product insert succeeded without returning its row")
            connection.commit()
            return _product_from_row(row)
        except Exception:
            connection.rollback()
            raise
        finally:
            cursor.close()
            connection.close()

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
        connection = self._connection_factory()
        cursor = connection.cursor()
        try:
            cursor.execute(
                f"""
                SET NOCOUNT ON;
                UPDATE [shopease].[products]
                SET [name] = ?, [description] = ?, [price] = ?,
                    [stock_quantity] = ?, [category] = ?, [status] = ?
                WHERE [id] = ?;
                SELECT {_PRODUCT_COLUMNS}
                FROM [shopease].[products]
                WHERE [id] = ?;
                """,
                name,
                description,
                price,
                stock_quantity,
                category,
                status,
                product_id,
                product_id,
            )
            row = cursor.fetchone()
            connection.commit()
            return None if row is None else _product_from_row(row)
        except Exception:
            connection.rollback()
            raise
        finally:
            cursor.close()
            connection.close()

    def delete_product(self, product_id: int) -> bool:
        connection = self._connection_factory()
        cursor = connection.cursor()
        try:
            cursor.execute(
                """
                SET NOCOUNT ON;
                DELETE FROM [shopease].[products]
                WHERE [id] = ?;
                SELECT @@ROWCOUNT;
                """,
                product_id,
            )
            row = cursor.fetchone()
            if row is None:
                raise RuntimeError("Product delete did not return its row count")
            connection.commit()
            return int(row[0]) > 0
        except Exception:
            connection.rollback()
            raise
        finally:
            cursor.close()
            connection.close()


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
