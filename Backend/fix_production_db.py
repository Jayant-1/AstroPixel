"""
Direct SQL fix for production PostgreSQL database
Run this to fix the user_id column type immediately without code deployment
"""

import logging
from sqlalchemy import text
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.config import settings

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def fix_production_db():
    """Fix production database immediately"""
    logger.info("Connecting to production database...")
    logger.info(f"Database: {settings.DATABASE_URL}")
    
    engine = create_engine(settings.DATABASE_URL, echo=False)
    SessionLocal = sessionmaker(bind=engine)
    db = SessionLocal()
    
    try:
        logger.info("Step 1: Dropping foreign key constraint if it exists...")
        try:
            db.execute(text("""
                ALTER TABLE annotations 
                DROP CONSTRAINT IF EXISTS annotations_user_id_fkey CASCADE;
            """))
            db.commit()
            logger.info("✅ Foreign key dropped")
        except Exception as e:
            logger.info(f"ℹ️  No foreign key constraint found: {e}")
            db.rollback()
        
        logger.info("Step 2: Altering user_id column type from INTEGER to VARCHAR(255)...")
        db.execute(text("""
            ALTER TABLE annotations 
            ALTER COLUMN user_id TYPE VARCHAR(255) USING CAST(user_id AS VARCHAR);
        """))
        db.commit()
        logger.info("✅ Column type changed to VARCHAR(255)")
        
        logger.info("Step 3: Setting default value for user_id...")
        db.execute(text("""
            ALTER TABLE annotations 
            ALTER COLUMN user_id SET DEFAULT 'anonymous';
        """))
        db.commit()
        logger.info("✅ Default value set to 'anonymous'")
        
        logger.info("✅ Production database schema fix completed!")
        logger.info("Annotations with user_id='demo-user' should now work correctly")
        
    except Exception as e:
        db.rollback()
        logger.error(f"❌ Error during migration: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    fix_production_db()
