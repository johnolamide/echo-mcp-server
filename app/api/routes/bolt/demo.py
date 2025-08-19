"""
Demo and testing endpoints for Bolt Food and Stores APIs.
Provides sample requests and responses for testing the integration.
"""
from fastapi import APIRouter, HTTPException
from typing import Dict, Any, List
import json

router = APIRouter(prefix="/bolt-demo")


@router.get("/samples/bolt-food/menu", operation_id="get_bolt_food_menu_sample")
async def get_bolt_food_menu_sample() -> Dict[str, Any]:
    """Get sample Bolt Food menu structure."""
    return {
        "description": "Sample Bolt Food menu push request",
        "endpoint": "POST /api/bolt-food/menu/push",
        "sample_request": {
            "provider_id": "restaurant_123",
            "menu_data": {
                "categories": [
                    {
                        "id": "cat_1",
                        "name": "Appetizers",
                        "description": "Start your meal right",
                        "children_ids": ["dish_1", "dish_2"]
                    },
                    {
                        "id": "cat_2", 
                        "name": "Main Courses",
                        "description": "Our signature dishes",
                        "children_ids": ["dish_3", "dish_4"]
                    }
                ],
                "dishes": [
                    {
                        "id": "dish_1",
                        "name": "Caesar Salad",
                        "description": "Fresh romaine lettuce with parmesan",
                        "price": 850,  # Price in cents
                        "currency": "EUR",
                        "image_url": "https://example.com/caesar.jpg",
                        "is_available": True,
                        "tags": ["vegetarian"],
                        "children_ids": ["option_group_1"]
                    },
                    {
                        "id": "dish_2",
                        "name": "Chicken Wings",
                        "description": "Spicy buffalo wings",
                        "price": 1200,
                        "currency": "EUR",
                        "is_available": True,
                        "tags": ["spicy"]
                    },
                    {
                        "id": "dish_3",
                        "name": "Margherita Pizza",
                        "description": "Classic tomato and mozzarella",
                        "price": 1450,
                        "currency": "EUR",
                        "is_available": True,
                        "children_ids": ["option_group_2"]
                    }
                ],
                "option_groups": [
                    {
                        "id": "option_group_1",
                        "name": "Dressing Choice",
                        "type": "option_select_group",
                        "min_selection": 1,
                        "max_selection": 1,
                        "children_ids": ["option_1", "option_2"]
                    },
                    {
                        "id": "option_group_2",
                        "name": "Extra Toppings",
                        "type": "option_multi_select_group",
                        "min_selection": 0,
                        "max_selection": 5,
                        "children_ids": ["option_3", "option_4", "option_5"]
                    }
                ],
                "options": [
                    {
                        "id": "option_1",
                        "name": "Caesar Dressing",
                        "price": 0,
                        "currency": "EUR"
                    },
                    {
                        "id": "option_2", 
                        "name": "Ranch Dressing",
                        "price": 50,
                        "currency": "EUR"
                    },
                    {
                        "id": "option_3",
                        "name": "Extra Cheese",
                        "price": 200,
                        "currency": "EUR"
                    },
                    {
                        "id": "option_4",
                        "name": "Pepperoni",
                        "price": 300,
                        "currency": "EUR"
                    },
                    {
                        "id": "option_5",
                        "name": "Mushrooms",
                        "price": 150,
                        "currency": "EUR"
                    }
                ]
            }
        },
        "sample_response": {
            "status": "success",
            "message": "Menu updated successfully",
            "menu_id": "menu_456"
        }
    }


@router.get("/samples/bolt-food/order-management", operation_id="get_bolt_food_order_management_samples")
async def get_bolt_food_order_samples() -> Dict[str, Any]:
    """Get sample Bolt Food order management requests."""
    return {
        "description": "Sample Bolt Food order management operations",
        "operations": {
            "accept_order": {
                "endpoint": "POST /api/bolt-food/orders/{order_id}/accept",
                "sample_request": {
                    "order_id": "order_789",
                    "provider_id": "restaurant_123"
                },
                "sample_response": {
                    "status": "accepted",
                    "message": "Order accepted successfully",
                    "estimated_preparation_time": 25
                }
            },
            "reject_order": {
                "endpoint": "POST /api/bolt-food/orders/{order_id}/reject", 
                "sample_request": {
                    "order_id": "order_789",
                    "provider_id": "restaurant_123",
                    "reason": "Item out of stock"
                },
                "sample_response": {
                    "status": "rejected",
                    "message": "Order rejected successfully"
                }
            },
            "mark_ready": {
                "endpoint": "POST /api/bolt-food/orders/{order_id}/ready",
                "sample_request": {
                    "order_id": "order_789",
                    "provider_id": "restaurant_123"
                },
                "sample_response": {
                    "status": "ready_for_pickup",
                    "message": "Order marked as ready for pickup"
                }
            }
        }
    }


