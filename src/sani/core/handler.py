"""This program parses various source files and extracts the comment texts.

Currently supported languages:
  Bash/sh
  C
  C++
  Go
  HTML
  Java
  Javascript
  Ruby
  XML

Dependencies:
  python-magic: pip install python-magic (optional)
"""

try:
    import magic

    has_magic = True
except ImportError:
    has_magic = False

from sani.debugger.debugger import Debugger
from sani.utils.custom_types import (
    Language,
    Mode,
    Optional,
    Dict,
    List,
    Context,
    Code,
    Os,
)
from sani.utils.exception import ParseError, UnsupportedError
from sani.utils.logger import get_logger


logger = get_logger(__name__)

MIME_MAP: Dict[str, Language] = {
    "application/javascript": Language.javascript,  # Javascript
    "text/html": Language.html,  # HTML
    "text/x-c": Language.c,  # C
    "text/x-c++": Language.c,  # C++/C#
    "text/x-go": Language.go,  # Go
    "text/x-java": Language.c,  # Java
    "text/x-java-source": Language.c,  # Java
    "text/x-javascript": Language.javascript,  # Javascript
    "text/x-python": Language.python,  # Python
    "text/x-ruby": Language.ruby,  # Ruby
    "text/x-script.python": Language.python,  # Python
    "text/x-shellscript": Language.shell,  # Unix shell
    "text/xml": Language.html,  # XML
}


def get_debugger(
    caller: str, mime: Optional[str] = None, channel: str = None, linter: str = None
) -> Debugger:
    """Extracts and returns comments from the given source string.

    Args:
      caller: String name of the file.
      mime: Optional MIME type for code (str). Note some MIME types accepted
        don't comply with RFC2045. If not given, an attempt to deduce the
        MIME type will occur.
      channel: Optional channel to use for debugging.
      linter: Optional linter to use for debugging.
    Returns:
        A Debugger object.
    Raises:
      UnsupportedError: If code is of an unsupported MIME type.
    """
    if not mime:
        if not has_magic:
            raise ImportError("python-magic was not imported")
        mime = magic.from_file(caller, mime=True)
        if isinstance(mime, bytes):
            mime = mime.decode("utf-8")
    if mime not in MIME_MAP:
        raise UnsupportedError(f"Unsupported MIME type {mime}")
    try:
        language = MIME_MAP[mime]
        return Debugger(
            language=language,
            channel=channel,
            linter=linter,
            caller=caller,
            attach_hook=False,
            run_as_main=False,
        )
    except Exception as e:
        raise ParseError() from e


prefix: str = "sani"
delimiter = ":"
seperator = "="
end_syntax = "sani:end"

comment_mode_map: Dict[str, Mode] = {
    "fix": Mode.fix,
    "analyze": Mode.analyze,
    "document": Mode.document,
    "improve": Mode.improve,
    "test": Mode.test,
}
order = "{prefix}{delimiter}mode{seperator}fix{delimiter}subject{seperator}A comment{delimiter}startline{seperator}10{delimiter}endline{seperator}15{delimiter}"
# SANI:mode=fix:subject=This is a comment:startline=10:endline=15
# SANI:end


def comment_handler():
    """Parses the source code and prints the comments."""
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "source", metavar="source", type=str, help="Path to source file."
    )
    parser.add_argument(
        "-m",
        "--mime",
        type=str,
        help="MIME type of source file. If not given, an attempt to deduce the MIME type will occur.",
    )
    parser.add_argument(
        "-c",
        "--channel",
        type=str,
        help="Channel to use for debugging. Defaults to stdout.",
    )
    parser.add_argument(
        "-l",
        "--linter",
        type=str,
        help="Linter to use for debugging. Defaults to pylint.",
    )
    args = parser.parse_args()
    debugger = get_debugger(
        args.source, mime=args.mime, channel=args.channel, linter=args.linter
    )
    adict: dict = {}

    def proc(val: str):
        spli = val.split(seperator)
        if len(spli) == 2:
            if spli[0] == Context.mode:
                adict[Context.mode.value] = comment_mode_map.get(spli[1])
            elif spli[0] == Context.subject:
                adict[Context.subject.value] = spli[1]
            elif spli[0] == Context.startline:
                adict[Context.startline.value] = spli[1]
            elif spli[0] == Context.endline:
                adict[Context.endline.value] = spli[1]
            else:
                print("Unknown suffix", spli[0])
        else:
            print("Unknown suffix", spli[0])

    for comment in debugger.__caller_comments:
        if comment.text.lower().startswith(prefix.lower()):
            print("Found a SANI comment.", comment)
            attributes = comment.text.split(delimiter)
            map(proc, attributes[1:-1])
            print(adict)
            if (
                adict.get(Context.startline)
                and adict.get(Context.endline)
                and adict.get(Context.mode)
            ):
                debugger.debug(
                    adict.get(Context.startline),
                    adict.get(Context.endline),
                    adict.get(Context.mode),
                    adict.get(Context.subject),
                )
            elif adict.get(Context.mode):
                debugger.breakpoint(
                    adict.get(Context.mode),
                    adict.get(Context.subject),
                    breakpoint=end_syntax or Code.end_syntax.value,
                )
            # adict = {}


def runtime_handler():
    pass


from subprocess import PIPE, Popen
from threading import Thread
from queue import Queue
import sys
import os


class RuntimeHandler:
    def __init__(self, file_path):
        if not os.path.isfile(file_path):
            raise FileNotFoundError(file_path)
        # Get script language using mime type
        

    def on_error():
        pass

    def listen(self, command):
        output: list = []
        errors: list = []
        pipe_queue = Queue()
        process = Popen(
            command,
            cwd=None,
            shell=False,
            close_fds=(sys.platform not in [Os.windows32, Os.windows64]),
            stdout=PIPE,
            stderr=PIPE,
            bufsize=1,
        )

        stdout_thread: Thread = Thread(
            target=self.read,
            args=(process.stdout, [pipe_queue.put, output.append]),
        )
        stderr_thread: Thread = Thread(
            target=self.read,
            args=(process.stderr, [pipe_queue.put, errors.append]),
        )

        writer_thread: Thread = Thread(
            target=self.write, args=(pipe_queue.get,)
        )  # Thread for printing items in the queue

        # Spawns each thread
        for thread in (stdout_thread, stderr_thread, writer_thread):
            thread.daemon = True
            thread.start()

            process.wait()

        for thread in (stdout_thread, stderr_thread):
            thread.join()

        pipe_queue.put(None)

        output = " ".join(output)
        errors = " ".join(errors)

        # if "java" != command[0] and not os.path.isfile(command[1]): # File doesn't exist, for java, command[1] is a class name instead of a file
        #    return (None, None)
        # else:
        return (output, errors)

    @staticmethod
    def read(pipe: PIPE, funcs: List[function]):
        """
        Reads and pushes piped output to a shared queue and appropriate lists.
        """
        for line in iter(pipe.readline, b""):
            for func in funcs:
                func(line.decode("utf-8"))
        pipe.close()

    @staticmethod
    def write(get: function):
        """
        Pulls output from shared queue and prints to terminal.
        """
        for line in iter(get, None):
            print(line)
