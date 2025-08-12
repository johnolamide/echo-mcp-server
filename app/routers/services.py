"""
Services management router with CRUD operations and external API proxy functionality.
Provides admin-only create, update, and delete endpoints with role validation,
public service listing and detail endpoints, and service execution capabilities.
"""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query, Path
from sqlmodel import Session, select, and_, or_, func

from app.db.database import get_db
from app.models.service import Service
from app.models.user import User
from app.schemas.service import (
    ServiceCreate,
    ServiceUpdate,
    ServiceResponse,
    ServiceDetailResponse,
    ServiceList,
    ServiceDeleteResponse,
    ServiceStatusUpdate,
    ServiceSearchQuery,
    ServiceExecuteRequest,
    ServiceExecuteResponse,
    ServiceTestRequest,
    ServiceSchemaResponse
)
from app.core.security import get_current_user_token, require_admin
from app.services.external_api_service import external_api_service

router = APIRouter(prefix="/services", tags=["services"])


def get_current_user(
    db: Session = Depends(get_db),
    current_user_token: dict = Depends(get_current_user_token)
) -> User:
    """Get current user from database."""
    user = db.exec(select(User).where(User.id == int(current_user_token["sub"]))).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    return user


@router.post("/create", response_model=ServiceResponse, status_code=status.HTTP_201_CREATED)
async def create_service(
    service_data: ServiceCreate,
    db: Session = Depends(get_db),
    current_user_token: dict = Depends(require_admin)
):
    """
    Create a new service with external API configuration (Admin only).
    
    Requirements: 4.1 - Admin can create services
    """
    # Get current user
    current_user = db.exec(select(User).where(User.id == int(current_user_token["sub"]))).first()
    if not current_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Verify user can manage services
    if not current_user.is_admin: # Simplified check
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions to create services"
        )
    
    # Check if service with same name and type already exists
    existing_service = db.exec(select(Service).where(
        and_(Service.name == service_data.name, Service.type == service_data.type)
    )).first()
    if existing_service:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Service '{service_data.name}' of type '{service_data.type}' already exists"
        )
    
    # Encrypt API key if provided
    encrypted_api_key = None
    if service_data.api_key:
        encrypted_api_key = external_api_service.api_key_manager.encrypt_api_key(service_data.api_key)
    
    # Create new service
    new_service = Service(
        name=service_data.name,
        type=service_data.type,
        description=service_data.description,
        api_base_url=str(service_data.api_base_url),
        api_endpoint=service_data.api_endpoint,
        http_method=service_data.http_method,
        request_template=service_data.request_template,
        response_mapping=service_data.response_mapping,
        headers_template=service_data.headers_template,
        encrypted_api_key=encrypted_api_key,
        creator_id=current_user.id
    )
    
    db.add(new_service)
    db.commit()
    db.refresh(new_service)
    
    return ServiceResponse.from_orm(new_service)


@router.put("/{service_id}", response_model=ServiceResponse)
async def update_service(
    service_id: int,
    service_data: ServiceUpdate,
    db: Session = Depends(get_db),
    current_user_token: dict = Depends(require_admin)
):
    """
    Update an existing service (Admin only).
    
    Requirements: 4.2 - Admin can update services
    """
    service = db.get(Service, service_id)
    if not service:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Service not found"
        )
        
    update_data = service_data.dict(exclude_unset=True)
    
    # Encrypt API key if it's being updated
    if 'api_key' in update_data and update_data['api_key']:
        update_data['encrypted_api_key'] = external_api_service.api_key_manager.encrypt_api_key(update_data['api_key'])
        del update_data['api_key']
    
    for key, value in update_data.items():
        setattr(service, key, value)
        
    db.add(service)
    db.commit()
    db.refresh(service)
    
    return ServiceResponse.from_orm(service)


@router.delete("/{service_id}", response_model=ServiceDeleteResponse)
async def delete_service(
    service_id: int,
    db: Session = Depends(get_db),
    current_user_token: dict = Depends(require_admin)
):
    """
    Delete a service (Admin only).
    
    Requirements: 4.3 - Admin can delete services
    """
    service = db.get(Service, service_id)
    if not service:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Service not found"
        )
        
    db.delete(service)
    db.commit()
    
    return ServiceDeleteResponse(message=f"Service '{service.name}' deleted successfully")


