"""
Create sample base data for testing the analysis pipeline when BigQuery is not available.
Run the real SQL export when you have bq CLI access.
"""

import random
from datetime import datetime, timedelta

import pandas as pd
from pathlib import Path

random.seed(42)

n = 2000
# Prior 6 months date range (~180 days)
_end = datetime.now()
_start = _end - timedelta(days=180)
date_range = pd.date_range(_start.strftime("%Y-%m-%d"), _end.strftime("%Y-%m-%d"), freq="D")
dispense_methods = ["Automation", "Manual", "Mixture"]
product_types = ["GLP", "Tablet", "Topical", "Gummy", "Rx", "Non-Rx"]
wh_names = ["OHIO", "BEYONDRX_OH", "BEYONDRX_AZ"]  # Ohio and Arizona only
level_2_vals = ["Weight Loss - Injectable", "Hair", "Sex", "Weight Loss - Oral", "Mental Health"]
level_3_vals = ["Finasteride", "Minoxidil", "Tadalafil", "Semaglutide", "Liraglutide", "Other"]
units = ["EACH", "MILLILITER", None]

# Realistic associations: Gummy/Tablet -> more Automation, Topical -> more Manual
dates = date_range.astype(str).tolist()
rxcuis = [f"rxcui_{i}" for i in range(50)]
df = pd.DataFrame({
    "fill_id": [f"fill_{i}" for i in range(n)],
    "order_id": [f"ord_{i // 2}" for i in range(n)],
    "product_id": random.choices(rxcuis, k=n),
    "dispense_method": random.choices(dispense_methods, weights=[0.5, 0.35, 0.15], k=n),
    "order_status_date": random.choices(dates, k=n),
    "wh_name": random.choices(wh_names, weights=[0.5, 0.3, 0.2], k=n),
    "is_rx": random.choices([True, False], weights=[0.85, 0.15], k=n),
    "is_compound": random.choices([True, False], weights=[0.7, 0.3], k=n),
    "is_multi": random.choices([True, False], weights=[0.2, 0.8], k=n),
    "level_2": random.choices(level_2_vals, k=n),
    "level_3": random.choices(level_3_vals, k=n),
    "unit_of_measure": random.choices(units, k=n),
    "order_qty": [random.randint(1, 3) for _ in range(n)],
})

# Assign product_type from level_2 / unit (subset get Gummy for variety)
def assign_product_type(row):
    if "Injectable" in str(row["level_2"]):
        return "GLP"
    if row["unit_of_measure"] == "MILLILITER" and row["is_compound"]:
        return "Topical"
    if row["is_compound"]:
        return "Tablet" if random.random() > 0.1 else "Gummy"
    return random.choice(["Rx", "Non-Rx"])

df["product_type"] = df.apply(assign_product_type, axis=1)

# Bias dispense_method by product_type (realistic patterns)
dispense_map = {
    "Gummy": [0.85, 0.1, 0.05],
    "Tablet": [0.7, 0.2, 0.1],
    "Topical": [0.2, 0.7, 0.1],
    "GLP": [0.6, 0.3, 0.1],
    "Rx": [0.5, 0.4, 0.1],
    "Non-Rx": [0.4, 0.45, 0.15],
}
def _pick_dispense(pt):
    probs = dispense_map.get(pt, [0.4, 0.4, 0.2])
    return random.choices(dispense_methods, weights=probs, k=1)[0]

df["dispense_method"] = df["product_type"].map(_pick_dispense)

out = Path("output/base_data.csv")
out.parent.mkdir(parents=True, exist_ok=True)
df.to_csv(out, index=False)
print(f"Sample data saved to {out} ({len(df)} rows)")
