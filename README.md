# Sani 🤖⚙️😎

Hello there, I am `Sani`:
An advanced AI-powered tool for building better softwares. I integrate AI directly into your codebase by making it blend in with your prefered language syntax.
My name is derived from the `Hausa` word for knowledge, as i have access to a wide range of resources for energizing your codebase with ai also, I can analyze any codebase for issues and provide the best solution there is.

## Support Languages

- Python

## Installation

## Debugger

Sani-Debugger is an AI debugger designed to help developers quickly identify and fix bugs in their code.
Sani-Debugger can detect and isolate bugs in real-time, providing detailed information on the root cause and potential solutions.
With Sani-Debugger's help, developers can increase their productivity and deliver high-quality software products faster

### Modes

- `test`: Write `Test` for the code block and run it to check if it passes.
- `fix`: `Fix` errors and suggest making changes to the code block.
- `improve`: `Improve` code blocks with the help of lint,suggestions and comments and suggest changes to the code block.
- `document`: Write `Documentation` for the code block.
- `analyze`: Gives a detailed `Analysis` of the code block or error encountered.

### Usage

#### Methods

- `wrap` - A Decorator that wraps a function and debug what is within it.
- `breakpoint` - Called on any line and uses an `debugger_end_breakpoint` method to terminate. Captures codes between the two methods
- `context-manager(with)` - Uses the `with` statement and captures code block within that statement.
- `debug` - A method that takes in a start and endline and captures code between them.

Sample Usage:

```python
from sani.debugger import Debugger

debug = Debugger(__name__,stdout="test.txt", channel="io")
debug.breakpoint(mode="test", subject="build an automatic scraper")


class Test:
    def __init__(self):
        self.name = "Test"

    @debug.wrap(mode="document")
    def test1(self):
        print("A documention block within Test class function test1 called with wrap")
        return self.name

    # debuggy_end_breakpoint
    @debug.wrap(mode="improve")
    def test2(self):
        print("An improve block within Test class function test2 called with wrap")
        # raising an exception and handle it
        try:
            raise Exception("I Raised this exception . Now handle it and fix me ..")
        except Exception as e:
            print("I caught this myself")

    @staticmethod
    @debug.wrap(mode="analyze")
    def test3():
        print("A test block within Test class function test3 called with wrap ")
        # raising an exception
        # raise Exception("I Raised this exception . Now handle it and fix me ..")

    @debug.wrap(mode="fix")
    def test4(self):
        print("I am here for testing the fix mode")
        return self


test = Test()
test.test1()
test.test2()
debug.debug(1, 10, mode="document")

with debug(mode="analyze") as debugger:
    set = 10
    print("The with statement is working fine")
    test.test3()
test.test4()
debug.debugger_end_breakpoint()

```

Output in Debug Terminal

```bash
2023-04-20 11:09:20,202::DEBUG::sani.debugger::DEBUGGer='activated'
2023-04-20 11:09:20,202::DEBUG::sani.debugger::method='BREAKPOINT'::mode='TEST'::startline=4::endline=49::sync=True::subject='build an automatic scraper'
2023-04-20 11:09:20,204::DEBUG::sani.debugger::method='WRAP'::mode='DOCUMENT'::startline=7::endline=38::sync=True::subject='None'
2023-04-20 11:09:20,204::DEBUG::sani.debugger::DISPATCHED `successfully` to the cli-engine for mode='DOCUMENT'::startline=7::endline=38::referer='None'
A documention block within Test class function test1 called with wrap
2023-04-20 11:09:20,204::DEBUG::sani.debugger::method='WRAP'::mode='IMPROVE'::startline=7::endline=38::sync=True::subject='None'
2023-04-20 11:09:20,204::DEBUG::sani.debugger::DISPATCHED `successfully` to the cli-engine for mode='IMPROVE'::startline=7::endline=38::referer='None'
An improve block within Test class function test2 called with wrap
I caught this myself
2023-04-20 11:09:20,204::DEBUG::sani.debugger::'SYNCHRONIZATION-CALL' mode='DOCUMENT'::current-startline=1::current-endline=10::previous-startline=7::previous-endline=38
2023-04-20 11:09:20,205::DEBUG::sani.debugger::method='SYNC'::mode='DOCUMENT'::startline=1::endline=38::sync=True
2023-04-20 11:09:20,205::DEBUG::sani.debugger::DISPATCHED `successfully` to the cli-engine for mode='DOCUMENT'::startline=1::endline=38::referer='None'
2023-04-20 11:09:20,205::DEBUG::sani.debugger::method='DEBUG'::mode='DOCUMENT'::startline=1::endline=10::sync=True::subject='None'
2023-04-20 11:09:20,205::DEBUG::sani.debugger::DISPATCHED `successfully` to the cli-engine for mode='ANALYZE'::startline=44::endline=47::referer='None'
2023-04-20 11:09:20,205::DEBUG::sani.debugger::method='WITH'::mode='ANALYZE'::startline=44::endline=47::sync=True::subject='None'
The with statement is working fine
2023-04-20 11:09:20,206::DEBUG::sani.debugger::method='WRAP'::mode='AI_FN'::startline=7::endline=38::sync=True::subject='None'
2023-04-20 11:09:20,206::DEBUG::sani.debugger::DISPATCHED `successfully` to the cli-engine for mode='AI_FN'::startline=7::endline=38::referer='None'
A test block within Test class function test3 called with wrap 
2023-04-20 11:09:20,206::DEBUG::sani.debugger::'ENDWITH'::startline=44::exc_type=None::exc_value=None::traceback=None
2023-04-20 11:09:20,206::DEBUG::sani.debugger::method='WRAP'::mode='FIX'::startline=7::endline=38::sync=True::subject='None'
I am here for testing the fix mode
2023-04-20 11:09:20,206::DEBUG::sani.debugger::DISPATCHED `successfully` to the cli-engine for mode='IMPROVE'::startline=7::endline=38::referer='fix'
2023-04-20 11:09:20,207::DEBUG::sani.debugger::'ENDBREAKPOINT'::endline=49
2023-04-20 11:09:20,207::DEBUG::sani.debugger::DISPATCHED `successfully` to the cli-engine for mode='TEST'::startline=4::endline=49::referer='None'
```

## Channels

## Features Update

- ♻️ Add a regex function that takes a description or what to extract and a sample string where that can be found and returns a list of matches.

```python
import sani
sani.regex(
    "get a the words that end in 'ing' from this sentence",
    "He has been leisurely testing the ending of the sentence but he is not sure if it is ending or not ending",
)  # returns ['testing', 'ending']
```

- ♻️ Add ai functions.

```python
import sani
@sani.ai_fn(description="A function that takes inputs and returns numbers")
def add_two_numbers(a,b):
    """
    Add two numbers together
    """
# Gives you an output from the function
```

- ⚙️ Add a prompt builder ... build prompts with suggestions from pylint/flack8 and comments
- 🖥️ Tui /cli build with textual.
- ⚙️ Add gpt support.
- ⚙️ Add comments parsing support for various languages.


## Inspirations

- [Auto-Gpt]()
- [Mavin-AI]()