"""
File: $CUBETIME/cubetime/Timer.py
Author: Keith Tauscher
Date: 19 Feb 2017

File containing a class representing a container of puzzle solution times (and
the UNIX times at which the solution occurred).
"""
from __future__ import division
import os, sys, pickle, time
import numpy as np
import matplotlib.pyplot as pl
from matplotlib.figure import Figure
from .Utilities import seconds_to_hours_minutes_seconds_string,\
    hours_minutes_seconds_string_to_seconds

try:
    from distpy import KroneckerDeltaDistribution, DistributionSet
    from pylinex import PolynomialBasis, ConstantModel, BasisModel,\
        TransformedModel, DistortedModel, SumModel, GaussianLoglikelihood,\
        LeastSquareFitter
except:
    have_distpy_and_pylinex = False
else:
    have_distpy_and_pylinex = True

python_major_version = sys.version_info[0]
input_function = input

class Timer(object):
    """
    Object which both times solutions of puzzles and stores the results. It has
    some built-in statistics, operations, and plots.
    """
    def __init__(self, puzzle, prefix):
        """
        Initializes a Timer using the given name and prefix of the puzzle.
        
        puzzle the name of the puzzle to which this timer corresponds
        prefix absolute path to prefix of files for this
        """
        self.puzzle = puzzle
        self.prefix = prefix
    
    def _load_times(self):
        """
        Loads the UNIX times and solve times from this puzzle timer's file on
        disk. Sets the times and unix_times attributes.
        """
        file_names = ['{0!s}.{1!s}.pkl'.format(self.prefix, which)\
            for which in ['unix_times', 'times']]
        loaded = []
        for file_name in file_names:
            if os.path.exists(file_name):
                with open(file_name, 'rb') as pickle_file:
                    loaded.append(pickle.load(pickle_file))
            else:
                loaded.append([])
        self._unix_times = loaded[0]
        self._times = loaded[1]

    @property
    def times(self):
        """
        The puzzle solve times stored in this database.
        """
        if not hasattr(self, '_times'):
            self._load_times()
        return self._times
    
    @times.setter
    def times(self, value):
        """
        Setter for the times of this Timer.
        """
        self._times = value

    @property
    def unix_times(self):
        """
        The UNIX times at which the puzzle solutions took place
        """
        if not hasattr(self, '_unix_times'):
            self._load_times()
        return self._unix_times
    
    @unix_times.setter
    def unix_times(self, value):
        """
        Setter for the UNIX times at which the puzzle solutions took place
        """
        self._unix_times = value
    
    def pop(self, verbose=True):
        """
        Clears the last solution time recorded.
        
        verbose boolean determining whether to print that pop() has been called
        """
        self.unix_times.pop()
        self.times.pop()
        self.save_state()
        if verbose:
            print('pop() called on timer for {!s}.'.format(self.puzzle))

    def save_state(self):
        """
        Saves the times and UNIX times stored in this container (which may or
        may not have changed since being read in.
        """
        with open('{!s}.times.pkl'.format(self.prefix), 'wb') as pickle_file:
            pickle.dump(self.times, pickle_file)
        with open('{!s}.unix_times.pkl'.format(self.prefix), 'wb') as\
            pickle_file:
            pickle.dump(self.unix_times, pickle_file)
    
    def measure(self):
        """
        Measures a solution time using the space between two presses of the
        enter key.
        """
        print(("Your solution time for the {!s} will be measured between " +\
            "the next two times you press enter.").format(self.puzzle))
        input_function()
        begin = time.time()
        print("Beginning at {!s}.".format(time.ctime()))
        input_function()
        end = time.time()
        end_str = time.ctime()
        print("Ending at {!s}.".format(time.ctime()))
        duration = end - begin
        unix_time = (begin + end) / 2
        self.insert_time(duration, unix_time)
    
    def add(self):
        """
        Allows user to manually add a time through command line prompts.
        """
        print("What time would you like to add for the {!s}?".format(\
            self.puzzle))
        duration_string = input_function()
        (duration, precision) = hours_minutes_seconds_string_to_seconds(\
            duration_string, return_precision=True)
        if precision < 3:
            raise ValueError("The duration given did not have ms precision.")
        unix_time = time.time()
        self.insert_time(duration, unix_time)
    
    def insert_time(self, duration, unix_time):
        """
        Inserts the given solve time and records that it took place at the
        given UNIX time. This function asks the user if the time entered is
        correct in case some error occurred. If the newly added time is a new
        record for this puzzle, a congratulation message is printed after
        confirmation.
        
        duration: solve time in seconds
        unix_time: UNIX time in seconds
        """
        print(("Your input solution time is {0:.3f} s. Is this a real time " +\
            "for the {1!s}? (Please type 'yes' or 'no'):").format(duration,\
            self.puzzle))
        input_str = input_function().lower() # any case combo will work
        while input_str not in ['yes', 'no']:
            print("Please type 'yes' or 'no':")
            input_str = input_function().lower()
        if input_str == 'yes':
            print("{0:.3f} s added to the {1!s} database.".format(duration,\
                self.puzzle))
            if (len(self.times) > 0) and (duration < self.min):
                print(("This is a new record for the {0!s}! The old record " +\
                    "was {1:.3f}").format(self.puzzle, self.min))
            self.times.append(duration)
            self.unix_times.append(unix_time)
            self.save_state()
        else:
            print("{:.3f} s ignored.".format(duration))
    
    def histogram(self, show=False, fig=1, ax=None, which=None,\
        plot_summary_statistics=True, sliding_average=1, grouping_average=1,\
        **kwargs):
        """
        Plots a histogram of the times stored in this Timer.
        
        show boolean determining whether the plot should be shown at the end of
             the function call
        fig either the matplotlib.figure.Figure instance in which to put a plot
            or the number of the figure to be created.
        ax either the matplotlib.axes.Axes instance in which to put the plot or
           None, in which case a new instance is created
        which either None (default; all are plotted) or a slice with which to
              determine which times to plot
        plot_summary_statistics plots mu+-1sigma interval
        sliding_average integer number of runs to average in a sliding average,
                        default 1
        grouping_average similar to sliding average except the times are parsed
                         into disjoint groups, instead of overlapping groups,
                         default 1
        kwargs dictionary containing extra arguments to pass to ax.hist
        
        returns (ninbins, bins) where bins is an array of bin edges
                (length nbins+1) and ninbins is an array containing the number
                of solutions within the edges of each bin (lengh nbins)
        """
        if type(ax) is type(None):
            if type(fig) is type(None):
                fig = pl.figure(figsize=(12,9))
            ax = fig.add_subplot(111)
        if type(which) is type(None):
            which = slice(None)
        if isinstance(which, slice):
            indices = np.array(list(range(*which.indices(len(self.times)))))
        else:
            raise TypeError("which must be a slice or None.")
        times_to_plot = np.array(self.times)[indices]
        if (sliding_average != 1) and (grouping_average != 1):
            raise ValueError("Sliding average and grouping average should " +\
                "not be combined because the results will be hard to " +\
                "interpret. Sliding average or grouping average (or both) " +\
                "should be 1.")
        y = 0
        for index in range(sliding_average):
            slc =\
                slice(index, len(times_to_plot) - sliding_average + 1 + index)
            y = y + times_to_plot[slc]
        times_to_plot = y / sliding_average
        (y, to_cut) = (0, (len(times_to_plot) % grouping_average))
        for index in range(grouping_average):
            slc = slice(to_cut + index, len(times_to_plot), grouping_average)
            y = y + times_to_plot[slc]
        times_to_plot = y / grouping_average
        (ninbins, bins, patches) = ax.hist(times_to_plot, **kwargs)
        ax.set_xlabel('Solution time [s]', size='xx-large')
        normed = (('density' in kwargs) and kwargs['density'])
        cumulative = ('cumulative' in kwargs) and kwargs['cumulative']
        (mean, stdv) = (np.mean(times_to_plot), np.std(times_to_plot))
        if normed and (not cumulative):
            xs = np.arange(mean - (4 * stdv), mean + (4 * stdv), stdv / 800)
            gaussian = np.exp(-(((xs - mean) / stdv) ** 2) / 2) /\
                (np.sqrt(2 * np.pi) * stdv)
            ax.plot(xs, gaussian, linewidth=2,\
                label='mu={0:.3f}, sigma={1:.3f}'.format(mean, stdv))
            ax.set_ylim((0, 1.25 * ax.get_ylim()[1]))
            ax.set_ylabel('PDF', size='xx-large')
            ax.legend(fontsize='xx-large')
        else:
            ax.set_ylabel('# of occurrences', size='xx-large')
        if plot_summary_statistics:
            ylim = ax.get_ylim()
            ax.plot([mean] * 2, ylim, color='k', linestyle='-',\
                linewidth=2)
            ax.plot([mean - stdv] * 2, ylim, color='k',\
                linestyle='--', linewidth=2)
            ax.plot([mean + stdv] * 2, ylim, color='k',\
                linestyle='--', linewidth=2)
            ax.set_ylim(ylim)
        ax.tick_params(labelsize='xx-large', width=2, length=6)
        ax.set_title('{!s} solution times'.format(self.puzzle),\
            size='xx-large')
        if show:
            pl.show()
        return ninbins, bins
    
    def scatter(self, show=False, fig=None, ax=None, timeless=False,\
        plot_trend_line=False, subtract_trend_line=False, fontsize=16,\
        which=None, sliding_average=1, grouping_average=1,\
        exponential_trend_line=False, **kwargs):
        """
        Plots a scatter plot of UNIX time vs. solution time.
        
        show boolean determining whether the plot should be shown at the end of
             the function call
        fig either the matplotlib.figure.Figure instance in which to put a plot
            or the number of the figure to be created.
        ax either the matplotlib.axes.Axes instance in which to put the plot or
           None, in which case a new instance is created
        timeless if True, each solution is equally far from the others, i.e.
                          x-axis is solution number, not time (default False)
        plot_trend_line if True, a trend line is plotted.
        subtract_trend_line if True, all plotted quantities have trend line
                            subtracted
        fontsize the size of the font to use for tick and axis labels and title
        which either None (default; all are plotted) or a slice with which to
              determine which times to plot
        sliding_average integer number of runs to average in a sliding average,
                        default 1
        grouping_average similar to sliding average except the times are parsed
                         into disjoint groups, instead of overlapping groups,
                         default 1
        exponential_trend_line if True (default False, pylinex must be
                               installed if True), then trend line is given as
                               an exponential with nonzero asymptote.
                               Otherwise, trend line is a simple line
        kwargs dictionary containing extra arguments to pass to ax.scatter
        """
        if type(ax) is type(None):
            if type(fig) is type(None):
                fig = pl.figure(figsize=(12,9))
            ax = fig.add_subplot(111)
        if type(which) is type(None):
            which = slice(None)
        if isinstance(which, slice):
            indices = np.array(list(range(*which.indices(len(self.times)))))
        else:
            raise TypeError("which must be a slice or None.")
        times_to_plot = np.array(self.times)[indices]
        if timeless:
            x_values = 1 + indices
            xlabel = 'Solution #'
        else:
            x_values = np.array(self.unix_times)[indices]
            xlabel = 'UNIX time (s)'
        if (sliding_average != 1) and (grouping_average != 1):
            raise ValueError("Sliding average and grouping average should " +\
                "not be combined because the results will be hard to " +\
                "interpret. Sliding average or grouping average (or both) " +\
                "should be 1.")
        (x, y) = (0, 0)
        for index in range(sliding_average):
            slc =\
                slice(index, len(times_to_plot) - sliding_average + 1 + index)
            x = x + x_values[slc]
            y = y + times_to_plot[slc]
        if timeless:
            x_values = 1 + np.arange(len(y))
        else:
            x_values = x / sliding_average
        times_to_plot = y / sliding_average
        (x, y, to_cut) = (0, 0, (len(times_to_plot) % grouping_average))
        for index in range(grouping_average):
            slc = slice(to_cut + index, len(times_to_plot), grouping_average)
            x = x + x_values[slc]
            y = y + times_to_plot[slc]
        if timeless:
            x_values = 1 + np.arange(len(y))
        else:
            x_values = x / grouping_average
        times_to_plot = y / grouping_average
        if exponential_trend_line:
            if have_distpy_and_pylinex:
                guess_asymptote = np.min(times_to_plot)
                times_less_asymptote = times_to_plot - guess_asymptote
                constant_part = ConstantModel(len(times_to_plot))
                logged_exponential_basis = PolynomialBasis(x_values, 2)
                logged_exponential_part = BasisModel(logged_exponential_basis)
                exponential_part = DistortedModel(TransformedModel(\
                    logged_exponential_part, 'exp'), ['log', None])
                guess_exponential_parts = exponential_part.quick_fit(\
                    times_less_asymptote + 1e-6, None)[0]
                model = SumModel(['constant', 'exponential'],\
                    [constant_part, exponential_part])
                error = np.ones_like(times_to_plot)
                loglikelihood =\
                    GaussianLoglikelihood(times_to_plot, error, model)
                prior_set = DistributionSet()
                prior_set.add_distribution(\
                    KroneckerDeltaDistribution(guess_asymptote), 'constant_a')
                prior_set.add_distribution(\
                    KroneckerDeltaDistribution(guess_exponential_parts),\
                    ['exponential_a{:d}'.format(index) for index in range(2)])
                least_square_fitter = LeastSquareFitter(\
                    loglikelihood=loglikelihood, prior_set=prior_set,\
                    constant_a=(0, None), exponential_a0=(0, None),\
                    exponential_a1=(None, 0))
                least_square_fitter.run(ftol=1e-8,\
                    eps=np.array([1e-8, 1e-8, 1e-8]), maxiter=int(1e4))
                optimized = least_square_fitter.argmin
                trend_line = model(optimized)
                trend_line_label =\
                    '${0:.3f}+[{1:.3f}*e^{{-{2!s}*({3:.3g})}}]$ s'.format(\
                    optimized[0], optimized[1], 'n' if timeless else 't',\
                    -optimized[2])
            else:
                raise NotImplementedError("Either distpy or pylinex cannot " +\
                    "be imported, so exponential_trend_line must be False.")
        else:
            coefficients = np.polyfit(x_values, times_to_plot, 1)
            trend_line = np.polyval(coefficients, x_values)
            trend_line_label = '$[({0:.3g}*{1!s})+{2:.1f}]$ s'.format(\
                coefficients[0], 'n' if timeless else 't', coefficients[1])
        standard_deviation_from_trend_line =\
            np.std(times_to_plot - trend_line)
        if subtract_trend_line:
            to_subtract = trend_line
            ylabel = 'Solution time [s] (best fit line subtracted)'
        else:
            to_subtract = np.zeros_like(times_to_plot)
            ylabel = 'Solution time [s]'
        ax.scatter(x_values, times_to_plot - to_subtract,\
            label='solution times', **kwargs)
        if plot_trend_line or subtract_trend_line:
            ax.plot(x_values, trend_line - to_subtract, color='k',\
                linestyle='-', linewidth=2,\
                label='{0!s}, $\sigma={1:.3f}$ s'.format(trend_line_label,\
                standard_deviation_from_trend_line))
            ax.legend(fontsize=fontsize)
        ax.set_xlim((x_values[0], x_values[-1]))
        ax.set_xlabel(xlabel, size=fontsize)
        ax.set_ylabel(ylabel, size=fontsize)
        ax.tick_params(labelsize=fontsize, width=2, length=6)
        ax.set_title('{!s} solution times'.format(self.puzzle), size=fontsize)
        if show:
            pl.show()
    
    def plot_minimum_history(self, show=False, fig=None, ax=None,\
        timeless=False, fontsize=16, **kwargs):
        """
        Plots the minimum history of this puzzle.
        
        show boolean determining whether the plot should be shown at the end of
             the function call
        fig either the matplotlib.figure.Figure instance in which to put a plot
            or the number of the figure to be created.
        ax either the matplotlib.axes.Axes instance in which to put the plot or
           None, in which case a new instance is created
        timeless if True, each solution is equally far from the others, i.e.
                          x-axis is solution number, not time (default False)
        fontsize the size of the font to use for tick and axis labels and title
        kwargs dictionary containing extra arguments to pass to ax.plot
        """
        if type(ax) is type(None):
            if type(fig) is type(None):
                fig = pl.figure(figsize=(12,9))
            ax = fig.add_subplot(111)
        if timeless:
            x_values = 1 + np.arange(len(self.times))
            xlabel = 'Solution #'
        else:
            x_values = self.unix_times
            xlabel = 'UNIX time (s)'
        minima = np.minimum.accumulate(self.times)
        ax.plot(x_values, minima, label='Minimum solution time', **kwargs)
        ax.set_xlim((x_values[0], x_values[-1]))
        ax.set_ylim((0, ax.get_ylim()[1]))
        ax.set_xlabel(xlabel, size=fontsize)
        ax.set_ylabel('Minimum solution time [s]', size=fontsize)
        ax.tick_params(labelsize=fontsize, width=2, length=6)
        ax.set_title('{!s} record history'.format(self.puzzle), size=fontsize)
        if show:
            pl.show()

    def print_times(self):
        """
        Prints the solution times stored in this Timer.
        """
        to_print = '{!s} times:'.format(self.puzzle)
        for time in self.times:
            to_print = "{0!s} {1:.3f},".format(to_print, time)
        print(to_print[:-1])
    
    @property
    def mean(self):
        """
        The mean of the solution times stored in this Timer.
        """
        return np.mean(self.times)

    @property
    def median(self):
        """
        The median of the solution times stored in this Timer.
        """
        return np.median(self.times)
    
    @property
    def min(self):
        """
        The minimum solution time stored in this Timer.
        """
        return min(self.times)
    
    @property
    def max(self):
        """
        The maximum solution time stored in this Timer.
        """
        return max(self.times)
    
    @property
    def stdv(self):
        """
        The standard deviation of the solution times stored in this Timer.
        """
        return np.std(self.times)

    @property
    def count(self):
        """
        The integer number of solution times stored in this Timer.
        """
        return len(self.times)
    
    @property
    def time_spent(self):
        """
        The time spent (in the form of a float number of seconds) performing
        solutions for this Timer.
        """
        return sum(self.times)
    
    @property
    def readable_time_spent(self):
        """
        String version of the time spent which splits the time into hours and
        minutes and is better to read.
        """
        return seconds_to_hours_minutes_seconds_string(self.time_spent)

