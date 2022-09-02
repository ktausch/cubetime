import os
from typing import Dict, List, Optional

from cubetime.Config import global_config
from cubetime.TimedTask import TimedTask


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

    def __getitem__(self, key: str) -> TimedTask:
        """
        Gets the task with the given name.

        Args:
            key: name of the task to find

        Returns:
            TimedTask object storing given task
        """
        try:
            return self.timed_tasks[key]
        except KeyError:
            raise KeyError(
                f'No indexed task named "{key}". Did you mean to create one first?'
            )
        

    def new_timed_task(
        self,
        name: str,
        segments: List[str],
        leaf_directory: str = None,
        min_best: bool = True,
    ) -> TimedTask:
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
        if name in self.timed_tasks:
            raise ValueError("Cannot add two timed tasks with the same name.")
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
        new_task: TimedTask = TimedTask(
            name=name, directory=directory, segments=segments, min_best=min_best
        )
        self.timed_tasks[name] = new_task
        new_task.save()
        return new_task
