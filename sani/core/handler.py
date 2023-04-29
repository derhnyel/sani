from sani.debugger.debugger import Debugger
from sani.utils.custom_types import (
    Mode,
    Context,
    Code,
    Mode,
    Tuple,
    Enums,
)
from sani.core.run import ScriptRun
from sani.core.config import Config

config = Config()


def handler(
    caller: str,
    channel: str = None,
    linter: str = None,
    executable: str = None,
    args: Tuple = tuple(),
):
    script: ScriptRun = ScriptRun(caller, executable, *args)
    debugger: Debugger = Debugger(
        name=script.file_path.name,
        language=script.language.value,
        channel=channel,
        linter=linter,
        caller=caller,
        attach_hook=False,
        run_as_main=False,
        stdout="./example/example.txt",
    )
    trigger: dict = {}

    def set_trigger(attr: str):
        sep_attr = attr.split(config.seperator)
        if len(sep_attr) == 2:
            if sep_attr[0] == Context.mode:
                trigger[Context.mode.value] = Mode.__dict__.get(Enums.members).get(
                    sep_attr[1]
                )
            elif sep_attr[0] == Context.subject:
                trigger[Context.subject.value] = sep_attr[1]
            elif sep_attr[0] == Context.startline:
                trigger[Context.startline.value] = sep_attr[1]
            elif sep_attr[0] == Context.endline:
                trigger[Context.endline.value] = sep_attr[1]
            else:
                print("Unknown suffix", sep_attr[0])
        else:
            print("Unknown suffix", sep_attr[0])

    for comment in debugger.caller_comments:
        if comment.text.strip().lower().startswith(config.prefix.strip().lower()):
            attributes = comment.text.split(config.delimiter)
            if len(attributes) > 1:
                [set_trigger(attr.strip()) for attr in attributes[1:]]
                if (
                    trigger.get(Context.startline)
                    and trigger.get(Context.endline)
                    and trigger.get(Context.mode)
                ):
                    debugger.debug(
                        int(trigger.get(Context.startline)),
                        int(trigger.get(Context.endline)),
                        trigger.get(Context.mode),
                        trigger.get(Context.subject),
                        remove_pattern=f"{config.prefix}",  # {config.delimiter}",
                    )
                elif trigger.get(Context.mode):
                    debugger.breakpoint(
                        trigger.get(Context.mode),
                        trigger.get(Context.subject),
                        syntax_format=config.end_syntax or Code.end_syntax.value,
                        startline=comment.lineno,
                        remove_pattern=f"{config.prefix}",  # {config.delimiter}",
                    )

    output, error = script.run()
    if error:
        debugger.dispatch_on_error(traceback_n=error)
    else:
        debugger.exit_handler(output)
