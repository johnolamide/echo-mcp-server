"""
Database models for Bolt API integration.
"""
from sqlalchemy import Column, String, Integer, DateTime, JSON, Text, Boolean, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.db.database import Base


class BoltProvider(Base):
    """Model for Bolt providers (restaurants/stores)."""
    __tablename__ = "bolt_providers"
    
    id = Column(Integer, primary_key=True, index=True)
    provider_id = Column(String(255), unique=True, index=True, nullable=False)
    provider_type = Column(String(50), nullable=False)  # 'food' or 'stores'
    name = Column(String(255), nullable=False)
    region_id = Column(Integer, nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    orders = relationship("BoltOrder", back_populates="provider")
    menu_items = relationship("BoltMenuItem", back_populates="provider")


class BoltOrder(Base):
    """Model for Bolt orders."""
    __tablename__ = "bolt_orders"
    
    id = Column(Integer, primary_key=True, index=True)
    bolt_order_id = Column(String(255), unique=True, index=True, nullable=False)
    provider_id = Column(String(255), ForeignKey("bolt_providers.provider_id"), nullable=False)
    order_type = Column(String(50), nullable=False)  # 'food', 'stores', 'dine_in'
    customer_info = Column(JSON, nullable=True)
    order_items = Column(JSON, nullable=False)
    total_price = Column(Integer, nullable=False)  # Price in cents
    currency = Column(String(3), default="EUR")
    status = Column(String(50), nullable=False, default="pending")  # pending, accepted, rejected, ready, picked_up, delivered, cancelled
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    delivery_address = Column(JSON, nullable=True)
    courier_info = Column(JSON, nullable=True)
    
    # Relationships
    provider = relationship("BoltProvider", back_populates="orders")


class BoltMenuItem(Base):
    """Model for Bolt menu items."""
    __tablename__ = "bolt_menu_items"
    
    id = Column(Integer, primary_key=True, index=True)
    provider_id = Column(String(255), ForeignKey("bolt_providers.provider_id"), nullable=False)
    external_id = Column(String(255), nullable=False)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    price = Column(Integer, nullable=False)  # Price in cents
    currency = Column(String(3), default="EUR")
    category = Column(String(255), nullable=True)
    is_available = Column(Boolean, default=True)
    menu_data = Column(JSON, nullable=True)  # Full menu item data from Bolt
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    provider = relationship("BoltProvider", back_populates="menu_items")


class BoltWebhookLog(Base):
    """Model for logging Bolt webhook events."""
    __tablename__ = "bolt_webhook_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    webhook_type = Column(String(100), nullable=False)  # new_order, cancel_order, etc.
    provider_type = Column(String(50), nullable=False)  # 'food' or 'stores'
    provider_id = Column(String(255), nullable=True)
    order_id = Column(String(255), nullable=True)
    payload = Column(JSON, nullable=False)
    processing_status = Column(String(50), default="received")  # received, processed, failed
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    processed_at = Column(DateTime(timezone=True), nullable=True)


class BoltApiCall(Base):
    """Model for logging Bolt API calls."""
    __tablename__ = "bolt_api_calls"
    
    id = Column(Integer, primary_key=True, index=True)
    api_type = Column(String(50), nullable=False)  # 'food' or 'stores'
    endpoint = Column(String(255), nullable=False)
    method = Column(String(10), default="POST")
    provider_id = Column(String(255), nullable=True)
    request_payload = Column(JSON, nullable=True)
    response_data = Column(JSON, nullable=True)
    status_code = Column(Integer, nullable=True)
    success = Column(Boolean, default=False)
    error_message = Column(Text, nullable=True)
    execution_time_ms = Column(Integer, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    user_id = Column(Integer, nullable=True)  # User who made the API call through our system
