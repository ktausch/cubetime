import logging
import os
from typing import Any, Callable, Dict, Iterator, Set
import yaml

logger = logging.getLogger(__name__)

HOME_DIRECTORY = os.environ["HOME"]
"""Home directory"""

GLOBAL_CONFIG_FILENAME: str = f"{HOME_DIRECTORY}/.config/cubetime.yml"
"""Filename for the global config."""

DEFAULT_GLOBAL_CONFIG: Dict[str, Any] = {
    "data_directory": f"{HOME_DIRECTORY}/.cubetime/data",
    "num_decimal_places": 1,
}
"""Default global configuration dictionary."""

PROTECTED_CONFIG_NAMES: Set[str] = {"data_directory"}


class _GlobalConfig:
    """
    Class to store the global configuration of cubetime
    """

    def __init__(self):
        """
        Creates the global config singleton.
        """
        self.values: Dict[str, Any] = {}
        if os.path.exists(GLOBAL_CONFIG_FILENAME):
            self.load()
        else:
            self.values.update(DEFAULT_GLOBAL_CONFIG)
            self.save()

    def save(self) -> None:
        """
        Saves the config to the yaml file.
        """
        with open(GLOBAL_CONFIG_FILENAME, "w") as file:
            yaml.dump(self.values, file)
        return

    def load(self) -> None:
        """
        Loads the config from the yaml file.
        """
        with open(GLOBAL_CONFIG_FILENAME, "r") as file:
            config = yaml.safe_load(file)
        assert isinstance(config, dict)
        self.values = config
        return

    def __getitem__(self, key: str) -> Any:
        """
        Gets the value associated with the config variable.

        Args:
            key: the config variable to retrieve

        Returns:
            the value stored for the given key
        """
        return self.values[key]

    def __setitem__(self, key: str, value: Any) -> None:
        """
        Sets a config value associated with the given key.

        Args:
            key: the config variable to change
            value: the value to set for the given key
        """
        self.values[key] = value
        logging.info(f"Setting global config variable {key} to {value}.")
        self.save()
        return

    def __contains__(self, key: str) -> bool:
        """
        Checks if key represents stored config variable.

        Args:
            key: the config variable to check for

        Returns:
            True if key represents stored variable, False otherwise
        """
        return key in self.values

    def __delitem__(self, key: str) -> None:
        """
        Deletes the given stored config variable.

        Args:
            key: the config variable to delete
        """
        if key in PROTECTED_CONFIG_NAMES:
            raise KeyError(
                f"Config variable {key} cannot be deleted. It can only be modified."
                "If you really think this should be done, you can manually delete "
                f"{key} entry from the config file at {GLOBAL_CONFIG_FILENAME}."
            )
        del self.values[key]
        logging.info(f"Deleting global config variable with name {key}.")
        self.save()
        return

    def __str__(self) -> str:
        """
        Gives a string representation of the status of the config.

        Returns:
            string showing all keys and values in the config
        """
        return str(self.values)

    def __iter__(self) -> Iterator:
        """
        Allows for use of for loop inside global config.

        Returns:
            iterator over config dictionary
        """
        return self.values.__iter__()

    def print(self, name: str = None, print_func: Callable[..., None] = print) -> None:
        """
        Prints the configuration.

        Args:
            name: name of the config variable to print. None if all should be printed
            print_func: the function to use for printing
        """
        if name is None:
            for name in self:
                print_func(f"{name}: {self[name]}")
        else:
            if name in self:
                print_func(f"{name}: {self[name]}")
            else:
                print_func(f"{name} not in cubetime config.")
        return


class GlobalConfig:
    """Class allowing for static creation/access of global configuration"""

    instance: _GlobalConfig = _GlobalConfig()
    """Static container storing global configuration settings."""


global_config: _GlobalConfig = GlobalConfig.instance
"""Convenience variable for accessing/modifying global configuration settings"""
