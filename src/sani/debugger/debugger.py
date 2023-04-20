from functools import wraps
import asyncio
import threading
import multiprocessing
from sani.utils.custom_types import Dict, List, Any, Tuple, NamedTuple, types
from sani.core.channel import Channel, BaseCommChannel
import sys
from sani.debugger.linter import Linter, BaseLinter
from sani.core.ops import (
    OsProcess,
    RuntimeInfo,
    Os,
    TerminalCommand,
    inspect,
    os,
)
import json
import traceback
import re
from sani.debugger.script import Scripts, ast
from sani.utils.utils import Object
from sani.core.config import Config
import atexit

from enum import Enum

# import signal  # https://docs.python.org/3/library/signal.html Handle debugger raises and keyboard interrupt errors
from sani.utils.logger import get_logger


class Mode(str, Enum):
    """
    Enum for execution mode
    """

    fix = "fix"
    document = "document"
    test = "test"
    improve = "improve"
    ai_function = "ai_fn"
    analyze = "analyze"
    regex = "regex"


config = Config()
logger = get_logger(__name__)
# RAISE2LOGS = config.raise2logs
# DEACTIVATE = config.deactivate
multiprocessing


class Debugger(Object):
    """
    Debugger class to debug and capture errors within a python script at runtime.
    * `start` and `stop` methods to spawn a new terminal session to monitor script i.e daemonic threads can also be used.
    * `debug` method to debug a range of lines within the python script at runtime.
    * `wrap` decorator method to debug a function within the python script at runtime.
    * Use a `with` statement to debug a block of code within the python script at runtime.
    """

    __default_ostty_command: Dict[Os, TerminalCommand] = config.default_ostty_command
    __interactive_shell_file_format: Dict[
        str, str
    ] = config.interactive_shell_file_format
    __deactivate_hook: bool = config.deactivate_exception_hooks
    deactivate: bool = config.deactivate

    runtime_info: RuntimeInfo = config.runtime_info
    script_utils: Scripts = Scripts
    process_utils: OsProcess = OsProcess()
    watch_logs: Dict = dict()
    channel: BaseCommChannel = None
    quick_dispatcher_modes: List[Mode] = [
        Mode.improve,
        Mode.document,
        Mode.ai_function,
        Mode.analyze,
    ]
    lifecycle_dispatcher_modes: List[Mode] = [Mode.fix, Mode.test]
    # main_thread: threading.Thread = threading.main_thread()
    # main_process: multiprocessing.Process = multiprocessing.current_process()

    def __new__(
        cls,
        __name__,
        terminal_type: str = None,
        channel: str = None,
        linter: str = None,
        *args,
        **kwargs,
    ):
        """
        Creates a singleton object, if it is not created,
        or else returns the previous singleton object
        """
        if __name__ != "__main__" and not config.deactivate:
            cls.deactivate = True
        elif __name__ == "__main__" and not config.deactivate:
            cls.deactivate = False
        if not hasattr(cls, "instance"):
            cls.instance = super(Debugger, cls).__new__(
                cls,
                __name__,
                terminal_type=terminal_type,
                channel=channel,
                linter=linter,
                *args,
                **kwargs,
            )
        return cls.instance

    def __init__(
        self,
        __name__,
        terminal_type: str = None,
        channel: str = None,
        linter: str = None,
        *args,
        **kwargs,
    ):
        """
        Initialize the Debugger class with the following parameters:
            Parameters:
                terminal_type (string): The terminal type to spawn a new terminal session.
                channel (string): The channel to use for communication between the debugger and cli-engine ie. io|socket
                linter (string): The linter to use for linting the python script. ie. pylint|flake8|disable
                *args: Variable length argument list.
                **kwargs: Arbitrary keyword arguments.
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

        if self.deactivate:
            logger.debug("DEBUGGER='deactivated'")
            return
        self.__terminal_type = terminal_type
        self.args = args
        self.kwargs = kwargs
        linter_: Linter = Linter.__dict__.get("_member_map_").get(
            linter or config.linter
        )
        channel: Channel = Channel.__dict__.get("_member_map_").get(
            channel or config.channel
        )
        self.__caller_module = self.runtime_info.get_module(
            self.runtime_info.get_stack()[-1][0]
        )
        self.__caller_filename: str = (
            self.runtime_info.get_stack_caller_frame().filename
        )
        if self.__check_run():
            self.deactivate = True
            logger.error("DEBBUGY is not supported in this runtime environment.")
            return
        # self.__calling_module: Tuple[
        #     str, types.ModuleType
        # ] = self.runtime_info.get_module_members(self.__caller_module)[-1]
        self.__caller_pid: int = self.process_utils.get_pid_of_current_process()
        self.__caller_filepath: str = os.path.dirname(self.__caller_module.__file__)
        self.__caller: str = os.path.join(
            self.__caller_filepath, self.__caller_filename
        )
        self.__caller_source: NamedTuple = self.script_utils.get_script(self.__caller)
        # startline = self.runtime_info.get_stack_caller_frame().lineno
        # init_line = self.__caller_source.lines[startline - 1].split('=')
        self.__source_lines: List[str] = self.__caller_source.lines.copy()
        Debugger.channel: BaseCommChannel = channel.value(*args, **kwargs)
        self.linter: BaseLinter = linter_.value(*args, **kwargs)
        self.lint_suggestions: str = self.linter.get_report(self.__caller)
        # faulthandler.enable(file=sys.stderr, all_threads=True)
        # Enable the fault handler: install handlers for the SIGSEGV, SIGFPE, SIGABRT, SIGBUS and SIGILL signals to dump the Python traceback. If all_threads is True, produce tracebacks for every running thread. Otherwise, dump only the current thread.
        # self.__engine: NamedTuple = self.__exec_engine()
        # print(self.__engine)
        if not self.__deactivate_hook:
            sys.excepthook = threading.excepthook = Debugger.handle_exception
            atexit.register(Debugger.exit_handler)

        # TODO: launch the terminal on init and connect to its stderr and stdin pipes .. so commands can be sent to it from anywhere
        # QUESTION: how to get the terminal pid and kill it when the script ends?
        # QUESTION: how does the script processes communicate with the terminal process?

        logger.debug("DEBUGGER='activated'")

    def regex(self, description: str, sample_text: str):
        """
        Returns a compiled regular expression object.
        """
        # Move out of this class and into a separate class
        # Return the ai results of matches if found else return None

    def __check_run(self) -> bool:
        """
        Check caller script runtime details and raise errors if not supported
        """
        deactivate = False
        if not self.__caller_module:
            raise Exception("Unable to locate caller module.")
        # if (
        #     self.__caller_module.__name__ != "__main__"
        # ) or "__main__" not in sys.modules:
        #     deactivate = True
        #     # raise DebuggerImportError("Debugger must be imported in the main script.")
        if (
            self.__terminal_type
            and self.__terminal_type not in TerminalCommand.__dict__.get("_member_map_")
        ):
            raise Exception(
                f"{self.__terminal_type} Terminal Not Supported by Debugger."
            )
        if self.runtime_info.os not in Os.__dict__.get("_value2member_map_"):
            raise Exception(
                f"{self.runtime_info.os} Operating System Not Supported by Debugger."
            )
        for tty_format in self.__interactive_shell_file_format:
            if (
                tty_format in self.__caller_filename
                or os.path.basename(self.__caller_filename).lower()
                == self.__interactive_shell_file_format[tty_format].lower()
            ):
                raise Exception(
                    "Debugger does not support interactive terminal like ipython, idle, bpython, reinteract."
                )
        return deactivate

    def __check_status(function: types.FunctionType) -> Any:
        """
        Decorator to check if debugggy is deactivated.
        """
        if inspect.ismethod(function):

            @wraps(function)
            def launch_status(self, *args, **kwargs):
                if not self.deactivate:
                    return function(self, *args, **kwargs)
                return self

        else:

            @wraps(function)
            def launch_status(*args, **kwargs):
                if not Debugger.deactivate:
                    return function(*args, **kwargs)
                return

        return launch_status

    def wrap(self, mode: str = None, subject: str = None) -> Any:
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

            @wraps(function)
            def wrapper(*args, **kwargs) -> Any:
                check: bool = (
                    inspect.iscoroutinefunction(function)
                    or inspect.isawaitable(function)
                    or inspect.iscoroutine(function)
                )
                if self.deactivate:
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
                )
                logger.debug(
                    f"method='WRAP'::mode='{mode.upper()}'::startline={startline}::endline={block.endline}::sync={sync}::subject='{subject}'"
                )
                if mode in self.quick_dispatcher_modes and sync:
                    Debugger.dispatch(mode, context, set_flag=True)
                exc_output = (
                    asyncio.run(function(*args, **kwargs))
                    if check
                    else function(*args, **kwargs)
                )
                if mode in self.lifecycle_dispatcher_modes and sync:
                    # after sending ... set the flag to True for non-atexit dispatches
                    if mode == Mode.fix:
                        context["prompt"]["referer"] = Mode.fix.value
                        context["prompt"]["mode"] = Mode.improve.value
                    context["execution"]["output"] = str(exc_output)
                    context["execution"]["status"] = "success"
                    Debugger.dispatch(mode, context, set_flag=True)
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
        mode: str = self.get("mode") or Mode.improve.value
        subject: str = self.get("subject")
        startline: int = self.runtime_info.get_stack_caller_frame().lineno
        context, sync, block = self.build(
            mode,
            startline,
            subject=subject,
        )
        if sync and mode in self.quick_dispatcher_modes:
            Debugger.dispatch(mode, context, set_flag=True)
        logger.debug(
            f"method='WITH'::mode='{mode.upper()}'::startline={startline}::endline={block.endline}::sync={sync}::subject='{subject}'"
        )

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
        tests = Debugger.watch_logs.get(Mode.test, [])
        fixes = Debugger.watch_logs.get(Mode.fix, [])

        def dispatch(attribute: dict):
            context = attribute.get("context")
            context["execution"]["status"] = "success"
            mode = context.get("prompt")["mode"]
            if mode == Mode.fix:
                context["prompt"]["referer"] = Mode.fix.value
                context["prompt"]["mode"] = Mode.improve.value
            Debugger.dispatch(mode, context, set_flag=True)

        if tests:
            test = tests[-1]
            if startline == test["startline"]:
                dispatch(test)
        if fixes:
            fix = fixes[-1]
            if startline == fix["startline"]:
                dispatch(fix)

    @__check_status
    def __call__(self, *args, **kwargs):
        self.update(kwargs)
        return self

    @__check_status
    def debug(
        self, startline: int, endline: int, mode: str = None, subject: str = None
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
            context, sync, block = self.build(mode, startline, subject, endline=endline)
            if sync and mode in self.quick_dispatcher_modes:
                Debugger.dispatch(mode, context, set_flag=True)

            logger.debug(
                f"method='DEBUG'::mode='{mode.upper()}'::startline={startline}::endline={block.endline}::sync={sync}::subject='{subject}'"
            )

        else:
            raise ValueError(
                f"Debugger can only debug a source script between line 1 and {self.__caller_source.lenght}."
            )

    @staticmethod
    @__check_status
    def handle_exception(*args) -> None:
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
        Debugger.dispatch_on_error(exc_type, exc_value, exc_traceback, thread, process)

    @__check_status
    def breakpoint(self, mode: str = None, subject: str = None) -> None:
        """
        Start Debugger to monitor, redirect stderr to a log file and
        debug a python script at runtime.
        Parameters:
            mode (str): Debugger mode. Default is `improve`.
            subject (str): A user defined  subject.
        """
        mode = mode or Mode.improve.value
        startline = self.runtime_info.get_stack_caller_frame().lineno
        context, sync, block = self.build(
            mode,
            startline,
            subject=subject,
            style="syntax",
            syntax_format="debugger_end_breakpoint",
        )
        if sync and mode in self.quick_dispatcher_modes:
            Debugger.dispatch(mode, context, set_flag=True)
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
            log["endline"] = endline
            logs.append(log)
            self.watch_logs[mode] = logs

            context["source"]["endline"] = endline
            context["source"]["startline"] = startline
            logger.debug(
                f"method='SYNC'::mode='{mode.upper()}'::startline={startline}::endline={endline}::sync={True}"
            )
            return context

        if last_item:
            last_startline = int(last_item["startline"])
            last_endline = int(last_item["endline"])
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
            "context": context,  # Context for the cli-engine
            current_thread.name: current_thread,  # Current thread
            current_process.name: current_process,  # Current process
            "startline": startline,  # Start line of the code block
            "endline": endline,  # End line of the code block
            "flag": False,  # Flag to indicate if the mode was dispatched
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

    @staticmethod
    @__check_status
    def dispatch(
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
            (mode in [Mode.test] and context.get("execution")["status"] == "success")
            or (mode in Debugger.quick_dispatcher_modes)
            or (
                mode in [Mode.fix]
                and context.get("prompt")["referer"] == Mode.fix
                and context.get("execution")["status"] == "success"
            )
        ):
            message = json.dumps(context)
            if dispatch_by_last_index:
                # Check flag of watch log before sending dispatch
                mode_objects: list = Debugger.watch_logs.get(mode)
                if mode_objects:
                    mode_object = mode_objects.pop(-1)
                    if not mode_object["flag"]:
                        Debugger.channel.send(message)
                        # Update flag to True to indicate the mode was dispatched
                        if set_flag:
                            mode_object["flag"] = set_flag
                    mode_objects.append(mode_object)
                    Debugger.watch_logs[mode] = mode_objects
            else:
                Debugger.channel.send(message)
            referer = context.get("prompt")["referer"]
            logger.debug(
                f"DISPATCHED `successfully` to the cli-engine for mode='{context.get('prompt')['mode'].upper()}'::startline={context.get('source')['startline']}::endline={context.get('source')['endline']}::referer='{referer}'"
            )

    @staticmethod
    @__check_status
    def dispatch_on_error(
        exc_type,
        exc_value,
        traceback_n,
        thread: threading.Thread = None,
        process: multiprocessing.Process = None,
    ) -> None:  # TODO: Define types for traceback objects
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
        atexit.unregister(Debugger.exit_handler)
        traceback_nodes: List[str] = traceback.format_tb(traceback_n)
        traceback_node = traceback_nodes[-1]
        fixes: List[Dict[str, str]] = Debugger.watch_logs.get(Mode.fix, [])
        tests: List[Dict[str, str]] = Debugger.watch_logs.get(Mode.test, [])
        process = process or multiprocessing.current_process()
        line_number: int = int(re.search(r"""line (\d+)""", traceback_node).group(1))

        attribute = thread if thread and process else process
        trace_str = ("").join(traceback_nodes)
        logger.error(trace_str)
        fixed = False  # Ensure a fix was defined for that block
        # Dispatch all fix mode code blocks on error
        for fix in fixes:
            if (
                fix.get(attribute.name) == attribute
                and line_number >= fix.get("startline")
                and line_number <= fix.get("endline")
                and not fix.get("flag")
            ):
                context: Dict = fix.get("context")
                context["execution"]["traceback"] = {
                    "exeception_type": str(exc_type),
                    "exception_message": str(exc_value),
                    "full_traceback": trace_str,
                    "error_line": str(line_number),
                }
                context["execution"]["status"] = "failed"
                # Check the flag that indicates the mode has been dispatched
                message = json.dumps(context)
                Debugger.channel.send(message)
                logger.debug(
                    f"DISPATCHED `on error` to the cli-engine for mode='{Mode.fix.upper()}'::startline={fix.get('startline')}::endline={fix.get('endline')}::error_line={line_number}::error_type={exc_type}::error_message={exc_value}"
                )
                fixed = True
                break
        # convert all test to fixes.. but ensure there are in sync with fix mode
        if not fixed:
            for test in tests:
                if (
                    test.get(attribute.name) == attribute
                    and line_number >= test.get("startline")
                    and line_number <= test.get("endline")
                    and not test.get("flag")
                ):
                    context: Dict = test.get("context")
                    context["execution"]["traceback"] = {
                        "exeception_type": str(exc_type),
                        "exception_message": str(exc_value),
                        "full_traceback": trace_str,
                        "error_line": str(line_number),
                    }
                    context["execution"]["status"] = "failed"
                    context["prompt"]["mode"] = Mode.fix
                    context["prompt"]["referer"] = Mode.test
                    # Check the flag that indicates the mode has been dispatched
                    message = json.dumps(context)
                    Debugger.channel.send(message)
                    logger.debug(
                        f"DISPATCHED `on error` to the cli-engine for mode='{Mode.fix.upper()}'::referer='{Mode.test.upper()}::startline={test.get('startline')}::endline={test.get('endline')}::error_line={line_number}::error_type={exc_type}::error_message={exc_value}'"
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
        style: str = "indent",
        body_index: int = 0,
        syntax_format: str = None,
        replace_syntax: bool = True,
    ) -> Tuple[Dict, bool, NamedTuple]:
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
        Returns:
            context (Dict): Context for the cli-engine.
            sync (bool): Sync status of the code block.
            block (NamedTuple): Code block.
        """
        # build code block tuple
        block: NamedTuple = self.__build_block(
            startline,
            endline,
            style,
            body_index,
            syntax_format,
            replace_syntax,
        )

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
        style: str = "indent",
        body_index: int = 0,
        syntax_format: str = None,
        replace_syntax: bool = True,
    ) -> NamedTuple:
        """
        Build the code block from the source file.
        Parameters:
            startline (int): Start line of the code block.
            endline (int): End line of the code block.
            style (str): Style to extract the code block with. Default is `indent`. | `syntax`
            body_index (int): Index of the body of the code block. Default is `0`.
            syntax_format (str): Syntax format of the code block. Default is `None`.
            replace_syntax (bool): Replace syntax of the code block. Default is `True`.
        Returns:
            block (NamedTuple): Code block.
        """
        if not endline:
            endline = self.__caller_source.lenght
            if style == "indent":
                lines = self.__caller_source.lines
                first_line = lines[startline - 1]
                strips = len(first_line) - len(first_line.lstrip())
                # Get the endline of a code block using the indent style
                source_script = ("").join(lines[startline - 1 : -1])
                block_ast: ast.AST = (
                    self.script_utils.get_ast(source_script).body[body_index]
                    if body_index
                    else self.script_utils.get_ast(source_script)
                )
                block = self.script_utils.get_script_from_ast(block_ast)
                for line in range(startline + 1, endline):
                    if len(lines[line]) - len(lines[line].lstrip()) == strips:
                        endline = line
                        break
            elif style == "syntax":
                lines = self.__source_lines
                for line in range(startline, endline):
                    if syntax_format in lines[line]:
                        # Maintain breakpoints end syntax.
                        # Remove so another breakpoint method would find its end syntax
                        if replace_syntax:
                            lines.pop(line)
                            lines.insert(
                                line, f"Debugger inserted placeholder in line {line+1}"
                            )
                        endline = line + 1
                        break
                block = ("").join(
                    self.__caller_source.lines[startline - 1 : endline - 1]
                )
                block_ast: ast.AST = self.script_utils.get_ast(block)
            block_ast_dump: str = ast.dump(block_ast)
            block_comments: str = self.script_utils.get_comments(block_ast)

        else:
            block = ("").join(self.__caller_source.lines[startline - 1 : endline - 1])
            block_ast = self.script_utils.get_ast(block)
            block_ast_dump = ast.dump(block_ast)
            block_comments = self.script_utils.get_comments(block_ast)
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
        return block_object(block, startline, endline, block_ast_dump, block_comments)

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
        status: str = "started",
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
            "execution": {
                "output": output,
                "traceback": {
                    "exception_type": exception_type,
                    "exception_message": exception_message,
                    "full_traceback": full_traceback,
                    "error_line": error_line,
                },
                "status": status,
            },
            "source": {
                "startline": str(startline),
                "endline": str(endline),
                "code": self.__caller_source.string,
                "block": block,
                "imports": self.__caller_source.imports,
                "lined_code": self.__caller_source.lined_string,
                "code_ast_dump": self.__caller_source.ast_dump,
                "linenos": str(self.__caller_source.lenght),
                "block_ast": block_ast_dump,
            },
            "prompt": {
                "suggestions": {
                    "linter": {
                        "value": self.lint_suggestions,
                        "format": "pylint",
                    },
                    "block_comments": block_comments,
                    "subject": subject,
                    "comments": self.__caller_source.comments,
                },
                "mode": mode,  # TODO: change to mode
                "referer": referer,
            },
        }
        # logger.debug(f"'CONTEXT'::context_dict={context}")
        return context

    @__check_status
    def debugger_end_breakpoint(self):
        endline = self.runtime_info.get_stack_caller_frame().lineno
        logger.debug(f"'ENDBREAKPOINT'::endline={endline}")
        # extract the record tied to this end block and dispatch it.. also update it with a flag as True on success ...also it should be the [-1] record in test and fix

    def __exec_engine(self, terminal_type: str = None) -> NamedTuple:
        """
        Spawn the debugger terminal and execute command in it.
        Parameters:
            terminal_type (str): The terminal type to spawn.
        Returns:
            NamedTuple: The terminal type, exit code and command.  NamedTuple("Terminal",[("terminal_type", str),("exit_code", int),("command", str),],)
        """
        # get debugger command
        engine = NamedTuple(
            "Terminal",
            [
                ("terminal_type", str),
                ("exit_code", int),
                ("command", str),
            ],
        )
        terminal_type = terminal_type or self.__terminal_type
        command: TerminalCommand = (
            eval(f"TerminalCommand.{terminal_type}")
            if terminal_type
            else self.__default_ostty_command[self.runtime_info.os]
            if self.runtime_info.distro[0].lower() != Os.ubuntu.lower()
            else TerminalCommand.gnome
        )  # Get the debugger command based on the terminal type and the os
        command = command.format(
            # TODO: Define the path to __main__.py
            command=f"{sys.executable} __main__.py run -c --comm {self.channel.channel_type} -cr --comm-cred {self.channel.channel_credential} --caller-pid -id {self.__caller_pid} -p --caller-path {self.__caller}"
        )
        exit_code: int = os.system(command)
        if exit_code != 0:
            raise Exception("Debugger failed to start")
        return engine(terminal_type, exit_code, command)

    @staticmethod
    @__check_status
    def exit_handler():
        """
        Exit handler to be called on exit of the program.
        """
        # Dispatch all test mode code blocks at exit
        tests = Debugger.watch_logs.get(Mode.test, [])
        fixes = Debugger.watch_logs.get(Mode.fix, [])
        for test in tests:
            if not test["flag"]:
                context = test.get("context")
                context["execution"]["status"] = "success"
                Debugger.dispatch(
                    Mode.test,
                    context,
                    dispatch_by_last_index=False,
                )
        # Redirect all fix modes to improve ... if the fix code block isnt within a previous improve code block
        improvements = Debugger.watch_logs.get(Mode.improve, [])
        for fix in fixes:
            if not fix["flag"]:
                startline = fix.get("startline")
                endline = fix.get("endline")
                if any(
                    [
                        improve
                        for improve in improvements
                        if startline >= improve.get("startline")
                        and endline <= improve.get("endline")
                    ]
                ):
                    continue
                context = fix.get("context")
                context["execution"]["status"] = "success"
                context["prompt"]["referer"] = Mode.fix.value
                context["prompt"]["mode"] = Mode.improve.value
                Debugger.dispatch(
                    Mode.fix,
                    context,
                    dispatch_by_last_index=False,
                )

        # TODO: Log the exit handler
        # TODO: If error occurs outside main thread or process do not unregister the exit handler or a not daemon thread or process
        # if Debugger.channel:
        # Debugger.channel.close()