@router.get("/", response_model=ServiceList)
async def list_services(
    type: Optional[str] = Query(None, description="Filter by service type"),
    is_active: bool = Query(True, description="Filter by active status"),
    search: Optional[str] = Query(None, description="Search by name or description"),
    limit: int = Query(50, ge=1, le=100, description="Limit number of results"),
    offset: int = Query(0, ge=0, description="Offset for pagination"),
    db: Session = Depends(get_db)
):
    """
    List all available services with filtering and pagination.
    
    Requirements: 4.4 - User can list all services
    """
    query = select(Service).where(Service.is_active == is_active)
    
    if type:
        query = query.where(Service.type == type)
        
    if search:
        search_term = f"%{search}%"
        query = query.where(
            or_(
                Service.name.ilike(search_term),
                Service.description.ilike(search_term)
            )
        )
        
    total_count = db.exec(select(func.count()).select_from(query.alias("subquery"))).one()
    
    services = db.exec(query.order_by(Service.name).offset(offset).limit(limit)).all()
    
    return ServiceList(
        services=[ServiceResponse.from_orm(s) for s in services],
        total=total_count,
        limit=limit,
        offset=offset
    )


@router.get("/{service_id}", response_model=ServiceDetailResponse)
async def get_service_details(
    service_id: int,
    db: Session = Depends(get_db)
):
    """
    Get detailed information about a specific service.
    
    Requirements: 4.5 - User can get service details
    """
    service = db.get(Service, service_id)
    if not service or not service.is_active:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Service not found or is inactive"
        )
        
    return ServiceDetailResponse.from_orm(service)


@router.post("/{service_id}/execute", response_model=ServiceExecuteResponse)
async def execute_service(
    service_id: int,
    request_data: ServiceExecuteRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Execute a service by its ID, proxying the request to the external API.
    
    Requirements: 4.6 - User can execute a service
    """
    service = db.get(Service, service_id)
    if not service or not service.is_active:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Service not found or is inactive"
        )
        
    try:
        result = await external_api_service.execute_service(
            service=service,
            user_input=request_data.user_input,
            user=current_user
        )
        return ServiceExecuteResponse(
            status="success",
            data=result
        )
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to execute service: {e}"
        )


@router.put("/{service_id}/status", response_model=ServiceResponse)
async def update_service_status(
    service_id: int,
    status_update: ServiceStatusUpdate,
    db: Session = Depends(get_db),
    current_user_token: dict = Depends(require_admin)
):
    """
    Activate or deactivate a service (Admin only).
    """
    service = db.get(Service, service_id)
    if not service:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Service not found"
        )
        
    service.is_active = status_update.is_active
    db.add(service)
    db.commit()
    db.refresh(service)
    
    return ServiceResponse.from_orm(service)


@router.post("/search", response_model=ServiceList)
async def search_services(
    search_query: ServiceSearchQuery,
    db: Session = Depends(get_db)
):
    """
    Advanced search for services with multiple criteria.
    """
    query = select(Service)
    
    if search_query.name:
        query = query.where(Service.name.ilike(f"%{search_query.name}%"))
    if search_query.type:
        query = query.where(Service.type == search_query.type)
    if search_query.description:
        query = query.where(Service.description.ilike(f"%{search_query.description}%"))
    if search_query.is_active is not None:
        query = query.where(Service.is_active == search_query.is_active)
        
    total_count = db.exec(select(func.count()).select_from(query.alias("subquery"))).one()
    
    services = db.exec(
        query.order_by(Service.name)
        .offset(search_query.offset)
        .limit(search_query.limit)
    ).all()
    
    return ServiceList(
        services=[ServiceResponse.from_orm(s) for s in services],
        total=total_count,
        limit=search_query.limit,
        offset=search_query.offset
    )


@router.post("/test-service", response_model=ServiceExecuteResponse)
async def test_service_execution(
    test_request: ServiceTestRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Test a service configuration without saving it to the database.
    """
    # Create a temporary service object for testing
    temp_service = Service(
        name="Test Service",
        type=test_request.type,
        description="A temporary service for testing.",
        api_base_url=str(test_request.api_base_url),
        api_endpoint=test_request.api_endpoint,
        http_method=test_request.http_method,
        request_template=test_request.request_template,
        response_mapping=test_request.response_mapping,
        headers_template=test_request.headers_template,
        is_active=True
    )
    
    # Encrypt API key for the test if provided
    if test_request.api_key:
        temp_service.encrypted_api_key = external_api_service.api_key_manager.encrypt_api_key(test_request.api_key)
        
    try:
        result = await external_api_service.execute_service(
            service=temp_service,
            user_input=test_request.user_input,
            user=current_user
        )
        return ServiceExecuteResponse(
            status="success",
            data=result
        )
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Service test failed: {e}"
        )


