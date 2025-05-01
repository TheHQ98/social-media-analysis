import requests
import csv

url = "https://data.api.abs.gov.au/rest/data/ABS,RES_DWELL_ST,1.0.0/all?startPeriod=2020-Q1"
headers = {"Accept": "application/vnd.sdmx.data+json"}

res = requests.get(url, headers=headers)
data = res.json()

dim_ids = ["MEASURE", "REGION", "FREQ", "TIME_PERIOD"]
dim_values = {
    "MEASURE": {
        0: "Mean Price of residential dwellings",
        1: "Total value of residential dwellings",
        2: "Number of residential dwellings"
    },
    "REGION": {
        0: "NSW", 1: "VIC", 2: "QLD", 3: "SA", 4: "WA", 5: "TAS", 6: "NT", 7: "ACT"
    },
    "FREQ": {
        0: "Quarterly"
    }
}

quarters = []
for year in range(2020, 2025):
    for q in range(1, 5):
        quarters.append(f"{year}-Q{q}")
time_map = {i: q for i, q in enumerate(quarters)}
series = data["data"]["dataSets"][0]["series"]
rows = []

for key, entry in series.items():
    m_idx, r_idx, f_idx = map(int, key.split(":"))
    measure = dim_values["MEASURE"].get(m_idx)
    region = dim_values["REGION"].get(r_idx)
    freq = dim_values["FREQ"].get(f_idx)
    unit = "Number" if m_idx == 2 else "AUD"

    for t_idx, val_list in entry["observations"].items():
        quarter = time_map.get(int(t_idx))
        value = val_list[0]
        rows.append([measure, region, quarter, value, unit])

with open("residential_dwellings.csv", "w", newline="") as f:
    writer = csv.writer(f)
    writer.writerow(["Measure", "Region", "Quarter", "Value", "Unit"])
    writer.writerows(rows)

print("CSV saved：residential_dwellings.csv")
