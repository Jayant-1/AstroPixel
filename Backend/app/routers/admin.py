"""
Admin panel routes for system administration
Requires admin privileges to access
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime
from typing import List

from app.database import get_db
from app.models import User, Dataset
from app.schemas import (
    MessageResponse,
)
from app.services.auth import get_current_user_required

router = APIRouter()

# Admin credentials
ADMIN_USERNAME = "Admin"
ADMIN_PASSWORD_HASH = None  # Will be set on first run

def is_admin(current_user: User) -> bool:
    """Check if user is admin"""
    return current_user.username == ADMIN_USERNAME


def verify_admin(current_user: User = Depends(get_current_user_required)):
    """Dependency to verify admin access"""
    if not is_admin(current_user):
        raise HTTPException(status_code=403, detail="Admin access required")
    return current_user


@router.get("/admin/stats", dependencies=[Depends(verify_admin)])
async def get_admin_stats(db: Session = Depends(get_db)):
    """
    Get system statistics (admin only)
    
    Returns:
    - Total users
    - Total datasets
    - Total demo datasets
    - Total user uploads (non-demo)
    - Total storage used
    - Average dataset size
    """
    try:
        # User statistics
        total_users = db.query(func.count(User.id)).scalar() or 0
        
        # Dataset statistics
        total_datasets = db.query(func.count(Dataset.id)).scalar() or 0
        demo_datasets = db.query(func.count(Dataset.id)).filter(
            Dataset.is_demo == True
        ).scalar() or 0
        user_datasets = total_datasets - demo_datasets
        
        # Storage statistics
        total_pixels = db.query(
            func.sum(Dataset.width * Dataset.height)
        ).scalar() or 0
        
        # Calculate storage in GB (assuming 3 bytes per pixel on average)
        storage_gb = (total_pixels * 3) / (1024**3) if total_pixels else 0
        
        # Average dataset size
        avg_pixels = total_pixels / user_datasets if user_datasets > 0 else 0
        avg_size_mp = (avg_pixels / (1024**2)) if avg_pixels else 0
        
        # Processing statistics
        completed_datasets = db.query(func.count(Dataset.id)).filter(
            Dataset.processing_status == "completed"
        ).scalar() or 0
        processing_datasets = db.query(func.count(Dataset.id)).filter(
            Dataset.processing_status == "processing"
        ).scalar() or 0
        failed_datasets = db.query(func.count(Dataset.id)).filter(
            Dataset.processing_status == "failed"
        ).scalar() or 0
        
        return {
            "users": {
                "total": total_users,
                "created_today": db.query(func.count(User.id)).filter(
                    func.date(User.created_at) == datetime.utcnow().date()
                ).scalar() or 0,
            },
            "datasets": {
                "total": total_datasets,
                "demo": demo_datasets,
                "user_uploads": user_datasets,
                "completed": completed_datasets,
                "processing": processing_datasets,
                "failed": failed_datasets,
            },
            "storage": {
                "total_gb": round(storage_gb, 2),
                "avg_dataset_mp": round(avg_size_mp, 2),
            },
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/admin/users", dependencies=[Depends(verify_admin)])
async def get_all_users(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
):
    """
    Get list of all users with their statistics (admin only)
    
    Returns:
    - User ID, username, email
    - Created date
    - Number of datasets
    - Total storage used
    - Last active (last dataset creation/access)
    """
    try:
        users = db.query(User).offset(skip).limit(limit).all()
        
        user_list = []
        for user in users:
            # Count user's datasets
            user_datasets = db.query(func.count(Dataset.id)).filter(
                Dataset.owner_id == user.id,
                Dataset.is_demo == False,
            ).scalar() or 0
            
            # Calculate storage used
            total_pixels = db.query(
                func.sum(Dataset.width * Dataset.height)
            ).filter(
                Dataset.owner_id == user.id,
                Dataset.is_demo == False,
            ).scalar() or 0
            
            storage_mb = (total_pixels * 3) / (1024**2) if total_pixels else 0
            
            # Get latest dataset
            latest_dataset = db.query(Dataset.created_at).filter(
                Dataset.owner_id == user.id
            ).order_by(Dataset.created_at.desc()).first()
            
            user_list.append({
                "id": user.id,
                "username": user.username,
                "email": user.email,
                "created_at": user.created_at,
                "datasets_count": user_datasets,
                "storage_mb": round(storage_mb, 2),
                "last_active": latest_dataset[0] if latest_dataset else None,
            })
        
        return {
            "total_users": db.query(func.count(User.id)).scalar() or 0,
            "users": user_list,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/admin/datasets", dependencies=[Depends(verify_admin)])
async def get_all_datasets(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
):
    """
    Get list of all datasets with their statistics (admin only)
    
    Returns:
    - Dataset ID, name, owner
    - Size, category, status
    - Created/updated dates
    - Expiry information
    """
    try:
        datasets = db.query(Dataset).offset(skip).limit(limit).all()
        
        dataset_list = []
        for dataset in datasets:
            # Get owner info
            owner = None
            if dataset.owner_id:
                owner = db.query(User).filter(User.id == dataset.owner_id).first()
            
            dataset_list.append({
                "id": dataset.id,
                "name": dataset.name,
                "category": dataset.category,
                "owner_id": dataset.owner_id,
                "owner_email": owner.email if owner else "Demo",
                "size_pixels": dataset.width * dataset.height,
                "size_mp": round((dataset.width * dataset.height) / (1024**2), 2),
                "processing_status": dataset.processing_status,
                "is_demo": dataset.is_demo,
                "expires_at": dataset.expires_at,
                "created_at": dataset.created_at,
                "updated_at": dataset.updated_at,
            })
        
        return {
            "total_datasets": db.query(func.count(Dataset.id)).scalar() or 0,
            "datasets": dataset_list,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/admin/datasets/{dataset_id}", dependencies=[Depends(verify_admin)])
async def admin_delete_dataset(
    dataset_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(verify_admin),
):
    """
    Force delete any dataset (admin only)
    
    Used for removing spam, expired, or problematic datasets
    """
    from app.services.dataset_processor import DatasetProcessor
    
    try:
        dataset = db.query(Dataset).filter(Dataset.id == dataset_id).first()
        
        if not dataset:
            raise HTTPException(status_code=404, detail="Dataset not found")
        
        # Delete dataset files and database entry
        success = DatasetProcessor.delete_dataset(dataset_id, db)
        
        if not success:
            raise HTTPException(status_code=500, detail="Failed to delete dataset")
        
        return {
            "message": f"Dataset {dataset_id} deleted by admin",
            "deleted_by": current_user.username,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/admin/users/{user_id}", dependencies=[Depends(verify_admin)])
async def admin_delete_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(verify_admin),
):
    """
    Force delete any user and their datasets (admin only)
    
    Cascades to delete all user's datasets
    """
    try:
        if user_id == current_user.id:
            raise HTTPException(status_code=400, detail="Cannot delete yourself")
        
        user = db.query(User).filter(User.id == user_id).first()
        
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        if user.username == ADMIN_USERNAME:
            raise HTTPException(status_code=400, detail="Cannot delete admin user")
        
        # Delete all user's datasets first
        from app.services.dataset_processor import DatasetProcessor
        
        user_datasets = db.query(Dataset).filter(Dataset.owner_id == user_id).all()
        for dataset in user_datasets:
            DatasetProcessor.delete_dataset(dataset.id, db)
        
        # Delete user
        db.delete(user)
        db.commit()
        
        return {
            "message": f"User {user.email} and all their datasets deleted",
            "deleted_by": current_user.username,
            "datasets_deleted": len(user_datasets),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/admin/activity", dependencies=[Depends(verify_admin)])
async def get_system_activity(
    db: Session = Depends(get_db),
):
    """
    Get recent system activity (admin only)
    
    Returns:
    - Recently created datasets
    - Recently created users
    - System events
    """
    try:
        # Recent datasets
        recent_datasets = db.query(Dataset).order_by(
            Dataset.created_at.desc()
        ).limit(10).all()
        
        recent_datasets_list = [
            {
                "type": "dataset_created",
                "name": d.name,
                "owner": db.query(User).filter(User.id == d.owner_id).first().email if d.owner_id else "Demo",
                "timestamp": d.created_at,
                "status": d.processing_status,
            }
            for d in recent_datasets
        ]
        
        # Recent users
        recent_users = db.query(User).order_by(
            User.created_at.desc()
        ).limit(10).all()
        
        recent_users_list = [
            {
                "type": "user_signup",
                "email": u.email,
                "timestamp": u.created_at,
            }
            for u in recent_users
        ]
        
        # Combine and sort
        activities = recent_datasets_list + recent_users_list
        activities.sort(key=lambda x: x["timestamp"], reverse=True)
        
        return {
            "recent_activities": activities[:20],
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/admin/init", response_model=dict)
async def initialize_admin(db: Session = Depends(get_db)):
    """
    Initialize admin user on first run
    
    Username: Admin
    Password: admin@jayant.com
    
    Should only work once (fails if admin already exists)
    """
    try:
        # Check if admin already exists
        existing_admin = db.query(User).filter(
            User.username == ADMIN_USERNAME
        ).first()
        
        if existing_admin:
            raise HTTPException(
                status_code=400,
                detail="Admin user already exists"
            )
        
        # Hash the password using bcrypt
        from passlib.context import CryptContext
        
        pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
        hashed_password = pwd_context.hash("admin@jayant.com")
        
        # Create admin user
        admin_user = User(
            username=ADMIN_USERNAME,
            email="admin@astropixel.local",
            hashed_password=hashed_password,
            is_active=True,
        )
        
        db.add(admin_user)
        db.commit()
        db.refresh(admin_user)
        
        return {
            "message": "Admin user initialized successfully",
            "username": ADMIN_USERNAME,
            "email": admin_user.email,
        }
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
