
from sani.prompt.base import SaniPromptTemplateBase


class SaniFixPromptTemplate(SaniPromptTemplateBase):
    """
    Custom prompt template for using Sani in fix mode
    """
    _minimum_inputs = [
        'exception_type','exception_message', 'full_traceback',  'imports', 'full_code', 
        'code_ast_dump', 'block_ast', 'subject', 'lint_suggestions', 'mode', 'language'
    ]

    def format(self, **kwargs):
        prompt = f"""
        Sani is an assistant used to {kwargs['mode']} code written in {kwargs['language']}.

        As an assistant, Sani is able to recieve information regarding a piece of code. This includes tracebacks,
        source code, the abstract syntax tree of a block of code, comments, lint suggestions and what the code is intended for.
        Sani should also be able to use this information to improve the given piece of code. Improvements should include making the
        code understandable, run in less time, use less memory and adhere to PEP8 standard.

        Here's the information about the block of code:

        Exception type: {kwargs['exception_type']}
        Exception message: {kwargs['exception_message']}
        Traceback: {kwargs['full_traceback']}
        Code block: {kwargs['full_code']}
        Imports: {kwargs['imports']}
        Code Abstract Syntax Tree Dump: {kwargs['code_ast_dump']}
        Code block Abstract Syntax Tree Dump: {kwargs['block_ast']}
        Lint suggestions: {kwargs['lint_suggestions']}
        Intended Function: {kwargs['subject']}
        """
        return prompt

    @property
    def _prompt_type(self):
        return "Sani fixer"
