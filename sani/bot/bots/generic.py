from langchain.chat_models import ChatOpenAI

# from langchain.llms import OpenAI
from sani.bot.prompt.generic import GenericSaniPrompt
from sani.bot.bots.base import BaseBot
from sani.utils.custom_types import Context as ct
from sani.bot.prompt.string_templates import (
    FIX_MODE_INSTRUCTIONS,
    FIX_MODE_PERSONALITY,
    FIX_MODE_RESPONSE_FORMAT,
    TEST_MODE_INSTRUCTIONS,
    TEST_MODE_PERSONALITY,
    TEST_MODE_RESPONSE_FORMAT,
    IMPROVE_MODE_INSTRUCTIONS,
    IMPROVE_MODE_PERSONALITY,
    IMPROVE_MODE_RESPONSE_FORMAT,
    DOCUMENT_MODE_INSTRUCTIONS,
    DOCUMENT_MODE_PERSONALITY,
    DOCUMENT_MODE_RESPONSE_FORMAT,
    ANALYZE_MODE_INSTRUCTIONS,
    ANALYZE_MODE_PERSONALITY,
    ANALYZE_MODE_RESPONSE_FORMAT,
)

from langchain.schema import (
    # AgentAction,
    # AgentFinish,
    AIMessage,
    HumanMessage,
    # LLMResult,
    SystemMessage,
)
from sani.core.config import Config
from sani.utils.custom_types import Union, Dict, List

config = Config()


# "system", content=prompt
# "bot",content = output
# "user", content = details


class GenericSaniBot(BaseBot):
    """
    A Generic bot for sani that can be operated in all modes.
    """

    def __init__(
        self, context, mode, *args, model_name=None, openai_key=None, **kwargs
    ) -> None:
        super().__init__(*args, **kwargs)
        if model_name:
            self.model_name = model_name

        self.mode = mode
        self.openai_api_key = openai_key
        valid_modes = ["fix", "improve", "test", "document", "analyze"]
        if self.mode not in valid_modes:
            raise ValueError(
                f"Sani must operate in one of the following modes: {valid_modes}"
            )

        self.prompt_templates = {
            "fix": {
                "personality": FIX_MODE_PERSONALITY,
                "instructions": FIX_MODE_INSTRUCTIONS,
                "response_format": FIX_MODE_RESPONSE_FORMAT,
            },
            "test": {
                "personality": TEST_MODE_PERSONALITY,
                "instructions": TEST_MODE_INSTRUCTIONS,
                "response_format": TEST_MODE_RESPONSE_FORMAT,
            },
            "improve": {
                "personality": IMPROVE_MODE_PERSONALITY,
                "instructions": IMPROVE_MODE_INSTRUCTIONS,
                "response_format": IMPROVE_MODE_RESPONSE_FORMAT,
            },
            "document": {
                "personality": DOCUMENT_MODE_PERSONALITY,
                "instructions": DOCUMENT_MODE_INSTRUCTIONS,
                "response_format": DOCUMENT_MODE_RESPONSE_FORMAT,
            },
            "analyze": {
                "personality": ANALYZE_MODE_PERSONALITY,
                "instructions": ANALYZE_MODE_INSTRUCTIONS,
                "response_format": ANALYZE_MODE_RESPONSE_FORMAT,
            },
        }
        self.llm = self.get_llm(
            temperature=self.temperature,
            model_name=self.model_name,
            openai_api_key=self.openai_api_key,
        )
        self.input = context
        self._build_prompt()

    @classmethod
    def prepare_messages(
        cls,
        messages: List[Dict[str, str]],
    ) -> Union[AIMessage, HumanMessage, SystemMessage]:
        """Prepare messages for LLM."""
        langchain_messages = []
        for msg in messages:
            if msg["role"] == "system":
                langchain_messages.append(SystemMessage(content=str(msg["content"])))
            elif msg["role"] == "bot":
                langchain_messages.append(AIMessage(content=str(msg["content"])))
            elif msg["role"] == "user":
                langchain_messages.append(HumanMessage(content=str(msg["content"])))
            else:
                raise ValueError(f"Unrecognized role: { msg['role']}")
        return langchain_messages

    @staticmethod
    def get_llm(
        model_name: str = None,
        temperature: float = None,
        openai_api_key: str = None,
        **kwargs,
    ) -> ChatOpenAI:
        if not model_name:
            model_name = config.openai_model_name

        if not temperature:
            temperature = config.openai_model_temperature
        return ChatOpenAI(
            model_name=model_name,
            temperature=temperature,
            openai_api_key=(openai_api_key or config.openai_api_key),
            # max_tokens=config.openai_model_max_tokens,
            **kwargs,
        )

    def _build_prompt(self):
        """
        Builds the prompt for a generic Sani bot
        """
        self.code_information = self._unpack_obj(self.input)
        self.language = self.input[ct.source.value][ct.language.value]
        self.personality = self.prompt_templates[self.mode]["personality"].format(
            self.language
        )
        self.instruction = self.prompt_templates[self.mode]["instructions"]
        self.response_format = self.prompt_templates[self.mode]["response_format"]

        self.prompt = GenericSaniPrompt(
            personality=self.personality,
            instruction=self.instruction,
            bot_information=self.code_information,
            response_format=self.response_format,
            input_variables=[],
        )
        self.message = self.prepare_messages(
            [
                {"role": "system", "content": self.prompt.format()},
                {"role": "user", "content": self.prompt.bot_information},
            ]
        )

    def get_prompt(self):
        """
        Returns the formatted input prompt string
        """
        return self.prompt.format()

    def code_str_to_json(self, input_str, start = 1):
        """
        Function for turning code strings to array of objects
        """
        str_split = input_str.split("\n")
        obj_array = [{'line': i + start, 'statement': line} for i, line in enumerate(str_split[:-1])]
        return obj_array

    def _unpack_obj(self, input_context: Dict):
        """
        Unpacks the context dictionary containing an additional info a bot might need
        to fulfill it's instructions
        """
        prompt_data = {
            "output": input_context[ct.execution][ct.output],
            "intended action": input_context[ct.prompt][ct.suggestions][ct.subject],
            # 'full source code': self.code_str_to_json(input_context[ct.source.value][ct.code.value]),
            # 'full source code with line numbers': input_context[ct.source.value][ct.lined_code.value],
            'code block': self.code_str_to_json(
                input_str = input_context[ct.source.value][ct.block.value],
                start = int(input_context[ct.source.value][ct.startline.value])
            )
        }
        return prompt_data
