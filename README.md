# lemondcsv v1.2.0

There are two scripts.

- lemondcsv.py : Converts LeMond Revolution Power Pilot CVS file
- lemondcsv_gt.py : Converts LeMond Revolution GT CVS files

Both scripts convert different workout file formats into a Garmin TCX file.
The TCX file can be then imported into applications such as Strava or Garmin Connect.

## Power Pilot Supported Firmare Versions

Currently this script only supports firmware version 63 of the
Lemond Power Pilot or 0.31 for GT. If you have a lower version, I highly recomend
installing the latest version which is currently 63 as a lot of
bugs have been fixed. See [the Lemond Website](http://lemond.myshopify.com/blogs/news/7299932-power-pilot-firmware-updates) for details. I don't know a lot about the GT versions, I only got
a sample file and modified the original script.

To check your Power Pilot firmware version press and hold HR/KCAL for
two seconds. The firmware version is shown in the lower right quadrant
of the screen.

If your Power Pilot has a newer firmware than 63, please let me
know and send a sample CSV workout file. I will try to fix the
script if possible.

## Strava and Speed

This script converts the data in such a way that Strava can
correctly show speed.

## Merging Multiple CSV files to one TCX workout

I've heard that if you cycle over a certain number of hours, the
Power Pilot will create multiple files to represent that single
workout. I'm not dedicated enough it seems so I haven't seen this
happen yet. As a result, I don't know how to properly convert a
group of CSV files into one TCX workout. If you have a workout 
session (on firmware 63) with multiple files, please send them
to me so that I can adjust the script to work with it.

## Running the lemondcsv.py

The script can be run in a number of ways. Here are some examples.

The simpliest way is to pass a single workout argument. This will take
convert the given CSV filename to a *TCX* filename of a similar name.
Note that if the TCX file already exists, the script will not overwrite it.

    ./lemondcsv.py 09261300.CSV

Another way is to specify a filename to use as the *TCX* filename. You
can do this by using the '-f' argument. Note that when you use -f, the
script will overwrite the target file if it exists as it presumes you
know what you want to do.

    ./lemondcsv.py -f 09261300.tcx 09261300.CSV

If you would like to output the TCX to stdout for some fancy processing
then you can always use the '-f' argument with the '-' option.

    ./lemondcsv.py -f - 09261300.CSV | xmllint --format - > 09261300.tcx

Once you have generated your TCX file, you can directly upload the file
to Strava and analyze your workout there.

For the GT script, the usage is similar.

## Python Version Support

This script has been tested on Python 2.6, 2.7, 3.2 and 3.3. It will not
work on Python 2.5 or earlier. I have tested this also on 3.10

## Contact/Questions/Bugs/Updates etc

If you find a problem with this script, check you have the latest
version by visiting
[the project on github](https://github.com/tpodowd/lemondcsv).
If you are using the latest version and have a question/bug etc,
please file an [issue](https://github.com/tpodowd/lemondcsv/issues)
if one doesn't already exist and I'll look into it. Sample files
you are having trouble with are always welcome.
