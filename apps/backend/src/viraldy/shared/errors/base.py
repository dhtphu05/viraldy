from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(slots=True)
class AppError(Exception):
    code: str
    message: str
    status_code: int = 400
    details: dict[str, object] = field(default_factory=dict)


class NotFoundError(AppError):
    def __init__(self, code: str, message: str = "Resource was not found.") -> None:
        super().__init__(code=code, message=message, status_code=404)


class UnauthorizedError(AppError):
    def __init__(self, code: str = "UNAUTHENTICATED", message: str = "Unauthenticated.") -> None:
        super().__init__(code=code, message=message, status_code=401)


class ForbiddenError(AppError):
    def __init__(self, code: str = "FORBIDDEN", message: str = "Forbidden.") -> None:
        super().__init__(code=code, message=message, status_code=403)


class ConflictError(AppError):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(code=code, message=message, status_code=409)


class PayloadTooLargeError(AppError):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(code=code, message=message, status_code=413)
