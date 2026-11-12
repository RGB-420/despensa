from collections import defaultdict
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Path, Response
from sqlalchemy import delete, select, text
from sqlalchemy.orm import Session

from .models import ShoppingItem, ShoppingList
from .units import convert_quantity
from .schemas import InventoryResponse
from .shopping_schemas import (
    ManualItemInput, PurchaseInput, ShoppingItemResponse, ShoppingListInput,
    ShoppingListResponse, TransferInput,
)
from .shopping_service import (
    recalculate_list, resolve_selections, timestamp, transfer_candidates, transfer_purchase,
)

Identifier = Annotated[int, Path(gt=0, le=2**63 - 1)]


def list_response(shopping_list: ShoppingList, items: list[ShoppingItem]) -> ShoppingListResponse:
    purchased = sum(item.purchased_at is not None for item in items)
    return ShoppingListResponse(
        id=shopping_list.id, name=shopping_list.name,
        selected_recipes=shopping_list.selected_recipes, requirements=shopping_list.requirements,
        items=[ShoppingItemResponse.model_validate(item) for item in items],
        pending_count=len(items) - purchased, purchased_count=purchased,
        transferred_count=sum(item.transferred_at is not None for item in items),
        is_complete=bool(items) and purchased == len(items),
        created_at=shopping_list.created_at, updated_at=shopping_list.updated_at,
    )


