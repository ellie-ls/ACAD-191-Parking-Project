'''
Ellie Lin-Stevens & Nina Zhang
ACAD 191, Fall 2026
elinstev@usc.edu & nzhang21@usc.edu
Exercise 6
'''

import os
import json
import re
import json
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
    plt.title("Parking Meters by Price (Downtown LA)")
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
#               lets you zoom by scrolling the trackpad or mouse wheel,
#               and lets you move the map by dragging
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
    figure = ax.figure
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

    # Function: onHover
    # Purpose: finds the meter under the mouse and sends the hover box and the big dot to it
    # Parameters: 1, the mouse move event
    # Side Effects: changes the hover text and starts the timer that moves the box
    # Returns: none
    def onHover(event):
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
    canvas.mpl_connect("motion_notify_event", onHover)

    fullWest, fullEast = ax.get_xlim()
    fullSouth, fullNorth = ax.get_ylim()

    # Function: zoomSide
    # Purpose: figures out the new edges of one side of the map (left/right or bottom/top) after a zoom
    # Parameters: 6, the current low and high edges, the mouse position, the zoom amount, and the full low and high edges
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
    # Purpose: zooms the map in or out around the mouse when you scroll (two fingers on the trackpad)
    # Parameters: 1, the scroll event
    # Side Effects: changes the area the map is showing
    # Returns: none
    def onScroll(event):
        if event.inaxes != ax:
            return

        # step can be a small fraction on a trackpad, so the zoom is smooth
        step = max(-MAX_SCROLL, min(MAX_SCROLL, event.step))
        scale = ZOOM_SPEED ** step

        west, east = ax.get_xlim()
        south, north = ax.get_ylim()
        ax.set_xlim(zoomSide(west, east, event.xdata, scale, fullWest, fullEast))
        ax.set_ylim(zoomSide(south, north, event.ydata, scale, fullSouth, fullNorth))
        figure.canvas.draw_idle()

    # remembers where a drag started (in screen pixels) and what the map showed then
    drag = {"start": None}

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

    # Function: onDrag
    # Purpose: moves the map along with the mouse while you drag
    # Parameters: 1, the mouse event
    # Side Effects: changes the area the map shows
    # Returns: none
    def onDrag(event):
        if drag["start"] is None:
            return
        startX, startY, (left, right), (bottom, top) = drag["start"]
        # turns how far the mouse moved (in pixels) into how far to move the map
        moveX = (event.x - startX) * (right - left) / ax.bbox.width
        moveY = (event.y - startY) * (top - bottom) / ax.bbox.height
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

    canvas.mpl_connect("scroll_event", onScroll)
    canvas.mpl_connect("button_press_event", onPress)
    canvas.mpl_connect("motion_notify_event", onDrag)
    canvas.mpl_connect("button_release_event", onRelease)

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

# Class: VectorStreetMap
# Purpose: adds a "vector" street map behind the dots. Instead of downloading pictures of the map
#          (which get pixelated up close), the browser gets the street data and draws it itself,
#          so roads stay sharp and street names stay the same size at every zoom.
#          Map from OpenFreeMap (free, no key needed), drawn with MapLibre.
class VectorStreetMap(JSCSSMixin, MacroElement):
    # the JavaScript code that runs on the web page
    _template = Template("""
        {% macro script(this, kwargs) %}
            L.maplibreGL({
                style: "https://tiles.openfreemap.org/styles/positron",
                attribution: '<a href="https://openfreemap.org">OpenFreeMap</a> &copy; <a href="https://www.openmaptiles.org/">OpenMapTiles</a> Data from <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
            }).addTo({{ this._parent.get_name() }});
            {{ this._parent.get_name() }}.setMaxZoom(20);
        {% endmacro %}
    """)

    # the libraries the web page needs to load
    default_js = [
        ("maplibre", "https://unpkg.com/maplibre-gl@5.24.0/dist/maplibre-gl.js"),
        ("maplibre_leaflet", "https://unpkg.com/@maplibre/maplibre-gl-leaflet@0.1.4/leaflet-maplibre-gl.js")
    ]
    default_css = [
        ("maplibre_css", "https://unpkg.com/maplibre-gl@5.24.0/dist/maplibre-gl.css")
    ]

