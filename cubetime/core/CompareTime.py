from enum import Enum
import numpy as np
from typing import Optional
from typing_extensions import Self

from cubetime.core.Formatting import make_time_string

COLOR_DICT = {"red": 31, "yellow": 33, "green": 32, "white": 37}
"""Integers to place in terminal formatting strings for colors used in printing."""


class CompareResultDiscrete(Enum):
    """Class representing discrete values of comparisons: better, equal, and worse"""

    WORSE = 0
    EQUAL = 1
    BETTER = 2


class CompareResult:
    """Class storing discrete comparison and numerical comparison of times."""

    def __init__(self, discrete: CompareResultDiscrete, continuous: float):
        """
        Stores the result of a time comparison.

        Args:
            discrete: equal, better, or worse
            continuous: numerical difference, (current - comparison)
        """
        self.discrete: CompareResultDiscrete = discrete
        self.continuous: float = continuous

    def __str__(self) -> str:
        """
        Gives a string representation of the continuous part of the comparison.

        Returns:
            " (num)" where num is same as decimal formatted number with "+"
            preprended if positive if numerical comparison available. If no
            numerical comparison is available, empty string is returned.
        """
        if np.isnan(self.continuous):
            return ""
        return f" ({make_time_string(self.continuous, show_plus=True)})"


def comparison_color(current: CompareResult, best: CompareResult) -> str:
    """
    Determines the color that should be used based on current and best comparisons.

    Args:
        current: the current comparison, which determines green v red
        best: the best comparison, which determines yellow v non-yellow

    Returns:
        color string
    """
    if best.discrete == CompareResultDiscrete.BETTER:
        return "yellow"
    elif current.discrete == CompareResultDiscrete.BETTER:
        return "green"
    elif current.discrete == CompareResultDiscrete.WORSE:
        return "red"
    else:
        return "white"


class CompareTime:
    """Class represents a time comparison. Essentially stores optional numpy array"""

    def __init__(self, data: np.ndarray = None):
        """
        Initializes a new comparison from data.

        Args:
            data: array of segment times if available or None otherwise
        """
        self.data: Optional[np.ndarray] = data

    def __eq__(self, other: Self) -> bool:
        """
        Checks for equality with the given compare time.

        Args:
            other: the object with which to check for equality

        Returns:
            true if both objects have no data or if the data of both are equal
        """
        if (self.data is None) != (other.data is None):
            return False
        if self.data is None:
            return True
        return list(self.data) == list(other.data)

    def compare(
        self, segment_index: int, main_time: float, min_better: bool = True
    ) -> CompareResult:
        """
        Compares a given segment time to this set.

        Args:
            segment_index: which time is being compared
            main_time: the time which is better, worse, or equal to this comparison
            min_better: if True, smaller times are considered better

        Returns:
            CompareResult determining how main_time relates to the times in this object
        """
        if self.data is None:
            return CompareResult(CompareResultDiscrete.EQUAL, np.nan)
        difference: float = main_time - self.data[segment_index]
        if difference == 0:
            return CompareResult(CompareResultDiscrete.EQUAL, difference)
        elif (difference < 0) == min_better:
            return CompareResult(CompareResultDiscrete.BETTER, difference)
        else:
            return CompareResult(CompareResultDiscrete.WORSE, difference)


def terminal_format(string: str, color: str, bold: bool = False) -> str:
    """
    Formats a string to be printed in a specific color and bold status in terminal.

    Args:
        string: the string to format
        color: one of "white", "red", "yellow", "green"
        bold: if True, text is bolded

    Returns:
        string such that when printed, shows text of parameter with given status
    """
    return f"\033[{'1;' if bold else ''}{COLOR_DICT[color.lower()]}m{string}\033[00m"


def compare_terminal_output(
    segment_index: int,
    time: float,
    current: CompareTime,
    best: CompareTime,
    min_best: bool,
) -> str:
    """
    Creates terminal output summarizing a time and comparison.

    Args:
        segment_index: the index of the segment being compared
        time: the newly achieved time
        current: the comparison to make green vs. red distinctions
        best: the comparison to make gold vs. non-gold distinctions
        min_best: True if smaller times are better for current comparison

    Returns:
        string with raw time and time relative to comparison, colored by how it compares
    """
    segment_compare_result: CompareResult = current.compare(
        segment_index, time, min_better=min_best
    )
    best_segment_compare_result: CompareResult = best.compare(
        segment_index, time, min_better=min_best
    )
    segment_color: str = comparison_color(
        segment_compare_result, best_segment_compare_result
    )
    main_string: str = make_time_string(time, show_plus=False)
    compare_string: str = str(segment_compare_result)
    return terminal_format(
        f"{main_string}{compare_string}",
        color=segment_color,
        bold=True,
    )
