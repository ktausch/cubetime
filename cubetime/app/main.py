import click
import logging
from typing import List

import pandas as pd

from cubetime.app.Options import (
    all_segments_option,
    compare_style_option,
    cumulative_segments_option,
    parse_directory,
    parse_min_best,
    parse_segments,
    plot_type_option,
    string_list_option,
    taskname_option,
)
from cubetime.app.Plotting import plot_correlations, PlotType, TimePlotter

from cubetime.core.Archiving import make_data_snapshot
from cubetime.core.CompareStyle import CompareStyle
from cubetime.core.Config import DEFAULT_GLOBAL_CONFIG, global_config
from cubetime.core.Formatting import print_pandas_dataframe
from cubetime.core.TaskIndex import TaskIndex
from cubetime.core.TimeSet import TimeSet
from cubetime.core.TimedTask import TimedTask

logging.basicConfig(level=logging.INFO, force=True)


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
@taskname_option(required=True, help_suffix="delete", allow_alias=False)
@click.option("--force", is_flag=True, default=False, help="skip confirmation message")
@click.pass_context
def delete(ctx: click.Context, taskname: str, force: bool) -> None:
    """
    Deletes the task with the given name.
    """
    task_index: TaskIndex = ctx.obj
    if taskname in task_index.task_names:
        if force or click.confirm(f"Are you sure you'd like to delete {taskname}?"):
            task_index.delete(taskname)
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
def time(ctx: click.Context, taskname: str, compare_style: CompareStyle) -> None:
    """
    Interactively times a run of the given task. Asks
    user to hit enter at beginning/end of all splits.
    """
    task_index: TaskIndex = ctx.obj
    task_index[taskname].time(compare_style=compare_style)
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
    letter="s",
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
@taskname_option(required=True, help_suffix="print", allow_alias=True)
@click.pass_context
def print_times(ctx: click.Context, taskname: str) -> None:
    """
    Prints the times of a given task.
    """
    task_index: TaskIndex = ctx.obj
    times: pd.DataFrame = task_index[taskname].time_set.times
    time_columns: List[str] = [column for column in times.columns if column != "date"]
    print_pandas_dataframe(times, time_columns=time_columns, print_func=click.echo)
    return


@main.command()
@taskname_option(required=True, help_suffix="make histogram(s) for", allow_alias=True)
@all_segments_option
@cumulative_segments_option
@plot_type_option(default=PlotType.HISTOGRAM)
@string_list_option(
    "segments", "segment name(s)", required=False, help_suffix="make histogram(s) of"
)
@click.option("--file_name", "-f", required=False, type=str, help="png file to save")
@click.option(
    "--headless",
    "-h",
    required=False,
    default=False,
    type=bool,
    is_flag=True,
    help="skips interactive plotting. Usually used with --file_name",
)
@click.pass_context
def plot(
    ctx: click.Context,
    taskname: str,
    all_segments: bool,
    cumulative_segments: bool,
    plot_type: PlotType,
    segments: List[str] = None,
    file_name: str = None,
    headless: bool = False,
) -> None:
    """
    Plots distribution of times.

    Can plot either histograms or scatter plots (against completion index) of times.
    """
    task_index: TaskIndex = ctx.obj
    timed_task: TimedTask = task_index[taskname]
    time_set: TimeSet = timed_task.time_set
    if not time_set.is_multi_segment:
        segments = None
    elif all_segments:
        segments = time_set.segments
    plotter = TimePlotter(
        timed_task=timed_task, segments=segments, cumulative=cumulative_segments
    )
    plotter.plot(plot_type, file_name=file_name, headless=headless)
    return


@main.command()
@taskname_option(
    required=True, help_suffix="find correlations amongst segments", allow_alias=True
)
@string_list_option(
    "segments", "segment names", required=False, help_suffix="find correlations amongst"
)
@click.pass_context
def correlation(ctx: click.Context, taskname: str, segments: List[str] = None) -> None:
    """
    Plots correlation matrix of segment times of a task.

    NOTE: correlations are only meaningful when the task
    is multi-segment and multiple segments are chosen.
    """
    task_index: TaskIndex = ctx.obj
    try:
        plot_correlations(timed_task=task_index[taskname], segments=segments)
    except ValueError:
        raise click.UsageError("Correlations are not meaningful for single segments.")
    return


@main.command(name="list")
@taskname_option(required=False, help_suffix="list segments of", allow_alias=True)
@click.pass_context
def list_command(ctx: click.Context, taskname: str) -> None:
    """
    Lists names/aliases of all tasks or segments of one task.
    """
    task_index: TaskIndex = ctx.obj
    if taskname is None:
        click.echo(f"\n{task_index.alias_summary}\n")
    else:
        timed_task: TimedTask = task_index[taskname]
        click.echo(f"\nTask name: {timed_task.name}")
        click.echo(f"\tAliases: {', '.join(sorted(timed_task.aliases))}")
        click.echo(f"\tSegments: {', '.join(timed_task.segments)}\n")
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
        try:
            confirmation_message: str = (
                f"Current: {name} -> "
                f"{DEFAULT_GLOBAL_CONFIG[name].stringifier(global_config[name])}. "
                f"Should it be changed to {name} -> {value}?"
            )
        except KeyError:
            raise KeyError(
                f"{name} not a valid config variable name. The available "
                f"names are {[key for key in global_config]}"
            )
        if click.confirm(confirmation_message):
            data_directory_confirmation: str = (
                "Changing the data directory is potentially destructive. "
                "It is recommended that you save an image of the data "
                'directory if you have not already done so (see "snapshot" '
                "command). Are you sure you want to change data_directory?"
            )
            if (name != "data_directory") or click.confirm(data_directory_confirmation):
                global_config[name] = value
    return


@main.command()
@click.option(
    "--name",
    "-n",
    required=True,
    default="cubetime_data_snapshot.zip",
    help="path to file to save (with .zip or .tar.gz extension)",
)
@click.option(
    "--force",
    "-f",
    default=False,
    required=True,
    is_flag=True,
    help="if true, overwrites file if it already exists",
)
def snapshot(name: str, force: bool) -> None:
    """
    Creates a snapshot of the data directory.
    """
    make_data_snapshot(name, force=force)
    return


@main.command()
@string_list_option(
    "tasknames",
    "task name(s) or alias(es)",
    required=False,
    help_suffix="find time spent on",
    letter="t",
)
@click.pass_context
def time_spent(ctx: click.Context, tasknames: List[str] = None) -> None:
    """
    Gets the total time spent on all tasks (or just one).
    """
    task_index: TaskIndex = ctx.obj
    task_index.print_time_spent(tasknames, print_func=click.echo)
    return


if __name__ == "__main__":
    main()
