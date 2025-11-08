"""Custom exception handlers for Meshup backend."""
from rest_framework.views import exception_handler


def custom_exception_handler(exc, context):
    """Wrap DRF exceptions to ensure consistent response schema."""
    response = exception_handler(exc, context)

    if response is None:
        return response

    response.data = {
        "status_code": response.status_code,
        "error": response.data,
        "detail": response.data.get("detail") if isinstance(response.data, dict) else None,
    }
    return response
