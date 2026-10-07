'''
Ellie Lin-Stevens & Nina Zhang
ACAD 191, Fall 2026
elinstev@usc.edu & nzhang21@usc.edu
Exercise 6
'''

import re
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.patheffects as patheffects
from matplotlib.path import Path
import contextily

SOUTH = 34.025
NORTH = 34.065
WEST = -118.28
EAST = -118.225

LOW_PRICE = 0.50
HIGH_PRICE = 6.00

ZOOM_SPEED = 0.9
MAX_SCROLL = 3

BOX_FONT_SIZE = 14
BOX_PADDING = 0.8
BOX_ROUNDING = 0.9
BOX_TAIL = 0.55
BOX_HEIGHT_ABOVE_DOT = 30
BOX_SHADOW = 0.3

DOT_SIZE = 6
HOVER_DOT_SIZE = 45

MOVE_STEP = 0.125
MOVE_DELAY = 20

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
        numbers = re.findall(r"\d+\.?\d*", rateText)
        prices = []
        for number in numbers:
            prices.append(float(number))


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
        parts = data["LatLng"].str.strip("()").str.split(",", expand=True)
        data["Latitude"] = parts[0].astype(float)
        data["Longitude"] = parts[1].astype(float)

        data["Price"] = data["RateRange"].apply(getPrice)
        data = data.dropna(subset=["Latitude", "Longitude", "Price"])

        data = data[data["Latitude"] > SOUTH]
        data = data[data["Latitude"] < NORTH]
        data = data[data["Longitude"] > WEST]
        data = data[data["Longitude"] < EAST]

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

# Function: bubbleShape
# Purpose: draws the outline of the hover box: a rounded box with a little tail at the bottom
# Parameters: 5, the left and bottom of the text, its width and height, and the font size
# Side Effects: none
# Returns: the outline as a Path
def bubbleShape(x, y, width, height, fontSize):
    padding = BOX_PADDING * fontSize
    corner = BOX_ROUNDING * fontSize
    tail = BOX_TAIL * fontSize

    left = x - padding
    right = x + width + padding
    bottom = y - padding
    top = y + height + padding
    middle = (left + right) / 2

    points = [
        (left + corner, top),
        (right - corner, top), (right, top), (right, top - corner),
        (right, bottom + corner), (right, bottom), (right - corner, bottom),
        (middle + tail, bottom), (middle, bottom - tail), (middle - tail, bottom),
        (left + corner, bottom), (left, bottom), (left, bottom + corner),
        (left, top - corner), (left, top), (left + corner, top),
        (left + corner, top)
    ]
    steps = [
        Path.MOVETO,
        Path.LINETO, Path.CURVE3, Path.CURVE3,
        Path.LINETO, Path.CURVE3, Path.CURVE3,
        Path.LINETO, Path.LINETO, Path.LINETO,
        Path.LINETO, Path.CURVE3, Path.CURVE3,
        Path.LINETO, Path.CURVE3, Path.CURVE3,
        Path.CLOSEPOLY
    ]
    return Path(points, steps)

