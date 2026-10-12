'''
Ellie Lin-Stevens & Nina Zhang
ACAD 191, Fall 2026
elinstev@usc.edu & nzhang21@usc.edu
Exercise 6
'''

import os
import json
import re
import webbrowser
import pandas as pd
import matplotlib
import matplotlib.pyplot as plt
import matplotlib.patheffects as patheffects
from matplotlib.path import Path
import contextily
import folium
import branca.element

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

# web map: search circle size (meters), price slider step, and dot size at each zoom level
SEARCH_RADIUS = 500
PRICE_STEP = 0.05
WEB_DOT_SIZES = [[0, 1], [14, 1.5], [15, 2.5], [16, 4], [17, 6]]
WEB_HOVER_DOT_SIZE = 11
# how close the map zooms when you click a dot
WEB_CLICK_ZOOM = 17
# smaller area circle (meters) around a clicked dot
WEB_CLICK_RADIUS = 200
# plain words for the city's rate types
RATE_TYPES = {"FLAT": "Flat rate", "TOD": "Changes by time of day", "JUMP": "Jump rate"}
# how long the web map animations take (milliseconds)
WEB_FADE_TIME = 220
WEB_GROW_TIME = 160
# how long the map takes to glide to a searched place or clicked dot (seconds)
WEB_ZOOM_TIME = 0.45

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
    ax.set_title("LA Parking Meter Prices per Hour (scroll to zoom, drag to move)")

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

    figure = ax.figure
    # remembers where a drag started (in screen pixels) and what the map showed then
    drag = {"start": None}

    # Function: onScroll
    # Purpose: zooms in or out around the mouse when you scroll (two fingers on the trackpad)
    # Parameters: 1, the scroll event
    # Side Effects: changes the area the map shows
    # Returns: none
    def onScroll(event):
        if event.inaxes != ax:
            return
        # scrolling up zooms in, scrolling down zooms out
        # (step can be a small fraction on a trackpad, so the zoom is smooth)
        factor = 0.9 ** event.step
        left, right = ax.get_xlim()
        bottom, top = ax.get_ylim()
        # keeps the spot under the mouse in the same place while zooming
        ax.set_xlim(event.xdata - (event.xdata - left) * factor, event.xdata + (right - event.xdata) * factor)
        ax.set_ylim(event.ydata - (event.ydata - bottom) * factor, event.ydata + (top - event.ydata) * factor)
        figure.canvas.draw_idle()

    # Function: onPress
    # Purpose: starts dragging the map when you click on it
    # Parameters: 1, the mouse event
    # Side Effects: saves where the drag started
    # Returns: none
    def onPress(event):
        # skips if you are using the toolbar's zoom or move button
        toolbar = figure.canvas.toolbar
        if event.inaxes != ax or event.button != 1 or (toolbar is not None and toolbar.mode != ""):
            return
        drag["start"] = (event.x, event.y, ax.get_xlim(), ax.get_ylim())

    # Function: onMove
    # Purpose: moves the map along with the mouse while you drag
    # Parameters: 1, the mouse event
    # Side Effects: changes the area the map shows
    # Returns: none
    def onMove(event):
        if drag["start"] is None:
            return
        startX, startY, (left, right), (bottom, top) = drag["start"]
        # turns how far the mouse moved (in pixels) into how far to move the map
        box = ax.bbox
        moveX = (event.x - startX) * (right - left) / box.width
        moveY = (event.y - startY) * (top - bottom) / box.height
        ax.set_xlim(left - moveX, right - moveX)
        ax.set_ylim(bottom - moveY, top - moveY)
        figure.canvas.draw_idle()

    # Function: onRelease
    # Purpose: stops dragging when you let go of the mouse
    # Parameters: 1, the mouse event
    # Side Effects: clears the saved drag
    # Returns: none
    def onRelease(event):
        drag["start"] = None

    figure.canvas.mpl_connect("scroll_event", onScroll)
    figure.canvas.mpl_connect("button_press_event", onPress)
    figure.canvas.mpl_connect("motion_notify_event", onMove)
    figure.canvas.mpl_connect("button_release_event", onRelease)

# Function: getColor
# Purpose: picks a color for a price, green (cheap) to red (expensive), same as the python map
# Parameters: 1, the price
# Side Effects: none
# Returns: the color as a hex string like "#1a9850"
def getColor(price):
    # turns the price into a number from 0 to 1 (0 = LOW_PRICE, 1 = HIGH_PRICE)
    amount = (price - LOW_PRICE) / (HIGH_PRICE - LOW_PRICE)
    amount = min(max(amount, 0), 1)
    return matplotlib.colors.to_hex(plt.get_cmap("RdYlGn_r")(amount))

