#!/usr/bin/env python3
import os

try:
    from setuptools import setup
except ImportError:
    from distutils.core import setup

packages = ['cubetime']

setup(
    name='cubetime',
    version='0.1',
    description='Timer for puzzles.',
    author='Keith Tauscher',
    author_email='Keith.Tauscher@gmail.com',
    packages=packages,
)
          
CUBETIME_env = os.getenv('CUBETIME')          
cwd = os.getcwd()

##
# TELL PEOPLE TO SET ENVIRONMENT VARIABLE
##
if not CUBETIME_env:

    import re    
    shell = os.getenv('SHELL')

    print(
        "\n\n"
        "##############################################################################"
        "It would be in your best interest to set an environment variable\n"
        "pointing to this directory.\n"
    )

    if shell:    

        if re.search('bash', shell):
            print(
                "Looks like you're using bash, so add the following to your "
                f".bashrc:\n\n    export CUBETIME={cwd}"
            )
        elif re.search('csh', shell):
            print(
                "Looks like you're using csh, so add the following to " +\
                f"your .cshrc:\n\n    setenv CUBETIME {cwd}"
            )

    print("\nGood luck!")
    print("#"*78)
    print("\n")

# Print a warning if there's already an environment variable but it's pointing
# somewhere other than the current directory
elif CUBETIME_env != cwd:
    print("\n")
    print("#"*78)
    print("It looks like you've already got an CUBETIME environment ")
    print("variable set, but it's pointing to a different directory:")
    print(f"\n    CUBETIME={CUBETIME_env}")
    print(f"\nHowever, we're currently in {cwd}.\n")
    print("Is this just a typo in your environment variable?")
    print("#"*78)
    print("\n")

