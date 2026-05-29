"""
Sécurité — JWT + bcrypt
"""
from datetime import datetime, timedelta
from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic import BaseModel
import os
import secrets
import string

SECRET_KEY = os.getenv("SECRET_KEY", "changeme_please_32chars_minimum!!")
ALGORITHM  = os.getenv("JWT_ALGORITHM", "HS256")
EXPIRE_MIN = int(os.getenv("JWT_EXPIRE_MINUTES", 1440))  # 24h par défaut

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class TokenData(BaseModel):
    user_id: str
    email:   str
    plan:    str


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


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