# Class: RegionOutlines
# Purpose: draws a dashed outline and a name label for Koreatown, Downtown, and South LA.
#          Each region only shows up once you have zoomed out far enough to see all of it.
#          Outlines are from the LA Times "Mapping L.A." project (saved in regions.geojson).
class RegionOutlines(MacroElement):
    # the style for the region names (goes in the <head> of the web page)
    # and the JavaScript code that runs on the web page
    _template = Template("""
        {% macro header(this, kwargs) %}
            <style>
                .region-label {
                    background: none;
                    border: none;
                    box-shadow: none;
                    color: #1e293b;
                    font-size: 15px;
                    font-weight: 700;
                    letter-spacing: 0.04em;
                    text-transform: uppercase;
                    text-shadow: 0 0 3px #fff, 0 0 3px #fff, 0 0 3px #fff;
                }
                .region-label::before {
                    display: none;
                }
            </style>
        {% endmacro %}

        {% macro script(this, kwargs) %}
            (function() {
                var map = {{ this._parent.get_name() }};

                // a layer under the dots, so the outlines never cover a meter
                map.createPane("regions");
                map.getPane("regions").style.zIndex = 350;
                var renderer = L.svg({ pane: "regions" });

                var regionData = {{ this.regions|tojson }};
                var regions = [];
                regionData.features.forEach(function(feature) {
                    var outline = L.geoJSON(feature, {
                        pane: "regions",
                        renderer: renderer,
                        interactive: false,
                        style: { color: "#334155", weight: 2, dashArray: "6 4", fill: false }
                    });
                    var label = L.tooltip({ permanent: true, direction: "center", className: "region-label" })
                        .setLatLng(outline.getBounds().getCenter())
                        .setContent(feature.properties.name);
                    regions.push({ bounds: outline.getBounds(), group: L.layerGroup([outline, label]) });
                });

                // shows a region only when the whole thing fits on the screen
                function updateRegions() {
                    var screen = map.getBounds();
                    regions.forEach(function(region) {
                        if (screen.contains(region.bounds)) {
                            region.group.addTo(map);
                        } else {
                            region.group.remove();
                        }
                    });
                }
                map.on("moveend", updateRegions);
                updateRegions();
            })();
        {% endmacro %}
    """)

    # Function: __init__
    # Purpose: saves the region outlines so the template can put them in the web page
    # Parameters: 1, the regions (GeoJSON, as a dictionary)
    # Side Effects: none
    # Returns: none
    def __init__(self, regions):
        super().__init__()
        self.regions = regions

