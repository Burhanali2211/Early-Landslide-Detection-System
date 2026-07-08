from flask import Flask, jsonify, render_template, request, Response
from rescue import rescue_bp
import numpy as np
import requests
import joblib
import os
import cv2
import threading
import time
import sensors

app = Flask(__name__)
app.register_blueprint(rescue_bp)

# -----------------------------
# 🔹 Load AI Model
# -----------------------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
model_path = os.path.join(BASE_DIR, "landslide_model.pkl")

model = joblib.load(model_path)
print("Model expects:", model.n_features_in_)

# -----------------------------
# 🔹 Camera & Sensor State
# -----------------------------
camera_alert_active = False
prev_camera_frame = None
tilt_threshold = 15.0  # Degrees
latest_jpeg_frame = None

# Background Video Capture
def camera_thread():
    global camera_alert_active, prev_camera_frame, latest_jpeg_frame
    cap = cv2.VideoCapture(0)
    
    # Try different backend if default fails on Pi (like V4L2)
    if not cap.isOpened():
        cap = cv2.VideoCapture(0, cv2.CAP_V4L2)
        
    # Optimize CPU: Reduce resolution to 320x240 for Raspberry Pi 4
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 320)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 240)
        
    while True:
        ret, frame = cap.read()
        if not ret:
            time.sleep(1)
            continue
            
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        gray = cv2.GaussianBlur(gray, (21, 21), 0)

        if prev_camera_frame is None or prev_camera_frame.shape != gray.shape:
            prev_camera_frame = gray
            continue

        frame_diff = cv2.absdiff(prev_camera_frame, gray)
        thresh = cv2.threshold(frame_diff, 25, 255, cv2.THRESH_BINARY)[1]
        thresh = cv2.dilate(thresh, None, iterations=2)
        
        contours, _ = cv2.findContours(thresh.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        motion_detected = False
        for contour in contours:
            if cv2.contourArea(contour) > 5000:
                motion_detected = True
                # Draw bounding box on frame
                (x, y, w, h) = cv2.boundingRect(contour)
                cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 0, 255), 2)
                
        camera_alert_active = motion_detected
        prev_camera_frame = gray
        
        # Add warning text
        if motion_detected:
            cv2.putText(frame, "MOTION DETECTED", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
            
        ret, jpeg = cv2.imencode('.jpg', frame)
        if ret:
            latest_jpeg_frame = jpeg.tobytes()
            
        time.sleep(0.1) # 10 FPS to save CPU

# Start background thread
threading.Thread(target=camera_thread, daemon=True).start()



# -----------------------------
# 🔹 Region Definitions
# Each region has:
#   lat/lon bounding box, OpenWeather city name, display name
# -----------------------------
REGIONS = {
    "ramban": {
        "name":      "Ramban (NH-44)",
        "lat_start": 33.20,
        "lat_end":   33.25,
        "lon_start": 75.15,
        "lon_end":   75.25,
        "city":      "Ramban",
    },
}

ROWS = 5
COLS = 5

# -----------------------------
# 🔹 API Keys & Config
# -----------------------------
OPENWEATHER_API_KEY = os.environ.get("OPENWEATHER_API_KEY", "YOUR_OPENWEATHER_API_KEY")

BHUVAN_API_TOKEN  = os.environ.get("BHUVAN_API_TOKEN", "YOUR_BHUVAN_API_TOKEN")
BHUVAN_WMS_URL    = "https://bhuvan-vec2.nrsc.gov.in/bhuvan/wms"
BHUVAN_LULC_LAYER = "lulc50k_1516"

# -----------------------------
# 🔹 LULC Class → Soil Risk Factor
# -----------------------------
LULC_RISK_MAP = {
    "Built-up":                        0.65,
    "Agricultural Land":               0.55,
    "Forest":                          0.25,
    "Wasteland":                       0.80,
    "Water Bodies":                    0.30,
    "Grassland / Grazing Land":        0.50,
    "Scrub Land":                      0.75,
    "Snow and Glaciers":               0.20,
    "Barren / Rocky / Stony Waste":   0.15,
    "Plantations":                     0.30,
    "Mining / Industrial":             0.70,
    "DEFAULT":                         0.50,
}

# -----------------------------
# 🔹 Caches (keyed by lat/lon so all regions share one cache)
# -----------------------------
elevation_cache = {}
soil_cache      = {}
weather_cache   = {}   # keyed by city name

# -----------------------------
# 🔹 Get Elevation (Open-Elevation)
# -----------------------------
def get_elevation(lat, lon):
    key = f"{round(lat, 5)}_{round(lon, 5)}"
    if key in elevation_cache:
        return elevation_cache[key]
    try:
        url = f"https://api.open-elevation.com/api/v1/lookup?locations={lat},{lon}"
        response = requests.get(url, timeout=5)
        data = response.json()
        elevation = data["results"][0]["elevation"]
        elevation_cache[key] = elevation
        return elevation
    except:
        return 100  # fallback

# -----------------------------
# 🔹 Get Weather (OpenWeather) — per city
# -----------------------------
def get_weather(city):
    if city in weather_cache:
        return weather_cache[city]
    try:
        url = (
            f"http://api.openweathermap.org/data/2.5/weather"
            f"?q={city}&appid={OPENWEATHER_API_KEY}&units=metric"
        )
        response = requests.get(url, timeout=5)
        data = response.json()
        rainfall = data.get("rain", {}).get("1h", 0)
        temp = data.get("main", {}).get("temp", 22.5)
        humidity = data.get("main", {}).get("humidity", 65)
        
        weather_cache[city] = {"rain": rainfall, "temp": temp, "humidity": humidity}
        return weather_cache[city]
    except:
        return {"rain": 0, "temp": 22.5, "humidity": 65}

# -----------------------------
# 🔹 Get Soil Factor from Bhuvan WMS
# -----------------------------
def get_soil_factor_bhuvan(lat, lon):
    key = f"{round(lat, 4)}_{round(lon, 4)}"
    if key in soil_cache:
        return soil_cache[key]

    try:
        delta = 0.0005
        bbox  = f"{lon - delta},{lat - delta},{lon + delta},{lat + delta}"

        params = {
            "SERVICE":      "WMS",
            "VERSION":      "1.1.1",
            "REQUEST":      "GetFeatureInfo",
            "LAYERS":       BHUVAN_LULC_LAYER,
            "QUERY_LAYERS": BHUVAN_LULC_LAYER,
            "STYLES":       "",
            "BBOX":         bbox,
            "WIDTH":        "3",
            "HEIGHT":       "3",
            "SRS":          "EPSG:4326",
            "FORMAT":       "image/png",
            "INFO_FORMAT":  "application/json",
            "X":            "1",
            "Y":            "1",
            "token":        BHUVAN_API_TOKEN,
        }

        response = requests.get(BHUVAN_WMS_URL, params=params, timeout=8)

        if response.status_code == 200:
            try:
                data     = response.json()
                features = data.get("features", [])
                if features:
                    props = features[0].get("properties", {})
                    lulc_class = (
                        props.get("class_name")
                        or props.get("Class_Name")
                        or props.get("LULC_CLASS")
                        or props.get("lulc_class")
                        or props.get("category")
                        or ""
                    )
                    factor = LULC_RISK_MAP["DEFAULT"]
                    for class_key, risk in LULC_RISK_MAP.items():
                        if class_key.lower() in lulc_class.lower():
                            factor = risk
                            break
                    soil_cache[key] = factor
                    print(f"Bhuvan LULC at ({lat},{lon}): '{lulc_class}' → soil_factor={factor}")
                    return factor
            except ValueError:
                factor = _parse_lulc_text(response.text.strip())
                soil_cache[key] = factor
                return factor

        print(f"Bhuvan WMS returned status {response.status_code} for ({lat},{lon})")

    except requests.exceptions.Timeout:
        print(f"Bhuvan WMS timeout for ({lat},{lon})")
    except Exception as e:
        print(f"Bhuvan WMS error for ({lat},{lon}): {e}")

    return 0.5


def _parse_lulc_text(text):
    text_lower = text.lower()
    for class_key, risk in LULC_RISK_MAP.items():
        if class_key.lower() in text_lower:
            return risk
    return LULC_RISK_MAP["DEFAULT"]


# -----------------------------
# 🔹 Generate Micro-Zones for a given region
# -----------------------------
def generate_microzones(region_cfg):
    lat_points = np.linspace(region_cfg["lat_start"], region_cfg["lat_end"], ROWS + 1)
    lon_points = np.linspace(region_cfg["lon_start"], region_cfg["lon_end"], COLS + 1)

    zones = []
    for i in range(ROWS):
        for j in range(COLS):
            zones.append({
                "zone_id": f"Z{i+1}{j+1}",
                "row":     i + 1,
                "col":     j + 1,
                "lat1":    float(lat_points[i]),
                "lon1":    float(lon_points[j]),
                "lat2":    float(lat_points[i + 1]),
                "lon2":    float(lon_points[j + 1]),
            })
    return zones


# -----------------------------
# 🔹 AI Grid Risk Route
# Usage: /grid_risk?region=ramban
#        /grid_risk           (defaults to ramban)
# -----------------------------
@app.route("/grid_risk")
def grid_risk():
    global camera_alert_active
    region_key = request.args.get("region", "ramban").lower().strip()

    if region_key not in REGIONS:
        return jsonify({
            "error":            f"Unknown region '{region_key}'.",
            "available_regions": list(REGIONS.keys()),
        }), 400

    region_cfg = REGIONS[region_key]
    base_grid  = generate_microzones(region_cfg)
    weather    = get_weather(region_cfg["city"])
    rainfall   = weather["rain"]

    # Get real DHT11 readings, fallback to OpenWeather API
    real_temp, real_hum = sensors.get_real_climate()
    current_temp = real_temp if real_temp is not None else weather["temp"]
    current_hum = real_hum if real_hum is not None else weather["humidity"]

    rain_24h = rainfall * 4
    rain_72h = rainfall * 10

    from concurrent.futures import ThreadPoolExecutor

    def process_zone(zone):
        center_lat = (zone["lat1"] + zone["lat2"]) / 2
        center_lon = (zone["lon1"] + zone["lon2"]) / 2

        elevation   = get_elevation(center_lat, center_lon)
        slope       = min(abs(elevation - 100) / 300, 1)
        soil_factor = get_soil_factor_bhuvan(center_lat, center_lon)

        features    = [[rain_24h, rain_72h, slope, elevation, soil_factor]]
        probability = model.predict_proba(features)[0][1]
        risk_score  = round(float(probability), 2)

        if risk_score < 0.4:
            status = "GREEN"
        elif risk_score < 0.7:
            status = "YELLOW"
        else:
            status = "RED"

        zone["risk"]        = risk_score
        zone["status"]      = status
        zone["elevation"]   = elevation
        zone["slope"]       = round(slope, 2)
        zone["soil_factor"] = soil_factor
        zone["rainfall_1h"] = rainfall
        
        return zone

    enriched_grid  = []
    highest_risk   = 0
    most_dangerous = None

    # Optimize CPU: Use 4 workers matching Pi 4's quad-core CPU, instead of 25 concurrent threads
    with ThreadPoolExecutor(max_workers=4) as executor:
        results = list(executor.map(process_zone, base_grid))

    # Get real tilt
    current_tilt = sensors.get_real_tilt()
    
    for zone in results:
        if zone["risk"] > highest_risk:
            highest_risk   = zone["risk"]
            most_dangerous = zone["zone_id"]
        enriched_grid.append(zone)

    if (camera_alert_active or current_tilt > tilt_threshold) and enriched_grid:
        # Override the most dangerous zone to RED due to camera motion detection or tilt sensor
        max_zone = next((z for z in enriched_grid if z["zone_id"] == most_dangerous), enriched_grid[0])
        max_zone["risk"] = 0.95
        max_zone["status"] = "RED"
        highest_risk = 0.95
        most_dangerous = max_zone["zone_id"]

    return jsonify({
        "region":         region_cfg["name"],
        "region_key":     region_key,
        "zones":          enriched_grid,
        "most_dangerous": most_dangerous,
        "sensors": {
            "temperature": current_temp,
            "humidity": current_hum,
            "vibration": sensors.get_real_vibration(),
            "soil_moisture": sensors.get_real_soil_moisture() if sensors.get_real_soil_moisture() is not None else min(100, int(current_hum * 0.9 + rainfall * 10)),
            "tilt": current_tilt,
            "tilt_threshold": tilt_threshold
        }
    })


# -----------------------------
# 🔹 List available regions
# -----------------------------
@app.route("/regions")
def list_regions():
    return jsonify({
        k: {"name": v["name"], "city": v["city"]}
        for k, v in REGIONS.items()
    })

# -----------------------------
# 🔹 Settings Endpoint (Update Tilt Threshold)
# -----------------------------
@app.route("/api/settings", methods=["POST"])
def update_settings():
    global tilt_threshold
    data = request.json
    if data and "tilt_threshold" in data:
        try:
            tilt_threshold = float(data["tilt_threshold"])
            return jsonify({"success": True, "tilt_threshold": tilt_threshold})
        except ValueError:
            return jsonify({"error": "Invalid tilt threshold"}), 400
    return jsonify({"error": "No settings provided"}), 400



# -----------------------------
# 🔹 Camera Motion & Video Streaming
# -----------------------------
def generate_video_stream():
    global latest_jpeg_frame
    while True:
        if latest_jpeg_frame is not None:
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + latest_jpeg_frame + b'\r\n\r\n')
        time.sleep(0.1)

@app.route("/video_feed")
def video_feed():
    return Response(generate_video_stream(), mimetype='multipart/x-mixed-replace; boundary=frame')



# -----------------------------
# 🔹 Basic Routes
# -----------------------------
@app.route("/")
def home():
    return "INNOBOT – AI Micro-Zone Landslide System Running"

@app.route("/dashboard")
def dashboard():
    return render_template("dashboard.html")


if __name__ == "__main__":
    app.run(debug=True)