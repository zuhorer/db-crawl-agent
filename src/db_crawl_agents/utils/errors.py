class LLMError(Exception):
    """Generic LLM error."""


class RateLimitError(LLMError):
    pass


class AuthError(LLMError):
    pass