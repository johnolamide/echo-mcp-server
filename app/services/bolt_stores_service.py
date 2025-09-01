"""
Bolt Stores API service implementation.
"""
import json
import hmac
import hashlib
import base64
import logging
from typing import Dict, Any, Optional, List
import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)


class BoltStoresService:
    """Service class for interacting with Bolt Stores API."""
    
    def __init__(self):
        self.api_url = settings.bolt_stores_api_url
        self.integrator_id = settings.bolt_stores_integrator_id
        self.secret_key = settings.bolt_stores_secret_key
        self.region_id = settings.bolt_region_id
        self.timeout = 60
        
    def _generate_hmac_signature(self, payload: str) -> str:
        """Generate HMAC-SHA256 signature for request authentication."""
        if not self.secret_key:
            raise ValueError("Bolt Stores secret key not configured")
            
        key = self.secret_key.encode('utf-8')
        message = payload.encode('utf-8')
        signature = hmac.new(key, message, hashlib.sha256).digest()
        return base64.b64encode(signature).decode('utf-8')
    
    def _get_headers(self, payload: str) -> Dict[str, str]:
        """Get headers with authentication for Bolt Stores API requests."""
        if not self.integrator_id:
            raise ValueError("Bolt Stores integrator ID not configured")
            
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
        """Make authenticated request to Bolt Stores API."""
        url = f"{self.api_url}{endpoint}"
        payload_str = json.dumps(payload)
        headers = self._get_headers(payload_str)
        
        logger.info(f"Making request to Bolt Stores API: {endpoint}")
        
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(url, content=payload_str, headers=headers)
                response.raise_for_status()
                return response.json()
        except httpx.HTTPStatusError as e:
            logger.error(f"Bolt Stores API error: {e.response.status_code} - {e.response.text}")
            raise
        except Exception as e:
            logger.error(f"Request to Bolt Stores API failed: {e}")
            raise
    
    # Menu Integration
    async def get_menu(self, provider_id: str) -> Dict[str, Any]:
        """Get menu from Bolt Stores."""
        payload = {
            "provider_id": provider_id,
            "region_id": self.region_id
        }
        return await self._make_request("/genericClient/getMenu", payload)
    
    # Order Management
    async def accept_order(self, order_id: str, provider_id: str) -> Dict[str, Any]:
        """Accept an incoming order."""
        payload = {
            "order_id": order_id,
            "provider_id": provider_id,
            "region_id": self.region_id
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
            "region_id": self.region_id,
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
            "provider_id": provider_id,
            "region_id": self.region_id
        }
        return await self._make_request("/genericClient/markOrderAsReadyForPickup", payload)
    
    async def mark_order_with_items_ready_for_pickup(
        self,
        order_id: str,
        provider_id: str,
        items: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Mark order with specific items as ready for pickup."""
        payload = {
            "order_id": order_id,
            "provider_id": provider_id,
            "region_id": self.region_id,
            "items": items
        }
        return await self._make_request("/genericClient/markOrderWithItemsAsReadyForPickUp", payload)
    
    async def mark_order_picked_up(
        self, 
        order_id: str, 
        provider_id: str
    ) -> Dict[str, Any]:
        """Mark order as picked up."""
        payload = {
            "order_id": order_id,
            "provider_id": provider_id,
            "region_id": self.region_id
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
            "provider_id": provider_id,
            "region_id": self.region_id
        }
        return await self._make_request("/genericClient/markOrderAsDelivered", payload)
    
    # Provider Management
    async def start_accepting_orders(self, provider_id: str) -> Dict[str, Any]:
        """Start accepting orders for a provider."""
        payload = {
            "provider_id": provider_id,
            "region_id": self.region_id
        }
        return await self._make_request("/genericClient/startAcceptingOrders", payload)
    
    async def pause_orders(self, provider_id: str) -> Dict[str, Any]:
        """Pause orders for a provider."""
        payload = {
            "provider_id": provider_id,
            "region_id": self.region_id
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
            "region_id": self.region_id,
            "schedule": schedule
        }
        return await self._make_request("/genericClient/updateProviderSchedule", payload)
    
    # Warehouse Management
    async def update_menu_quantity(
        self,
        provider_id: str,
        sku_quantities: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Update SKU quantities."""
        payload = {
            "provider_id": provider_id,
            "region_id": self.region_id,
            "sku_quantities": sku_quantities
        }
        return await self._make_request("/genericClient/updateMenuQuantity", payload)
    
    # PIM Integration - Products
    async def create_products(
        self,
        provider_id: str,
        products: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Create or fully overwrite products."""
        payload = {
            "provider_id": provider_id,
            "region_id": self.region_id,
            "products": products
        }
        return await self._make_request("/pim/v1/products/import/create", payload)
    
    async def edit_products(
        self,
        provider_id: str,
        products: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Partially update products."""
        payload = {
            "provider_id": provider_id,
            "region_id": self.region_id,
            "products": products
        }
        return await self._make_request("/pim/v1/products/import/edit", payload)
    
    async def get_product_import_status(
        self,
        provider_id: str,
        task_id: str
    ) -> Dict[str, Any]:
        """Retrieve product import status."""
        payload = {
            "provider_id": provider_id,
            "region_id": self.region_id,
            "task_id": task_id
        }
        return await self._make_request("/pim/v1/products/import/status/retrieve", payload)
    
    async def apply_product_import(
        self,
        provider_id: str,
        task_id: str
    ) -> Dict[str, Any]:
        """Apply pending product import."""
        payload = {
            "provider_id": provider_id,
            "region_id": self.region_id,
            "task_id": task_id
        }
        return await self._make_request("/pim/v1/products/import/apply", payload)
    
    async def cancel_product_import(
        self,
        provider_id: str,
        task_id: str
    ) -> Dict[str, Any]:
        """Cancel pending product import."""
        payload = {
            "provider_id": provider_id,
            "region_id": self.region_id,
            "task_id": task_id
        }
        return await self._make_request("/pim/v1/products/import/cancel", payload)
    
    async def delist_products(
        self,
        provider_id: str,
        product_ids: List[str]
    ) -> Dict[str, Any]:
        """Delist products."""
        payload = {
            "provider_id": provider_id,
            "region_id": self.region_id,
            "product_ids": product_ids
        }
        return await self._make_request("/pim/v1/products/delist", payload)
    
    # PIM Integration - Pricing
    async def import_prices(
        self,
        provider_id: str,
        prices: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Import selling prices."""
        payload = {
            "provider_id": provider_id,
            "region_id": self.region_id,
            "prices": prices
        }
        return await self._make_request("/pim/v1/products/prices/import", payload)
    
    async def import_discount_prices(
        self,
        provider_id: str,
        discount_prices: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Import discount selling price list."""
        payload = {
            "provider_id": provider_id,
            "region_id": self.region_id,
            "discount_prices": discount_prices
        }
        return await self._make_request("/pim/v1/products/discount/prices/import", payload)
    
    # PIM Integration - Fees
    async def list_fees(self, provider_id: str) -> Dict[str, Any]:
        """List fees."""
        payload = {
            "provider_id": provider_id,
            "region_id": self.region_id
        }
        return await self._make_request("/pim/v1/fee/list", payload)
    
    async def update_fee(
        self,
        provider_id: str,
        fee_id: int,
        fee_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Update fee."""
        payload = {
            "provider_id": provider_id,
            "region_id": self.region_id,
            "fee_id": fee_id,
            **fee_data
        }
        return await self._make_request("/pim/v1/fee/update", payload)


# Global service instance
bolt_stores_service = BoltStoresService()
