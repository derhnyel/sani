from sani.core.channel import Channel, BaseCommChannel
from sani.utils.custom_types import (
    Enums,
    Mode,
    Context,
    script as script_type,
    ChatResponse,
    List,
    Dict,
)
from typing import Optional
from sani.bot.bots import (
    FixBot,
    ImproveBot,
    TestBot,
    DocumentBot,
    AnalyzeBot,
    GenericSaniBot,
    BaseBot,
)
from sani.core.run import ScriptRun
from sani.core.config import Config
from sani.debugger.script import Script, BaseScript
from termcolor import cprint
from platformdirs import user_data_path

import os
from pathlib import Path
import shutil

config = Config()
DEFAULT_MODE_BOT: Dict[Mode, BaseBot] = {
    Mode.fix: FixBot,
    Mode.improve: ImproveBot,
    Mode.test: TestBot,
    Mode.document: DocumentBot,
    Mode.analyze: AnalyzeBot,
}
MUST_RUN_MODES = [
    Mode.fix,
    Mode.improve,
    Mode.document
]  # Modes to  Rerun scripts and scripts must execute succesfully

NEW_FILE_MODES = [
    Mode.test,
]  # Modes to create new script and scripts must execute succesfully
from io import BytesIO, TextIOWrapper

MODIFIED_SOURCE_LIST: List[str] = None
PARSED_SOURCE: tuple[str, List[str], List[str], script_type] = None
# import sys
import difflib
import json


# def main(channel: str, credentials: str):
#     channel: Channel = Channel.__dict__.get(Enums.members).get(channel)
#     if not channel:
#         raise Exception("Unknown channel")
#     comm: BaseCommChannel = channel.value(**credentials)
#     for message in comm.receive(callback=callback):
#         print(message)


def get_workspace():
    app_name = config.app_name
    app_author = config.app_author
    app_version = config.app_version
    workspace = user_data_path(app_name, app_author, app_version)
    if not os.path.exists(workspace):
        os.makedirs(workspace)
    return workspace


def backup(source_path: str, mode="create"):
    source_path: Path = Path(source_path)
    file = source_path.name + ".backup"
    workspace = get_workspace()
    backup = os.path.join(workspace, file)
    if os.path.exists(backup):
        if mode == "create":
            # raise Exception("Backup already exists")
            return False
        elif mode == "restore":
            shutil.copy(backup, source_path)
        return True
    else:
        if mode == "create":
            shutil.copy(source_path, backup)
        elif mode == "restore":
            # raise Exception("No backup exists")
            return False
        return True


def callback(message: dict):
    # try:
        global PARSED_SOURCE
        mode = message.get(Context.prompt).get(Context.mode)
        source_path = message.get(Context.source).get(Context.source_path)
        script_args = message.get(Context.execution).get(Context.args)
        source_list = message.get(Context.source).get(Context.source_list)
        command = message.get(Context.execution).get(Context.command)
        backup(source_path, mode="create")
        cnt = 0
        bot: BaseBot = DEFAULT_MODE_BOT.get(mode)
        if bot:
            bot = bot(context=message)
        else:
            raise Exception("Invalid Bot")

        bot_response: str = bot.dispatch(append_result=True)

        # Get response.. extract code block and parse replacement also creating a backup
        if mode in MUST_RUN_MODES:
            script = ScriptRun(file_path=source_path, *script_args)
            script_parser: Script = Script.__dict__.get(Enums.members).get(
                script.language
            )
            if not script_parser:
                raise Exception("Unable to Parse Script")
            parser: BaseScript = script_parser.value()
            # Get the new block from bot output and replace it in the source file AND create a backup .
            (
                diff,
                explanations,
                operation_changes,
                parsed_object,
            ) = sync_script_with_json(
                bot, bot_response, source_list, source_path, parser
            )
            output, _, success = script.check(command)
            print_changes(diff, explanations, output)

            while not success and cnt < config.runtime_recusive_limit:
                # write modified changes to file
                # Call fix bot to fix script on error

                message[Context.execution.value][Context.traceback.value][
                    Context.full_traceback.value
                ] = output
                message[Context.source.value][Context.code.value] = parsed_object.string
                message[Context.source.value][
                    Context.lined_code.value
                ] = parsed_object.lined_string
                message[Context.source.value][
                    Context.block.value
                ] = parsed_object.string
                message[Context.source.value][
                    Context.lined_block.value
                ] = parsed_object.lined_string
                message[Context.source.value][
                    Context.linenos.value
                ] = parsed_object.lenght
                message[Context.source.value][Context.startline.value] = 1
                message[Context.source.value][
                    Context.endline.value
                ] = parsed_object.lenght
                message[Context.execution.value][Context.traceback.value][
                    Context.exception_message.value
                ] = output
                message[Context.execution.value][Context.traceback.value][
                    Context.full_traceback.value
                ] = output
                message[Context.execution.value][Context.traceback.value][
                    Context.exception_type.value
                ] = output
                source_list = parsed_object.lines
                # print(parsed_object.string)
                # print(message.get(Context.source).get(Context.code))
                fix_bot = FixBot(context=message)
                bot_response: str = fix_bot.dispatch()
                (
                    diff,
                    explanations,
                    operation_changes,
                    parsed_object,
                ) = PARSED_SOURCE = sync_script_with_json(
                    fix_bot, bot_response, source_list, source_path, parser
                )
                output, _, success = script.check(command)
                print_changes(diff, explanations, output)
                cnt += 1
    # except Exception as e:
    #     print("An Error occured:", e)
    #     backup(source_path, mode="restore")


