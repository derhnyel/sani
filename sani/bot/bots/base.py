from abc import ABC, abstractmethod
import os
from typing import Union, Callable


class BaseBot(ABC):
    # A bot has a prompt, chain, mode and agents
    """
    Abstract Bot Class to be implemented by all Bots
    """
    def __init__(self, *args, api_key=None, temperature=0, **kwargs) -> None:
        self.args = args
        self.kwargs = kwargs
        self.temperature: float = temperature
        self.llm: Union[Callable, None] = None
        self.prompt: str = None
        if api_key:
            os.environ['OPENAI_API_KEY'] = api_key
        self.model_name: str = 'text-davinci-003'

    @property
    def temperature(self):
        """
        Getter for temperature value
        """
        return self._temperature

    @temperature.setter
    def temperature(self, value: int):
        """
        Setter for temperature value
        """
        self._temperature = value

    def _construct_chain(self):
        """
        Pure virtual method for constructing the chain for each bot
        """
        raise NotImplementedError()
    
    @abstractmethod
    def _build_prompt(self):
        """
        Pure virtual method for building the prompt for each bot
        """
        raise NotImplementedError()

    def dispatch(self):
        """
        Runs the llm for a particular bot.

        Different bots can use different llms but this method provides a general interface
        for dispatching any type of Bot.
        Can be overriden if necessary.
        """
        return self.llm(self.prompt.format())