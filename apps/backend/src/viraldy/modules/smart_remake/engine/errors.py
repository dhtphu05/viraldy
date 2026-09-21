from typing import Any


class SmartRemakeError(Exception):
    def __init__(
        self,
        message: str,
        code: str = "INVALID_SMART_REMAKE_INPUT",
        details: Any | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.details = details


class SmartRemakeDisabledError(SmartRemakeError):
    def __init__(self) -> None:
        super().__init__(
            "Smart Remake is disabled. Set SMART_REMAKE_ENABLED=true to enable it.",
            "SMART_REMAKE_DISABLED",
        )


class SmartRemakeValidationError(SmartRemakeError):
    pass


class SmartRemakeSecurityError(SmartRemakeError):
    pass
