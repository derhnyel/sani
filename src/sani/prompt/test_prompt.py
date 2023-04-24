
from sani.prompt.base import SaniPromptTemplateBase


class SaniTestPromptTemplate(SaniPromptTemplateBase):
    """
    Custom prompt template for using Sani in fix mode
    """
    _minimum_inputs = [
       'imports', 'full_code', 'code_ast_dump', 'block_ast', 'subject', 'mode', 'language'
    ]

    def format(self, **kwargs):
        prompt = f"""
        Sani is an assistant used to test code written in {kwargs['language']}.

        As an assistant, Sani is able to use information regarding a piece of code to write unit tests. 
        This includes the source code, the abstract syntax tree of a block of code, comments and what the code is 
        intended for.

        Here's the information about the block of code:

        Code block: {kwargs['full_code']}
        Imports: {kwargs['imports']}
        Code Abstract Syntax Tree Dump: {kwargs['code_ast_dump']}
        Code block Abstract Syntax Tree Dump: {kwargs['block_ast']}
        Intended Function: {kwargs['subject']}
        """
        return prompt

    @property
    def _prompt_type(self):
        return "Sani tester"
