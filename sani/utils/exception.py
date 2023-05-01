# TerminalNotSupportedError
# OsNotSupportedError


class UnterminatedCommentError(Exception):
    """Raised if an Unterminated multi-line comment is encountered."""


class UnsupportedError(Exception):
    """Raised when trying to extract comments from an unsupported MIME type."""


class ParseError(Exception):
    """Raised when a parser issue is encountered."""


class CallerNotFoundError(Exception):
    """Raised when a module or caller is not found."""
