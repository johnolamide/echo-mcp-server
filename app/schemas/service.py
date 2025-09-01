"""
Service schemas for API validation and external API integration.
"""
from datetime import datetime
from typing import Optional, List, Dict, Any, Union
from pydantic import BaseModel, Field, validator, HttpUrl
import json


class ServiceCreate(BaseModel):
    """Schema for creating a new service with external API configuration."""
    name: str = Field(..., min_length=1, max_length=255, description="Service name (e.g., 'Uber', 'DoorDash')")
    type: str = Field(..., min_length=1, max_length=100, description="Service type (e.g., 'ride', 'food', 'delivery')")
    description: Optional[str] = Field(None, max_length=1000, description="Service description")
    
    # External API Configuration
    api_base_url: str = Field(..., description="Base URL of the external API")
    api_endpoint: str = Field(..., description="API endpoint path")
    http_method: str = Field(default="POST", description="HTTP method for the API call")
    
    # Templates
    request_template: Dict[str, Any] = Field(..., description="Template for transforming user input to vendor API format")
    response_mapping: Optional[Dict[str, Any]] = Field(None, description="Template for transforming vendor response to user format")
    headers_template: Optional[Dict[str, str]] = Field(None, description="Headers template for API calls")
    
    # Security
    api_key: Optional[str] = Field(None, description="API key for the external service")
    api_key_header: Optional[str] = Field(None, description="Header name for the API key")
    
    # Settings
    timeout_seconds: Optional[int] = Field(30, ge=5, le=300, description="Request timeout in seconds")
    retry_attempts: Optional[int] = Field(3, ge=0, le=10, description="Number of retry attempts")
    
    @validator('name')
    def validate_name(cls, v):
        """Validate service name."""
        if not v.strip():
            raise ValueError('Service name cannot be empty or whitespace only')
        return v.strip()
    
    @validator('type')
    def validate_type(cls, v):
        """Validate service type."""
        if not v.strip():
            raise ValueError('Service type cannot be empty or whitespace only')
        return v.strip().lower()
    
    @validator('http_method')
    def validate_http_method(cls, v):
        """Validate HTTP method."""
        allowed_methods = ['GET', 'POST', 'PUT', 'PATCH', 'DELETE']
        if v.upper() not in allowed_methods:
            raise ValueError(f'HTTP method must be one of: {", ".join(allowed_methods)}')
        return v.upper()
    
    @validator('api_base_url')
    def validate_api_base_url(cls, v):
        """Validate API base URL."""
        if not v.startswith(('http://', 'https://')):
            raise ValueError('API base URL must start with http:// or https://')
        return v.rstrip('/')
    
    @validator('api_endpoint')
    def validate_api_endpoint(cls, v):
        """Validate API endpoint."""
        if not v.startswith('/'):
            v = '/' + v
        return v
    
    @validator('request_template')
    def validate_request_template(cls, v):
        """Validate request template."""
        if not isinstance(v, dict):
            raise ValueError('Request template must be a valid JSON object')
        return v
    
    class Config:
        json_schema_extra = {
            "example": {
                "name": "Uber Ride Service",
                "type": "ride",
                "description": "Complete Uber ride booking service with real-time tracking, multiple ride types, and fare estimation",
                "api_base_url": "https://api.uber.com/v1.2",
                "api_endpoint": "/requests",
                "http_method": "POST",
                "request_template": {
                    "start_latitude": "{{pickup_lat}}",
                    "start_longitude": "{{pickup_lng}}",
                    "end_latitude": "{{destination_lat}}",
                    "end_longitude": "{{destination_lng}}",
                    "product_id": "{{ride_type}}",
                    "fare_id": "{{fare_id}}",
                    "surge_confirmation_id": "{{surge_confirmation_id}}",
                    "payment_method_id": "{{payment_method_id}}",
                    "passenger_count": "{{passenger_count}}"
                },
                "response_mapping": {
                    "ride_id": "{{response.request_id}}",
                    "status": "{{response.status}}",
                    "eta": "{{response.eta}}",
                    "driver_name": "{{response.driver.name}}",
                    "driver_phone": "{{response.driver.phone_number}}",
                    "vehicle_make": "{{response.vehicle.make}}",
                    "vehicle_model": "{{response.vehicle.model}}",
                    "license_plate": "{{response.vehicle.license_plate}}"
                },
                "headers_template": {
                    "Authorization": "Bearer {{api_key}}",
                    "Content-Type": "application/json",
                    "Accept-Language": "en_US"
                },
                "api_key": "your_uber_server_token",
                "api_key_header": "Authorization",
                "timeout_seconds": 45,
                "retry_attempts": 3
            }
        }