@router.get("/samples/bolt-food/webhooks", operation_id="get_bolt_food_webhook_samples")
async def get_bolt_food_webhook_samples() -> Dict[str, Any]:
    """Get sample Bolt Food webhook payloads."""
    return {
        "description": "Sample webhook payloads from Bolt Food",
        "webhooks": {
            "new_order": {
                "endpoint": "POST /api/bolt-webhooks/food/new-order",
                "sample_payload": {
                    "order_id": "order_789",
                    "provider_id": "restaurant_123",
                    "customer": {
                        "name": "John Doe",
                        "phone": "+1234567890"
                    },
                    "items": [
                        {
                            "id": "dish_1",
                            "name": "Caesar Salad",
                            "quantity": 1,
                            "price": 850,
                            "options": [
                                {
                                    "id": "option_1",
                                    "name": "Caesar Dressing",
                                    "price": 0
                                }
                            ]
                        }
                    ],
                    "total_price": 850,
                    "currency": "EUR",
                    "delivery_address": {
                        "street": "123 Main St",
                        "city": "Berlin",
                        "postal_code": "10115"
                    },
                    "estimated_delivery_time": "2025-08-19T19:30:00Z"
                }
            },
            "cancel_order": {
                "endpoint": "POST /api/bolt-webhooks/food/cancel-order",
                "sample_payload": {
                    "order_id": "order_789",
                    "provider_id": "restaurant_123",
                    "reason": "Customer cancelled",
                    "cancelled_at": "2025-08-19T18:45:00Z"
                }
            },
            "courier_details": {
                "endpoint": "POST /api/bolt-webhooks/food/courier-details",
                "sample_payload": {
                    "order_id": "order_789",
                    "courier": {
                        "name": "Jane Smith",
                        "phone": "+1234567891",
                        "vehicle_type": "bike"
                    },
                    "estimated_pickup_time": "2025-08-19T19:15:00Z"
                }
            }
        }
    }


@router.get("/samples/bolt-stores/products", operation_id="get_bolt_stores_product_samples")
async def get_bolt_stores_product_samples() -> Dict[str, Any]:
    """Get sample Bolt Stores product management requests."""
    return {
        "description": "Sample Bolt Stores product management operations",
        "operations": {
            "create_products": {
                "endpoint": "POST /api/bolt-stores/pim/products/create",
                "sample_request": {
                    "provider_id": "store_456",
                    "products": [
                        {
                            "external_id": "prod_001",
                            "name": {
                                "en": "Organic Apples",
                                "de": "Bio Äpfel"
                            },
                            "description": {
                                "en": "Fresh organic apples from local farms",
                                "de": "Frische Bio-Äpfel vom Bauernhof"
                            },
                            "price": 299,  # Price in cents per kg
                            "currency": "EUR",
                            "categories": ["fruits", "organic"],
                            "barcode": "1234567890123",
                            "weight_net": 1000,  # grams
                            "is_measured": True,
                            "measure_unit": "kg",
                            "tags": ["organic", "local"],
                            "image_url": "https://example.com/apples.jpg"
                        },
                        {
                            "external_id": "prod_002",
                            "name": {
                                "en": "Whole Milk",
                                "de": "Vollmilch"
                            },
                            "description": {
                                "en": "Fresh whole milk 3.5% fat",
                                "de": "Frische Vollmilch 3,5% Fett"
                            },
                            "price": 149,
                            "currency": "EUR",
                            "categories": ["dairy"],
                            "barcode": "9876543210987",
                            "volume": 1000,  # ml
                            "fees": [
                                {
                                    "type": "deposit",
                                    "amount": 25  # 25 cents deposit
                                }
                            ]
                        }
                    ]
                },
                "sample_response": {
                    "status": "success",
                    "task_id": "task_123",
                    "message": "Product import task created"
                }
            },
            "update_quantities": {
                "endpoint": "POST /api/bolt-stores/warehouse/quantities",
                "sample_request": {
                    "provider_id": "store_456",
                    "sku_quantities": [
                        {
                            "sku": "prod_001",
                            "quantity": 50,
                            "measure_unit": "kg"
                        },
                        {
                            "sku": "prod_002", 
                            "quantity": 24,
                            "measure_unit": "pieces"
                        }
                    ]
                },
                "sample_response": {
                    "status": "success",
                    "message": "Quantities updated successfully"
                }
            }
        }
    }


