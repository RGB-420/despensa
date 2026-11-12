from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException, Path, Response
from sqlalchemy import select
from sqlalchemy.orm import Session

from .models import InventoryItem
from .schemas import InventoryInput, InventoryResponse

ItemId = Annotated[int, Path(gt=0, le=2**63 - 1)]
ExpirationFilter = Literal["all", "expired", "expiring_soon", "not_expired", "no_date"]
StockFilter = Literal["all", "in_stock", "out_of_stock", "low_stock"]


def inventory_router(get_session) -> APIRouter:
    router = APIRouter(prefix="/inventory", tags=["Inventory"])

    def find_item(item_id: int, session: Session) -> InventoryItem:
        item = session.get(InventoryItem, item_id)
        if item is None:
            raise HTTPException(status_code=404, detail="Product not found.")
        return item

    @router.get("", response_model=list[InventoryResponse])
    def list_items(
        q: str = "",
        expiration: ExpirationFilter = "all",
        stock: StockFilter = "all",
        session: Session = Depends(get_session),
    ):
        today = date.today()
        results = []
        for item in session.scalars(select(InventoryItem).order_by(InventoryItem.id.desc())):
            if q.strip().casefold() not in item.name.casefold():
                continue
            expires = item.expiration_date
            expiration_matches = {
                "all": True,
                "expired": expires is not None and expires < today,
                "expiring_soon": expires is not None and today <= expires <= today + timedelta(days=7),
                "not_expired": expires is None or expires >= today,
                "no_date": expires is None,
            }
            quantity = Decimal(item.quantity)
            stock_matches = {
                "all": True,
                "in_stock": quantity > 0,
                "out_of_stock": quantity == 0,
                "low_stock": item.minimum_stock is not None and quantity <= Decimal(item.minimum_stock),
            }
            if expiration_matches[expiration] and stock_matches[stock]:
                results.append(item)
        return results

    @router.get("/{item_id}", response_model=InventoryResponse)
    def get_item(item_id: ItemId, session: Session = Depends(get_session)):
        return find_item(item_id, session)

    @router.post("", response_model=InventoryResponse, status_code=201)
    def create_item(data: InventoryInput, session: Session = Depends(get_session)):
        timestamp = datetime.now(UTC).isoformat()
        values = data.model_dump()
        values["quantity"] = str(data.quantity)
        values["minimum_stock"] = None if data.minimum_stock is None else str(data.minimum_stock)
        item = InventoryItem(**values, created_at=timestamp, updated_at=timestamp)
        session.add(item)
        session.commit()
        return item

    @router.put("/{item_id}", response_model=InventoryResponse)
    def update_item(item_id: ItemId, data: InventoryInput, session: Session = Depends(get_session)):
        item = find_item(item_id, session)
        for field, value in data.model_dump().items():
            if field in ("quantity", "minimum_stock") and value is not None:
                value = str(value)
            setattr(item, field, value)
        item.updated_at = datetime.now(UTC).isoformat()
        session.commit()
        return item

    @router.delete("/{item_id}", status_code=204)
    def delete_item(item_id: ItemId, session: Session = Depends(get_session)):
        session.delete(find_item(item_id, session))
        session.commit()
        return Response(status_code=204)

    return router

