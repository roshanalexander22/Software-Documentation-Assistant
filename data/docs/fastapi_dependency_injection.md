---
doc_id: DOC-FA-003
title: Modern Dependency Injection with typing.Annotated in FastAPI
version: v0.115
framework: FastAPI
category: Dependencies
tags: [dependency-injection, depends, annotated, modern, typing]
source_url: https://fastapi.tiangolo.com/tutorial/dependencies/
---

# Modern Dependency Injection with typing.Annotated in FastAPI

Starting with FastAPI version 0.95.0 and emphasized in FastAPI 0.115+, the official and recommended standard for declaring dependencies is using Python's `typing.Annotated` (or `typing_extensions.Annotated` for Python <3.9).

## The Evolution of Dependency Syntax

### Legacy Approach (FastAPI < 0.95)
In older code, `Depends(...)` was passed as the default parameter value:
```python
# Legacy style - not recommended in modern FastAPI
@app.get("/items")
async def read_items(db: Session = Depends(get_db), token: str = Depends(oauth2_scheme)):
    return {"token": token}
```
**Problems with legacy style**:
- Default values mask whether the parameter is actually optional or required.
- Standard static type checkers (mypy, pyright) cannot verify parameter types accurately when default values differ from runtime assignments.
- Repeating `Depends(get_db)` across multiple route definitions violates DRY.

### Modern Annotated Approach (FastAPI >= 0.95 and 0.115+)
Using `Annotated`, the type annotation contains both the data type and the metadata dependency rule:

```python
from typing import Annotated
from fastapi import FastAPI, Depends, Header, HTTPException, status

app = FastAPI(title="Modern DI API", version="0.115.0")

# Reusable dependency types
def verify_api_key(x_api_key: Annotated[str, Header()]):
    if x_api_key != "secret-token-123":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing API key"
        )
    return x_api_key

# Type alias definition for dependency injection
ApiKeyDep = Annotated[str, Depends(verify_api_key)]

class DatabaseSession:
    def query(self, entity: str):
        return [f"{entity}_1", f"{entity}_2"]

def get_db():
    db = DatabaseSession()
    try:
        yield db
    finally:
        pass  # cleanup session

DbSessionDep = Annotated[DatabaseSession, Depends(get_db)]

@app.get("/secure-data")
async def get_secure_data(api_key: ApiKeyDep, db: DbSessionDep):
    """
    Endpoint protected by ApiKeyDep and injecting DbSessionDep.
    Both dependencies are cleanly typed and easily mocked in unit tests.
    """
    records = db.query("User")
    return {"status": "authenticated", "records": records}
```

## Advantages of Annotated Type Aliases

1. **Clean Signature**: Route parameters do not have awkward default values (`= Depends(...)`).
2. **Reusability**: Type aliases like `DbSessionDep` can be imported across any router file.
3. **Painless Testing**: Pytest test suites can override dependencies using `app.dependency_overrides[get_db] = mock_get_db` seamlessly.
