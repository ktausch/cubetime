from typing import Callable, Dict, List, Tuple, Union

import numpy as np
import pandas as pd

from cubetime.Config import global_config

SECONDS_PER_MINUTE: int = 60
"""Number of seconds per minute"""
MINUTES_PER_HOUR: int = 60
"""Number of minutes in an hour"""
SECONDS_PER_HOUR: int = SECONDS_PER_MINUTE * MINUTES_PER_HOUR
"""Number of seconds in an hour."""


class TimeFormatter:
    """Class designed to format numerical time data."""

    @staticmethod
    def divrem(numerator: float, denominator: int) -> Tuple[int, float]:
        """
        Divides (with remainder) numerator by denominator.

        Args:
            numerator: number to divide
            denominator: number to divide by

        Returns:
            (quotient, remainder):
                quotient: integer number of times denominator goes into numerator
                remainder: floating point number such that
                           (quotient * denominator) == (numerator - remainder)
        """
        quotient: int = int(numerator // denominator)
        remainder: float = numerator - (quotient * denominator)
        return (quotient, remainder)

    @staticmethod
    def signabs(number: float) -> Tuple[int, float]:
        """
        Finds the sign and the magnitude of the given number.

        Args:
            number: number to find sign and magnitude of

        Returns:
            (sign, magnitude)
                sign: either +1 (if non-negative) or -1 (if negative)
                magnitude: absolute value of number
        """
        return (1, number) if (number >= 0) else (-1, -number)

    def decimal_format(number: float) -> str:
        """
        Formats a float using the configured number of decimal places.

        Args:
            number: number to make a string for

        Returns:
            string form of number using configured number of decimal places
        """
        return (f"{{:.{global_config['num_decimal_places']}f}}").format(number)

    def make_time_string(signed_total: float, show_plus: bool = False) -> str:
        """
        Makes a time string of the form (H:)(M:)S.

        Args:
            signed_total: number of seconds to make into a time string
            show_plus: if True, "+" is shown at beginning of string if number of positive

        Returns:
            pretty string form of number of seconds
        """
        if not np.isfinite(signed_total):
            return "NA"
        (sign, total) = TimeFormatter.signabs(signed_total)
        (hours, intermediate) = TimeFormatter.divrem(total, SECONDS_PER_HOUR)
        (minutes, seconds) = TimeFormatter.divrem(intermediate, SECONDS_PER_MINUTE)
        string: str = TimeFormatter.decimal_format(seconds)
        if (hours != 0) or (minutes != 0):
            if seconds < 10:
                string = f"0{string}"
            if hours == 0:
                string = f"{minutes}:{string}"
            else:
                string = f"{hours}:{f'{minutes}'.zfill(2)}:{string}"
        if sign < 0:
            string = f"-{string}"
        elif show_plus:
            string = f"+{string}"
        return string

    @staticmethod
    def make_time_column(old_column: pd.Series, show_plus: bool = False) -> pd.Series:
        """
        Makes a time string column from a numerical column containing number of seconds.

        Args:
            old_column: the column to make into a column of strings
            show_plus: if True, "+" is prepended to non-negative numbers

        Returns:
            Series containing time string versions of elements of old_column
        """
        data: List[str] = []
        for element in old_column.values:
            data.append(TimeFormatter.make_time_string(element, show_plus=show_plus))
        return pd.Series(data=data, index=old_column.index, name=old_column.name)


SliceMaker = Callable[[str], Tuple[Union[slice, str], Union[slice, str]]]


def print_pandas_dataframe(
    frame: pd.DataFrame,
    time_columns: Union[List[str], Dict[str, bool]] = None,
    time_rows: Union[List[str], Dict[str, bool]] = None,
    print_func=print,
) -> None:
    """
    Prints DataFrame with config variables determining formatting.

    Args:
        frame: the DataFrame to print
        time_columns: the columns that should be shown in time format, if any. If
            dictionary, keys from column name to boolean describing whether "+" should
            be prepended to time. If it is a list, "+" is never prepended
        time_rows: the columns to be shown in time format, if any. Same format as
            time_columns. NOTE: that only zero or one of time_rows and time_columns
            should be provided
    """
    time_columns_provided: bool = time_columns is not None
    time_rows_provided: bool = time_rows is not None
    to_print: pd.DataFrame = frame
    if time_columns_provided and time_rows_provided:
        raise ValueError("Only one of time_columns and time_rows can be provided.")
    if time_rows_provided or time_columns_provided:
        to_print = to_print.copy()
        cols_or_rows = time_columns if time_columns_provided else time_rows
        if isinstance(cols_or_rows, list):
            cols_or_rows = {col_or_row: False for col_or_row in cols_or_rows}
        slice_maker: SliceMaker = lambda s: (
            (slice(None), s) if time_columns_provided else (s, slice(None))
        )
        for (col_or_row, show_plus) in cols_or_rows.items():
            this_slice = slice_maker(col_or_row)
            to_print.loc[this_slice] = TimeFormatter.make_time_column(
                to_print.loc[this_slice], show_plus=show_plus
            )
    with pd.option_context("display.precision", global_config["num_decimal_places"]):
        print_func(to_print)
