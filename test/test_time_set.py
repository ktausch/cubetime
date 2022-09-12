from datetime import datetime
from itertools import product as direct_product
import numpy as np
import pandas as pd
import pytest
from typing import List

from cubetime.TimeSet import TimeSet


def bool_combinations(num_bools: int) -> List:
    """
    Creates a list of all 2^N combinations of N bools.

    Args:
        num_bools: the number of bools, N

    Returns:
        length-2^N List of length-N sequences of bools
    """
    return list(direct_product(*(num_bools * [[True, False]])))


@pytest.mark.parametrize("copy,multi_segment", bool_combinations(2))
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
        data=[[1., datetime.now(), 2., 3.], [2., datetime.now(), 3., 4.]],
        columns=["first", "date", "second", "third"],
    )
    if not multi_segment:
        times = times.iloc[:,:2]
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


# TODO:
#     1) compare times,
#     2) best and worst runs
#     3) cumulative_times
#     4) correlations