@router.get("/{service_id}/schema", response_model=ServiceSchemaResponse)
async def get_service_schema(
    service_id: int,
    db: Session = Depends(get_db)
):
    """
    Get the request and response JSON schema for a service.
    """
    service = db.get(Service, service_id)
    if not service or not service.is_active:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Service not found or is inactive"
        )
        
    try:
        request_schema = external_api_service.get_request_schema(service)
        response_schema = external_api_service.get_response_schema(service)
        
        return ServiceSchemaResponse(
            request_schema=request_schema,
            response_schema=response_schema
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Could not generate schema: {e}"
        )

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query, Path
from sqlmodel import Session, select
from sqlalchemy import and_, or_, func

from app.db.database import get_db
from app.models.service import Service
from app.models.user import User
from app.schemas.service import (
    ServiceCreate,
    ServiceUpdate,
    ServiceResponse,
    ServiceDetailResponse,
    ServiceList,
    ServiceDeleteResponse,
    ServiceStatusUpdate,
    ServiceSearchQuery,
    ServiceExecuteRequest,
    ServiceExecuteResponse,
    ServiceTestRequest,
    ServiceSchemaResponse
)
from app.core.security import get_current_user_token, require_admin
from app.services.external_api_service import external_api_service

router = APIRouter(prefix="/services", tags=["services"])


def get_current_user(
    db: Session = Depends(get_db),
    current_user_token: dict = Depends(get_current_user_token)
) -> User:
    """Get current user from database."""
    user = db.query(User).filter(User.id == int(current_user_token["sub"])).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    return user


@router.post("/create", response_model=ServiceResponse, status_code=status.HTTP_201_CREATED)
async def create_service(
    service_data: ServiceCreate,
    db: Session = Depends(get_db),
    current_user_token: dict = Depends(require_admin)
):
    """
    Create a new service with external API configuration (Admin only).
    
    Requirements: 4.1 - Admin can create services
    """
    # Get current user
    current_user = db.query(User).filter(User.id == int(current_user_token["sub"])).first()
    if not current_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Verify user can manage services
    if not current_user.can_manage_services():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions to create services"
        )
    
    # Check if service with same name and type already exists
    existing_service = db.query(Service).filter(
        and_(Service.name == service_data.name, Service.type == service_data.type)
    ).first()
    if existing_service:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Service '{service_data.name}' of type '{service_data.type}' already exists"
        )
    
    # Encrypt API key if provided
    encrypted_api_key = None
    if service_data.api_key:
        encrypted_api_key = external_api_service.api_key_manager.encrypt_api_key(service_data.api_key)
    
    # Create new service
    new_service = Service(
        name=service_data.name,
        type=service_data.type,
        description=service_data.description,
        api_base_url=service_data.api_base_url,
        api_endpoint=service_data.api_endpoint,
        http_method=service_data.http_method,
        request_template=service_data.request_template,
        response_mapping=service_data.response_mapping,
        headers_template=service_data.headers_template,
        encrypted_api_key=encrypted_api_key,
        api_key_header=service_data.api_key_header,
        timeout_seconds=service_data.timeout_seconds or 30,
        retry_attempts=service_data.retry_attempts or 3,
        created_by=current_user.id,
        is_active=True
    )
    
    db.add(new_service)
    db.commit()
    db.refresh(new_service)
    
    return new_service


