from typing import Union, Dict, List, Any, Tuple, NamedTuple, Type, Generator, Optional
import types
import shutil
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


error_object = NamedTuple(
    "Error",
    [
        ("exception_type", str),
        ("exception_message", str),
        ("full_traceback", str),
        ("error_line", int),
    ],
)


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
    text = "text"
    rust = "rust"
    java = "java"
    php = "php"
    typescript = "typescript"
    css = "css"
    sql = "sql"
    dart = "dart"
    kotlin = "kotlin"
    swift = "swift"
    r = "r"
    csharp = "csharp"
    scala = "scala"
    elixir = "elixir"
    erlang = "erlang"
    haskell = "haskell"
    julia = "julia"
    lua = "lua"
    perl = "perl"
    matlab = "matlab"
    cpp = "cpp"
    scss = "scss"


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
    lined_code = "lined_code"
    linenos = "linenos"
    prompt = "prompt"
    suggestions = "suggestions"
    linter = "linter"
    lint_suggestions = "lint_suggestions"
    lint_format = "format"
    block_comments = "code block comments"
    subject = "intended action"
    comments = "full code comments"
    mode = "mode"
    referer = "referer"
    flag = "flag"
    language = "language"
    context = "context"
    pid = "pid"
    source_path = "source_path"
    imports = "imports"


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


class Executables(str, Enum):
    python = "python"
    python3 = "python3"
    node = "node"
    go = "go"
    ruby = "ruby"
    bash = "bash"
    sh = "sh"
    npm = "npm"
    rust = "rustc"
    cargo = "cargo"
    clang = "clang"
    gcc = "gcc"
    javac = "java"
    java = "javac"
    typescript = "tsc"

    def get(language: str, command: List[str]) -> List[str]:
        executable: Executables = Executables.__dict__.get(Enums.members).get(language)
        if executable:
            exec_dir = shutil.which(executable.value)
            if language == Language.python and not exec_dir:
                exec_dir: str = shutil.which(Executables.python3.value)
            return [exec_dir] + command

    def get_custom_exec(executable: str, command: List[str]) -> List[str]:
        exec_dir = shutil.which(executable)
        return [exec_dir] + command
