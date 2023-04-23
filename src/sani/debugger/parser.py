import io
import re
import tokenize
from bisect import bisect_left
from sani.utils.custom_types import (
    List,
    Generator,
    ABC,
    abstractmethod,
    Comment,
    Enum,
    Tuple,
)
from sani.utils.exception import UnterminatedCommentError


"""
comment_parser library: https://github.com/jeanralphaviles/comment_parser/blob/master/comment_parser/parsers
"""


class BaseParser(ABC):
    """Base class for parsers."""

    def __init__(self, *args, **kwargs) -> None:
        self.args = args
        self.kwargs = kwargs

    @abstractmethod
    def extract_attributes(
        self, code: str
    ) -> Tuple[List[Comment], List[str], str, int, str]:
        """Extracts a list of comments from the given code.

        Args:
            code: String containing code to extract comments from.
        Returns:
            Python list of Comment in the order that they appear in the code.
        """
        pass


class PythonParser(BaseParser):
    """This class provides methods for parsing comments from Python scripts."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def extract_attributes(
        self, source: str
    ) -> Tuple[List[Comment], List[str], str, int, str]:
        """Extracts a list of comments from the given Python script.

        Comments are identified using the tokenize module. Does not include function,
        class, or module docstrings. All comments are single line comments.

        Args:
            source: String containing source code to extract comments from.
        Returns:
            Python list of Comment in the order that they appear in the code.
        Raises:
            tokenize.TokenError
        """
        comments = []
        source_list = []
        lined_source = str()
        tokens: Generator = tokenize.tokenize(io.BytesIO(source.encode()).readline)
        for toknum, tokstring, tokloc, _, _ in tokens:
            line = tokloc[0]
            if toknum is tokenize.COMMENT:
                # Removes leading '#' character.
                tokstring = tokstring[1:]
                comments.append(Comment(tokstring, line, False))
            source_list.append(tokstring)
            lined_source += f"{line}:{tokstring}"
        return comments, source_list, lined_source, line, source


class GoParser(BaseParser):
    """This class provides methods for parsing comments from Go source code."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def extract_attributes(
        self, code: str
    ) -> Tuple[List[Comment], List[str], str, int, str]:
        """Extracts a list of comments from the given Go source code.

        Comments are represented with the Comment class found in the module.
        Go comments come in two forms, single and multi-line comments.
        - Single-line comments begin with '//' and continue to the end of line.
        - Multi-line comments begin with '/*' and end with '*/' and can span
            multiple lines of code. If a multi-line comment does not terminate
            before EOF is reached, then an exception is raised.
        Go comments are not allowed to start in a string or rune literal. This
        module makes sure to watch out for those.

        https://golang.org/ref/spec#Comments

        Args:
        code: String containing code to extract comments from.
        Returns:
        Python list of Comment in the order that they appear in the code.
        Raises:
        UnterminatedCommentError: Encountered an unterminated multi-line
            comment.
        """
        state = 0
        current_comment = ""
        comments = []
        line_counter = 1
        comment_start = 1
        string_char = ""
        source_list = []
        lined_source = str()
        line_char = str()
        for char in code:
            line_char += char
            if state == 0:
                # Waiting for comment start character or beginning of
                # string or rune literal.
                if char == "/":
                    state = 1
                elif char in ('"', "'", "`"):
                    string_char = char
                    state = 5
            elif state == 1:
                # Found comment start character, classify next character and
                # determine if single or multi-line comment.
                if char == "/":
                    state = 2
                elif char == "*":
                    comment_start = line_counter
                    state = 3
                else:
                    state = 0
            elif state == 2:
                # In single-line comment, read characters util EOL.
                if char == "\n":
                    comment = Comment(current_comment, line_counter, False)
                    comments.append(comment)
                    current_comment = ""
                    state = 0
                else:
                    current_comment += char
            elif state == 3:
                # In multi-line comment, add characters until '*' is
                # encountered.
                if char == "*":
                    state = 4
                else:
                    current_comment += char
            elif state == 4:
                # In multi-line comment with asterisk found. Determine if
                # comment is ending.
                if char == "/":
                    comment = Comment(current_comment, comment_start, multiline=True)
                    comments.append(comment)
                    current_comment = ""
                    state = 0
                else:
                    current_comment += "*"
                    # Care for multiple '*' in a row
                    if char != "*":
                        current_comment += char
                        state = 3
            elif state == 5:
                # In string literal, expect literal end or escape character.
                if char == string_char:
                    state = 0
                elif char == "\\":
                    state = 6
            elif state == 6:
                # In string literal, escaping current char.
                state = 5
            if char == "\n":
                line_counter += 1
                source_list.append(line_char)
                lined_source += f"{line_counter}:{line_char}"
                line_char = str()

        # EOF.
        if state in (3, 4):
            raise UnterminatedCommentError()
        if state == 2:
            # Was in single-line comment. Create comment.
            comment = Comment(current_comment, line_counter, False)
            comments.append(comment)
        return comments, source_list, lined_source, line_counter, code


