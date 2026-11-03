from dataclasses import dataclass
from datetime import datetime
from typing import Literal


@dataclass
class Product:
    id: int
    name: str
    description: str | None
    price: float
    stock_quantity: int
    category: str
    status: Literal["Active", "Inactive"]
    created_at: datetime
