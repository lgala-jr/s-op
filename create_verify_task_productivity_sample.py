"""Create sample task productivity data for testing when BigQuery is unavailable."""
import random
from pathlib import Path

Path("output").mkdir(exist_ok=True)
tasks = ["Verify Fill", "Verify Order", "Verify Batch"]
wh_names = ["OHIO", "BEYONDRX_OH", "BEYONDRX_AZ"]
n = 5000
data = []
for _ in range(n):
    task = random.choice(tasks)
    wh = random.choice(wh_names)
    # Lognormal-like duration (minutes)
    dur = max(0.1, random.gammavariate(3, 2) + random.uniform(0, 5))
    data.append({"task": task, "wh_name": wh, "logic_adjusted_new_step_duration_minutes": round(dur, 2)})

import pandas as pd
df = pd.DataFrame(data)
df.to_csv("output/verify_task_productivity.csv", index=False)
print(f"Created sample data: output/verify_task_productivity.csv ({len(df)} rows)")
