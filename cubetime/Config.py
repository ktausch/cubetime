import os
import pandas as pd
from typing import Any, Dict
import yaml

HOME_DIRECTORY = os.environ["HOME"]
"""Home directory"""

GLOBAL_CONFIG_FILENAME: str = f"{HOME_DIRECTORY}/.config/cubetime.yml"
"""Filename for the global config."""

DEFAULT_GLOBAL_CONFIG: Dict[str, Any] = {
    "data_directory": f"{HOME_DIRECTORY}/.cubetime/data",
    "num_decimal_places": 3,
}
"""Default global configuration dictionary."""


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
        del self.values[key]
        self.save()
        return

    def __str__(self) -> str:
        """
        Gives a string representation of the status of the config.

        Returns:
            string showing all keys and values in the config
        """
        return str(self.values)


global_config = _GlobalConfig()
"""Static container storing global configuration options."""


def decimal_format(number: float) -> str:
    """
    Formats a float using the configured number of decimal places.

    Args:
        number: number to make a string for

    Returns:
        string form of number using configured number of decimal places
    """
    return (f"{{:.{global_config['num_decimal_places']}f}}").format(number)

def pandas_option_context() -> pd.option_context:
    """
    Creates a context in which printed data frames are customized via config.

    Returns:
        context: allows for the following
            ```
            with context:
                print(dataframe)
            ```
    """
    return pd.option_context("display.precision", global_config["num_decimal_places"])