@router.get("/samples/bolt-stores/pricing", operation_id="get_bolt_stores_pricing_samples")
async def get_bolt_stores_pricing_samples() -> Dict[str, Any]:
    """Get sample Bolt Stores pricing operations."""
    return {
        "description": "Sample Bolt Stores pricing operations",
        "operations": {
            "import_prices": {
                "endpoint": "POST /api/bolt-stores/pim/prices/import",
                "sample_request": {
                    "provider_id": "store_456",
                    "prices": [
                        {
                            "sku": "prod_001",
                            "price": 329,  # New price in cents
                            "currency": "EUR",
                            "effective_from": "2025-08-20T00:00:00Z"
                        },
                        {
                            "sku": "prod_002",
                            "price": 159,
                            "currency": "EUR",
                            "effective_from": "2025-08-20T00:00:00Z"
                        }
                    ]
                }
            },
            "import_discount_prices": {
                "endpoint": "POST /api/bolt-stores/pim/discount-prices/import",
                "sample_request": {
                    "provider_id": "store_456",
                    "discount_prices": [
                        {
                            "sku": "prod_001",
                            "original_price": 329,
                            "discount_price": 249,
                            "discount_percentage": 24.3,
                            "valid_from": "2025-08-20T00:00:00Z",
                            "valid_until": "2025-08-27T23:59:59Z",
                            "reason": "Weekly special"
                        }
                    ]
                }
            }
        }
    }


@router.get("/samples/bolt-stores/webhooks", operation_id="get_bolt_stores_webhook_samples")
async def get_bolt_stores_webhook_samples() -> Dict[str, Any]:
    """Get sample Bolt Stores webhook payloads."""
    return {
        "description": "Sample webhook payloads from Bolt Stores",
        "webhooks": {
            "new_order": {
                "endpoint": "POST /api/bolt-webhooks/stores/new-order",
                "sample_payload": {
                    "order_id": "store_order_456",
                    "provider_id": "store_456",
                    "customer": {
                        "name": "Alice Johnson",
                        "phone": "+1234567892"
                    },
                    "items": [
                        {
                            "sku": "prod_001",
                            "name": "Organic Apples",
                            "quantity": 2.5,
                            "measure_unit": "kg",
                            "unit_price": 299,
                            "total_price": 747,
                            "picked_quantity": None,
                            "replacement_info": None
                        },
                        {
                            "sku": "prod_002",
                            "name": "Whole Milk",
                            "quantity": 2,
                            "measure_unit": "pieces",
                            "unit_price": 149,
                            "total_price": 298,
                            "fees": [
                                {
                                    "type": "deposit",
                                    "amount": 50  # 2 x 25 cents
                                }
                            ]
                        }
                    ],
                    "total_price": 1095,  # Including fees
                    "currency": "EUR",
                    "delivery_address": {
                        "street": "456 Oak Avenue",
                        "city": "Munich",
                        "postal_code": "80331"
                    },
                    "delivery_window": {
                        "start": "2025-08-19T14:00:00Z",
                        "end": "2025-08-19T16:00:00Z"
                    }
                }
            }
        }
    }


@router.get("/test-endpoints", operation_id="get_test_endpoints")
async def get_test_endpoints() -> Dict[str, Any]:
    """Get a summary of all available test endpoints."""
    return {
        "description": "Available demo and test endpoints for Bolt integration",
        "endpoints": {
            "bolt_food_samples": {
                "menu": "/api/bolt-demo/samples/bolt-food/menu",
                "orders": "/api/bolt-demo/samples/bolt-food/order-management", 
                "webhooks": "/api/bolt-demo/samples/bolt-food/webhooks"
            },
            "bolt_stores_samples": {
                "products": "/api/bolt-demo/samples/bolt-stores/products",
                "pricing": "/api/bolt-demo/samples/bolt-stores/pricing",
                "webhooks": "/api/bolt-demo/samples/bolt-stores/webhooks"
            },
            "actual_api_endpoints": {
                "bolt_food": "/api/bolt-food/*",
                "bolt_stores": "/api/bolt-stores/*", 
                "webhooks": "/api/bolt-webhooks/*"
            }
        },
        "note": "To test the actual APIs, you need to configure Bolt credentials in your .env file"
    }
