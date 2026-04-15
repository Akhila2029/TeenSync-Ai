"""
Burnout Detection Service

Analyzes user's mood and journal patterns to detect risk of burnout/emotional exhaustion.

Algorithm:
1. Collect last 14 days of mood scores and journal sentiments.
2. Compute features: avg_score, trend_slope, consecutive_negative_days, engagement_gap.
3. Apply rule-based scoring → weighted risk score 0-100.
4. Optionally apply IsolationForest for anomaly detection on rolling features.
5. Return risk label: low / medium / high.
"""
from datetime import datetime, timedelta, timezone
from typing import Any

import numpy as np

try:
    from sklearn.ensemble import IsolationForest
    SKLEARN_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False

from app.config import settings


def _compute_trend_slope(values: list[float]) -> float:
    """Least-squares slope of the values (positive = improving, negative = declining)."""
    if len(values) < 2:
        return 0.0
    x = np.arange(len(values), dtype=float)
    y = np.array(values, dtype=float)
    slope = float(np.polyfit(x, y, 1)[0])
    return round(slope, 4)


def _count_consecutive_negatives(scores: list[float], threshold: float = 4.5) -> int:
    """Count trailing consecutive days where mood score < threshold."""
    count = 0
    for s in reversed(scores):
        if s < threshold:
            count += 1
        else:
            break
    return count


def compute_burnout_risk(
    mood_scores: list[float],           # list of scores (1-10), recent-first
    journal_sentiments: list[float],    # VADER compound scores, recent-first
    last_activity_days_ago: int = 0,   # Days since last app interaction
    session_count_last_7_days: int = 0,
) -> dict[str, Any]:
    """
    Compute a burnout risk score and label.

    Returns:
        risk_score: float (0-100)
        risk_label: "low" | "medium" | "high"
        features: dict of computed features
        consecutive_negative_days: int
        avg_mood_score: float
        avg_sentiment: float
        recommendation: str
    """
    # ── Feature Computation ───────────────────────────────────────────────────
    scores = mood_scores[:14] if len(mood_scores) >= 14 else mood_scores
    sentiments = journal_sentiments[:14] if len(journal_sentiments) >= 14 else journal_sentiments

    avg_mood = float(np.mean(scores)) if scores else 5.0
    avg_sentiment = float(np.mean(sentiments)) if sentiments else 0.0

    mood_slope = _compute_trend_slope(list(reversed(scores))) if len(scores) >= 3 else 0.0
    consecutive_neg = _count_consecutive_negatives(scores)

    # Engagement penalty (0 = active today, 7 = 7 days inactive)
    engagement_gap_penalty = min(last_activity_days_ago * 5, 30)
    low_session_penalty = max(0, (3 - session_count_last_7_days) * 5)

    features = {
        "avg_mood_score": round(avg_mood, 2),
        "avg_sentiment": round(avg_sentiment, 4),
        "mood_trend_slope": mood_slope,
        "consecutive_negative_days": consecutive_neg,
        "last_activity_days_ago": last_activity_days_ago,
        "session_count_7d": session_count_last_7_days,
        "data_points": len(scores),
    }

    # ── Rule-Based Risk Scoring ───────────────────────────────────────────────
    risk_score = 0.0

    # Low mood (avg below 5 is concerning)
    if avg_mood < 3:
        risk_score += 40
    elif avg_mood < 4:
        risk_score += 25
    elif avg_mood < 5:
        risk_score += 15
    elif avg_mood < 6:
        risk_score += 5

    # Negative sentiment in journals
    if avg_sentiment < -0.4:
        risk_score += 25
    elif avg_sentiment < -0.2:
        risk_score += 15
    elif avg_sentiment < 0:
        risk_score += 8

    # Consecutive negative days
    risk_score += min(consecutive_neg * 6, 24)

    # Declining mood trend
    if mood_slope < -0.5:
        risk_score += 15
    elif mood_slope < -0.2:
        risk_score += 8

    # Engagement gap
    risk_score += engagement_gap_penalty
    risk_score += low_session_penalty

    # Cap at 100
    risk_score = min(float(risk_score), 100.0)

    # ── IsolationForest Anomaly Detection (if enough data) ───────────────────
    if SKLEARN_AVAILABLE and len(scores) >= 7:
        try:
            feature_matrix = np.array([[avg_mood, avg_sentiment, mood_slope, consecutive_neg]])
            clf = IsolationForest(contamination=0.1, random_state=42)
            # Use historical data as training if available (here simplified)
            all_features = []
            for i in range(min(len(scores), 7)):
                window = scores[i:i + 3] if i + 3 <= len(scores) else scores[-3:]
                s_window = sentiments[i:i + 3] if i + 3 <= len(sentiments) else sentiments[-3:]
                all_features.append([
                    np.mean(window),
                    np.mean(s_window) if s_window else 0,
                    _compute_trend_slope(list(reversed(window))),
                    0,
                ])
            if len(all_features) >= 3:
                clf.fit(all_features)
                anomaly = clf.predict(feature_matrix)[0]  # -1 = anomaly, 1 = normal
                if anomaly == -1:
                    risk_score = min(risk_score + 15, 100)
                    features["anomaly_detected"] = True
            features["isolation_forest_used"] = True
        except Exception:
            features["isolation_forest_used"] = False
    else:
        features["isolation_forest_used"] = False

    # ── Label Assignment ──────────────────────────────────────────────────────
    if risk_score >= settings.burnout_high_threshold:
        risk_label = "high"
        recommendation = (
            "Your patterns suggest significant emotional stress. Please consider talking to a school counselor, "
            "trusted adult, or mental health professional. You deserve support. 💙"
        )
    elif risk_score >= settings.burnout_medium_threshold:
        risk_label = "medium"
        recommendation = (
            "You've been going through a tough stretch. Try to build in some rest, connect with someone you trust, "
            "and use the breathing exercises in the Resources section."
        )
    else:
        risk_label = "low"
        recommendation = (
            "You seem to be managing well! Keep up with your daily check-ins and journaling. "
            "Remember to celebrate small wins. 🌱"
        )

    return {
        "risk_score": round(risk_score, 1),
        "risk_label": risk_label,
        "features": features,
        "consecutive_negative_days": consecutive_neg,
        "avg_mood_score": round(avg_mood, 2),
        "avg_sentiment": round(avg_sentiment, 4),
        "recommendation": recommendation,
        "needs_professional_help": risk_score >= settings.burnout_high_threshold,
    }
