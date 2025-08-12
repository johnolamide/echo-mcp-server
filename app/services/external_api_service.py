"""
External API service for handling service proxy calls and template processing.
"""
import asyncio
import json
import re
import time
from typing import Dict, Any, Optional, Tuple
import httpx
import logging
from cryptography.fernet import Fernet
import os

from app.core.config import settings
from app.models.service import Service

logger = logging.getLogger(__name__)


class TemplateProcessor:
    """Handles template processing for request and response transformation."""
    
    @staticmethod
    def render_template(template: Dict[str, Any], variables: Dict[str, Any]) -> Dict[str, Any]:
        """
        Render a template by replacing variables with actual values.
        
        Args:
            template: Template dictionary with {{variable}} placeholders
            variables: Dictionary of variable values
            
        Returns:
            Rendered template with variables replaced
        """
        def replace_variables(obj):
            if isinstance(obj, dict):
                return {key: replace_variables(value) for key, value in obj.items()}
            elif isinstance(obj, list):
                return [replace_variables(item) for item in obj]
            elif isinstance(obj, str):
                # Replace {{variable}} patterns
                pattern = r'\{\{([^}]+)\}\}'
                
                def replacer(match):
                    var_path = match.group(1).strip()
                    # Handle nested variables like response.data.id
                    try:
                        value = variables
                        for part in var_path.split('.'):
                            value = value[part]
                        return str(value)
                    except (KeyError, TypeError):
                        logger.warning(f"Variable '{var_path}' not found in template variables")
                        return match.group(0)  # Return original if not found
                
                return re.sub(pattern, replacer, obj)
            else:
                return obj
        
        return replace_variables(template)
    
    @staticmethod
    def extract_template_variables(template: Dict[str, Any]) -> set:
        """
        Extract all variable names from a template.
        
        Args:
            template: Template dictionary
            
        Returns:
            Set of variable names found in the template
        """
        variables = set()
        
        def extract_from_obj(obj):
            if isinstance(obj, dict):
                for value in obj.values():
                    extract_from_obj(value)
            elif isinstance(obj, list):
                for item in obj:
                    extract_from_obj(item)
            elif isinstance(obj, str):
                pattern = r'\{\{([^}]+)\}\}'
                matches = re.findall(pattern, obj)
                for match in matches:
                    var_name = match.strip().split('.')[0]  # Get root variable name
                    variables.add(var_name)
        
        extract_from_obj(template)
        return variables


class APIKeyManager:
    """Handles API key encryption and decryption."""
    
    def __init__(self):
        # In production, this should come from environment variables
        self.encryption_key = self._get_or_create_key()
        self.cipher = Fernet(self.encryption_key)
    
    def _get_or_create_key(self) -> bytes:
        """Get encryption key from environment or create a new one."""
        key_env = os.getenv('API_KEY_ENCRYPTION_KEY')
        if key_env:
            return key_env.encode()
        
        # For development, create a key (in production, this should be persistent)
        key = Fernet.generate_key()
        logger.warning("Using generated encryption key. Set API_KEY_ENCRYPTION_KEY in production.")
        return key
    
    def encrypt_api_key(self, api_key: str) -> str:
        """Encrypt an API key."""
        if not api_key:
            return ""
        return self.cipher.encrypt(api_key.encode()).decode()
    
    def decrypt_api_key(self, encrypted_key: str) -> str:
        """Decrypt an API key."""
        if not encrypted_key:
            return ""
        try:
            return self.cipher.decrypt(encrypted_key.encode()).decode()
        except Exception as e:
            logger.error(f"Failed to decrypt API key: {e}")
            return ""


