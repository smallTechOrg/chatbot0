"""ServiceError: a request that failed in a way the API answers with a status and a message that is safe to show."""


class ServiceError(Exception):
    def __init__(self, message: str, status: int):
        super().__init__(message)
        self.message = message
        self.status = status
