from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_password_hash, verify_password
from app.models.user_model import User
from app.schemas.user_schema import UserCreateSchema, UserLoginSchema, UserResponseSchema

router = APIRouter()

@router.post("/register", response_model=UserResponseSchema, status_code=status.HTTP_201_CREATED)
def register_user(user_in: UserCreateSchema, db: Session = Depends(get_db)):
    """Creates a user with a hashed password"""
    existing_user = db.query(User).filter(User.username == user_in.username).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already exists"
        )
    
    #Hash raw password
    hashed_pwd = get_password_hash(user_in.password)
    
    new_user = User(
        username = user_in.username,
        hashed_password = hashed_pwd
    )
    
    try:
        db.add(new_user)
        db.commit()
        db.refresh(new_user)
        return new_user
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to register user: {str(e)}"
        )

@router.post("/login", response_model=UserResponseSchema)
def login_user(credentials: UserLoginSchema, db: Session = Depends(get_db)):
    """Validates username and password against DB hash"""
    user = db.query(User). filter(User.username == credentials.username).first()
    
    if not user or not verify_password(credentials.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password"
        )
    
    return user
    
    