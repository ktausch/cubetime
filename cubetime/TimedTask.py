import logging
import os
import shutil
from typing import Any, Callable, Dict, List, Optional, Set
from typing_extensions import Self
import yaml

from cubetime.TimeSet import TimeSet

logger = logging.getLogger(__name__)


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
        aliases: Set[str] = None,
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
        self.aliases: Set[str] = set() if aliases is None else aliases

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
        logger.debug(f"Loading task from directory {directory}.")
        return cls(**kwargs)

    def save(self) -> None:
        """
        Saves the config describing this timed task in the directory.
        """
        to_dump: Dict[str, Any] = {
            "name": self.name,
            "segments": self.segments,
            "min_best": self.min_best,
            "aliases": self.aliases,
        }
        with open(self.config_filename, "w") as file:
            yaml.dump(to_dump, file)
        return

    def add_alias(self, alias: str) -> None:
        """
        Adds an alias of this task.

        Throws a ValueError if the alias is the same as the name

        Args:
            alias: alternate string that can be used to refer to this task
        """
        if alias == self.name:
            raise ValueError("Task alias cannot be identical to name.")
        self.aliases.add(alias)
        self.save()
        return

    def remove_alias(self, alias: str) -> None:
        """
        Removes an alias.

        Throws KeyError if alias does not exist.

        Args:
            alias: the alias to remove
        """
        self.aliases.remove(alias)
        return

    def time(self, *args, **kwargs) -> None:
        """
        Interactively times a new run for this task.
        """
        self.time_set.time(*args, **kwargs)
        self.time_set.save(self.data_file_name)
        return

    @property
    def name_summary(self) -> str:
        """
        Summarizes the name and aliases of this task

        Returns:
            a summary of the naming of this task. Contains name and aliases.
        """
        return f"Task name: {self.name}\nAliases: {sorted(self.aliases)}"

    def print_detailed_summary(self, print_func: Callable[..., None] = print) -> None:
        """
        Prints a detailed summary of the data stored in this object.

        Shows everything from standalone_summary (+ cumulative_summary if multi-segment)

        Args:
            print_func: function to use to print
        """
        print_func(f"\n{self.name_summary}")
        self.time_set.print_detailed_summary(print_func=print_func)
        return

    def delete(self):
        """Deletes this task from disk."""
        shutil.rmtree(self.directory)
        return

    @property
    def total_time_spent(self):
        """
        Gets the total amount of time spent on this task.

        Returns:
            amount of time in seconds spent on this task
        """
        return self.time_set.total_time_spent