# Function: getTimeLimit
# Purpose: turns a time limit like "2HR" or "2HR-30MIN" into words like "2 hours 30 minutes"
# Parameters: 1, the time limit text
# Side Effects: none
# Returns: the time limit in words, or "" if it is missing
def getTimeLimit(limitText):
    if pd.isna(limitText):
        return ""
    words = []
    for amount, unit in re.findall(r"(\d+)\s*(HR|MIN)", str(limitText).upper()):
        name = "hour" if unit == "HR" else "minute"
        words.append(amount + " " + name + ("" if amount == "1" else "s"))
    return " ".join(words) if words else str(limitText)

# Function: addMapTools
# Purpose: adds the search box, price slider, zoom buttons, and dot hover/click effects to the web map
#          (styled after the team's Figma board; the dots are drawn in javascript so the
#          slider can hide and show them)
# Parameters: 2, the web map and the data
# Side Effects: adds style and script code to the web map
# Returns: none
def addMapTools(webMap, data):
    # one list per meter: latitude, longitude, price, color, street, rate, time limit, rate type
    spots = []
    for index, row in data.iterrows():
        spots.append([
            round(row["Latitude"], 6),
            round(row["Longitude"], 6),
            row["Price"],
            getColor(row["Price"]),
            row["BlockFace"],
            row["RateRange"],
            getTimeLimit(row["MeteredTimeLimit"]),
            RATE_TYPES.get(row["RateType"], "")
        ])

    style = """
    <link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Hubballi&display=swap">
    <style>
    .parking-panel { background: rgba(31, 31, 31, 0.85); color: white; border-radius: 10px;
        font-family: Hubballi, "Trebuchet MS", sans-serif; box-shadow: 0 2px 8px rgba(0,0,0,0.35); }
    .parking-panel { width: 300px; max-width: calc(100vw - 40px); padding: 14px 16px; font-size: 16px; }
    .parking-search { position: relative; display: flex; gap: 6px; }
    .parking-place { flex: 1; min-width: 0; padding: 7px 10px; border: 0; border-radius: 8px; font: inherit; font-size: 16px; }
    .parking-go { padding: 0 12px; border: 0; border-radius: 8px; background: #c7cdb2; color: #1f1f1f; font: inherit; cursor: pointer; }
    .parking-suggestions { position: absolute; top: 100%; left: 0; right: 0; z-index: 2; margin: 4px 0 0; padding: 0;
        list-style: none; background: white; color: #222; border-radius: 8px; overflow: hidden; box-shadow: 0 2px 8px rgba(0,0,0,0.35); }
    .parking-suggestions li { padding: 6px 10px; cursor: pointer; line-height: 1.2; }
    .parking-suggestions li small { display: block; color: #777; }
    .parking-suggestions li:hover, .parking-suggestions li.active { background: #eef1e4; }
    .parking-message { margin-top: 8px; font-size: 14px; line-height: 1.3; color: #ddd; }
    .parking-label { margin-top: 12px; font-size: 20px; }
    .parking-hint { font-size: 13px; color: #bbb; }
    .parking-slider { -webkit-appearance: none; appearance: none; width: 100%; height: 7px; margin: 12px 0 6px;
        border-radius: 10px; outline: none; cursor: pointer;
        background: linear-gradient(to right, rgba(0,104,54,0.8), rgba(239,248,169,0.8) 48.077%, rgba(172,10,41,0.8)); }
    .parking-slider::-webkit-slider-thumb { -webkit-appearance: none; width: 20px; height: 20px; border-radius: 50%; background: white; border: 0;
        box-shadow: 0 1px 3px rgba(0,0,0,0.4); transition: transform 0.15s ease-out; }
    .parking-slider::-moz-range-thumb { width: 20px; height: 20px; border-radius: 50%; background: white; border: 0;
        box-shadow: 0 1px 3px rgba(0,0,0,0.4); transition: transform 0.15s ease-out; }
    .parking-slider:hover::-webkit-slider-thumb { transform: scale(1.15); }
    .parking-slider:active::-webkit-slider-thumb { transform: scale(1.3); }
    .parking-slider:hover::-moz-range-thumb { transform: scale(1.15); }
    .parking-slider:active::-moz-range-thumb { transform: scale(1.3); }
    .parking-price { font-variant-numeric: tabular-nums; }
    .parking-slider:focus-visible::-webkit-slider-thumb { box-shadow: 0 0 0 3px #c7cdb2; }
    .parking-list { margin: 6px 0 0; padding: 0; list-style: none; max-height: 180px; overflow-y: auto; font-size: 14px; }
    .parking-list li { padding: 4px 0; cursor: pointer; border-top: 1px solid rgba(255,255,255,0.15); line-height: 1.25; }
    .parking-list li:hover { color: #c7cdb2; }
    .parking-dot { display: inline-block; width: 9px; height: 9px; border-radius: 50%; margin-right: 6px; }
    .leaflet-container .leaflet-control-zoom.leaflet-bar.parking-zoom { border: 0; box-shadow: none; background: none; display: flex; flex-direction: column; gap: 10px; }
    .leaflet-container .leaflet-control-zoom.leaflet-bar.parking-zoom a { box-sizing: border-box; width: 44px; height: 44px; margin: 0;
        border: 0; border-radius: 10px; background: rgba(2,2,2,0.7);
        color: white; font: 40px/44px Hubballi, sans-serif; text-indent: 0; }
    .leaflet-container .leaflet-control-zoom.leaflet-bar.parking-zoom a:hover { background: rgba(2,2,2,0.85); }
    .leaflet-container .leaflet-control-zoom.leaflet-bar.parking-zoom a.leaflet-disabled { opacity: 0.4; }
    .leaflet-tooltip.parking-tag { padding: 10px 20px 8px; border: 0; border-radius: 16px; background: white; color: black;
        box-shadow: 0 4px 4px rgba(0,0,0,0.25); text-align: center; font-family: Hubballi, "Trebuchet MS", sans-serif; white-space: nowrap; }
    .leaflet-tooltip.parking-tag strong { display: block; font-size: 22px; font-weight: normal; line-height: 1.1; }
    .leaflet-tooltip.parking-tag span { display: block; font-size: 15px; line-height: 1.3; }
    .parking-info { position: relative; width: 280px; max-width: calc(100vw - 40px); padding: 14px 18px 12px;
        background: rgba(31, 31, 31, 0.85); color: white; border-radius: 10px; box-shadow: 0 2px 8px rgba(0,0,0,0.35);
        font-family: Hubballi, "Trebuchet MS", sans-serif; }
    .parking-info[hidden] { display: none; }
    .parking-info-in { animation: parking-info-in 0.22s ease-out; }
    @keyframes parking-info-in { from { opacity: 0; transform: translateX(12px); } to { opacity: 1; transform: none; } }
    .parking-info-title { padding-right: 24px; font-size: 24px; line-height: 1.1; }
    .parking-info dl { display: grid; grid-template-columns: auto 1fr; gap: 6px 14px; margin: 12px 0 0; font-size: 15px; }
    .parking-info dt { color: #bbb; }
    .parking-info dd { margin: 0; text-align: right; }
    .parking-info-close { position: absolute; top: 8px; right: 10px; width: 28px; height: 28px; padding: 0; border: 0;
        border-radius: 50%; background: none; color: #ddd; font-size: 24px; line-height: 28px; cursor: pointer; }
    .parking-info-close:hover { background: rgba(255,255,255,0.15); color: white; }
    .leaflet-tooltip.parking-tag { animation: parking-tag-in 0.18s ease-out; }
    .leaflet-tooltip.parking-tag .parking-tag-body { animation: parking-tag-rise 0.18s ease-out; }
    @keyframes parking-tag-in { from { opacity: 0; } to { opacity: 1; } }
    @keyframes parking-tag-rise { from { transform: translateY(6px); } to { transform: none; } }
    @media (prefers-reduced-motion: reduce) {
        .leaflet-tooltip.parking-tag, .leaflet-tooltip.parking-tag .parking-tag-body, .parking-info-in { animation: none; }
    }
    .leaflet-tooltip-top.parking-tag::before { margin-left: -12px; border-width: 12px 12px 0; border-top-color: white; }
    </style>
    """
    webMap.get_root().header.add_child(folium.Element(style))

    script = """
    var map = __MAP_NAME__;
    var spots = __SPOTS__;
    var lowestPrice = __LOWEST__, highestPrice = __HIGHEST__, priceStep = __PRICE_STEP__;
    var searchRadius = __SEARCH_RADIUS__;
    var dataBounds = [__SOUTH__, __WEST__, __NORTH__, __EAST__];
    var dotSizes = __DOT_SIZES__;
    var hoverDotSize = __HOVER_DOT_SIZE__;
    var clickZoom = __CLICK_ZOOM__;
    var clickRadius = __CLICK_RADIUS__;
    // animations are skipped for people who turn off motion on their computer
    var calm = window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    var fadeTime = calm ? 0 : __FADE_TIME__;
    var growTime = calm ? 0 : __GROW_TIME__;
    var zoomTime = __ZOOM_TIME__;
    var area = { center: null, name: "", layer: L.layerGroup().addTo(map) };

    // zoom buttons (Figma "Zoom in" frame) in the bottom right corner
    map.zoomControl.setPosition("bottomright");
    L.DomUtil.addClass(map.zoomControl.getContainer(), "parking-zoom");

    // dot size for the current zoom (smaller when zoomed out, and in between while the map is zooming)
    function getDotSize() {
        var zoom = map.getZoom();
        var size = dotSizes[0][1];
        dotSizes.forEach(function (pair, index) {
            var next = dotSizes[index + 1];
            if (zoom >= pair[0]) {
                size = next && zoom < next[0] ? pair[1] + (next[1] - pair[1]) * (zoom - pair[0]) / (next[0] - pair[0]) : pair[1];
            }
        });
        return size;
    }

    // makes one dot per meter
    var dots = L.layerGroup().addTo(map);
    function escapeText(text) {
        var holder = document.createElement("div");
        holder.textContent = text;
        return holder.innerHTML;
    }

    var markers = spots.map(function (spot) {
        var marker = L.circleMarker([spot[0], spot[1]], {
            radius: getDotSize(), color: spot[3], fillColor: spot[3], fillOpacity: 0.9, weight: 1
        });
        // street tag (Figma "Hover example" frame) floats above the dot
        marker.bindTooltip('<div class="parking-tag-body"><strong>' + escapeText(spot[4]) + "</strong><span>" +
            escapeText(spot[5]) + "</span></div>", {
            className: "parking-tag", direction: "top", offset: [0, -(hoverDotSize + 18)]
        });
        marker.spot = spot;

        marker.shown = true;
        marker.alpha = 1;

        // hovering grows the dot smoothly
        marker.on("mouseover", function () {
            marker.hovered = true;
            marker.bringToFront();
            growDot(marker, hoverDotSize);
        });
        marker.on("mouseout", function () {
            marker.hovered = false;
            growDot(marker, getDotSize());
        });

        // clicking zooms in close to the dot, like searching its street, and shows its details
        marker.on("click", function () {
            input.value = spot[4];
            suggestions.hidden = true;
            showArea(spot[0], spot[1], spot[4], clickZoom);
            openTag(marker);
            showInfo(marker);
        });

        dots.addLayer(marker);
        return marker;
    });

    // draws a dot with its current size and fade
    function styleDot(marker) {
        var full = marker.hovered ? 1 : 0.9;
        marker.setStyle({
            weight: marker.hovered || marker.getRadius() < 3 ? 0 : 1,
            opacity: marker.alpha,
            fillOpacity: full * marker.alpha
        });
    }

    // eases a dot's size toward a new size
    function growDot(marker, size) {
        cancelAnimationFrame(marker.growFrame);
        var start = marker.getRadius();
        var startTime = performance.now();
        function step(now) {
            var amount = growTime ? Math.min(1, (now - startTime) / growTime) : 1;
            amount = 1 - Math.pow(1 - amount, 3);
            marker.setRadius(start + (size - start) * amount);
            styleDot(marker);
            if (amount < 1) { marker.growFrame = requestAnimationFrame(step); }
        }
        marker.growFrame = requestAnimationFrame(step);
    }

    map.on("zoomend", function () {
        var size = getDotSize();
        markers.forEach(function (marker) {
            if (!marker.hovered) { marker.setRadius(size); styleDot(marker); }
        });
    });

    // while the map glides to a new zoom, the dots are redrawn every frame at their real size
    // (otherwise the browser stretches the old picture of the dots, which makes them big and blurry)
    function redrawWhileZooming() {
        var renderer = markers.length ? markers[0]._renderer : null;
        if (!renderer || map._animatingZoom) { return; }
        var size = getDotSize();
        markers.forEach(function (marker) {
            if (!marker.hovered) { marker._radius = marker.options.radius = size; }
        });
        for (var id in renderer._layers) { renderer._layers[id]._project(); }
        renderer._update();
    }
    map.on("zoom", redrawWhileZooming);

    // the + and - buttons glide too, so they get the same sharp dots
    map.zoomIn = function (delta) {
        return map.flyTo(map.getCenter(), Math.min(map.getMaxZoom(), map.getZoom() + (delta || 1)), { duration: calm ? 0 : 0.3 });
    };
    map.zoomOut = function (delta) {
        return map.flyTo(map.getCenter(), Math.max(map.getMinZoom(), map.getZoom() - (delta || 1)), { duration: calm ? 0 : 0.3 });
    };

    // fades dots in and out when the price changes (one animation for all of them)
    var fading = new Set();
    var lastFrame = null;
    function fadeStep(now) {
        var amount = lastFrame === null || !fadeTime ? (fadeTime ? 0 : 1) : (now - lastFrame) / fadeTime;
        lastFrame = now;
        fading.forEach(function (marker) {
            var target = marker.shown ? 1 : 0;
            var change = Math.min(Math.abs(target - marker.alpha), amount);
            marker.alpha += target > marker.alpha ? change : -change;
            styleDot(marker);
            if (marker.alpha == target) {
                fading.delete(marker);
                if (!marker.shown) { dots.removeLayer(marker); }
            }
        });
        if (fading.size) { requestAnimationFrame(fadeStep); } else { lastFrame = null; }
    }
    function showDot(marker, show) {
        if (marker.shown == show) { return; }
        marker.shown = show;
        if (show && !dots.hasLayer(marker)) { dots.addLayer(marker); styleDot(marker); }
        if (!fading.size) { requestAnimationFrame(fadeStep); }
        fading.add(marker);
    }

    // search box and price slider (Figma "Price Filter" frame) in the top left corner
    var panel = L.control({ position: "topleft" });
    panel.onAdd = function () {
        var box = L.DomUtil.create("div", "parking-panel");
        box.innerHTML =
            '<form class="parking-search" autocomplete="off">' +
            '<input type="text" class="parking-place" placeholder="Search a place or address" aria-label="Search a place or address">' +
            '<button type="submit" class="parking-go">Go</button>' +
            '<ul class="parking-suggestions" hidden></ul></form>' +
            '<div class="parking-message">Type in a street name anywhere near DTLA, Koreatown, or USC.</div>' +
            '<div class="parking-label">Estimated price: <span class="parking-price"></span></div>' +
            '<input type="range" class="parking-slider" aria-label="Highest price you want to pay">' +
            '<div class="parking-hint">Showing meters at or below this hourly price</div>' +
            '<ul class="parking-list"></ul>';
        L.DomEvent.disableClickPropagation(box);
        L.DomEvent.disableScrollPropagation(box);
        return box;
    };
    panel.addTo(map);

    var box = panel.getContainer();
    var input = box.querySelector(".parking-place");
    var suggestions = box.querySelector(".parking-suggestions");
    var slider = box.querySelector(".parking-slider");
    var message = box.querySelector(".parking-message");
    var list = box.querySelector(".parking-list");
    slider.min = lowestPrice;
    slider.max = highestPrice;
    slider.step = priceStep;
    slider.value = highestPrice;

    // shows only the dots at or below the slider's price
    // (the slider can fire many times a frame while dragging, so the work waits for the next frame)
    var filterFrame = null;
    function applyFilter() {
        filterFrame = null;
        var price = Number(slider.value);
        box.querySelector(".parking-price").textContent = "$ " + price.toFixed(2);
        markers.forEach(function (marker) { showDot(marker, marker.spot[2] <= price); });
        listArea();
    }
    slider.addEventListener("input", function () {
        if (filterFrame === null) { filterFrame = requestAnimationFrame(applyFilter); }
    });

    // lists the blocks near the searched place, cheapest first
    function listArea() {
        list.innerHTML = "";
        if (!area.center) { return; }
        var nearby = [];
        var hidden = 0;
        markers.forEach(function (marker) {
            if (map.distance(area.center, marker.getLatLng()) <= area.radius) {
                if (marker.shown) { nearby.push(marker); } else { hidden += 1; }
            }
        });
        nearby.sort(function (a, b) { return a.spot[2] - b.spot[2]; });
        message.textContent = nearby.length + " meters within " + area.radius + " m of " + area.name +
            (nearby.length ? ", cheapest blocks first:" : ".") +
            (hidden ? " " + hidden + " more cost more than your price." : "");

        // one row per block (a block can have many meters with the same rate)
        var blocks = [];
        var blockIndex = {};
        nearby.forEach(function (marker) {
            var key = marker.spot[4] + "|" + marker.spot[5];
            if (!(key in blockIndex)) {
                blockIndex[key] = blocks.length;
                blocks.push({ marker: marker, count: 0 });
            }
            blocks[blockIndex[key]].count += 1;
        });
        blocks.forEach(function (block) {
            var marker = block.marker;
            var item = document.createElement("li");
            var dot = document.createElement("span");
            dot.className = "parking-dot";
            dot.style.background = marker.spot[3];
            item.appendChild(dot);
            item.appendChild(document.createTextNode(marker.spot[4] + ", " + marker.spot[5] +
                " (" + block.count + (block.count == 1 ? " meter)" : " meters)")));
            item.addEventListener("click", function () {
                var zoom = Math.max(map.getZoom(), 17);
                if (calm) { map.setView(marker.getLatLng(), zoom); } else { map.flyTo(marker.getLatLng(), zoom, { duration: zoomTime }); }
                openTag(marker);
                showInfo(marker);
            });
            list.appendChild(item);
        });
    }

    // zooms to the place and draws the search circle
    // (zoom is only given when a dot was clicked: the map then zooms in closer, centered on that dot)
    function showArea(lat, lng, name, zoom) {
        area.center = L.latLng(lat, lng);
        area.name = name;
        area.radius = zoom ? clickRadius : searchRadius;
        area.layer.clearLayers();
        if (!zoom) { closeTag(); hideInfo(); }
        // the circle and center point let clicks pass through to the dots under them
        L.circle(area.center, { radius: area.radius, color: "#2b6cb0", weight: 2, fillOpacity: 0.05, interactive: false })
            .addTo(area.layer);
        if (!zoom) {
            L.circleMarker(area.center, { radius: 7, color: "white", weight: 3, fillColor: "#2b6cb0", fillOpacity: 1, interactive: false })
                .addTo(area.layer);
        }
        if (zoom) {
            if (calm) { map.setView(area.center, zoom); } else { map.flyTo(area.center, zoom, { duration: zoomTime }); }
        } else {
            var bounds = area.center.toBounds(searchRadius * 2);
            if (calm) { map.fitBounds(bounds); } else { map.flyToBounds(bounds, { duration: zoomTime }); }
        }
        listArea();
    }

    // only one street tag stays open at a time
    var tagMarker = null;
    function closeTag() {
        if (tagMarker) { tagMarker.closeTooltip(); tagMarker = null; }
    }
    function openTag(marker) {
        if (tagMarker && tagMarker !== marker) { tagMarker.closeTooltip(); }
        tagMarker = marker;
        marker.openTooltip();
    }

    // street details box in the top right corner
    var info = L.control({ position: "topright" });
    info.onAdd = function () {
        var holder = L.DomUtil.create("div", "parking-info");
        holder.hidden = true;
        L.DomEvent.disableClickPropagation(holder);
        L.DomEvent.disableScrollPropagation(holder);
        return holder;
    };
    info.addTo(map);
    var infoBox = info.getContainer();

    function hideInfo() { infoBox.hidden = true; }
    function showInfo(marker) {
        var spot = marker.spot;
        var count = markers.filter(function (other) {
            return other.spot[4] == spot[4] && other.spot[5] == spot[5];
        }).length;
        var rows = [
            ["Price per hour", spot[5]],
            ["Metered time", spot[6] || "Not listed"],
            ["Rate type", spot[7] || "Not listed"],
            ["Meters on this block", String(count)]
        ];
        infoBox.innerHTML = "";
        var close = document.createElement("button");
        close.className = "parking-info-close";
        close.type = "button";
        close.setAttribute("aria-label", "Close street details");
        close.textContent = "\u00d7";
        close.addEventListener("click", function () { hideInfo(); closeTag(); });
        var title = document.createElement("div");
        title.className = "parking-info-title";
        var dot = document.createElement("span");
        dot.className = "parking-dot";
        dot.style.background = spot[3];
        title.appendChild(dot);
        title.appendChild(document.createTextNode(spot[4]));
        var table = document.createElement("dl");
        rows.forEach(function (row) {
            var term = document.createElement("dt");
            term.textContent = row[0];
            var value = document.createElement("dd");
            value.textContent = row[1];
            table.appendChild(term);
            table.appendChild(value);
        });
        infoBox.appendChild(close);
        infoBox.appendChild(title);
        infoBox.appendChild(table);
        infoBox.hidden = false;
        // restarts the pop-in animation
        infoBox.classList.remove("parking-info-in");
        void infoBox.offsetWidth;
        infoBox.classList.add("parking-info-in");
    }

    // matches street names in the data, so search still works without the internet
    function shortenStreet(text) {
        return text.toUpperCase().replace(/[.,]/g, " ")
            .replace(/\\bAVENUE\\b/g, "AVE").replace(/\\bSTREET\\b/g, "ST").replace(/\\bBOULEVARD\\b/g, "BLVD")
            .replace(/\\bDRIVE\\b/g, "DR").replace(/\\bPLACE\\b/g, "PL").replace(/\\s+/g, " ").trim();
    }
    function findStreets(text) {
        var words = shortenStreet(text);
        var number = parseInt(words, 10);
        var street = words.replace(/^\\d+\\s*/, "");
        if (street.length < 3) { return []; }
        var streets = {};
        markers.forEach(function (marker) {
            var name = marker.spot[4].replace(/^\\d+\\s*/, "");
            if (name.indexOf(street) < 0) { return; }
            var best = streets[name];
            var distance = isNaN(number) ? 0 : Math.abs(parseInt(marker.spot[4], 10) - number);
            if (!best || distance < best.distance) { streets[name] = { marker: marker, distance: distance }; }
        });
        return Object.keys(streets).slice(0, 3).map(function (name) {
            var spot = streets[name].marker.spot;
            return { name: isNaN(number) ? name : spot[4], detail: "Street in the parking data", lat: spot[0], lng: spot[1] };
        });
    }

    // place suggestions from Photon (OpenStreetMap search made for as-you-type map apps),
    // looking near the mapped area first
    function findPlaces(text) {
        var url = "https://photon.komoot.io/api/?limit=5&lang=en" +
            "&lat=" + ((dataBounds[0] + dataBounds[2]) / 2) + "&lon=" + ((dataBounds[1] + dataBounds[3]) / 2) +
            "&bbox=" + [dataBounds[1] - 0.05, dataBounds[0] - 0.05, dataBounds[3] + 0.05, dataBounds[2] + 0.05].join(",") +
            "&q=" + encodeURIComponent(text);
        return fetch(url)
            .then(function (response) { return response.json(); })
            .then(function (result) {
                return result.features.map(function (feature) {
                    var p = feature.properties;
                    var street = [p.housenumber, p.street].filter(Boolean).join(" ");
                    var name = p.name || street;
                    var detail = [p.name ? street : "", p.district || p.locality, p.city].filter(Boolean).join(", ");
                    return { name: name, detail: detail, lat: feature.geometry.coordinates[1], lng: feature.geometry.coordinates[0] };
                });
            })
            .catch(function () { return []; });
    }

    var choices = [];
    var activeChoice = -1;
    var typingTimer = null;
    var latestQuery = "";

    function showChoices(found) {
        choices = found;
        activeChoice = -1;
        suggestions.innerHTML = "";
        found.forEach(function (choice, index) {
            var item = document.createElement("li");
            item.appendChild(document.createTextNode(choice.name));
            if (choice.detail) {
                var detail = document.createElement("small");
                detail.textContent = choice.detail;
                item.appendChild(detail);
            }
            item.addEventListener("mousedown", function (event) { event.preventDefault(); pick(index); });
            suggestions.appendChild(item);
        });
        suggestions.hidden = found.length == 0;
    }

    function lookUp(text) {
        latestQuery = text;
        return findPlaces(text).then(function (places) {
            if (text != latestQuery) { return null; }
            return findStreets(text).concat(places);
        });
    }

    function pick(index) {
        var choice = choices[index];
        if (!choice) { return; }
        input.value = choice.name;
        suggestions.hidden = true;
        showArea(choice.lat, choice.lng, choice.name);
    }

    // suggestions update as you type
    input.addEventListener("input", function () {
        clearTimeout(typingTimer);
        var text = input.value.trim();
        if (text.length < 3) { showChoices([]); return; }
        typingTimer = setTimeout(function () {
            lookUp(text).then(function (found) { if (found) { showChoices(found); } });
        }, 250);
    });

    // arrow keys move through the suggestions, Escape closes them
    input.addEventListener("keydown", function (event) {
        var items = suggestions.querySelectorAll("li");
        if (event.key == "ArrowDown" || event.key == "ArrowUp") {
            if (!items.length) { return; }
            event.preventDefault();
            activeChoice = (activeChoice + (event.key == "ArrowDown" ? 1 : items.length - 1)) % items.length;
            items.forEach(function (item, index) { item.classList.toggle("active", index == activeChoice); });
        } else if (event.key == "Escape") {
            suggestions.hidden = true;
        }
    });
    input.addEventListener("blur", function () { suggestions.hidden = true; });

    // Go or Enter picks the highlighted suggestion, or the best match
    box.querySelector(".parking-search").addEventListener("submit", function (event) {
        event.preventDefault();
        var text = input.value.trim();
        if (!text) { return; }
        if (activeChoice >= 0 && !suggestions.hidden) { pick(activeChoice); return; }
        message.textContent = "Searching...";
        lookUp(text).then(function (found) {
            if (!found) { return; }
            if (found.length) { choices = found; pick(0); }
            else { message.textContent = "Couldn't find \\"" + text + "\\" near the mapped area."; }
        });
    });

    applyFilter();
    """
    replacements = {
        "__MAP_NAME__": webMap.get_name(),
        # the slider covers every price in the data (some meters cost more than the color key's top)
        "__LOWEST__": str(data["Price"].min()),
        "__HIGHEST__": str(data["Price"].max()),
        "__PRICE_STEP__": str(PRICE_STEP),
        "__SEARCH_RADIUS__": str(SEARCH_RADIUS),
        "__DOT_SIZES__": json.dumps(WEB_DOT_SIZES),
        "__HOVER_DOT_SIZE__": str(WEB_HOVER_DOT_SIZE),
        "__CLICK_ZOOM__": str(WEB_CLICK_ZOOM),
        "__CLICK_RADIUS__": str(WEB_CLICK_RADIUS),
        "__FADE_TIME__": str(WEB_FADE_TIME),
        "__GROW_TIME__": str(WEB_GROW_TIME),
        "__ZOOM_TIME__": str(WEB_ZOOM_TIME),
        "__WEST__": str(WEST),
        "__NORTH__": str(NORTH),
        "__EAST__": str(EAST),
        "__SOUTH__": str(SOUTH)
    }
    for key in replacements:
        script = script.replace(key, replacements[key])
    # the data goes in last, so street names can't be mistaken for a placeholder
    script = script.replace("__SPOTS__", json.dumps(spots))

    # a MacroElement's script runs after the map is made, so the code can use it
    tools = branca.element.MacroElement()
    tools._template = branca.element.Template("{% macro script(this, kwargs) %}" + script + "{% endmacro %}")
    webMap.add_child(tools)