# Modes
# test: Write `Test`` for the code block and run it to check if it passes. utilizes pytest python api ... Doesn't write test if an error occurs within the code block at runtime ...  instead it logs the error and suggest a `fix` to the code block.
# fix: `Fix` and suggest making changes to the code block. Only runs if an error occurs within the code block at runtime. instead it suggests `improve` to the code block.
# improve: `Improve` and suggest changes to the code block. runs irrespective of errors within the code block at runtime. utilizes linters suggestions,comments and subject. suggest making changes to the code block.
# document: Write `Documentation` for the code block. runs irrespective of errors within the code block at runtime.
# TODO: Add a referer to cli context ... to know what mode suggested another mode. based on this we could come up with better optimized prompts
# TODO: Restrict execute function to wrap method only
# A Sample usage of the debugger class
# from debugger import Debugger
# debug = Debugger()

# Usage
# 1. Using a start and stop method to capture code between the blocks
# debug.breakpoint(mode="fix",subject="This is a sample subject")
# #code goes here
# debug.end_breakpoint()

# 2. Using a with statement to capture code between the blocks
# with debug(mode="improve",subject="This is a sample subject") as debugger:
#     #code goes here

# 3. Using a decorator method `wrap` to capture code between the blocks
# @debug.wrap(mode="test",subject="This is a sample subject")
# def function():
#     #code goes here

