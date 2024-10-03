#!/usr/bin/env python

# Copyright (c) 2024 Thomas O'Dowd
#
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.

"""
This script converts a native LeMond Revolution GT CVS
workout file to a Garmin TCX file. The TCX file can be then imported
into applications such as Strava or Garmin Connect.

Simply run the program from the shell as follows:

    ./lemondcsv_gt.py 09261300.CSV

This will create a new file of the same name but with a TCX extension
in the same directory as the CSV file, ie 09261300.tcx.

This is version: v1.2.0. You can always find the latest version of
this script at: https://github.com/tpodowd/lemondcsv
"""

# Some TODO:
# Check error cases like missing file, bad format etc
# Add some sample files for future reference
#
# Known Bugs:
# 1. Do we have to care about daylight savings?
# This is all based on one example file. Not sure if we nailed everything

import os
import sys
import csv
import time
import getopt
from xml.etree import ElementTree
from xml.etree.ElementTree import Element, SubElement

SUPPORTED_FIRMWARE = ["0.31"]

XSI = 'http://www.w3.org/2001/XMLSchema-instance'
XSD = 'http://www.garmin.com/xmlschemas/TrainingCenterDatabasev2.xsd'
XML_NS = 'http://www.garmin.com/xmlschemas/TrainingCenterDatabase/v2'
EXT_NS = 'http://www.garmin.com/xmlschemas/ActivityExtension/v2'


class Point:
    """
    The Power Pilot logs a data point every second with information
    such as speed, distance, heartrate, power etc. This object
    represents one particular data point.
    """
    def __init__(self, csvrow):
        self.secs = self.timeToSecs(csvrow[0])
        self.speed = float(csvrow[1])
        self.dist = float(csvrow[2])
        self.power = int(csvrow[3])
        self.heart = int(csvrow[4])
        self.cadence = int(csvrow[5])
        self.calories = int(csvrow[6])
        self.torque = int(csvrow[7])
        self.target = csvrow[8]

    def timeToSecs(self, tstr):
        t = time.strptime(tstr, '%H:%M:%S')
        return (t.tm_hour * 3600) + (t.tm_min * 60) + t.tm_sec

    def __str__(self):
        return "%d %f %d" % (self.secs, self.speed, self.power)

    def trackpointElement(self, start):
        tp = Element('Trackpoint')
        time = SubElement(tp, 'Time')
        time.text = Revolution.isoTimestamp(start + self.secs)
        dist = SubElement(tp, 'DistanceMeters')
        dist.text = str(self.dist * 1000)
        heart = SubElement(tp, 'HeartRateBpm')
        heartvalue = SubElement(heart, 'Value')
        heartvalue.text = str(self.heart)
        cadence = SubElement(tp, 'Cadence')
        cadence.text = str(self.cadence)
        ext = SubElement(tp, 'Extensions')
        tpx = SubElement(ext, 'TPX', {'xmlns': EXT_NS})
        mps = Revolution.metersPerSec(self.speed)
        speed = SubElement(tpx, 'Speed')
        speed.text = str(mps)
        watts = SubElement(tpx, 'Watts')
        watts.text = str(self.power)
        return tp

    def trackpointExtension(self, ext, tag, text):
        tpx = SubElement(ext, 'TPX', {'xmlns': EXT_NS})
        value = SubElement(tpx, tag)
        value.text = str(text)

    @staticmethod
    def parsePointHdr(csvrow):
        """
        We assume the order of the fields when parsing the points
        so we fail if the headers are unexpectedly ordered or
        missing or more than expected.
        """
        if len(csvrow) != 9:
            raise Exception("Expected 9 cols, got %d" % len(csvrow))
        exp = []
        exp.append("secs")
        exp.append("SPEED")
        exp.append("DIST")
        exp.append("POWER")
        exp.append("heart")
        exp.append("cadence")
        exp.append("CALORIES")
        exp.append("TORQUE")
        exp.append("target")
        if exp != csvrow:
            raise Exception("Unexpected Header %s != %s" % (exp, csvrow))


