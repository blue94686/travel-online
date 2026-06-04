"""JWT authentication and password hashing utilities."""
import os
from datetime import datetime, timedelta, timezone

import bcrypt
from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt

JWT_SECRET_KEY = os.environ.get("JWT_SECRET_KEY", "scenic-online-dev-secret-change-in-production")
JWT_ALGORITHM = "HS256"
JWT_EXPIRE_MINUTES = 60 * 24  # 24 hours

bearer_scheme = HTTPBearer(auto_error=False)


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    if not hashed:
        return False
    try:
        # bcrypt hashed
        if hashed.startswith("$2b$") or hashed.startswith("$2a$"):
            return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))
        # Legacy plaintext fallback
        return plain == hashed
    except Exception:
        return plain == hashed


def create_access_token(data: dict, expires_delta: timedelta | None = None) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (expires_delta or timedelta(minutes=JWT_EXPIRE_MINUTES))
    to_encode["exp"] = expire
    return jwt.encode(to_encode, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)


def decode_access_token(token: str) -> dict | None:
    try:
        return jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
    except JWTError:
        return None


async def get_current_user(request: Request) -> dict | None:
    """Extract user from Authorization header. Returns None if not authenticated."""
    auth: HTTPAuthorizationCredentials | None = await bearer_scheme(request)
    if not auth or not auth.credentials:
        return None
    payload = decode_access_token(auth.credentials)
    if not payload:
        return None
    user_id = payload.get("sub")
    if not user_id:
        return None
    from app.core.database import get_db
    with get_db() as db:
        user = db.execute("SELECT * FROM users WHERE id=?", (int(user_id),)).fetchone()
    if not user:
        return None
    return dict(user)


async def require_user(user: dict | None = Depends(get_current_user)) -> dict:
    """Require authenticated user. Raises 401 if not logged in."""
    if not user:
        raise HTTPException(status_code=401, detail="请先登录")
    return user


def require_role(*roles: str):
    """Dependency factory: require specific role(s)."""
    async def _check(user: dict = Depends(require_user)) -> dict:
        if user.get("role") not in roles:
            raise HTTPException(status_code=403, detail="权限不足")
        return user
    return _check
