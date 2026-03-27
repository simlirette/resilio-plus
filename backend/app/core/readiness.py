from __future__ import annotations

from app.schemas.connector import TerraHealthData


def compute_readiness(
    terra_data: list[TerraHealthData],
    hrv_baseline: float | None = None,
) -> float:
    """Compute readiness modifier in [0.5, 1.5] from HRV and sleep data.

    Returns 1.0 for empty input (cold start with no data).
    hrv_baseline: externally provided long-term HRV mean (ms). If None, computed
    from available data or cold-start (delta = 0) if fewer than 4 valid entries.
    """
    if not terra_data:
        return 1.0

    # Sort newest-first, take last 7 entries
    sorted_data = sorted(terra_data, key=lambda e: e.date, reverse=True)
    last_7 = sorted_data[:7]

    # Step 1: HRV delta
    all_hrv = [e.hrv_rmssd for e in sorted_data if e.hrv_rmssd is not None]
    hrv_7d = [e.hrv_rmssd for e in last_7 if e.hrv_rmssd is not None]

    if hrv_7d:
        hrv_7d_mean = sum(hrv_7d) / len(hrv_7d)
        if hrv_baseline is None:
            if len(all_hrv) < 4:
                hrv_delta = 0.0  # cold start — not enough data
            else:
                computed_baseline = sum(all_hrv) / len(all_hrv)
                hrv_delta = _hrv_ratio_to_delta(hrv_7d_mean / computed_baseline)
        else:
            hrv_delta = _hrv_ratio_to_delta(hrv_7d_mean / hrv_baseline if hrv_baseline > 0 else 1.0)
    else:
        hrv_delta = 0.0

    # Step 2: Sleep delta
    sleep_hours = [e.sleep_duration_hours for e in last_7 if e.sleep_duration_hours is not None]
    sleep_scores = [e.sleep_score for e in last_7 if e.sleep_score is not None]

    if sleep_hours or sleep_scores:
        h_mean = sum(sleep_hours) / len(sleep_hours) if sleep_hours else None
        s_mean = sum(sleep_scores) / len(sleep_scores) if sleep_scores else None
        if (h_mean is not None and h_mean < 6.0) or (s_mean is not None and s_mean < 50):
            sleep_delta = -0.20
        elif h_mean is not None and h_mean >= 7.0 and s_mean is not None and s_mean >= 70:
            sleep_delta = 0.0
        else:
            sleep_delta = -0.10
    else:
        sleep_delta = 0.0

    modifier = 1.0 + hrv_delta + sleep_delta
    return max(0.5, min(1.5, modifier))


def _hrv_ratio_to_delta(ratio: float) -> float:
    if ratio >= 1.0:
        return 0.10
    if ratio >= 0.80:
        return 0.0
    if ratio >= 0.60:
        return -0.15
    return -0.30
