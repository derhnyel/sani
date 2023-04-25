# TerminalNotSupportedError
# OsNotSupportedError


class UnterminatedCommentError(Exception):
    """Raised if an Unterminated multi-line comment is encountered."""


class UnsupportedError(BaseException):
    """Raised when trying to extract comments from an unsupported MIME type."""


class ParseError(BaseException):
    """Raised when a parser issue is encountered."""
