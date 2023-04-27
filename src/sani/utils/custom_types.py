from typing import Union, Dict, List, Any, Tuple, NamedTuple, Type, Generator, Optional
import types
from enum import Enum
import ast
from abc import ABC, abstractmethod, abstractclassmethod
import io

JsonType = Union[
    Dict[str, Any],
    List[Any],
]

Comment = NamedTuple(
    "Comment",
    [
        ("text", str),
        ("lineno", int),
        ("multiline", bool),
    ],
)
script = NamedTuple(
    "Script",
    [
        ("lenght", int),
        ("lines", List[str]),
        ("string", str),
        ("lined_string", str),
        ("lined_list", List[str]),
        ("ast", ast.AST),
        ("imports", str),
        ("comments", List[Comment]),
        (
            "ast_dump",
            str,
        ),
    ],
)
block_object = NamedTuple(
    "Block",
    [
        ("block", str),
        ("startline", int),
        ("endline", int),
        ("block_ast_dump", str),
        ("block_comments", str),
    ],
)


engine = NamedTuple(
    "Terminal",
    [
        ("terminal_type", str),
        ("exit_code", int),
        ("command", str),
    ],
)

io_object = NamedTuple("IO", [("path", str), ("stream", io.TextIOWrapper)])


class Mode(str, Enum):
    """
    Enum for execution mode
    """

    fix = "fix"
    document = "document"
    test = "test"
    improve = "improve"
    ai_function = "ai_fn"
    regex = "regex"
    analyze = "analyze"


class Language(str, Enum):
    python = "python"
    javascript = "javascript"
    go = "go"
    c = "c"
    ruby = "ruby"
    html = "html"
    shell = "shell"


class Code(str, Enum):
    success = "success"
    failed = "failed"
    inprogress = "inprogress"
    syntax = "syntax"
    indent = "indent"
    error = "error"
    enable = "enable"
    disable = "disable"
    end_breakpoint = "debugger_end_breakpoint"
    end_syntax = "sani:end"


class Context(str, Enum):
    execution = "execution"
    output = "output"
    traceback = "traceback"
    exception_type = "exception_type"
    exception_message = "exception_message"
    full_traceback = "full_traceback"
    error_line = "error_line"
    status = "status"
    source = "source"
    startline = "startline"
    endline = "endline"
    code = "code"
    block = "block"
    imports = "imports"
    lined_code = "lined_code"
    code_ast_dump = "code_ast_dump"
    linenos = "linenos"
    block_ast = "block_ast"
    prompt = "prompt"
    suggestions = "suggestions"
    linter = "linter"
    value = "value"
    lint_format = "format"
    block_comments = "block_comments"
    subject = "subject"
    comments = "comments"
    mode = "mode"
    referer = "referer"
    flag = "flag"
    language = "language"
    context = "context"
    pid = "pid"


class Enums(str, Enum):
    members = "_member_map_"
    values = "_value2member_map_"


class Os(str, Enum):
    """
    Operating Systems Enum
    """

    linux = "linux"
    linux2 = "linux2"
    ubuntu = "ubuntu"
    mac = "darwin"
    windows32 = "win32"
    windows64 = "win64"
