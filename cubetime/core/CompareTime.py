from enum import Enum
import numpy as np
from typing import Callable, Optional
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
            return " (????)"
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
        if len(self.data) != len(other.data):
            return False
        this_data = self.data.astype(float)
        other_data = other.data.astype(float)
        where_nan = np.isnan(this_data)
        if np.any(where_nan != np.isnan(other_data)):
            return False
        return np.all(
            np.where(where_nan, 0, this_data) == np.where(where_nan, 0, other_data)
        )

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
        if np.isnan(difference):
            return CompareResult(CompareResultDiscrete.EQUAL, np.nan)
        elif difference == 0:
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
    main_string: str = "????"
    if not np.isnan(time):
        main_string = make_time_string(time, show_plus=False)
    compare_string: str = str(segment_compare_result)
    return terminal_format(
        f"{main_string}{compare_string}",
        color=segment_color,
        bold=True,
    )


class ComparisonSet:
    """Class representing full set of four CompareTime objects to compare to in run."""

    def __init__(
        self,
        current_segments: CompareTime,
        current_cumulatives: CompareTime,
        best_segments: CompareTime,
        best_cumulatives: CompareTime,
        min_best: bool,
    ):
        """
        Assembles a full set of four CompareTime objects.

        Args:
            current_segments: standalone times being compared to
            current_cumulatives: cumulative times being compared to
            best_segments: best standalone times achieved (used to determine gold)
            best_cumulatives: best cumulative times achieved (used to determine gold)
            min_best: True if smaller times are better
        """
        self.current_segments: CompareTime = current_segments
        self.current_cumulatives: CompareTime = current_cumulatives
        self.best_segments: CompareTime = best_segments
        self.best_cumulatives: CompareTime = best_cumulatives
        self.min_best: bool = min_best

    def print_segment_terminal_output(
        self,
        segment_index: int,
        standalone: float,
        cumulative: float,
        print_func: Callable[..., None] = print,
    ) -> None:
        """
        Creates terminal output for the given segment.

        Args:
            segment_index: the segment currently being compared against
            standalone: the standalone time for the given segment
            cumulative: the cumulative time to the given segment
            print_func: the function used to print the output
        """
        segment_time_string: str = compare_terminal_output(
            segment_index=segment_index,
            time=standalone,
            current=self.current_segments,
            best=self.best_segments,
            min_best=self.min_best,
        )
        message: str = f"Segment time: {segment_time_string}"
        if segment_index > 0:
            cumulative_time_string: str = compare_terminal_output(
                segment_index=segment_index,
                time=cumulative,
                current=self.current_cumulatives,
                best=self.best_cumulatives,
                min_best=self.min_best,
            )
            message += f", cumulative time: {cumulative_time_string}"
        print_func(message)
        return
