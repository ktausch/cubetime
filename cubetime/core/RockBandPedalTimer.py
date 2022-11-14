from contextlib import contextmanager
from ctypes import cdll, CFUNCTYPE, c_char_p, c_int
from datetime import datetime
import logging
import time
from typing import Dict, Tuple

import click
import numpy as np
has_pyaudio: bool
try:
    import pyaudio
except ImportError:
    has_pyaudio = False
else:
    has_pyaudio = True

from cubetime.core.Timer import Timer


logger = logging.getLogger(__name__)
SAMPLING_RATE_HZ: int = 44100
NUM_SAMPLES_PER_CHUNK: int = 50
# using 50 samples per chunk means audio is processed about every millisecond


@contextmanager
def noalsaerr():
    """Context manager that ignores ALSA errors."""

    def py_error_handler(filename, line, function, err, fmt):
        pass

    ERROR_HANDLER_FUNC = CFUNCTYPE(None, c_char_p, c_int, c_char_p, c_int, c_char_p)
    asound = cdll.LoadLibrary('libasound.so')
    asound.snd_lib_error_set_handler(ERROR_HANDLER_FUNC(py_error_handler))
    yield
    asound.snd_lib_error_set_handler(None)


class RockBandPedalTimer(Timer):
    """Timer that uses a rock band pedal that is set as the default microphone."""

    def __init__(self, *args, **kwargs):
        """Initializes a new pedal-based timer. Same args/kwargs as Timer class."""
        super().__init__(*args, **kwargs)
        if not has_pyaudio:
            raise NotImplementedError(
                "RockBandPedalTimer cannot be used unless optional "
                "dependency pyaudio is installed."
            )
        self._started: bool = False
        self._extreme_on_previous: bool = False

    def restart(self) -> None:
        """Restarts the timer: sets unix times to [now] and sets the _started flag."""
        super().restart()
        self._started = True
        return

    def _on_press(self) -> bool:
        """
        The function called when the pedal is pressed.

        Returns:
            True if all segments have been completed, False otherwise
        """
        log_message: str = f"Received pedal press at {datetime.now()}."
        if self._started:
            segment_index: int = len(self.unix_times) - 1
            segment: str = self.segments[segment_index]
            logger.debug(f"{log_message} Marking {segment} as complete.")
            self._add_new_segment(segment_index, skipped=False)
            return not self._print_next_segment_info()
        else:
            logger.debug(f"{log_message} Starting timer.")
            self.restart()
            self._print_next_segment_info()
            return False

    def _process_audio(
        self, data: bytes, frame_count: int, time_info: Dict[str, float], status: int
    ) -> Tuple[np.ndarray, int]:
        """
        Processes a batch of audio data from the pedal microphone.

        Args:
            data: the bytes of audio data from the microphone (16 bit ints)
            frame_count: the number of data points in data
            time_info: information about timing of the data
            status: audio stream status

        Returns:
            (array, flag):
                array: numpy array of the 16 bit ints of data
                flag: pyaudio.paComplete if done, pyaudio.paContinue otherwise
        """
        array: np.ndarray = np.frombuffer(data, dtype=np.int16)
        flag: int = pyaudio.paContinue
        if (np.min(array) < -16500):
            if not self._extreme_on_previous:
                if self._on_press():
                    flag = pyaudio.paComplete
                self._extreme_on_previous = True
        else:
            self._extreme_on_previous = False
        return (array, flag)
    
    def _time(self) -> None:
        """Times a run using a microphone-like rock band drum pedal"""
        with noalsaerr():
            audio = pyaudio.PyAudio()
        try:
            input_device_index: int = next(
                index
                for index in range(audio.get_device_count())
                if audio.get_device_info_by_index(index)["name"].lower() == "default"
            )
        except StopIteration:
            raise RuntimeError("Could not find a default microphone.")
        stream: pyaudio.Stream = audio.open(
            format=pyaudio.paInt16,
            channels=1,
            rate=SAMPLING_RATE_HZ,
            input=True,
            frames_per_buffer=NUM_SAMPLES_PER_CHUNK,
            stream_callback=self._process_audio,
            input_device_index=input_device_index,
        )
        click.echo(f"Hit the pedal to start {self.segments[0]}")
        stream.start_stream()
        try:
            while stream.is_active():
                time.sleep(0.1)
        except KeyboardInterrupt:
            logger.info(
                "KeyboardInterrupt while using pedal timer. Aborting rest of run."
            )
        stream.stop_stream()
        stream.close()
        audio.terminate()
        return
