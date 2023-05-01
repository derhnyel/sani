from typing import Dict
from langchain.llms import OpenAI
from sani.bot.bots.generic import GenericSaniBot
from sani.utils.custom_types import Context as ct


class FixBot(GenericSaniBot):
    """
    Derived FixBot class that inherits from GenericSaniBot

    Used for fixing code errors
    """
    def __init__(self, context, *args, model_name=None, **kwargs) -> None:
        super().__init__(context, mode='fix', model_name=model_name, *args, **kwargs)

    def _unpack_obj(self, input_context: Dict):
        base_fields = super()._unpack_obj(input_context)
        additional_fields = {
            'exception_type': input_context[ct.execution.value][ct.traceback.value][ct.exception_type.value],
            'exception_message': input_context[ct.execution.value][ct.traceback.value][ct.exception_message.value],
            'full_traceback': input_context[ct.execution.value][ct.traceback.value][ct.full_traceback.value],
            'error line':  input_context[ct.execution.value][ct.traceback.value][ct.error_line.value],
        }
        prompt_data = {**base_fields, **additional_fields}
        return prompt_data


class ImproveBot(GenericSaniBot):
    """
    Derived Bot class that inherits from GenericSaniBot

    Used for improving code
    """
    def __init__(self, context, *args, model_name=None, **kwargs) -> None:
        super().__init__(context, mode='improve', model_name=model_name, *args, **kwargs)

    def _unpack_obj(self, input_context: Dict):
        base_fields = super()._unpack_obj(input_context)
        additional_fields = {
            'exception_type': input_context[ct.execution.value][ct.traceback.value][ct.exception_type.value],
            'exception_message': input_context[ct.execution.value][ct.traceback.value][ct.exception_message.value],
            'full_traceback': input_context[ct.execution.value][ct.traceback.value][ct.full_traceback.value],
            'output': input_context[ct.execution.value][ct.output.value],
            'error line':  input_context[ct.execution.value][ct.traceback.value][ct.error_line.value],
            'linter':input_context[ct.prompt.value][ct.suggestions.value][ct.linter.value],
            'linter suggestions': input_context[ct.prompt.value][ct.suggestions.value][ct.lint_suggestions.value],
        }
        prompt_data = {**base_fields, **additional_fields}
        return prompt_data


class TestBot(GenericSaniBot):
    """
    Derived Bot class that inherits from GenericSaniBot

    Used for writing tests for code
    """
    def __init__(self, context, *args, model_name=None, **kwargs) -> None:
        super().__init__(context, mode='test', model_name=model_name, *args, **kwargs)

    def _unpack_obj(self, input_context: Dict):
        prompt_data = super()._unpack_obj(input_context)
        return prompt_data


class DocumentBot(GenericSaniBot):
    """
    Derived Bot class that inherits from GenericSaniBot

    Used for writing documentation for code blocks
    """
    def __init__(self, context, *args, model_name=None, **kwargs) -> None:
        super().__init__(context, mode='document', model_name=model_name, *args, **kwargs)

    def _unpack_obj(self, input_context: Dict):
        prompt_data = {
            'language': input_context[ct.source.value][ct.language.value],
            'intended action': input_context[ct.prompt.value][ct.suggestions.value][ct.subject.value],
            'startline': input_context[ct.source.value][ct.startline.value],
            'endline': input_context[ct.source.value][ct.endline.value],
            'code block': input_context[ct.source.value][ct.block.value],
        }
        return prompt_data

class AnalyzeBot(GenericSaniBot):
    """
    Derived Bot class that inherits from GenericSaniBot

    Used for analyzing code blocks
    """
    def __init__(self, context, *args, model_name=None, **kwargs) -> None:
        super().__init__(context, mode='analyze', model_name=model_name, *args, **kwargs)

    def _unpack_obj(self, input_context: Dict):
        base_fields = super()._unpack_obj(input_context)
        additional_fields = {
            'exception_type': input_context[ct.execution.value][ct.traceback.value][ct.exception_type.value],
            'exception_message': input_context[ct.execution.value][ct.traceback.value][ct.exception_message.value],
            'full_traceback': input_context[ct.execution.value][ct.traceback.value][ct.full_traceback.value],
            'output': input_context[ct.execution.value][ct.output.value],
            'error line':  input_context[ct.execution.value][ct.traceback.value][ct.error_line.value],
        }
        prompt_data = {**base_fields, **additional_fields}
        return prompt_data
    
    