import re
import atexit
import asyncio
import threading
import traceback
import multiprocessing
from functools import wraps
from sani.utils.custom_types import (
    Dict,
    List,
    Any,
    Tuple,
    types,
    block_object,
    script,
    Code,
    Context,
    Enums,
)
from pathlib import Path
from sani.utils.utils import Object
from sani.core.config import Config, Mode, Language
from sani.utils.logger import get_logger
from sani.debugger.linter import Linter, BaseLinter
from sani.core.channel import Channel, BaseCommChannel
from sani.debugger.script import Script, BaseScript, ast
from sani.core.ops import OsProcess, RuntimeInfo, inspect, os, sys

config = Config()
logger = get_logger(__name__)


class Debugger(Object):
    """
    Debugger class to debug and capture errors within a script at runtime.
    * `start` and `stop` methods to spawn a new terminal session to monitor script i.e daemonic threads can also be used. (python module only)
    * `debug` method to debug a range of lines within the script at runtime. (for all languages)
    * `wrap` decorator method to debug a function within the script at runtime. (python module only)
    * Use a `with` statement to debug a block of code within the script at runtime. (python module only)
    """

    disable: bool = config.disable
    runtime_info: RuntimeInfo = RuntimeInfo()
    process_utils: OsProcess = OsProcess()
    watch_logs: Dict = dict()
    instant_modes: List[Mode] = config.instant_modes
    atexit_modes: List[Mode] = config.atexit_modes
    skip_errors: List[BaseException] = [KeyboardInterrupt, SystemExit, GeneratorExit]

    def __new__(
        cls,
        name: str = None,
        channel: str = Channel.io.name,
        linter: str = Linter.disable.name,
        caller: str = None,
        attach_hook: bool = True,
        language: str = Language.python.name,
        run_as_main: bool = True,
        *args,
        **kwargs,
    ):
        """
        Creates a singleton object for the Debugger class.
        Parameters
            name: str         -> Name of the module
            channel: str      -> Channel to use for communication
            linter: str       -> Linter to use for linting
            caller: str       -> Name of the caller module
            attach_hook: bool -> Attach hook to the script
            language: str     -> Language of the script
            run_as_main: bool -> Run as main script
            args             -> Positional arguments
            kwargs           -> Keyword arguments
        Returns
            Debugger instance
        Note:
                For flake8 linter: line lengths are recommended to be no greater than 79 characters. The reasoning for this comes from PEP8 itself:
                Limiting the required editor window width makes it possible to have several files open side-by-side, and works well when using code review tools that present the two versions in adjacent columns.
                You would have to sepcify a max_line_length as **kwargs if selecting the flake8 linter.
        Note:
                For io communication channel: The following kwargs are supported:
                    stderr (string): The path to the log file which stderr would be redirected to.
                    stdin (string): The path to the log file which stdin would be redirected to.
                    stdout (string): The path to the log file which stdout would be redirected to.
        """
        cls.run_as_main: bool = run_as_main
        cls.attach_hook: bool = attach_hook
        cls.language = language
        if not Linter.__dict__.get(Enums.members).get(linter):
            linter = Linter.disable.name
            logger.warning(
                f" {linter} Linter Not Supported by Debugger. Linter has been disabled."
            )
        elif not Channel.__dict__.get(Enums.members).get(channel):
            channel = Channel.io.name
            logger.warning(
                f"{channel} Channel Not Supported by Debugger. Default io selected."
            )
        elif not Language.__dict__.get(Enums.members).get(language):
            language = Language.python.name
            logger.warning(
                f"{language} Language Not Supported by Debugger. Default python selected."
            )
        if run_as_main:
            if not config.disable:
                if name != "__main__":
                    logger.error(
                        f"Debugger can only be used in __main__ module. Debugger has been deactivated in {name}"
                    )
                    cls.disable = True
                else:
                    cls.disable = False
        if not cls.disable:
            logger.debug("DEBUGGER='enabled'")
            logger.debug(
                f"Debugger is active in {name} module. Debugger is using {channel} channel and {linter} linter."
            )
            cls.script_utils: BaseScript = (
                Script.__dict__.get(Enums.members).get(language).value()
            )
            channel: Channel = Channel.__dict__.get(Enums.members).get(
                channel or config.channel
            )
            cls.channel: BaseCommChannel = channel.value(*args, **kwargs)
            linter: Linter = Linter.__dict__.get(Enums.members).get(
                linter or config.linter
            )
            cls.linter: BaseLinter = (
                linter.value(*args, **kwargs) if linter.value else None
            )

            if not caller and language == Language.python:
                cls.__caller_module = cls.runtime_info.get_module(
                    cls.runtime_info.get_stack()[-1][0]
                )
                cls.__caller_filename: str = (
                    cls.runtime_info.get_stack_caller_frame().filename
                )
                cls.__caller_filepath: str = os.path.dirname(
                    cls.__caller_module.__file__
                )
                cls.__caller: str = os.path.join(
                    cls.__caller_filepath, cls.__caller_filename
                )
            elif not caller:
                logger.error("Caller script is required for non-python languages.")
                cls.disable = True
                raise ValueError("Caller script is required for non-python languages.")
            else:
                cls.__caller: Path = caller
            if language == Language.python:
                cls.__caller_source: script = cls.script_utils.get_script(cls.__caller)
                cls.__script: script = cls.script_utils.get_attributes(
                    cls.__caller_source.string
                )
                cls.caller_comments = cls.__script.comments
            else:
                with open(cls.__caller, "r", encoding="utf-8") as code:
                    cls.__caller_source: script = cls.script_utils.get_attributes(code)
                cls.caller_comments = cls.__caller_source.comments
            cls.__caller_pid: int = cls.process_utils.get_pid_of_current_process()
            cls.__source_lines: List[str] = cls.__caller_source.lines.copy()

            cls.name = name or os.path.basename(cls.__caller)
            cls.lint_suggestions: str = str()

            if cls.linter:
                cls.lint_suggestions: str = cls.linter.get_report(cls.__caller)
            if cls.attach_hook:
                sys.excepthook = threading.excepthook = cls.handle_exception
                atexit.register(cls.exit_handler)
        else:
            logger.debug("DEBUGGER='disabled'")
        if not hasattr(cls, "instance"):
            cls.instance = super(Debugger, cls).__new__(
                cls,
                channel,
                linter,
                caller,
                attach_hook,
                language,
                name,
                run_as_main,
                *args,
                **kwargs,
            )
        return cls.instance

    def __init__(
        self,
        *args,
        **kwargs,
    ):
        """
        Initialize the Debugger class with the following parameters:
            Parameters:
                *args: Variable length argument list.
                **kwargs: Arbitrary keyword arguments.
        """
        self.args = args
        self.kwargs = kwargs
        self.assigned_var = None
        if self.language == Language.python and self.run_as_main:
            startline = self.runtime_info.get_stack_caller_frame().lineno
            line = self.__caller_source.lines[startline - 1].split("=")
            if len(line) > 1:
                self.assigned_var = f"{line[0].strip()}"

    def __check_status(function: types.FunctionType) -> Any:
        """
        Decorator to check if debugggy is disabled.
        """

        @wraps(function)
        def launch_status(self, *args, **kwargs):
            if not self.disable:
                return function(self, *args, **kwargs)
            return self

        return launch_status

    def wrap(
        self,
        mode: str = None,
        subject: str = None,
    ) -> Any:
        """
        Decorator to debug a function block within the script at runtime.

        Parameters:
            mode (str): The debugger mode to run the function. Default is `improve`.
            subject (str): The subject of the function to debug.
        Returns:
            A result object from executed function.
        """
        mode = mode or Mode.improve.value

        def wrap(
            function: types.FunctionType,
        ) -> Any:
            startline = self.runtime_info.get_stack_caller_frame().lineno
            # line = self.__caller_source.lines[startline-1]

            @wraps(function)
            def wrapper(*args, **kwargs) -> Any:
                check: bool = (
                    inspect.iscoroutinefunction(function)
                    or inspect.isawaitable(function)
                    or inspect.iscoroutine(function)
                )
                if self.disable:
                    exc_output = (
                        asyncio.run(function(*args, **kwargs))
                        if check
                        else function(*args, **kwargs)
                    )
                    return exc_output
                context, sync, block = self.build(
                    mode,
                    startline,
                    subject,
                    remove_pattern=f"{self.assigned_var}.",
                )
                logger.debug(
                    f"method='WRAP'::mode='{mode.upper()}'::startline={startline}::endline={block.endline}::sync={sync}::subject='{subject}'"
                )
                if mode in self.instant_modes and sync:
                    self.dispatch(mode, context, set_flag=True)
                exc_output = (
                    asyncio.run(function(*args, **kwargs))
                    if check
                    else function(*args, **kwargs)
                )
                if mode in self.atexit_modes and sync:
                    # after sending ... set the flag to True for non-atexit dispatches
                    if mode == Mode.fix:
                        context[Context.prompt.value][
                            Context.referer.value
                        ] = Mode.fix.value
                        context[Context.prompt.value][
                            Context.mode.value
                        ] = Mode.improve.value
                    context[Context.execution.value][Context.output.value] = str(
                        exc_output
                    )
                    context[Context.execution.value][
                        Context.status.value
                    ] = Code.success.value
                    self.dispatch(mode, context, set_flag=True)
                return exc_output

            return wrapper

        return wrap

    @__check_status
    def __enter__(self):
        """
        Entry function for the debugger context manager.
        Captures code block within with statement.
        Parameters:
            mode (str): The debugger mode to run the function. Defaults to `improve`.
            subject (str): The subject of the code block.
        """
        mode: str = self.get(Context.mode) or Mode.improve.value
        subject: str = self.get(Context.subject)
        startline: int = self.runtime_info.get_stack_caller_frame().lineno
        line = self.__caller_source.lines[startline - 1]
        context, sync, block = self.build(
            mode,
            startline,
            subject=subject,
            remove_pattern=f"{self.assigned_var}." or line,
        )
        if sync and mode in self.instant_modes:
            self.dispatch(mode, context, set_flag=True)
        logger.debug(
            f"method='WITH'::mode='{mode.upper()}'::startline={startline}::endline={block.endline}::sync={sync}::subject='{subject}'"
        )

    @__check_status
    def __exit__(self, exc_type, exc_value, traceback) -> None:
        """
        Exit function for the debugger context manager.
        The exception handler handles the exception raised within the code block while
        the atexit handler handles graceful exit of the code block.
        Parameters:
            exc_type (Exception): The exception type.
            exc_value (str): The exception value.
            traceback (traceback): The traceback object.
        """
        startline = self.runtime_info.get_stack_caller_frame().lineno
        logger.debug(
            f"'ENDWITH'::startline={startline}::exc_type={exc_type}::exc_value={exc_value}::traceback={traceback}"
        )
        if exc_type or exc_value or traceback:
            # On error let the exception handler handle dispatch
            return
        # On success dispatch fix/test modes
        tests = self.watch_logs.get(Mode.test, [])
        fixes = self.watch_logs.get(Mode.fix, [])

        def dispatch(attribute: dict):
            context = attribute.get(Context.context)
            context[Context.execution.value][Context.status.value] = Code.success.value
            mode = context.get(Context.prompt)[Context.mode]
            if mode == Mode.fix:
                context[Context.prompt.value][Context.referer.value] = Mode.fix.value
                context[Context.prompt.value][Context.mode.value] = Mode.improve.value
            self.dispatch(mode, context, set_flag=True)

        if tests:
            test = tests[-1]
            if startline == test[Context.startline]:
                dispatch(test)
        if fixes:
            fix = fixes[-1]
            if startline == fix[Context.startline]:
                dispatch(fix)

    @__check_status
    def __call__(self, *args, **kwargs):
        self.update(kwargs)
        return self

    @__check_status
    def debug(
        self,
        startline: int,
        endline: int,
        mode: str = None,
        subject: str = None,
        remove_pattern: str = None,
    ):
        """
        Debug a code block within a codebase.
        Parameters:
            startline (int): The line number where the code block starts.
            endline (int): The line number where the code block ends.
            mode (str): The debugger mode to run the function. Defaults to `improve`.
            subject (str): The subject of the code block.
        """
        mode = mode or Mode.improve.value
        if (
            startline > 0
            and endline > 0
            and startline <= endline
            and endline <= self.__caller_source.lenght
        ):
            # line = self.__caller_source.lines[startline-1]
            context, sync, block = self.build(
                mode,
                startline,
                subject,
                endline=endline,
                remove_pattern=remove_pattern or f"{self.assigned_var}.",
            )
            if sync and mode in self.instant_modes:
                self.dispatch(mode, context, set_flag=True)

            logger.debug(
                f"method='DEBUG'::mode='{mode.upper()}'::startline={startline}::endline={block.endline}::sync={sync}::subject='{subject}'"
            )

        else:
            logger.error(
                f"Debugger can only debug a source script between line 1 and {self.__caller_source.lenght}."
            )

    @classmethod
    @__check_status
    def handle_exception(cls, *args) -> None:
        """
        Handle exceptions raised by Threads and Process.
            Parameters:
                The args argument has the following attributes:
                    exc_type: Exception type.
                    exc_value: Exception value, can be None.
                    exc_traceback: Exception traceback, can be None.
                    thread: Thread which raised the exception, can be None.
        """
        lenght: int = len(args)
        thread: threading.Thread = None
        process = multiprocessing.current_process()
        # Handle exception raised by threads or processes based on the number of arguments
        if lenght == 1:
            exception_object: threading._ExceptHookArgs = args[0]
            exc_type, exc_value, exc_traceback, thread = (
                exception_object.exc_type,
                exception_object.exc_value,
                exception_object.exc_traceback,
                exception_object.thread,
            )
        elif lenght >= 3:
            exc_type, exc_value, exc_traceback = args
        if exc_type in cls.skip_errors:
            logger.debug(
                f"SKIP ERROR `not dispatched` to the cli-engine for traceback={exc_traceback}::error_type={exc_type}::error_message={exc_value}'"
            )
            logger.error(f"{exc_type.__name__}: {exc_value}")
            if cls.attach_hook:
                atexit.unregister(cls.exit_handler)
            return
        cls.dispatch_on_error(exc_type, exc_value, exc_traceback, thread, process)

    @__check_status
    def breakpoint(
        self,
        mode: str = None,
        subject: str = None,
        syntax_format: str = Code.end_breakpoint.value,
        startline: int = None,
        remove_pattern: str = None,
    ) -> None:
        """
        Start Debugger to monitor, redirect stderr to a log file and
        debug a script at runtime.
        Parameters:
            mode (str): Debugger mode. Default is `improve`.
            subject (str): A user defined  subject.
            syntax_format (str): The syntax format to use for the end breakpoint.
            startline (int): The line number where the code block starts.
        """
        mode = mode or Mode.improve.value
        startline = startline or self.runtime_info.get_stack_caller_frame().lineno
        # line = self.__caller_source.lines[startline-1]
        context, sync, block = self.build(
            mode,
            startline,
            subject=subject,
            style=Code.syntax,
            syntax_format=syntax_format,
            remove_pattern=remove_pattern or f"{self.assigned_var}.",
        )
        if sync and mode in self.instant_modes:
            self.dispatch(mode, context, set_flag=True)
        logger.debug(
            f"method='BREAKPOINT'::mode='{mode.upper()}'::startline={startline}::endline={block.endline}::sync={sync}::subject='{subject}'"
        )

    def __sync_modes(
        self,
        mode: str,
        context: Dict,
        startline: int,
        endline: int,
    ) -> Tuple[bool, Dict]:
        """
        Synchronize debugger modes created.
        Parameters:
            mode (str): Debugger mode.
            context (Dict): Debugger context.
            startline (int): Code block startline.
            endline (int): Code block endline.
        Returns:
            bool: True if the mode was synchronized, False otherwise.
        """
        logs = self.watch_logs.get(mode, [])
        last_item = logs[-1] if logs else None
        index = None

        def modify_log(startline: int, endline: int) -> Dict:
            """
            Modify a log.
            Parameters:
                log (Dict): Log to modify.
                index (int): Index of the log to modify.
            """
            log = logs.pop(-1)
            log[Context.endline.value] = endline
            logs.append(log)
            self.watch_logs[mode] = logs

            context[Context.source.value][Context.endline.value] = endline
            context[Context.source.value][Context.startline.value] = startline
            logger.debug(
                f"method='SYNC'::mode='{mode.upper()}'::startline={startline}::endline={endline}::sync={True}"
            )
            return context

        if last_item:
            last_startline = int(last_item[Context.startline])
            last_endline = int(last_item[Context.endline])
            # No point in having same code blocks with same mode overlapping each other
            logger.debug(
                f"'SYNCHRONIZATION-CALL' mode='{mode.upper()}'::current-startline={startline}::current-endline={endline}::previous-startline={last_startline}::previous-endline={last_endline}"
            )
            if (
                startline >= last_startline
                and startline < last_endline
                and endline >= last_endline
            ):
                # Swap last line of the previous mode with the current mode
                # Extend the code block instead of creating a new mode instance
                context = modify_log(last_startline, endline)
                return True, context
            elif startline >= last_endline and (
                endline > last_endline and endline >= startline
            ):
                # Only add mode if the code blocks are not overlapping
                pass
            elif (
                last_startline >= startline
                and last_startline > endline
                and last_startline < last_endline
            ):
                # Swap items in the watch logs (Sorting the watch logs)
                index = -2
            elif (
                last_startline <= endline
                and endline > startline
                and last_endline > last_startline
            ):
                # Get the startline and the last endline
                # Modify the watch log and context logs to reflect that
                context = modify_log(startline, last_endline)
                return True, context
            else:
                return False, context
        else:
            f"'SYNCHRONIZATION-CALL' mode='{mode.upper()}'::current-startline={startline}::current-endline{endline} no logs found"
        return self.__watch(mode, context, startline, endline, index), context

    def __watch(
        self,
        mode: str,
        context: Dict,
        startline: int,
        endline: int,
        index: int = None,
    ) -> bool:
        """
        Update the watch logs, which keep track of all debugger mode calls and thier attributes.
        Parameters:
            mode (str): Debugger mode. Default is `improve`.
            context (Dict): Context for the cli-engine.
            startline (int): Start line of the code block.
            endline (int): End line of the code block.
            index (int): Index of the watch log to update.
        Note:
            This works for modes that require the code to end before results can be generated.
        """
        current_thread: threading.Thread = threading.current_thread()
        current_process: multiprocessing.Process = multiprocessing.current_process()
        watch_log = {
            Context.context.value: context,  # Context for the cli-engine
            current_thread.name: current_thread,  # Current thread
            current_process.name: current_process,  # Current process
            Context.startline.value: startline,  # Start line of the code block
            Context.endline.value: endline,  # End line of the code block
            Context.flag.value: False,  # Flag to indicate if the mode was dispatched
        }
        logs = self.watch_logs.get(mode, [])
        if index:
            logs.insert(
                index,
                watch_log,
            )
        else:
            logs.append(watch_log)
        self.watch_logs[mode] = logs
        return True

    @classmethod
    @__check_status
    def dispatch(
        cls,
        mode: str,
        context: Dict,
        set_flag: bool = False,
        dispatch_by_last_index: bool = True,
    ):
        """
        Dispatch context to the cli-engine.
        Parameters:
            mode (str): Debugger mode. Default is `improve`.
            context (Dict): Context for the cli-engine.
            set_flag (bool): Set the flag  indicate the mode was dispatched
            dispatch_by_last_index (bool): Dispatch the context of the last index item in the watch logs
        """
        if (
            (
                mode in [Mode.test]
                and context.get(Context.execution)[Context.status] == Code.success
            )
            or (mode in cls.instant_modes)
            or (
                mode in [Mode.fix]
                and context.get(Context.prompt)[Context.referer] == Mode.fix
                and context.get(Context.execution)[Context.status] == Code.success
            )
        ):
            if dispatch_by_last_index:
                # Check flag of watch log before sending dispatch
                mode_objects: list = cls.watch_logs.get(mode)
                if mode_objects:
                    mode_object = mode_objects.pop(-1)
                    if not mode_object[Context.flag]:
                        cls.channel.send(context)
                        # Update flag to True to indicate the mode was dispatched
                        if set_flag:
                            mode_object[Context.flag] = set_flag
                    mode_objects.append(mode_object)
                    cls.watch_logs[mode] = mode_objects
            else:
                cls.channel.send(context)
            logger.debug(
                f"DISPATCHED `successfully` to the cli-engine for mode='{context.get('prompt')['mode'].upper()}'::startline={context.get('source')['startline']}::endline={context.get('source')['endline']}::referer='{context.get(Context.prompt)[Context.referer]}'"
            )

    @classmethod
    @__check_status
    def dispatch_on_error(
        cls,
        exc_type: str = None,
        exc_value: str = None,
        traceback_n: str = None,
        thread: threading.Thread = None,
        process: multiprocessing.Process = None,
    ) -> None:
        """
        Dispatch context to the cli-engine when the program exits with an error.
        Works for both `threads` and `processes` in `test` and `fix` modes.
        Parameters:
            exc_type (Exception): Type of the error.
            exc_value (Exception): Value of the error.
            traceback_n (Traceback object): Traceback of the error.
            thread (threading.Thread): Thread that caused the error.
            process (multiprocessing.Process): Process that caused the error.
        """
        line_number = cls.__caller_source.lenght
        if cls.attach_hook:
            atexit.unregister(cls.exit_handler)
        if (
            isinstance(traceback_n, types.TracebackType)
            and cls.language == Language.python
        ):
            traceback_nodes: List[str] = traceback.format_tb(traceback_n)
            traceback_node = traceback_nodes[-1]
            line_number: int = int(
                re.search(r"""line (\d+)""", traceback_node).group(1)
            )
            traceback_n = ("").join(traceback_nodes)
        fixes: List[Dict[str, str]] = cls.watch_logs.get(Mode.fix, [])
        tests: List[Dict[str, str]] = cls.watch_logs.get(Mode.test, [])
        process = process or multiprocessing.current_process()
        attribute = thread if thread and process else process
        logger.error(traceback_n)
        fixed = False  # Ensure a fix was defined for that block
        # Dispatch all fix mode code blocks on error
        for fix in fixes:
            if (
                fix.get(attribute.name) == attribute
                and line_number >= fix.get(Context.startline)
                and (
                    line_number <= fix.get(Context.endline)
                    or cls.language != Language.python
                )
                and not fix.get(Context.flag)
            ):
                context: Dict = fix.get(Context.context)
                context[Context.execution.value][Context.traceback.value] = {
                    Context.exception_type.value: str(exc_type),
                    Context.exception_message.value: str(exc_value),
                    Context.full_traceback.value: traceback_n,
                    Context.error_line.value: None,
                }
                context[Context.execution.value][
                    Context.status.value
                ] = Code.failed.value
                # Check the flag that indicates the mode has been dispatched
                cls.channel.send(context)
                logger.debug(
                    f"DISPATCHED `on error` to the cli-engine for mode='{Mode.fix.upper()}'::startline={fix.get('startline')}::endline={fix.get('endline')}::error_line=None::error_type={exc_type}::error_message={exc_value}"
                )
                fixed = True
                break
        # convert all test to fixes.. but ensure there are in sync with fix mode
        if not fixed:
            for test in tests:
                if (
                    test.get(attribute.name) == attribute
                    and not test.get(Context.flag)
                    and line_number >= test.get(Context.startline)
                    and (
                        line_number <= test.get(Context.endline)
                        or cls.language != Language.python
                    )
                ):
                    context: Dict = test.get(Context.context)
                    context[Context.execution.value][Context.traceback.value] = {
                        Context.exception_type.value: str(exc_type),
                        Context.exception_message.value: str(exc_value),
                        Context.full_traceback.value: traceback_n,
                        Context.error_line.value: None,
                    }
                    context[Context.execution.value][
                        Context.status.value
                    ] = Code.failed.value
                    context[Context.prompt.value][Context.mode.value] = Mode.fix
                    context[Context.prompt.value][Context.referer.value] = Mode.test
                    # Check the flag that indicates the mode has been dispatched
                    cls.channel.send(context)
                    logger.debug(
                        f"DISPATCHED `on error` to the cli-engine for mode='{Mode.fix.upper()}'::referer='{Mode.test.upper()}::startline={test.get('startline')}::endline={test.get('endline')}::error_line=None::error_type={exc_type}::error_message={exc_value}'"
                    )
                    fixed = True
                    break

    @__check_status
    def build(
        self,
        mode: str,
        startline: int,
        subject=None,
        endline: int = None,
        style: str = Code.indent,
        body_index: int = 0,
        syntax_format: str = None,
        replace_syntax: bool = True,
        remove_pattern: str = None,
    ) -> Tuple[Dict, bool, block_object]:
        """
        Build the context and code block for a specific mode.
        Parameters:
            mode (str): Debugger mode. Default is `improve`.
            startline (int): Start line of the code block.
            subject (str): Subject of the code block.
            endline (int): End line of the code block.
            style (str): Style of the code block. Default is `indent`.
            body_index (int): Index of the body of the code block. Default is `0`.
            syntax_format (str): Syntax format of the code block. Default is `None`.
            replace_syntax (bool): Replace syntax of the code block. Default is `True`.
            remove_pattern (str): Remove pattern of the code block. Default is `None`.
        Returns:
            context (Dict): Context for the cli-engine.
            sync (bool): Sync status of the code block.
            block (NamedTuple): Code block.
        """
        # build code block tuple
        block: block_object = self.__build_block(
            startline,
            endline,
            style,
            body_index,
            syntax_format,
            replace_syntax,
            remove_pattern,
        )
        if not block.block:
            return {}, False, block

        # build context with code block
        context = self.__build_context(
            mode=mode,
            startline=startline,
            endline=block.endline,
            subject=subject,
            block=block.block,
            block_ast_dump=block.block_ast_dump,
            block_comments=block.block_comments,
        )
        sync, context = self.__sync_modes(
            mode, context, block.startline, block.endline
        )  # synchronize all code blocks in a particular mode
        return context, sync, block

    def __build_block(
        self,
        startline: int,
        endline: int = None,
        style: str = Code.indent,
        body_index: int = 0,
        syntax_format: str = None,
        replace_syntax: bool = True,
        remove_pattern: str = None,
    ) -> block_object:
        """
        Build the code block from the source file.
        Parameters:
            startline (int): Start line of the code block.
            endline (int): End line of the code block.
            style (str): Style to extract the code block with. Default is `indent`. | `syntax`
            body_index (int): Index of the body of the code block. Default is `0`.
            syntax_format (str): Syntax format of the code block. Default is `None`.
            replace_syntax (bool): Replace syntax of the code block. Default is `True`.
            remove_pattern (str): Remove pattern of the code block. Default is `None`.
        Returns:
            block (NamedTuple): Code block.
        """

        def omit(iter_list: List[str], pattern: str = None) -> str:
            logger.debug(f"OMITTING: {pattern}")
            result = ""
            if remove_pattern:
                for line in iter_list:
                    if (
                        pattern.strip().lower() in line.strip().lower()
                        or pattern.strip().lower().replace(".", "(")
                        in line.strip().lower()
                    ):
                        logger.debug(f"OMITTED: {line.strip()}")
                        continue
                    result += line
            else:
                result = ("").join(iter_list)
            return result

        print(
            f"startline: {startline}, endline: {endline}, style: {style}, body_index: {body_index}, syntax_format: {syntax_format}, replace_syntax: {replace_syntax}, remove_pattern: {remove_pattern}"
        )
        try:
            if not endline:
                endline = self.__caller_source.lenght
                if style == Code.indent:
                    first_line = self.__caller_source.lines[startline - 1]
                    strips = len(first_line) - len(first_line.lstrip())
                    # Get the endline of a code block using the indent style
                    for line in range(startline + 1, endline):
                        if (
                            len(self.__caller_source.lines[line])
                            - len(self.__caller_source.lines[line].lstrip())
                            == strips
                        ):
                            endline = line
                            break
                    block_ast: ast.AST = (
                        (
                            self.script_utils.get_ast(self.__caller_source.string).body[
                                body_index
                            ]
                            if body_index
                            else self.script_utils.get_ast(self.__caller_source.string)
                        )
                        if self.language == Language.python
                        else None
                    )
                    block = omit(
                        self.__caller_source.lines[startline - 1 : endline - 1],
                        remove_pattern,
                    )
                elif style == Code.syntax:
                    for line in range(startline, endline):
                        if syntax_format.lower() in self.__source_lines[line].lower():
                            # Maintain end syntax.
                            if replace_syntax:
                                # Remove so another break point method would find its end syntax
                                self.__source_lines.pop(line)
                                self.__source_lines.insert(
                                    line,
                                    f"Debugger inserted placeholder in line {line+1}",
                                )
                            endline = line + 1
                            break
                    block = omit(
                        self.__caller_source.lines[startline - 1 : endline - 1],
                        remove_pattern,
                    )
                    block_ast: ast.AST = (
                        self.script_utils.get_ast(block)
                        if self.language == Language.python
                        else None
                    )
                block_ast_dump: str = ast.dump(block_ast) if block_ast else None
                block_comments: str = (
                    self.script_utils.get_comments(block_ast) if block_ast else None
                )
            else:
                block = omit(
                    self.__caller_source.lines[startline - 1 : endline - 1],
                    remove_pattern,
                )

                block_ast = (
                    self.script_utils.get_ast(block)
                    if self.language == Language.python
                    else None
                )
                block_ast_dump = ast.dump(block_ast) if block_ast else None
                block_comments = (
                    self.script_utils.get_comments(block_ast) if block_ast else None
                )
            return block_object(
                block, startline, endline, block_ast_dump, block_comments
            )
        except IndentationError as e:
            logger.error(
                f"Block startline={startline} to endline={endline} has the incorrect language syntax within it. Please select a valid language syntax block. "
            )
            return block_object(None, startline, endline, None, None)

    def __build_context(
        self,
        mode: str = None,
        startline: int = None,
        endline: int = None,
        block: str = None,
        block_ast_dump: str = None,
        block_comments: str = None,
        subject: str = None,
        output: str = None,
        error_line: int = None,
        exception_type: BaseException = None,
        exception_message: str = None,
        full_traceback: str = None,
        status: str = Code.inprogress.value,
        referer: str = None,
    ) -> Dict:
        """
        Build context for the cli-engine.
        Parameters:
            mode (Mode): Debugger mode.
            startline (int): Start line of the code block.
            endline (int): End line of the code block.
            block (str): Code block.
            block_ast_dump (ast.AST): AST of the code block.
            block_comments (List[str]): Comments in the code block.
            subject (str): Subject of the code block.
            output (str): Output of the code block.
            error_line (int): Line number of the error.
            exception_type (Exception): Type of the error.
            exception_message (Exception): Value of the error.
            full_traceback (Traceback object): Traceback of the error.
        Returns:
            context (Dict[str : Dict[str, str]]): Context for the cli-engine.
        """
        context: Dict = {
            Context.execution.value: {
                Context.output.value: output,
                Context.traceback.value: {
                    Context.exception_type.value: exception_type,
                    Context.exception_message.value: exception_message,
                    Context.full_traceback: full_traceback,
                    Context.error_line: error_line,
                    Context.pid.value: self.__caller_pid,
                },
                Context.status.value: status,
            },
            Context.source.value: {
                Context.startline.value: str(startline),
                Context.endline.value: str(endline),
                Context.code.value: self.__caller_source.string,
                Context.block.value: block,
                Context.imports.value: self.__caller_source.imports,
                Context.lined_code.value: self.__caller_source.lined_string,
                Context.code_ast_dump.value: self.__caller_source.ast_dump,
                Context.linenos.value: str(self.__caller_source.lenght),
                Context.block_ast.value: block_ast_dump,
                Context.language.value: self.language,
            },
            Context.prompt.value: {
                Context.suggestions.value: {
                    Context.linter.value: {
                        Context.suggestions.value: self.lint_suggestions,
                        Context.lint_format: Linter.pylint.name,
                    },
                    Context.block_comments.value: block_comments,
                    Context.subject.value: subject,
                    Context.comments.value: self.caller_comments,
                },
                Context.mode.value: mode,
                Context.referer.value: referer,
            },
        }
        # logger.debug(f"'CONTEXT'::context_dict={context}")
        return context

    @__check_status
    def debugger_end_breakpoint(self):
        if self.language == Language.python:
            endline = self.runtime_info.get_stack_caller_frame().lineno
            logger.debug(f"'ENDBREAKPOINT'::endline={endline}")

    @classmethod
    @__check_status
    def exit_handler(cls, output: str = None):
        """
        Exit handler to be called on exit of the program.
        Parameters:
            output (str): Output of the executed code.
        """
        # Dispatch all test mode code blocks at exit
        tests: List[Dict] = cls.watch_logs.get(Mode.test, [])
        fixes: List[Dict] = cls.watch_logs.get(Mode.fix, [])
        for test in tests:
            if not test[Context.flag]:
                context = test.get(Context.context)
                context[Context.execution.value][
                    Context.status.value
                ] = Code.success.value
                if output:
                    context[Context.execution.value][Context.output.value] = output
                cls.dispatch(
                    Mode.test,
                    context,
                    dispatch_by_last_index=False,
                )
        # Redirect all fix modes to improve ... if the fix code block isnt within a previous improve code block
        improvements: List[Dict] = cls.watch_logs.get(Mode.improve, [])
        for fix in fixes:
            if not fix[Context.flag]:
                startline = fix.get(Context.startline)
                endline = fix.get(Context.endline)
                if any(
                    [
                        improve
                        for improve in improvements
                        if startline >= improve.get(Context.startline)
                        and endline <= improve.get(Context.endline)
                    ]
                ):
                    continue
                context = fix.get(Context.context)
                context[Context.execution.value][
                    Context.status.value
                ] = Code.success.value
                context[Context.prompt.value][Context.referer.value] = Mode.fix.value
                context[Context.prompt.value][Context.mode.value] = Mode.improve.value
                if output:
                    context[Context.execution.value][Context.output.value] = output
                cls.dispatch(
                    Mode.fix,
                    context,
                    dispatch_by_last_index=False,
                )
