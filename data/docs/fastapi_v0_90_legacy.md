---
doc_id: DOC-FA-011
title: FastAPI v0.90 Legacy Query and Path Validation (Deprecated Regex Syntax)
version: v0.90-legacy
framework: FastAPI
category: Validation
tags: [legacy, query, path, regex, pattern, deprecated]
source_url: https://fastapi.tiangolo.com/tutorial/query-params-str-validations/
---

# FastAPI v0.90 Legacy Query and Path Validation (Deprecated Regex Syntax)

In FastAPI versions prior to 0.100 (such as v0.90), parameter validations in `Query`, `Path`, and `Header` used Pydantic V1 argument conventions.

## Regex Parameter Deprecation

In FastAPI v0.90, regular expressions were provided via the `regex` keyword argument:

```python
# Legacy FastAPI v0.90 Syntax
from fastapi import FastAPI, Query

app = FastAPI(version="0.90.0")

@app.get("/legacy-items/")
async def read_legacy_items(
    q: str = Query(None, min_length=3, max_length=50, regex="^[a-zA-Z0-9_-]+$")
):
    return {"q": q}
```

## Migration to FastAPI Modern Syntax (`pattern`)

In modern FastAPI with Pydantic V2, the `regex` argument has been replaced by `pattern`:

```python
# Modern FastAPI v0.115 Syntax
from typing import Annotated
from fastapi import FastAPI, Query

app = FastAPI(version="0.115.0")

@app.get("/items/")
async def read_items(
    q: Annotated[str | None, Query(min_length=3, max_length=50, pattern="^[a-zA-Z0-9_-]+$")] = None
):
    return {"q": q}
```

Passing `regex=` in newer versions triggers a deprecation warning: *"The `regex` parameter is deprecated in Pydantic V2, use `pattern` instead."*

