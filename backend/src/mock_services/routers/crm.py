"""
File: backend/src/mock_services/routers/crm.py
Purpose: Mock CRM endpoints — customer lookup / order list / ticket lookup.
Category: Mock services / routers
Scope: Phase 51 / Sprint 51.0 Day 1.5

Description:
    Three read-only endpoints simulating Salesforce/D365-style CRM access:
    - GET /mock/crm/customers/{id}    — single customer by id
    - GET /mock/crm/orders            — order list with optional customer_id filter
    - GET /mock/crm/tickets/{id}      — single ticket by id

    All data sourced from in-memory SeedDB (loader). 404 if id not found.

Created: 2026-04-30 (Sprint 51.0 Day 1)
Last Modified: 2026-04-30
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query

from mock_services.data.loader import SeedDB, get_db
from mock_services.schemas import Customer, Order, Ticket

router = APIRouter(prefix="/mock/crm", tags=["mock-crm"])


@router.get("/customers/{customer_id}", response_model=Customer)
async def get_customer(customer_id: str, db: SeedDB = Depends(get_db)) -> Customer:
    raw = db.customers.get(customer_id)
    if raw is None:
        raise HTTPException(status_code=404, detail=f"customer {customer_id} not found")
    return Customer(**raw)


@router.get("/orders", response_model=list[Order])
async def list_orders(
    customer_id: str | None = Query(default=None),
    limit: int = Query(default=20, ge=1, le=100),
    db: SeedDB = Depends(get_db),
) -> list[Order]:
    items = list(db.orders.values())
    if customer_id is not None:
        items = [o for o in items if o["customer_id"] == customer_id]
    items.sort(key=lambda o: o["created_at"], reverse=True)
    return [Order(**o) for o in items[:limit]]


@router.get("/tickets/{ticket_id}", response_model=Ticket)
async def get_ticket(ticket_id: str, db: SeedDB = Depends(get_db)) -> Ticket:
    raw = db.tickets.get(ticket_id)
    if raw is None:
        raise HTTPException(status_code=404, detail=f"ticket {ticket_id} not found")
    return Ticket(**raw)
