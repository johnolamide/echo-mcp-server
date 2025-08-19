"""
API routes for Bolt Food integration.
"""
from fastapi import APIRouter, HTTPException, Depends
from typing import Dict, Any, List
import logging

from app.models.user import User
from app.services.bolt_food_service import bolt_food_service
from app.routers.services import get_current_user
from typing import Dict, Any, List
    
logger = logging.getLogger(__name__)

router = APIRouter(prefix="/bolt-food", dependencies=[Depends(get_current_user)])


@router.post("/menu/push", operation_id="push_menu")
async def push_menu(
    provider_id: str,
    menu_data: Dict[str, Any],
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """Push menu to Bolt Food."""
    try:
        result = await bolt_food_service.push_menu(provider_id, menu_data)
        logger.info(f"Menu pushed successfully for provider {provider_id} by user {current_user.id}")
        return result
    except Exception as e:
        logger.error(f"Failed to push menu for provider {provider_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to push menu: {str(e)}")


@router.get("/menu/{provider_id}", operation_id="get_menu")
async def get_menu(
    provider_id: str,
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """Get menu from Bolt Food."""
    try:
        result = await bolt_food_service.get_menu(provider_id)
        logger.info(f"Menu retrieved successfully for provider {provider_id} by user {current_user.id}")
        return result
    except Exception as e:
        logger.error(f"Failed to get menu for provider {provider_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get menu: {str(e)}")


@router.post("/menu/availability", operation_id="update_menu_availability")
async def update_menu_availability(
    provider_id: str,
    availability_updates: List[Dict[str, Any]],
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """Update menu item availability."""
    try:
        result = await bolt_food_service.update_menu_item_availability(
            provider_id, availability_updates
        )
        logger.info(f"Menu availability updated for provider {provider_id} by user {current_user.id}")
        return result
    except Exception as e:
        logger.error(f"Failed to update menu availability for provider {provider_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to update availability: {str(e)}")


@router.post("/orders/{order_id}/accept", operation_id="accept_order")
async def accept_order(
    order_id: str,
    provider_id: str,
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """Accept an incoming order."""
    try:
        result = await bolt_food_service.accept_order(order_id, provider_id)
        logger.info(f"Order {order_id} accepted for provider {provider_id} by user {current_user.id}")
        return result
    except Exception as e:
        logger.error(f"Failed to accept order {order_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to accept order: {str(e)}")


@router.post("/orders/{order_id}/reject", operation_id="reject_order")
async def reject_order(
    order_id: str,
    provider_id: str,
    reason: str,
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """Reject an incoming order."""
    try:
        result = await bolt_food_service.reject_order(order_id, provider_id, reason)
        logger.info(f"Order {order_id} rejected for provider {provider_id} by user {current_user.id}")
        return result
    except Exception as e:
        logger.error(f"Failed to reject order {order_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to reject order: {str(e)}")


@router.post("/orders/{order_id}/ready", operation_id="mark_order_ready")
async def mark_order_ready(
    order_id: str,
    provider_id: str,
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """Mark order as ready for pickup."""
    try:
        result = await bolt_food_service.mark_order_ready_for_pickup(order_id, provider_id)
        logger.info(f"Order {order_id} marked ready for provider {provider_id} by user {current_user.id}")
        return result
    except Exception as e:
        logger.error(f"Failed to mark order {order_id} as ready: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to mark order ready: {str(e)}")


@router.post("/orders/{order_id}/picked-up", operation_id="mark_order_picked_up")
async def mark_order_picked_up(
    order_id: str,
    provider_id: str,
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """Mark order as picked up."""
    try:
        result = await bolt_food_service.mark_order_picked_up(order_id, provider_id)
        logger.info(f"Order {order_id} marked picked up for provider {provider_id} by user {current_user.id}")
        return result
    except Exception as e:
        logger.error(f"Failed to mark order {order_id} as picked up: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to mark order picked up: {str(e)}")


@router.post("/orders/{order_id}/delivered", operation_id="mark_order_delivered")
async def mark_order_delivered(
    order_id: str,
    provider_id: str,
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """Mark order as delivered."""
    try:
        result = await bolt_food_service.mark_order_delivered(order_id, provider_id)
        logger.info(f"Order {order_id} marked delivered for provider {provider_id} by user {current_user.id}")
        return result
    except Exception as e:
        logger.error(f"Failed to mark order {order_id} as delivered: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to mark order delivered: {str(e)}")


@router.post("/providers/{provider_id}/start-accepting", operation_id="start_accepting_orders")
async def start_accepting_orders(
    provider_id: str,
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """Start accepting orders for a provider."""
    try:
        result = await bolt_food_service.start_accepting_orders(provider_id)
        logger.info(f"Provider {provider_id} started accepting orders by user {current_user.id}")
        return result
    except Exception as e:
        logger.error(f"Failed to start accepting orders for provider {provider_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to start accepting orders: {str(e)}")


@router.post("/providers/{provider_id}/pause", operation_id="pause_orders")
async def pause_orders(
    provider_id: str,
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """Pause orders for a provider."""
    try:
        result = await bolt_food_service.pause_orders(provider_id)
        logger.info(f"Provider {provider_id} paused orders by user {current_user.id}")
        return result
    except Exception as e:
        logger.error(f"Failed to pause orders for provider {provider_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to pause orders: {str(e)}")


@router.post("/providers/{provider_id}/schedule", operation_id="update_provider_schedule")
async def update_provider_schedule(
    provider_id: str,
    schedule: Dict[str, Any],
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """Update provider schedule."""
    try:
        result = await bolt_food_service.update_provider_schedule(provider_id, schedule)
        logger.info(f"Provider {provider_id} schedule updated by user {current_user.id}")
        return result
    except Exception as e:
        logger.error(f"Failed to update schedule for provider {provider_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to update schedule: {str(e)}")


@router.post("/dine-in/orders", operation_id="create_dine_in_order")
async def create_dine_in_order(
    provider_id: str,
    order_data: Dict[str, Any],
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """Create a dine-in order."""
    try:
        result = await bolt_food_service.create_dine_in_order(provider_id, order_data)
        logger.info(f"Dine-in order created for provider {provider_id} by user {current_user.id}")
        return result
    except Exception as e:
        logger.error(f"Failed to create dine-in order for provider {provider_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to create dine-in order: {str(e)}")


@router.post("/dine-in/orders/{order_id}/finalize", operation_id="finalize_dine_in_order")
async def finalize_dine_in_order(
    order_id: str,
    provider_id: str,
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """Finalize a dine-in order."""
    try:
        result = await bolt_food_service.finalize_dine_in_order(order_id, provider_id)
        logger.info(f"Dine-in order {order_id} finalized for provider {provider_id} by user {current_user.id}")
        return result
    except Exception as e:
        logger.error(f"Failed to finalize dine-in order {order_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to finalize dine-in order: {str(e)}")
