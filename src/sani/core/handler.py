"""This program parses various source files and extracts the comment texts.
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
    Mode,
    Context,
    Code,
    Mode,
    Tuple,
    Enums,
)
from sani.utils.logger import get_logger
from sani.core.run import ScriptRun
from config import Config

config = Config()
logger = get_logger(__name__)


def handler(
    caller: str,
    channel: str = None,
    linter: str = None,
    executable: str = None,
    args: Tuple = tuple(),
):
    script: ScriptRun = ScriptRun(caller, executable, *args)
    debugger: Debugger = (
        Debugger(
            language=script.language,
            channel=channel,
            linter=linter,
            caller=caller,
            attach_hook=False,
            run_as_main=False,
        ),
    )
    adict: dict = {}

    def proc(val: str):
        spli = val.split(config.seperator)
        if len(spli) == 2:
            if spli[0] == Context.mode:
                adict[Context.mode.value] = Mode.__dict__.get(Enums.members).get(
                    spli[1]
                )
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
        if comment.text.lower().startswith(config.prefix.lower()):
            print("Found a SANI comment.", comment)
            attributes = comment.text.split(config.delimiter)
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
                    breakpoint=config.end_syntax or Code.end_syntax.value,
                )
            # adict = {}
    output, error = script.run()
    if error:
        debugger.dispatch_on_error(traceback_n=error)
    else:
        debugger.exit_handler(output)


