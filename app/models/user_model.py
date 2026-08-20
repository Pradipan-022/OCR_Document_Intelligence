import uuid
from datetime import datetime, timezone
from sqlalchemy import String, DateTime
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base

class User(Base):
    """Represents a registered user in the database"""
    
    __tablename__ = "users"
    
    #Unique user ID UUID primary key
    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4())
    )
    
    #Username for login identification
    username: Mapped[str] = mapped_column(
        String(50),
        unique=True,
        index=True,
        nullable=False,
    )
    
    #Securely hashed password(bcrypt)
    hashed_password: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    
    #Account creation timestamp (stored in UTC)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )