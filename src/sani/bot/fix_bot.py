import os
from langchain.chains import LLMChain
from langchain.llms import OpenAI
from langchain.chat_models import ChatOpenAI
from sani.prompt.fix_prompt import SaniFixPromptTemplate
from sani.bot.base import BaseBot

class FixBot(BaseBot):
    """
    Derived FixBot class that inherits from BaseBot

    Used for fixing code errors
    """
    def __init__(self, *args, model_name=None, **kwargs) -> None:   
        super().__init__(*args, **kwargs)
        if model_name:
            self.model_name = model_name
        self._build_prompt()
        self._construct_chain()
        

    def _build_prompt(self):
        prompt_variables = [
            "exception_type", "exception_message", "exception_message", "full_traceback", 
            "full_code", "imports", "code_ast_dump", "block_ast", "lint_suggestions", "subject",
            "mode", "language"
        ]
        self.prompt = SaniFixPromptTemplate(input_variables=prompt_variables)

    def _construct_chain(self):
        if not self.prompt:
            raise TypeError("Must build a prompt before constructing a chain")
        
        if not os.getenv('OPENAI_API_KEY'):
            raise TypeError(
                """
                Please provide OPENAI_API_KEY as an environment variable or specify as api_key
                keyword argument in bot instance
                """
            )
        self.chain = LLMChain(llm=OpenAI(temperature=self.temperature, model_name=self.model_name), prompt=self.prompt)
