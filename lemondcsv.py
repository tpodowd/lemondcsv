#!/usr/bin/env python

# Copyright (c) 2013 Thomas O'Dowd
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
This script converts a native Lemond Revolution Power Pilot CVS
workout file to a Garmin TCX file. The TCX file can be then imported
into applications such as Strava or Garmin Connect.

Simply run the program from the shell as follows:

    ./lemondcsv.py 09261300.CSV > 09261300.tcx
"""

# Some TODO:
# Check error cases like missing file, bad format etc
# Add some sample files for future reference
#
# Known Bugs:
# 1. Lemond format doesn't provide a year so we have to guess based
#    on the current year. At New Year we'll probably be wrong!
# 2. Do we have to care about daylight savings?
# 3. I've heard that if you cycle over a certain number of hours, the
#    Power Pilot will create multiple files to represent that workout.
#    I haven't tried this yet, so I don't know how to convert such a
#    file. If you have a session with multiple files, please send them
#    to me so that I can adjust the script to work with it.

import sys
import csv
import time
from xml.etree import ElementTree
from xml.etree.ElementTree import Element, SubElement

SUPPORTED_FIRMWARE = [63]

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
        exp.append("TIME")
        exp.append("SPEED")
        exp.append("DIST")
        exp.append("POWER")
        exp.append("HEART RATE")
        exp.append("CADENCE")
        exp.append("CALORIES")
        exp.append("TORQUE")
        exp.append("TARGET")
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
        fp = open(file, 'rb')
        rdr = csv.reader(fp)
        self.parseDeviceHdr(rdr.next())
        Point.parsePointHdr(rdr.next())
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
        if len(csvrow) != 11:
            raise Exception("Expected 11 cols, got %d" % len(csvrow))
        self.make = csvrow[0].strip()
        self.model = csvrow[1].strip()
        if (self.make, self.model) != ("LeMond", "Revolution"):
            raise Exception("Not a LeMond Revolution CSV workout file")
        self.fw = self.parseInt(csvrow[2], "FW")
        if self.fw not in SUPPORTED_FIRMWARE:
            err = "Power Pilot Firmware %d is not supported. " % self.fw
            err += "The following versions are supported "
            err += str(SUPPORTED_FIRMWARE)
            raise Exception(err)
        self.hw = self.parseInt(csvrow[3], "HW")
        self.startsec = self.parseTime(csvrow[4], csvrow[5])
        self.alt = self.parseInt(csvrow[6], "Alt")
        self.temp = self.parseInt(csvrow[7], "Temp")
        self.humid = self.parseInt(csvrow[8], "Hum")
        self.tire = self.parseInt(csvrow[9], "Tire")
        self.cf = self.parseInt(csvrow[10], "CF")

    def parseInt(self, str, tag):
        list = str.split(' ')
        if list[0] != tag:
            raise Exception("Expected %s, got %s" % (tag, list[0]))
        return int(list[1])

    def parseTime(self, dstr, tstr):
        # No year provided by lemond. Use current
        ct = time.localtime()
        # Parse using current year and localtime
        # as power pilot is most likely set to localtime
        str = "%d/%s %s" % (ct.tm_year, dstr, tstr)
        t = time.strptime(str, '%Y/%m/%d %H:%M:%S')
        # TODO: set Daylight Savings based on the current time
        # TODO: fix end of year issues due to missing year
        return time.mktime(t)

    @staticmethod
    def isoTimestamp(seconds):
        # Use UTC for isoTimestamp
        tm = time.gmtime(seconds)
        return time.strftime("%Y-%m-%dT%H:%M:%S.000Z", tm)

    @staticmethod
    def metersPerSec(speed):
        return speed / 3.6

    def writeTCX(self):
        tcdb = self.trainingCenterDB()
        print ElementTree.tostring(tcdb, encoding='UTF-8')

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
        name.text = "%s %s" % (self.make, self.model)
        unit = SubElement(c, 'UnitId')
        unit.text = '0'
        prd = SubElement(c, 'ProductID')
        prd.text = str(self.hw)
        ver = SubElement(c, 'Version')
        vmaj = SubElement(ver, 'VersionMajor')
        vmaj.text = str(self.fw)
        vmin = SubElement(ver, 'VersionMinor')
        vmin.text = '0'
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

if len(sys.argv) != 2:
    sys.stderr.write("Usage: %s workout.csv > workout.tcx\n" % sys.argv[0])
    sys.exit(1)
else:
    revo = Revolution(sys.argv[1])
    revo.writeTCX()
