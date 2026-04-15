"""
NLP Service – Sentiment analysis, emotion detection, and keyword extraction.

Uses:
- VADER SentimentIntensityAnalyzer (fast, offline, slang-aware)
- TextBlob for noun phrase / keyword extraction
- Rule-based emotion classifier (no model download required)
"""
import re
from functools import lru_cache
from typing import Any

# ── VADER Sentiment ───────────────────────────────────────────────────────────
try:
    from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
    _vader = SentimentIntensityAnalyzer()
    VADER_AVAILABLE = True
except ImportError:
    VADER_AVAILABLE = False

# ── TextBlob ──────────────────────────────────────────────────────────────────
try:
    from textblob import TextBlob
    TEXTBLOB_AVAILABLE = True
except ImportError:
    TEXTBLOB_AVAILABLE = False


# ── Emotion keyword lexicon ───────────────────────────────────────────────────
_EMOTION_LEXICON: dict[str, list[str]] = {
    "happy": [
        "happy", "joy", "excited", "grateful", "amazing", "wonderful", "great",
        "love", "hopeful", "proud", "cheerful", "smile", "laugh", "fun", "awesome",
        "content", "pleased", "thrilled", "ecstatic", "delighted"
    ],
    "sad": [
        "sad", "unhappy", "cry", "depressed", "down", "low", "lonely", "miss",
        "hurt", "heartbroken", "miserable", "gloomy", "hopeless", "grief", "loss",
        "empty", "worthless", "helpless", "devastated"
    ],
    "anxious": [
        "anxious", "anxiety", "nervous", "worried", "worry", "fear", "scared",
        "panic", "overwhelmed", "tense", "uneasy", "dreading", "terrified",
        "on edge", "restless", "can't sleep", "overthinking"
    ],
    "angry": [
        "angry", "mad", "furious", "rage", "irritated", "annoyed", "frustrated",
        "hate", "upset", "resentful", "bitter", "fed up", "livid", "outraged"
    ],
    "stressed": [
        "stressed", "stress", "pressure", "exhausted", "tired", "burnt out",
        "overwhelmed", "deadline", "too much", "overloaded", "can't cope",
        "falling behind", "struggling", "stuck"
    ],
    "hopeful": [
        "hope", "hopeful", "optimistic", "better", "improve", "looking forward",
        "excited about", "positive", "progress", "growing", "healing", "trying"
    ],
    "neutral": [],
}

# ── Crisis keywords ───────────────────────────────────────────────────────────
_CRISIS_KEYWORDS = [
    "suicide", "suicidal", "kill myself", "end my life", "don't want to live",
    "self harm", "self-harm", "cutting myself", "hurt myself", "overdose",
    "not worth it", "no reason to live", "want to disappear", "give up on life"
]

# ── Content moderation keywords ───────────────────────────────────────────────
_HARMFUL_KEYWORDS = [
    "idiot", "stupid", "loser", "kill yourself", "kys", "die", "worthless",
    "trash", "hate you", "you suck", "shut up", "dumb", "retard", "freak"
]


def analyze_sentiment(text: str) -> dict[str, Any]:
    """
    Run VADER sentiment analysis on text.
    Returns:
        compound: float -1.0 to +1.0
        label: "positive" | "neutral" | "negative"
        positive: float, neutral: float, negative: float
    """
    if not text or not text.strip():
        return {"compound": 0.0, "label": "neutral", "positive": 0.0, "neutral": 1.0, "negative": 0.0}

    if VADER_AVAILABLE:
        scores = _vader.polarity_scores(text)
        compound = scores["compound"]
    else:
        # TextBlob fallback
        if TEXTBLOB_AVAILABLE:
            blob = TextBlob(text)
            compound = blob.sentiment.polarity
        else:
            compound = 0.0

    # Label thresholds (VADER standard)
    if compound >= 0.05:
        label = "positive"
    elif compound <= -0.05:
        label = "negative"
    else:
        label = "neutral"

    return {
        "compound": round(compound, 4),
        "label": label,
        "positive": round(max(0.0, compound), 4),
        "neutral": round(1.0 - abs(compound), 4),
        "negative": round(max(0.0, -compound), 4),
    }


