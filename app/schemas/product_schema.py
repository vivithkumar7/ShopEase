from datetime import datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class ProductCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1, max_length=100)
    description: str | None = Field(default=None, max_length=1000)
    price: float = Field(
        gt=0,
        lt=1_000_000_000_000_000,
        allow_inf_nan=False,
        strict=True,
    )
    stock_quantity: int = Field(ge=0, strict=True)
    category: str = Field(min_length=1, max_length=100)
    status: Literal["Active", "Inactive"]

    @field_validator("name", "description", "category")
    @classmethod
    def value_must_not_be_blank(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized_value = value.strip()
        if not normalized_value:
            raise ValueError("Value must not be blank")
        return normalized_value

    @field_validator("price")
    @classmethod
    def price_must_fit_database_precision(cls, value: float) -> float:
        if Decimal(str(value)).as_tuple().exponent < -4:
            raise ValueError("Price must have at most 4 decimal places")
        return value


class ProductUpdate(ProductCreate):
    pass


class ProductResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    description: str | None
    price: float
    stock_quantity: int
    category: str
    status: Literal["Active", "Inactive"]
    created_at: datetime
