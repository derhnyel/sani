import time
"""
Module docstring: This module is an example of building an automatic scraper using the Debugger class.
"""
from sani.debugger.debugger import Debugger

# Debuggy.deactivate = False
# Debuggy.__deactivate_hook = False
debug = Debugger(name=__name__, stdout="example.txt", channel="iuio", linter="pylint")

debug.breakpoint(mode="improve", subject="build an automatic scraper")


# SANI:mode=fix:subject=This is a comment:startline=11:endline=18
class Test:
    """Class representing a Test object."""
    def __init__(self):
        self.name = "Test"

    @debug.wrap(mode="document")
    def test1(self):
        """Test method 1 with a documentation block."""
        print("A documention block within Test class function test1 called with wrap")
        return self.name

    # debuggy_end_breakpoint
    @debug.wrap(mode="improve")
    def test2(self):
        """Test method 2 with an improvement block."""
        print("An improve block within Test class function test2 called with wrap")
        # raising an exception
        try:
            raise ValueError("I Raised this exception. Now handle it and fix me.")
            print("I caught this myself")
        except Exception as e:
            print(e)

    @staticmethod
    @debug.wrap(mode="ai_fn")
    def test3():
        """Test method 3 with a test block."""
        print("A test block within Test class function test3 called with wrap ")
        # raising an exception
        # raise Exception("I Raised this exception . Now handle it and fix me ..")

    @debug.wrap(mode="fix")
    def test4(self):
        """Test method 4 for testing the fix mode."""
        print("I am here for testing the fix mode")
        return self


# sani fix
test = Test()
test.test1()
# test.test2()
debug.debug(1, 10, mode="document")
# sani fix-end

# with debug(mode="analyze") as debugger:
#     set = 10
#     print("The with statement is working fine")
#     test.test3()
import time

test.test4()
while True:
    print("I am here for testing the fix mode")
    time.sleep(2)
    break


debug.debugger_end_breakpoint()
# sani fix-end
# sani.regex(
#     "get a the words that end in 'ing' from this sentence",
#     "He has been leisurely testing the ending of the sentence but he is not sure if it is ending or not ending",
# )  # returns ['testing', 'ending']
