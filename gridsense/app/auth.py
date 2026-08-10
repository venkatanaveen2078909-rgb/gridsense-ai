"""
GRIDSENSE Auth Module — Phase 3
JWT creation and validation, RBAC decorators.
"""
from __future__ import annotations
import os
import jwt
import bcrypt
from functools import wraps
from datetime import datetime, timezone, timedelta
from flask import request, jsonify, g
from app.logging_config import get_logger

log = get_logger(__name__)

JWT_SECRET  = os.getenv("JWT_SECRET", "super_secret_jwt_signing_key_for_gridsense")
JWT_ALGO    = "HS256"
JWT_EXPIRY_H = 8  # 8 hours


def create_token(user_id: int, tenant_id: str, email: str, role: str) -> str:
    payload = {
        "sub": str(user_id),
        "tid": tenant_id,
        "email": email,
        "role": role,
        "iat": datetime.now(timezone.utc),
        "exp": datetime.now(timezone.utc) + timedelta(hours=JWT_EXPIRY_H),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGO)


def verify_token(token: str) -> dict | None:
    try:
        return jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGO])
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None


def require_jwt(*allowed_roles):
    """
    Decorator that requires a valid JWT and optionally restricts access by role.
    Usage:
        @require_jwt()                         # any authenticated user
        @require_jwt("Admin", "Operator")      # specific roles only
    Sets g.tenant_id, g.user_id, g.role on the request context.
    """
    def decorator(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            auth = request.headers.get("Authorization", "")
            token = auth.removeprefix("Bearer ").strip()
            if not token:
                return jsonify({"error": "Authentication required"}), 401
            payload = verify_token(token)
            if not payload:
                return jsonify({"error": "Invalid or expired token"}), 401
            if allowed_roles and payload.get("role") not in allowed_roles:
                return jsonify({"error": "Insufficient permissions"}), 403
            g.tenant_id = payload["tid"]
            g.user_id   = payload["sub"]
            g.role      = payload["role"]
            g.email     = payload["email"]
            return f(*args, **kwargs)
        return decorated
    return decorator


def hash_password(plain: str) -> str:
    return bcrypt.hashpw(plain.encode(), bcrypt.gensalt()).decode()


def check_password(plain: str, hashed: str) -> bool:
    return bcrypt.checkpw(plain.encode(), hashed.encode())
