"""
JWT Authentication Middleware

Validates JWT tokens and manages user authentication/authorization.
"""

from datetime import datetime, timedelta
from typing import Optional, Dict, Any
import structlog

from fastapi import Request, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from passlib.context import CryptContext
from starlette.middleware.base import BaseHTTPMiddleware

from app.config import settings

logger = structlog.get_logger()

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# HTTP Bearer token scheme
security = HTTPBearer(auto_error=False)


class AuthMiddleware(BaseHTTPMiddleware):
    """JWT authentication middleware."""

    # Public endpoints that don't require authentication
    PUBLIC_PATHS = [
        "/",
        "/docs",
        "/redoc",
        "/openapi.json",
        "/health",
        "/ready",
        "/metrics",
        "/api/v1/auth/login",
        "/api/v1/auth/register",
        "/api/v1/auth/refresh",
    ]

    async def dispatch(self, request: Request, call_next):
        """Process request and validate JWT token."""
        # Skip authentication for public paths
        if any(request.url.path.startswith(path) for path in self.PUBLIC_PATHS):
            return await call_next(request)

        # Extract token from Authorization header
        auth_header = request.headers.get("Authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            logger.warning("missing_auth_token", path=request.url.path)
            return self._unauthorized_response("Missing authentication token")

        token = auth_header.replace("Bearer ", "")

        # Validate token
        try:
            payload = decode_jwt_token(token)
            request.state.user_id = payload.get("sub")
            request.state.username = payload.get("username")
            request.state.roles = payload.get("roles", [])

            logger.debug(
                "request_authenticated",
                user_id=request.state.user_id,
                path=request.url.path,
            )

        except JWTError as e:
            logger.warning("invalid_jwt_token", error=str(e), path=request.url.path)
            return self._unauthorized_response("Invalid authentication token")

        return await call_next(request)

    def _unauthorized_response(self, message: str):
        """Return 401 Unauthorized response."""
        return HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=message,
            headers={"WWW-Authenticate": "Bearer"},
        )


def create_access_token(
    data: Dict[str, Any],
    expires_delta: Optional[timedelta] = None,
) -> str:
    """
    Create JWT access token.

    Args:
        data: Token payload data
        expires_delta: Token expiration time

    Returns:
        Encoded JWT token
    """
    to_encode = data.copy()

    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.JWT_EXPIRATION_MINUTES)

    to_encode.update({"exp": expire, "iat": datetime.utcnow()})

    encoded_jwt = jwt.encode(
        to_encode,
        settings.JWT_SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM,
    )

    return encoded_jwt


def create_refresh_token(user_id: str) -> str:
    """
    Create JWT refresh token.

    Args:
        user_id: User identifier

    Returns:
        Encoded refresh token
    """
    expire = datetime.utcnow() + timedelta(days=settings.JWT_REFRESH_EXPIRATION_DAYS)

    to_encode = {
        "sub": user_id,
        "type": "refresh",
        "exp": expire,
        "iat": datetime.utcnow(),
    }

    encoded_jwt = jwt.encode(
        to_encode,
        settings.JWT_SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM,
    )

    return encoded_jwt


def decode_jwt_token(token: str) -> Dict[str, Any]:
    """
    Decode and validate JWT token.

    Args:
        token: JWT token string

    Returns:
        Token payload

    Raises:
        JWTError: If token is invalid or expired
    """
    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
        )
        return payload

    except JWTError as e:
        logger.error("jwt_decode_error", error=str(e))
        raise


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify password against hash.

    Args:
        plain_password: Plain text password
        hashed_password: Hashed password

    Returns:
        True if password matches
    """
    return pwd_context.verify(plain_password, hashed_password)


def hash_password(password: str) -> str:
    """
    Hash password using bcrypt.

    Args:
        password: Plain text password

    Returns:
        Hashed password
    """
    return pwd_context.hash(password)


def get_current_user(request: Request) -> Dict[str, Any]:
    """
    Get current authenticated user from request state.

    Args:
        request: FastAPI request object

    Returns:
        User information dictionary

    Raises:
        HTTPException: If user is not authenticated
    """
    if not hasattr(request.state, "user_id"):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
        )

    return {
        "user_id": request.state.user_id,
        "username": request.state.username,
        "roles": request.state.roles,
    }


def require_roles(required_roles: list[str]):
    """
    Dependency to require specific roles for endpoint access.

    Args:
        required_roles: List of required role names

    Returns:
        Dependency function

    Raises:
        HTTPException: If user doesn't have required roles
    """

    def role_checker(request: Request):
        user = get_current_user(request)
        user_roles = user.get("roles", [])

        if not any(role in user_roles for role in required_roles):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Insufficient permissions. Required roles: {required_roles}",
            )

        return user

    return role_checker
