from dataclasses import dataclass, field
from sani.core.ops import RuntimeInfo, Os, TerminalCommand, os
from sani.utils.custom_types import Dict, Language, List, Mode
from dotenv import load_dotenv
import configparser

load_dotenv()


@dataclass
class Config:
    """Configuration for the application."""

    disable: bool = os.getenv("DEBUGGER_DEACTIVATE", False)
    deactivate = disable
    linter: str = os.getenv("DEBUGGER_LINTER", "pylint")  # pylint|flake8|disable
    linter_max_line_length: int = int(os.getenv("DEBUGGER_LINTER_MAX_LINE_LENGTH", 120))
    channel: str = os.getenv("DEBUGGER_CHANNEL", "io")  # io|rmq|redis
    log_level = os.getenv("DEBUGGY_LOG_LEVEL", "DEBUG")
    default_ostty_command: Dict[Os, TerminalCommand] = field(
        default_factory=lambda: {
            Os.linux: TerminalCommand.xterm,
            Os.ubuntu: TerminalCommand.gnome,
            Os.linux2: TerminalCommand.xterm,
            Os.mac: TerminalCommand.osascript,
            Os.windows32: TerminalCommand.cmd,
            Os.windows64: TerminalCommand.powershell,
        }
    )
    interactive_shell_file_format: Dict[str, str] = field(
        default_factory=lambda: {
            "<ipython-input-": "ipython",
            "<stdin>": "idle",
            "<bpython-input-": "bpython",
            "<reinteract-input-": "reinteract",
        }
    )
    raise2logs: bool = os.getenv("DEBUGGY_RAISE2LOGS", True)
    deactivate_exception_hooks: bool = os.getenv(
        "DEBUGGER_DEACTIVATE_EXCEPTION_HOOKS", False
    )

    SOURCE_LANGUAGE_MAP: Dict[str, Language] = field(
        default_factory=lambda: {
            ".py": Language.python,
            ".m4": Language.python,
            ".nsi": Language.python,
            # ".hpp": Language.cpp,
            ".c": Language.c,
            # ".h": Language.cpp,
            # ".cs": Language.csharp,
            # ".cpp": Language.cpp,
            # ".scss": Language.scss,
            # ".sep": Language.cpp,
            # ".hxx": Language.cpp,
            # ".cc": Language.cpp,
            # ".css": Language.css,
            # ".dart": Language.dart,
            ".go": Language.go,
            # ".hs": Language.haskell,
            ".html": Language.html,
            ".xml": Language.html,
            ".java": Language.java,
            ".js": Language.javascript,
            ".jsx": Language.javascript,
            # ".jl": Language.julia,
            # ".kt": Language.kotlin,
            # ".kts": Language.kotlin,
            # ".ktm": Language.kotlin,
            # ".m": Language.matlab,
            # ".php": Language.php,
            # ".pl": Language.perl,
            # ".r": Language.r,
            # ".R": Language.r,
            ".rb": Language.ruby,
            ".rs": Language.rust,
            ".sh": Language.shell,
            # ".sql": Language.sql,
            # ".swift": Language.swift,
            # ".scala": Language.scala,
            # ".sc": Language.scala,
            ".ts": Language.typescript,
            ".tsx": Language.typescript,
            # ".txt": Language.text,
            # ".lic": Language.text,
            # ".install": Language.text,
            # ".OSS": Language.text,
            # ".gl": Language.text,
        }
    )
    compiled_languages: List[Language] = field(
        default_factory=lambda: [Language.java, Language.c, Language.rust]
    )
    interpreted_languages: List[Language] = field(
        default_factory=lambda: [
            Language.go,
            Language.python,
            Language.javascript,
            Language.typescript,
        ]
    )
    instant_modes: List[Mode] = field(
        default_factory=lambda: [
            Mode.improve,
            Mode.document,
            Mode.analyze,
        ]
    )
    atexit_modes: List[Mode] = field(default_factory=lambda: [Mode.fix, Mode.test])
    prefix: str = "sani"
    delimiter: str = ":"
    seperator: str = "="
    end_syntax: str = "sani:end"
    runtime_recusive_limit: int = 5
