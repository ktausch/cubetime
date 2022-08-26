"""
File: $CUBETIME/cubetime/TimerSet.py
Author: Keith Tauscher
Date: 19 Feb 2017

File containing a class representing a container of cubetime.Timer objects.
"""
import os
import numpy as np
import matplotlib.pyplot as pl
from matplotlib.figure import Figure
from .Utilities import seconds_to_hours_minutes_seconds_string
from .Timer import Timer

puzzles = {'tetrahedron', 'octahedron', 'dodecahedron', 'kilominx',\
    'gigaminx', 'fisher_cube', 'eitans_cube', 'unequal_cube',\
    '(3x3x3)+(4x4x4)+(5x5x5)'}
puzzle_shorthands =\
{\
    'tetrahedron': {'-t', 't', '-T', 'T'},\
    'octahedron': {'-o', 'o', '-O', 'O'},\
    'dodecahedron': {'-d', 'd', '-D', 'D'},\
    'kilominx': {'dodecahedron2', '-d2', 'd2', '-D2', 'D2'},\
    'gigaminx': {'dodecahedron5', '-d5', 'd5', '-D5', 'D5'},\
    'fisher_cube': {'fisher', '-f', '-F', 'f', 'F'},\
    'eitans_cube': {'eitans', '-e', '-E', 'e', 'E'},\
    '(3x3x3)+(4x4x4)+(5x5x5)': {'345'},\
    'unequal_cube': {'unequal', '-u', '-U', 'u', 'U'}
}

for side_length in range(2, 10):
    puzzle_name = '{0:d}x{0:d}x{0:d}'.format(side_length)
    puzzles.add(puzzle_name)
    puzzle_shorthands[puzzle_name] = {'{:d}'.format(side_length)}
    if side_length >= 4:
        puzzle_name = 'edges_first_{0:d}x{0:d}x{0:d}'.format(side_length)
        this_puzzle_shorthands = set()
        for fix in ['e', 'E', 'ef', 'EF']:
            this_puzzle_shorthands |= {'{0!s}{1:d}'.format(fix, side_length),\
                '{0:d}{1!s}'.format(side_length, fix)}
        puzzles.add(puzzle_name)
        puzzle_shorthands[puzzle_name] = this_puzzle_shorthands
if puzzles != set(puzzle_shorthands.keys()):
    raise NotImplementedError("Something is wrong in the implementation of " +\
                              "the non-numeric puzzles and their " +\
                              "shorthands. The keys of puzzle_shorthands " +\
                              "are the same as the elements of puzzles.")
puzzles_and_shorthands = {puzzle for puzzle in puzzles}
for puzzle in puzzles:
    puzzles_and_shorthands |= puzzle_shorthands[puzzle]
sorted_puzzles = sorted([puzzle for puzzle in puzzles])


def puzzle_from_key(key):
    """
    Finds the puzzle described by the given identifier.
    
    key identifier of puzzle (i.e. the puzzle name or a shorthand for the
        puzzle)
    
    returns the puzzle which the key identifies
    """
    if key in puzzles_and_shorthands:
        if key in puzzles:
            return key
        else:
            for puzzle in puzzles:
                if key in puzzle_shorthands[puzzle]:
                    return puzzle
    else:
        raise KeyError(("The given key ({!s}) was not a puzzle or a " +\
            "shorthand for a puzzle.").format(key))

def prefix_from_puzzle(puzzle):
    """
    Gets the prefix of the data files for a given puzzle. This function
    requires the setting of the CUBETIME shell environment variable.
    
    puzzle the name of the puzzle for which to find the prefix
    
    returns string prefix giving an absolute path to the data storage directory
    """
    return os.environ['CUBETIME'] + '/times/' + puzzle

def prefix_from_key(key):
    """
    Gets the prefix of the data for the puzzle indicated by the given
    identifier.
    
    key identifier of the puzzle for which the prefix is desired
    """
    return prefix_from_puzzle(puzzle_from_key(key))

