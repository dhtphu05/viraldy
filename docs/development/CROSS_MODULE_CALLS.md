# Cross-Module Calls

Modules are allowed to call another feature module only through `public.py`.

Allowed:

```python
from viraldy.modules.products.public import ProductQueries
from viraldy.modules.jobs.public import request_process_asset
```

Not allowed:

```python
from viraldy.modules.products.models import ProductModel
from viraldy.modules.products.repository import ProductRepository
from viraldy.modules.products.service import ProductService
```

Public contracts must:

- Accept `workspace_id` for workspace-owned resources.
- Return small stable DTOs or Pydantic schemas.
- Not return SQLAlchemy ORM objects.
- Not expose provider or repository internals.

Architecture tests enforce this for module-to-module imports.
