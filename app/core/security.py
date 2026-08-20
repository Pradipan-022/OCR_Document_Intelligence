from passlib.context import CryptContext

#Set up password hashing context using bcrypt
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Check if the provided plain password matches the stored hash"""
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    """Generate a secure hash from a plain password string"""
    return pwd_context.hash(password)