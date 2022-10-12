from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import matplotlib.pyplot as pl
import pandas as pd

from cubetime.core.TimedTask import TimedTask
from cubetime.core.TimeSet import TimeSet


class PlotType(Enum):
    """Enumeration representing types of plots that can be performed."""

    HISTOGRAM = 1
    """Distribution of times"""
    SCATTER = 2
    """Plots times against completion index"""

    @property
    def default_kwargs(self):
        """
        Gets the default keyword args for the given plot.

        Returns:
            dictionary of keyword arguments to pass to plotting function
        """
        kwargs: Dict[str, Any] = {}
        if self == PlotType.HISTOGRAM:
            kwargs.update(dict(linewidth=3, histtype="step"))
        elif self == PlotType.SCATTER:
            kwargs.update(dict(s=12))
        return kwargs

    def single_plot(self, ax: pl.Axes, times: np.ndarray, **kwargs) -> None:
        """
        Creates a single plot of this type.

        Args:
            ax: the axes on which to plot
            times: the completion times to plot
            **kwargs: any other keyword arguments to pass to plotting function
        """
        if self == PlotType.HISTOGRAM:
            ax.hist(times, **kwargs)
        elif self == PlotType.SCATTER:
            ax.scatter(1 + np.arange(len(times)), times, **kwargs)
        return

    def make_xlabel(self, cumulative: bool) -> str:
        """
        Makes the label for the x-axis.

        Args:
            cumulative: True if cumulative times are being plotted, False if standalone

        Returns:
            label for x axis of plot
        """
        label: str = ""
        if self == PlotType.HISTOGRAM:
            label = f"{'cumulative ' if cumulative else ''}completion time [s]"
        elif self == PlotType.SCATTER:
            label = "completion #"
        return label

    def make_ylabel(self, cumulative: bool) -> str:
        """
        Makes the label for the y-axis.

        Args:
            cumulative: True if cumulative times are being plotted, False if standalone

        Returns:
            label for y axis of plot
        """
        label: str = ""
        if self == PlotType.HISTOGRAM:
            label = "# of occurrences"
        elif self == PlotType.SCATTER:
            label = f"{'cumulative' if cumulative else ''}completion time [s]"
        return label

    def make_title(
        self, taskname: str, segments: Optional[List[Tuple[int, str]]], cumulative: bool
    ) -> str:
        """
        Creates the title of a plot of this type.

        Args:
            taskname: string name of the task with times being plotted
            segments: either None (if all are plotted) or list of (index, segment)
            cumulative: true if cumulative times being plotted (false for standalone)

        Returns:
            string title
        """
        title: str = ""
        if self == PlotType.HISTOGRAM:
            title = " time distribution"
        elif self == PlotType.SCATTER:
            title = " time progression"
        if segments is None:
            title = f"{taskname}{title}"
        else:
            title = f"{title}, {taskname}"
            if len(segments) == 1:
                title = f"{segments[0][1]}{title}"
            else:
                title = f"Segment{title}"
            if cumulative:
                title = f"Cumulative {title[0].lower()}{title[1:]}"
        return title


class TimePlotter:
    """Class that can produces plots of any PlotType from a given set of data."""

    def __init__(
        self, timed_task: TimedTask, segments: Optional[List[str]], cumulative: bool
    ):
        """
        Creates an object that can make plots from the given segments

        Args:
            timed_task: task to plot times from
            segments: the segments to be plotted (or none if final times to be plotted)
            cumulative: True if cumulative times should be plotted (doesn't change anything )
        """
        time_set: TimeSet = timed_task.time_set
        self.name: str = timed_task.name
        self.segments: Optional[List[Tuple[int, str]]] = None
        self.times: pd.DataFrame = time_set.cumulative_times[[time_set.segments[-1]]]
        if segments is not None:
            self.segments = []
            for segment in segments:
                self.segments.append((time_set.segments.index(segment), segment))
            self.times = time_set.cumulative_times if cumulative else time_set.times
        self.cumulative: bool = cumulative and (segments is not None)

    def plot(
        self,
        plot_type: PlotType,
        file_name: str = None,
        headless: bool = False,
        **extra_kwargs,
    ) -> None:
        """
        Plots histogram or scatter plot.

        Args:
            plot_type: the type of plot to make
            file_name: if not None, matplotlib figure is saved to this file
            headless: if True, matplotlib.pyplot.show() is not called
            **extra_kwargs: keyword arguments to pass to matplotlib plotting function
        """
        fontsize: int = 12
        fig = pl.figure(figsize=(12, 9))
        ax = fig.add_subplot(111)
        kwargs: Dict[str, Any] = plot_type.default_kwargs
        kwargs.update(extra_kwargs)
        if self.segments is None:
            plot_type.single_plot(ax, self.times.iloc[:, 0], **kwargs)
        else:
            for (segment_index, segment) in self.segments:
                kwargs["label"] = f"{1 + segment_index}. {segment}"
                plot_type.single_plot(ax, self.times[segment].values, **kwargs)
            if len(self.segments) > 1:
                ax.legend(fontsize=fontsize)
        title: str = plot_type.make_title(
            taskname=self.name, segments=self.segments, cumulative=self.cumulative
        )
        ax.set_title(title, size=fontsize)
        ax.set_xlabel(plot_type.make_xlabel(cumulative=self.cumulative), size=fontsize)
        ax.set_ylabel(plot_type.make_ylabel(cumulative=self.cumulative), size=fontsize)
        ax.tick_params(labelsize=fontsize, width=2.5, length=7.5, which="major")
        ax.tick_params(width=1.5, length=4.5, which="minor")
        fig.tight_layout()
        if file_name is not None:
            fig.savefig(file_name)
        if not headless:
            pl.show()
        return


def plot_correlations(
    timed_task: TimedTask, segments: List[str] = None, **kwargs
) -> None:
    """
    Plots the correlations between segment completion times of a task.

    Args:
        timed_task: the task whose segment times are being analyzed
        segments: the segments to plot (or None if all segments should be plotted)
        **kwargs: extra kwargs to pass to matplotlib.pyplot.imshow
    """
    fontsize: int = 12
    taskname = timed_task.name
    time_set = timed_task.time_set
    segments = time_set.segments if segments is None else segments
    correlation: np.ndarray = time_set.correlations(segments=segments).values
    num_segments: int = time_set.num_segments if segments is None else len(segments)
    fig = pl.figure(figsize=(12, 9))
    ax = fig.add_subplot(111)
    single_dim_extent: Tuple[float, float] = (-0.5, num_segments - 0.5)
    extent = single_dim_extent + single_dim_extent[-1::-1]
    kwargs.update(
        dict(interpolation="none", extent=extent, vmin=-1, vmax=1, cmap="seismic")
    )
    image = ax.imshow(correlation, **kwargs)
    colorbar = pl.colorbar(image, ax=ax)
    ax.set_xlabel("segment", size=fontsize)
    ax.set_ylabel("segment", size=fontsize)
    ax.set_title(f"{taskname} segment time correlations", size=fontsize)
    ticks = np.arange(num_segments)
    ax.set_xticks(ticks)
    ax.set_xticklabels(segments)
    ax.set_yticks(ticks)
    ax.set_yticklabels(segments)
    ax.tick_params(labelsize=fontsize, width=2.5, length=7.5)
    colorbar.ax.tick_params(labelsize=fontsize, width=2.5, length=7.5)
    fig.tight_layout()
    pl.show()
    return
