from abc import ABC, abstractmethod
import os
from typing import Dict, Any
from langchain.chains import LLMChain


class BaseBot(ABC):
    # A bot has a prompt, chain, mode and agents
    """
    Abstract Bot Class to be implemented by all Bots
    """
    def __init__(self, *args, api_key=None, temperature=0.7, **kwargs) -> None:
        self.args = args
        self.kwargs = kwargs
        self.temperature: float = temperature
        self.chain: LLMChain = None
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

    @abstractmethod
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

    def dispatch(self, prompt_object: Any):
        """
        Runs the chain for a particular bot.

        Different bots have different chains but this method provides a general interface
        for dispatching any type of Bot
        """
        if not self.chain:
            raise TypeError("Please construct a chain before trying to dispatch a bot")
        prompt_data = self._unpack_obj(prompt_object)
        return self.chain.run(**prompt_data)

    def _unpack_obj(self, debug_data: Dict):
        """
        Unpacks and filters the data obtained from a Debugger session
        """
        prompt_data = {
            'mode': debug_data['prompt']['mode'], # Add to context builder
            # 'language': debug_data['language'], # Add to context builder
            'language': 'python',
            "exception_type": debug_data['execution']['traceback']['exception_type'],
            "exception_message": debug_data['execution']['traceback']['exception_message'],
            "full_traceback": debug_data['execution']['traceback']['full_traceback'],
            "output": debug_data['execution']['output'],
            "error_line":  debug_data['execution']['traceback']['error_line'],
            "status": debug_data['execution']['status'],
            "subject": debug_data['prompt']['suggestions']['subject'],
            "startline": debug_data['source']['startline'],
            "endline": debug_data['source']['endline'],
            "full_code": debug_data['source']['code'],
            "debug_session_code_block": debug_data['source']['block'],
            "imports": debug_data['source']['imports'],
            "lined_code": debug_data['source']['lined_code'],
            "linenos": debug_data['source']['linenos'],
            "block_ast": debug_data['source']['block_ast'],
            "code_ast_dump": debug_data['source']['code_ast_dump'],
            "lint_suggestions": debug_data['prompt']['suggestions']['linter'],
            # comments should be None instead of null
            "full_code_comments": debug_data['prompt']['suggestions']['comments'],
            "debug_session_block_comments":  debug_data['prompt']['suggestions']['block_comments']
        }
        return prompt_data
