from abc import ABC, abstractmethod
from langchain.prompts import StringPromptTemplate
from pydantic import BaseModel, validator

class SaniPromptTemplateBase(StringPromptTemplate, BaseModel, ABC):
    """
    A custom prompt template that takes in the mode sani operates in, it's role and responsibilities
    """
    _minimum_inputs = ['full_code', 'code_ast_dump', 'block_ast', 'subject']

    @validator("input_variables")
    def validate_input_variables(cls, inputs, values):
        """ Validate that the input variables are correct. """
        print(inputs)
        values['input_variables'] = inputs # bugfix
        if not all(x in inputs for x in cls._minimum_inputs):
            raise ValueError(
                f"Sani's prompt must have the following inputs: {cls._minimum_inputs}\n Your inputs: {inputs}"
            )
        return inputs
    
    @abstractmethod
    def format(self, **kwargs):
        """
        Virtual function to be implemented by all child SaniPromptTemplates
        """
        raise NotImplementedError()

    # @abstractmethod
    # def _build_prompt(self, **kwargs):
    #     """
    #     Virtual function to be implemented by all child SaniPromptTemplates
    #     """
    #     raise NotImplementedError()

    @property
    def _prompt_type(self):
        """
        Virtual function describing the prompt type
        """
        raise NotImplementedError()