class ExternalAPIService:
    """Service for making external API calls using service configurations."""
    
    def __init__(self):
        self.template_processor = TemplateProcessor()
        self.api_key_manager = APIKeyManager()
    
    async def execute_service_call(
        self, 
        service: Service, 
        user_parameters: Dict[str, Any]
    ) -> Tuple[bool, Dict[str, Any], int, int]:
        """
        Execute an external API call using service configuration.
        
        Args:
            service: Service configuration
            user_parameters: Parameters provided by the user
            
        Returns:
            Tuple of (success, response_data, status_code, execution_time_ms)
        """
        start_time = time.time()
        
        try:
            # Prepare request data
            request_data = self._prepare_request_data(service, user_parameters)
            headers = self._prepare_headers(service)
            
            # Make the external API call
            async with httpx.AsyncClient(timeout=service.timeout_seconds) as client:
                response = await self._make_api_call(
                    client, service, request_data, headers
                )
            
            # Process response
            processed_response = self._process_response(service, response)
            
            execution_time = int((time.time() - start_time) * 1000)
            
            return True, processed_response, response.status_code, execution_time
            
        except httpx.TimeoutException:
            execution_time = int((time.time() - start_time) * 1000)
            error_response = {
                "error": "Request timeout",
                "message": f"External API call timed out after {service.timeout_seconds} seconds"
            }
            return False, error_response, 408, execution_time
            
        except httpx.RequestError as e:
            execution_time = int((time.time() - start_time) * 1000)
            error_response = {
                "error": "Request failed",
                "message": str(e)
            }
            return False, error_response, 500, execution_time
            
        except Exception as e:
            execution_time = int((time.time() - start_time) * 1000)
            logger.error(f"Service call failed: {e}")
            error_response = {
                "error": "Internal error",
                "message": "Failed to process service call"
            }
            return False, error_response, 500, execution_time
    
    def _prepare_request_data(self, service: Service, user_parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Prepare request data using the service template."""
        request_template = service.request_template or {}
        return self.template_processor.render_template(request_template, user_parameters)
    
    def _prepare_headers(self, service: Service) -> Dict[str, str]:
        """Prepare headers for the API call."""
        headers = (service.headers_template or {}).copy()
        
        # Add API key if configured
        if service.encrypted_api_key and service.api_key_header:
            api_key = self.api_key_manager.decrypt_api_key(service.encrypted_api_key)
            if api_key:
                # Replace {{api_key}} in headers
                headers = self.template_processor.render_template(headers, {"api_key": api_key})
        
        return headers
    
    async def _make_api_call(
        self, 
        client: httpx.AsyncClient, 
        service: Service, 
        request_data: Dict[str, Any], 
        headers: Dict[str, str]
    ) -> httpx.Response:
        """Make the actual API call with retry logic."""
        url = service.full_api_url
        method = service.http_method.upper()
        
        for attempt in range(service.retry_attempts + 1):
            try:
                if method == 'GET':
                    response = await client.get(url, params=request_data, headers=headers)
                elif method == 'POST':
                    response = await client.post(url, json=request_data, headers=headers)
                elif method == 'PUT':
                    response = await client.put(url, json=request_data, headers=headers)
                elif method == 'PATCH':
                    response = await client.patch(url, json=request_data, headers=headers)
                elif method == 'DELETE':
                    response = await client.delete(url, headers=headers)
                else:
                    raise ValueError(f"Unsupported HTTP method: {method}")
                
                # If successful or client error (4xx), don't retry
                if response.status_code < 500:
                    return response
                
                # Server error (5xx), retry if attempts remaining
                if attempt < service.retry_attempts:
                    await asyncio.sleep(2 ** attempt)  # Exponential backoff
                    continue
                
                return response
                
            except httpx.RequestError as e:
                if attempt < service.retry_attempts:
                    await asyncio.sleep(2 ** attempt)
                    continue
                raise e
        
        return response
    
    def _process_response(self, service: Service, response: httpx.Response) -> Dict[str, Any]:
        """Process the API response using response mapping."""
        try:
            response_data = response.json()
        except json.JSONDecodeError:
            response_data = {"raw_response": response.text}
        
        # Apply response mapping if configured
        response_mapping = service.response_mapping
        if response_mapping:
            try:
                mapped_response = self.template_processor.render_template(
                    response_mapping, 
                    {"response": response_data}
                )
                return mapped_response
            except Exception as e:
                logger.warning(f"Failed to apply response mapping: {e}")
                return response_data
        
        return response_data
    
    def validate_service_parameters(self, service: Service, user_parameters: Dict[str, Any]) -> Tuple[bool, str]:
        """
        Validate that user parameters match service requirements.
        
        Args:
            service: Service configuration
            user_parameters: Parameters provided by the user
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        try:
            # Extract required variables from template
            request_template = service.request_template or {}
            required_vars = self.template_processor.extract_template_variables(request_template)
            
            # Check if all required variables are provided
            missing_vars = required_vars - set(user_parameters.keys())
            if missing_vars:
                return False, f"Missing required parameters: {', '.join(missing_vars)}"
            
            return True, ""
            
        except Exception as e:
            logger.error(f"Parameter validation failed: {e}")
            return False, "Failed to validate parameters"
    
    def get_service_schema(self, service: Service) -> Dict[str, Any]:
        """
        Get the parameter schema for a service.
        
        Args:
            service: Service configuration
            
        Returns:
            Dictionary containing parameter requirements and examples
        """
        try:
            request_template = service.request_template or {}
            required_vars = list(self.template_processor.extract_template_variables(request_template))
            
            # Generate example values based on variable names
            example_values = {}
            for var in required_vars:
                if 'lat' in var.lower():
                    example_values[var] = 40.7128
                elif 'lng' in var.lower() or 'lon' in var.lower():
                    example_values[var] = -74.0060
                elif 'id' in var.lower():
                    example_values[var] = "example_id_123"
                elif 'phone' in var.lower():
                    example_values[var] = "+1234567890"
                elif 'email' in var.lower():
                    example_values[var] = "user@example.com"
                else:
                    example_values[var] = f"example_{var}"
            
            return {
                "service_name": service.name,
                "service_type": service.type,
                "required_parameters": required_vars,
                "parameter_descriptions": {var: f"Parameter for {var}" for var in required_vars},
                "example_request": example_values
            }
            
        except Exception as e:
            logger.error(f"Failed to generate service schema: {e}")
            return {
                "service_name": service.name,
                "service_type": service.type,
                "required_parameters": [],
                "parameter_descriptions": {},
                "example_request": {}
            }


# Global service instance
external_api_service = ExternalAPIService()