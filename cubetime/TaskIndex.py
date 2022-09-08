import os
from typing import Callable, Collection, Dict, List, Optional

import pandas as pd

from cubetime.Config import global_config
from cubetime.TimedTask import TimedTask
from cubetime.TimeSet import TimeSet, TIME_AGG_FUNCS
from cubetime.Utilities import print_pandas_dataframe

SPECIAL_CHARACTERS: List[str] = [","]
"""Characters that are not allowed in segment or task names."""


class TaskIndex:
    """
    An index of all timed tasks stored in cubetime.
    """

    def __init__(self):
        """
        Creates the index by reading from the global config.
        """
        self.data_directory: str = global_config["data_directory"]
        os.makedirs(self.data_directory, exist_ok=True)
        self._timed_tasks: Optional[Dict[str, TimedTask]] = None
        self._alias_dictionary: Optional[Dict[str, str]] = None

    @property
    def timed_tasks(self) -> Dict[str, TimedTask]:
        """
        Loads all timed tasks from their configs.

        Returns:
            dictionary from timed task name to the task itself
        """
        if self._timed_tasks is None:
            tasks: List[TimedTask] = []
            for element in os.scandir(self.data_directory):
                if element.is_dir():
                    tasks.append(TimedTask.from_directory(element.path))
            self._timed_tasks = {task.name: task for task in tasks}
        return self._timed_tasks

    @property
    def task_names(self) -> List[str]:
        """
        Lists all task names.

        Returns:
            list of task names sorted alphabetically
        """
        return sorted(self.timed_tasks)

    @property
    def alias_dictionary(self) -> Dict[str, str]:
        """
        A dictionary that allows task names to be found from aliases.

        Returns:
            dictionary from name/alias to name
        """
        if self._alias_dictionary is None:
            self._alias_dictionary = {}
            for (name, task) in self.timed_tasks.items():
                self._alias_dictionary[name] = name
                for alias in task.aliases:
                    self._alias_dictionary[alias] = name
        return self._alias_dictionary

    def __getitem__(self, key: str) -> TimedTask:
        """
        Gets the task with the given name.

        Args:
            key: name of the task to find

        Returns:
            TimedTask object storing given task
        """
        try:
            return self.timed_tasks[self.alias_dictionary[key]]
        except KeyError:
            raise KeyError(f'No indexed task named (or aliased) "{key}".')

    @staticmethod
    def check_names(*names: str) -> None:
        """
        Checks given strings for special characters not allowed in task/segment names.

        Throws ValueError if any of the special characters appear.

        Args:
            names: task and/or segment name(s) to check
        """
        for name in names:
            if any(character in name for character in SPECIAL_CHARACTERS):
                raise ValueError(
                    "The following characters are not allowed in "
                    f"task or segment names, {SPECIAL_CHARACTERS}."
                )
        return

    def new_timed_task(
        self,
        name: str,
        segments: List[str],
        leaf_directory: str = None,
        min_best: bool = True,
        aliases: Collection[str] = None,
    ) -> None:
        """
        Adds a new task to the index.

        Args:
            name: name of the task
            segments: segments of the task
            leaf_directory: the name of the directory within package's data folder
            min_best: if True, smaller times are considered better than larger times

        Returns:
            the new task (whose config has been saved)
        """
        if name in self.alias_dictionary:
            raise ValueError("Cannot add two timed tasks with the same name.")
        self.check_names(name, *segments)
        if leaf_directory is None:
            leaf_directory = "".join(c if c.isalnum() else "_" for c in name)
        directory = os.path.join(self.data_directory, leaf_directory)
        try:
            os.makedirs(directory, exist_ok=False)
        except FileExistsError:
            raise FileExistsError(
                f"{leaf_directory} already exists within {self.data_directory}, and "
                f'creating new task "{name}" with that directory, would overwrite it.'
            )
        self.alias_dictionary[name] = name
        new_task: TimedTask = TimedTask(
            name=name, directory=directory, segments=segments, min_best=min_best
        )
        self.timed_tasks[name] = new_task
        new_task.save()
        if aliases is not None:
            self.add_aliases(name, aliases)
        return

    def print_summary(
        self, tasknames: List[str] = None, print_func: Callable[..., None] = print
    ) -> None:
        """
        Prints a summary of one or more tasks.

        Args:
            tasknames: comma separated list of tasks to print (or None for all tasks)
            print_func: function to use for printing
        """
        task_names: List[str] = self.task_names if tasknames is None else tasknames
        summary: pd.DataFrame = pd.DataFrame()
        for key in task_names:
            task: TimedTask = self[key]
            time_set: TimeSet = task.time_set
            summary[task.name] = time_set.cumulative_summary.loc[time_set.segments[-1]]
        print_func()
        print_pandas_dataframe(summary, time_rows=TIME_AGG_FUNCS, print_func=print_func)
        print_func()
        return

    @property
    def alias_summary(self) -> str:
        """
        Summarizes all stored task names and aliases.

        Returns:
            a multi-line string where each line contains a task name followed by aliases
        """
        summary_lines: List[str] = []
        for name in self.task_names:
            timed_task: TimedTask = self.timed_tasks[name]
            summary_lines.append(f'{name}: {", ".join(sorted(timed_task.aliases))}')
        return '\n'.join(summary_lines)

    def add_alias(self, key: str, new_alias: str) -> None:
        """
        Adds an alias to a task in the index.

        Throws a ValueError if the new alias is not globally unique.

        Args:
            key: name or existing alias of task to add alias to
            new_alias: must be globally unique (i.e. is not an alias of any other task)
        """
        timed_task: TimedTask = self[key]
        if new_alias in self.alias_dictionary:
            raise ValueError(
                f'Cannot add new alias "{new_alias}" because that alias already exists '
                f'and aliases the task named "{self.alias_dictionary[new_alias]}"'
            )
        self.check_names(new_alias)
        timed_task.add_alias(new_alias)
        self.alias_dictionary[new_alias] = timed_task.name
        return

    def add_aliases(self, key: str, aliases: Collection[str]) -> None:
        """
        Adds aliases to a stored task.

        Args:
            key: name or existing alias of task to add aliases to
            aliases: string aliases to add
        """
        failed_aliases: Dict[str, str] = {}
        for alias in aliases:
            try:
                self.add_alias(key, alias)
            except ValueError:
                failed_aliases[alias] = self.alias_dictionary[alias]
        if failed_aliases:
            failed_alias_strings = [
                f'"{alias}"->"{name}"' for (alias, name) in failed_aliases.items()
            ]
            raise ValueError(
                f"Aliases {list(failed_aliases)} couldn't be added because they "
                f"already exist as names/aliases ({','.join(failed_alias_strings)})."
            )
        return

    def remove_alias(self, alias: str) -> None:
        """
        Removes an alias from a stored task.

        Throws KeyError if no such alias exists.
        Throws ValueError if alias is the name of a task.

        Args:
            alias: string alias to remove
        """
        name: str = self.alias_dictionary[alias]
        if alias == name:
            raise ValueError(
                f"Cannot remove {name} from aliases because it is the name of a task."
            )
        self.timed_tasks[name].remove_alias(alias)
        self.alias_dictionary.pop(alias)
        return

    def remove_aliases(self, aliases: List[str]) -> None:
        """
        Removes the given aliases from the index.

        Throws a ValueError if one or more aliases is a name.

        Args:
            aliases: list of aliases to remove, non-existent aliases are ignored
        """
        aliases_that_are_names: List[str] = []
        for alias in aliases:
            try:
                self.remove_alias(alias)
            except ValueError:
                aliases_that_are_names.append(alias)
            except KeyError:
                pass
        if aliases_that_are_names:
            raise ValueError(
                f"Could not remove {aliases_that_are_names} "
                "because they are names, not aliases"
            )
        return

    def delete(self, name: str) -> None:
        """
        Deletes the task with the given name.

        Args:
            name: the string name of the task to delete (aliases not allowed!)
        """
        timed_task: TimedTask = self[name]
        if name != timed_task.name:
            raise ValueError(
                f"Cannot delete a task by alias. Use the full name ({timed_task.name})."
            )
        self.alias_dictionary.pop(timed_task.name)
        for alias in timed_task.aliases:
            self.alias_dictionary.pop(alias)
        timed_task.delete()
        return
