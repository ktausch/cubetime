from abc import ABCMeta, abstractmethod
import click
import logging
import numpy as np
import time
from typing import List, Optional

from cubetime.core.CompareTime import ComparisonSet

logger = logging.getLogger(__name__)


class Timer(metaclass=ABCMeta):
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
        self._unix_times: Optional[List[float]] = None

    @property
    def unix_times(self) -> List[float]:
        """
        Gets the list of start/end timestamps of current run.

        Returns:
            List of timestamps [start1, end1, end2, ...]
        """
        if self._unix_times is None:
            self._unix_times = []
        return self._unix_times

    def restart(self) -> None:
        """Sets the unix times to list of one timestamp: now."""
        self._unix_times = None
        self.unix_times.append(time.time())
        return

    def _undo(self, segment_index: int) -> None:
        """
        Undoes the most recent segment finishing time.

        Args:
            segment_index: segment currently being timed (the one after the one to undo)
        """
        self.unix_times.pop()
        logger.info(f'Undoing finish of {self.segments[segment_index - 1]}')
        if self.unix_times:
            return True
        else:
            self.restart()
            return False

    def _add_new_segment(self, segment_index: int, skipped: bool) -> None:
        """
        Adds a new segment to the current timestamps.

        Args:
            segment_index: the index of the segment to add
            skipped: if True, nan timestamp is added, otherwise now is added
        """
        self.unix_times.append(np.nan if skipped else time.time())
        self.comparison.print_segment_terminal_output(
            segment_index=segment_index,
            standalone=(self.unix_times[-1] - self.unix_times[-2]),
            cumulative=(self.unix_times[-1] - self.unix_times[0]),
            print_func=click.echo,
        )
        return

    def _print_next_segment_info(self) -> bool:
        """
        Prints out info about the next segment if there is one.

        Returns:
            True if there is a next segment, False if the timer is finished
        """
        try:
            print(f"Current segment: {self.segments[len(self.unix_times) - 1]}")
        except IndexError:
            return False
        else:
            return True

    @abstractmethod
    def _time(self) -> None:
        """
        Technique-specific timing method. Should fill unix_times property.

        NOTE: This is an abstract method that should be overridden by subclass of Timer.
        """
        raise NotImplementedError("_time method of Timer base class can't be called.")

    def time(self) -> Optional[np.ndarray]:
        """
        Interactively times a new run.

        Returns:
            times for each of the segments, None if run shouldn't be added
        """
        self._time()
        if len(self.unix_times) == 0:
            logger.warning("Timer was never started in _time method.")
            return None
        final_times: np.ndarray = np.ones(len(self.segments)) * np.nan
        final_times[: len(self.unix_times) - 1] = self.unix_times[1:]
        final_times -= self.unix_times[0]
        if np.all(np.isnan(final_times)):
            logger.warning(
                "Not adding new time because run aborted during first segment."
            )
            return None
        elif click.confirm("Should this run be added?", default=None):
            logger.info("Adding new completion time.")
            return final_times
        else:
            logger.info("Not adding new completion time at user request.")
            return None
