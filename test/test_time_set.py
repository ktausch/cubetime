from datetime import datetime
from itertools import product as direct_product
import numpy as np
import os
import pandas as pd
import pytest
from typing import List

from cubetime.CompareStyle import CompareStyle
from cubetime.CompareTime import CompareTime
from cubetime.TimeSet import SINGLETON_SEGMENT_COLUMN, TimeSet

TEST_FILE_NAME: str = "tempTHISfileSHOULDbeDELETED"


@pytest.mark.parametrize(
    "copy,multi_segment", list(direct_product(*(2 * [[True, False]])))
)
def test_time_set_from_data_frame(copy: bool, multi_segment: bool) -> None:
    """
    Creates time set using initializer and tests its properties.

    1) Checks whether copy keyword argument actually causes data frame to be copied
    2) Checks whether is_multi_segment matches num_segments>1
    3) Checks if segments are taken from columns as expected from data frame
    4) Checks if number of segments is correct
    5) Checks that length is the number of times in the given data frame
    6) Checks that bool(time_set) is true because times are given

    Args:
        copy: if True, TimeSet should copy input data frame
        multi_segment: if True, multiple segments are added instead of just one
    """
    times: pd.DataFrame = pd.DataFrame(
        data=[[1.0, datetime.now(), 2.0, 3.0], [2.0, datetime.now(), 3.0, 4.0]],
        columns=["first", "date", "second", "third"],
    )
    if not multi_segment:
        times = times.iloc[:, :2]
    time_set: TimeSet = TimeSet(times, copy=copy)
    expected_segments = ["first"] + (["second", "third"] if multi_segment else [])
    assert time_set.segments == expected_segments
    assert time_set.is_multi_segment == multi_segment
    assert (time_set.times is times) == (not copy)
    assert time_set.num_segments == len(expected_segments)
    assert len(time_set) == 2
    assert time_set
    return


def test_create_new() -> None:
    """
    Tests the create_new method of making a TimeSet.

    1) Ensures that no times exist
    2) Ensures segments are set correctly
    """
    segments: List[str] = ["first", "second"]
    time_set: TimeSet = TimeSet.create_new(segments)
    assert time_set.segments == segments
    assert time_set.num_segments == 2
    assert len(time_set) == 0
    assert not time_set
    return


def test_add_row() -> None:
    """
    Tests the method that adds a set of times to the data.

    1) Ensures that one time exists after call to add_row
    """
    segments: List[str] = ["first", "second"]
    time_set: TimeSet = TimeSet.create_new(segments)
    time_set.add_row(date=datetime.now(), segment_times=np.linspace(10, 20, 2))
    assert len(time_set) == 1
    assert time_set
    return


def test_equality_check() -> None:
    """
    Tests "==" oberator on TimeSet objects. Segments, min_best, and times must be equal.
    """
    time_set1: TimeSet = TimeSet.create_new(["first", "second"], min_best=True)
    time_set2: TimeSet = TimeSet.create_new(["first", "second"], min_best=False)
    time_set3: TimeSet = TimeSet.create_new(["first", "Second"], min_best=True)
    time_set4: TimeSet = TimeSet.create_new(["first", "second"], min_best=True)
    time_set4.add_row(date=datetime.now(), segment_times=np.linspace(10, 20, 2))
    assert time_set1 == time_set1
    assert time_set1 != time_set2
    assert time_set1 != time_set3
    assert time_set1 != time_set4
    return


def test_copy() -> None:
    """
    Tests ways to copy TimeSet objects.

    1) create_new_like creates copies of empty TimeSet objects
    2) copy can create copy of any TimeSet
    """
    time_set: TimeSet = TimeSet.create_new(["first", "second"])
    assert time_set == time_set.copy()
    assert time_set == TimeSet.create_new_like(time_set)
    time_set.add_row(date=datetime.now(), segment_times=np.linspace(10, 20, 2))
    assert time_set == time_set.copy()
    return


