from dataclasses import dataclass, field
import os
from sani.core.ops import RuntimeInfo, Os, TerminalCommand
from sani.utils.custom_types import Dict


@dataclass
class Config:
    """Configuration for the application."""

    debug: bool = False
    deactivate: bool = os.getenv("DEBUGGY_DEACTIVATE", False)
    runtime_info: RuntimeInfo = RuntimeInfo()
    linter: str = os.getenv("DEBUGGY_LINTER", "pylint")  # pylint|flake8|disable
    linter_max_line_length: int = int(os.getenv("DEBUGGY_LINTER_MAX_LINE_LENGTH", 120))
    channel: str = os.getenv("DEBUGGY_CHANNEL", "io")  # io|rmq|redis
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
        "DEBUGGY_DEACTIVATE_EXCEPTION_HOOKS", False
    )
