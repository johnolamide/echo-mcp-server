"""
Migration script to update the services table with new columns for external API integration.
"""
import os
import sys
from sqlalchemy import create_engine, text
from sqlalchemy.exc import OperationalError

# Add the app directory to the path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.core.config import settings
from app.db.database import Base, engine
from app.models.service import Service
from app.models.user import User
from app.models.chat import ChatMessage

def migrate_services_table():
    """Migrate the services table to include new columns."""
    print("🔄 Starting services table migration...")
    
    try:
        # Create a connection
        with engine.connect() as connection:
            # Check if we're using SQLite (for testing) or MySQL/TiDB
            result = connection.execute(text("SELECT 1"))
            
            # For SQLite, we need to recreate the table
            # For MySQL/TiDB, we can use ALTER TABLE
            
            try:
                # Try to check if new columns already exist
                connection.execute(text("SELECT type FROM services LIMIT 1"))
                print("✅ Services table already has new columns - migration not needed")
                return True
            except OperationalError:
                # Columns don't exist, need to migrate
                pass
            
            print("📝 Adding new columns to services table...")
            
            # Add new columns one by one
            migration_queries = [
                "ALTER TABLE services ADD COLUMN type VARCHAR(100) DEFAULT 'general'",
                "ALTER TABLE services ADD COLUMN api_base_url VARCHAR(500) DEFAULT ''",
                "ALTER TABLE services ADD COLUMN api_endpoint VARCHAR(255) DEFAULT '/'",
                "ALTER TABLE services ADD COLUMN http_method VARCHAR(10) DEFAULT 'POST'",
                "ALTER TABLE services ADD COLUMN request_template JSON",
                "ALTER TABLE services ADD COLUMN response_mapping JSON",
                "ALTER TABLE services ADD COLUMN headers_template JSON",
                "ALTER TABLE services ADD COLUMN encrypted_api_key VARCHAR(500)",
                "ALTER TABLE services ADD COLUMN api_key_header VARCHAR(100)",
                "ALTER TABLE services ADD COLUMN timeout_seconds INTEGER DEFAULT 30",
                "ALTER TABLE services ADD COLUMN retry_attempts INTEGER DEFAULT 3",
            ]
            
            for query in migration_queries:
                try:
                    connection.execute(text(query))
                    print(f"✅ Executed: {query}")
                except OperationalError as e:
                    if "Duplicate column name" in str(e) or "duplicate column name" in str(e):
                        print(f"⚠️  Column already exists: {query}")
                    else:
                        print(f"❌ Failed: {query} - {e}")
                        raise
            
            # Update existing services with default values
            connection.execute(text("""
                UPDATE services 
                SET 
                    type = 'general',
                    api_base_url = 'https://api.example.com',
                    api_endpoint = '/service',
                    http_method = 'POST',
                    request_template = '{}',
                    timeout_seconds = 30,
                    retry_attempts = 3
                WHERE type IS NULL OR type = ''
            """))
            
            # Create indexes for new columns
            index_queries = [
                "CREATE INDEX IF NOT EXISTS idx_service_type_active ON services(type, is_active)",
                "CREATE INDEX IF NOT EXISTS idx_service_type_name ON services(type, name)",
            ]
            
            for query in index_queries:
                try:
                    connection.execute(text(query))
                    print(f"✅ Created index: {query}")
                except OperationalError as e:
                    print(f"⚠️  Index might already exist: {e}")
            
            connection.commit()
            print("✅ Services table migration completed successfully!")
            return True
            
    except Exception as e:
        print(f"❌ Migration failed: {e}")
        return False

def create_sample_services():
    """Create sample services for testing."""
    print("\n🎯 Creating sample services...")
    
    from app.db.database import SessionLocal
    from app.models.user import User
    from app.models.service import Service
    
    db = SessionLocal()
    try:
        # Find an admin user or create one
        admin_user = db.query(User).filter(User.is_admin == True).first()
        if not admin_user:
            print("⚠️  No admin user found. Please create an admin user first.")
            return
        
        # Check if sample services already exist
        existing_service = db.query(Service).filter(Service.name == "Mock Uber").first()
        if existing_service:
            print("✅ Sample services already exist")
            return
        
        # Create sample Uber service
        uber_service = Service(
            name="Mock Uber",
            type="ride",
            description="Mock Uber ride service for testing",
            api_base_url="https://httpbin.org",
            api_endpoint="/post",
            http_method="POST",
            request_template={
                "pickup_location": {
                    "lat": "{{pickup_lat}}",
                    "lng": "{{pickup_lng}}"
                },
                "destination": {
                    "lat": "{{destination_lat}}",
                    "lng": "{{destination_lng}}"
                },
                "ride_type": "{{ride_type}}"
            },
            response_mapping={
                "ride_id": "{{response.json.pickup_location.lat}}_{{response.json.destination.lat}}",
                "status": "confirmed",
                "eta_minutes": 5,
                "driver_name": "Test Driver"
            },
            headers_template={
                "Content-Type": "application/json",
                "User-Agent": "FastAPI-Service-Proxy"
            },
            timeout_seconds=30,
            retry_attempts=3,
            created_by=admin_user.id,
            is_active=True
        )
        
        # Create sample food service
        food_service = Service(
            name="Mock DoorDash",
            type="food",
            description="Mock DoorDash food delivery service for testing",
            api_base_url="https://httpbin.org",
            api_endpoint="/post",
            http_method="POST",
            request_template={
                "restaurant_id": "{{restaurant_id}}",
                "items": "{{items}}",
                "delivery_address": "{{address}}",
                "customer_phone": "{{phone}}"
            },
            response_mapping={
                "order_id": "order_{{response.json.restaurant_id}}",
                "status": "confirmed",
                "estimated_delivery_minutes": 30,
                "restaurant_name": "Test Restaurant"
            },
            headers_template={
                "Content-Type": "application/json"
            },
            timeout_seconds=45,
            retry_attempts=2,
            created_by=admin_user.id,
            is_active=True
        )
        
        db.add(uber_service)
        db.add(food_service)
        db.commit()
        
        print("✅ Sample services created:")
        print(f"   • Mock Uber (ride service) - ID: {uber_service.id}")
        print(f"   • Mock DoorDash (food service) - ID: {food_service.id}")
        
    except Exception as e:
        print(f"❌ Failed to create sample services: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    print("🚀 FastAPI Service Proxy Migration")
    print("=" * 50)
    
    # Run migration
    if migrate_services_table():
        create_sample_services()
        print("\n🎉 Migration completed successfully!")
        print("\nYou can now:")
        print("1. Create service vendors via admin endpoints")
        print("2. Test service calls via user endpoints")
        print("3. Use the service proxy functionality")
    else:
        print("\n❌ Migration failed!")
        sys.exit(1)