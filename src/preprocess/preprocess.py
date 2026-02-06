import json
import pandas as pd

filename = r"D:\Data Science Project\job_finder\src\data\jobs\2026-01-30.jsonl"

data = []
with open(filename, "r", encoding="utf-8") as f:
    for line in f:
        data.append(json.loads(line))

df = pd.DataFrame(data)
print(df)

