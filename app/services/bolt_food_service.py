"""
Bolt Food API service implementation.
"""
import json
import hmac
import hashlib
import base64
import logging
from typing import Dict, Any, Optional
import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)


class BoltFoodService:
    """Service class for interacting with Bolt Food API."""
    
    def __init__(self):
        self.api_url = settings.bolt_food_api_url
        self.integrator_id = settings.bolt_food_integrator_id
        self.secret_key = settings.bolt_food_secret_key
        self.timeout = 60
        
    def _generate_hmac_signature(self, payload: str) -> str:
        """Generate HMAC-SHA256 signature for request authentication."""
        if not self.secret_key:
            raise ValueError("Bolt Food secret key not configured")
            
        key = self.secret_key.encode('utf-8')
        message = payload.encode('utf-8')
        signature = hmac.new(key, message, hashlib.sha256).digest()
        return base64.b64encode(signature).decode('utf-8')
    
    def _get_headers(self, payload: str) -> Dict[str, str]:
        """Get headers with authentication for Bolt Food API requests."""
        if not self.integrator_id:
            raise ValueError("Bolt Food integrator ID not configured")
            
        signature = self._generate_hmac_signature(payload)
        
        return {
            'Content-Type': 'application/json',
            'x-external-integrator-id': self.integrator_id,
            'x-server-authorization-hmac-sha256': signature
        }
    
    async def _make_request(
        self, 
        endpoint: str, 
        payload: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Make authenticated request to Bolt Food API."""
        url = f"{self.api_url}{endpoint}"
        payload_str = json.dumps(payload)
        headers = self._get_headers(payload_str)
        
        logger.info(f"Making request to Bolt Food API: {endpoint}")
        
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(url, content=payload_str, headers=headers)
                response.raise_for_status()
                return response.json()
        except httpx.HTTPStatusError as e:
            logger.error(f"Bolt Food API error: {e.response.status_code} - {e.response.text}")
            raise
        except Exception as e:
            logger.error(f"Request to Bolt Food API failed: {e}")
            raise
    
    async def push_menu(self, provider_id: str, menu_data: Dict[str, Any]) -> Dict[str, Any]:
        """Push menu to Bolt Food."""
        payload = {
            "provider_id": provider_id,
            "menu": menu_data
        }
        return await self._make_request("/genericClient/pushMenu", payload)
    
    async def get_menu(self, provider_id: str) -> Dict[str, Any]:
        """Get menu from Bolt Food."""
        payload = {
            "provider_id": provider_id
        }
        return await self._make_request("/genericClient/getMenu", payload)
    
    async def update_menu_item_availability(
        self, 
        provider_id: str, 
        availability_updates: list
    ) -> Dict[str, Any]:
        """Update menu item availability."""
        payload = {
            "provider_id": provider_id,
            "items": availability_updates
        }
        return await self._make_request("/genericClient/updateMenuItemAvailability", payload)
    
    async def accept_order(self, order_id: str, provider_id: str) -> Dict[str, Any]:
        """Accept an incoming order."""
        payload = {
            "order_id": order_id,
            "provider_id": provider_id
        }
        return await self._make_request("/genericClient/acceptOrder", payload)
    
    async def reject_order(
        self, 
        order_id: str, 
        provider_id: str, 
        reason: str
    ) -> Dict[str, Any]:
        """Reject an incoming order."""
        payload = {
            "order_id": order_id,
            "provider_id": provider_id,
            "reason": reason
        }
        return await self._make_request("/genericClient/rejectOrder", payload)
    
    async def mark_order_ready_for_pickup(
        self, 
        order_id: str, 
        provider_id: str
    ) -> Dict[str, Any]:
        """Mark order as ready for pickup."""
        payload = {
            "order_id": order_id,
            "provider_id": provider_id
        }
        return await self._make_request("/genericClient/markOrderAsReadyForPickup", payload)
    
    async def mark_order_picked_up(
        self, 
        order_id: str, 
        provider_id: str
    ) -> Dict[str, Any]:
        """Mark order as picked up."""
        payload = {
            "order_id": order_id,
            "provider_id": provider_id
        }
        return await self._make_request("/genericClient/markOrderAsPickedUp", payload)
    
    async def mark_order_delivered(
        self, 
        order_id: str, 
        provider_id: str
    ) -> Dict[str, Any]:
        """Mark order as delivered."""
        payload = {
            "order_id": order_id,
            "provider_id": provider_id
        }
        return await self._make_request("/genericClient/markOrderAsDelivered", payload)
    
    async def start_accepting_orders(self, provider_id: str) -> Dict[str, Any]:
        """Start accepting orders for a provider."""
        payload = {
            "provider_id": provider_id
        }
        return await self._make_request("/genericClient/startAcceptingOrders", payload)
    
    async def pause_orders(self, provider_id: str) -> Dict[str, Any]:
        """Pause orders for a provider."""
        payload = {
            "provider_id": provider_id
        }
        return await self._make_request("/genericClient/pauseOrders", payload)
    
    async def update_provider_schedule(
        self, 
        provider_id: str, 
        schedule: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Update provider schedule."""
        payload = {
            "provider_id": provider_id,
            "schedule": schedule
        }
        return await self._make_request("/genericClient/updateProviderSchedule", payload)
    
    async def create_dine_in_order(
        self, 
        provider_id: str, 
        order_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Create a dine-in order."""
        payload = {
            "provider_id": provider_id,
            **order_data
        }
        return await self._make_request("/genericClient/waiter/createOrder", payload)
    
    async def finalize_dine_in_order(
        self, 
        order_id: str, 
        provider_id: str
    ) -> Dict[str, Any]:
        """Finalize a dine-in order."""
        payload = {
            "order_id": order_id,
            "provider_id": provider_id
        }
        return await self._make_request("/genericClient/waiter/finalizeOrder", payload)


# Global service instance
bolt_food_service = BoltFoodService()