# Class: OpenChance
# Purpose: adds "Usually open X% of the time" to each meter's hover box, using the numbers
#          from occupancy.json (made by build_occupancy.py). A box in the corner lets you pick
#          the day and hour; it starts on "Right now" (LA time).
class OpenChance(MacroElement):
    # the style for the picker and hover text, and the JavaScript code that runs on the web page
    _template = Template("""
        {% macro header(this, kwargs) %}
            <style>
                .open-chance-picker {
                    background: #fff;
                    border-radius: 6px;
                    box-shadow: 0 1px 4px rgba(0, 0, 0, 0.3);
                    font: 13px/1.4 system-ui, sans-serif;
                    padding: 8px 10px;
                }
                .open-chance-picker label {
                    display: block;
                    font-weight: 600;
                    margin-bottom: 4px;
                }
                .open-chance-picker select {
                    font: inherit;
                    margin-right: 4px;
                }
                .open-chance-picker .note {
                    color: #64748b;
                    font-size: 11px;
                    margin-top: 4px;
                }
                .open-chance-note {
                    color: #64748b;
                    font-size: 11px;
                }
            </style>
        {% endmacro %}

        {% macro script(this, kwargs) %}
            (function() {
                var map = {{ this._parent.get_name() }};
                var occupancy = {{ this.meters|tojson }};
                var DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"];

                // "2 PM" style hour names
                function hourName(hour) {
                    var h = hour % 24;
                    return (h % 12 === 0 ? 12 : h % 12) + (h < 12 ? " AM" : " PM");
                }

                // the day/hour picker in the top right corner
                var picker = L.control({ position: "topright" });
                picker.onAdd = function() {
                    var box = L.DomUtil.create("div", "open-chance-picker");
                    var days = '<option value="now">Right now</option>';
                    DAYS.forEach(function(day, i) { days += '<option value="' + i + '">' + day + '</option>'; });
                    var hours = "";
                    for (var h = 0; h < 24; h++) {
                        hours += '<option value="' + h + '"' + (h === 12 ? " selected" : "") + '>' + hourName(h) + '</option>';
                    }
                    box.innerHTML = '<label>Chance a spot is open</label>' +
                        '<select class="day">' + days + '</select>' +
                        '<select class="hour" disabled>' + hours + '</select>' +
                        '<div class="note">From parking sensors, {{ this.dates }}</div>';
                    // so using the picker doesn't drag or zoom the map
                    L.DomEvent.disableClickPropagation(box);
                    L.DomEvent.disableScrollPropagation(box);
                    box.querySelector(".day").addEventListener("change", function() {
                        box.querySelector(".hour").disabled = (this.value === "now");
                    });
                    picker.box = box;
                    return box;
                };
                picker.addTo(map);

                // the day (0 = Monday) and hour chosen in the picker, or the current time in LA
                function chosenTime() {
                    var day = picker.box.querySelector(".day").value;
                    if (day !== "now") {
                        return { day: Number(day), hour: Number(picker.box.querySelector(".hour").value) };
                    }
                    var parts = new Intl.DateTimeFormat("en-US", {
                        timeZone: "America/Los_Angeles", weekday: "short", hour: "numeric", hourCycle: "h23"
                    }).formatToParts(new Date());
                    var weekday = parts.find(function(p) { return p.type === "weekday"; }).value;
                    var hour = Number(parts.find(function(p) { return p.type === "hour"; }).value);
                    return { day: ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"].indexOf(weekday), hour: hour };
                }

                // the line added to the hover box for one meter
                function describe(spaceId) {
                    var meter = occupancy[spaceId];
                    if (!meter) {
                        return '<span class="open-chance-note">No sensor data nearby</span>';
                    }
                    var time = chosenTime();
                    var when = DAYS[time.day] + " " + hourName(time.hour) + "–" + hourName(time.hour + 1);
                    var percent = meter.open[time.day * 24 + time.hour];
                    if (percent === null) {
                        return '<span class="open-chance-note">Not enough data for ' + when + '</span>';
                    }
                    var how = "measured over " + meter.weeks + " weeks";
                    if (meter.source === "nearby") {
                        how = "based on nearby spots";
                    } else if (meter.source === "nearby-less-certain") {
                        how = "based on nearby spots, less certain";
                    }
                    return '<b>Usually open ' + percent + '% of the time</b><br>' +
                        '<span class="open-chance-note">' + when + ' · ' + how + '</span>';
                }

                // fills in the open chance every time a hover box opens, so it matches the picker
                map.on("tooltipopen", function(e) {
                    var tooltip = e.tooltip;
                    if (tooltip.originalText === undefined) {
                        tooltip.originalText = tooltip.getContent();
                    }
                    var text = tooltip.originalText;
                    var match = typeof text === "string" && text.match(/<span data-open=([^> ]+)><.span>/);
                    if (match) {
                        tooltip.setContent(text.replace(match[0], describe(match[1])));
                    }
                });
            })();
        {% endmacro %}
    """)

    # Function: __init__
    # Purpose: saves the open chances so the template can put them in the web page
    # Parameters: 2, the open chances for each meter on the map, and the months the data covers
    # Side Effects: none
    # Returns: none
    def __init__(self, meters, dates):
        super().__init__()
        self.meters = meters
        self.dates = dates

