from subprocess import PIPE, Popen
from threading import Thread
from queue import Queue
import sys
import os
from sani.utils.custom_types import Os, Language, List, Executables, Tuple, types
from pathlib import Path
from sani.core.config import Config
from sani.utils.exception import UnsupportedError

config = Config()


class ScriptRun:
    def __init__(self, file_path, executable: str = None, *args):
        self.args = args
        self.executable = executable
        self.file_path: Path = Path(file_path)
        if not os.path.isfile(file_path):
            raise FileNotFoundError(file_path)
        self.language = self.__get_language()
        if not self.language:
            raise UnsupportedError(f"Language not supported for {file_path}")
        command: List[str] = [file_path] + list(self.args)
        self.command: List[str] = (
            Executables.get_custom_exec(executable, command)
            if executable
            else Executables.get(self.language, command)
        )

    def __get_language(self) -> Language:
        self.extension = self.file_path.suffix
        language = config.SOURCE_LANGUAGE_MAP.get(self.extension)
        return language

    def __is_compiled(self):
        return self.language in config.compiled_languages

    def run(self) -> Tuple[str, str]:
        return self.__listen(self.command)

    def __listen(self, command) -> Tuple[str, str]:
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
        return (output, errors)

    @staticmethod
    def read(pipe: PIPE, funcs: List[types.FunctionType]):
        """
        Reads and pushes piped output to a shared queue and appropriate lists.
        """
        for line in iter(pipe.readline, b""):
            for func in funcs:
                func(line.decode("utf-8"))
        pipe.close()

    @staticmethod
    def write(get: types.FunctionType):
        """
        Pulls output from shared queue and prints to terminal.
        """
        for line in iter(get, None):
            print(line)