@router.put("/update/{service_id}", response_model=ServiceResponse)
async def update_service(
    service_id: int,
    service_data: ServiceUpdate,
    db: Session = Depends(get_db),
    current_user_token: dict = Depends(require_admin)
):
    """
    Update an existing service (Admin only).
    
    Requirements: 4.2 - Admin can update services
    """
    # Get current user
    current_user = db.query(User).filter(User.id == int(current_user_token["sub"])).first()
    if not current_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Get service
    service = db.query(Service).filter(Service.id == service_id).first()
    if not service:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Service not found"
        )
    
    # Verify user can modify this service
    if not service.can_be_modified_by(current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions to update this service"
        )
    
    # Check if new name/type combination conflicts with existing service
    if (service_data.name and service_data.name != service.name) or (service_data.type and service_data.type != service.type):
        check_name = service_data.name or service.name
        check_type = service_data.type or service.type
        existing_service = db.query(Service).filter(
            and_(
                Service.name == check_name, 
                Service.type == check_type,
                Service.id != service_id
            )
        ).first()
        if existing_service:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Service '{check_name}' of type '{check_type}' already exists"
            )
    
    # Update service fields
    if service_data.name is not None:
        service.name = service_data.name
    if service_data.type is not None:
        service.type = service_data.type
    if service_data.description is not None:
        service.description = service_data.description
    if service_data.api_base_url is not None:
        service.api_base_url = service_data.api_base_url
    if service_data.api_endpoint is not None:
        service.api_endpoint = service_data.api_endpoint
    if service_data.http_method is not None:
        service.http_method = service_data.http_method
    if service_data.request_template is not None:
        service.request_template = service_data.request_template
    if service_data.response_mapping is not None:
        service.response_mapping = service_data.response_mapping
    if service_data.headers_template is not None:
        service.headers_template = service_data.headers_template
    if service_data.api_key is not None:
        service.encrypted_api_key = external_api_service.api_key_manager.encrypt_api_key(service_data.api_key)
    if service_data.api_key_header is not None:
        service.api_key_header = service_data.api_key_header
    if service_data.timeout_seconds is not None:
        service.timeout_seconds = service_data.timeout_seconds
    if service_data.retry_attempts is not None:
        service.retry_attempts = service_data.retry_attempts
    if service_data.is_active is not None:
        service.is_active = service_data.is_active
    
    db.commit()
    db.refresh(service)
    
    return service


@router.delete("/delete/{service_id}", response_model=ServiceDeleteResponse)
async def delete_service(
    service_id: int,
    db: Session = Depends(get_db),
    current_user_token: dict = Depends(require_admin)
):
    """
    Delete a service (Admin only).
    
    Requirements: 4.3 - Admin can delete services
    """
    # Get current user
    current_user = db.query(User).filter(User.id == int(current_user_token["sub"])).first()
    if not current_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Get service
    service = db.query(Service).filter(Service.id == service_id).first()
    if not service:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Service not found"
        )
    
    # Verify user can delete this service
    if not service.can_be_deleted_by(current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions to delete this service"
        )
    
    # Soft delete by deactivating instead of hard delete
    service.deactivate()
    db.commit()
    
    return ServiceDeleteResponse(
        message="Service deleted successfully",
        deleted_service_id=service_id
    )


@router.patch("/status/{service_id}", response_model=ServiceResponse)
async def update_service_status(
    service_id: int,
    status_data: ServiceStatusUpdate,
    db: Session = Depends(get_db),
    current_user_token: dict = Depends(require_admin)
):
    """
    Update service status (Admin only).
    
    Requirements: 4.4 - Admin can manage service status
    """
    # Get current user
    current_user = db.query(User).filter(User.id == int(current_user_token["sub"])).first()
    if not current_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Get service
    service = db.query(Service).filter(Service.id == service_id).first()
    if not service:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Service not found"
        )
    
    # Verify user can modify this service
    if not service.can_be_modified_by(current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions to update service status"
        )
    
    # Update status
    service.is_active = status_data.is_active
    db.commit()
    db.refresh(service)
    
    return service


@router.get("/list", response_model=ServiceList)
async def list_services(
    active_only: bool = Query(True, description="Filter to show only active services"),
    limit: int = Query(10, ge=1, le=100, description="Maximum number of services to return"),
    offset: int = Query(0, ge=0, description="Number of services to skip"),
    search: Optional[str] = Query(None, description="Search query for service name or description"),
    db: Session = Depends(get_db)
):
    """
    List all services with optional filtering.
    Public endpoint - no authentication required.
    
    Requirements: 5.1 - Users can browse available services
    """
    # Build query
    query = db.query(Service)
    
    # Apply filters
    if active_only:
        query = query.filter(Service.is_active == True)
    
    if search:
        search_term = f"%{search}%"
        query = query.filter(
            or_(
                Service.name.ilike(search_term),
                Service.description.ilike(search_term)
            )
        )
    
    # Get total count before pagination
    total_count = query.count()
    active_count = db.query(Service).filter(Service.is_active == True).count()
    
    # Apply pagination
    services = query.order_by(Service.created_at.desc()).offset(offset).limit(limit).all()
    
    return ServiceList(
        services=services,
        total=total_count,
        active_count=active_count
    )


