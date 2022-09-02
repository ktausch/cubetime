import os
from typing import Any, Dict, List, Optional
from typing_extensions import Self
import yaml

from cubetime.TimeSet import TimeSet

CONSOLIDATION_THRESHOLD: int = 10


class TimedTask:
    """
    Class to store info about how a timed task's time are stored by cubetime
    """

    def __init__(
        self,
        name: str,
        directory: str,
        segments: List[str],
        min_best: bool,
    ):
        """
        Creates a new task given its name, location, and segment info

        Args:
            name: name of the task
            directory: directory to save config and data in
            segments: list of string names of segments in this timed task
            min_best: determines whether small times are better (True) or worse (False)
        """
        self.name: str = name
        self.directory: str = directory
        self.segments: List[str] = segments
        self.min_best: bool = min_best
        self._time_set: Optional[TimeSet] = None

    @property
    def data_file_name(self) -> str:
        """
        Gets the path to the file containing the data for this task.

        Returns:
            path to file from which TimeSet can be loaded
        """
        return os.path.join(self.directory, "data.parquet")

    @property
    def time_set(self) -> TimeSet:
        """
        Gets the stored time set if one exists.

        Returns:
            TimeSet object containing existing data for this task
        """
        if self._time_set is None:
            try:
                self._time_set = TimeSet.load(
                    self.data_file_name, min_best=self.min_best
                )
            except FileNotFoundError:
                self._time_set = TimeSet.create_new(
                    segments=self.segments, min_best=self.min_best
                )
        return self._time_set

    @staticmethod
    def make_config_filename(directory: str) -> str:
        """
        Makes a config file path from the directory it is stored in.

        Args:
            directory: directory in which to find config file

        Returns:
            full path to config file
        """
        return os.path.join(directory, "config.yml")

    @property
    def config_filename(self) -> str:
        """
        The filename of the config file of this task.

        Returns:
            absolute path to config file for this task
        """
        return self.make_config_filename(self.directory)

    @classmethod
    def from_directory(cls, directory: str) -> Self:
        """
        Creates a new TimedTask from a directory with a config file.

        Args:
            directory: absolute path to directory with config file

        Returns:
            TimedTask stored in directory
        """
        kwargs: Dict[str, Any] = {"directory": directory}
        with open(cls.make_config_filename(directory), "r") as file:
            kwargs.update(yaml.safe_load(file))
        return cls(**kwargs)

    def save(self) -> None:
        """
        Saves the config describing this timed task in the directory.
        """
        to_dump: Dict[str, Any] = {
            "name": self.name,
            "segments": self.segments,
            "min_best": self.min_best,
        }
        with open(self.config_filename, "w") as file:
            yaml.dump(to_dump, file)
        return

    def time(self, *args, **kwargs) -> None:
        """
        Interactively times a new run for this task.
        """
        self.time_set.time(*args, **kwargs)
        self.time_set.save(self.data_file_name)
        return
