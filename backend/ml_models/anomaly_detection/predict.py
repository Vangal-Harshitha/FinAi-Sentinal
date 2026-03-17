def predict_single(features: dict) -> dict:
    amount = features.get("amount", 0)
    income = features.get("monthly_income", 50000)

    ratio = amount / max(income, 1)

    if ratio > 0.7:
        return {"is_anomaly": True, "score": ratio, "severity": "high"}
    if ratio > 0.4:
        return {"is_anomaly": True, "score": ratio, "severity": "medium"}

    return {"is_anomaly": False, "score": ratio, "severity": "low"}