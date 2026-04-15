"""
Recommendation Service – Personalized wellness suggestions.

Combines mood score + journal sentiment + burnout risk to suggest
breathing exercises, journal prompts, tips, and community sessions.
"""
import random
from typing import Any

# ── Recommendation Pools ──────────────────────────────────────────────────────

BREATHING_EXERCISES = [
    {
        "title": "4-7-8 Breathing",
        "description": "Inhale for 4 counts, hold for 7, exhale for 8. Repeat 4 times. Calms the nervous system instantly.",
        "action_label": "Try Now",
    },
    {
        "title": "Box Breathing",
        "description": "Breathe in 4 counts, hold 4, out 4, hold 4. Used by Navy SEALs for stress control.",
        "action_label": "Start Exercise",
    },
    {
        "title": "5-5-5 Breathing",
        "description": "Simple: breathe in for 5 counts, hold for 5, breathe out for 5. Great for anxiety.",
        "action_label": "Start Exercise",
    },
    {
        "title": "Belly Breathing",
        "description": "Place a hand on your stomach. Breathe deeply until your belly rises. 1 minute of this resets your nervous system.",
        "action_label": "Learn How",
    },
]

JOURNAL_PROMPTS = [
    {
        "title": "Three Good Things",
        "description": "Write down exactly 3 things — big or tiny — that went well today and why.",
        "action_label": "Open Journal",
    },
    {
        "title": "Letter to Yourself",
        "description": "Write a kind letter to yourself as if you were your own best friend. What would you say?",
        "action_label": "Start Writing",
    },
    {
        "title": "What I'm Proud Of",
        "description": "List 3 things you've handled well this week — even if they feel small.",
        "action_label": "Open Journal",
    },
    {
        "title": "What's Weighing on Me",
        "description": "Write freely about what's on your mind. No judgment — just let it out on the page.",
        "action_label": "Start Writing",
    },
    {
        "title": "My Energy Sources",
        "description": "What gives you energy? What drains it? Map it out.",
        "action_label": "Reflect on This",
    },
    {
        "title": "Tomorrow's One Win",
        "description": "Set one tiny, achievable goal for tomorrow and write down exactly how you'll do it.",
        "action_label": "Open Journal",
    },
]

WELLNESS_TIPS = [
    {
        "title": "Hydrate First Thing",
        "description": "Drink a glass of water before checking your phone in the morning. Your mood often depends on your hydration.",
        "action_label": "Got It",
    },
    {
        "title": "5-Minute Walk",
        "description": "A 5-minute walk outside can shift your mood more effectively than most interventions.",
        "action_label": "Step Outside",
    },
    {
        "title": "Phone-Free Hour",
        "description": "Try one hour today without your phone. Read, draw, cook, or just sit. Notice how you feel after.",
        "action_label": "Try Today",
    },
    {
        "title": "Reach Out to One Person",
        "description": "Text or call one person you care about today — not for anything specific, just to connect.",
        "action_label": "Connect",
    },
    {
        "title": "Sleep Boundary",
        "description": "Set a phone-off alarm 30 minutes before bed. Quality sleep is the single best mental health tool.",
        "action_label": "Set Alarm",
    },
    {
        "title": "Gratitude Pause",
        "description": "Before you sleep, think of one person you're grateful for and why. Don't skip this — it rewires your brain over time.",
        "action_label": "Try Tonight",
    },
]

COMMUNITY_SESSIONS = [
    {
        "title": "Join a Mindful Mornings Session",
        "description": "Live group meditation every Tuesday and Thursday at 8am. Gentle, welcoming, 15 minutes.",
        "action_label": "See Schedule",
    },
    {
        "title": "Creative Flow Workshop",
        "description": "Express yourself through art, writing, or music. No skills needed — just a willingness to try.",
        "action_label": "View Sessions",
    },
    {
        "title": "Anxiety Circle",
        "description": "A safe space to share what anxiety feels like and learn from peers who get it.",
        "action_label": "Join Circle",
    },
]

CRISIS_RESOURCES = [
    {
        "title": "Talk to a Mentor Now",
        "description": "Our verified mentors are online 24/7. Private and judgment-free.",
        "action_label": "Connect Now",
    },
    {
        "title": "Crisis Support Line",
        "description": "iCall India: 9152987821 — Available Mon-Sat, 8am-10pm. Free and confidential.",
        "action_label": "Call Now",
    },
]


def get_recommendations(
    mood_score: float | None,
    sentiment_score: float | None,
    burnout_label: str,
    emotion: str | None,
    max_items: int = 5,
) -> list[dict[str, Any]]:
    """
    Generate personalized recommendations based on user state.

    Priority rules:
    - Crisis/high burnout → crisis resources first
    - Negative mood + sentiment → breathing + journaling
    - Low mood → wellness tips + community
    - Neutral/positive → journaling prompts + tips
    """
    items: list[dict[str, Any]] = []
    score = mood_score or 5.0
    sentiment = sentiment_score or 0.0

    # ── Crisis override ───────────────────────────────────────────────────────
    if burnout_label == "high":
        for r in CRISIS_RESOURCES:
            items.append({**r, "type": "resource", "priority": 1})

    # ── Breathing (always useful under stress/anxiety) ────────────────────────
    if emotion in ("stressed", "anxious", "angry") or score < 5:
        items.append({**random.choice(BREATHING_EXERCISES), "type": "breathing", "priority": 2})

    # ── Journal prompts ───────────────────────────────────────────────────────
    if sentiment < -0.1 or score < 6:
        items.append({**random.choice(JOURNAL_PROMPTS[:4]), "type": "journal_prompt", "priority": 3})
    else:
        items.append({**random.choice(JOURNAL_PROMPTS), "type": "journal_prompt", "priority": 4})

    # ── Wellness tips ─────────────────────────────────────────────────────────
    tip = random.choice(WELLNESS_TIPS)
    items.append({**tip, "type": "tip", "priority": 3})

    # ── Community session ─────────────────────────────────────────────────────
    if burnout_label in ("medium", "high") or emotion in ("sad", "lonely"):
        items.append({**random.choice(COMMUNITY_SESSIONS), "type": "session", "priority": 3})
    else:
        items.append({**random.choice(COMMUNITY_SESSIONS), "type": "session", "priority": 5})

    # Extra breathing if very stressed
    if score < 4:
        items.append({**random.choice(BREATHING_EXERCISES), "type": "breathing", "priority": 2})

    # Sort by priority, deduplicate, limit
    items.sort(key=lambda x: x["priority"])
    seen_titles = set()
    unique_items = []
    for item in items:
        if item["title"] not in seen_titles:
            seen_titles.add(item["title"])
            unique_items.append(item)

    return unique_items[:max_items]
