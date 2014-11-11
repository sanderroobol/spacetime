# Spacetime

Spacetime is a program that allows you to easily correlate microscopy images with some time-dependent external parameter like pressure, temperature, deposition rate, etc. It can directly show you what happened during a specific frame or even scan line. Since this program basically unifies space and time, what name could be more appropriate than Spacetime?

Spacetime can work with quite a few different data files, the most important type being LPM Camera .raw files. You can of course plot images from such a file, but you can also plot one or more channels as function of time, frequency (performing FFT) or versus another channel.

In addition, a couple of other data sources are implemented, mainly focussing on the gas control and analysis systems of the ReactorSTM and -AFM of the Interface Physics group at Leiden Univeristy. There is some support for plain text files as well.

The software is written in a very modular way and it's easy to add support for different data types. It's written in Python and runs on all common operating systems. Spacetime is still beta quality, but it's quite useful already.

## Requirements

* Python 2.6 or later but not 3.x.
* numpy and scipy (probably any version will do)
* Matplotlib (1.0.1 or later)
* Traits, TraitsUI and Pyface (with WX backend), part of the and Enthought Tool Suite, version 4.0.0 or later.
* pytz
* Python Imaging Library (PIL)
* pyglet


## Optional dependencies:

 * FFmpeg (to generate videos)
 * AVbin (to load videos)
 * Camera Python Package (for the LPM Camera modules)


## Installation

### Windows installer

There is a fully self-contained Windows installer for Spacetime. The only external dependency is the [Microsoft Visual C++ 2008 SP1 Redistributable Package (x86)](http://www.microsoft.com/downloads/en/details.aspx?familyid=A5C84275-3B97-4AB7-A40D-3802B2AF5FC2&displaylang=en).

### Linux, Mac OS X, other unix...

There are no packages yet. Make sure the spacetime module is in your PYTHONPATH and run the included `spacetime executable/script`.

## About

Copyright 2010-2014 Leiden University. Written by Sander Roobol

Spacetime is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 2 of the License, or
(at your option) any later version.



