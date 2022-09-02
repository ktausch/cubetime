import click
from typing import List, Optional

from cubetime.CompareStyle import CompareStyle, compare_style_option
from cubetime.Config import pandas_option_context
from cubetime.TaskIndex import TaskIndex


task_option = click.option("--taskname", prompt=True, required=True, type=str)


def parse_segments() -> List[str]:
    """
    Parses a list of segments from user input.

    Returns:
       List with at least one element. If user supplies no input, ["total"] is yielded
    """
    prompt_message: str = (
        "Enter comma-separated segments to use "
        "(empty string creates one 'total' segment)"
    )
    raw: str = click.prompt(prompt_message, type=str, default="")
    if raw:
        return raw.split(",")
    else:
        return ["total"]


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
    """TODO"""
    ctx.obj = TaskIndex()


@main.command()
@click.pass_context
def list_tasks(ctx: click.Context) -> None:
    """TODO"""
    task_index: TaskIndex = ctx.obj
    print(task_index.task_names)
    return


@main.command()
@task_option
@click.pass_context
def add_new_task(ctx: click.Context, taskname: str) -> None:
    """TODO"""
    task_index: TaskIndex = ctx.obj
    task_index.new_timed_task(
        name=taskname,
        segments=parse_segments(),
        leaf_directory=parse_directory(),
        min_best=parse_min_best(),
    )


@main.command()
@task_option
@compare_style_option(CompareStyle.BEST_RUN)
@click.pass_context
def time(ctx: click.Context, taskname: str, comparestyle: CompareStyle) -> None:
    """TODO"""
    task_index: TaskIndex = ctx.obj
    task_index[taskname].time(compare_style=comparestyle)
    return


@main.command()
@task_option
@click.pass_context
def summarize(ctx: click.Context, taskname: str) -> None:
    """TODO"""
    task_index: TaskIndex = ctx.obj
    with pandas_option_context():
        print(task_index[taskname].time_set.segment_summary)


if __name__ == "__main__":
    main()
