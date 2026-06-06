"""
Sécurité — JWT + bcrypt (sans passlib)
"""
from datetime import datetime, timedelta
from jose import jwt
from pydantic import BaseModel
import bcrypt
import os
import secrets
import string

SECRET_KEY = os.getenv("SECRET_KEY", "changeme_please_32chars_minimum!!")
ALGORITHM  = os.getenv("JWT_ALGORITHM", "HS256")
EXPIRE_MIN = int(os.getenv("JWT_EXPIRE_MINUTES", 1440))


class TokenData(BaseModel):
    user_id: str
    email:   str
    plan:    str


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))


def create_token(data: dict, expires_delta: timedelta = None) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=EXPIRE_MIN))
    to_encode["exp"] = expire
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def decode_token(token: str) -> TokenData:
    payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    return TokenData(
        user_id=payload["user_id"],
        email=payload["email"],
        plan=payload["plan"],
    )


def generate_licence_token(length: int = 32) -> str:
    alphabet = string.ascii_uppercase + string.digits
    return "BRVM-" + "".join(secrets.choice(alphabet) for _ in range(length))
