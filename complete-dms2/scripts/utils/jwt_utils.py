from datetime import datetime, timedelta
from typing import Optional, Annotated

from fastapi.security import HTTPBearer, OAuth2PasswordBearer
from jose import jwt, JWTError, ExpiredSignatureError
from fastapi import HTTPException, Request, status, Depends
from scripts.constants.app_configuration import settings
from scripts.constants.app_constants import *
from scripts.models.jwt_model import TokenData


SECRET_KEY = settings.JWT_SECRET
ALGORITHM = settings.JWT_ALGORITHM
ACCESS_TOKEN_EXPIRE_MINUTES = settings.ACCESS_TOKEN_EXPIRE_MINUTES


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def create_user_token(username: str, role: str) -> str:
    payload = {
        "sub": username,
        "role": role,
    }
    return create_access_token(payload)


def decode_access_token(token: str) -> TokenData:
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username = payload.get("sub")
        role = payload.get("role")

        if username is None or role is None:
            raise JWTError("Missing username or role in token.")

        return TokenData(username=username, role=role, access_token=token)

    except ExpiredSignatureError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=TOKEN_EXPIRED)
    except JWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=INVALID_TOKEN)


def get_current_user_from_token(request: Request) -> TokenData:
    auth_header: Optional[str] = request.headers.get("Authorization")

    if auth_header and auth_header.lower().startswith("bearer "):
        token = auth_header.split(" ")[1]
        return decode_access_token(token)

    raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=UNAUTHORIZED)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="app1/auth/auth/login")
def get_current_user(token: Annotated[str, Depends(oauth2_scheme)]):
    print(token)
    user = decode_access_token(token)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    return user