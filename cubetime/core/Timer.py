import click
import logging
import numpy as np
from pynput.keyboard import Controller as KeyboardController
from pynput.keyboard import Events as KeyboardEvents
from pynput.keyboard import Key as KeyboardKey
import signal
import time
from typing import List, Optional

from cubetime.core.CompareTime import ComparisonSet
from cubetime.core.Config import global_config

logger = logging.getLogger(__name__)

SWALLOW_TIMEOUT: int = 1


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
        """
        Sets the unix times to list of one timestamp: now.
        """
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
        logger.info(f'Undoing finish of "{self.segments[segment_index - 1]}"')
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

    def _time_loop_iteration(self, event: KeyboardEvents.Press) -> Optional[bool]:
        """
        Performs a loop of garnering user input while timing a run.

        This function asks the user to press enter when they've completed the next
        segment. Alternatively, the user could KeyboardInterrupt to unto the last
        segment completed (or cancel entirely if no segments have been completed) or
        type "abort" to abort a run without finishing the rest of the segments.

        Args:
            event: the event detected by the keyboard listener from pynput

        Returns:
            True if input loop should be continued,
            False if it should be broken,
            None if this event did nothing
        """
        segment_index: int = len(self.unix_times) - 1
        log_dispatch = lambda func, event: logger.debug(
            f"Dispatching to {func} because {event.key} was pressed."
        )
        if event.key in global_config["undo_keys"]:
            log_dispatch("undo", event)
            return self._undo(segment_index)
        elif event.key in global_config["continue_keys"]:
            log_dispatch("continue", event)
            self._add_new_segment(segment_index, skipped=False)
            return True
        elif event.key in global_config["skip_keys"]:
            log_dispatch("skip", event)
            self._add_new_segment(segment_index, skipped=True)
            return True
        elif event.key in global_config["abort_keys"]:
            log_dispatch("abort", event)
            return False
        return None

    def _print_next_segment_info(self) -> bool:
        """
        Prints out info about the next segment if there is one.

        Returns:
            True if there is a next segment, False if the timer is finished
        """
        try:
            print(
                f"Next segment: {self.segments[len(self.unix_times) - 1]} "
                "(press ESC to abort!)"
            )
        except IndexError:
            return False
        else:
            return True

    @staticmethod
    def _swallow_all_queued_keystrokes() -> None:
        """Swallows keystrokes from run by calling input() repeatedly for one second."""
        signal.signal(signal.SIGALRM, lambda *args: exec("raise StopIteration"))
        controller: KeyboardController = KeyboardController()
        controller.press(KeyboardKey.enter)
        controller.release(KeyboardKey.enter)
        try:
            signal.alarm(SWALLOW_TIMEOUT)
            while True:
                input()
        except StopIteration:
            pass
        return

    def time(self) -> Optional[np.ndarray]:
        """
        Interactively times a new run.

        Returns:
            times for each of the segments, None if run shouldn't be added
        """
        click.prompt(
            f"Press enter to start {self.segments[0]}", default="", show_default=False
        )
        self.restart()
        self._print_next_segment_info()
        with KeyboardEvents() as events:
            for event in events:
                if isinstance(event, KeyboardEvents.Press):
                    iteration_result: Optional[bool] = self._time_loop_iteration(event)
                    if iteration_result is None:
                        continue
                    elif not (iteration_result and self._print_next_segment_info()):
                        break
            self._swallow_all_queued_keystrokes()
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