# 4. Using a `debug` method to capture code between a start and end line
# debug.debug(startline=1, endline=10,mode="document",subject="This is a sample subject")

# TODO: A regex function that takes a description or what to extract and a sample string where that can be found and returns a list of matches
# TODO: Define a debugger exception class and raise it when an error occurs
# TODO: Define a logging class to log debugger errors and other debugger related information instead of raising errors and exceptions logs could be used
# TODO: When debugger is imported as a module, it should start monitoring the code from the calling script
# TODO: Add a prompt builder ... build prompts with suggestions from pylint/flack8 and comments
# TODO: Self healing code ... comment (use difflib) out block/blocks based on users inputs/choices and replace with an alternative block ... You can use exec() to execute the code from the same directory as the caller script ... The prompt should specify little modification to the source code is required to make it work
# TODO: integrate with pytest ... aside self healing also run script and install missing packages/dependencies (a general code fix to make sure the code runs)
# TODO: A watch all code function that behave like debugger v1.0 ... when imported it should watch all code in the script , write errors to stderr and perform suggestions and refactoring on the code
# TODO: Add a beeping system to both tui/cli and debugger instance to keep both in sync.... on program start and end and execution phase etc..
# TODO: Implement file locking system when communicating with the tui/cli .. https://blog.gitnux.com/code/python-file-lock/#:~:text=In%20Python%2C%20file%20locking%20can,access%2C%20including%20locking%20and%20unlocking.
# TODO: Use a watchdog to watch for file change in tui/cli then read it in as stdin
# EDGECASE: How does debugger function within a thread... does it work as expected
# EDGECASE: How does debugger function within a process... does it work as expected
# EDGECASE: What happens when debugger is imported as a module ???
# TODO: For the llm use auto gpt to save google links into memory and extract sugestions and links ... this would help in fixing code especially.
# BUG: Stop debugger from debugging its own errors and if any(e in error for e in ["KeyboardInterrupt", "SystemExit", "GeneratorExit"]): # Non-compiler errors .. Skip Crtl+C and other keyboard interrupts error
# BUG: Does not work with multiprocessing code... fix it
# BUG : When checking error line.. add check to ensure the file names are same .. if it fails use the other method... with fname and line number and check again
# BUG: Class methods codeblock are not capture correctly .. it captures the whole class
# BUG: Code throws errors when using with method `AttributeError: __enter__` on deactivate
# TODO: Auto pick debugger mode based on code outcome ... if code fails use fix mode if code passes use improve mode
# TODO: OPTIMIZE: Use the line number an intelligent parsing to get what variable name debugger was assign to on init
# TODO: Use signals handlers
# TODO: Configure signals for different os and terminals
# TODO: HAndle invalid modes
# if exc_type and exc_value and traceback: are none then call the watch_logs and remove the latest item from the watch_logs for  fix mode
# if exc_type and exc_value and traceback: are none then call the watch_logs and extract the test latest entry and dispatch for test mode
# else get the watch log call the dispatch_on_error __exit__ works for modes that supoort watch (fix,test)
# exc_type, exc_obj, exc_tb = sys.exc_info()
# fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
# print(exc_type, fname, exc_tb.tb_lineno)
# Get the watch logs for fix .. get the latest entry dictionary .....
# Remember to remove the latest entry from the watch logs .... if no error occurs
# context = (  # A sampl context for the cli-engine
#     {
#         "execution": {
#             "output": "code_execution_output",
#             "traceback": {
#                 "exeception_type": "The type of the execption raised",
#                 "exception_message": "The message of the exception raised",
#                 "full_traceback": "traceback of the code if any",
#                 "error_line": "the line where the error occured",
#             },
#             "status": "failed/success/started",
#         },  # "traceback of the code if any"
#         "source": {
#             "startline": "the start line of the block of code",
#             "endline": "the end line of the block of code",
#             "code": "The whole source code",
#             "block": "The block of code that was selected by the user",  # could be same as the code
#             "imports": "The imports within the code block",
#             "line_code": "The code with line numbers",
#             "line_block": "The block of code with line numbers",
#             "code_ast": "The ast of the whole source code",
#             "linenos": "The line numbers of the code",
#             "block_ast": "The ast of the block of code that was selected by the user",  # could be same as the code_ast .. use ast.dump() to get the ast
#         },  # "the whole source code"
#         "prompt": {
#             "suggestions": {
#                 "linter": {
#                     "value": "The suggestions from the linter eg. pylint, flake8",
#                     "format": "pylint, flake8, etc",
#                 },
#                 "comments": "The suggestions from the comments within the code block",
#                 "subject": "The suggestions from the user",  # This could be a list or dictionary from the options arguement defined by the user
#             },  # "suggestions from the debugger",  # suggestions from the debugger could be from pylint, flake8, comments/documentations, etc,
#             "mode": "The mode of the prompt eg. refactor, fix,test,documentation",
#         },
#     },
# )

