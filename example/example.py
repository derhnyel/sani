from sani.debugger.debugger import Debugger

# Debuggy.deactivate = False
# Debuggy.__deactivate_hook = False
debug = Debugger(
    name=__name__, stdout="./example/example.txt", channel="iuio", linter="pylint"
)

debug.breakpoint(mode="test", subject="build an automatic scraper")


# SANI:mode=fix:subject=This is a comment:startline=11:endline=18
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
        # raising an exception
        try:
            raise Exception("I Raised this exception . Now handle it and fix me ..")
        except Exception as e:
            print("I caught this myself")

    @staticmethod
    @debug.wrap(mode="ai_fn")
    def test3():
        print("A test block within Test class function test3 called with wrap ")
        # raising an exception
        # raise Exception("I Raised this exception . Now handle it and fix me ..")

    @debug.wrap(mode="fix")
    def test4(self):
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
