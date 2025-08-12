"""
Services service for service management.
"""
from typing import List, Optional
from sqlmodel import Session, select
from app.models.service import Service
from app.schemas.services import ServiceCreate

class ServicesService:
    """Service for services operations."""
    
    def __init__(self, db: Session):
        self.db = db
    
    def get_services(
        self, 
        active_only: bool = True, 
        limit: int = 10, 
        offset: int = 0
    ) -> List[Service]:
        """Get services with filtering."""
        statement = select(Service)
        
        if active_only:
            statement = statement.where(Service.is_active == True)
        
        statement = statement.offset(offset).limit(limit)
        return self.db.exec(statement).all()
    
    def create_service(self, service_data: ServiceCreate, created_by: int) -> Service:
        """Create a new service."""
        service = Service(
            name=service_data.name,
            description=service_data.description,
            created_by=created_by,
            is_active=True
        )
        
        self.db.add(service)
        self.db.commit()
        self.db.refresh(service)
        
        return service
    
    def get_service_by_id(self, service_id: int) -> Optional[Service]:
        """Get service by ID."""
        statement = select(Service).where(Service.id == service_id)
        return self.db.exec(statement).first()
    
    def update_service(self, service_id: int, service_data: ServiceCreate) -> Optional[Service]:
        """Update a service."""
        service = self.get_service_by_id(service_id)
        if not service:
            return None
        
        service.name = service_data.name
        service.description = service_data.description
        
        self.db.commit()
        self.db.refresh(service)
        
        return service
    
    def delete_service(self, service_id: int) -> bool:
        """Delete a service."""
        service = self.get_service_by_id(service_id)
        if not service:
            return False
        
        self.db.delete(service)
        self.db.commit()
        
        return True