# Function: graphWebMap
# Purpose: makes a web map of the meters you can pinch to zoom and drag around in the browser
#          (the street map loads new pictures at every zoom level, so it stays sharp up close)
# Parameters: 1, the data
# Side Effects: saves the map as an html file and opens it in the web browser
# Returns: none
def graphWebMap(data):
    # starts centered on the middle of the area
    center = [(SOUTH + NORTH) / 2, (WEST + EAST) / 2]
    webMap = folium.Map(
        location=center,
        zoom_start=14,
        # gray street map (best for seeing the colored dots)
        tiles="https://server.arcgisonline.com/ArcGIS/rest/services/Canvas/World_Light_Gray_Base/MapServer/tile/{z}/{y}/{x}",
        attr="Tiles &copy; Esri",
        # makes thousands of dots draw much faster
        prefer_canvas=True
    )

    # dots, search box, price slider, and zoom buttons
    addMapTools(webMap, data)

    # saves the map next to this file and opens it
    mapFile = os.path.join(os.path.dirname(os.path.abspath(__file__)), "parking_map.html")
    webMap.save(mapFile)
    webbrowser.open("file://" + mapFile)
    print("Web map opened in your browser:", mapFile)

# Function: main
# Purpose: runs loadFile, cleanData, graphWebMap, graphCounts, and graphMap
# Parameters: none
# Side Effects: prints to the console, asks for input, shows a chart and a map, opens a web map
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

    # the web map opens in the browser first, because plt.show() waits until the windows close
    graphWebMap(data)
    graphCounts(data)
    graphMap(data)
    plt.show()

main()