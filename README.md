# ALPROS - Automatic Landscape Prediction & Rescue Optimization System

ALPROS is a comprehensive landslide risk prediction and monitoring system specifically adapted for the highly vulnerable **Ramban-Banihal stretch (NH-44) in Kashmir**. It combines classical statistical analysis, state-of-the-art machine learning, and real-time computer vision to provide accurate, real-time landslide hazard assessments across micro-scale geographic zones.

## System Components

ALPROS features three integrated modules that form the core of the risk assessment engine:

1. **ML Risk Predictor** (`src/train_model.py` & `src/landslide_model.pkl`) - XGBoost-based classification
2. **Web Dashboard & Live Monitor** (`src/app.py` & `src/templates/dashboard.html`) - Real-time micro-zone grid visualization and camera integration
3. **Rescue & Damage Analysis** (`src/rescue.py`) - Computer Vision structural damage assessment

---

## The Three Checks: How a Landslide is Declared

ALPROS uses three distinct, multi-layered checks to continuously monitor the region and declare a landslide emergency.

### 1. Machine Learning Environmental Checks (Predictive)
The system divides the Ramban stretch into a 5×5 grid of micro-zones. For each zone, an AI model (XGBoost classifier trained on high-altitude topographic data) evaluates the following 5 critical environmental factors in real-time:
- **24-hour & 72-hour Rainfall**: Fetched live via the OpenWeatherMap API. Heavy prolonged rainfall drastically increases soil saturation.
- **Elevation**: Retrieved via Open-Elevation API, representing the high-altitude nature of Kashmir (1500m+).
- **Terrain Slope Angle**: Calculated from elevation differentials. Steeper slopes have a higher susceptibility to sheer failure.
- **Soil Composition Factor**: Fetched via India's Bhuvan satellite WMS layer (LULC data), classifying the ground into rock, forest, built-up areas, etc.

*Outcome*: The model outputs a probability score (0.0 to 1.0). If the score is ≥ 0.7, the zone is declared **RED** (High Risk).

### 2. Live Camera Motion Checks (Reactive)
If a physical landslide or rockfall occurs abruptly, environmental data might lag. ALPROS integrates a live webcam feed to act as a reactive mountain monitor.
- **OpenCV Background Subtraction**: The backend continuously receives frames from the dashboard camera and compares the current frame to the previous frame using absolute differencing (`cv2.absdiff`).
- **Thresholding**: If a massive pixel shift is detected (contour area > 5000), simulating a sudden rockfall or mudslide in the camera's view, the system triggers a global `CAMERA_ALERT`.
- *Outcome*: This instantly overrides the grid and forces the most vulnerable zone into a **RED** emergency state, flashing a "MOTION DETECTED" warning on the dashboard.

### 3. Computer Vision Rescue Checks (Post-Disaster)
Once an event has occurred, the system switches to Rescue Mode to assess damage from drone or satellite imagery.
- **SSIM (Structural Similarity Index)**: The uploaded post-disaster image is compared to a pre-disaster baseline reference image. A low SSIM score indicates catastrophic structural changes to the landscape.
- **Color-Based Mud/Water Detection**: The system applies HSV color masking to detect the desaturated browns of mudslides, debris fields, and standing floodwaters.
- *Outcome*: The system outputs a visual heat map of the damage and a percentage of the area destroyed, helping guide rescue operations.

---

## Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/Anandhanachu/ALPROS.git
   cd ALPROS
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Ensure you have your OpenWeatherMap API key and Bhuvan API token configured in `src/app.py`.

4. Run the Flask server:
   ```bash
   cd src
   python app.py
   ```

5. Access the web dashboard at `http://127.0.0.1:5000/dashboard`.
   *(Note: You will need to allow webcam permissions in your browser to test the Live Camera Motion check).*

## Model Training

To retrain the predictive XGBoost model for different topological thresholds, run:
```bash
cd src
python train_model.py
```
This simulates thousands of realistic rainfall, slope, and elevation scenarios specifically tailored for the high-altitude environment of Kashmir and generates a new `landslide_model.pkl`.
