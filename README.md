# lemondcsv v1.0.1

This script converts a native Lemond Revolution Power Pilot CVS
workout file to a Garmin TCX file. The TCX file can be then imported
into applications such as Strava or Garmin Connect.

## Power Pilot Supported Firmare Versions

Currently this script only supports firmware version 63 of the
Lemond Power Pilot. If you have a lower version, I highly recomend
installing the latest version which is currently 63 as a lot of
bugs have been fixed. See [the Lemond Website](http://lemond.myshopify.com/blogs/news/7299932-power-pilot-firmware-updates) for details.

To check your Power Pilot firmware version press and hold HR/KCAL for
two seconds. The firmware version is shown in the lower right quadrant
of the screen.

If your Power Pilot has a newer firmware than 63, please let me
know and send a sample CSV workout file. I will try to fix the
script if possible.

## Strava and Speed

This version of the script includes a fix for Strava so that it
correctly shows distance and speed.

## Merging Multiple CSV files to one TCX workout

I've heard that if you cycle over a certain number of hours, the
Power Pilot will create multiple files to represent that single
workout. I'm not dedicated enough it seems so I haven't seen this
happen yet. As a result, I don't know how to properly convert a
group of CSV files into one TCX workout. If you have a workout 
session (on firmware 63) with multiple files, please send them
to me so that I can adjust the script to work with it.

## Running the Script

Simply run the script from the shell as follows:

    ./lemondcsv.py 09261300.CSV > 09261300.tcx

The TCX file can then be uploaded to Strava etc as a file
upload.

## Contact/Questions/Bugs/Updates etc

If you find a problem with this script, check you have the latest
version by visiting
[the project on github](https://github.com/tpodowd/lemondcsv).
If you are using the latest version and have a question/bug etc,
please file an [issue](https://github.com/tpodowd/lemondcsv/issues)
if one doesn't already exist and I'll look into it. Sample files
you are having trouble with are always welcome.
