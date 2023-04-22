from typing import Union, Dict, List, Any, Tuple, NamedTuple, Type, Generator
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
        ("comments", str),
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
