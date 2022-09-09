from enum import Enum


class CompareStyle(Enum):
    """Class to represent different ways of comparing times"""

    NONE = 0
    """Represents no comparison. Used if explicitly asked for or if no times stored."""
    BEST_RUN = 1
    """Compares against the best run stored."""
    BEST_SEGMENTS = 2
    """Compares against the set of best stored standalone times for each segment."""
    WORST_RUN = 3
    """Compares against the worst run stored."""
    WORST_SEGMENTS = 4
    """Compares against the set of worst stored standalone times for each segment."""
    LAST_RUN = 5
    """Compares against the last stored run."""
    AVERAGE_SEGMENTS = 6
    """Compares against the average standalone times for each segment."""
    BALANCED_BEST = 7
    """
    Compares against a modified best run. The segment times add up to
    best run, but segment times are modified so that the total time save
    from the best run is split evenly amongst all segments.
    """
