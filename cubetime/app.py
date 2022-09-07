import click
from enum import Enum
import matplotlib.pyplot as pl
import numpy as np
from typing import Any, Dict, List, Optional

from cubetime.CompareStyle import CompareStyle, compare_style_option
from cubetime.Config import global_config
from cubetime.TaskIndex import TaskIndex
from cubetime.TimeSet import TimeSet
from cubetime.TimedTask import TimedTask


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


@click.group()
@click.pass_context
def main(ctx: click.Context):
    """
    Multi-segment timing program.
    """
    ctx.obj = TaskIndex()


@main.command()
@taskname_option(required=True, help_suffix="create", allow_alias=False)
@string_list_option(
    "aliases", "alias(es)", required=False, help_suffix="use to refer to new task"
)
@click.pass_context
def create(ctx: click.Context, taskname: str, aliases: List[str] = None) -> None:
    """
    Creates a new task and adds it to the index of all tasks.
    """
    task_index: TaskIndex = ctx.obj
    task_index.new_timed_task(
        name=taskname,
        segments=parse_segments(),
        leaf_directory=parse_directory(),
        min_best=parse_min_best(),
        aliases=aliases,
    )
    return


@main.command()
@taskname_option(required=True, help_suffix="add alias(es) for", allow_alias=True)
@string_list_option(
    "aliases", "alias(es)", required=True, help_suffix="use to refer to task"
)
@click.pass_context
def add_alias(ctx: click.Context, taskname: str, aliases: List[str]) -> None:
    """
    Adds alias(es) to a task.
    """
    task_index: TaskIndex = ctx.obj
    task_index.add_aliases(taskname, aliases)
    return


@main.command()
@string_list_option("aliases", "alias(es)", required=True, help_suffix="to remove")
@click.pass_context
def remove_alias(ctx: click.Context, aliases: List[str]) -> None:
    """
    Removes aliases from the task index.
    """
    task_index: TaskIndex = ctx.obj
    task_index.remove_aliases(aliases)
    return


@main.command()
@taskname_option(required=True, help_suffix="time", allow_alias=True)
@compare_style_option(default=CompareStyle.BEST_RUN)
@click.pass_context
def time(ctx: click.Context, taskname: str, comparestyle: str) -> None:
    """
    Interactively times a run of the given task. Asks
    user to hit enter at beginning/end of all splits.
    """
    task_index: TaskIndex = ctx.obj
    task_index[taskname].time(compare_style=CompareStyle.__members__[comparestyle])
    return


@main.command()
@taskname_option(
    required=False,
    help_suffix="summarize (if detailed summary desired)",
    allow_alias=True,
)
@string_list_option(
    "tasknames",
    "task name(s) or alias(es)",
    required=False,
    help_suffix="summarize",
    letter='s',
)
@click.pass_context
def summarize(
    ctx: click.Context, taskname: str = None, tasknames: List[str] = None
) -> None:
    """
    Summarizes one or more task.

    1) provides a detailed summary of a single task (if --taskname given), or
    2) provides high level summaries of all (or some, if --tasknames given) tasks
    """
    task_index: TaskIndex = ctx.obj
    if taskname is None:
        task_index.print_summary(tasknames=tasknames, print_func=click.echo)
    elif tasknames is None:
        timed_task: TimedTask = task_index[taskname]
        timed_task.print_detailed_summary(print_func=click.echo)
    else:
        raise click.UsageError(
            "Only one of --taskname and --tasknames can be provided."
        )
    return


@main.command()
@taskname_option(required=True, help_suffix="make histogram(s) for", allow_alias=True)
@all_segments_option
@cumulative_segments_option
@string_list_option(
    "segments", "segment name(s)", required=False, help_suffix="make histogram(s) of"
)
@click.pass_context
def histogram(
    ctx: click.Context,
    taskname: str,
    all_segments: bool,
    cumulative_segments: bool,
    segments: List[str] = None,
) -> None:
    """
    Plots distribution of times.
    """
    fontsize: int = 12
    task_index: TaskIndex = ctx.obj
    time_set: TimeSet = task_index[taskname].time_set
    fig = pl.figure(figsize=(12, 9))
    ax = fig.add_subplot(111)
    kwargs: Dict = dict(histtype="step", linewidth=3)
    if all_segments and time_set.is_multi_segment:
        segments = time_set.segments
    if segments is None:
        ax.hist(time_set.cumulative_times[time_set.segments[-1]], **kwargs)
        ax.set_xlabel(f"{taskname} completion time [s]", size=fontsize)
        ax.set_title(f"{taskname} time distribution", size=fontsize)
    else:
        for segment in segments:
            kwargs["label"] = f"{1 + time_set.segments.index(segment)}. {segment}"
            if cumulative_segments:
                ax.hist(time_set.cumulative_times[segment], **kwargs)
            else:
                ax.hist(time_set.times[segment], **kwargs)
        title: str = "Cumulative " if cumulative_segments else ""
        if len(segments) > 1:
            ax.legend(fontsize=fontsize)
            ax.set_xlabel("Segment length [s]", size=fontsize)
            title = f"{title}segment time distribution, {taskname}"
        else:
            ax.set_xlabel(f"{segments[0]} length [s]", size=fontsize)
            title = f"{title}{segments[0]} time distribution, {taskname}"
        ax.set_title(title, size=fontsize)
    ax.set_ylabel("# of occurrences", size=fontsize)
    ax.tick_params(labelsize=fontsize, width=2.5, length=7.5, which="major")
    ax.tick_params(width=1.5, length=4.5, which="minor")
    fig.tight_layout()
    pl.show()
    return


