import psutil  # https://psutil.readthedocs.io/en/latest/
from sani.utils.custom_types import List, Tuple
import inspect
from enum import Enum
import time
import sys
import os
import subprocess
import types
import distro
import platform  # https://docs.python.org/3/library/platform.html
import resource  # https://docs.python.org/3/library/resource.html


class OsProcess:
    """
    Utilities for process management and monitoring
    """

    def monitor_process(self, process_id: int) -> bool:
        """
        Checks if a process is still alive
        """
        try:
            while self.get_process(process_id):
                time.sleep(1)
        except psutil.NoSuchProcess:
            return False

    def get_process(self, process_id: int) -> psutil.Process:
        """
        Get process object of a process
        """

        return psutil.Process(process_id)

    def get_pid_of_current_process(self) -> int:
        """
        Get process id of the current process
        """
        return os.getpid()

    def get_pid_by_name(
        self, os, name: str
    ) -> str:  # Fix this when you move os to config.. remove it as a parameter
        """
        Get process id of a process by its name
        """
        try:
            output = b""
            if os == Os.windows32 or os == Os.windows64:
                output = subprocess.check_output(
                    [
                        "wmic",
                        "process",
                        "where",
                        f"name='{name}'",
                        "get",
                        "processid",
                    ]
                )

            elif os == Os.linux or os == Os.linux2:
                output = subprocess.check_output(["pidof", name])
            elif os == Os.mac:
                cmd = "ps aux | grep -v grep |grep -i " + name + " | awk '{print $2;}'"
                ps = subprocess.Popen(
                    cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT
                )
                output = ps.communicate()[0]
        except Exception as e:
            pass
        return output.decode("utf-8")


class Os(str, Enum):
    """
    Operating Systems Enum
    """

    linux = "linux"
    linux2 = "linux2"
    ubuntu = "ubuntu"
    mac = "darwin"
    windows32 = "win32"
    windows64 = "win64"


class TerminalCommand(str, Enum):
    """
    Commands to spawn new terminal session for
    different Tty Terminals on different Operating Systems
    """

    osascript = """osascript -e 'tell application "Terminal" to do script "{command}"'"""  # 'osascript -e \'tell application "Terminal" do script "{command}"\''
    gnome = 'gnome-terminal --command="{command}"'
    xterm = "xterm -e '{command}' &"
    cmd = "start cmd /c {command}"
    powershell = 'start powershell "{command}"'
    command = "command {command}"
    echo2temp = 'echo "{command}" > /tmp/tmp.sh ; chmod +x /tmp/tmp.sh ; open -a Terminal -F -n -g /tmp/tmp.sh ; sleep 2 ; rm /tmp/tmp.sh'


class RuntimeInfo:
    """
    RuntimeInfo class to get runtime
    information about the current process
    """

    def __init__(self) -> None:
        self.os = self.__get_os()
        self.distro = self.__get_distro()

    def __get_os(self) -> str:
        """
        Get the current operating system
        """
        return sys.platform

    def __get_distro(self) -> Tuple[str, str, str]:
        """
        Get the current linux distribution
        """
        return distro.linux_distribution()

    def get_stack(self) -> List[inspect.FrameInfo]:
        """
        Get the stack frames of the current process
        """
        return inspect.stack()

    def get_current_frame(self) -> types.FrameType:
        """
        Get the current frame of the current process
        """
        return inspect.currentframe()

    def get_module_members(self, module):
        """
        Get module members of the current process
        """
        return inspect.getmembers(module)

    def get_stack_caller_frame(self) -> inspect.FrameInfo:
        """
        Get the caller frame of the current process
        """
        caller_stack = self.get_stack()[-1]
        return caller_stack

    def get_module(self, module):
        """
        Get module of the current process
        """
        return inspect.getmodule(module)
