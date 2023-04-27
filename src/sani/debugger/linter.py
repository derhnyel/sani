from sani.utils.custom_types import Enum, ABC, abstractmethod


class BaseLinter(ABC):
    """
    An abstract class to be inherited by all linters
    must have a `get_report` method.
    """

    linter_name: str = None

    def __init__(self, *args, **kwargs) -> None:
        self.args = args
        self.kwargs = kwargs

    @abstractmethod
    def get_report(self, *args, **kwargs) -> str:
        """
        Get a report from the linter
        """
        raise NotImplementedError()


class PyLinter(BaseLinter):
    """
    The PyLint class which inherits from the BaseLinter class
    """

    linter_name = "pylint"

    def __init__(self, *args, **kwargs) -> None:
        from pylint.lint import Run
        from pylint.reporters.text import TextReporter
        from io import StringIO

        super().__init__(*args, **kwargs)
        self.pylint_output = StringIO()  # Custom open stream
        self.reporter = TextReporter(self.pylint_output)
        self.run = Run

    def get_report(self, filepath: str = None) -> str:
        """
        Get a report from the linter
        """
        self.run(
            [filepath or self.kwargs.get("filepath")],
            reporter=self.reporter,
            exit=False,
        )
        suggestions = self.pylint_output.getvalue()  # Retrieve  the text report
        return suggestions


class Flake8Linter(BaseLinter):
    """
    The Flake8 class which inherits from the BaseLinter class
    """

    linter_name = "flake8"

    def __init__(self, *args, **kwargs) -> None:
        from flake8.api import legacy as flake8
        import operator

        super().__init__(*args, **kwargs)
        self.style_guide = flake8.get_style_guide(
            max_line_length=kwargs.get("max_line_length") or 120,
            format="pylint",
        )
        self.operator = operator

    def get_report(self, filepath: str = None) -> str:
        """
        Get a report from the linter
        """
        suggestions = str()
        report = self.style_guide.check_files([filepath or self.kwargs.get("filepath")])
        results = report._application.file_checker_manager.results
        results.sort(key=self.operator.itemgetter(0))
        for filename, results, _ in results:
            results.sort(key=self.operator.itemgetter(1, 2))
            for error_code, line_number, column, text, physical_line in results:
                suggestions += f"\n{filename}:{line_number}:{column}: [{error_code}] {text} : {physical_line}"
        return suggestions


class PyJsLint(BaseLinter):
    """
    The PyJsLint class which inherits from the BaseLinter class
    """

    linter_name = "pyjslint"

    def __init__(self, *args, **kwargs) -> None:
        from pyjslint import check_JSLint

        super().__init__(*args, **kwargs)
        self.pyjslint = check_JSLint

    def get_report(self, filepath: str = None) -> str:
        """
        Get a report from the linter
        """
        if filepath or (self.kwargs.get("filepath")):
            with open(filepath or self.kwargs.get("filepath")) as f:
                suggestions = ("\n").join(self.pyjslint(f.read()))
        elif self.kwargs.get("source_code"):
            suggestions = ("\n").join(self.pyjslint(self.kwargs.get("source_code")))
        return suggestions


class HtmlLinter(BaseLinter):
    """
    The HtmlLinter class which inherits from the BaseLinter class
    """

    linter_name = "htmllinter"

    def __init__(self):
        from html_linter import lint

        self.lint = lint

    def get_report(self, filepath: str = None) -> str:
        if filepath or (self.kwargs.get("filepath")):
            with open(filepath or self.kwargs.get("filepath")) as f:
                suggestions = self.lint(f.read())
        elif self.kwargs.get("source_code"):
            suggestions = self.lint(self.kwargs.get("source_code"))
        return suggestions


class Linter(Enum):
    """
    Enum for linters
    """

    flake8 = Flake8Linter
    pylint = PyLinter
    pyjslint = PyJsLint
    htmllint = HtmlLinter
    disable = None