def sync_script_with_json(
    bot: BaseBot,
    bot_response: str,
    source_list: List[str],
    source_path: str,
    parser: BaseScript,
) -> tuple[str, List[str], List[str], script_type]:
    global MODIFIED_SOURCE_LIST
    print(bot_response)

    json_response: Dict = json_validated_response(bot, bot_response)
    (
        modified_source_list,
        diff,
        explanations,
        operation_changes,
    ) = parse_bot_json_response(source_list, json_response)
    # Write/Read the modified source list to file before checking for errors
    with open(source_path, "w") as f:
        f.writelines(modified_source_list)
    b_mod_list = BytesIO(("").join(modified_source_list).encode("utf-8"))
    io_mod_source = TextIOWrapper(b_mod_list, encoding="utf-8")
    # try:
    parsed_object: script_type = parser.get_attributes(io_mod_source)
    # except IndentationError:
    #     # Use another parser
    #     pass
    MODIFIED_SOURCE_LIST = modified_source_list
    return diff, explanations, operation_changes, parsed_object


def json_validated_response(bot: BaseBot, output: str):
    """
    This function is needed because the API can return a non-json response.
    This will run recursively until a valid json response is returned.
    todo: might want to stop after a certain number of retries
    """
    # see if json can be parsed
    try:
        # json_start_index = output.index(
        #     "{"
        # )  # find the starting position of the JSON data
        json_data = output  # output[json_start_index:]  # extract the JSON data from the response string
        json_response = json.loads(json_data)
    except (json.decoder.JSONDecodeError, ValueError) as e:
        cprint(f"{e}. Re-running the query.", "red")
        # debug
        cprint(f"\nGPT RESPONSE:\n\n{output}\n\n", "yellow")
        # append a user message that says the json is invalid
        output = bot.dispatch(
            message="Your response could not be parsed by json.loads. Please restate or continue your last message as pure JSON.",
            append_message=True,
            append_result=True,
        )
        # rerun the api call recursively
        return json_validated_response(bot, output)
    except Exception as e:
        cprint(f"Unknown error: {e}", "red")
        cprint(f"\nGPT RESPONSE:\n\n{output}\n\n", "yellow")
        raise e
    else:
        return json_response


def parse_bot_json_response(source_list: List[str], changes: List[Dict[str, str]]):
    """
    Parse the bot json response and return the changes to be made to the source file
    Parameters
            source_list: List[str]
                List of lines in the source file
            changes: List[Dict[str]]
                List of changes to be made to the source file
    """
    # Filter out explanation elements
    operation_changes: List[Dict[str, str]] = changes[ChatResponse.operation]
    explanations = changes[ChatResponse.explanation]
    # Sort the changes in reverse line order
    operation_changes.sort(key=lambda x: x[ChatResponse.line], reverse=True)
    file_lines = source_list.copy()
    for change in operation_changes:
        print(change)
        operation = change[ChatResponse.type_]
        line = change[ChatResponse.line]
        content = change.get(ChatResponse.statement)
        if operation == ChatResponse.replace_:
            if content:
                file_lines[line - 1] = content + "\n"
        elif operation == ChatResponse.delete:
            del file_lines[line - 1]
        elif operation == ChatResponse.insert:
            if content:
                file_lines.insert(line, content + "\n")
    diff = difflib.unified_diff(source_list, file_lines, lineterm="")
    return file_lines, diff, explanations, operation_changes


