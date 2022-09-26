import click
from datetime import datetime
import logging
import time
from typing import Any, Callable, Dict, List, Optional, Tuple
from typing_extensions import Self

import numpy as np
import pandas as pd

from cubetime.core.CompareStyle import CompareStyle
from cubetime.core.CompareTime import CompareTime, ComparisonSet
from cubetime.core.Formatting import print_pandas_dataframe

logger = logging.getLogger(__name__)

DATE_COLUMN: str = "date"
"""Name of the date column in the dataframes"""
SINGLETON_SEGMENT_COLUMN = "complete"
"""Name of single segment in single segment tasks with no custom segment name."""
AGG_FUNCS: List[str] = ["min", "median", "max", "mean", "std", "sum", "count"]
"""Aggregation functions to use for summarizing times."""
TIME_AGG_FUNCS: List[str] = [f for f in AGG_FUNCS if f not in ["count"]]
"""Subset of aggregation functions that create times (columns that should be H:MM:SS)"""


class TimeSet:
    """
    Class representing a set of times on a single timed task.
    """

    def __init__(self, times: pd.DataFrame, copy: bool = False, min_best: bool = True):
        """
        Initializes a new TimeSet with a DataFrame

        Args:
            times: DataFrame containing segment times and dates of runs
            copy: if True, times is copied before being stored
            min_best: if True, smaller times are considered better
        """
        self.times: pd.DataFrame = times.copy() if copy else times
        self.segments: List[str] = self._process_columns_into_segments()
        self.min_best: bool = min_best

    def __eq__(self, other: Self) -> bool:
        """
        Checks for equality between TimeSet objects.

        Args:
            other: TimeSet to check for equality with

        Returns:
            true if segments, min_best, and times are equal
        """
        if self.min_best != other.min_best:
            return False
        if self.segments != other.segments:
            return False
        if self.times.shape != other.times.shape:
            return False
        return np.all(self.times.values == other.times.values)

    @property
    def num_segments(self) -> int:
        """
        Gets the number of segments.

        Returns:
            integer number of segments
        """
        return len(self.segments)

    @property
    def is_multi_segment(self) -> bool:
        """
        Determines if this is a multi-segment task or not.

        Returns:
            True if there is more than one segment
        """
        return self.num_segments > 1

    def __len__(self) -> int:
        """
        Allows use of len built-in.

        Returns:
            integer number of times stored in this set
        """
        return len(self.times)

    def __bool__(self) -> bool:
        """
        Allows this object to be used in boolean contexts.

        Returns:
            True if times exist, False otherwise
        """
        return len(self) > 0

    @classmethod
    def create_new(cls, segments: List[str] = None, min_best: bool = True) -> Self:
        """
        Creates a new TimeSet that is empty (i.e. has no runs in it).

        Args:
            segments: string names of segments of run.
                If None, segments set to [SINGLETON_SEGMENT_COLUMN]
            min_best: if True, minimum times are considered best, otherwise maximum used
        """
        if segments is None:
            segments = [SINGLETON_SEGMENT_COLUMN]
        columns = [DATE_COLUMN] + segments
        frame = pd.DataFrame(columns=columns)
        return cls(frame, copy=False, min_best=min_best)

    @classmethod
    def create_new_like(cls, other: Self) -> Self:
        """
        Creates a new TimeSet with same columns as the given one.

        Args:
            other: the TimeSet to copy segments from

        """
        return cls(other.times[0:0], min_best=other.min_best, copy=True)

    def copy(self) -> Self:
        """
        Creates a copy of this object.

        Returns:
            exact copy of this object
        """
        return TimeSet(self.times, copy=True, min_best=self.min_best)

    def save(self, filename: str) -> None:
        """
        Saves the TimeSet database to a parquet file.

        NOTE: the min_best switch is not stored. It must be provided upon loading

        Args:
            filename: location to save parquet file, preferably with .parquet extension
        """
        self.times.to_parquet(filename)
        return

    @classmethod
    def load(cls, filename: str, min_best: bool = True) -> Self:
        """
        Creates a TimeSet object from a database previously saved via save method.

        Args:
            filename: location to load parquet file from
            min_best: if True, minimum times are considered best, otherwise maximum used

        Returns:
            TimeSet object based on database loaded from the parquet file
        """
        return cls(pd.read_parquet(filename), copy=False, min_best=min_best)

    def _process_columns_into_segments(self: Self) -> List[str]:
        """
        Checks the times DataFrame is valid and assembles lists of segments.

        Ensures that the date and segment columns are included in
        the columns of DataFrame (throws ValueError otherwise).

        Returns:
            list of string names of segments
        """
        date_present: bool = False
        segments: List[str] = []
        for column in self.times.columns:
            if column == DATE_COLUMN:
                date_present = True
            else:
                segments.append(column)
        if date_present:
            if segments:
                return segments
            else:
                raise ValueError(f"No segment columns were found in times DataFrame.")
        else:
            raise ValueError(
                f'"{DATE_COLUMN}" was expected to be a column in '
                "times DataFrame, but it was not found."
            )

    @property
    def dates(self) -> np.ndarray:
        """
        Gets the dates of all runs.

        Returns:
            1D numpy.ndarray of dates when runs took place
        """
        return self.times[DATE_COLUMN].values

    @property
    def values(self) -> np.ndarray:
        """
        Gets the times of all segments from all runs.

        Returns:
            2D numpy.ndarray where the rows are different
            runs and the columns are different segments.
        """
        return self.times[self.segments].values

    @property
    def cumulative_times(self) -> pd.DataFrame:
        """
        Gets the times at the end of each segment of each run.

        Returns:
            DataFrame with same column names as times with
            cumulative times instead of segment times
        """
        frame = self.times[[DATE_COLUMN]].copy()
        frame[self.segments] = np.cumsum(self.values, axis=1)
        return frame

    def _get_extreme_times(self, frame: pd.DataFrame, best: bool = True) -> pd.Series:
        """
        Aggregates all rows into the extreme times by segment

        Args:
            frame: DataFrame containing times (standalone or cumulative) by segment
            best: if True, best times are yielded. if False, worst times are yielded

        Returns:
            Series containing the extreme times for each segment
        """
        subframe = frame[self.segments]
        kwargs: Dict[str, Any] = {"axis": 0, "skipna": True}
        should_do_min: bool = self.min_best == best
        return subframe.min(**kwargs) if should_do_min else subframe.max(**kwargs)

    def _get_average_times(self, frame: pd.DataFrame) -> pd.Series:
        """
        Aggregates all rows into the average times by segment

        Args:
            frame: DataFrame containing times (standalone or cumulative) by segment

        Returns:
            Series containing the average times for each segment
        """
        return frame[self.segments].mean(axis=0, skipna=True)

    @property
    def best_cumulative_times(self) -> pd.Series:
        """
        For each segment, stores the best time through that segment.

        Returns:
            Series containing best cumulative times, indexed by segment name
        """
        return self._get_extreme_times(frame=self.cumulative_times, best=True)

    def extreme_run_index(self, best: bool = True) -> int:
        """
        Finds the run with either the best or worst final time.

        Args:
            best: if True, best run index returned. if False, worst run index returned

        Returns:
            run index of extreme run
        """
        final_times: np.ndarray = self.cumulative_times[self.segments[-1]].values
        should_do_min: bool = self.min_best == best
        return np.argmin(final_times) if should_do_min else np.argmax(final_times)

    @property
    def best_run_index(self) -> int:
        """
        The index of the run with the best final time.

        Returns:
            integer index of best run
        """
        return self.extreme_run_index(best=True)

    @property
    def worst_run_index(self) -> int:
        """
        The index of the run with the worst final time.

        Returns:
            integer index of worst run
        """
        return self.extreme_run_index(best=False)

    @property
    def average_cumulative_times(self) -> pd.Series:
        """
        For each segment, stores the average time through that segment.

        Returns:
            Series containing average cumulative times, indexed by segment name
        """
        return self._get_average_times(frame=self.cumulative_times)

    @property
    def worst_cumulative_times(self) -> pd.Series:
        """
        For each segment, stores the worst time through that segment.

        Returns:
            Series containing best cumulative times, indexed by segment name
        """
        return self._get_extreme_times(frame=self.cumulative_times, best=False)

    @property
    def best_times(self) -> pd.Series:
        """
        For each segment, stores the best time of that segment.

        Returns:
            Series containing best standalone times, indexed by segment name
        """
        return self._get_extreme_times(frame=self.times, best=True)

    @property
    def average_times(self) -> pd.Series:
        """
        For each segment, stores the average time of that segment.

        Returns:
            Series containing average standalone times, indexed by segment name
        """
        return self._get_average_times(frame=self.times)

    @property
    def worst_times(self) -> pd.Series:
        """
        For each segment, stores the worst time of that segment.

        Returns:
            Series containing worst standalone times, indexed by segment name
        """
        return self._get_extreme_times(frame=self.times, best=False)

    def add_row(self, date: datetime, segment_times: np.ndarray) -> None:
        """
        Adds a new row to the set.

        Args:
            date: the time with which the row should be associated
            segment_times: array of (standalone) segment times
        """
        array_data: np.ndarray = np.ndarray((1, len(self.times.columns)), dtype=object)
        segment_index = 0
        for (column_index, column) in enumerate(self.times.columns):
            if column == DATE_COLUMN:
                array_data[0, column_index] = date
            else:
                array_data[0, column_index] = segment_times[segment_index]
                segment_index += 1
        new_row = pd.DataFrame(array_data, columns=self.times.columns)
        if len(self.times) == 0:
            self.times = new_row
        else:
            self.times = pd.concat([self.times, new_row], axis=0, ignore_index=True)

    @staticmethod
    def _make_compare_times_from_segment_times(
        times: np.ndarray,
    ) -> Tuple[CompareTime, CompareTime]:
        """
        Makes standalone and cumulative compare times from a given set of segment times.

        Args:
            times: standalone times for each segment

        Returns:
            (segment_comparison, cumulative_comparison)
                segment_comparison: compare times for standalone segments
                cumulative_comparison: compare times for cumulative segments
        """
        return (CompareTime(times), CompareTime(np.cumsum(times)))

    def _make_compare_times_from_run(
        self, which: int
    ) -> Tuple[CompareTime, CompareTime]:
        """
        Makes standalone and cumulative compare times from a specific run index.

        Args:
            which: the index of the run to create comparisons with

        Returns:
            (segment_comparison, cumulative_comparison)
                segment_comparison: compare times for standalone segments
                cumulative_comparison: compare times for cumulative segments
        """
        times: np.ndarray = self.values[which,:]
        return self._make_compare_times_from_segment_times(times)

    def _make_balanced_best_compare_times(self) -> Tuple[CompareTime, CompareTime]:
        """
        Makes the compare times to use for balanced best, which splits the
        time save left from the best run into equal amounts per segment.

        Returns:
            (segment_comparison, cumulative_comparison)
                segment_comparison: compare times for standalone segments
                cumulative_comparison: compare times for cumulative segments
        """
        best_run_times: np.ndarray = self.values[self.best_run_index,:]
        best_segment_times: np.ndarray = self.best_times.values
        time_saves: np.ndarray = best_run_times - best_segment_times
        balanced_time_save_per_segment: float = np.sum(time_saves) / self.num_segments
        balanced_times: np.ndarray = best_segment_times + balanced_time_save_per_segment
        return self._make_compare_times_from_segment_times(balanced_times)

    def make_compare_times(
        self, compare_style: CompareStyle
    ) -> Tuple[CompareTime, CompareTime]:
        """
        Makes standalone and cumulative compare times from a specific run index.

        Args:
            compare_style: the method of comparison

        Returns:
            (segment_comparison, cumulative_comparison)
                segment_comparison: compare times for standalone segments
                cumulative_comparison: compare times for cumulative segments
        """
        if not self:
            return (CompareTime(None), CompareTime(None))
        elif compare_style == CompareStyle.BEST_RUN:
            return self._make_compare_times_from_run(self.best_run_index)
        elif compare_style == CompareStyle.WORST_RUN:
            return self._make_compare_times_from_run(self.worst_run_index)
        elif compare_style == CompareStyle.LAST_RUN:
            return self._make_compare_times_from_run(len(self) - 1)
        elif compare_style == CompareStyle.BEST_SEGMENTS:
            return self._make_compare_times_from_segment_times(self.best_times.values)
        elif compare_style == CompareStyle.AVERAGE_SEGMENTS:
            return self._make_compare_times_from_segment_times(
                self.average_times.values
            )
        elif compare_style == CompareStyle.WORST_SEGMENTS:
            return self._make_compare_times_from_segment_times(self.worst_times.values)
        elif compare_style == CompareStyle.BALANCED_BEST:
            return self._make_balanced_best_compare_times()
        else:
            return CompareTime(None), CompareTime(None)

    @property
    def best_compare_times(self) -> Tuple[CompareTime, CompareTime]:
        """
        Gets the best segment and cumulative times.

        Returns:
            (best_segments, best_cumulative)
                best_segments: Comparison for best standalone times
                best_cumulative: Comparison for best cumulative times
        """
        if self:
            best_segments = CompareTime(self.best_times.values)
            best_cumulatives = CompareTime(self.best_cumulative_times.values)
            return (best_segments, best_cumulatives)
        else:
            return (CompareTime(None), CompareTime(None))

    def make_comparison_set(self, compare_style: CompareStyle) -> ComparisonSet:
        """
        Makes a full set of comparisons that will print
        times and differences in red, green, gold, or white.

        Args:
            compare_style: CompareStyle determining times to determine green/red with

        Returns:
            ComparisonSet containing current and best standalone and cumulative times
        """
        (current_segments, current_cumulatives) = self.make_compare_times(compare_style)
        (best_segments, best_cumulatives) = self.best_compare_times
        return ComparisonSet(
            current_segments,
            current_cumulatives,
            best_segments,
            best_cumulatives,
            self.min_best,
        )


    def _time_loop_iteration(
        self, unix_times: List[float], comparison: ComparisonSet
    ) -> bool:
        """
        Performs a loop of garnering user input while timing a run.

        This function asks the user to press enter when they've completed the next
        segment. Alternatively, the user could KeyboardInterrupt to unto the last
        segment completed (or cancel entirely if no segments have been completed) or
        type "abort" to abort a run without finishing the rest of the segments.

        Args:
            unix_times: list of times marking beginnings/ends of segments. When
                entering into first iteration of the loop, unix_times should have
                one element, the time of the beginning of the first segment.
                This list will be modified in this function.
            comparison: comparison times with which to determine color/differential

        Returns:
            True if input loop should be continued, False if it should be broken
        """
        segment_index: int = len(unix_times) - 1
        if segment_index == self.num_segments:
            return False
        prompt_message: str = (
            f'Finish {self.segments[segment_index]} (or "abort" to cancel run)'
        )
        try:
            prompt_input: str = click.prompt(
                prompt_message, default="", show_default=False
            )
        except (click.Abort, KeyboardInterrupt):
            unix_times.pop()
            if unix_times:
                click.echo(
                    f'Undoing finish of "{self.segments[segment_index - 1]}"'
                )
                return True
            else:
                raise KeyboardInterrupt("Aborting run!")
        if prompt_input.lower() == "abort":
            return False
        else:
            unix_times.append(time.time())
            comparison.print_segment_terminal_output(
                segment_index=segment_index,
                standalone=(unix_times[-1] - unix_times[-2]),
                cumulative=(unix_times[-1] - unix_times[0]),
                print_func=click.echo,
            )
            return True

    def time(self, compare_style: CompareStyle = CompareStyle.BEST_RUN) -> None:
        """
        Interactively times a new run.

        Args:
            compare_style: the method of comparison
        """
        date: datetime = datetime.now()
        logger.info(f"Comparing against {compare_style.name}.")
        comparison: ComparisonSet = self.make_comparison_set(compare_style)
        click.prompt(f"Start {self.segments[0]}", default="", show_default=False)
        unix_times: List[float] = [time.time()]
        while self._time_loop_iteration(unix_times, comparison):
            pass
        self._process_raw_times(date, unix_times)
        return

    def _process_raw_times(self, date: datetime, unix_times: List[float]) -> None:
        """
        Processes times that were given interactively.

        NOTE: If run was aborted before finishing, fills in remaining segments with NaNs

        Args:
            date: datetime representing time that run was started
            unix_times: list of max length self.num_segments+1 giving start/end times
        """
        new_times: np.ndarray = np.diff(unix_times)
        if len(new_times) > 0:
            num_nans_to_concatenate: int = self.num_segments - len(new_times)
            if num_nans_to_concatenate > 0:
                if not self:
                    click.echo(
                        "First run must be complete for stability "
                        "reasons. Not adding times."
                    )
                    return
                nans_to_concatenate = np.ones(num_nans_to_concatenate) * np.nan
                new_times = np.concatenate([new_times, nans_to_concatenate])
            if click.confirm("Should this run be added?"):
                self.add_row(date, new_times)
                logger.info("Adding new completion time.")
            else:
                logger.info("Not adding new time because of user request.")
        else:
            click.echo("Not adding new time because run aborted during first segment.")
        return

    @property
    def standalone_summary(self) -> pd.DataFrame:
        """
        Creates a summary dataframe by computing agg
        functions on standalone segment times.

        Returns:
            DataFrame with agg functions as columns and segments as rows
        """

        def make_sort_element(series: pd.Series) -> int:
            """
            Makes a value that characterizes where a row should be placed.

            Args:
                series: DataFrame row, containing column "segment"

            Returns:
                integer specifying where elements are sorted first by
                their segment index and then by their value of cumulative
            """
            segment: str = series.loc["segment"]
            if segment == "total":
                return self.num_segments
            else:
                return self.segments.index(segment)

        SORT_COLUMN: str = "SORTCOLUMNIGNORE"
        result: pd.DataFrame = self.times[self.segments].agg(AGG_FUNCS)
        if self.is_multi_segment:
            result["total"] = result.apply("sum", axis=1)
            # variance, not standard deviation, is additive
            result.loc["std", "total"] = np.sqrt(
                np.sum(result.loc["std", self.segments].values ** 2)
            )
            # count don't have meaningful sums over segments
            result.loc["count", "total"] = result.loc["count", self.segments[-1]]
        result = result.T
        result["count"] = result["count"].astype(int)
        result.reset_index(inplace=True)
        result.rename(columns={"index": "segment"}, inplace=True)
        result[SORT_COLUMN] = result.apply(make_sort_element, axis=1)
        result.sort_values(SORT_COLUMN, inplace=True)
        result.drop(columns=SORT_COLUMN, inplace=True)
        result.set_index("segment", inplace=True)
        return result

    @property
    def cumulative_summary(self) -> Optional[pd.DataFrame]:
        """
        Creates a summary dataframe by computing agg
        functions on cumulative segment times.

        Returns:
            DataFrame with agg functions as columns and segments as rows
        """

        def make_sort_element(series: pd.Series) -> int:
            """
            Makes a value that characterizes where a row should be placed.

            Args:
                series: DataFrame row, containing column "segment"

            Returns:
                integer specifying where elements are sorted first by
                their segment index and then by their value of cumulative
            """
            return self.segments.index(series.loc["segment"])

        SORT_COLUMN: str = "SORTCOLUMNIGNORE"
        result: pd.DataFrame = self.cumulative_times[self.segments].agg(AGG_FUNCS).T
        # sum of cumulative times is not meaningful except for the final segment
        result.loc[self.segments[:-1], "sum"] = np.nan
        result["count"] = result["count"].astype(int)
        result.reset_index(inplace=True)
        result.rename(columns={"index": "segment"}, inplace=True)
        result[SORT_COLUMN] = result.apply(make_sort_element, axis=1)
        result.sort_values(SORT_COLUMN, inplace=True)
        result.drop(columns=SORT_COLUMN, inplace=True)
        result.set_index("segment", inplace=True)
        return result

    def print_detailed_summary(self, print_func: Callable[..., None] = print) -> None:
        """
        Prints a detailed summary of the data stored in this object.

        Shows everything from standalone_summary (+ cumulative_summary if multi-segment)

        Args:
            print_func: function to use to print
        """
        kwargs: Dict = {"time_columns": TIME_AGG_FUNCS, "print_func": print_func}
        print_func()
        if self.is_multi_segment:
            print_func("Standalone summary:\n")
        print_pandas_dataframe(self.standalone_summary, **kwargs)
        if self.is_multi_segment:
            print_func("\n\nCumulative summary:\n")
            print_pandas_dataframe(self.cumulative_summary, **kwargs)
        print_func()
        return

    def correlations(self, segments: List[str] = None) -> pd.DataFrame:
        """
        Gets the correlations between segment times.

        Args:
            segments: list of string segment names (or None if all segments included)

        Returns:
            DataFrame containing correlation values
        """
        if segments is None:
            segments = self.segments
        if len(segments) < 2:
            raise ValueError("correlations are not meaningful for single segments.")
        times: np.ndarray = self.times[segments].values.astype(float)
        means: np.ndarray = np.mean(times, axis=0, keepdims=True)
        differences: np.ndarray = times - means
        covariance: np.ndarray = np.dot(differences.T, differences)
        variance: np.ndarray = np.diag(covariance)
        squared_norm: np.ndarray = variance[:,np.newaxis] * variance[np.newaxis,:]
        norm: np.ndarray = np.sqrt(squared_norm)
        correlation: np.ndarray = covariance / np.sqrt(squared_norm)
        return pd.DataFrame(data=correlation, index=segments, columns=segments)

    @property
    def total_time_spent(self) -> float:
        """
        Gets the total amount of time spent on this task.

        Returns:
            total number of seconds spend on this task
        """
        return np.sum(self.values)