@main.command()
@taskname_option(required=True, help_suffix="make scatter plot for", allow_alias=True)
@all_segments_option
@cumulative_segments_option
@string_list_option(
    "segments",
    "segment name(s)",
    required=False,
    help_suffix="make scatter plot(s) for"
)
@click.pass_context
def scatter(
    ctx: click.Context,
    taskname: str,
    all_segments: bool,
    cumulative_segments: bool,
    segments: List[str] = None,
) -> None:
    """
    Plot times against completion number.
    """
    fontsize: int = 12
    task_index: TaskIndex = ctx.obj
    time_set: TimeSet = task_index[taskname].time_set
    x_values: np.ndarray = 1 + np.arange(len(time_set))
    fig = pl.figure(figsize=(12, 9))
    ax = fig.add_subplot(111)
    kwargs: Dict = dict(s=12)
    if all_segments:
        segments = time_set.segments
    if segments is None:
        ax.scatter(x_values, time_set.cumulative_times[time_set.segments[-1]], **kwargs)
        ax.set_ylabel(f"{taskname} completion time", size=fontsize)
        ax.set_title(f"{taskname} time progression", size=fontsize)
    else:
        for segment in segments:
            kwargs["label"] = f"{1 + time_set.segments.index(segment)}. {segment}"
            if cumulative_segments:
                ax.scatter(x_values, time_set.cumulative_times[segment], **kwargs)
            else:
                ax.scatter(x_values, time_set.times[segment], **kwargs)
        title: str = "Cumulative " if cumulative_segments else ""
        if len(segments) > 1:
            ax.legend(fontsize=fontsize)
            ax.set_ylabel("Segment completion time [s]", size=fontsize)
            title = f"{title}segment time progression, {taskname}"
        else:
            ax.set_ylabel(f"{title}{segments[0]} completion time [s]", size=fontsize)
            title = f"{title}{segments[0]} time progression, {taskname}"
        ax.set_title(title, size=fontsize)
    ax.set_xlabel("completion #", size=fontsize)
    ax.tick_params(labelsize=fontsize, width=2.5, length=7.5, which="major")
    ax.tick_params(width=1.5, length=4.5, which="minor")
    fig.tight_layout()
    pl.show()
    return


@main.command(name="list")
@click.pass_context
def list_command(ctx: click.Context) -> None:
    """
    Lists all names and aliases of stored tasks.
    """
    task_index: TaskIndex = ctx.obj
    click.echo(f"\n{task_index.alias_summary}\n")
    return


@main.command()
@click.option("--name", "-n", required=False, type=str, help="config variable name")
@click.option("--value", "-v", required=False, type=str, help="config variable value")
def config(name: str = None, value: str = None) -> None:
    """
    Lists or edits the configuration settings of cubetime.

    If no options are given, the full config is printed. If a name is given but no value
    is given, then the config variable with that name is printed alongside its value. If
    both a name and a value are given, then this command edits the global config file
    (after confirmation from user).
    """
    if value is None:
        global_config.print(name=name, print_func=click.echo)
    elif name is None:
        raise click.UsageError("--value can only be given if --name is given")
    else:
        formatted: Any = value
        if value.lower() == "true":
            formatted = True
        elif value.lower() == "false":
            formatted = False
        elif value.isnumeric():
            formatted = int(value)
        confirmation_message: str = f"Should it be added with value {formatted}?"
        if name in global_config:
            confirmation_message = (
                f"{name} exists already in cubetime config "
                f"(value={global_config[name]}). {confirmation_message}"
            )
        else:
            confirmation_message = (
                f"{name} not in cubetime config. {confirmation_message}"
            )
        if click.confirm(confirmation_message):
            global_config[name] = formatted
    return


if __name__ == "__main__":
    main()