class TimerSet:
    """
    Container meant to store cubetime.Timer objects. It has some built-in
    statistics which it calculates and some built-in plotting routines.
    """
    def __init__(self):
        """
        Creates a new TimerSet by associating each puzzle with its prefix.
        """
        self._timers =\
            {puzzle: prefix_from_puzzle(puzzle) for puzzle in puzzles}
    
    def __getitem__(self, key):
        """
        Gets the timer associated with a given identifier.
        
        key identifier of the puzzle to retrieve. It must be a puzzle name or a
            recognized shorthand for the puzzle name
        
        returns the cubetime.Timer object associated with the given puzzle
        """
        puzzle = puzzle_from_key(key)
        current_data = self._timers[puzzle]
        if isinstance(current_data, Timer):
            return current_data
        else:
            timer = Timer(puzzle, current_data)
            self._timers[puzzle] = timer
            return timer
    
    @property
    def time_spent(self):
        """
        The total time spent on all cubetime.Timer objects in this container in
        the form of a float number of seconds.
        """
        total = 0.
        for puzzle in puzzles:
            timer = self[puzzle]
            if timer.count != 0:
                total += timer.time_spent
        return total
    
    @property
    def readable_time_spent(self):
        """
        String version of the total time spent on all cubetime.Timer objects in
        this container which matches well adhered standards.
        """
        return seconds_to_hours_minutes_seconds_string(self.time_spent)
    
    def print_summary(self):
        """
        Prints a summary of the cubetime.Timer objects stored in this container.
        The summary contains the number of solutions of each puzzle type along
        with means and standard deviations of solution times.
        """
        for puzzle in sorted_puzzles:
            timer = self[puzzle]
            count = timer.count
            if count != 0:
                mu = timer.mean
                string_to_print =\
                    ("{0!s} ({1:d} runs): {2:.3f}".format(puzzle, count, mu))
                if count != 1:
                    sigma = timer.stdv
                    string_to_print += (" +- {:.3f}".format(sigma))
                print(string_to_print)
        print("Total time spent: " + self.readable_time_spent)
    
    def plot_times(self, show=False, fig=1, ax=None, **kwargs):
        """
        Plots the mean solution times for all puzzles with standard deviations
        as error bars.
        
        show boolean determining whether the plot should be shown at the end of
             the function call
        fig either the matplotlib.figure.Figure instance in which to put a plot
            or the number of the figure to be created.
        ax either the matplotlib.axes.Axes instance in which to put the plot or
           None, in which case a new instance is created
        kwargs dictionary of extra arguments to ax.errorbar
        """
        if ax is None:
            if not isinstance(fig, Figure):
                fig = pl.figure(fig)
            ax = fig.add_subplot(111)
        num_puzzles = len(sorted_puzzles)
        means, stdvs = np.ndarray(num_puzzles), np.ndarray(num_puzzles)
        for ipuzzle in range(num_puzzles):
            timer = self[sorted_puzzles[ipuzzle]]
            if timer.count == 0:
                means[ipuzzle], stdvs[ipuzzle] = -9999. , 0.
            else:
                means[ipuzzle], stdvs[ipuzzle] = timer.mean, timer.stdv
        nominal_x = np.arange(num_puzzles)
        ax.errorbar(nominal_x, means, yerr=stdvs, fmt='o', **kwargs)
        ax.set_xlabel('Puzzle', size='xx-large')
        ax.set_ylabel('Solve time [s]', size='xx-large')
        ax.set_yscale('log', nonposy='clip')
        ax.tick_params('y', width=2, length=6, labelsize='xx-large')
        ax.set_xticks(nominal_x)
        ax.set_xticklabels(sorted_puzzles, rotation=45)
        yticks = []
        for order in range(1, 4):
            yticks += [i * (10 ** order) for i in [1, 3]]
        ax.set_yticks(yticks)
        ax.set_yticklabels(['{:d}'.format(ytick) for ytick in yticks])
        ax.set_xlim((nominal_x[0] - 0.5, nominal_x[-1] + 0.5))
        if show:
            pl.show()