# Function: graphMap
# Purpose: makes a map of the meters, colored green (cheap) to red (expensive)
# Parameters: 1, the data
# Side Effects: creates a map (it appears when plt.show() runs in main),
#               makes the meter you point at bigger and shows a box above it
#               (the box fades in the first time, then slides from meter to meter),
#               and lets you zoom it by scrolling the trackpad or mouse wheel
# Returns: none
def graphMap(data):
    ax = data.plot.scatter(
        x="Longitude",
        y="Latitude",
        c="Price",
        cmap="RdYlGn_r",
        vmin=LOW_PRICE,
        vmax=HIGH_PRICE,
        s=DOT_SIZE,
        colorbar=True,
        figsize=(9, 9)
    )
    ax.set_aspect(1.2)
    ax.set_title("LA Parking Meter Prices per Hour (scroll to zoom)")

    colorbar = ax.figure.axes[-1]
    colorbar.yaxis.set_major_formatter("${x:.2f}")
    colorbar.set_ylabel("Highest hourly price")

    contextily.add_basemap(ax, crs="EPSG:4326", source=contextily.providers.Esri.WorldGrayCanvas)

    canvas = ax.figure.canvas
    dots = ax.collections[0]

    # the box and the big dot are "animated" so they can be redrawn quickly
    # on top of a saved picture of the map, instead of redrawing every meter
    bigDot = ax.scatter(
        [], [],
        s=DOT_SIZE,
        edgecolor="white",
        linewidth=1.5,
        zorder=3,
        animated=True
    )
    box = ax.annotate(
        "",
        xy=(0, 0),
        xytext=(0, BOX_HEIGHT_ABOVE_DOT),
        textcoords="offset points",
        horizontalalignment="center",
        verticalalignment="bottom",
        fontsize=BOX_FONT_SIZE,
        linespacing=1.5,
        bbox=dict(boxstyle=bubbleShape, facecolor="white", edgecolor="none"),
        zorder=4,
        visible=False,
        animated=True
    )

    timer = canvas.new_timer(interval=MOVE_DELAY)
    hover = {"meter": None, "map": None, "progress": 1, "fading": False,
             "startX": 0, "startY": 0, "endX": 0, "endY": 0}

    # Function: setBoxAlpha
    # Purpose: makes the hover box (its text, background, and shadow) more or less see-through
    # Parameters: 1, how solid it should be (0 is invisible, 1 is solid)
    # Side Effects: changes how the hover box looks
    # Returns: none
    def setBoxAlpha(alpha):
        box.set_alpha(alpha)
        background = box.get_bbox_patch()
        background.set_alpha(alpha)
        background.set_path_effects([
            patheffects.SimplePatchShadow(offset=(0, -2), shadow_rgbFace="black", alpha=BOX_SHADOW * alpha),
            patheffects.Normal()
        ])

    # Function: drawHover
    # Purpose: draws the big dot and the hover box on top of the saved picture of the map
    # Parameters: none
    # Side Effects: changes what the map window shows
    # Returns: none
    def drawHover():
        if hover["map"] is None:
            canvas.draw_idle()
            return
        canvas.restore_region(hover["map"])
        ax.draw_artist(bigDot)
        ax.draw_artist(box)
        canvas.blit(ax.figure.bbox)

    # Function: onDraw
    # Purpose: saves a picture of the map every time it is fully redrawn (at the start, after a zoom, after a resize)
    # Parameters: 1, the draw event
    # Side Effects: saves the picture and draws the big dot and the hover box on top
    # Returns: none
    def onDraw(event):
        hover["map"] = canvas.copy_from_bbox(ax.figure.bbox)
        ax.draw_artist(bigDot)
        ax.draw_artist(box)

    # Function: moveHover
    # Purpose: moves the hover box a little closer to the meter and grows the big dot each time the timer ticks
    # Parameters: none
    # Side Effects: changes the hover box and the big dot, stops the timer when they arrive
    # Returns: none
    def moveHover():
        hover["progress"] = min(1, hover["progress"] + MOVE_STEP)
        # starts fast and slows down at the end
        eased = hover["progress"] * (2 - hover["progress"])

        x = hover["startX"] + (hover["endX"] - hover["startX"]) * eased
        y = hover["startY"] + (hover["endY"] - hover["startY"]) * eased
        box.xy = (x, y)
        bigDot.set_sizes([DOT_SIZE + (HOVER_DOT_SIZE - DOT_SIZE) * eased])
        if hover["fading"]:
            setBoxAlpha(eased)

        if hover["progress"] == 1:
            hover["fading"] = False
            timer.stop()
        drawHover()

    # Function: onMove
    # Purpose: finds the meter under the mouse and sends the hover box and the big dot to it
    # Parameters: 1, the mouse move event
    # Side Effects: changes the hover text and starts the timer that moves the box
    # Returns: none
    def onMove(event):
        if event.inaxes != ax:
            return
        found, details = dots.contains(event)
        if not found:
            return
        meter = details["ind"][-1]
        if meter == hover["meter"]:
            return
        hover["meter"] = meter

        row = data.iloc[meter]
        # a "\" in front of each "$" keeps matplotlib from reading the prices as math
        box.set_text(row["BlockFace"] + "\n" + row["RateRange"].replace("$", "\\$"))
        bigDot.set_offsets([(row["Longitude"], row["Latitude"])])
        bigDot.set_facecolor(dots.to_rgba(row["Price"]))
        bigDot.set_sizes([DOT_SIZE])

        hover["endX"] = row["Longitude"]
        hover["endY"] = row["Latitude"]
        if box.get_visible():
            # slide from wherever the box is right now
            hover["startX"], hover["startY"] = box.xy
        else:
            # the first time, fade in right above the meter
            hover["startX"] = row["Longitude"]
            hover["startY"] = row["Latitude"]
            hover["fading"] = True
            setBoxAlpha(0)
            box.set_visible(True)
        hover["progress"] = 0
        timer.start()

    timer.add_callback(moveHover)
    canvas.mpl_connect("draw_event", onDraw)
    canvas.mpl_connect("motion_notify_event", onMove)

    fullWest, fullEast = ax.get_xlim()
    fullSouth, fullNorth = ax.get_ylim()

    # Function: zoomSide
    # Purpose: figures out the new edges of one side of the map (left/right or bottom/top) after a zoom
    # Parameters: 5, the current low and high edges, the mouse position, the zoom amount, and the full low and high edges
    # Side Effects: none
    # Returns: the new low and high edges
    def zoomSide(low, high, mouse, scale, fullLow, fullHigh):
        newLow = mouse - (mouse - low) * scale
        newHigh = mouse + (high - mouse) * scale

        if newHigh - newLow >= fullHigh - fullLow:
            return fullLow, fullHigh
        if newLow < fullLow:
            newHigh = newHigh + (fullLow - newLow)
            newLow = fullLow
        if newHigh > fullHigh:
            newLow = newLow - (newHigh - fullHigh)
            newHigh = fullHigh
        return newLow, newHigh

    # Function: onScroll
    # Purpose: zooms the map in or out around the mouse when you scroll
    # Parameters: 1, the scroll event
    # Side Effects: changes the area the map is showing
    # Returns: none
    def onScroll(event):
        if event.inaxes != ax:
            return

        step = max(-MAX_SCROLL, min(MAX_SCROLL, event.step))
        scale = ZOOM_SPEED ** step

        west, east = ax.get_xlim()
        south, north = ax.get_ylim()
        ax.set_xlim(zoomSide(west, east, event.xdata, scale, fullWest, fullEast))
        ax.set_ylim(zoomSide(south, north, event.ydata, scale, fullSouth, fullNorth))
        event.canvas.draw_idle()

    ax.figure.canvas.mpl_connect("scroll_event", onScroll)

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
    plt.show()

main()