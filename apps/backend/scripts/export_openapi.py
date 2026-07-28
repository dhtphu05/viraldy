from __future__ import annotations

import json
from pathlib import Path

from viraldy.api.main import app


def main() -> None:
    output = Path("../../docs/api/openapi.json").resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(app.openapi(), indent=2, sort_keys=True), encoding="utf-8")
    print(output)


if __name__ == "__main__":
    main()