class ServiceUpdate(BaseModel):
    """Schema for updating an existing service."""
    name: Optional[str] = Field(None, min_length=1, max_length=255, description="Service name")
    type: Optional[str] = Field(None, min_length=1, max_length=100, description="Service type")
    description: Optional[str] = Field(None, max_length=1000, description="Service description")
    
    # External API Configuration
    api_base_url: Optional[str] = Field(None, description="Base URL of the external API")
    api_endpoint: Optional[str] = Field(None, description="API endpoint path")
    http_method: Optional[str] = Field(None, description="HTTP method for the API call")
    
    # Templates
    request_template: Optional[Dict[str, Any]] = Field(None, description="Template for transforming user input")
    response_mapping: Optional[Dict[str, Any]] = Field(None, description="Template for transforming vendor response")
    headers_template: Optional[Dict[str, str]] = Field(None, description="Headers template for API calls")
    
    # Security
    api_key: Optional[str] = Field(None, description="API key for the external service")
    api_key_header: Optional[str] = Field(None, description="Header name for the API key")
    
    # Settings
    timeout_seconds: Optional[int] = Field(None, ge=5, le=300, description="Request timeout in seconds")
    retry_attempts: Optional[int] = Field(None, ge=0, le=10, description="Number of retry attempts")
    is_active: Optional[bool] = Field(None, description="Whether service is active")
    
    @validator('name')
    def validate_name(cls, v):
        """Validate service name."""
        if v is not None and not v.strip():
            raise ValueError('Service name cannot be empty or whitespace only')
        return v.strip() if v else v
    
    @validator('type')
    def validate_type(cls, v):
        """Validate service type."""
        if v is not None and not v.strip():
            raise ValueError('Service type cannot be empty or whitespace only')
        return v.strip().lower() if v else v
    
    @validator('http_method')
    def validate_http_method(cls, v):
        """Validate HTTP method."""
        if v is not None:
            allowed_methods = ['GET', 'POST', 'PUT', 'PATCH', 'DELETE']
            if v.upper() not in allowed_methods:
                raise ValueError(f'HTTP method must be one of: {", ".join(allowed_methods)}')
            return v.upper()
        return v
    
    @validator('api_base_url')
    def validate_api_base_url(cls, v):
        """Validate API base URL."""
        if v is not None:
            if not v.startswith(('http://', 'https://')):
                raise ValueError('API base URL must start with http:// or https://')
            return v.rstrip('/')
        return v
    
    @validator('api_endpoint')
    def validate_api_endpoint(cls, v):
        """Validate API endpoint."""
        if v is not None:
            if not v.startswith('/'):
                v = '/' + v
        return v
    
    class Config:
        json_schema_extra = {
            "example": {
                "name": "Updated Uber Service",
                "description": "Updated Uber ride booking service with new features",
                "is_active": True,
                "timeout_seconds": 45
            }
        }


class ServiceResponse(BaseModel):
    """Schema for service response data."""
    id: int = Field(..., description="Service ID")
    name: str = Field(..., description="Service name")
    type: str = Field(..., description="Service type")
    description: Optional[str] = Field(None, description="Service description")
    api_base_url: str = Field(..., description="Base URL of the external API")
    api_endpoint: str = Field(..., description="API endpoint path")
    http_method: str = Field(..., description="HTTP method")
    timeout_seconds: int = Field(..., description="Request timeout in seconds")
    retry_attempts: int = Field(..., description="Number of retry attempts")
    is_active: bool = Field(..., description="Whether service is active")
    created_by: int = Field(..., description="ID of the user who created the service")
    created_at: datetime = Field(..., description="Service creation timestamp")
    updated_at: datetime = Field(..., description="Last service update timestamp")
    
    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "id": 1,
                "name": "Uber",
                "type": "ride",
                "description": "Uber ride booking service",
                "api_base_url": "https://api.uber.com/v1",
                "api_endpoint": "/requests",
                "http_method": "POST",
                "timeout_seconds": 30,
                "retry_attempts": 3,
                "is_active": True,
                "created_by": 1,
                "created_at": "2023-01-01T00:00:00Z",
                "updated_at": "2023-01-01T00:00:00Z"
            }
        }


class ServiceDetailResponse(ServiceResponse):
    """Schema for detailed service response including creator information."""
    creator_username: Optional[str] = Field(None, description="Username of the service creator")
    
    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "id": 1,
                "name": "User Authentication Service",
                "description": "Provides secure user authentication and authorization functionality",
                "is_active": True,
                "created_by": 1,
                "creator_username": "admin",
                "created_at": "2023-01-01T00:00:00Z",
                "updated_at": "2023-01-01T00:00:00Z"
            }
        }


class ServiceList(BaseModel):
    """Schema for service list response."""
    services: List[ServiceResponse] = Field(..., description="List of services")
    total: int = Field(..., description="Total number of services")
    active_count: int = Field(..., description="Number of active services")
    
    class Config:
        json_schema_extra = {
            "example": {
                "services": [
                    {
                        "id": 1,
                        "name": "User Authentication Service",
                        "description": "Provides secure user authentication and authorization functionality",
                        "is_active": True,
                        "created_by": 1,
                        "created_at": "2023-01-01T00:00:00Z",
                        "updated_at": "2023-01-01T00:00:00Z"
                    }
                ],
                "total": 1,
                "active_count": 1
            }
        }