@router.get("/{service_id}", response_model=ServiceDetailResponse)
async def get_service_detail(
    service_id: int,
    db: Session = Depends(get_db)
):
    """
    Get detailed information about a specific service.
    Public endpoint - no authentication required.
    
    Requirements: 5.2 - Users can view service details
    """
    # Get service with creator information
    service = db.query(Service).filter(Service.id == service_id).first()
    
    if not service:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Service not found"
        )
    
    # For inactive services, only show to admins
    if not service.is_active:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Service not found"
        )
    
    # Create response with creator username
    response_data = ServiceDetailResponse.from_orm(service)
    response_data.creator_username = service.creator_username
    
    return response_data


@router.get("/search/advanced", response_model=ServiceList)
async def advanced_service_search(
    query: Optional[str] = Query(None, description="Search query"),
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
    created_by: Optional[int] = Query(None, description="Filter by creator user ID"),
    limit: int = Query(10, ge=1, le=100, description="Maximum number of results"),
    offset: int = Query(0, ge=0, description="Number of results to skip"),
    db: Session = Depends(get_db)
):
    """
    Advanced service search with multiple filters.
    Public endpoint - no authentication required.
    
    Requirements: 5.3 - Advanced service browsing capabilities
    """
    # Build query
    db_query = db.query(Service)
    
    # Apply filters
    if query:
        search_term = f"%{query}%"
        db_query = db_query.filter(
            or_(
                Service.name.ilike(search_term),
                Service.description.ilike(search_term)
            )
        )
    
    if is_active is not None:
        db_query = db_query.filter(Service.is_active == is_active)
    
    if created_by is not None:
        db_query = db_query.filter(Service.created_by == created_by)
    
    # Get total count before pagination
    total_count = db_query.count()
    active_count = db.query(Service).filter(Service.is_active == True).count()
    
    # Apply pagination and ordering
    services = db_query.order_by(Service.created_at.desc()).offset(offset).limit(limit).all()
    
    return ServiceList(
        services=services,
        total=total_count,
        active_count=active_count
    )


@router.get("/admin/all", response_model=ServiceList)
async def get_all_services_admin(
    include_inactive: bool = Query(True, description="Include inactive services"),
    limit: int = Query(50, ge=1, le=100, description="Maximum number of services to return"),
    offset: int = Query(0, ge=0, description="Number of services to skip"),
    db: Session = Depends(get_db),
    current_user_token: dict = Depends(require_admin)
):
    """
    Get all services including inactive ones (Admin only).
    
    Requirements: 4.4 - Admin can view all services including inactive ones
    """
    # Build query
    query = db.query(Service)
    
    # Include inactive services only if requested
    if not include_inactive:
        query = query.filter(Service.is_active == True)
    
    # Get counts
    total_count = query.count()
    active_count = db.query(Service).filter(Service.is_active == True).count()
    
    # Apply pagination
    services = query.order_by(Service.created_at.desc()).offset(offset).limit(limit).all()
    
    return ServiceList(
        services=services,
        total=total_count,
        active_count=active_count
    )


@router.get("/stats/summary")
async def get_service_statistics(
    db: Session = Depends(get_db),
    current_user_token: dict = Depends(require_admin)
):
    """
    Get service statistics (Admin only).
    
    Requirements: 4.4 - Admin can view service statistics
    """
    # Get various statistics
    total_services = db.query(Service).count()
    active_services = db.query(Service).filter(Service.is_active == True).count()
    inactive_services = total_services - active_services
    
    # Get services by creator
    services_by_creator = db.query(
        User.username,
        func.count(Service.id).label('service_count')
    ).join(Service, User.id == Service.created_by).group_by(User.username).all()
    
    # Get recent services (last 30 days)
    from datetime import datetime, timedelta
    thirty_days_ago = datetime.utcnow() - timedelta(days=30)
    recent_services = db.query(Service).filter(
        Service.created_at >= thirty_days_ago
    ).count()
    
    return {
        "total_services": total_services,
        "active_services": active_services,
        "inactive_services": inactive_services,
        "recent_services_30_days": recent_services,
        "services_by_creator": [
            {"creator": creator, "count": count}
            for creator, count in services_by_creator
        ]
    }


