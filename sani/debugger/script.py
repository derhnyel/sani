import io
import astor
import linecache
from sani.core.ops import os
from sani.utils.custom_types import Any, Generator, script, ast, Enum, Language
from sani.debugger.parser import Parser, BaseParser


class BaseScript:
    """
    An abstract class to be inherited by all scripts
    must have a `get_report` method.
    """

    script_type: str = None
    script = script

    def __init__(self, *args, **kwargs) -> None:
        self.args = args
        self.kwargs = kwargs
        self.parser: BaseParser = (
            Parser.__dict__.get("_member_map_").get(self.script_type).value()
        )

    def get_script(self, file) -> script:
        """
        Get a report from the script
        """

    def get_attributes(self, source_code: io.TextIOWrapper) -> script:
        (
            comments,
            source_list,
            lined_source,
            lenght,
            code,
        ) = self.parser.extract_attributes(source_code)
        return script(
            lenght,
            source_list,
            code,
            lined_source,
            None,
            None,
            None,
            comments,
            None,
        )

    def get_script_path(self, file: str) -> str:
        """
        Get the absolute path of the script
        Parameters:
            file (string): filepath to python source file.
        Returns:
            A string of the absolute path.
        """

        return os.path.dirname(os.path.realpath(file))


class PythonScript(BaseScript):
    """
    Utility class to get a python script information/attributes
    """

    script_type = Language.python

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)

    @staticmethod
    def get_ast(script: str) -> ast.AST:
        """
        Get the  abstract syntax tree of a source script.
        Parameters:
            script (str): Source script.
        """

        return ast.parse(script)

    @staticmethod
    def get_script_from_ast(ast: ast.AST) -> str:
        """
        Get the source from an abstract syntax tree using AST Observe/Rewrite.
        Parameters:
            ast (ast.AST): Abstract syntax tree object.
        """
        return astor.to_source(ast)

    @staticmethod
    def get_script_imports(
        source: Any, format="text"
    ) -> Generator[str, str, ast.Import]:
        """
        Get the import statements from the source code.
        Parameters:
            source (Any): The source code to get the imports from.
            format (str): The format to return the imports in.
        Returns:
            Generator[str, ast.Import]: The import statements.
        """
        if isinstance(source, str):
            source = PythonScript.get_ast(source)
        for node in ast.iter_child_nodes(source):
            if isinstance(node, ast.Import) or isinstance(node, ast.ImportFrom):
                if format == "text":
                    yield PythonScript.get_script_from_ast(node)
                elif format == "ast":
                    yield node

    @staticmethod
    def get_comments(source: Any, clean: bool = False) -> str:
        """
        Get comments from a script.
        Parameters:
            script (str): script to get comments from.
        Returns:
            A list of string comments.
        """
        if isinstance(source, str):
            source = PythonScript.get_ast(source)
        return ast.get_docstring(source, clean=clean)

    @staticmethod
    def get_script_name(file: str) -> str:
        """
        Get the basename of the script
        Parameters:
            file (string): filepath to python source file.
        Returns:
            A string of the basename of the script.
        """
        return os.path.basename(file)

    def get_script(self, file: str) -> script:
        """
        Get the lines of a python source file as a list of strings.
        Parameters:
            file (string): filepath to python source file.
        Returns:
            A NamedTuple object of Type[ScriptLines] ie.`NamedTuple("Script",[("lenght", int),("lines", List[str]),("string", str),(lined_string,str),("lined_list", List[str]),("ast",ast.Ast), ("imports", str),("comments", str),("ast_dump",str,)],)`.
        """

        lined_list = list()
        lined_string = str()
        string = str()
        lines = linecache.getlines(file)

        for index, line in enumerate(lines):
            lined_text = f"{index + 1} : {line}"
            lined_list.append(lined_text)
            lined_string += lined_text
            string += line
        ast_object = PythonScript.get_ast(string)

        ast_dump = ast.dump(ast_object)
        imports = ("").join(
            [impt for impt in PythonScript.get_script_imports(ast_object)]
        )
        comments = PythonScript.get_comments(ast_object)
        return self.script(
            len(lines),
            lines,
            string,
            lined_string,
            lined_list,
            ast_object,
            imports,
            comments,
            ast_dump,
        )


class GoScript(BaseScript):
    """
    Utility class to get a golang script information/attributes
    """

    script_type = Language.go

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)


class CScript(BaseScript):
    """
    Utility class to get a c script information/attributes
    """

    script_type = Language.c

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)


class HtmlScript(BaseScript):
    script_type = Language.html

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)


class RubyScript(BaseScript):
    """
    Utility class to get a ruby script information/attributes
    """

    script_type = Language.ruby

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)


class JavaScript(BaseScript):
    """
    Utility class to get a javascript script information/attributes
    """

    script_type = Language.javascript

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)


class ShellScript(BaseScript):
    """
    Utility class to get a shell script information/attributes
    """

    script_type = Language.shell

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)


class RustScript(BaseScript):
    """
    Utility class to get a rust script information/attributes
    """

    script_type = Language.rust

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)


class JavaLangScript(BaseScript):
    """
    Utility class to get a javascript script information/attributes
    """

    script_type = Language.javascript

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)


class TypeScript(BaseScript):
    """
    Utility class to get a typescript script information/attributes
    """

    script_type = Language.typescript

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)


class Script(Enum):
    python = PythonScript
    go = GoScript
    c = CScript
    javascript = JavaScript
    ruby = RubyScript
    shell = ShellScript
    html = HtmlScript
    rust = RustScript
    typescript = TypeScript
    java = JavaLangScript
