"""
Migration script to update Annotation.user_id from INTEGER to VARCHAR(255)
This handles both SQLite and PostgreSQL databases
"""

import logging
from sqlalchemy import text, inspect
from app.database import engine, SessionLocal
from app.config import settings

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def get_db_type():
    """Determine database type from connection string"""
    if "postgresql" in settings.DATABASE_URL or "postgres" in settings.DATABASE_URL:
        return "postgresql"
    elif "sqlite" in settings.DATABASE_URL:
        return "sqlite"
    else:
        return "unknown"


def check_column_type(db_type):
    """Check current user_id column type"""
    inspector = inspect(engine)
    
    if not inspector.has_table("annotations"):
        logger.info("annotations table does not exist yet")
        return None
    
    columns = inspector.get_columns("annotations")
    for col in columns:
        if col["name"] == "user_id":
            return col["type"]
    
    return None


def migrate_postgresql():
    """Migrate PostgreSQL database"""
    logger.info("Migrating PostgreSQL database...")
    
    db = SessionLocal()
    try:
        # Check if column exists and is integer type
        current_type = check_column_type("postgresql")
        logger.info(f"Current user_id column type: {current_type}")
        
        # Drop the foreign key constraint if it exists
        logger.info("Dropping foreign key constraint if it exists...")
        try:
            db.execute(text("""
                ALTER TABLE annotations 
                DROP CONSTRAINT IF EXISTS annotations_user_id_fkey;
            """))
            logger.info("Foreign key constraint dropped")
        except Exception as e:
            logger.info(f"No foreign key to drop: {e}")
        
        # Alter the column type from INTEGER to VARCHAR
        logger.info("Altering user_id column type to VARCHAR(255)...")
        db.execute(text("""
            ALTER TABLE annotations 
            ALTER COLUMN user_id TYPE VARCHAR(255);
        """))
        
        # Set default value
        logger.info("Setting default value for user_id...")
        db.execute(text("""
            ALTER TABLE annotations 
            ALTER COLUMN user_id SET DEFAULT 'anonymous';
        """))
        
        db.commit()
        logger.info("✅ PostgreSQL migration completed successfully")
        
    except Exception as e:
        db.rollback()
        logger.error(f"❌ PostgreSQL migration failed: {e}")
        raise
    finally:
        db.close()


def migrate_sqlite():
    """Migrate SQLite database"""
    logger.info("Migrating SQLite database...")
    
    db = SessionLocal()
    try:
        # SQLite doesn't support direct ALTER COLUMN, so we need to recreate the table
        logger.info("Recreating annotations table...")
        
        # Create backup table
        db.execute(text("""
            ALTER TABLE annotations RENAME TO annotations_backup;
        """))
        
        # Create new table with correct schema
        db.execute(text("""
            CREATE TABLE annotations (
                id INTEGER NOT NULL, 
                dataset_id INTEGER NOT NULL, 
                user_id VARCHAR(255), 
                geometry_json JSON NOT NULL, 
                annotation_type VARCHAR(50), 
                label VARCHAR(255) NOT NULL, 
                description TEXT, 
                properties JSON, 
                confidence REAL, 
                created_at DATETIME NOT NULL, 
                updated_at DATETIME NOT NULL, 
                PRIMARY KEY (id), 
                FOREIGN KEY(dataset_id) REFERENCES datasets (id) ON DELETE CASCADE
            );
        """))
        
        # Copy data from backup, converting user_id to string if needed
        db.execute(text("""
            INSERT INTO annotations (
                id, dataset_id, user_id, geometry_json, annotation_type, 
                label, description, properties, confidence, created_at, updated_at
            )
            SELECT 
                id, dataset_id, 
                COALESCE(CAST(user_id AS TEXT), 'anonymous') AS user_id,
                geometry_json, annotation_type, label, description, 
                properties, confidence, created_at, updated_at
            FROM annotations_backup;
        """))
        
        # Drop backup table
        db.execute(text("""
            DROP TABLE annotations_backup;
        """))
        
        # Recreate indexes
        db.execute(text("""
            CREATE INDEX ix_annotations_dataset_id ON annotations (dataset_id);
        """))
        db.execute(text("""
            CREATE INDEX ix_annotations_label ON annotations (label);
        """))
        db.execute(text("""
            CREATE INDEX ix_annotations_user_id ON annotations (user_id);
        """))
        
        db.commit()
        logger.info("✅ SQLite migration completed successfully")
        
    except Exception as e:
        db.rollback()
        logger.error(f"❌ SQLite migration failed: {e}")
        raise
    finally:
        db.close()


def main():
    """Run migration"""
    logger.info(f"Starting database migration...")
    logger.info(f"Database URL: {settings.DATABASE_URL}")
    
    db_type = get_db_type()
    logger.info(f"Detected database type: {db_type}")
    
    if db_type == "postgresql":
        migrate_postgresql()
    elif db_type == "sqlite":
        migrate_sqlite()
    else:
        logger.error(f"Unknown database type: {db_type}")
        raise ValueError(f"Unknown database type: {db_type}")
    
    logger.info("✅ Migration completed!")


if __name__ == "__main__":
    main()
