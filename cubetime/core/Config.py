from collections import defaultdict
import logging
import os
from pynput.keyboard import Key as KeyboardKey
from pynput.keyboard import KeyCode as KeyboardKeyCode
from typing import Any, Callable, DefaultDict, Dict, Iterator, List, Set, Tuple, Union
import yaml

logger = logging.getLogger(__name__)

HOME_DIRECTORY = os.environ["HOME"]
"""Home directory"""

GLOBAL_CONFIG_FILENAME: str = f"{HOME_DIRECTORY}/.config/cubetime.yml"
"""Filename for the global config."""


def _key_config_parser(string: str) -> List[Union[KeyboardKey, KeyboardKeyCode]]:
    """
    Parses string into list of keys that can have events in pynput.

    Args:
        string: the string form of the key. Single char or special name

    Returns:
        List of Key/KeyCode objects representing keys on the keyboard
    """
    string_forms: List[str] = list(map(str.lower, string.split(",")))
    final: List[Union[KeyboardKey, KeyboardKeyCode]] = []
    for string_form in string_forms:
        if string_form.isalnum():
            if len(string_form) == 1:
                final.append(KeyboardKeyCode.from_char(string_form))
            else:
                try:
                    final.append(KeyboardKey[string_form])
                except KeyError:
                    raise ValueError(
                        "Special keys must be one of the following: "
                        f"{list(KeyboardKey.__members__)}."
                    )
        else:
            raise ValueError(
                'Keys must be alpha-numeric, either single characters '
                'on the keyboard or special names like "enter".'
            )
    return final


def _string_form_of_key(key: Union[KeyboardKey, KeyboardKeyCode]) -> str:
    """
    Gets the string form of the given key/keycode.

    Args:
        key: Key or KeyCode representing keys that can have events in pynput

    Returns:
        string form of the given key. Single char or special name
    """
    return key.name if isinstance(key, KeyboardKey) else key.char


def _key_config_stringifier(keys: List[Union[KeyboardKey, KeyboardKeyCode]]) -> str:
    """
    Creates a single string form of a key list for printing to console in useful way.

    Args:
        keys: list of Key/KeyCode objects that are in the config variable value

    Returns:
        comma-separated list like the one that could be provided to _key_config_parser
    """
    return ",".join(_string_form_of_key(key) for key in keys)


class ConfigVariable:
    """A class to represent a config variable and its interface to strings."""

    def __init__(
        self,
        string_default: str,
        parser: Callable[[str], Any],
        stringifier: Callable[[Any], str]
    ):
        """
        Initializes a new config variable with the given default and string interface.

        Args:
            string_default: the default value in string form (accepted by parser)
            parser: function that takes in string form and gives out real form
            stringifier: function that takes in real form and gives out string form
        """
        self.default: str = string_default
        self.parser: Callable[[str], Any] = parser
        self.stringifier: Callable[[Any], str] = stringifier


DEFAULT_GLOBAL_CONFIG: Dict[str, ConfigVariable] = {
    "data_directory": ConfigVariable(f"{HOME_DIRECTORY}/.cubetime/data", str, str),
    "num_decimal_places": ConfigVariable("1", int, int),
    "skip_keys": ConfigVariable("s", _key_config_parser, _key_config_stringifier),
    "abort_keys": ConfigVariable("esc,a", _key_config_parser, _key_config_stringifier),
    "continue_keys": ConfigVariable(
        "enter,space,c", _key_config_parser, _key_config_stringifier
    ),
    "undo_keys": ConfigVariable("u,z", _key_config_parser, _key_config_stringifier),
}
"""
Default global configuration dictionary. Keys are variable names and
values are tuples  of the form (default, parser) where default is the default
value and parser creates a  value of the right type from a string.
"""


