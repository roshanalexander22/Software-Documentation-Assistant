---
doc_id: DOC-FA-004
title: OAuth2 Password Flow and JWT Authentication in FastAPI
version: v0.115
framework: FastAPI
category: Security
tags: [security, oauth2, jwt, authentication, authorization, passwords]
source_url: https://fastapi.tiangolo.com/tutorial/security/oauth2-jwt/
---

# OAuth2 Password Flow and JWT Authentication in FastAPI

FastAPI provides built-in utilities for implementing standard OAuth2 specification flows with JSON Web Tokens (JWT) for stateless, secure user authentication.

## Core Security Concepts

- `OAuth2PasswordBearer`: Tells FastAPI that the client will send a Bearer token in the `Authorization` header (`Authorization: Bearer <token>`).
- `OAuth2PasswordRequestForm`: Form parser for extracting `username` and `password` submitted to the `/token` login route.
- Token generation: Uses HMAC-SHA256 (`HS256`) signature with an expiration timestamp (`exp`).

## Complete Authentication Implementation

```python
from datetime import datetime, timedelta, timezone
from typing import Annotated, Optional
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from pydantic import BaseModel
import jwt

SECRET_KEY = "super-secret-developer-key-change-in-production"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

app = FastAPI(title="FastAPI Security Service", version="0.115.0")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    username: Optional[str] = None

class User(BaseModel):
    username: str
    email: str
    disabled: bool = False

# Simulated database
FAKE_USERS_DB = {
    "alice": {
        "username": "alice",
        "email": "alice@example.com",
        "hashed_password": "fakehashedsecretpassword123",
        "disabled": False,
    }
}

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (expires_delta or timedelta(minutes=15))
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

async def get_current_user(token: Annotated[str, Depends(oauth2_scheme)]) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
    except Exception:
        raise credentials_exception
        
    user_dict = FAKE_USERS_DB.get(username)
    if user_dict is None:
        raise credentials_exception
    return User(**user_dict)

@app.post("/token", response_model=Token)
async def login_for_access_token(form_data: Annotated[OAuth2PasswordRequestForm, Depends()]):
    user = FAKE_USERS_DB.get(form_data.username)
    if not user or form_data.password != "secretpassword123":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token = create_access_token(
        data={"sub": user["username"]},
        expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    return {"access_token": access_token, "token_type": "bearer"}

@app.get("/users/me", response_model=User)
async def read_users_me(current_user: Annotated[User, Depends(get_current_user)]):
    return current_user
```

## Security Best Practices
- Always store hashed passwords using algorithms like bcrypt or argon2. Never store plaintext passwords.
- Verify JWT expiration (`exp`) and audience/issuer claims where appropriate.
- Configure HTTPS in production so tokens cannot be intercepted in transit.
