---
doc_id: DOC-FA-008
title: Custom Error Handling and Exception Handlers in FastAPI
version: v0.115
framework: FastAPI
category: Error Handling
tags: [error-handling, exceptions, httpexception, validationerror, handlers]
source_url: https://fastapi.tiangolo.com/tutorial/handling-errors/
---

# Custom Error Handling and Exception Handlers in FastAPI

FastAPI provides standard HTTP exceptions as well as the ability to override built-in validation error handlers and register custom domain exception handlers.

## Standard HTTPException

Throwing `HTTPException` terminates request execution and returns an RFC-compliant JSON response:

```python
from fastapi import FastAPI, HTTPException, status

app = FastAPI(title="Error Handling Service", version="0.115.0")

ITEMS = {"foo": "The Foo Item"}

@app.get("/items/{item_id}")
async def read_item(item_id: str):
    if item_id not in ITEMS:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Item with id '{item_id}' not found.",
            headers={"X-Error-Reason": "ItemDoesNotExist"}
        )
    return {"item": ITEMS[item_id]}
```

## Custom Business Exceptions & Handlers

Custom exception classes allow decoupling business logic from web HTTP status codes:

```python
from fastapi import Request
from fastapi.responses import JSONResponse

class ItemOutOfStockException(Exception):
    def __init__(self, item_name: str, requested: int, available: int):
        self.item_name = item_name
        self.requested = requested
        self.available = available

@app.exception_handler(ItemOutOfStockException)
async def item_out_of_stock_handler(request: Request, exc: ItemOutOfStockException):
    return JSONResponse(
        status_code=409,
        content={
            "error_code": "OUT_OF_STOCK",
            "message": f"Cannot fulfill order for {exc.item_name}.",
            "requested": exc.requested,
            "available": exc.available,
            "path": str(request.url)
        }
    )
```

## Overriding RequestValidationError

By default, FastAPI returns validation errors in Starlette's format. You can customize the 422 Unprocessable Entity payload:

```python
from fastapi.exceptions import RequestValidationError

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    errors = [{"field": err["loc"], "msg": err["msg"]} for err in exc.errors()]
    return JSONResponse(
        status_code=422,
        content={
            "status": "validation_failed",
            "total_errors": len(errors),
            "errors": errors
        }
    )
```
