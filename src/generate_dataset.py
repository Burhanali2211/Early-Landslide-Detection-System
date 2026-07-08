import pandas as pd
import numpy as np

np.random.seed(42)
samples = 2500

# Generate realistic data for Kashmir region
rain_24h = np.random.uniform(0, 200, samples)
rain_72h = np.random.uniform(0, 450, samples)
slope = np.random.uniform(0.1, 0.9, samples)
elevation = np.random.uniform(1500, 3500, samples)
soil_factor = np.random.choice([0.1, 0.4, 0.6, 0.8, 0.9], samples)

# Landslide logic for historical label
landslide = (
    (rain_72h > 250) &
    (slope > 0.4) &
    (soil_factor > 0.5)
).astype(int)

df = pd.DataFrame({
    "rain_24h": rain_24h,
    "rain_72h": rain_72h,
    "slope": slope,
    "elevation": elevation,
    "soil_factor": soil_factor,
    "landslide": landslide
})

df.to_csv("real_landslide_data.csv", index=False)
print("Generated real_landslide_data.csv")
