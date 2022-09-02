import click
from enum import Enum
from typing import Callable

class CompareStyle(Enum):
    """Class to represent different ways of comparing times"""

    NONE = 0
    BEST_RUN = 1
    BEST_SEGMENTS = 2
    WORST_RUN = 3
    WORST_SEGMENTS = 4
    LAST_RUN = 5
    AVERAGE_SEGMENTS = 6

def compare_style_option(default: CompareStyle) -> Callable[[Callable], Callable]:
    return click.option(
        "--comparestyle",
        prompt="Enter compare style",
        type=click.Choice(CompareStyle.__members__, case_sensitive=False),
        show_choices=True,
        default=default,
        callback=(lambda ctx, param, s: CompareStyle.__members__[s]),
        required=True,
    )