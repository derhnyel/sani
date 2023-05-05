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
]  # Modes to  Rerun scripts and scripts must execute succesfully

NEW_FILE_MODES = [
    Mode.test,
]  # Modes to create new script and scripts must execute succesfully
from io import BytesIO, TextIOWrapper

MODIFIED_SOURCE_LIST: List[str] = None
PARSED_SOURCE: tuple[str, List[str], List[str], script_type] = None
import sys
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
    try:
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
    except Exception as e:
        print("An Error occured:", e)
        backup(source_path, mode="restore")


def sync_script_with_json(
    bot: BaseBot,
    bot_response: str,
    source_list: List[str],
    source_path: str,
    parser: BaseScript,
) -> tuple[str, List[str], List[str], script_type]:
    global MODIFIED_SOURCE_LIST

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


context = {
    "execution": {
        "output": None,
        "traceback": {
            "exception_type": None,
            "exception_message": None,
            "full_traceback": None,
            "error_line": None,
            "pid": 80192,
        },
        "status": "inprogress",
        "args": [],
        "command": [],
    },
    "source": {
        "startline": "7",
        "endline": "63",
        "code": 'from sani.debugger.debugger import Debugger\n\n# Debuggy.deactivate = False\n# Debuggy.__deactivate_hook = False\ndebug = Debugger(name=__name__, stdout="example.txt", channel="iuio", linter="pylint")\n\ndebug.breakpoint(mode="improve", subject="build an automatic scraper")\n\n\n# SANI:mode=fix:subject=This is a comment:startline=11:endline=18\nclass Test:\n    def __init__(self):\n        self.name = "Test"\n\n    @debug.wrap(mode="document")\n    def test1(self):\n        print("A documention block within Test class function test1 called with wrap")\n        return self.name\n\n    # debuggy_end_breakpoint\n    @debug.wrap(mode="improve")\n    def test2(self):\n        print("An improve block within Test class function test2 called with wrap")\n        # raising an exception\n        try:\n            raise Exception("I Raised this exception . Now handle it and fix me ..")\n        except Exception as e:\n            print("I caught this myself")\n\n    @staticmethod\n    @debug.wrap(mode="ai_fn")\n    def test3():\n        print("A test block within Test class function test3 called with wrap ")\n        # raising an exception\n        # raise Exception("I Raised this exception . Now handle it and fix me ..")\n\n    @debug.wrap(mode="fix")\n    def test4(self):\n        print("I am here for testing the fix mode")\n        return self\n\n\n# sani fix\ntest = Test()\ntest.test1()\n# test.test2()\ndebug.debug(1, 10, mode="document")\n# sani fix-end\n\n# with debug(mode="analyze") as debugger:\n#     set = 10\n#     print("The with statement is working fine")\n#     test.test3()\nimport time\n\ntest.test4()\nwhile True:\n    print("I am here for testing the fix mode")\n    time.sleep(2)\n    break\n\n\ndebug.debugger_end_breakpoint()\n# sani fix-end\n# sani.regex(\n#     "get a the words that end in \'ing\' from this sentence",\n#     "He has been leisurely testing the ending of the sentence but he is not sure if it is ending or not ending",\n# )  # returns [\'testing\', \'ending\']\n',
        "block": '\n\n\n# SANI:mode=fix:subject=This is a comment:startline=11:endline=18\nclass Test:\n    def __init__(self):\n        self.name = "Test"\n\n\n    def test1(self):\n        print("A documention block within Test class function test1 called with wrap")\n        return self.name\n\n    # debuggy_end_breakpoint\n\n    def test2(self):\n        print("An improve block within Test class function test2 called with wrap")\n        # raising an exception\n        try:\n            raise Exception("I Raised this exception . Now handle it and fix me ..")\n        except Exception as e:\n            print("I caught this myself")\n\n    @staticmethod\n\n    def test3():\n        print("A test block within Test class function test3 called with wrap ")\n        # raising an exception\n        # raise Exception("I Raised this exception . Now handle it and fix me ..")\n\n\n    def test4(self):\n        print("I am here for testing the fix mode")\n        return self\n\n\n# sani fix\ntest = Test()\ntest.test1()\n# test.test2()\n\n# sani fix-end\n\n\n#     set = 10\n#     print("The with statement is working fine")\n#     test.test3()\nimport time\n\ntest.test4()\nwhile True:\n    print("I am here for testing the fix mode")\n    time.sleep(2)\n    break\n\n\n\n',
        "lined_code": '1 : from sani.debugger.debugger import Debugger\n2 : \n3 : # Debuggy.deactivate = False\n4 : # Debuggy.__deactivate_hook = False\n5 : debug = Debugger(name=__name__, stdout="example.txt", channel="iuio", linter="pylint")\n6 : \n7 : debug.breakpoint(mode="improve", subject="build an automatic scraper")\n8 : \n9 : \n10 : # SANI:mode=fix:subject=This is a comment:startline=11:endline=18\n11 : class Test:\n12 :     def __init__(self):\n13 :         self.name = "Test"\n14 : \n15 :     @debug.wrap(mode="document")\n16 :     def test1(self):\n17 :         print("A documention block within Test class function test1 called with wrap")\n18 :         return self.name\n19 : \n20 :     # debuggy_end_breakpoint\n21 :     @debug.wrap(mode="improve")\n22 :     def test2(self):\n23 :         print("An improve block within Test class function test2 called with wrap")\n24 :         # raising an exception\n25 :         try:\n26 :             raise Exception("I Raised this exception . Now handle it and fix me ..")\n27 :         except Exception as e:\n28 :             print("I caught this myself")\n29 : \n30 :     @staticmethod\n31 :     @debug.wrap(mode="ai_fn")\n32 :     def test3():\n33 :         print("A test block within Test class function test3 called with wrap ")\n34 :         # raising an exception\n35 :         # raise Exception("I Raised this exception . Now handle it and fix me ..")\n36 : \n37 :     @debug.wrap(mode="fix")\n38 :     def test4(self):\n39 :         print("I am here for testing the fix mode")\n40 :         return self\n41 : \n42 : \n43 : # sani fix\n44 : test = Test()\n45 : test.test1()\n46 : # test.test2()\n47 : debug.debug(1, 10, mode="document")\n48 : # sani fix-end\n49 : \n50 : # with debug(mode="analyze") as debugger:\n51 : #     set = 10\n52 : #     print("The with statement is working fine")\n53 : #     test.test3()\n54 : import time\n55 : \n56 : test.test4()\n57 : while True:\n58 :     print("I am here for testing the fix mode")\n59 :     time.sleep(2)\n60 :     break\n61 : \n62 : \n63 : debug.debugger_end_breakpoint()\n64 : # sani fix-end\n65 : # sani.regex(\n66 : #     "get a the words that end in \'ing\' from this sentence",\n67 : #     "He has been leisurely testing the ending of the sentence but he is not sure if it is ending or not ending",\n68 : # )  # returns [\'testing\', \'ending\']\n',
        "linenos": "68",
        "language": "python",
        "code block comments": None,
        "source_path": "/Users/derhnyel/Documents/GitHub/projects/sani/example/example.py",
        "lined_block": '7:\n8:\n9:\n10:# SANI:mode=fix:subject=This is a comment:startline=11:endline=18\n11:class Test:\n12:    def __init__(self):\n13:        self.name = "Test"\n14:\n15:\n16:    def test1(self):\n17:        print("A documention block within Test class function test1 called with wrap")\n18:        return self.name\n19:\n20:    # debuggy_end_breakpoint\n21:\n22:    def test2(self):\n23:        print("An improve block within Test class function test2 called with wrap")\n24:        # raising an exception\n25:        try:\n26:            raise Exception("I Raised this exception . Now handle it and fix me ..")\n27:        except Exception as e:\n28:            print("I caught this myself")\n29:\n30:    @staticmethod\n31:\n32:    def test3():\n33:        print("A test block within Test class function test3 called with wrap ")\n34:        # raising an exception\n35:        # raise Exception("I Raised this exception . Now handle it and fix me ..")\n36:\n37:\n38:    def test4(self):\n39:        print("I am here for testing the fix mode")\n40:        return self\n41:\n42:\n43:# sani fix\n44:test = Test()\n45:test.test1()\n46:# test.test2()\n47:\n48:# sani fix-end\n49:\n50:\n51:#     set = 10\n52:#     print("The with statement is working fine")\n53:#     test.test3()\n54:import time\n55:\n56:test.test4()\n57:while True:\n58:    print("I am here for testing the fix mode")\n59:    time.sleep(2)\n60:    break\n61:\n62:\n63:\n',
        "source_list": [
            "from sani.debugger.debugger import Debugger\n",
            "\n",
            "# Debuggy.deactivate = False\n",
            "# Debuggy.__deactivate_hook = False\n",
            'debug = Debugger(name=__name__, stdout="example.txt", channel="iuio", linter="pylint")\n',
            "\n",
            'debug.breakpoint(mode="improve", subject="build an automatic scraper")\n',
            "\n",
            "\n",
            "# SANI:mode=fix:subject=This is a comment:startline=11:endline=18\n",
            "class Test:\n",
            "    def __init__(self):\n",
            '        self.name = "Test"\n',
            "\n",
            '    @debug.wrap(mode="document")\n',
            "    def test1(self):\n",
            '        print("A documention block within Test class function test1 called with wrap")\n',
            "        return self.name\n",
            "\n",
            "    # debuggy_end_breakpoint\n",
            '    @debug.wrap(mode="improve")\n',
            "    def test2(self):\n",
            '        print("An improve block within Test class function test2 called with wrap")\n',
            "        # raising an exception\n",
            "        try:\n",
            '            raise Exception("I Raised this exception . Now handle it and fix me ..")\n',
            "        except Exception as e:\n",
            '            print("I caught this myself")\n',
            "\n",
            "    @staticmethod\n",
            '    @debug.wrap(mode="ai_fn")\n',
            "    def test3():\n",
            '        print("A test block within Test class function test3 called with wrap ")\n',
            "        # raising an exception\n",
            '        # raise Exception("I Raised this exception . Now handle it and fix me ..")\n',
            "\n",
            '    @debug.wrap(mode="fix")\n',
            "    def test4(self):\n",
            '        print("I am here for testing the fix mode")\n',
            "        return self\n",
            "\n",
            "\n",
            "# sani fix\n",
            "test = Test()\n",
            "test.test1()\n",
            "# test.test2()\n",
            'debug.debug(1, 10, mode="document")\n',
            "# sani fix-end\n",
            "\n",
            '# with debug(mode="analyze") as debugger:\n',
            "#     set = 10\n",
            '#     print("The with statement is working fine")\n',
            "#     test.test3()\n",
            "import time\n",
            "\n",
            "test.test4()\n",
            "while True:\n",
            '    print("I am here for testing the fix mode")\n',
            "    time.sleep(2)\n",
            "    break\n",
            "\n",
            "\n",
            "debug.debugger_end_breakpoint()\n",
            "# sani fix-end\n",
            "# sani.regex(\n",
            "#     \"get a the words that end in 'ing' from this sentence\",\n",
            '#     "He has been leisurely testing the ending of the sentence but he is not sure if it is ending or not ending",\n',
            "# )  # returns ['testing', 'ending']\n",
        ],
    },
    "prompt": {
        "suggestions": {
            "lint_suggestions": '************* Module example\nexample.py:67:0: C0301: Line too long (114/100) (line-too-long)\nexample.py:1:0: C0114: Missing module docstring (missing-module-docstring)\nexample.py:11:0: C0115: Missing class docstring (missing-class-docstring)\nexample.py:16:4: C0116: Missing function or method docstring (missing-function-docstring)\nexample.py:22:4: C0116: Missing function or method docstring (missing-function-docstring)\nexample.py:27:15: W0718: Catching too general exception Exception (broad-exception-caught)\nexample.py:26:12: W0719: Raising too general exception: Exception (broad-exception-raised)\nexample.py:27:8: C0103: Variable name "e" doesn\'t conform to snake_case naming style (invalid-name)\nexample.py:27:8: W0612: Unused variable \'e\' (unused-variable)\nexample.py:32:4: C0116: Missing function or method docstring (missing-function-docstring)\nexample.py:38:4: C0116: Missing function or method docstring (missing-function-docstring)\nexample.py:54:0: C0413: Import "import time" should be placed at the top of the module (wrong-import-position)\nexample.py:54:0: C0411: standard import "import time" should be placed before "from sani.debugger.debugger import Debugger" (wrong-import-order)\n\n------------------------------------------------------------------\nYour code has been rated at 5.67/10 (previous run: 5.67/10, +0.00)\n\n',
            "linter": "pylint",
            "intended action": "build an automatic scraper",
        },
        "mode": "improve",
        "referer": None,
    },
}


callback(context)
