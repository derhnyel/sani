from typing import Dict
from langchain.llms import OpenAI
from sani.bot.prompt.generic import GenericSaniPrompt
from sani.bot.bots.base import BaseBot
from sani.utils.custom_types import Context as ct
from sani.bot.prompt.string_templates import (
    FIX_MODE_INSTRUCTIONS, FIX_MODE_PERSONALITY, FIX_MODE_RESPONSE_FORMAT,
    TEST_MODE_INSTRUCTIONS, TEST_MODE_PERSONALITY, TEST_MODE_RESPONSE_FORMAT,
    IMPROVE_MODE_INSTRUCTIONS, IMPROVE_MODE_PERSONALITY, IMPROVE_MODE_RESPONSE_FORMAT,
    DOCUMENT_MODE_INSTRUCTIONS, DOCUMENT_MODE_PERSONALITY, DOCUMENT_MODE_RESPONSE_FORMAT,
    ANALYZE_MODE_INSTRUCTIONS, ANALYZE_MODE_PERSONALITY, ANALYZE_MODE_RESPONSE_FORMAT
)


class GenericSaniBot(BaseBot):
    """
    A Generic bot for sani that can be operated in all modes.
    """
    def __init__(self, context, mode, *args, model_name=None, **kwargs) -> None:   
        super().__init__(*args, **kwargs)
        if model_name:
            self.model_name = model_name

        self.mode = mode
        valid_modes = ['fix', 'improve', 'test', 'document', 'analyze']
        if self.mode not in valid_modes:
            raise ValueError(f'Sani must operate in one of the following modes: {valid_modes}')

        self.prompt_templates = {
            'fix': {
                'personality': FIX_MODE_PERSONALITY, 
                'instructions': FIX_MODE_INSTRUCTIONS,
                'response_format': FIX_MODE_RESPONSE_FORMAT
            },
            'test': {
                'personality': TEST_MODE_PERSONALITY, 
                'instructions': TEST_MODE_INSTRUCTIONS,
                'response_format': TEST_MODE_RESPONSE_FORMAT
            },
            'improve': {
                'personality': IMPROVE_MODE_PERSONALITY, 
                'instructions': IMPROVE_MODE_INSTRUCTIONS,
                'response_format': IMPROVE_MODE_RESPONSE_FORMAT
            },
            'document': {
                'personality': DOCUMENT_MODE_PERSONALITY, 
                'instructions': DOCUMENT_MODE_INSTRUCTIONS,
                'response_format': DOCUMENT_MODE_RESPONSE_FORMAT
            },
            'analyze': {
                'personality': ANALYZE_MODE_PERSONALITY, 
                'instructions': ANALYZE_MODE_INSTRUCTIONS,
                'response_format': ANALYZE_MODE_RESPONSE_FORMAT
            }
        }
        self.llm = OpenAI(temperature=self.temperature, model_name=self.model_name)
        self.input = context
        self._build_prompt()

    def _build_prompt(self):
        """
        Builds the prompt for a generic Sani bot
        """
        code_information = self._unpack_obj(self.input)
        language=code_information['language']
        personality = self.prompt_templates[self.mode]['personality'].format(language)
        instruction = self.prompt_templates[self.mode]['instructions']
        response_format = self.prompt_templates[self.mode]['response_format']

        self.prompt = GenericSaniPrompt(
            personality=personality,
            instruction=instruction,
            bot_information=code_information,
            response_format=response_format,
            input_variables=[]
        )

    def get_prompt(self):
        """
        Returns the formatted input prompt string
        """
        return self.prompt.format()

    def _unpack_obj(self, input_context: Dict):
        """
        Unpacks the context dictionary containing an additional info a bot might need
        to fulfill it's instructions
        """
        prompt_data = {
            'language': input_context[ct.source.value][ct.language.value],
            'mode': input_context[ct.prompt.value][ct.mode.value],
            'output': input_context[ct.execution.value][ct.output.value],
            'intended action': input_context[ct.prompt.value][ct.suggestions.value][ct.subject.value],
            'startline': input_context[ct.source.value][ct.startline.value],
            'endline': input_context[ct.source.value][ct.endline.value],
            'full source code': input_context[ct.source.value][ct.code.value],
            'full source code with line numbers': input_context[ct.source.value][ct.lined_code.value],
            'code block': input_context[ct.source.value][ct.block.value],
        }
        return prompt_data