def test_no_segments_given() -> None:
    """
    Checks that when no segments are given, the predicted single segment column exists.
    """
    assert TimeSet.create_new() == TimeSet.create_new([SINGLETON_SEGMENT_COLUMN])
    return


def test_save_and_load() -> None:
    """
    Tests that saving and loading a TimeSet creates an identical object.
    """
    segments: List[str] = ["first", "second"]
    time_set: TimeSet = TimeSet.create_new(segments)
    time_set.add_row(date=datetime.now(), segment_times=np.linspace(10, 20, 2))
    time_set.add_row(date=datetime.now(), segment_times=np.linspace(15, 30, 2))
    time_set.save(TEST_FILE_NAME)
    try:
        assert time_set == TimeSet.load(TEST_FILE_NAME)
        os.remove(TEST_FILE_NAME)
    except Exception as exception:
        os.remove(TEST_FILE_NAME)
        raise exception
    return


def test_extreme_run() -> None:
    """
    Tests the best_run_index and worst_run_index properties.
    """
    time_set: TimeSet = TimeSet.create_new(["first", "second"])
    time_set.add_row(date=datetime.now(), segment_times=np.linspace(10, 15, 2))
    time_set.add_row(date=datetime.now(), segment_times=np.linspace(10, 20, 2))
    time_set.add_row(date=datetime.now(), segment_times=np.linspace(15, 30, 2))
    assert time_set.best_run_index == 0
    assert time_set.worst_run_index == 2
    return


def test_time_spent() -> None:
    """
    Tests the total_time_spent property, which is the sum of all standalone times.
    """
    time_set: TimeSet = TimeSet.create_new(["first", "second"])
    time_set.add_row(date=datetime.now(), segment_times=np.linspace(10, 15, 2))
    assert time_set.total_time_spent == 25
    return


def test_invalid_initializer() -> None:
    """
    Tests initialization with invalid data frames.

    1) Checks that DataFrame must have one non-"date" column
    2) Checks that DataFrame must have the "date" column
    """
    times: pd.DataFrame = pd.DataFrame(data=[[datetime.now()]], columns=["date"])
    try:
        TimeSet(times)
    except ValueError:
        pass
    else:
        raise AssertionError("times frame with no segments should raise error.")
    times["complete"] = [10.0]
    times.drop(columns="date", inplace=True)
    try:
        TimeSet(times)
    except ValueError:
        pass
    else:
        raise AssertionError("times frame with no date should raise error")
    return


def test_dates() -> None:
    """
    Tests the dates property to ensure that it contains the dates input by add_row.
    """
    time_set: TimeSet = TimeSet.create_new(["first", "second"])
    date1: datetime = datetime.now()
    date2: datetime = datetime.now()
    time_set.add_row(date=date1, segment_times=np.linspace(10, 20, 2))
    time_set.add_row(date=date2, segment_times=np.linspace(5, 25, 2))
    assert list(time_set.dates) == [np.datetime64(date1), np.datetime64(date2)]
    return


def test_compares_when_empty() -> None:
    """
    Ensures that there is no comparison to use when no times have been added.
    """
    time_set: TimeSet = TimeSet.create_new()
    for compare_style in CompareStyle:
        (standalone, cumulative) = time_set.make_compare_times(compare_style)
        assert standalone == CompareTime(None)
        assert cumulative == CompareTime(None)
    (standalone, cumulative) = time_set.best_compare_times
    assert standalone == CompareTime(None)
    assert cumulative == CompareTime(None)
    return


