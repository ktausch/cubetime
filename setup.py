from setuptools import setup

setup(
    name='cubetime',
    version='0.1.0',    
    description='A multi-segment terminal-based timer',
    url='https://github.com/ktausch/cubetime',
    author='Keith Tauscher',
    author_email='Keith.Tauscher@gmail.com',
    license='MIT',
    packages=['cubetime.app', 'cubetime.core'],
    install_requires=[
        "click",
        "fastparquet",
        "matplotlib",
        "numpy",
        "pandas",
        "pynput",
        "pyyaml",
    ],
    classifiers=[
        "Development Status :: 2 - Pre-Alpha",
        "Environment :: Console",
        "Intended Audience :: End Users/Desktop",
        "License :: OSI Approved :: MIT License",
        "Natural Language :: English",
        "Operating System :: POSIX :: Linux",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
    ],
    entry_points={
        "console_scripts": [
            "cubetime = cubetime.app.main:main"
        ]
    },
)
