'''
Ellie Lin-Stevens
ACAD 191, Fall 2026
elinstev@usc.edu
Exercise 6
'''

import re
import pandas as pd
import matplotlib.pyplot as plt
import mplcursors
import contextily

# Rough box around South LA, Downtown LA, and Koreatown
# (change these numbers if the map looks off)
SOUTH = 34.025
NORTH = 34.065
WEST = -118.28
EAST = -118.225

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

        # sorts cheapest to most expensive so the red dots are drawn on top
        data = data.sort_values("Price")
        return data
    except (KeyError, ValueError):
        print("Something is wrong with the columns in the file.")
        return None

# Function: graphCounts
# Purpose: makes a bar chart of how many meters are at each price
# Parameters: 1, the data
# Side Effects: creates a chart (it appears when plt.show() runs in main)
# Returns: none
def graphCounts(data):
    counts = data["Price"].value_counts().sort_index()

    labels = []
    for price in counts.index:
        labels.append("$" + format(price, ".2f"))

    plt.figure(figsize=(10, 5))
    plt.bar(labels, counts.values, color="steelblue")
    plt.title("Parking Meters by Price (South LA, Downtown, Koreatown)")
    plt.xlabel("Highest hourly price")
    plt.ylabel("Number of meters")
    plt.xticks(rotation=45)
    plt.tight_layout()

# Function: graphMap
# Purpose: makes a map of the meters, colored green (cheap) to red (expensive)
# Parameters: 1, the data
# Side Effects: creates a map (it appears when plt.show() runs in main)
# Returns: none
def graphMap(data):
    ax = data.plot.scatter(
        x="Longitude",
        y="Latitude",
        c="Price",
        cmap="RdYlGn_r",
        vmin=LOW_PRICE,
        vmax=HIGH_PRICE,
        s=6,
        colorbar=True,
        figsize=(9, 9)
    )
    # stretches the map a little so LA is not squished
    ax.set_aspect(1.2)
    ax.set_title("LA Parking Meter Prices per Hour (zoom with the magnifier button)")

 
    # gray street map (best for seeing the colored dots)
    contextily.add_basemap(ax, crs="EPSG:4326", source=contextily.providers.Esri.WorldGrayCanvas)
  

    # shows the street and price when you hover over a dot
    cursor = mplcursors.cursor(ax.collections[0], hover=True)

    # Function: onHover
    # Purpose: sets the hover text for the meter you are pointing at
    # Parameters: 1, the selected dot
    # Side Effects: changes the text of the hover box
    # Returns: none
    @cursor.connect("add")
    def onHover(selected):
        row = data.iloc[selected.index]
        selected.annotation.set_text(row["BlockFace"] + "\n" + row["RateRange"])

# Function: main
# Purpose: runs loadFile, cleanData, graphCounts, and graphMap
# Parameters: none
# Side Effects: prints to the console, asks for input, shows a chart and a map
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

    graphCounts(data)
    graphMap(data)
    # shows both windows at the same time
    plt.show()

main()