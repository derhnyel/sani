from sani.utils.custom_types import (
    JsonType,
    Tuple,
    Enum,
    abstractmethod,
    ABC,
    io_object,
    Dict,
)
import time
from json import dumps, loads
import tempfile


class BaseCommChannel(ABC):
    """
    An abstract class to be inherited by all comm channels
    must have a `send` ,`connect` ,`close` and `receive` methods.
    """

    channel_name: str = None
    channel_type: str = None

    channel_credential: JsonType = None

    def __init__(self, *args, **kwargs) -> None:
        self.args = args
        self.kwargs = kwargs

    @abstractmethod
    def connect(self, *args, **kwargs):
        """
        Connect to the comm channel
        """
        raise NotImplementedError()

    @abstractmethod
    def send(self, message=None, *args, **kwargs):
        """
        Send a message to the comm channel
            Parameters:
                message (string): message to be sent to the comm channel.
        """
        raise NotImplementedError()

    @abstractmethod
    def receive(self, *args, **kwargs):
        """
        Receive a message from the comm channel
        """
        raise NotImplementedError()

    @abstractmethod
    def close(self, *args, **kwargs):
        """
        Close the comm channel
        """
        raise NotImplementedError()


class IoCommChannel(BaseCommChannel):
    """
    The File Based IO communication channel for debuggy and the cli-engine
    """

    channel_name = "iocommunicationchannel"
    channel_type = "io"

    def __init__(self, *args, **kwargs) -> None:
        from io import TextIOWrapper
        import sys

        self.TextIOWrapper = TextIOWrapper
        self.sys = sys

        super().__init__(*args, **kwargs)
        self.default_stdin = sys.stdin
        self.default_stdout = sys.stdout
        self.default_stderr = sys.stderr
        self.connect()
        self.channel_credential = dumps(
            {
                "stdin": self.stdin[1].path,
                "stdout": self.stdout[1].path,
                "stderr": self.stderr[1].path,
            }
        )

    def send(self, message: Dict = None):
        """
        Send a message to the io comm channel
            Parameters:
                message (string): message to be sent to the comm channel.
        """
        message = dumps(message)
        self.redirect(stdout=True)
        if self.sys.stdout.writable():
            print(message, flush=True)
        self.redirect(stdout=False)

    def connect(self):
        stdin = self.kwargs.get("stdin") or tempfile.NamedTemporaryFile()
        stdout = self.kwargs.get("stdout") or tempfile.NamedTemporaryFile()
        stderr = self.kwargs.get("stderr") or tempfile.NamedTemporaryFile()
        self.stdin: Tuple[tempfile._TemporaryFileWrapper, io_object] = (
            stdin,
            self.get_io(stdin if isinstance(stdin, str) else stdin.name, mode="r"),
        )
        self.stdout: Tuple[tempfile._TemporaryFileWrapper, io_object] = (
            stdout,
            self.get_io(stdout if isinstance(stdout, str) else stdout.name),
        )
        self.stderr: Tuple[tempfile._TemporaryFileWrapper, io_object] = (
            stderr,
            self.get_io(stdout if isinstance(stdout, str) else stdout.name),
        )

    def close(self):
        self.stdin[1].stream.close()
        self.stdout[1].stream.close()
        self.stderr[1].stream.close()
        self.redirect(stdin=False, stdout=False, stderr=False)

    def receive(self, callback: callable = None):
        """
        Receive a message from the io comm channel
        """
        self.redirect(stdin=True)
        callback: callable = callback or self.callback

        def stdin_monitor():
            while self.sys.stdin.readable():
                try:
                    message = input()
                    if message:
                        message = loads(message)
                        callback(message)
                        yield message
                except EOFError:
                    time.sleep(1)

        return stdin_monitor()

    def callback(self, message: str):
        """
        Callback for the io comm channel .
        """

    def redirect(self, stdin: bool = False, stdout: bool = False, stderr: bool = False):
        """
        Redirect the standard streams to the comm channel
        """
        self.sys.stdin = self.stdin[1].stream if stdin else self.default_stdin
        self.sys.stdout = self.stdout[1].stream if stdout else self.default_stdout
        self.sys.stderr = self.stderr[1].stream if stderr else self.default_stderr

    def get_io(self, path: str, mode: str = "w") -> io_object:
        """
        Get a Text input/output warpper object
        """
        io_stream: self.TextIOWrapper = open(
            path,
            mode,
        )
        return io_object(path, io_stream)


class Channel(Enum):
    """
    Channels Enum
    """

    io = IoCommChannel
    # socket = WebSocketCommChannel
    # rmq = RabbitMqCommChannel
    # redis = RedisCommChannel
    # server = ServerCommChannel
