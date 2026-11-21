import json
d = json.load(open("D:/chrono-data/corporate_actions/spin_offs.json"))
print(type(d).__name__, list(d)[:5] if isinstance(d, dict) else len(d))
dates = []
def walk(x):
    if isinstance(x, dict):
        for k, v in x.items():
            if k in ("ex_date", "process_date", "date", "record_date", "payable_date") and isinstance(v, str):
                dates.append(v[:10])
            walk(v)
    elif isinstance(x, list):
        for v in x: walk(v)
walk(d)
print("date-like fields", len(dates), "min", min(dates) if dates else None, "max", max(dates) if dates else None)
print("records dated before 2019-01-01:", sum(x < "2019-01-01" for x in dates))