class _GlobalConfig:
    """
    Class to store the global configuration of cubetime
    """

    def __init__(self):
        """Creates the global config singleton."""
        self.values: Dict[str, Any] = {}
        if os.path.exists(GLOBAL_CONFIG_FILENAME):
            self.load()
        else:
            for key in DEFAULT_GLOBAL_CONFIG:
                self._set(key, DEFAULT_GLOBAL_CONFIG[key].default)
            self.save()

    def _validate_config_variables(self) -> None:
        """Ensures that the config variable names currently set are same as defaults."""
        these_keys: Set[str] = set(self.values.keys())
        default_keys: Set[str] = set(DEFAULT_GLOBAL_CONFIG.keys())
        added_keys: Set[str] = these_keys - default_keys
        removed_keys: Set[str] = default_keys - these_keys
        if added_keys | removed_keys:
            error_message: str = ""
            if added_keys:
                error_message += (
                    "The following keys are in the config to be saved, "
                    f"but not in the default config: {added_keys}. "
                )
            if removed_keys:
                error_message += (
                    "The following keys are in the default config, "
                    f"but not in the config to be saved: {removed_keys}. "
                )
            raise ValueError(error_message[:-1])

    def _validate_keyboard_config(self) -> None:
        """Ensures that no keys are bound to multiple functions."""
        bound: DefaultDict[str, List[str]] = defaultdict(list)
        for config_key in [f"{e}_keys" for e in ["skip", "abort", "continue", "undo"]]:
            for key in self.values[config_key]:
                bound[_string_form_of_key(key)].append(config_key)
        for valid in {key for (key, value) in bound.items() if len(value) == 1}:
            bound.pop(valid)
        if bound:
            raise ValueError(
                "The following keys are bound to multiple different functions: "
                f"{', '.join([f'{key} ({value})' for (key, value) in bound.items()])}."
            )
        return

    def validate(self) -> None:
        """Performs validation of config to ensure that config has not broken."""
        self._validate_config_variables()
        self._validate_keyboard_config()
        return

    def save(self) -> None:
        """
        Saves the config to the yaml file.
        """
        try:
            self.validate()
        except ValueError as exception:
            raise ValueError(
                "Couldn't save config because validation failed "
                f"with the following exception: {exception}"
            )
        config: Dict[str, str] = {
            key: DEFAULT_GLOBAL_CONFIG[key].stringifier(value)
            for (key, value) in self.values.items()
        }
        with open(GLOBAL_CONFIG_FILENAME, "w") as file:
            yaml.dump(config, file)
        return

    def load(self) -> None:
        """
        Loads the config from the yaml file.
        """
        with open(GLOBAL_CONFIG_FILENAME, "r") as file:
            config = yaml.safe_load(file)
        assert isinstance(config, dict)
        for (key, value) in config.items():
            self._set(key, value)
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

    def _set(self, key: str, value: str) -> None:
        """
        Private method that sets a variable without saving. Needed for initializer.

        Args:
            key: the config variable to change
            value: the string form of the value to set for the given key
        """
        formatted: Any = DEFAULT_GLOBAL_CONFIG[key].parser(value)
        self.values[key] = formatted
        logging.info(
            f'Setting global config variable {key} to {formatted}. '
            f'The string passed was {value}.'
        )
        return

    def __setitem__(self, key: str, value: str) -> None:
        """
        Sets a config value associated with the given key.

        Args:
            key: the config variable to change
            value: the string form of the value to set for the given key
        """
        self._set(key, value)
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
                print_func(
                    f"{name}: {DEFAULT_GLOBAL_CONFIG[name].stringifier(self[name])}"
                )
        elif name in self:
            print_func(f"{name}: {DEFAULT_GLOBAL_CONFIG[name].stringifier(self[name])}")
        else:
            print_func(f"{name} not in cubetime config.")
        return


class GlobalConfig:
    """Class allowing for static creation/access of global configuration"""

    instance: _GlobalConfig = _GlobalConfig()
    """Static container storing global configuration settings."""


global_config: _GlobalConfig = GlobalConfig.instance
"""Convenience variable for accessing/modifying global configuration settings"""
