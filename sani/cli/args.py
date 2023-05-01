import argparse


def parse_args() -> argparse.Namespace:
    """
    Parse command line arguments.
    """
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "source", metavar="source", type=str, help="Path to source file."
    )
    parser.add_argument(
        "-c",
        "--channel",
        type=str,
        help="Communication channel to use by the debugger and cli. Defaults to fileio.",
    )
    parser.add_argument(
        "-l",
        "--linter",
        type=str,
        help="Linter to use for debugging. Defaults to disable.",
    )
    parser.add_argument(
        "-e",
        "--executable",
        type=str,
        help="Executable used to run script. Defaults to supported language specific executable.",
    )
    parser.add_argument(
        "-a",
        "--args",
        type=str,
        help="Arguments to pass to the source script. Defaults to empty.",
    )
    return parser.parse_args()
