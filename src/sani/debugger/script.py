from typing import Any, Generator, List, NamedTuple
import os
import ast
import astor
import linecache


class Scripts:
    """
    Utility class to get a script information/attributes
    """

    @staticmethod
    def get_script_path(file: str) -> str:
        """
        Get the absolute path of the script
        Parameters:
            file (string): filepath to python source file.
        Returns:
            A string of the absolute path.
        """
        return os.path.dirname(os.path.realpath(file))

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
            source = Scripts.get_ast(source)
        for node in ast.iter_child_nodes(source):
            if isinstance(node, ast.Import) or isinstance(node, ast.ImportFrom):
                if format == "text":
                    yield Scripts.get_script_from_ast(node)
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
            source = Scripts.get_ast(source)
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

    @staticmethod
    def get_script(file: str) -> NamedTuple:
        """
        Get the lines of a python source file as a list of strings.
        Parameters:
            file (string): filepath to python source file.
        Returns:
            A NamedTuple object of Type[ScriptLines] ie.`NamedTuple("ScriptLines",[("lenght", int),("lines", List[str]),("string", str),(lined_string,str),("lined_list", List[str]),("ast",ast.Ast), ("imports", str),("comments", str),("ast_dump",str,)],)`.
        """
        script = NamedTuple(
            "Script",
            [
                ("lenght", int),
                ("lines", List[str]),
                ("string", str),
                ("lined_string", str),
                ("lined_list", List[str]),
                ("ast", ast.AST),
                ("imports", str),
                ("comments", str),
                (
                    "ast_dump",
                    str,
                ),
            ],
        )
        lined_list = list()
        lined_string = str()
        string = str()
        lines = linecache.getlines(file)

        for index, line in enumerate(lines):
            lined_text = f"{index + 1} : {line}"
            lined_list.append(lined_text)
            lined_string += lined_text
            string += line
        ast_object = Scripts.get_ast(string)

        ast_dump = ast.dump(ast_object)
        imports = ("").join([impt for impt in Scripts.get_script_imports(ast_object)])
        comments = Scripts.get_comments(ast_object)
        return script(
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
