from typing import Annotated

from fastapi import APIRouter, Query

from backend.app.db import DbSession
from backend.app.schemas.sales import SalesFilters, SalesSummary
from backend.app.services.sales import get_sales_summary

router = APIRouter(prefix="/sales", tags=["Sales"])


@router.get("/summary")
def sales_summary(filters: Annotated[SalesFilters, Query()], session: DbSession) -> SalesSummary:
    return get_sales_summary(session, filters)
