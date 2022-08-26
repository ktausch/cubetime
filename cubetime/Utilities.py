"""
File: $CUBETIME/cubetime/Utilities.py
Author: Keith Tauscher
Date: 19 Feb 2017

Utility functions for the puzzle timing tools in cubetime including time
conversion and keyword argument extraction routines.
"""
from __future__ import division

def hours_minutes_seconds_to_seconds(hours, minutes, seconds):
    """
    Converts an integer number of hours, 
    
    hours: non-negative integer number of hours
    minutes: non-negative integer number of minutes less than 60
    seconds: non-negative float number of seconds less than 60
    
    returns: float number of seconds summing given hours, minutes, and seconds
    """
    return ((((hours * 60) + minutes) * 60) + seconds)

def hours_minutes_seconds_string_to_seconds(hours_minutes_seconds_string,\
    return_precision=False):
    """
    Converts a string time to seconds.
    
    hours_minutes_seconds_string: string of form 'h:m:s', 'm:s', or 's'
                                  where h is a number of hours, m is a number
                                  of minutes, and s is a number of seconds
    return_precision: if True, then the integer number of decimal places in the
                               number of seconds is returned
    
    returns: (secs, prec) if return_precision_in_decimal_places else secs
             where secs is a float number of seconds and prec is an integer
             number of decimal places on the given seconds number
    """
    split_string = hours_minutes_seconds_string.split(':')
    num_tokens = len(split_string)
    if num_tokens > 3:
        raise ValueError("The given string could not be interpreted as a " +\
            "number of seconds, a number of minutes and a number of " +\
            "seconds, or a number of hours, a number of minutes, and a " +\
            "number of seconds because there were 3 or more ':'s.")
    (hours_string, minutes_string, seconds_string) =\
        (['0'] * (3 - num_tokens)) + split_string
    if hours_string.isdigit():
        hours = int(hours_string)
    else:
        raise ValueError("hours could not be interpreted as a non-negative " +\
            "integer.")
    if minutes_string.isdigit():
        minutes = int(minutes_string)
    else:
        raise ValueError("minutes could not be interpreted as a " +\
            "non-negative integer.")
    split_seconds_string = seconds_string.split('.')
    if len(split_seconds_string) == 1:
        split_seconds_string.append('')
    if len(split_seconds_string) != 2:
        raise ValueError("The seconds string has more than one '.'.")
    precision = len(split_seconds_string[1])
    processed_seconds_string = '.'.join(split_seconds_string)
    if processed_seconds_string == '.':
        raise ValueError("The empty string cannot be interpreted as a time.")
    seconds = float(processed_seconds_string)
    seconds_only = hours_minutes_seconds_to_seconds(hours, minutes, seconds)
    if return_precision:
        return (seconds_only, precision)
    else:
        return seconds_only

def seconds_to_hours_minutes_seconds(seconds_only):
    """
    Converts a float number of seconds into an integer number of hours, an
    integer number of minutes less than 60, and a float number of seconds less
    than 60.
    
    seconds_only float number of seconds to convert
    
    returns tuple of the form (hours, minutes, seconds) where hours is an
            integer, minutes is an integer less than 60, and seconds is a float
            less than 60
    """
    hours = int(seconds_only // 3600)
    total_seconds_only_mod_hour = seconds_only - (3600 * hours)
    minutes = int(total_seconds_only_mod_hour // 60)
    seconds = total_seconds_only_mod_hour - (minutes * 60)
    return (hours, minutes, seconds)

def seconds_to_hours_minutes_seconds_string(seconds_only):
    """
    Converts a float number of seconds into a readable string amount of time.
    
    seconds_only float number of seconds to convert
    
    returns string of the one of the forms (h:m:s, m:s, or s) where h and m are
            integers and s is a float
    """
    (hours, minutes, seconds) = seconds_to_hours_minutes_seconds(seconds_only)
    final = ''
    if hours == 0:
        if minutes == 0:
            to_join = ['{:d}'.format(int(seconds))]
        else:
            to_join =\
                ['{:d}'.format(minutes), '{:d}'.format(int(seconds)).zfill(2)]
    else:
        to_join = ['{:d}'.format(hours), '{:d}'.format(minutes).zfill(2),\
            '{:d}'.format(int(seconds)).zfill(2)]
    return ':'.join(to_join)

def kwargs_from_equality_strings(equality_strings):
    """
    Puts together a dictionary of keyword arguments which are described by the
    given strings.
    
    equality_strings collection of strings of the form "name=value" where name
                     is a parameter name and eval("value") is the corresponding
                     parameter value
    
    return dictionary of kwargs derived from the given equality_strings
    """
    kwargs = {}
    for equality_string in equality_strings:
        try:
            name, strvalue = equality_string.split('=')
            value = eval(strvalue)
        except:
            raise KeyError("All keyword arguments must be of the form " +\
                           "'name=value' where name is a parameter name " +\
                           "and eval('value') is the corresponding " +\
                           "parameter value.")
        kwargs[name] = value
    return kwargs

