from abc import ABC, abstractmethod
import os
from typing import Union, Callable, List, Dict
from langchain.chat_models import ChatOpenAI
from langchain.schema import LLMResult
from sani.bot.prompt import GenericSaniPrompt


class BaseBot(ABC):
    # A bot has a prompt, chain, mode and agents
    """
    Abstract Bot Class to be implemented by all Bots
    """

    def __init__(self, *args, api_key=None, temperature=0, **kwargs) -> None:
        self.args = args
        self.kwargs = kwargs
        self.temperature: float = temperature
        self.llm: ChatOpenAI = None
        self.message: List[Dict[str, str]] = None
        self.prompt: str = None
        self.input: str = None
        if api_key:
            os.environ["OPENAI_API_KEY"] = api_key
        self.model_name: str = None

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

    def dispatch(
        self,
        message: str = None,
        llm: ChatOpenAI = None,
        information: Dict[str, Dict[str, str]] = None,
        append_message: bool = False,
        append_result: bool = False,
        rebuild_prompt: bool = False,
    ) -> str:
        """
        Runs the llm for a particular bot.

        Different bots can use different llms but this method provides a general interface
        for dispatching any type of Bot.
        Can be overriden if necessary.
        """

        if rebuild_prompt:
            self._build_prompt()

        message = (
            self.message + self.prepare_messages([{"role": "user", "content": message}])
            if message
            else self.message
        )

        if information:
            context = self._unpack_obj(information)
            prompt = GenericSaniPrompt(
                personality=self.personality,
                instruction=self.instruction,
                bot_information=context,
                response_format=self.response_format,
                input_variables=[],
            )
            message = f"{message}\n{prompt.bot_information}"

        if append_message:
            self.message = message
        # messages_repr = "\n".join(repr(m) for m in self.message)
        # logger.info(f"Dispatching messages: {messages_repr}")
        llm = llm or self.llm
        result: LLMResult = llm.generate(messages=[message], stop=["</stop>"])
        if append_result:
            self.message = self.message + self.prepare_messages(
                [{"role": "bot", "content": result.generations[0][0].text}]
            )
        return result.generations[0][0].text
