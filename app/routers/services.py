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
from app.models.agent import Agent, UserService
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
# Authentication removed for hackathon demo
# from app.core.security import get_current_user_token, require_admin
from app.services.external_api_service import external_api_service
from app.utils import success_response, error_response

router = APIRouter(prefix="/services", tags=["services"])


# Mock user for hackathon demo (no authentication required)
def get_mock_user() -> User:
    """Return a mock user for demo purposes."""
    return User(
        id=1,
        username="demo",
        is_active=True
    )


# Authentication removed for hackathon demo
# def get_current_user(
#     db: Session = Depends(get_db),
#     current_user_token: dict = Depends(get_current_user_token)
# ) -> User:
#     """Get current user from database."""
#     user = db.exec(select(User).where(User.id == int(current_user_token["sub"]))).first()
#     if not user:
#         raise HTTPException(
#             status_code=status.HTTP_404_NOT_FOUND,
#             detail="User not found"
#         )
#     return success_response(message="User retrieved successfully", data=user)


@router.post("/create", response_model=ServiceResponse, status_code=status.HTTP_201_CREATED)
async def create_service(
    service_data: ServiceCreate,
    db: Session = Depends(get_db),
    # Authentication removed for hackathon demo
    # current_user_token: dict = Depends(require_admin)
    current_user: User = Depends(get_mock_user)
):
    """
    Create a new service with external API configuration (Admin only).
    
    Requirements: 4.1 - Admin can create services
    """
    # Authentication removed for hackathon demo - using mock user
    # Get current user
    # current_user = db.exec(select(User).where(User.id == int(current_user_token["sub"]))).first()
    # if not current_user:
    #     raise HTTPException(
    #         status_code=status.HTTP_404_NOT_FOUND,
    #         detail="User not found"
    #     )
    
    # For demo purposes, allow all users to create services
    # (No admin check needed)
    
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
    
    return success_response(
        message="Service created successfully",
        data=ServiceResponse.from_orm(new_service),
        status_code=201
    )


