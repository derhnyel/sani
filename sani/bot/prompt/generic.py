from typing import Dict
from pydantic import validator
from jinja2 import Template
from sani.bot.prompt.base import GenericPromptTemplateBase


class GenericSaniPrompt(GenericPromptTemplateBase):
    """
    Custom prompt template for using Sani in fix, test, improve, document and analyze mode
    """

    bot_information: Dict
    response_format: str
    instruction: str

    @validator("bot_information")
    @classmethod
    def validate_bot_information(cls, bot_info: Dict, values: Dict):
        """
        Validator that ensures that the information the bot needs to function is provided in the correct form
        """
        values["input_variables"] = []  # temp fix to a lang chain issue
        if not isinstance(bot_info, dict):
            raise ValueError("bot_information must be a dictionary")

        template_str = """
        # INFORMATION
        Here are the details you need to know about the code you are working on:
        {% for key, value in information.items() %}
        Here is the {{ key }}:\n`{{ value }}`\n
        {% endfor %}
        Use the information provided above to complete the task.
        """
        return Template(template_str).render(information=bot_info)

    def format(self):
        """
        Renders the jinja 2 template to a string
        """
        template = Template(self.template_str)
        kwargs = self.dict()
        kwargs.pop("bot_information")
        return template.render(**kwargs)

    @property
    def _prompt_type(self):
        return "Sani fixer"
