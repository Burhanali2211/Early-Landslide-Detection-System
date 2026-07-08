import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split
from xgboost import XGBClassifier
import joblib

import os

# -----------------------------
# 1️⃣ Load Real Training Data
# -----------------------------
DATA_FILE = "real_landslide_data.csv"

if not os.path.exists(DATA_FILE):
    print(f"Error: Real dataset '{DATA_FILE}' not found.")
    print("Generating a sample template file for you to fill with real data...")
    
    # Generate a dummy template with one row to show the format
    dummy_data = pd.DataFrame({
        "rain_24h": [150.0],
        "rain_72h": [400.0],
        "slope": [0.6],
        "elevation": [2500.0],
        "soil_factor": [0.8],
        "landslide": [1] # 1 for landslide, 0 for no landslide
    })
    dummy_data.to_csv(DATA_FILE, index=False)
    
    print(f"Template '{DATA_FILE}' created.")
    print("PLEASE FILL IT WITH REAL HISTORICAL DATA BEFORE TRAINING!")
    exit(1)

print(f"Loading real data from {DATA_FILE}...")
data = pd.read_csv(DATA_FILE)

# Ensure required columns exist
required_columns = ["rain_24h", "rain_72h", "slope", "elevation", "soil_factor", "landslide"]
for col in required_columns:
    if col not in data.columns:
        print(f"Error: Missing required column '{col}' in your dataset.")
        exit(1)

# -----------------------------
# 3️⃣ Train Model
# -----------------------------

X = data[["rain_24h", "rain_72h", "slope", "elevation", "soil_factor"]]
y = data["landslide"]

X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=42
)

model = XGBClassifier(
    n_estimators=300,
    max_depth=5,
    learning_rate=0.05
)

model.fit(X_train, y_train)

accuracy = model.score(X_test, y_test)
print("Model Accuracy:", accuracy)

# -----------------------------
# 4️⃣ Feature Importance
# -----------------------------

feature_names = ["rain_24h", "rain_72h", "slope", "elevation", "soil_factor"]
importances = model.feature_importances_

print("\nFeature Importances:")
for name, score in zip(feature_names, importances):
    print(f"{name}: {round(score, 3)}")

# -----------------------------
# 5️⃣ Save Model
# -----------------------------

joblib.dump(model, "landslide_model.pkl")
print("\nModel saved successfully.")