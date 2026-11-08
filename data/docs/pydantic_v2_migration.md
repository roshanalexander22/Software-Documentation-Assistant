---
doc_id: DOC-PYD-001
title: Pydantic V2 Architecture, Migration Guide, and New Syntax
version: v2.0
framework: Pydantic
category: Data Modeling
tags: [pydantic, v2, migration, model_dump, field_validator, model_validator, configdict]
source_url: https://docs.pydantic.dev/latest/migration/
---

# Pydantic V2 Architecture, Migration Guide, and New Syntax

Pydantic V2 is a ground-up rewrite of Pydantic. The core validation engine was rewritten in Rust (`pydantic-core`), delivering a 5x to 50x speed increase over Pydantic V1.

With this rewrite, several core methods and decorators were deprecated and replaced with cleaner, unambiguous APIs.

## Key Syntax Changes: V1 to V2

| Feature / Intent | Pydantic V1 (Deprecated) | Pydantic V2 (Current Standard) |
| :--- | :--- | :--- |
| Export model to Python dict | `model.dict()` | `model.model_dump()` |
| Export model to JSON string | `model.json()` | `model.model_dump_json()` |
| Field-level validator | `@validator('field')` | `@field_validator('field', mode='after')` |
| Whole-model validator | `@root_validator` | `@model_validator(mode='after')` |
| Model configuration | `class Config:` inner class | `model_config = ConfigDict(...)` attribute |
| Parse from raw Python dict | `Model.parse_obj(data)` | `Model.model_validate(data)` |
| Parse from JSON string | `Model.parse_raw(str)` | `Model.model_validate_json(str)` |
| Schema generation | `Model.schema()` | `Model.model_json_schema()` |

## Modern Pydantic V2 Code Example

```python
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

class UserAccount(BaseModel):
    # Modern V2 configuration dictionary
    model_config = ConfigDict(
        str_strip_whitespace=True,
        populate_by_name=True,
        extra="forbid"
    )
    
    username: str = Field(..., min_length=3, max_length=20)
    email: str
    age: int
    is_active: bool = True

    # Modern V2 Field Validator
    @field_validator("username")
    @classmethod
    def validate_alphanumeric(cls, v: str) -> str:
        if not v.isalnum():
            raise ValueError("username must be alphanumeric")
        return v.lower()

    # Modern V2 Model Validator
    @model_validator(mode="after")
    def verify_account_eligibility(self) -> "UserAccount":
        if self.age < 18 and self.is_active:
            raise ValueError("Minors cannot have an active primary account")
        return self

# Serialization in V2
user = UserAccount(username="JohnDoe123", email="john@example.com", age=25)
data_dict = user.model_dump(exclude_unset=True)
json_string = user.model_dump_json(indent=2)
```

## Migration Notes for FastAPI Developers
FastAPI 0.100.0+ automatically works with Pydantic V2. When upgrading your codebase:
1. Replace all calls to `.dict()` with `.model_dump()`.
2. Replace `@validator` with `@field_validator` and ensure `@classmethod` is added.
3. Replace inner `class Config:` with `model_config = ConfigDict(...)`.