@router.put("/{service_id}", response_model=ServiceResponse)
async def update_service(
    service_id: int,
    service_data: ServiceUpdate,
    db: Session = Depends(get_db),
    # Authentication removed for hackathon demo
    # current_user_token: dict = Depends(require_admin)
    current_user: User = Depends(get_mock_user)
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
    
    return success_response(
        message="Service updated successfully",
        data=ServiceResponse.from_orm(service)
    )


@router.delete("/{service_id}", response_model=ServiceDeleteResponse)
async def delete_service(
    service_id: int,
    db: Session = Depends(get_db),
    # Authentication removed for hackathon demo
    # current_user_token: dict = Depends(require_admin)
    current_user: User = Depends(get_mock_user)
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
    
    return success_response(
        message=f"Service '{service.name}' deleted successfully",
        data=ServiceDeleteResponse(message=f"Service '{service.name}' deleted successfully")
    )


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
    
    # Calculate active count
    active_query = select(func.count()).select_from(Service).where(Service.is_active == True)
    if type:
        active_query = active_query.where(Service.type == type)
    active_count = db.exec(active_query).one()
    
    services = db.exec(query.order_by(Service.name).offset(offset).limit(limit)).all()
    
    return success_response(
        message="Services retrieved successfully",
        data=ServiceList(
            services=[ServiceResponse.from_orm(s) for s in services],
            total=total_count,
            active_count=active_count
        ).dict()
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
        
    return success_response(
        message="Service details retrieved successfully",
        data=ServiceDetailResponse.from_orm(service)
    )


@router.post("/{service_id}/execute", response_model=ServiceExecuteResponse)
async def execute_service(
    service_id: int,
    request_data: ServiceExecuteRequest,
    db: Session = Depends(get_db),
    # Authentication removed for hackathon demo
    # current_user: User = Depends(get_current_user)
    current_user: User = Depends(get_mock_user)
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
        return success_response(
            message="Service executed successfully",
            data=ServiceExecuteResponse(
                status="success",
                data=result
            )
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
    # Authentication removed for hackathon demo
    # current_user_token: dict = Depends(require_admin)
    current_user: User = Depends(get_mock_user)
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
    
    return success_response(
        message="Service status updated successfully",
        data=ServiceResponse.from_orm(service)
    )


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
    
    return success_response(
        message="Services search completed successfully",
        data=ServiceList(
            services=[ServiceResponse.from_orm(s) for s in services],
            total=total_count,
            limit=search_query.limit,
            offset=search_query.offset
        ).dict()
    )


@router.post("/test-service", response_model=ServiceExecuteResponse)
async def test_service_execution(
    test_request: ServiceTestRequest,
    db: Session = Depends(get_db),
    # Authentication removed for hackathon demo
    # current_user: User = Depends(get_current_user)
    current_user: User = Depends(get_mock_user)
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
        return success_response(
            message="Service test executed successfully",
            data=ServiceExecuteResponse(
                status="success",
                data=result
            )
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
        
        return success_response(
            message="Service schema retrieved successfully",
            data=ServiceSchemaResponse(
                request_schema=request_schema,
                response_schema=response_schema
            )
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Could not generate schema: {e}"
        )


# User Agent Service Management Endpoints

@router.post("/user/agent/services", response_model=dict)
async def add_service_to_agent(
    service_id: int,
    db: Session = Depends(get_db),
    # Authentication removed for hackathon demo
    # current_user: User = Depends(get_current_user)
    current_user: User = Depends(get_mock_user)
):
    """
    Add a service to the user's agent (plug-and-play).
    """
    # Check if service exists
    service = db.exec(select(Service).where(Service.id == service_id)).first()
    if not service:
        raise HTTPException(status_code=404, detail="Service not found")

    # Check if already added
    existing = db.exec(select(UserService).where(
        and_(UserService.user_id == current_user.id, UserService.service_id == service_id)
    )).first()
    if existing:
        raise HTTPException(status_code=409, detail="Service already added to agent")

    # Get or create agent for user
    agent = db.exec(select(Agent).where(Agent.user_id == current_user.id)).first()
    if not agent:
        agent = Agent(user_id=current_user.id)
        db.add(agent)
        db.commit()
        db.refresh(agent)

    # Add service to user_services
    user_service = UserService(
        user_id=current_user.id,
        service_id=service_id,
        agent_id=agent.id
    )
    db.add(user_service)
    db.commit()

    return success_response(
        message="Service added to agent successfully",
        data={"agent_id": agent.id}
    )


@router.delete("/user/agent/services/{service_id}", response_model=dict)
async def remove_service_from_agent(
    service_id: int,
    db: Session = Depends(get_db),
    # Authentication removed for hackathon demo
    # current_user: User = Depends(get_current_user)
    current_user: User = Depends(get_mock_user)
):
    """
    Remove a service from the user's agent.
    """
    user_service = db.exec(select(UserService).where(
        and_(UserService.user_id == current_user.id, UserService.service_id == service_id)
    )).first()
    if not user_service:
        raise HTTPException(status_code=404, detail="Service not found in agent")

    db.delete(user_service)
    db.commit()

    return success_response(message="Service removed from agent successfully")


@router.get("/user/agent/services", response_model=dict)
async def get_user_agent_services(
    db: Session = Depends(get_db),
    # Authentication removed for hackathon demo
    # current_user: User = Depends(get_current_user)
    current_user: User = Depends(get_mock_user)
):
    """
    Get all services added to the user's agent.
    """
    user_services = db.exec(select(UserService).where(
        and_(UserService.user_id == current_user.id, UserService.is_active == True)
    )).all()

    services = []
    for us in user_services:
        service = db.exec(select(Service).where(Service.id == us.service_id)).first()
        if service:
            services.append({
                "id": service.id,
                "name": service.name,
                "type": service.type,
                "description": service.description,
                "added_at": us.added_at
            })

    return success_response(
        message="User agent services retrieved successfully",
        data={"services": services}
    )