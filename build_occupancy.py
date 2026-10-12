'''
Ellie Lin-Stevens & Nina Zhang
ACAD 191, Fall 2026
elinstev@usc.edu & nzhang21@usc.edu
Exercise 6 - occupancy builder

Reads the LA parking sensor files (Sensor_Transactions_YYYY_MM.csv) and works out how often
each meter is open for every day of the week and hour of the day. Saves the result as
occupancy.json, which ex06.py uses to show "Usually open X% of the time" when you hover a meter.

The sensor files are big (about 8 GB), so this only needs to run once, or again when you
download new months. It takes around 10-20 minutes.
'''

import os
import sys
import glob
import json
import numpy as np
import pandas as pd
from multiprocessing import Pool
from ex06 import loadFile

# folder with the Sensor_Transactions_*.csv files (or pass a folder when running the script)
SENSOR_FOLDER = "/Users/elizalin-stevens/Downloads/parking tracking"

# checks what every meter is doing every 5 minutes
SAMPLE_MINUTES = 5

# if a sensor sends nothing for this many hours, it is probably broken, so that time is skipped
MAX_SILENCE_HOURS = 48

# an hour slot (like "Tuesday 2-3 PM") needs at least this many weeks of data to show a number
MIN_WEEKS_PER_SLOT = 4

# meters without a sensor borrow from sensored meters this close (in meters)
NEARBY_METERS = 50
LESS_CERTAIN_METERS = 100
NEIGHBORS_TO_USE = 5

# 7 days x 24 hours = 168 hour slots, Monday 12-1 AM is slot 0
SLOTS = 7 * 24