class Revolution:
    """
    The object represents the complete Lemond Revolution workout file.
    """
    def __init__(self, file):
        self.maxSpeed = 0
        self.maxHeart = 0
        self.maxCadence = 0
        self.maxWatts = 0
        self.ttlSpeed = 0
        self.ttlHeart = 0
        self.ttlCadence = 0
        self.ttlWatts = 0
        self.ttlDist = 0     # meters
        self.readCSV(file)

    def readCSV(self, file):
        fp = open(file, 'rt')
        rdr = csv.reader(fp)
        self.parseDeviceHdr(next(rdr))
        Point.parsePointHdr(next(rdr))
        self.points = []
        for row in rdr:
            p = Point(row)
            self.points.append(p)
            self.collectStats(p)
            self.fixDistance(p)

    def fixDistance(self, p):
        # Current version of lemond uses km to 1 decimal place for
        # distance travelled. Therefore distance by default only
        # increments every 100m travelled which means many points
        # share the same distance so it appears we are not moving.
        # As Strava uses distance to calculate speed, we correct
        # the distance by using speed.
        mps = Revolution.metersPerSec(p.speed)
        self.ttlDist += mps
        p.dist = self.ttlDist / 1000  # km

    def collectStats(self, p):
        self.ttlSpeed += p.speed
        self.ttlHeart += p.heart
        self.ttlCadence += p.cadence
        self.ttlWatts += p.power
        if p.speed > self.maxSpeed:
            self.maxSpeed = p.speed
        if p.heart > self.maxHeart:
            self.maxHeart = p.heart
        if p.cadence > self.maxCadence:
            self.maxCadence = p.cadence
        if p.power > self.maxWatts:
            self.maxWatts = p.power

    def parseDeviceHdr(self, csvrow):
        if len(csvrow) != 9:
            raise Exception("Expected 9 cols, got %d" % len(csvrow))
        self.make_model = csvrow[0].strip()
        if self.make_model != "LeMond Revolution":
            raise Exception("Not a LeMond Revolution CSV workout file")
        fw_str = csvrow[1]
        if not fw_str.startswith("FW "):
            raise Exception("Firmware string format unexpected %s", fw_str)
        self.fw = fw_str[3:].strip()  # "FW 0.31" -> "0.31"
        if self.fw not in SUPPORTED_FIRMWARE:
            err = "Power Pilot Firmware %s is not supported. " % self.fw
            err += "The following versions are supported "
            err += str(SUPPORTED_FIRMWARE)
            raise Exception(err)
        self.hw = csvrow[2][3:].strip() # "HW 1.0" -> "1.0"
        # Not sure what STN is in 3?
        # Date and Time is 4 and 5... Fix 5 to prepend a 0 if missing
        self.startsec = self.parseTime(csvrow[4], "{0:>05s}".format(csvrow[5]))

        # Not used
        #self.alt = self.parseInt(csvrow[6], "Alt")
        #self.temp = self.parseInt(csvrow[7], "Temp")
        #self.humid = self.parseInt(csvrow[8], "Hum")
        #self.tire = self.parseInt(csvrow[9], "Tire")
        #self.cf = self.parseInt(csvrow[10], "CF")

    def parseInt(self, str, tag):
        list = str.split(' ')
        if list[0] != tag:
            raise Exception("Expected %s, got %s" % (tag, list[0]))
        return int(list[1])

    # dstr is YYMMDD and tstr is HH:MM
    def parseTime(self, dstr, tstr):
        # Parse using localtime as most likely using localtime
        str = "%s %s" % (dstr, tstr)
        t = time.strptime(str, '%y%m%d %H:%M')
        # TODO: set Daylight Savings based on the current time
        return time.mktime(t)

    @staticmethod
    def isoTimestamp(seconds):
        # Use UTC for isoTimestamp
        tm = time.gmtime(seconds)
        return time.strftime("%Y-%m-%dT%H:%M:%S.000Z", tm)

    @staticmethod
    def metersPerSec(speed):
        return speed / 3.6

    def writeTCX(self, file):
        tcdb = self.trainingCenterDB()
        et = ElementTree.ElementTree(tcdb)
        try:
            et.write(file, 'UTF-8', True)
        except TypeError:
            # pre-python 2.7
            et.write(file, 'UTF-8')

    def trainingCenterDB(self):
        dict = {'xsi:schemaLocation': XML_NS + ' ' + XSD,
                'xmlns': XML_NS,
                'xmlns:xsi': XSI}
        tcdb = Element('TrainingCenterDatabase', dict)
        acts = SubElement(tcdb, 'Activities')
        self.addActivity(acts)
        self.addAuthor(tcdb)
        return tcdb

    def addActivity(self, acts):
        act = SubElement(acts, 'Activity', {'Sport': 'Biking'})
        id = SubElement(act, 'Id')
        id.text = Revolution.isoTimestamp(self.startsec)
        self.addLap(act)
        self.addCreator(act)

    def addCreator(self, act):
        c = SubElement(act, 'Creator', {'xsi:type': 'Device_t'})
        name = SubElement(c, 'Name')
        name.text = self.make_model
        unit = SubElement(c, 'UnitId')
        unit.text = '0'
        prd = SubElement(c, 'ProductID')
        prd.text = str(self.hw)
        ver = SubElement(c, 'Version')
        fw_ver = self.fw.split('.')
        vmaj = SubElement(ver, 'VersionMajor')
        vmaj.text = fw_ver[0]
        vmin = SubElement(ver, 'VersionMinor')
        vmin.text = fw_ver[1]
        bmaj = SubElement(ver, 'BuildMajor')
        bmaj.text = '0'
        bmin = SubElement(ver, 'BuildMinor')
        bmin.text = '0'

    def addAuthor(self, tcdb):
        a = SubElement(tcdb, 'Author', {'xsi:type': 'Application_t'})
        name = SubElement(a, 'Name')
        name.text = 'Revolution CSV to TCX Convertor'
        build = SubElement(a, 'Build')
        ver = SubElement(build, 'Version')
        vmaj = SubElement(ver, 'VersionMajor')
        vmaj.text = '1'
        vmin = SubElement(ver, 'VersionMinor')
        vmin.text = '0'
        bmaj = SubElement(ver, 'BuildMajor')
        bmaj.text = '0'
        bmin = SubElement(ver, 'BuildMinor')
        bmin.text = '0'
        lang = SubElement(a, 'LangID')
        lang.text = 'en'
        partnum = SubElement(a, 'PartNumber')
        partnum.text = 'none'

    def addLap(self, act):
        st = Revolution.isoTimestamp(self.startsec)
        lap = SubElement(act, 'Lap', {'StartTime': st})
        last = len(self.points) - 1
        tts = SubElement(lap, 'TotalTimeSeconds')
        tts.text = str(self.points[last].secs)
        dist = SubElement(lap, 'DistanceMeters')
        dist.text = str(self.points[last].dist * 1000)
        ms = SubElement(lap, 'MaximumSpeed')
        ms.text = str(Revolution.metersPerSec(self.maxSpeed))
        calories = SubElement(lap, 'Calories')
        calories.text = str(self.points[last].calories)
        avgheart = SubElement(lap, 'AverageHeartRateBpm')
        avgheartvalue = SubElement(avgheart, 'Value')
        avgheartvalue.text = str(self.ttlHeart / (last+1))
        maxheart = SubElement(lap, 'MaximumHeartRateBpm')
        maxheartvalue = SubElement(maxheart, 'Value')
        maxheartvalue.text = str(self.maxHeart)
        intensity = SubElement(lap, 'Intensity')
        intensity.text = 'Active'
        cadence = SubElement(lap, 'Cadence')
        cadence.text = str(self.ttlCadence / (last+1))
        trigger = SubElement(lap, 'TriggerMethod')
        trigger.text = 'Manual'
        lap.append(self.trackElement())
        ext = SubElement(lap, 'Extensions')
        self.LapExtension(ext, 'MaxBikeCadence', self.maxCadence)
        avgspeed = Revolution.metersPerSec(self.ttlSpeed / (last+1))
        self.LapExtension(ext, 'AvgSpeed', avgspeed)
        avgwatts = self.ttlWatts / (last+1)
        self.LapExtension(ext, 'AvgWatts', avgwatts)
        self.LapExtension(ext, 'MaxWatts', self.maxWatts)

    def LapExtension(self, ext, tag, text):
        tpx = SubElement(ext, 'LX', {'xmlns': EXT_NS})
        value = SubElement(tpx, tag)
        value.text = str(text)

    def trackElement(self):
        t = Element('Track')
        for p in self.points:
            t.append(p.trackpointElement(self.startsec))
        return t


def output_name(iname):
    # validate name ends with .CSV
    if iname.lower().endswith(".csv"):
        prefix = iname[:-3]
        oname = prefix + "tcx"
        if not os.path.exists(oname):
            return oname
        else:
            raise Exception("File %s already exists. Cannot continue." % oname)
    else:
        raise Exception("%s does not end with .csv" % iname)


def usage_exit():
    sys.stderr.write("Usage: lemondcsv.py [-f workout.tcx] workout.csv\n")
    sys.exit(1)

opts, args = getopt.getopt(sys.argv[1:], 'f:h')
oname = None
for opt, arg in opts:
    if opt == '-f':
        oname = arg
    elif opt == '-h':
        usage_exit()

if len(args) != 1:
    # TODO: support multiple CSV files to join them up to one TCX.
    usage_exit()
else:
    iname = args[0]
    if oname is None:
        oname = output_name(iname)
    revo = Revolution(iname)
    if oname == '-':
        if hasattr(sys.stdout, 'buffer'):
            ofile = sys.stdout.buffer
        else:
            ofile = sys.stdout
    else:
        sys.stderr.write("Writing to: %s\n" % oname)
        ofile = open(oname, "wb")
    revo.writeTCX(ofile)
    if oname != '-':
        ofile.close()
