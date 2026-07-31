from __future__ import annotations

from dataclasses import dataclass

from pydantic import BaseModel, ValidationError

from viraldy.modules.ai_gateway.providers.base import OutputValidator, ProviderErrorCode

_MAX_REPAIR_OUTPUT_CHARS = 12000
_MAX_VALIDATION_SUMMARY_CHARS = 2000


@dataclass(frozen=True, slots=True)
class StructuredOutputIssue:
    code: ProviderErrorCode
    summary: str


class StructuredOutputValidationError(ValueError):
    def __init__(self, issue: StructuredOutputIssue) -> None:
        self.issue = issue
        super().__init__(issue.summary)


def validate_structured_output(
    parsed: object,
    output_model: type[BaseModel],
    validator: OutputValidator | None = None,
) -> BaseModel:
    try:
        if isinstance(parsed, output_model):
            output = parsed
        elif isinstance(parsed, BaseModel):
            output = output_model.model_validate(parsed.model_dump(mode="python"))
        else:
            output = output_model.model_validate(parsed)
    except ValidationError as exc:
        raise StructuredOutputValidationError(
            StructuredOutputIssue(
                code=ProviderErrorCode.OUTPUT_INVALID,
                summary=_validation_summary(exc),
            )
        ) from exc

    if validator is not None:
        try:
            validator(output)
        except StructuredOutputValidationError:
            raise
        except ValueError as exc:
            reason = " ".join(str(exc).split())
            summary = "Domain validation rejected the structured output."
            if reason:
                summary = f"{summary} Reason: {reason}"
            raise StructuredOutputValidationError(
                StructuredOutputIssue(
                    code=ProviderErrorCode.DOMAIN_VALIDATION_FAILED,
                    summary=summary[:_MAX_VALIDATION_SUMMARY_CHARS],
                )
            ) from exc
    return output


def repair_messages(
    issue: StructuredOutputIssue,
    invalid_output: str,
) -> tuple[str, str]:
    safe_summary = issue.summary[:_MAX_VALIDATION_SUMMARY_CHARS]
    bounded_output = invalid_output[:_MAX_REPAIR_OUTPUT_CHARS]
    developer_message = (
        "Repair the previous structured output against the same required schema. "
        "Preserve supported evidence and unknown values. Do not remove required evidence, "
        "invent facts, or change the requested business meaning."
    )
    user_message = (
        f"Validation error code: {issue.code.value}\n"
        f"Validation summary: {safe_summary}\n"
        "Invalid output to repair:\n"
        f"{bounded_output or '[parsed output unavailable]'}"
    )
    return developer_message, user_message


def _validation_summary(exc: ValidationError) -> str:
    errors: list[str] = []
    for error in exc.errors(include_url=False, include_context=False, include_input=False)[:8]:
        location = ".".join(str(part) for part in error["loc"]) or "output"
        errors.append(f"{location}: {error['msg']}")
    summary = "; ".join(errors) or "Structured output did not match the required schema."
    return summary[:_MAX_VALIDATION_SUMMARY_CHARS]
