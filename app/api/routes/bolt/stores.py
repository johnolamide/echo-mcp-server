"""
API routes for Bolt Stores integration.
"""
from fastapi import APIRouter, HTTPException, Depends
from typing import Dict, Any, List
import logging

from app.services.bolt_stores_service import bolt_stores_service
from app.routers.services import get_current_user
from app.models.user import User

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/bolt-stores", dependencies=[Depends(get_current_user)])


# Menu Integration
@router.get("/menu/{provider_id}", operation_id="get_menu")
async def get_menu(
    provider_id: str,
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """Get menu from Bolt Stores."""
    try:
        result = await bolt_stores_service.get_menu(provider_id)
        logger.info(f"Stores menu retrieved for provider {provider_id} by user {current_user.id}")
        return result
    except Exception as e:
        logger.error(f"Failed to get stores menu for provider {provider_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get menu: {str(e)}")


# Order Management
@router.post("/orders/{order_id}/accept", operation_id="accept_order")
async def accept_order(
    order_id: str,
    provider_id: str,
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """Accept an incoming stores order."""
    try:
        result = await bolt_stores_service.accept_order(order_id, provider_id)
        logger.info(f"Stores order {order_id} accepted for provider {provider_id} by user {current_user.id}")
        return result
    except Exception as e:
        logger.error(f"Failed to accept stores order {order_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to accept order: {str(e)}")


@router.post("/orders/{order_id}/reject", operation_id="reject_order")
async def reject_order(
    order_id: str,
    provider_id: str,
    reason: str,
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """Reject an incoming stores order."""
    try:
        result = await bolt_stores_service.reject_order(order_id, provider_id, reason)
        logger.info(f"Stores order {order_id} rejected for provider {provider_id} by user {current_user.id}")
        return result
    except Exception as e:
        logger.error(f"Failed to reject stores order {order_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to reject order: {str(e)}")


@router.post("/orders/{order_id}/ready", operation_id="mark_order_ready")
async def mark_order_ready(
    order_id: str,
    provider_id: str,
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """Mark stores order as ready for pickup."""
    try:
        result = await bolt_stores_service.mark_order_ready_for_pickup(order_id, provider_id)
        logger.info(f"Stores order {order_id} marked ready for provider {provider_id} by user {current_user.id}")
        return result
    except Exception as e:
        logger.error(f"Failed to mark stores order {order_id} as ready: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to mark order ready: {str(e)}")


@router.post("/orders/{order_id}/ready-with-items", operation_id="mark_order_ready_with_items")
async def mark_order_ready_with_items(
    order_id: str,
    provider_id: str,
    items: List[Dict[str, Any]],
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """Mark stores order with specific items as ready for pickup."""
    try:
        result = await bolt_stores_service.mark_order_with_items_ready_for_pickup(
            order_id, provider_id, items
        )
        logger.info(f"Stores order {order_id} marked ready with items for provider {provider_id} by user {current_user.id}")
        return result
    except Exception as e:
        logger.error(f"Failed to mark stores order {order_id} ready with items: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to mark order ready with items: {str(e)}")


# Provider Management
@router.post("/providers/{provider_id}/start-accepting", operation_id="start_accepting_orders")
async def start_accepting_orders(
    provider_id: str,
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """Start accepting orders for a stores provider."""
    try:
        result = await bolt_stores_service.start_accepting_orders(provider_id)
        logger.info(f"Stores provider {provider_id} started accepting orders by user {current_user.id}")
        return result
    except Exception as e:
        logger.error(f"Failed to start accepting orders for stores provider {provider_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to start accepting orders: {str(e)}")


@router.post("/providers/{provider_id}/pause", operation_id="pause_orders")
async def pause_orders(
    provider_id: str,
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """Pause orders for a stores provider."""
    try:
        result = await bolt_stores_service.pause_orders(provider_id)
        logger.info(f"Stores provider {provider_id} paused orders by user {current_user.id}")
        return result
    except Exception as e:
        logger.error(f"Failed to pause orders for stores provider {provider_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to pause orders: {str(e)}")


# Warehouse Management
@router.post("/warehouse/quantities", operation_id="update_warehouse_quantities")
async def update_quantities(
    provider_id: str,
    sku_quantities: List[Dict[str, Any]],
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """Update SKU quantities in warehouse."""
    try:
        result = await bolt_stores_service.update_menu_quantity(provider_id, sku_quantities)
        logger.info(f"SKU quantities updated for provider {provider_id} by user {current_user.id}")
        return result
    except Exception as e:
        logger.error(f"Failed to update quantities for provider {provider_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to update quantities: {str(e)}")


# PIM Integration - Products
@router.post("/pim/products/create", operation_id="create_products")
async def create_products(
    provider_id: str,
    products: List[Dict[str, Any]],
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """Create or fully overwrite products."""
    try:
        result = await bolt_stores_service.create_products(provider_id, products)
        logger.info(f"Products created for provider {provider_id} by user {current_user.id}")
        return result
    except Exception as e:
        logger.error(f"Failed to create products for provider {provider_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to create products: {str(e)}")


@router.post("/pim/products/edit", operation_id="edit_products")
async def edit_products(
    provider_id: str,
    products: List[Dict[str, Any]],
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """Partially update products."""
    try:
        result = await bolt_stores_service.edit_products(provider_id, products)
        logger.info(f"Products edited for provider {provider_id} by user {current_user.id}")
        return result
    except Exception as e:
        logger.error(f"Failed to edit products for provider {provider_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to edit products: {str(e)}")


@router.get("/pim/products/import-status/{task_id}", operation_id="get_import_status")
async def get_import_status(
    provider_id: str,
    task_id: str,
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """Get product import status."""
    try:
        result = await bolt_stores_service.get_product_import_status(provider_id, task_id)
        logger.info(f"Import status retrieved for task {task_id} by user {current_user.id}")
        return result
    except Exception as e:
        logger.error(f"Failed to get import status for task {task_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get import status: {str(e)}")


@router.post("/pim/products/import-apply/{task_id}", operation_id="apply_import")
async def apply_import(
    provider_id: str,
    task_id: str,
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """Apply pending product import."""
    try:
        result = await bolt_stores_service.apply_product_import(provider_id, task_id)
        logger.info(f"Import applied for task {task_id} by user {current_user.id}")
        return result
    except Exception as e:
        logger.error(f"Failed to apply import for task {task_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to apply import: {str(e)}")


@router.post("/pim/products/delist", operation_id="delist_products")
async def delist_products(
    provider_id: str,
    product_ids: List[str],
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """Delist products."""
    try:
        result = await bolt_stores_service.delist_products(provider_id, product_ids)
        logger.info(f"Products delisted for provider {provider_id} by user {current_user.id}")
        return result
    except Exception as e:
        logger.error(f"Failed to delist products for provider {provider_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to delist products: {str(e)}")


# PIM Integration - Pricing
@router.post("/pim/prices/import", operation_id="import_prices")
async def import_prices(
    provider_id: str,
    prices: List[Dict[str, Any]],
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """Import selling prices."""
    try:
        result = await bolt_stores_service.import_prices(provider_id, prices)
        logger.info(f"Prices imported for provider {provider_id} by user {current_user.id}")
        return result
    except Exception as e:
        logger.error(f"Failed to import prices for provider {provider_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to import prices: {str(e)}")


@router.post("/pim/discount-prices/import", operation_id="import_discount_prices")
async def import_discount_prices(
    provider_id: str,
    discount_prices: List[Dict[str, Any]],
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """Import discount selling prices."""
    try:
        result = await bolt_stores_service.import_discount_prices(provider_id, discount_prices)
        logger.info(f"Discount prices imported for provider {provider_id} by user {current_user.id}")
        return result
    except Exception as e:
        logger.error(f"Failed to import discount prices for provider {provider_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to import discount prices: {str(e)}")


# PIM Integration - Fees
@router.get("/pim/fees/{provider_id}", operation_id="list_fees")
async def list_fees(
    provider_id: str,
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """List fees for a provider."""
    try:
        result = await bolt_stores_service.list_fees(provider_id)
        logger.info(f"Fees listed for provider {provider_id} by user {current_user.id}")
        return result
    except Exception as e:
        logger.error(f"Failed to list fees for provider {provider_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to list fees: {str(e)}")


@router.post("/pim/fees/{fee_id}", operation_id="update_fee")
async def update_fee(
    provider_id: str,
    fee_id: int,
    fee_data: Dict[str, Any],
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """Update a fee."""
    try:
        result = await bolt_stores_service.update_fee(provider_id, fee_id, fee_data)
        logger.info(f"Fee {fee_id} updated for provider {provider_id} by user {current_user.id}")
        return result
    except Exception as e:
        logger.error(f"Failed to update fee {fee_id} for provider {provider_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to update fee: {str(e)}")
