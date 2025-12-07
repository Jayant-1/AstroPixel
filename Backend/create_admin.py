"""
Create Admin User in Neon Database
===================================
Creates the hardcoded admin user that matches the frontend expectations.

Username: Admin
Email: admin@astropixel.local
Password: admin123

Usage:
    python create_admin.py
"""

import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).resolve().parent))

from app.database import SessionLocal
from app.models import User
from app.services.auth import get_password_hash
import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def create_admin_user():
    """Create the admin user in the database"""
    db = SessionLocal()
    
    try:
        # Check if admin already exists
        existing_admin = db.query(User).filter(User.username == "Admin").first()
        
        if existing_admin:
            logger.info("✅ Admin user already exists")
            logger.info(f"   Username: {existing_admin.username}")
            logger.info(f"   Email: {existing_admin.email}")
            logger.info(f"   Is Superuser: {existing_admin.is_superuser}")
            return existing_admin
        
        # Create new admin user
        logger.info("Creating admin user...")
        
        admin_user = User(
            username="Admin",
            email="admin@astropixel.local",
            hashed_password=get_password_hash("admin123"),
            full_name="System Administrator",
            is_superuser=True,
            is_active=True
        )
        
        db.add(admin_user)
        db.commit()
        db.refresh(admin_user)
        
        logger.info("✅ Admin user created successfully!")
        logger.info(f"   ID: {admin_user.id}")
        logger.info(f"   Username: {admin_user.username}")
        logger.info(f"   Email: {admin_user.email}")
        logger.info(f"   Is Superuser: {admin_user.is_superuser}")
        logger.info("\n📝 Login Credentials:")
        logger.info("   Username: Admin")
        logger.info("   Password: admin123")
        
        return admin_user
        
    except Exception as e:
        logger.error(f"❌ Failed to create admin user: {e}", exc_info=True)
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    print("\n🔐 AstroPixel Admin User Creation\n")
    create_admin_user()
    print("\n✨ Done!\n")
