import click
import logging
import numpy as np
import time
from typing import List, Optional

from cubetime.core.CompareTime import ComparisonSet

logger = logging.getLogger(__name__)


class Timer:
    """An interactive multi-segment timer."""

    def __init__(self, segments: List[str], comparison: ComparisonSet):
        """
        Creates a new timer with the given comparison.

        Args:
            segments: the segments of to time
            comparison: comparison times with which to determine color/differential
        """
        self.segments: List[str] = segments
        self.comparison: ComparisonSet = comparison

    def _time_loop_iteration(self, unix_times: List[float]) -> bool:
        """
        Performs a loop of garnering user input while timing a run.

        This function asks the user to press enter when they've completed the next
        segment. Alternatively, the user could KeyboardInterrupt to unto the last
        segment completed (or cancel entirely if no segments have been completed) or
        type "abort" to abort a run without finishing the rest of the segments.

        Args:
            unix_times: list of times marking beginnings/ends of segments. When
                entering into first iteration of the loop, unix_times should have
                one element, the time of the beginning of the first segment.
                This list will be modified in this function.

        Returns:
            True if input loop should be continued, False if it should be broken
        """
        segment_index: int = len(unix_times) - 1
        if segment_index == len(self.segments):
            return False
        prompt_message: str = (
            f'Finish {self.segments[segment_index]} (or "abort" to cancel run)'
        )
        try:
            prompt_input: str = click.prompt(
                prompt_message, default="", show_default=False
            )
        except (click.Abort, KeyboardInterrupt):
            unix_times.pop()
            if unix_times:
                click.echo(f'Undoing finish of "{self.segments[segment_index - 1]}"')
                return True
            else:
                raise KeyboardInterrupt("Aborting run!")
        lower_input = prompt_input.lower()
        if lower_input == "abort":
            return False
        else:
            if lower_input == "skip":
                unix_times.append(np.nan)
            else:
                unix_times.append(time.time())
            self.comparison.print_segment_terminal_output(
                segment_index=segment_index,
                standalone=(unix_times[-1] - unix_times[-2]),
                cumulative=(unix_times[-1] - unix_times[0]),
                print_func=click.echo,
            )
            return True

    def time(self) -> Optional[np.ndarray]:
        """
        Interactively times a new run.

        Returns:
            times for each of the segments
        """
        click.prompt(f"Start {self.segments[0]}", default="", show_default=False)
        unix_times: List[float] = [time.time()]
        while self._time_loop_iteration(unix_times):
            pass
        final_times: np.ndarray = np.ones(len(self.segments)) * np.nan
        final_times[: len(unix_times)] = np.array(unix_times[1:]) - unix_times[0]
        if np.all(np.isnan(final_times)):
            logger.warning(
                "Not adding new time because run aborted during first segment."
            )
            return None
        elif click.confirm("Should this run be added?"):
            logger.info("Adding new completion time.")
            return final_times
        else:
            logger.info("Not adding new completion time at user request.")
            return None
