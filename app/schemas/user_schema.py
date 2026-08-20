from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field

class UserCreateSchema(BaseModel):
    """Schema for incoming HTTP POST request payload during registration"""
    
    username: str = Field(..., min_length=3, max_length=50, description="Unique username")
    password: str = Field(..., min_length=6, description="Raw plain password")
    
class UserLoginSchema(BaseModel):
    """Schema for incoming HTTP POST request payload during login"""
    
    username: str
    password: str
    
class UserResponseSchema(BaseModel):
    """Schema for outgoing HTTP JSON response payload"""
    
    id: str
    username: str
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)