def shopping_router(get_session) -> APIRouter:
    router = APIRouter(prefix="/shopping-lists", tags=["Shopping lists"])

    def begin_write(session: Session):
        # Serialize read-modify-write operations, including repeated transfers.
        session.execute(text("BEGIN IMMEDIATE"))

    def find_list(list_id: int, session: Session) -> ShoppingList:
        shopping_list = session.get(ShoppingList, list_id)
        if shopping_list is None:
            raise HTTPException(status_code=404, detail="La lista de compra no existe.")
        return shopping_list

    def find_item(list_id: int, item_id: int, session: Session) -> ShoppingItem:
        item = session.get(ShoppingItem, item_id)
        if item is None or item.list_id != list_id:
            raise HTTPException(status_code=404, detail="El producto no pertenece a esta lista.")
        return item

    def detail(shopping_list: ShoppingList, session: Session):
        items = session.scalars(select(ShoppingItem).where(
            ShoppingItem.list_id == shopping_list.id,
        ).order_by(ShoppingItem.id)).all()
        return list_response(shopping_list, list(items))

    @router.get("", response_model=list[ShoppingListResponse])
    def get_lists(session: Session = Depends(get_session)):
        lists = session.scalars(select(ShoppingList).order_by(ShoppingList.id.desc())).all()
        grouped = defaultdict(list)
        for item in session.scalars(select(ShoppingItem).order_by(ShoppingItem.id)):
            grouped[item.list_id].append(item)
        return [list_response(shopping_list, grouped[shopping_list.id]) for shopping_list in lists]

    @router.post("", response_model=ShoppingListResponse, status_code=201)
    def create_list(data: ShoppingListInput, session: Session = Depends(get_session)):
        begin_write(session)
        selected = resolve_selections(data, session)
        now = timestamp()
        shopping_list = ShoppingList(
            name=data.name, selected_recipes=selected, requirements=[],
            created_at=now, updated_at=now,
        )
        session.add(shopping_list)
        session.flush()
        recalculate_list(shopping_list, session)
        session.commit()
        return detail(shopping_list, session)

    @router.get("/{list_id}", response_model=ShoppingListResponse)
    def get_list(list_id: Identifier, session: Session = Depends(get_session)):
        return detail(find_list(list_id, session), session)

    @router.put("/{list_id}", response_model=ShoppingListResponse)
    def update_list(list_id: Identifier, data: ShoppingListInput, session: Session = Depends(get_session)):
        begin_write(session)
        shopping_list = find_list(list_id, session)
        shopping_list.name = data.name
        shopping_list.selected_recipes = resolve_selections(data, session)
        recalculate_list(shopping_list, session)
        session.commit()
        return detail(shopping_list, session)

    @router.delete("/{list_id}", status_code=204)
    def delete_list(list_id: Identifier, session: Session = Depends(get_session)):
        begin_write(session)
        shopping_list = find_list(list_id, session)
        session.execute(delete(ShoppingItem).where(ShoppingItem.list_id == list_id))
        session.delete(shopping_list)
        session.commit()
        return Response(status_code=204)

    @router.post("/{list_id}/recalculate", response_model=ShoppingListResponse)
    def recalculate(list_id: Identifier, session: Session = Depends(get_session)):
        begin_write(session)
        shopping_list = find_list(list_id, session)
        recalculate_list(shopping_list, session)
        session.commit()
        return detail(shopping_list, session)

    @router.post("/{list_id}/items", response_model=ShoppingListResponse, status_code=201)
    def add_manual(list_id: Identifier, data: ManualItemInput, session: Session = Depends(get_session)):
        begin_write(session)
        shopping_list = find_list(list_id, session)
        now = timestamp()
        session.add(ShoppingItem(
            list_id=list_id, source="manual", name=data.name, quantity=str(data.quantity),
            unit=data.unit, created_at=now, updated_at=now,
        ))
        shopping_list.updated_at = now
        session.commit()
        return detail(shopping_list, session)

    @router.put("/{list_id}/items/{item_id}", response_model=ShoppingListResponse)
    def edit_manual(list_id: Identifier, item_id: Identifier, data: ManualItemInput, session: Session = Depends(get_session)):
        begin_write(session)
        shopping_list = find_list(list_id, session)
        item = find_item(list_id, item_id, session)
        if item.source != "manual" or item.purchased_at:
            raise HTTPException(status_code=409, detail="Solo se pueden editar productos manuales pendientes.")
        item.name, item.quantity, item.unit = data.name, str(data.quantity), data.unit
        item.updated_at = shopping_list.updated_at = timestamp()
        session.commit()
        return detail(shopping_list, session)

    @router.delete("/{list_id}/items/{item_id}", response_model=ShoppingListResponse)
    def remove_item(list_id: Identifier, item_id: Identifier, session: Session = Depends(get_session)):
        begin_write(session)
        shopping_list = find_list(list_id, session)
        item = find_item(list_id, item_id, session)
        if item.purchased_at:
            raise HTTPException(status_code=409, detail="Conserva el registro de compra o desmarca la compra antes de quitarlo.")
        session.delete(item)
        shopping_list.updated_at = timestamp()
        session.commit()
        return detail(shopping_list, session)

    @router.put("/{list_id}/items/{item_id}/purchase", response_model=ShoppingListResponse)
    def set_purchase(list_id: Identifier, item_id: Identifier, data: PurchaseInput, session: Session = Depends(get_session)):
        begin_write(session)
        shopping_list = find_list(list_id, session)
        item = find_item(list_id, item_id, session)
        if item.transferred_at:
            raise HTTPException(status_code=409, detail="La compra ya está añadida a la despensa y su registro se conserva.")
        if data.purchased:
            try:
                convert_quantity(data.quantity, data.unit, item.unit)
            except ValueError:
                raise HTTPException(status_code=422, detail="La unidad comprada no es compatible con la del producto.")
            item.purchased_at = item.purchased_at or timestamp()
            item.purchased_quantity = str(data.quantity)
            item.purchased_unit = data.unit
            item.expiration_date = data.expiration_date
        else:
            item.purchased_at = item.purchased_quantity = item.purchased_unit = None
            item.expiration_date = None
        item.updated_at = timestamp()
        session.flush()
        recalculate_list(shopping_list, session)
        session.commit()
        return detail(shopping_list, session)

    @router.get("/{list_id}/items/{item_id}/transfer-options", response_model=list[InventoryResponse])
    def get_transfer_options(list_id: Identifier, item_id: Identifier, session: Session = Depends(get_session)):
        item = find_item(list_id, item_id, session)
        if not item.purchased_at:
            raise HTTPException(status_code=409, detail="Registra primero la compra.")
        return transfer_candidates(item, session)

    @router.post("/{list_id}/items/{item_id}/transfer", response_model=ShoppingListResponse)
    def transfer(list_id: Identifier, item_id: Identifier, data: TransferInput, session: Session = Depends(get_session)):
        begin_write(session)
        shopping_list = find_list(list_id, session)
        item = find_item(list_id, item_id, session)
        if item.transferred_at:
            return detail(shopping_list, session)
        transfer_purchase(item, data, session)
        recalculate_list(shopping_list, session)
        session.commit()
        return detail(shopping_list, session)

    return router