# Function: readMonth
# Purpose: counts, for every meter, how many 5-minute checks were open in each hour slot
# Parameters: 1, the path to one month's sensor file
# Side Effects: prints when the month is done
# Returns: a dictionary of SpaceID -> (open counts, total counts, set of weeks with data)
def readMonth(path):
    data = pd.read_csv(path, usecols=["SpaceID", "EventTime_Local", "OccupancyState"], dtype=str)
    data["SpaceID"] = data["SpaceID"].str.strip()
    data["Time"] = pd.to_datetime(data["EventTime_Local"], format="%m/%d/%Y %I:%M:%S %p")
    data = data.sort_values(["SpaceID", "Time"])

    # every 5 minutes from the start of the month to the end
    start = data["Time"].min().normalize().replace(day=1)
    end = start + pd.offsets.MonthBegin(1)
    checks = pd.date_range(start, end, freq=str(SAMPLE_MINUTES) + "min", inclusive="left")
    checkTimes = checks.to_numpy().astype("datetime64[ns]").astype("int64")
    checkSlots = (checks.dayofweek * 24 + checks.hour).to_numpy()
    checkWeeks = ((checks - pd.Timestamp("2020-01-06")).days // 7).to_numpy()
    maxSilence = int(MAX_SILENCE_HOURS * 3600 * 1e9)

    counts = {}
    for spaceId, events in data.groupby("SpaceID"):
        times = events["Time"].to_numpy().astype("datetime64[ns]").astype("int64")
        states = events["OccupancyState"].to_numpy()

        # for each check, finds the last thing the sensor said before it
        last = np.searchsorted(times, checkTimes, side="right") - 1
        valid = last >= 0
        last = np.clip(last, 0, None)
        valid &= (checkTimes - times[last]) <= maxSilence
        valid &= states[last] != "UNKNOWN"
        isOpen = valid & (states[last] == "VACANT")

        openCount = np.bincount(checkSlots[isOpen], minlength=SLOTS)
        totalCount = np.bincount(checkSlots[valid], minlength=SLOTS)
        # which weeks had data in each slot (to make sure a number is based on enough weeks)
        weeks = set(zip(checkSlots[valid].tolist(), checkWeeks[valid].tolist()))
        counts[spaceId] = (openCount, totalCount, weeks)

    print("done", os.path.basename(path), flush=True)
    return counts

# Function: addUp
# Purpose: adds all the months together
# Parameters: 1, the list of monthly results from readMonth
# Side Effects: none
# Returns: a dictionary of SpaceID -> (open counts, total counts, weeks per slot, total weeks)
def addUp(months):
    totals = {}
    for month in months:
        for spaceId, (openCount, totalCount, weeks) in month.items():
            if spaceId not in totals:
                totals[spaceId] = [np.zeros(SLOTS), np.zeros(SLOTS), set()]
            totals[spaceId][0] += openCount
            totals[spaceId][1] += totalCount
            totals[spaceId][2] |= weeks

    result = {}
    for spaceId, (openCount, totalCount, weeks) in totals.items():
        weeksPerSlot = np.zeros(SLOTS)
        for slot, week in weeks:
            weeksPerSlot[slot] += 1
        allWeeks = len(set(week for slot, week in weeks))
        result[spaceId] = (openCount, totalCount, weeksPerSlot, allWeeks)
    return result

# Function: toPercents
# Purpose: turns open/total counts into whole-number percents, or None when there's not enough data
# Parameters: 3, the open counts, the total counts, and the weeks of data in each slot
# Side Effects: none
# Returns: a list of 168 percents (or None)
def toPercents(openCount, totalCount, weeksPerSlot):
    percents = []
    for slot in range(SLOTS):
        if weeksPerSlot[slot] < MIN_WEEKS_PER_SLOT or totalCount[slot] == 0:
            percents.append(None)
        else:
            percents.append(int(round(100 * openCount[slot] / totalCount[slot])))
    return percents

# Function: getMeterLocations
# Purpose: gets the location of every meter in the city meter file (in meters, for distances)
# Parameters: 1, the meter file name
# Side Effects: none
# Returns: a table with SpaceID, X, and Y
def getMeterLocations(fileName):
    meters = loadFile(fileName)
    meters["SpaceID"] = meters["SpaceID"].str.strip()
    parts = meters["LatLng"].str.strip("()").str.split(",", expand=True)
    meters["Latitude"] = pd.to_numeric(parts[0], errors="coerce")
    meters["Longitude"] = pd.to_numeric(parts[1], errors="coerce")
    meters = meters.dropna(subset=["Latitude", "Longitude"]).drop_duplicates("SpaceID")
    # in LA, 1 degree of latitude is about 111 km and 1 degree of longitude is about 92 km
    meters["X"] = meters["Longitude"] * 92000
    meters["Y"] = meters["Latitude"] * 111000
    return meters[["SpaceID", "X", "Y"]].reset_index(drop=True)

# Function: main
# Purpose: reads every sensor file, works out the open percents, borrows for nearby meters,
#          and saves occupancy.json
# Parameters: none
# Side Effects: prints progress, saves occupancy.json next to this file
# Returns: none
def main():
    folder = sys.argv[1] if len(sys.argv) > 1 else SENSOR_FOLDER
    files = sorted(glob.glob(os.path.join(folder, "Sensor_Transactions_*.csv")))
    if len(files) == 0:
        print("No Sensor_Transactions_*.csv files found in", folder)
        return
    print("Reading", len(files), "sensor files...")

    # reads 4 months at a time to go faster
    with Pool(4) as pool:
        months = pool.map(readMonth, files)
    measured = addUp(months)

    here = os.path.dirname(os.path.abspath(__file__))
    meters = getMeterLocations(os.path.join(here, "metered_parking.csv"))
    output = {}

    # meters with their own sensor
    for spaceId, (openCount, totalCount, weeksPerSlot, allWeeks) in measured.items():
        output[spaceId] = {
            "open": toPercents(openCount, totalCount, weeksPerSlot),
            "weeks": allWeeks,
            "source": "measured"
        }

    # meters without a sensor borrow from up to 5 of the closest sensored meters within 100 m
    hasSensor = meters["SpaceID"].isin(measured.keys()).to_numpy()
    sensorX = meters["X"].to_numpy()[hasSensor]
    sensorY = meters["Y"].to_numpy()[hasSensor]
    sensorIds = meters["SpaceID"].to_numpy()[hasSensor]
    for index in np.where(~hasSensor)[0]:
        distances = np.hypot(sensorX - meters.at[index, "X"], sensorY - meters.at[index, "Y"])
        closest = np.argsort(distances)[:NEIGHBORS_TO_USE]
        closest = closest[distances[closest] <= LESS_CERTAIN_METERS]
        if len(closest) == 0:
            continue

        openCount = np.zeros(SLOTS)
        totalCount = np.zeros(SLOTS)
        weeksPerSlot = np.zeros(SLOTS)
        for neighbor in closest:
            neighborOpen, neighborTotal, neighborWeeks, allWeeks = measured[sensorIds[neighbor]]
            openCount += neighborOpen
            totalCount += neighborTotal
            weeksPerSlot = np.maximum(weeksPerSlot, neighborWeeks)

        if distances[closest[0]] <= NEARBY_METERS:
            source = "nearby"
        else:
            source = "nearby-less-certain"
        output[meters.at[index, "SpaceID"]] = {
            "open": toPercents(openCount, totalCount, weeksPerSlot),
            "source": source
        }

    # the months the data covers, like "2023_09" to "2026_08"
    first = os.path.basename(files[0])[len("Sensor_Transactions_"):-4]
    last = os.path.basename(files[-1])[len("Sensor_Transactions_"):-4]
    outFile = os.path.join(here, "occupancy.json")
    with open(outFile, "w") as file:
        json.dump({"from": first, "to": last, "meters": output}, file, separators=(",", ":"))

    sources = pd.Series([meter["source"] for meter in output.values()]).value_counts()
    print("Saved", outFile)
    print(sources.to_string())

if __name__ == "__main__":
    main()
