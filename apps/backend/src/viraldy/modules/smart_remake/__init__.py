"""Viraldy integration for the Smart Remake 8s/16s workflow."""

from typing import Any

__all__ = ["router"]


def __getattr__(name: str) -> Any:
    if name != "router":
        raise AttributeError(name)
    from .router import router

    globals()["router"] = router
    return router