# Function: loadOccupancy
# Purpose: loads occupancy.json (the open chances made by build_occupancy.py)
# Parameters: none
# Side Effects: prints a message if the file is missing
# Returns: the occupancy data, or None
def loadOccupancy():
    occupancyFile = os.path.join(os.path.dirname(os.path.abspath(__file__)), "occupancy.json")
    try:
        with open(occupancyFile) as file:
            return json.load(file)
    except FileNotFoundError:
        print("occupancy.json not found, so the map will not show open chances (run build_occupancy.py)")
        return None

# Function: monthName
# Purpose: turns "2023_09" into "Sep 2023"
# Parameters: 1, the month text
# Side Effects: none
# Returns: the month name
def monthName(month):
    return pd.Timestamp(month.replace("_", "-") + "-01").strftime("%b %Y")

# Function: graphWebMap
# Purpose: makes a web map of the meters you can pinch to zoom and drag around in the browser,
#          with the chance each spot is open in the hover box
#          (the street map is drawn by the browser, so it stays sharp and the street names stay
#          the same size at every zoom, like Apple Maps)
# Parameters: 1, the data
# Side Effects: saves the map as an html file and opens it in the web browser
# Returns: none
def graphWebMap(data):
    # starts centered on the middle of the area
    center = [(SOUTH + NORTH) / 2, (WEST + EAST) / 2]
    webMap = folium.Map(
        location=center,
        zoom_start=14,
        # the street map is added below instead
        tiles=None,
        # makes thousands of dots draw much faster
        prefer_canvas=True
    )

    # light gray street map that the browser draws itself, so it stays sharp at every zoom
    VectorStreetMap().add_to(webMap)

    # outlines and names for Koreatown, Downtown, and South LA (only shown when zoomed out)
    regionFile = os.path.join(os.path.dirname(os.path.abspath(__file__)), "regions.geojson")
    try:
        with open(regionFile) as file:
            RegionOutlines(json.load(file)).add_to(webMap)
    except FileNotFoundError:
        print("regions.geojson not found, so the map will not show region outlines")

    # "Usually open X% of the time" in the hover boxes
    occupancy = loadOccupancy()
    if occupancy is not None:
        spaceIds = data["SpaceID"].str.strip()
        onMap = {}
        for spaceId in spaceIds:
            if spaceId in occupancy["meters"]:
                onMap[spaceId] = occupancy["meters"][spaceId]
        dates = monthName(occupancy["from"]) + " \u2013 " + monthName(occupancy["to"])
        OpenChance(onMap, dates).add_to(webMap)

    for index, row in data.iterrows():
        color = getColor(row["Price"])
        # the empty span gets filled in with the open chance when you hover
        openChance = ""
        if occupancy is not None:
            openChance = "<br><span data-open=" + row["SpaceID"].strip() + "></span>"
        folium.CircleMarker(
            location=[row["Latitude"], row["Longitude"]],
            radius=4,
            color=color,
            fill=True,
            fill_color=color,
            fill_opacity=0.9,
            weight=1,
            # shows the street and price when you hover over a dot
            tooltip=row["BlockFace"] + "<br>" + row["RateRange"] + openChance
        ).add_to(webMap)

    # color key in the corner
    legend = branca.colormap.LinearColormap(
        [getColor(LOW_PRICE), getColor((LOW_PRICE + HIGH_PRICE) / 2), getColor(HIGH_PRICE)],
        vmin=LOW_PRICE,
        vmax=HIGH_PRICE,
        caption="Highest hourly price ($)"
    )
    legend.add_to(webMap)

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

# only runs main() when you run this file
# (so build_occupancy.py can use loadFile and cleanData without asking for a file name)
if __name__ == "__main__":
    main()