# class GracefulDeath:
#     """Catch signals to allow graceful shutdown."""

#     def __init__(self):
#         self.received_signal = self.received_term_signal = False
#         catch_signals = [
#             1,
#             2,
#             3,
#         ]
#         for signum in catch_signals:
#             signal.signal(signum, self.handler)

#     def handler(self, signum, frame):
#         self.last_signal = signum
#         self.received_signal = True
#         if signum in [2, 3, 15]:
#             self.received_term_signal = True
#         # {
#         #     signal.SIGHUP: 1,
#         #     signal.SIGINT: 2,
#         #     signal.SIGQUIT: 3,
#         #     signal.SIGILL: 4,
#         #     signal.SIGTRAP: 5,
#         #     signal.SIGABRT: 6,
#         #     signal.SIGEMT: 7,
#         #     signal.SIGFPE: 8,
#         # signal.SIGKILL: 9, # this is not working for unix
#         #     signal.SIGBUS: 10,
#         #     signal.SIGSEGV: 11,
#         #     signal.SIGSYS: 12,
#         #     signal.SIGPIPE: 13,
#         #     signal.SIGALRM: 14,
#         #     signal.SIGTERM: 15,
#         #     signal.SIGURG: 16,
#         # signal.SIGSTOP: 17,# this is not working for unix
#         #     signal.SIGTSTP: 18,
#         #     signal.SIGCONT: 19,
#         #     signal.SIGCHLD: 20,
#         #     signal.SIGTTIN: 21,
#         #     signal.SIGTTOU: 22,
#         #     signal.SIGIO: 23,
#         #     signal.SIGXCPU: 24,
#         #     signal.SIGXFSZ: 25,
#         #     signal.SIGVTALRM: 26,
#         #     signal.SIGPROF: 27,
#         #     signal.SIGWINCH: 28,
#         #     signal.SIGINFO: 29,
#         #     signal.SIGUSR1: 30,
#         #     signal.SIGUSR2: 31,
#         # }
