# src/api/dependencies/auth.py
from fastapi import Security, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from src.config.settings import settings

security = HTTPBearer()

def verify_token(credentials: HTTPAuthorizationCredentials = Security(security)) -> bool:
    """Verify the API token."""
    if credentials.credentials not in settings.bearer_tokens_list:
        raise HTTPException(
            status_code=401,
            detail="Invalid API token"
        )
    return True