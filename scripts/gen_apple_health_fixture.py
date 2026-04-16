"""Generate large_range_90d.xml with 90 days of all 5 metric types (~450 records)."""
import random
from datetime import date, timedelta

lines = ['<?xml version="1.0" encoding="UTF-8"?>', '<HealthData locale="en_US">']
base = date(2026, 1, 16)
random.seed(42)  # deterministic
for i in range(90):
    d = base + timedelta(days=i)
    prev = d - timedelta(days=1)
    ds = d.isoformat()
    ps = prev.isoformat()
    lines.append(
        f' <Record type="HKQuantityTypeIdentifierHeartRateVariabilitySDNN" '
        f'sourceName="Apple Watch" unit="ms" '
        f'creationDate="{ds} 08:00:00 +0000" startDate="{ps} 22:00:00 +0000" '
        f'endDate="{ds} 06:00:00 +0000" value="{random.uniform(30,70):.1f}"/>'
    )
    lines.append(
        f' <Record type="HKCategoryTypeIdentifierSleepAnalysis" '
        f'sourceName="Apple Watch" unit="" '
        f'creationDate="{ds} 08:00:00 +0000" startDate="{ps} 23:00:00 +0000" '
        f'endDate="{ds} 07:00:00 +0000" value="HKCategoryValueSleepAnalysisAsleep"/>'
    )
    lines.append(
        f' <Record type="HKQuantityTypeIdentifierRestingHeartRate" '
        f'sourceName="Apple Watch" unit="count/min" '
        f'creationDate="{ds} 08:00:00 +0000" startDate="{ds} 08:00:00 +0000" '
        f'endDate="{ds} 08:00:00 +0000" value="{random.randint(48,65)}"/>'
    )
    lines.append(
        f' <Record type="HKQuantityTypeIdentifierActiveEnergyBurned" '
        f'sourceName="Apple Watch" unit="kcal" '
        f'creationDate="{ds} 20:00:00 +0000" startDate="{ds} 06:00:00 +0000" '
        f'endDate="{ds} 20:00:00 +0000" value="{random.uniform(200,600):.1f}"/>'
    )
lines.append('</HealthData>')

with open("tests/fixtures/apple_health/large_range_90d.xml", "w", encoding="utf-8") as f:
    f.write("\n".join(lines))
print(f"Generated {len(lines)-2} record lines")
