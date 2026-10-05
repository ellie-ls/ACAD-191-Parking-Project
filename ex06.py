'''
Ellie Lin-Stevens
ACAD 191, Fall 2026
elinstev@usc.edu
Exercise 6
'''

import re
import pandas as pd
import matplotlib.pyplot as plt
import folium
from branca.colormap import LinearColormap

# Rough box around South LA, Downtown LA, and Koreatown
# (change these numbers if the map looks off)
SOUTH = 33.93
NORTH = 34.07
WEST = -118.34
EAST = -118.19

# Prices at or below LOW are fully green, prices at or above HIGH are fully red
LOW_PRICE = 0.50
HIGH_PRICE = 6.00

# Function: loadFile
# Purpose: loads the file into the code and grabs the data
# Parameters: 1, the file name
# Side Effects: prints a warning if file is not found
# Returns: data
def loadFile(fileName):
    try:
        data = pd.read_csv(fileName)
        return data
    except FileNotFoundError:
        print("File not found")
        return None

# Function: getPrice
# Purpose: turns a rate like "$0.50 - $5.00" into one number (the highest hourly price)
# Parameters: 1, the rate text
# Side Effects: none
# Returns: the price as a number, or None if it can't be read
def getPrice(rateText):
    try:
        # finds every number in the text, like "$1.5/H - $6/10H" -> 1.5, 6, 10
        numbers = re.findall(r"\d+\.?\d*", rateText)
        prices = []
        for number in numbers:
            prices.append(float(number))

        # "/H" rates are like "$1.5/H - $6/10H": the first number is the hourly
        # price and the second is a total for many hours, so only use the first
        if "/H" in rateText:
            return prices[0]
        return max(prices)
    except (ValueError, IndexError, TypeError):
        return None

# Function: cleanData
# Purpose: makes latitude/longitude/price columns and keeps only meters inside the area
# Parameters: 1, the data
# Side Effects: prints a warning if a column is missing
# Returns: the cleaned data
def cleanData(data):
    try:
        # LatLng looks like "(34.077536, -118.264627)", so split it into two columns
        parts = data["LatLng"].str.strip("()").str.split(",", expand=True)
        data["Latitude"] = parts[0].astype(float)
        data["Longitude"] = parts[1].astype(float)

        data["Price"] = data["RateRange"].apply(getPrice)
        data = data.dropna(subset=["Latitude", "Longitude", "Price"])

        data = data[data["Latitude"] > SOUTH]
        data = data[data["Latitude"] < NORTH]
        data = data[data["Longitude"] > WEST]
        data = data[data["Longitude"] < EAST]
        return data
    except (KeyError, ValueError):
        print("Something is wrong with the columns in the file.")
        return None

# Function: makeColorScale
# Purpose: makes the green -> yellow -> red color range for prices
# Parameters: none
# Side Effects: none
# Returns: the color scale
def makeColorScale():
    colorScale = LinearColormap(
        ["green", "yellow", "red"],
        vmin=LOW_PRICE,
        vmax=HIGH_PRICE
    )
    colorScale.caption = "Meter price per hour (highest rate)"
    return colorScale

# Function: graphCounts
# Purpose: shows a bar chart of how many meters are at each price
# Parameters: 2, the data and the color scale
# Side Effects: shows a chart
# Returns: none
def graphCounts(data, colorScale):
    counts = data["Price"].value_counts().sort_index()

    labels = []
    colors = []
    for price in counts.index:
        labels.append("$" + format(price, ".2f"))
        colors.append(colorScale(price))

    plt.figure(figsize=(10, 5))
    plt.bar(labels, counts.values, color=colors)
    plt.title("Parking Meters by Price (South LA, Downtown, Koreatown)")
    plt.xlabel("Highest hourly price")
    plt.ylabel("Number of meters")
    plt.xticks(rotation=45)
    plt.tight_layout()
    plt.show()

# Function: makeMap
# Purpose: makes a map with a colored dot on every meter
# Parameters: 2, the data and the color scale
# Side Effects: saves parking_map.html
# Returns: none
def makeMap(data, colorScale):
    parkingMap = folium.Map(location=[34.02, -118.28], zoom_start=12)

    for index, row in data.iterrows():
        label = row["BlockFace"] + ": " + row["RateRange"] + " (" + row["MeteredTimeLimit"] + " limit)"

        folium.CircleMarker(
            location=[row["Latitude"], row["Longitude"]],
            radius=4,
            color=colorScale(row["Price"]),
            weight=0,
            fill=True,
            fill_opacity=0.8,
            tooltip=label
        ).add_to(parkingMap)

    colorScale.add_to(parkingMap)
    parkingMap.save("parking_map.html")
    print("Map saved as parking_map.html. Open it in your browser.")

# Function: main
# Purpose: runs loadFile, cleanData, graphCounts, and makeMap
# Parameters: none
# Side Effects: prints to the console, asks for input, makes a chart and a map
# Returns: none
def main():
    fileName = input("Enter the name of the file: ")
    data = loadFile(fileName)
    if data is None:
        return
    data = cleanData(data)
    if data is None:
        return
    print("Meters in the area:", len(data))

    colorScale = makeColorScale()
    graphCounts(data, colorScale)
    makeMap(data, colorScale)

main()
