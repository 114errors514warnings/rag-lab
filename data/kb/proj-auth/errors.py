"""错误码定义（proj-auth）。"""

AUTH_INVALID_CREDENTIALS = "AUTH_1001"
AUTH_USER_DISABLED = "AUTH_1002"
AUTH_TOKEN_EXPIRED = "AUTH_1003"
AUTH_PERMISSION_DENIED = "AUTH_1004"


class AuthError(Exception):
    """带错误码的认证异常。"""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message

    def __str__(self) -> str:
        return f"[{self.code}] {self.message}"