def detect_emotion(text: str) -> str:
    """
    Classify the dominant emotion using keyword matching.
    Returns: "happy" | "sad" | "anxious" | "angry" | "stressed" | "hopeful" | "neutral"
    """
    if not text:
        return "neutral"

    text_lower = text.lower()
    scores: dict[str, int] = {emotion: 0 for emotion in _EMOTION_LEXICON}

    for emotion, keywords in _EMOTION_LEXICON.items():
        for kw in keywords:
            if kw in text_lower:
                scores[emotion] += 1

    # Remove neutral for comparison
    content_scores = {k: v for k, v in scores.items() if k != "neutral" and v > 0}

    if not content_scores:
        # Fall back to VADER-based emotion
        sentiment = analyze_sentiment(text)
        if sentiment["compound"] >= 0.3:
            return "happy"
        elif sentiment["compound"] <= -0.3:
            return "sad"
        return "neutral"

    return max(content_scores, key=lambda k: content_scores[k])


def extract_keywords(text: str, max_keywords: int = 10) -> list[str]:
    """
    Extract meaningful keywords using TextBlob noun phrases + simple word frequency.
    """
    if not text or not text.strip():
        return []

    keywords = []

    # TextBlob noun phrases
    if TEXTBLOB_AVAILABLE:
        blob = TextBlob(text)
        noun_phrases = [np.lower().strip() for np in blob.noun_phrases if len(np) > 2]
        keywords.extend(noun_phrases[:max_keywords])

    # Word frequency fallback / supplement
    if len(keywords) < 3:
        # Simple word frequency on meaningful words
        stop_words = {
            "the", "a", "an", "is", "it", "in", "on", "at", "to", "for",
            "and", "or", "but", "i", "me", "my", "we", "you", "he", "she",
            "they", "it", "was", "are", "be", "been", "have", "had", "do",
            "did", "will", "would", "could", "should", "this", "that"
        }
        words = re.findall(r"\b[a-zA-Z]{4,}\b", text.lower())
        freq: dict[str, int] = {}
        for w in words:
            if w not in stop_words:
                freq[w] = freq.get(w, 0) + 1
        top_words = sorted(freq.items(), key=lambda x: x[1], reverse=True)[:5]
        keywords.extend([w for w, _ in top_words if w not in keywords])

    # Deduplicate and limit
    seen = set()
    result = []
    for kw in keywords:
        if kw not in seen:
            seen.add(kw)
            result.append(kw)
    return result[:max_keywords]


def detect_crisis(text: str) -> bool:
    """Return True if crisis/self-harm keywords are detected."""
    text_lower = text.lower()
    return any(kw in text_lower for kw in _CRISIS_KEYWORDS)


def is_harmful_content(text: str) -> tuple[bool, str | None]:
    """
    Check if text contains harmful/abusive content for peer moderation.
    Returns (is_harmful, reason_string)
    """
    text_lower = text.lower()
    for kw in _HARMFUL_KEYWORDS:
        if kw in text_lower:
            return True, f"Contains inappropriate language: '{kw}'"
    if detect_crisis(text):
        return True, "Possible crisis content detected"
    return False, None


def full_nlp_analysis(text: str) -> dict[str, Any]:
    """
    Run complete NLP pipeline on a text: sentiment + emotion + keywords.
    """
    word_count = len(text.split()) if text else 0

    sentiment = analyze_sentiment(text)
    emotion = detect_emotion(text)
    keywords = extract_keywords(text)
    crisis = detect_crisis(text)

    # Readability heuristic
    avg_word_len = sum(len(w) for w in text.split()) / max(word_count, 1)
    if word_count < 30 or avg_word_len < 4.5:
        readability = "simple"
    elif word_count < 100 or avg_word_len < 5.5:
        readability = "moderate"
    else:
        readability = "complex"

    return {
        "sentiment_score": sentiment["compound"],
        "sentiment_label": sentiment["label"],
        "emotion_label": emotion,
        "keywords": keywords,
        "themes": keywords[:5],  # top 5 as "themes"
        "word_count": word_count,
        "readability": readability,
        "is_crisis": crisis,
        "raw_sentiment": sentiment,
    }