@pytest.fixture
def time_set_for_compares() -> TimeSet:
    """
    Makes a TimeSet to use when testing Comparisons.
    """
    time_set: TimeSet = TimeSet.create_new(["first", "second", "third", "fourth"])
    time_set.add_row(
        date=datetime.now(), segment_times=np.array([10.0, 20.0, 30.0, 40.0])
    )
    time_set.add_row(
        date=datetime.now(), segment_times=np.array([15.0, 15.0, 10.0, 30.0])
    )
    time_set.add_row(
        date=datetime.now(), segment_times=np.array([1.0, 60.0, 60.0, 20.0])
    )
    time_set.add_row(
        date=datetime.now(), segment_times=np.array([60.0, 1.0, 60.0, 10.0])
    )
    return time_set


def test_best_compares(time_set_for_compares: TimeSet) -> None:
    """
    Tests best comparisons (used to determine golds) when some procured times are added.
    """
    (standalone, cumulative) = time_set_for_compares.best_compare_times
    print(standalone.data)
    assert standalone == CompareTime(np.array([1.0, 1.0, 10.0, 10.0]))
    assert cumulative == CompareTime(np.array([1.0, 30.0, 40.0, 70.0]))
    return


def test_none_compares(time_set_for_compares: TimeSet) -> None:
    """
    Ensures that CompareStyle.NONE always produces no comparison.
    """
    compares = time_set_for_compares.make_compare_times(CompareStyle.NONE)
    assert compares == (CompareTime(None), CompareTime(None))
    return


@pytest.mark.parametrize(
    "style,times",
    [
        (CompareStyle.AVERAGE_SEGMENTS, [21.5, 24.0, 40.0, 25.0]),
        (CompareStyle.BALANCED_BEST, [13.0, 13.0, 22.0, 22.0]),
        (CompareStyle.BEST_RUN, [15.0, 15.0, 10.0, 30.0]),
        (CompareStyle.BEST_SEGMENTS, [1.0, 1.0, 10.0, 10.0]),
        (CompareStyle.LAST_RUN, [60.0, 1.0, 60.0, 10.0]),
        (CompareStyle.WORST_RUN, [1.0, 60.0, 60.0, 20.0]),
        (CompareStyle.WORST_SEGMENTS, [60.0, 60.0, 60.0, 40.0]),
    ],
)
def test_non_none_compares(
    time_set_for_compares: TimeSet, style: CompareStyle, times: List[float]
) -> None:
    """
    Tests that the different compare styles produce the expected compares.
    """
    compares = time_set_for_compares.make_compare_times(style)
    assert compares == (CompareTime(np.array(times)), CompareTime(np.cumsum(times)))
    return


def test_worst_cumulative_times(time_set_for_compares: TimeSet) -> None:
    """
    Tests worst_cumulative_times property, which gives worst time up to each segment.
    """
    times: List[float] = list(time_set_for_compares.worst_cumulative_times.values)
    assert times == [60.0, 61.0, 121.0, 141.0]
    return


def test_average_cumulative_times(time_set_for_compares: TimeSet) -> None:
    """
    Tests average_cumulative_times properties, which gives mean time up to each segment.
    """
    times: List[float] = list(time_set_for_compares.average_cumulative_times.values)
    assert times == [21.5, 45.5, 85.5, 110.5]
    return


def test_correlations() -> None:
    """
    Tests the correlations function, which computes correlations amongst segment times.
    """
    time_set: TimeSet = TimeSet.create_new(["first", "second", "third"])
    time_set.add_row(date=datetime.now(), segment_times=np.array([1., 2., 3.]))
    time_set.add_row(date=datetime.now(), segment_times=np.array([2., 1., 5.]))
    actual_all: np.ndarray = time_set.correlations()
    actual_subset: np.ndarray = time_set.correlations(segments=["first", "third"])
    expected_all: np.ndarray = np.array([[1., -1., 1.], [-1., 1., -1.], [1., -1., 1.]])
    assert np.allclose(actual_all, expected_all)
    assert np.all(actual_subset.values == actual_all.values[::2, :][:, ::2])
    try:
        time_set.correlations(["first"])
    except ValueError:
        pass
    else:
        raise AssertionError("correlations with only one segment should raise error.")
    return


# TODO: summaries
