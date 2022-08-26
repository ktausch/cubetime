#!/usr/bin/env python3
"""
File: $CUBETIME/run_timer.py
Author: Keith Tauscher
Date: 19 Feb 2017
Last update: 5 Aug 2019

There are two ways of calling this script: 'timer_set' and 'timer'. 'timer_set'
mode includes things to do on the entire set of timers while 'timer' mode
includes things to do on a single timer.

Call 'timer' mode using "python $CUBETIME/run_timer.py key [func] [options]"
where key is an identifier of the puzzle (either the name of the puzzle or a
shorthand for the puzzle: both of which are defined in the file
$CUBETIME/cubetime/TimerSet.py) for which the desired timer applies.

Call 'timer_set' mode using "python $CUBETIME/run_timer.py [func] [options]"

For both modes, [func] can be anything defined in the [mode]_stats,
[mode]_plots, or [mode]_operations lists defined in this file (where [mode] is
the given mode), and [options] are only necessary when [func] is in
[mode]_plots.
"""
import sys
import matplotlib.pyplot as pl
from cubetime.TimerSet import TimerSet, puzzle_from_key, sorted_puzzles
from cubetime.Utilities import kwargs_from_equality_strings

timer_set_stats = ['time_spent', 'readable_time_spent']
timer_set_plots = ['plot_times']
timer_set_operations = ['print_summary']
timer_set_special = ['print_commands', 'help']
all_timer_set_modes = timer_set_stats + timer_set_plots +\
    timer_set_operations + timer_set_special

timer_stats = ['median', 'mean', 'stdv', 'min', 'max', 'count', 'time_spent',\
    'readable_time_spent']
timer_plots = ['scatter', 'histogram', 'plot_minimum_history']
timer_operations = ['measure', 'pop', 'print_times', 'add']
timer_special = ['print_commands', 'help']
all_timer_modes = timer_stats + timer_plots + timer_operations + timer_special

if len(sys.argv) == 1:
    arg1 = '3'
else:
    arg1 = sys.argv[1]

ts = TimerSet()
if arg1 in timer_set_operations:
    getattr(ts, arg1)()
elif arg1 in timer_set_plots:
    fig = pl.figure(figsize=(10, 10))
    ax = fig.add_subplot(111)
    kwargs = kwargs_from_equality_strings(sys.argv[2:])
    getattr(ts, arg1)(show=True, ax=ax, **kwargs)
elif arg1 in timer_set_stats:
    print(getattr(ts, arg1))
elif arg1 in timer_set_special:
    print("Acceptable commands to call on the entire TimerSet: {!s}.".format(\
        all_timer_set_modes))
else:
    try:
        puzzle = puzzle_from_key(arg1)
    except:
        raise NotImplementedError(("The first argument to the run_timer.py " +\
            "script must be either a) a puzzle name or a shorthand of a " +\
            "puzzle name or b) one of the following modes of operating on " +\
            "the full timer set: {!s}.").format(all_timer_set_modes))
    timer = ts[puzzle]
    if (len(sys.argv) < 3) or (sys.argv[2] == 'measure'):
        timer.measure()
    elif sys.argv[2] in timer_plots:
        fig = pl.figure(figsize=(10, 10))
        ax = fig.add_subplot(111)
        kwargs = kwargs_from_equality_strings(sys.argv[3:])
        getattr(timer, sys.argv[2])(show=True, ax=ax, **kwargs)
    elif sys.argv[2] in timer_stats:
        print(getattr(timer, sys.argv[2]))
    elif sys.argv[2] in timer_operations:
        getattr(timer, sys.argv[2])()
    elif sys.argv[2] in timer_special:
        print("Acceptable commands to call on a single Timer: {!s}.".format(\
            all_timer_modes))
    else:
        raise ValueError(('Secondary mode not defined. It should be one of ' +\
            'the following: {!s}.').format(all_timer_modes))