# ============================================================================
# SERVICE EXECUTION ENDPOINTS (User-facing service proxy functionality)
# ============================================================================

@router.get("/available/types")
async def get_service_types(db: Session = Depends(get_db)):
    """
    Get all available service types.
    Public endpoint - no authentication required.
    """
    service_types = db.query(Service.type).filter(Service.is_active == True).distinct().all()
    return {
        "service_types": [service_type[0] for service_type in service_types]
    }


@router.get("/available/types/{service_type}")
async def get_services_by_type(
    service_type: str = Path(..., description="Service type (e.g., 'ride', 'food')"),
    db: Session = Depends(get_db)
):
    """
    Get all active services of a specific type.
    Public endpoint - no authentication required.
    """
    services = db.query(Service).filter(
        and_(Service.type == service_type.lower(), Service.is_active == True)
    ).all()
    
    if not services:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No active services found for type '{service_type}'"
        )
    
    return {
        "service_type": service_type,
        "services": [
            {
                "id": service.id,
                "name": service.name,
                "description": service.description
            }
            for service in services
        ]
    }


@router.get("/available/{service_type}/{service_name}/schema", response_model=ServiceSchemaResponse)
async def get_service_schema(
    service_type: str = Path(..., description="Service type"),
    service_name: str = Path(..., description="Service name"),
    db: Session = Depends(get_db)
):
    """
    Get the parameter schema for a specific service.
    Shows what parameters are required to call the service.
    """
    service = db.query(Service).filter(
        and_(
            Service.type == service_type.lower(),
            Service.name.ilike(service_name),
            Service.is_active == True
        )
    ).first()
    
    if not service:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Service '{service_name}' of type '{service_type}' not found"
        )
    
    schema = external_api_service.get_service_schema(service)
    return ServiceSchemaResponse(**schema)


@router.post("/available/{service_type}/{service_name}/execute", response_model=ServiceExecuteResponse)
async def execute_service(
    request_data: ServiceExecuteRequest,
    service_type: str = Path(..., description="Service type"),
    service_name: str = Path(..., description="Service name"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Execute a service call to an external API.
    Requires user authentication.
    """
    # Find the service
    service = db.query(Service).filter(
        and_(
            Service.type == service_type.lower(),
            Service.name.ilike(service_name),
            Service.is_active == True
        )
    ).first()
    
    if not service:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Service '{service_name}' of type '{service_type}' not found"
        )
    
    # Validate parameters
    is_valid, error_message = external_api_service.validate_service_parameters(
        service, request_data.parameters
    )
    if not is_valid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error_message
        )
    
    # Execute the service call
    success, response_data, status_code, execution_time = await external_api_service.execute_service_call(
        service, request_data.parameters
    )
    
    return ServiceExecuteResponse(
        success=success,
        data=response_data if success else None,
        error=response_data if not success else None,
        status_code=status_code,
        execution_time_ms=execution_time
    )


@router.post("/admin/{service_id}/test", response_model=ServiceExecuteResponse)
async def test_service_configuration(
    service_id: int,
    test_request: ServiceTestRequest,
    db: Session = Depends(get_db),
    current_user_token: dict = Depends(require_admin)
):
    """
    Test a service configuration with sample parameters (Admin only).
    Useful for validating service setup before making it active.
    """
    # Get service
    service = db.query(Service).filter(Service.id == service_id).first()
    if not service:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Service not found"
        )
    
    # Validate parameters
    is_valid, error_message = external_api_service.validate_service_parameters(
        service, test_request.test_parameters
    )
    if not is_valid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Test parameters invalid: {error_message}"
        )
    
    # Execute test call
    success, response_data, status_code, execution_time = await external_api_service.execute_service_call(
        service, test_request.test_parameters
    )
    
    return ServiceExecuteResponse(
        success=success,
        data=response_data if success else None,
        error=response_data if not success else None,
        status_code=status_code,
        execution_time_ms=execution_time
    )