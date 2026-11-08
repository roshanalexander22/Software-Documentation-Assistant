---
doc_id: DOC-PYD-002
title: Pydantic V1 Legacy API and Validation Reference (Deprecated)
version: v1.10-legacy
framework: Pydantic
category: Data Modeling
tags: [pydantic, v1, legacy, dict, validator, root_validator, config, deprecated]
source_url: https://docs.pydantic.dev/1.10/usage/models/
---

# Pydantic V1 Legacy API and Validation Reference (Deprecated)

In Pydantic version 1 (specifically Pydantic 1.10 and earlier), data models relied on Python-level attribute reflection and inner configuration classes.

Although Pydantic V1 remains partially backwards-compatible via `pydantic.v1` in modern installations, using V1 idioms causes deprecation warnings in modern FastAPI environments.

## Legacy Model Declaration and Inner Config

In Pydantic V1, models configured behavior through an inner class named `Config`:

```python
# Pydantic V1 Legacy Syntax
from pydantic import BaseModel, Field, validator, root_validator

class LegacyUserProfile(BaseModel):
    user_id: int
    full_name: str
    email: str

    class Config:
        orm_mode = True  # Renamed to from_attributes in V2
        allow_population_by_field_name = True  # Renamed to populate_by_name in V2
        validate_assignment = True

    @validator("email")
    def email_must_contain_at(cls, value):
        if "@" not in value:
            raise ValueError("Invalid email format")
        return value

    @root_validator(pre=True)
    def check_legacy_values(cls, values):
        if not values.get("user_id"):
            values["user_id"] = 9999
        return values

# Legacy Serialization
profile = LegacyUserProfile(user_id=1, full_name="Alice Smith", email="alice@test.com")
legacy_dict = profile.dict()  # DEPRECATED in V2 -> use .model_dump()
legacy_json = profile.json()  # DEPRECATED in V2 -> use .model_dump_json()
```

## Deprecated Methods Summary in V1
- `model.dict()`: Emits `PydanticDeprecatedSince20` in modern runtime.
- `model.json()`: Deprecated in favor of `model.model_dump_json()`.
- `@validator`: Deprecated in favor of `@field_validator`.
- `@root_validator`: Deprecated in favor of `@model_validator`.
- `orm_mode = True`: Replaced with `from_attributes = True` in V2.