class ServiceDeleteResponse(BaseModel):
    """Schema for service deletion response."""
    message: str = Field(..., description="Deletion confirmation message")
    deleted_service_id: int = Field(..., description="ID of the deleted service")
    
    class Config:
        json_schema_extra = {
            "example": {
                "message": "Service deleted successfully",
                "deleted_service_id": 1
            }
        }


class ServiceStatusUpdate(BaseModel):
    """Schema for updating service status."""
    is_active: bool = Field(..., description="Whether service should be active")
    
    class Config:
        json_schema_extra = {
            "example": {
                "is_active": False
            }
        }


class ServiceSearchQuery(BaseModel):
    """Schema for service search query parameters."""
    query: Optional[str] = Field(None, min_length=1, max_length=100, description="Search query")
    type: Optional[str] = Field(None, description="Filter by service type")
    is_active: Optional[bool] = Field(None, description="Filter by active status")
    created_by: Optional[int] = Field(None, description="Filter by creator user ID")
    limit: Optional[int] = Field(10, ge=1, le=100, description="Maximum number of results")
    offset: Optional[int] = Field(0, ge=0, description="Number of results to skip")
    
    @validator('query')
    def validate_query(cls, v):
        """Validate search query."""
        if v is not None and not v.strip():
            raise ValueError('Search query cannot be empty or whitespace only')
        return v.strip() if v else v
    
    class Config:
        json_schema_extra = {
            "example": {
                "query": "uber",
                "type": "ride",
                "is_active": True,
                "limit": 10,
                "offset": 0
            }
        }


class ServiceExecuteRequest(BaseModel):
    """Schema for executing a service call."""
    parameters: Dict[str, Any] = Field(..., description="Parameters to pass to the service")
    
    class Config:
        json_schema_extra = {
            "example": {
                "parameters": {
                    "pickup_lat": 40.7128,
                    "pickup_lng": -74.0060,
                    "destination_lat": 40.7589,
                    "destination_lng": -73.9851,
                    "ride_type": "uberx",
                    "fare_id": "fare_12345",
                    "surge_confirmation_id": "surge_67890",
                    "payment_method_id": "payment_abc123",
                    "passenger_count": 2
                }
            }
        }


class ServiceExecuteResponse(BaseModel):
    """Schema for service execution response."""
    success: bool = Field(..., description="Whether the service call was successful")
    data: Optional[Dict[str, Any]] = Field(None, description="Response data from the service")
    error: Optional[Dict[str, Any]] = Field(None, description="Error information if the call failed")
    status_code: int = Field(..., description="HTTP status code from the external API")
    execution_time_ms: int = Field(..., description="Execution time in milliseconds")
    
    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "data": {
                    "ride_id": "request_abc123def456",
                    "status": "confirmed",
                    "eta": 5,
                    "driver_name": "John Doe",
                    "driver_phone": "+1-555-0123",
                    "vehicle_make": "Toyota",
                    "vehicle_model": "Camry",
                    "license_plate": "ABC-1234"
                },
                "error": None,
                "status_code": 200,
                "execution_time_ms": 1250
            }
        }


class ServiceTestRequest(BaseModel):
    """Schema for testing a service configuration."""
    test_parameters: Dict[str, Any] = Field(..., description="Test parameters to validate the service")
    
    class Config:
        json_schema_extra = {
            "example": {
                "test_parameters": {
                    "pickup_lat": 40.7128,
                    "pickup_lng": -74.0060,
                    "destination_lat": 40.7589,
                    "destination_lng": -73.9851
                }
            }
        }


class ServiceSchemaResponse(BaseModel):
    """Schema for service parameter requirements."""
    service_name: str = Field(..., description="Name of the service")
    service_type: str = Field(..., description="Type of the service")
    required_parameters: List[str] = Field(..., description="List of required parameter names")
    parameter_descriptions: Dict[str, str] = Field(..., description="Descriptions of each parameter")
    example_request: Dict[str, Any] = Field(..., description="Example request with sample values")
    
    class Config:
        json_schema_extra = {
            "example": {
                "service_name": "Uber Ride Service",
                "service_type": "ride",
                "required_parameters": [
                    "pickup_lat", "pickup_lng", "destination_lat", "destination_lng",
                    "ride_type", "fare_id", "surge_confirmation_id", "payment_method_id"
                ],
                "parameter_descriptions": {
                    "pickup_lat": "Pickup location latitude (decimal degrees)",
                    "pickup_lng": "Pickup location longitude (decimal degrees)",
                    "destination_lat": "Destination latitude (decimal degrees)",
                    "destination_lng": "Destination longitude (decimal degrees)",
                    "ride_type": "Type of ride (uberx, uberxl, uberblack, etc.)",
                    "fare_id": "Fare estimate ID from previous fare request",
                    "surge_confirmation_id": "Surge pricing confirmation ID",
                    "payment_method_id": "Payment method identifier"
                },
                "example_request": {
                    "pickup_lat": 40.7128,
                    "pickup_lng": -74.0060,
                    "destination_lat": 40.7589,
                    "destination_lng": -73.9851,
                    "ride_type": "uberx",
                    "fare_id": "fare_12345",
                    "surge_confirmation_id": "surge_67890",
                    "payment_method_id": "payment_abc123"
                }
            }
        }