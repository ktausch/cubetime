from typing import Any

import numpy as np
import pandas as pd

from cubetime.Config import global_config
from cubetime.Formatting import make_time_string, print_pandas_dataframe


class StringWrapper:
    """Class to use to represent a mutable string"""

    def __init__(self):
        """Initializes with an empty string"""
        self.string: str = ""

    def __iadd__(self, to_add: Any) -> None:
        """
        Prints things to this string.

        Args:
            to_add: thing to print to the end of the string (newline is added!)
        """
        self.string += f"{to_add}\n"
    
    def __contains__(self, key: str) -> bool:
        """
        Checks if the given string is in this object's string.

        Args:
            key: string to check for

        Returns:
            bool describing whether key is in string
        """
        return key in self.string


def test_make_time_string() -> None:
    """
    Checks some basic outputs of the make_time_string function.
    """
    global_config.values = {"num_decimal_places": 1}
    assert make_time_string(12.63) == "12.6"
    assert make_time_string(-123.4) == "-2:03.4"
    assert make_time_string(7583.03, show_plus=True) == "+2:06:23.0"
    assert make_time_string(np.inf) == "NA"


def test_print_pandas_dataframe_time_columns() -> None:
    """
    Checks that print_pandas_dataframe with time_columns formats columns as times.
    """
    global_config.values = {"num_decimal_places": 1}
    output: StringWrapper = StringWrapper()
    frame: pd.DataFrame = pd.DataFrame(data=[[123.4, -567.8]], columns=["A", "B"])
    print_pandas_dataframe(frame, time_columns=["B"], print_func=output.__iadd__)
    assert "123.4" in output
    assert "-9:27.8" in output
    return


def test_print_pandas_dataframe_time_rows() -> None:
    """
    Checks that print_pandas_dataframe with time_rows formats rows as times.
    """
    global_config.values = {"num_decimal_places": 1}
    output: StringWrapper = StringWrapper()
    frame: pd.DataFrame = pd.DataFrame(data=[[123.4, -567.8]], columns=["A", "B"]).T
    print_pandas_dataframe(frame, time_rows=["B"], print_func=output.__iadd__)
    assert "123.4" in output
    assert "-9:27.8" in output
    return


def test_print_pandas_dataframe_time_rows_and_time_columns() -> None:
    """
    Checks error raised if time_rows, time_columns both given to print_pandas_dataframe
    """
    global_config.values = {"num_decimal_places": 1}
    output: StringWrapper = StringWrapper()
    frame: pd.DataFrame = pd.DataFrame(data=[[123.4, -567.8]], columns=["A", "B"]).T
    try:
        print_pandas_dataframe(
            frame, time_rows=["B"], time_columns=["A"], print_func=output.__iadd__
        )
    except ValueError:
        pass
    else:
        assert False
    return