class CParser(BaseParser):
    """
    This module provides methods for parsing comments from C family languages.
    Works with:
    C99+
    C++
    Objective-C
    Java
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def extract_attributes(code: str) -> Tuple[List[Comment], List[str], str, int, str]:
        """Extracts a list of comments from the given C family source code.

        Comments are represented with the Comment class found in the module.
        C family comments come in two forms, single and multi-line comments.
            - Single-line comments begin with '//' and continue to the end of line.
            - Multi-line comments begin with '/*' and end with '*/' and can span
            multiple lines of code. If a multi-line comment does not terminate
            before EOF is reached, then an exception is raised.

        Note that this doesn't take language-specific preprocessor directives into
        consideration.

        Args:
            code: String containing code to extract comments from.
        Returns:
            Python list of Comment in the order that they appear in the code.
        Raises:
            UnterminatedCommentError: Encountered an unterminated multi-line
            comment.
        """
        pattern = r"""
            (?P<literal> (\"([^\"\n])*\")+) |
            (?P<single> //(?P<single_content>.*)?$) |
            (?P<multi> /\*(?P<multi_content>(.|\n)*?)?\*/) |
            (?P<error> /\*(.*)?)
        """
        lined_source = str()

        compiled = re.compile(pattern, re.VERBOSE | re.MULTILINE)

        lines_indexes = []
        for match in re.finditer(r"$", code, re.M):
            lines_indexes.append(match.start())

        comments = []
        for match in compiled.finditer(code):
            kind = match.lastgroup

            start_character = match.start()
            line_no = bisect_left(lines_indexes, start_character)

            if kind == "single":
                comment_content = match.group("single_content")
                comment = Comment(comment_content, line_no + 1)
                comments.append(comment)
            elif kind == "multi":
                comment_content = match.group("multi_content")
                comment = Comment(comment_content, line_no + 1, multiline=True)
                comments.append(comment)
            elif kind == "error":
                raise UnterminatedCommentError()

        source_list = code.split("\n")
        for index, line in enumerate(source_list):
            lined_source += f"{index+1} : {line}"

        return comments, source_list, lined_source, len(source_list), code


class JsParser(BaseParser):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def extract_attributes(code: str) -> Tuple[List[Comment], List[str], str, int, str]:
        """Extracts a list of comments from the given Javascript source code.

        Comments are represented with the Comment class found in the module.
        Javascript comments come in two forms, single and multi-line comments.
            - Single-line comments begin with '//' and continue to the end of line.
            - Multi-line comments begin with '/*' and end with '*/' and can span
            multiple lines of code. If a multi-line comment does not terminate
            before EOF is reached, then an exception is raised.
        This module takes quoted strings into account when extracting comments from
        source code.

        Args:
            code: String containing code to extract comments from.
        Returns:
            Python list of Comment in the order that they appear in the code.
        Raises:
            UnterminatedCommentError: Encountered an unterminated multi-line
            comment.
        """
        state = 0
        source_list = []
        lined_source = str()
        line_char = str()
        current_comment = ""
        comments = []
        line_counter = 1
        comment_start = 1
        string_char = ""
        for char in code:
            line_char += char
            if state == 0:
                # Waiting for comment start character or beginning of
                # string.
                if char == "/":
                    state = 1
                elif char in ('"', "'"):
                    string_char = char
                    state = 5
            elif state == 1:
                # Found comment start character, classify next character and
                # determine if single or multi-line comment.
                if char == "/":
                    state = 2
                elif char == "*":
                    comment_start = line_counter
                    state = 3
                else:
                    state = 0
            elif state == 2:
                # In single-line comment, read characters until EOL.
                if char == "\n":
                    comment = Comment(current_comment, line_counter)
                    comments.append(comment)
                    current_comment = ""
                    state = 0
                else:
                    current_comment += char
            elif state == 3:
                # In multi-line comment, add characters until '*' is
                # encountered.
                if char == "*":
                    state = 4
                else:
                    current_comment += char
            elif state == 4:
                # In multi-line comment with asterisk found. Determine if
                # comment is ending.
                if char == "/":
                    comment = Comment(current_comment, comment_start, multiline=True)
                    comments.append(comment)
                    current_comment = ""
                    state = 0
                else:
                    current_comment += "*"
                    # Care for multiple '*' in a row
                    if char != "*":
                        current_comment += char
                        state = 3
            elif state == 5:
                # In string literal, expect literal end or escape character.
                if char == string_char:
                    state = 0
                elif char == "\\":
                    state = 6
            elif state == 6:
                # In string literal, escaping current char.
                state = 5
            if char == "\n":
                line_counter += 1
                source_list.append(line_char)
                lined_source += f"{line_counter}:{line_char}"
                line_char = str()

        # EOF.
        if state in (3, 4):
            raise UnterminatedCommentError()
        if state == 2:
            # Was in single-line comment. Create comment.
            comment = Comment(current_comment, line_counter)
            comments.append(comment)
        return comments, source_list, lined_source, line_counter, code


class HtmlParser(BaseParser):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def extract_attributes(code: str) -> Tuple[List[Comment], List[str], str, int, str]:
        """Extracts a list of comments from the given HTML family source code.

        Comments are represented with the Comment class found in the module.
        HTML family comments come in one form, comprising all text within '<!--' and
        '-->' markers. Comments cannot be nested.

        Args:
            code: String containing code to extract comments from.
        Returns:
            Python list of Comment in the order that they appear in the code..
        Raises:
            UnterminatedCommentError: Encountered an unterminated multi-line
            comment.
        """
        lined_source = str()
        pattern = r"""
            (?P<literal> (\"([^\"\n])*\")+) |
            (?P<single> <!--(?P<single_content>.*?)-->) |
            (?P<multi> <!--(?P<multi_content>(.|\n)*?)?-->) |
            (?P<error> <!--(.*)?)
        """
        compiled = re.compile(pattern, re.VERBOSE | re.MULTILINE)

        lines_indexes = []
        for match in re.finditer(r"$", code, re.M):
            lines_indexes.append(match.start())

        comments = []
        for match in compiled.finditer(code):
            kind = match.lastgroup

            start_character = match.start()
            line_no = bisect_left(lines_indexes, start_character)

            if kind == "single":
                comment_content = match.group("single_content")
                comment = Comment(comment_content, line_no + 1)
                comments.append(comment)
            elif kind == "multi":
                comment_content = match.group("multi_content")
                comment = Comment(comment_content, line_no + 1, multiline=True)
                comments.append(comment)
            elif kind == "error":
                raise UnterminatedCommentError()

        source_list = code.split("\n")
        for index, line in enumerate(source_list):
            lined_source += f"{index+1} : {line}"

        return comments, source_list, lined_source, len(source_list), code


class RubyParser(BaseParser):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def extract_attributes(code: str) -> Tuple[List[Comment], List[str], str, int, str]:
        """Extracts a list of comments from the given Ruby source code.

        Comments are represented with the Comment class found in the module.

        Ruby comments start with a '#' character and run to the end of the line,
        http://ruby-doc.com/docs/ProgrammingRuby.

        Args:
            code: String containing code to extract comments from.
        Returns:
            Python list of Comment in the order that they appear in the code..
        """
        pattern = r"""
            (?P<literal> ([\"'])((?:\\\2|(?:(?!\2)).)*)(\2)) |
            (?P<single> \#(?P<single_content>.*?)$)
            """
        lined_source = str()
        compiled = re.compile(pattern, re.VERBOSE | re.MULTILINE)

        lines_indexes = []
        for match in re.finditer(r"$", code, re.M):
            lines_indexes.append(match.start())

        comments = []
        for match in compiled.finditer(code):
            kind = match.lastgroup

            start_character = match.start()
            line_no = bisect_left(lines_indexes, start_character)

            if kind == "single":
                comment_content = match.group("single_content")
                comment = Comment(comment_content, line_no + 1)
                comments.append(comment)

        source_list = code.split("\n")
        for index, line in enumerate(source_list):
            lined_source += f"{index+1} : {line}"

        return comments, source_list, lined_source, len(source_list), code


class ShellParser(BaseParser):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def extract_attributes(code: str) -> Tuple[List[Comment], List[str], str, int, str]:
        """Extracts a list of comments from the given shell script.

        Comments are represented with the Comment class found in the module.
        Shell script comments only come in one form, single-line. Single line
        comments start with an unquoted or unescaped '#' and continue on until the
        end of the line. A quoted '#' is one that is located within a pair of
        matching single or double quote marks. An escaped '#' is one that is
        immediately preceeded by a backslash '\'

        Args:
        code: String containing code to extract comments from.
        Returns:
        Python list of Comment in the order that they appear in the code.
        """
        state = 0
        string_char = ""
        current_comment = ""
        comments = []
        source_list = []
        lined_source = str()
        line_counter = 1
        for char in code:
            if state == 0:
                # Waiting for comment start character, beginning of string,
                # or escape character.
                if char == "#":
                    state = 1
                elif char in ('"', "'"):
                    string_char = char
                    state = 2
                elif char == "\\":
                    state = 4
            elif state == 1:
                # Found comment start character. Read comment until EOL.
                if char == "\n":
                    comment = Comment(current_comment, line_counter)
                    comments.append(comment)
                    current_comment = ""
                    state = 0
                else:
                    current_comment += char
            elif state == 2:
                # In string literal, wait for string end or escape char.
                if char == string_char:
                    state = 0
                elif char == "\\":
                    state = 3
            elif state == 3:
                # Escaping current char, inside of string.
                state = 2
            elif state == 4:
                # Escaping current char, outside of string.
                state = 0
            if char == "\n":
                line_counter += 1
                source_list.append(line_char)
                lined_source += f"{line_counter}:{line_char}"
                line_char = str()

        # EOF.
        if state == 1:
            # Was in single line comment. Create comment.
            comment = Comment(current_comment, line_counter)
            comments.append(comment)
        return comments, source_list, lined_source, line_counter, code


class Parser(Enum):
    python = PythonParser
    javascript = JsParser
    c = CParser
    html = HtmlParser
    ruby = RubyParser
    shell = ShellParser
    go = GoParser
