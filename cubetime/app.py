import click
import matplotlib.pyplot as pl
import numpy as np
from typing import Any, Dict, List, Optional

from cubetime.CompareStyle import CompareStyle, compare_style_option
from cubetime.Config import global_config
from cubetime.TaskIndex import TaskIndex
from cubetime.TimeSet import TimeSet


def taskname_option(required: bool, help_suffix: str):
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
        prompt=False,
        required=required,
        type=str,
        help=f"single task name to {help_suffix}",
    )


def tasknames_option(required: bool, help_suffix: str):
    """
    Creates option decorator for tasknames argument.

    Args:
        required: True if tasknames is necessary
        help_suffix: help message is f"comma-separated task name(s) to {help_suffix}"

    Returns:
        click option decorator
    """
    return click.option(
        "--tasknames",
        prompt=False,
        required=required,
        type=str,
        help=f"comma-separated task name(s) to {help_suffix}",
    )


def segments_option(required: bool, help_suffix: str):
    """
    Creates option decorator for segments argument.

    Args:
        required: True if segments is necessary
        help_suffix: help message is f"comma-separated segment name(s) to {help_suffix}"

    Returns:
        click option decorator
    """
    return click.option(
        "--segments",
        prompt=False,
        required=required,
        type=str,
        callback=(lambda ctx, param, s: None if s is None else s.split(",")),
        help=f"comma-separated segment name(s) to {help_suffix}",
    )


all_segments_option = click.option(
    "--all_segments",
    default=False,
    is_flag=True,
    help="if given, all segments plotted (overrides --segments)",
)


cumulative_segments_option = click.option(
    "--cumulative_segments",
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
    Command that runs before all sub-commands.
    """
    ctx.obj = TaskIndex()


@main.command()
@click.pass_context
def list_tasks(ctx: click.Context) -> None:
    """
    Lists all tasks stored in the index.
    """
    task_index: TaskIndex = ctx.obj
    click.echo(task_index.task_names)
    return


@main.command()
@taskname_option(required=True, help_suffix="create")
@click.pass_context
def add_new_task(ctx: click.Context, taskname: str) -> None:
    """
    Adds a new task to the idex of all tasks.
    """
    task_index: TaskIndex = ctx.obj
    task_index.new_timed_task(
        name=taskname,
        segments=parse_segments(),
        leaf_directory=parse_directory(),
        min_best=parse_min_best(),
    )


@main.command()
@taskname_option(required=True, help_suffix="time")
@compare_style_option(default=CompareStyle.BEST_RUN)
@click.pass_context
def time(ctx: click.Context, taskname: str, comparestyle: str) -> None:
    """
    Interactively times a run of the given task.
    """
    task_index: TaskIndex = ctx.obj
    task_index[taskname].time(compare_style=CompareStyle.__members__[comparestyle])
    return


@main.command()
@taskname_option(required=False, help_suffix="summarize (if detailed summary desired)")
@tasknames_option(required=False, help_suffix="summarize")
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
        time_set: TimeSet = task_index[taskname].time_set
        time_set.print_detailed_summary(print_func=click.echo)
    else:
        raise ValueError("Only one of --taskname and --tasknames can be provided.")
    return


@main.command()
@taskname_option(required=True, help_suffix="make histogram(s) for")
@all_segments_option
@cumulative_segments_option
@segments_option(required=False, help_suffix="make histogram(s) of")
@click.pass_context
def histogram(
    ctx: click.Context,
    taskname: str,
    all_segments: bool,
    cumulative_segments: bool,
    segments: List[str] = None,
) -> None:
    """
    Makes histograms of one task or one or more segments of a task.
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
@taskname_option(required=True, help_suffix="make scatter plot for")
@all_segments_option
@cumulative_segments_option
@segments_option(required=False, help_suffix="make scatter plot(s) for")
@click.pass_context
def scatter(
    ctx: click.Context,
    taskname: str,
    all_segments: bool,
    cumulative_segments: bool,
    segments: List[str] = None,
) -> None:
    """
    Plot times of one task or one or more segments of a task against time.
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


@main.command()
@click.option("--name", required=False, type=str, help="config variable name")
def print_config(name: str = None) -> None:
    """
    Prints the configuration settings of cubetime.
    """
    global_config.print(name=name, print_func=click.echo)
    return


@main.command()
@click.option("--name", required=True, type=str, help="config variable name")
@click.option("--value", required=True, type=str, help="config variable value")
def update_config(name: str, value: str) -> None:
    """
    Updates config with the given value. Only bools, ints, and strings supported.
    """
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
        confirmation_message = f"{name} not in cubetime config. {confirmation_message}"
    if click.confirm(confirmation_message):
        global_config[name] = formatted
    return


if __name__ == "__main__":
    main()
