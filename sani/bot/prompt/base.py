from abc import ABC, abstractmethod
from typing import Union
from langchain.prompts import StringPromptTemplate
from pydantic import BaseModel
from .string_templates import DEFAULT_TEMPLATE


class GenericPromptTemplateBase(StringPromptTemplate, BaseModel, ABC):
    """
    A custom prompt template that takes in the mode sani operates in, it's role and responsibilities. 
    """
    personality: Union[str, None] = None
    instruction: Union[str, None] = None
    response_format: Union[str, None] = None
    template_str: str = DEFAULT_TEMPLATE

    @abstractmethod
    def format(self, **kwargs):
        """
        Virtual function to be implemented by all child SaniPromptTemplates.
        This method converts a prompt template to a string that can be fed to the language model
        """
        raise NotImplementedError()

    @property
    def _prompt_type(self):
        """
        Virtual function describing the prompt type
        """
        raise NotImplementedError()
