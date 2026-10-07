class AppError(Exception):
    status_code = 500
    code = "INTERNAL_ERROR"

    def __init__(self, message: str = "An unexpected error occurred."):
        self.message = message
        super().__init__(message)


class BadRequestError(AppError):
    status_code, code = 400, "BAD_REQUEST"


class UnauthorizedError(AppError):
    status_code, code = 401, "UNAUTHORIZED"


class ForbiddenError(AppError):
    status_code, code = 403, "FORBIDDEN"


class NotFoundError(AppError):
    status_code, code = 404, "NOT_FOUND"


class ConflictError(AppError):
    status_code, code = 409, "CONFLICT"


class RateLimitError(AppError):
    status_code, code = 429, "RATE_LIMITED"


class DatabaseError(AppError):
    status_code, code = 500, "DATABASE_ERROR"


class NLPServiceError(AppError):
    status_code, code = 502, "NLP_SERVICE_ERROR"


class MLServiceError(AppError):
    status_code, code = 502, "ML_SERVICE_ERROR"
