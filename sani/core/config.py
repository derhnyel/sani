from dataclasses import dataclass, field
from sani.core.ops import RuntimeInfo, Os, TerminalCommand, os
from sani.utils.custom_types import Dict, Language, List, Mode
from dotenv import load_dotenv
import configparser
from sani.debugger.linter import Linter

load_dotenv()


@dataclass
class Config:
    """Configuration for the application."""

    disable: bool = os.getenv("SANI_DISABLE", False)
    deactivate = disable
    linter: str = os.getenv("SANI_LINTER", "pylint").lower()
    # linter_max_line_length: int = int(os.getenv("SANI_LINT_MAX_LENGHT", 120))
    channel: str = os.getenv("SANI_CHANNEL", "io").lower()
    log_level = os.getenv("SANI_LOGLEVEL", "DEBUG").upper()
    prefix: str = "sani"
    delimiter: str = ":"
    seperator: str = "="
    end_syntax: str = "sani:end"
    raise2logs: bool = os.getenv("SANI_RAISE2LOGS", True)
    runtime_recusive_limit: int = 5
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
    atexit_modes: List[Mode] = field(default_factory=lambda: [Mode.test])
    on_error_modes: List[Mode] = field(default_factory=lambda: [Mode.fix])
    redirect_on_error_mode: Dict[Mode, Mode] = field(
        default_factory=lambda: {
            Mode.fix: Mode.improve.value,
        }
    )
    redirect_atexit_mode: Dict[Mode, Mode] = field(
        default_factory=lambda: {
            Mode.test: Mode.fix.value,
        }
    )
    linter_language_map: Dict[Language, str] = field(
        default_factory=lambda: {
            Language.python: [Linter.pylint.name, Linter.flake8.name],
            Language.javascript: [Linter.pyjslint.name],
            Language.html: [Linter.htmllint.name],
        }
    )
    skip_errors: List[str] = field(
        default_factory=lambda: ["KeyboardInterrupt", "SystemExit", "GeneratorExit"]
    )
