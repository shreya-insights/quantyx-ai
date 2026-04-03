import math
from typing import TypeVar

from app.schemas.common import PaginatedResponse

T = TypeVar("T")


def paginate(data: list[T], total: int, page: int, page_size: int) -> PaginatedResponse[T]:
    total_pages = math.ceil(total / page_size) if page_size > 0 else 1
    return PaginatedResponse(
        data=data,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )
