import click
import logging
from pynput.keyboard import Controller as KeyboardController
from pynput.keyboard import Events as KeyboardEvents
from pynput.keyboard import Key as KeyboardKey
import signal
from typing import Optional

from cubetime.core.Config import global_config
from cubetime.core.Timer import Timer

logger = logging.getLogger(__name__)

SWALLOW_TIMEOUT: int = 1


class KeyboardTimer(Timer):
    """An interactive multi-segment timer."""

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

        def log_dispatch(func: str) -> None:
            logger.debug(f"Dispatching to {func} because {event.key} was pressed.")
            return

        if event.key in global_config["undo_keys"]:
            log_dispatch("undo")
            return self._undo(segment_index)
        elif event.key in global_config["continue_keys"]:
            log_dispatch("continue")
            self._add_new_segment(segment_index, skipped=False)
            return True
        elif event.key in global_config["skip_keys"]:
            log_dispatch("skip")
            self._add_new_segment(segment_index, skipped=True)
            return True
        elif event.key in global_config["abort_keys"]:
            log_dispatch("abort")
            return False
        return None

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

    def _time(self) -> None:
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
        return
