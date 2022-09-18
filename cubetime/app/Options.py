import click
from typing import List, Optional

from cubetime.app.Plotting import PlotType
from cubetime.core.CompareStyle import CompareStyle


def taskname_option(required: bool, help_suffix: str, allow_alias: bool):
    """
    Creates option decorator for taskname argument.

    Args:
        required: True if taskname is necessary
        help_suffix: help message is f"single task name to {help_suffix}"

    Returns:
        click option decorator
    """
    return click.option(
        "--taskname",
        "-t",
        prompt=False,
        required=required,
        type=str,
        help=f"single task name{' (or alias)' if allow_alias else ''} to {help_suffix}",
    )


def string_list_option(
    option_name: str,
    description: str,
    required: bool,
    help_suffix: str,
    letter: str = None,
):
    """
    Creates an option that should be interpreted as a comma-separated list of strings.

    Args:
        option_name: the name to specify the option in the terminal
        description: few-words description of what is in the list
        required: True if the option must be provided for command to work
        help_suffix: string to put after "comma-separated {description} to " in help

    Returns:
        click option decorator
    """
    return click.option(
        f"--{option_name}",
        f"-{option_name[0] if letter is None else letter}",
        prompt=False,
        required=required,
        type=str,
        callback=(lambda ctx, param, s: None if s is None else s.split(",")),
        help=f"comma-separated {description} to {help_suffix}",
    )


all_segments_option = click.option(
    "--all_segments",
    "-a",
    default=False,
    is_flag=True,
    help="if given, all segments plotted (overrides --segments)",
)


cumulative_segments_option = click.option(
    "--cumulative_segments",
    "-c",
    default=False,
    is_flag=True,
    help=(
        "if given, cumulative times are plotted (ignored "
        "if neither --segments nor --all_segments are given)"
    ),
)


def parse_segments() -> List[str]:
    """
    Parses a list of segments from user input.

    Returns:
       List with at least one element. If user supplies no input, ["complete"] yielded
    """
    prompt_message: str = (
        "Enter comma-separated segments to use "
        "(empty string creates one 'complete' segment)"
    )
    raw: str = click.prompt(prompt_message, type=str, default="")
    if raw:
        return raw.split(",")
    else:
        return ["complete"]


def parse_directory() -> Optional[str]:
    """
    Gets the directory to pass to use for a new task from user input.

    Returns:
        None if the user supplies no input (implicitly desiring code to make one).
        Otherwise, gives the name of the directory that the user provided
    """
    prompt_message: str = (
        "Enter directory to put data from this task "
        "(empty string attempts to auto-create a directory)"
    )
    raw: str = click.prompt(prompt_message, type=str, default="")
    return raw if raw else None


def parse_min_best() -> bool:
    """
    Solicits input from user on whether smaller or larger times are better for a task.

    Returns:
        True if smaller times are better than larger times
    """
    return click.confirm("Are smaller times better for this task?")


def compare_style_option(default: CompareStyle):
    """
    Implements a click option for the CompareStyle enum.

    Args:
        default: the default compare style

    Returns:
        click option decorator
    """
    return click.option(
        "--compare_style",
        "-c",
        type=click.Choice(CompareStyle.__members__, case_sensitive=False),
        show_choices=True,
        default=default.name,
        show_default=True,
        callback=(lambda ctx, param, style: CompareStyle.__members__[style]),
    )


def plot_type_option(default: PlotType):
    """
    Creates an option decorator for the plot type enum.

    Args:
        default: default type of plot

    Returns:
        click option decorator
    """
    return click.option(
        "--plot_type",
        "-p",
        type=click.Choice(PlotType.__members__, case_sensitive=False),
        show_choices=True,
        default=default.name,
        show_default=True,
        callback=(lambda ctx, param, name: PlotType.__members__[name]),
        help="Type of plot to make",
    )