def print_changes(diff: List[str], explanations: List[str], output=None):
    # Print explanations
    cprint("Explanations:", "blue")
    cprint(f"- {explanations}", "blue")
    for line in diff:
        if line.startswith("+"):
            cprint(line, "green", end="")
        elif line.startswith("-"):
            cprint(line, "red", end="")
        else:
            print(line, end="")
    cprint("Output :", "red")
    cprint(f"- {output}", "blue")


context = {"execution": {"output": None, "traceback": {"exception_type": None, "exception_message": None, "full_traceback": None, "error_line": None, "pid": 24818}, "status": "inprogress", "args": [], "command": []}, "source": {"startline": "12", "endline": "32", "code": "\"\"\"\nModule for caching operations.\n\"\"\"\nfrom sani.debugger import debugger\nimport json\nimport zlib\nfrom typing import Any, Dict\nimport datetime\n\nfrom typing import Any, Dict\ndebug = debugger.Debugger(__name__, stdout=\"test.txt\", channel=\"io\")\ndebug.breakpoint(mode=\"improve\", subject=\"cache operations\")\n\ndef write_to_cache(query: str, result: Any, cache_obj: Dict):\n    \"\"\"\n    Write the result of a query to the cache object.\n    \"\"\"\n    hash_value = zlib.adler32(query.encode('utf-8'))\n    cache_obj[hash] = json.dumps(result)\n    # redis_connection.set(hash, json.dumps(result))\n\nobjects = [\n    {'id': '12341228', 'title': 'Hello world in python', 'view_count': 2378},\n    {'id': '44780514', 'title': 'FastAPI with Odmantic', 'view_count': 1970},\n    {'id': datetime.date(7123, 11, 28), 'title': 'pandas loc vs iloc', 'view_count': 4012},\n    {'id': '02139172', 'title': 'Dataframe in Pandas', 'view_count': 4012}\n]\ncache = {}\nQUERY = 'pandas'\nwrite_to_cache(QUERY, objects[2], cache) # buggy call here.\nprint(cache)\ndebug.debugger_end_breakpoint()\n", "block": "\n\ndef write_to_cache(query: str, result: Any, cache_obj: Dict):\n    \"\"\"\n    Write the result of a query to the cache object.\n    \"\"\"\n    hash_value = zlib.adler32(query.encode('utf-8'))\n    cache_obj[hash] = json.dumps(result)\n    # redis_connection.set(hash, json.dumps(result))\n\nobjects = [\n    {'id': '12341228', 'title': 'Hello world in python', 'view_count': 2378},\n    {'id': '44780514', 'title': 'FastAPI with Odmantic', 'view_count': 1970},\n    {'id': datetime.date(7123, 11, 28), 'title': 'pandas loc vs iloc', 'view_count': 4012},\n    {'id': '02139172', 'title': 'Dataframe in Pandas', 'view_count': 4012}\n]\ncache = {}\nQUERY = 'pandas'\nwrite_to_cache(QUERY, objects[2], cache) # buggy call here.\nprint(cache)\n\n", "lined_code": "1 : \"\"\"\n2 : Module for caching operations.\n3 : \"\"\"\n4 : from sani.debugger import debugger\n5 : import json\n6 : import zlib\n7 : from typing import Any, Dict\n8 : import datetime\n9 : \n10 : from typing import Any, Dict\n11 : debug = debugger.Debugger(__name__, stdout=\"test.txt\", channel=\"io\")\n12 : debug.breakpoint(mode=\"improve\", subject=\"cache operations\")\n13 : \n14 : def write_to_cache(query: str, result: Any, cache_obj: Dict):\n15 :     \"\"\"\n16 :     Write the result of a query to the cache object.\n17 :     \"\"\"\n18 :     hash_value = zlib.adler32(query.encode('utf-8'))\n19 :     cache_obj[hash] = json.dumps(result)\n20 :     # redis_connection.set(hash, json.dumps(result))\n21 : \n22 : objects = [\n23 :     {'id': '12341228', 'title': 'Hello world in python', 'view_count': 2378},\n24 :     {'id': '44780514', 'title': 'FastAPI with Odmantic', 'view_count': 1970},\n25 :     {'id': datetime.date(7123, 11, 28), 'title': 'pandas loc vs iloc', 'view_count': 4012},\n26 :     {'id': '02139172', 'title': 'Dataframe in Pandas', 'view_count': 4012}\n27 : ]\n28 : cache = {}\n29 : QUERY = 'pandas'\n30 : write_to_cache(QUERY, objects[2], cache) # buggy call here.\n31 : print(cache)\n32 : debug.debugger_end_breakpoint()\n", "linenos": "32", "language": "python", "code block comments": None, "source_path": "/workspaces/sani/test_improve.py", "lined_block": "12:\n13:\n14:def write_to_cache(query: str, result: Any, cache_obj: Dict):\n15:    \"\"\"\n16:    Write the result of a query to the cache object.\n17:    \"\"\"\n18:    hash_value = zlib.adler32(query.encode('utf-8'))\n19:    cache_obj[hash] = json.dumps(result)\n20:    # redis_connection.set(hash, json.dumps(result))\n21:\n22:objects = [\n23:    {'id': '12341228', 'title': 'Hello world in python', 'view_count': 2378},\n24:    {'id': '44780514', 'title': 'FastAPI with Odmantic', 'view_count': 1970},\n25:    {'id': datetime.date(7123, 11, 28), 'title': 'pandas loc vs iloc', 'view_count': 4012},\n26:    {'id': '02139172', 'title': 'Dataframe in Pandas', 'view_count': 4012}\n27:]\n28:cache = {}\n29:QUERY = 'pandas'\n30:write_to_cache(QUERY, objects[2], cache) # buggy call here.\n31:print(cache)\n32:\n", "source_list": ["\"\"\"\n", "Module for caching operations.\n", "\"\"\"\n", "from sani.debugger import debugger\n", "import json\n", "import zlib\n", "from typing import Any, Dict\n", "import datetime\n", "\n", "from typing import Any, Dict\n", "debug = debugger.Debugger(__name__, stdout=\"test.txt\", channel=\"io\")\n", "debug.breakpoint(mode=\"improve\", subject=\"cache operations\")\n", "\n", "def write_to_cache(query: str, result: Any, cache_obj: Dict):\n", "    \"\"\"\n", "    Write the result of a query to the cache object.\n", "    \"\"\"\n", "    hash_value = zlib.adler32(query.encode('utf-8'))\n", "    cache_obj[hash] = json.dumps(result)\n", "    # redis_connection.set(hash, json.dumps(result))\n", "\n", "objects = [\n", "    {'id': '12341228', 'title': 'Hello world in python', 'view_count': 2378},\n", "    {'id': '44780514', 'title': 'FastAPI with Odmantic', 'view_count': 1970},\n", "    {'id': datetime.date(7123, 11, 28), 'title': 'pandas loc vs iloc', 'view_count': 4012},\n", "    {'id': '02139172', 'title': 'Dataframe in Pandas', 'view_count': 4012}\n", "]\n", "cache = {}\n", "QUERY = 'pandas'\n", "write_to_cache(QUERY, objects[2], cache) # buggy call here.\n", "print(cache)\n", "debug.debugger_end_breakpoint()\n"]}, "prompt": {"suggestions": {"lint_suggestions": "************* Module test_improve\ntest_improve.py:10:0: W0404: Reimport 'Any' (imported line 7) (reimported)\ntest_improve.py:10:0: W0404: Reimport 'Dict' (imported line 7) (reimported)\ntest_improve.py:18:4: W0612: Unused variable 'hash_value' (unused-variable)\ntest_improve.py:5:0: C0411: standard import \"import json\" should be placed before \"from sani.debugger import debugger\" (wrong-import-order)\ntest_improve.py:6:0: C0411: standard import \"import zlib\" should be placed before \"from sani.debugger import debugger\" (wrong-import-order)\ntest_improve.py:7:0: C0411: standard import \"from typing import Any, Dict\" should be placed before \"from sani.debugger import debugger\" (wrong-import-order)\ntest_improve.py:8:0: C0411: standard import \"import datetime\" should be placed before \"from sani.debugger import debugger\" (wrong-import-order)\ntest_improve.py:10:0: C0411: standard import \"from typing import Any, Dict\" should be placed before \"from sani.debugger import debugger\" (wrong-import-order)\ntest_improve.py:10:0: C0412: Imports from package typing are not grouped (ungrouped-imports)\n\n------------------------------------------------------------------\nYour code has been rated at 4.71/10 (previous run: 2.14/10, +2.56)\n\n", "linter": "pylint", "intended action": "cache operations"}, "mode": "improve", "referer": None}}

callback(context)
