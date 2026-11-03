from fastapi import APIRouter, HTTPException, Path, Query, Response, status

from app.schemas.product_schema import ProductCreate, ProductResponse, ProductUpdate
from app.services.product_service import product_service

router = APIRouter(prefix="/api/products", tags=["products"])


@router.post(
    "/",
    response_model=ProductResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_product(product: ProductCreate) -> ProductResponse:
    return product_service.create_product(**product.model_dump())


@router.get("/", response_model=list[ProductResponse])
def list_products(
    category: str | None = Query(default=None, min_length=1, max_length=100),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=500),
) -> list[ProductResponse]:
    return product_service.list_products(category=category, skip=skip, limit=limit)


@router.get("/{product_id}", response_model=ProductResponse)
def get_product(product_id: int = Path(gt=0)) -> ProductResponse:
    product = product_service.get_product(product_id)
    if product is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found",
        )
    return product


@router.put("/{product_id}", response_model=ProductResponse)
def update_product(
    product: ProductUpdate,
    product_id: int = Path(gt=0),
) -> ProductResponse:
    updated_product = product_service.update_product(
        product_id,
        **product.model_dump(),
    )
    if updated_product is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found",
        )
    return updated_product


@router.delete(
    "/{product_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
)
def delete_product(product_id: int = Path(gt=0)) -> Response:
    if not product_service.delete_product(product_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found",
        )
    return Response(status_code=status.HTTP_204_NO_CONTENT)
