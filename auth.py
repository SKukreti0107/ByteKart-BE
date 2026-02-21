import os
import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jwt import PyJWKClient
from dotenv import load_dotenv
from sqlmodel import select
from sqlalchemy.ext.asyncio import AsyncSession
from db import get_session
from models import User

load_dotenv()

NEON_AUTH_JWKS_URL = os.getenv("NEON_AUTH_JWKS_URL")

if not NEON_AUTH_JWKS_URL:
    raise ValueError("NEON_AUTH_JWKS_URL environment variable not set")

jwks_client = PyJWKClient(NEON_AUTH_JWKS_URL)
security = HTTPBearer()

def verify_token(token: str):
    try:
        unverified_header = jwt.get_unverified_header(token)
        alg = unverified_header.get("alg", "RS256")
        signing_key = jwks_client.get_signing_key_from_jwt(token)
        data = jwt.decode(
            token,
            signing_key.key,
            algorithms=[alg],
            audience="neon_auth", # Adjust audience if needed based on Neon Auth config
            options={"verify_aud": False}, # Temporarily disable audience verification if not strictly configured
            leeway=60
        )
        return data
    except jwt.PyJWKClientError as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Unable to fetch JWKS")
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token has expired")
    except jwt.InvalidTokenError as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=f"Invalid token: {str(e)}")

def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    token = credentials.credentials
    user_data = verify_token(token)
    return user_data

async def get_db_user(
    current_user: dict = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
) -> User:
    user_id = current_user.get("sub")
    if not user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token: sub missing")
    
    try:
        import uuid
        valid_uuid = uuid.UUID(user_id)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token: sub is not a valid UUID")
    
    result = await session.execute(select(User).where(User.id == valid_uuid))
    user = result.scalars().first()
    
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found in database")
    return user

async def admin_only(user: User = Depends(get_db_user)):
    print(f"Database User: {user}")
    if user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, 
            detail=f"Admin privileges required. Your role: {user.role}"
        )
    return user
