from datetime import UTC, datetime
from decimal import Decimal
from typing import Annotated, Self

from pydantic import AfterValidator, AwareDatetime, BaseModel, Field, model_validator

MAX_INT = 2_147_483_647
PositiveId = Annotated[int, Field(gt=0, le=MAX_INT)]
Money = Annotated[Decimal, Field(ge=0, le=Decimal("9999999.99"), decimal_places=2)]


def as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    try:
        return value.astimezone(UTC)
    except OverflowError as exc:
        raise ValueError("Timestamp is out of range in UTC") from exc


UtcTimestamp = Annotated[datetime, AfterValidator(as_utc)]
InputTimestamp = Annotated[AwareDatetime, AfterValidator(as_utc)]


def validate_date_range(start: datetime | None, end: datetime | None) -> None:
    if start is not None and end is not None and start >= end:
        raise ValueError("start must be earlier than end")


class Pagination(BaseModel):
    limit: int = Field(20, ge=1, le=100)
    offset: int = Field(0, ge=0, le=MAX_INT)


class Page[T](BaseModel):
    items: list[T]
    total: int
    limit: int
    offset: int


class DateRange(BaseModel):
    start: InputTimestamp
    end: InputTimestamp

    @model_validator(mode="after")
    def check_range(self) -> Self:
        validate_date_range(self.start, self.end)
        return self
