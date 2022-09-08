import click
from typing import Any, List, Optional

from cubetime.CompareStyle import CompareStyle, compare_style_option
from cubetime.Config import global_config
from cubetime.Plotting import plot_type_option, PlotType, TimePlotter
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
@plot_type_option(default=PlotType.HISTOGRAM)
@string_list_option(
    "segments", "segment name(s)", required=False, help_suffix="make histogram(s) of"
)
@click.pass_context
def plot(
    ctx: click.Context,
    taskname: str,
    all_segments: bool,
    cumulative_segments: bool,
    plot_type: PlotType,
    segments: List[str] = None,
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
    plotter.plot(plot_type)
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
