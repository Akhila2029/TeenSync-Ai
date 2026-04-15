"""
Chatbot Service – RAG-Augmented Empathetic AI Response Generation.

Updated pipeline (6 steps):
  Step 1: Analyze user input (NLP: emotion, sentiment)        [EXISTING]
  Step 2: Crisis check → return immediate safety response     [EXISTING – highest priority]
  Step 3: Retrieve relevant documents via RAG (FAISS)         [NEW]
  Step 4: Construct enhanced, mental-health-safe LLM prompt   [NEW]
  Step 5: Generate response with OpenAI or Gemini             [EXISTING + RAG-augmented]
  Step 6: Rule-based empathetic fallback if LLM unavailable   [EXISTING]

All existing features are preserved:
  ✅ Emotion detection       ✅ Sentiment analysis
  ✅ Crisis detection        ✅ Rule-based fallback
  ✅ Helpline resources      ✅ OpenAI + Gemini integration

New additions:
  🆕 RAG retrieval (FAISS similarity search)
  🆕 Source document citations in response
  🆕 Conversation memory (last 3 turns for context)
  🆕 rag_used flag in response
"""
import logging
import random
from typing import Any

import httpx

from app.config import settings
from app.services.nlp_service import analyze_sentiment, detect_crisis, detect_emotion
from app.services.rag_service import retrieve_context

logger = logging.getLogger(__name__)

# ── Crisis Resources ──────────────────────────────────────────────────────────
CRISIS_RESOURCES = [
    "🆘 iCall India: 9152987821 (Mon-Sat, 8am-10pm)",
    "🆘 Vandrevala Foundation: 1860-2662-345 (24/7)",
    "🆘 iChalk: www.ichalk.in",
    "💙 You are not alone. Please reach out to a trusted adult or counselor.",
]

CRISIS_RESPONSE = (
    "I hear you, and I want you to know that what you're feeling matters deeply. "
    "You don't have to face this alone. Please reach out to a professional right away — "
    "your feelings are valid, and help is available. 💙\n\n"
    "Here are some immediate resources:"
)

# ── Safety System Prompt ──────────────────────────────────────────────────────
_SAFETY_SYSTEM_PROMPT = (
    "You are Luna, a warm and supportive mental health companion for teenagers. "
    "Your role is to listen empathetically, validate feelings, and gently guide "
    "teens toward healthy coping strategies. "
    "Rules you MUST follow:\n"
    "- Be empathetic, non-judgmental, and warm at all times\n"
    "- Never provide medical diagnoses or specific medical advice\n"
    "- Never suggest harmful actions under any circumstances\n"
    "- Keep responses concise (under 150 words) and human-like\n"
    "- Use emojis sparingly for warmth (1–2 per response at most)\n"
    "- Always acknowledge the user's feelings before offering suggestions\n"
    "- If the user seems severely distressed, gently suggest speaking to a trusted adult or counselor\n"
    "- Cite relevant coping techniques from the provided context when helpful"
)

# ── Emotion-based Response Templates ─────────────────────────────────────────
_TEMPLATES: dict[str, list[str]] = {
    "happy": [
        "That's wonderful to hear! 🌟 Your happiness is contagious. Keep holding onto this feeling — you deserve it.",
        "I love seeing you in a good place! 😊 What's been bringing you this joy? I'd love to know more.",
        "This makes me so happy for you! 🎉 Moments like these are worth cherishing.",
    ],
    "sad": [
        "I'm really sorry you're feeling this way 💙. It's okay to feel sad — your feelings are completely valid. Would you like to talk about what's been going on?",
        "Sadness can feel so heavy. I'm here with you right now. You don't have to go through this alone. 💙",
        "Thank you for sharing this with me. It takes courage to acknowledge when we're hurting. What's been weighing on your heart?",
    ],
    "anxious": [
        "Anxiety can feel overwhelming, but you're doing so well by acknowledging it. 💜 Let's try this: take a slow breath in for 4 counts... hold for 4... and out for 4. How does that feel?",
        "I understand — those anxious feelings can be really intense. You're not alone in this. What's been on your mind most lately?",
        "It sounds like your mind is working overtime right now. That's completely normal. Want to try a quick grounding exercise together? 🌿",
    ],
    "angry": [
        "I hear you, and it's completely okay to feel angry sometimes. 🔥 Your feelings are valid. What happened that made you feel this way?",
        "Anger is a signal that something important to you has been affected. Take a breath — I'm here to listen without judgment.",
        "That sounds really frustrating. Want to talk through it? Sometimes just naming what made us angry helps release some of that tension.",
    ],
    "stressed": [
        "It sounds like you're carrying a lot right now. 💙 Remember: you don't have to do everything at once. What feels most urgent to you?",
        "Stress is your mind's way of saying 'this matters to me' — but you also need rest. Let's talk about what's piling up and maybe break it down together.",
        "I can feel the pressure you're under. One thing at a time — that's how we get through tough periods. What's one small thing you could set aside today?",
    ],
    "hopeful": [
        "That hopeful spark is beautiful! 🌱 Hold onto it — hope is one of the most powerful things we carry. What are you looking forward to?",
        "Hope is so important, and I'm glad you're feeling it. What's been shifting things in a better direction for you?",
        "That's a really positive outlook, and it shows real strength. Keep nurturing that feeling! 🌻",
    ],
    "neutral": [
        "I'm here and listening. How has your day been going?",
        "Thanks for checking in. What's on your mind today? I'm all ears. 💙",
        "I'm glad you're here. Whether something's bothering you or you just wanted to talk, I've got time for you.",
    ],
}

_FOLLOW_UP_QUESTIONS: dict[str, list[str]] = {
    "sad": ["Would it help to journal about this feeling?", "Is there someone you trust you could talk to today?"],
    "anxious": ["Have you tried any breathing exercises?", "What usually helps you feel calmer?"],
    "stressed": ["What's one task you could delegate or postpone?", "When did you last take a proper break?"],
    "angry": ["What do you need right now to feel better?", "Would some physical movement help release this?"],
    "happy": ["What's one thing you're grateful for today?"],
    "hopeful": ["What's your next small step?"],
    "neutral": ["Is there something specific you'd like to explore today?"],
}


# ── Rule-based Response (Step 6 fallback) ─────────────────────────────────────

def _get_rule_based_response(emotion: str, user_text: str, history: list[dict]) -> str:
    """Generate an empathetic rule-based response. Used when LLM is unavailable."""
    templates = _TEMPLATES.get(emotion, _TEMPLATES["neutral"])
    response = random.choice(templates)

    # Occasionally add a follow-up question
    follow_ups = _FOLLOW_UP_QUESTIONS.get(emotion, [])
    if follow_ups and random.random() > 0.4:
        response += f"\n\n{random.choice(follow_ups)}"

    return response


# ── RAG Prompt Builder (Step 4) ────────────────────────────────────────────────

def _build_rag_prompt(
    user_text: str,
    emotion: str,
    context_docs: list[dict],
    history: list[dict],
) -> str:
    """
    Construct a mental-health-safe, context-enriched prompt for the LLM.

    Combines:
      - System safety instructions
      - Retrieved RAG context (top document chunks)
      - Conversation memory (last 3 messages)
      - Detected emotion
      - User's current message
    """
    # Format retrieved context
    if context_docs:
        context_parts = []
        for i, doc in enumerate(context_docs, 1):
            topic = doc.get("topic", doc.get("source", "mental health"))
            excerpt = doc.get("content", "")[:600]  # Truncate to keep prompt manageable
            context_parts.append(f"[Source {i} – {topic}]\n{excerpt}")
        context_block = "\n\n".join(context_parts)
    else:
        context_block = "No specific context retrieved."

    # Format conversation memory (last 3 turns)
    memory_parts = []
    for msg in history[-6:]:  # Last 3 turns = 6 messages (user + assistant)
        role_label = "User" if msg.get("role") == "user" else "Luna"
        memory_parts.append(f"{role_label}: {msg.get('content', '')}")
    memory_block = "\n".join(memory_parts) if memory_parts else "No prior conversation."

    prompt = (
        f"--- RELEVANT MENTAL HEALTH CONTEXT ---\n"
        f"{context_block}\n\n"
        f"--- RECENT CONVERSATION ---\n"
        f"{memory_block}\n\n"
        f"--- CURRENT SITUATION ---\n"
        f"User's message: \"{user_text}\"\n"
        f"(NLP Context Only: detected user emotion is {emotion})\n\n"
        f"--- YOUR RESPONSE (as Luna) ---\n"
        f"IMPORTANT: Respond directly to the user's message above. "
        f"If the user asks for tips, techniques, or has a specific question, you MUST provide a detailed, helpful answer using the context provided. "
        f"Do not just acknowledge feelings. Be empathetic, concise, and offer actionable support. "
        f"End with an open, caring question."
    )
    return prompt


# ── OpenAI Integration (Step 5a) ───────────────────────────────────────────────

async def _get_openai_response(
    user_text: str,
    emotion: str,
    history: list[dict],
    context_docs: list[dict],
) -> str:
    """Call OpenAI API with RAG-augmented prompt."""
    augmented_user_prompt = _build_rag_prompt(user_text, emotion, context_docs, history)

    messages = [
        {"role": "system", "content": _SAFETY_SYSTEM_PROMPT},
        {"role": "user", "content": augmented_user_prompt},
    ]

    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.post(
            "https://api.openai.com/v1/chat/completions",
            headers={"Authorization": f"Bearer {settings.openai_api_key}"},
            json={
                "model": settings.openai_model,
                "messages": messages,
                "max_tokens": 250,
                "temperature": 0.75,
            },
        )
        resp.raise_for_status()
        data = resp.json()
        return data["choices"][0]["message"]["content"].strip()


# ── Gemini Integration (Step 5b) ───────────────────────────────────────────────

async def _get_gemini_response(
    user_text: str,
    emotion: str,
    history: list[dict],
    context_docs: list[dict],
) -> str:
    """Call Google Gemini API with RAG-augmented prompt."""
    augmented_prompt = (
        f"{_SAFETY_SYSTEM_PROMPT}\n\n"
        + _build_rag_prompt(user_text, emotion, context_docs, history)
    )

    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.post(
            f"https://generativelanguage.googleapis.com/v1beta/models/{settings.gemini_model}:generateContent",
            params={"key": settings.gemini_api_key},
            json={"contents": [{"parts": [{"text": augmented_prompt}]}]},
        )
        resp.raise_for_status()
        data = resp.json()
        return data["candidates"][0]["content"]["parts"][0]["text"].strip()


# ── Ollama Integration (Step 5c) ───────────────────────────────────────────────

async def _get_ollama_response(
    user_text: str,
    emotion: str,
    history: list[dict],
    context_docs: list[dict],
) -> str:
    """Call local Ollama API with RAG-augmented prompt."""
    augmented_prompt = _build_rag_prompt(user_text, emotion, context_docs, history)
    
    async with httpx.AsyncClient(timeout=180.0) as client:
        resp = await client.post(
            f"{settings.ollama_url}/api/chat",
            json={
                "model": settings.ollama_model,
                "messages": [
                    {"role": "system", "content": _SAFETY_SYSTEM_PROMPT},
                    {"role": "user", "content": augmented_prompt}
                ],
                "stream": False,
                "options": {
                    "temperature": 0.75,
                    "num_ctx": 2048
                }
            },
        )
        resp.raise_for_status()
        data = resp.json()
        return data["message"]["content"].strip()


# ── Main Response Generator ────────────────────────────────────────────────────

async def generate_response(
    user_text: str,
    conversation_history: list[dict[str, str]],
) -> dict[str, Any]:
    """
    Main chatbot response generator — RAG-augmented pipeline.

    Returns a dict with:
        response        : str  — the assistant's reply
        emotion_detected: str  — detected emotion label
        sentiment_score : float — VADER compound score (-1 to +1)
        is_crisis       : bool — True if crisis keywords detected
        resources       : list[str] | None — crisis resources if needed
        source_docs     : list[dict] — retrieved RAG document sources
        rag_used        : bool — whether RAG retrieval was performed
        confidence      : str  — qualitative confidence level
    """

    # ── Step 1: NLP Analysis (EXISTING) ──────────────────────────────────────
    sentiment = analyze_sentiment(user_text)
    emotion = detect_emotion(user_text)
    is_crisis = detect_crisis(user_text)

    # ── Step 2: Crisis Check (EXISTING – HIGHEST PRIORITY) ───────────────────
    # If crisis signals detected, skip RAG entirely and return immediate help
    if is_crisis:
        logger.warning("Crisis detected in user message. Returning safety response.")
        return {
            "response": CRISIS_RESPONSE,
            "emotion_detected": "crisis",
            "sentiment_score": sentiment["compound"],
            "is_crisis": True,
            "resources": CRISIS_RESOURCES,
            "source_docs": [],
            "rag_used": False,
            "confidence": "high",
        }

    # ── Step 3: RAG Retrieval (NEW) ───────────────────────────────────────────
    # Retrieve top-4 most relevant mental health document chunks
    context_docs: list[dict] = []
    rag_used = False
    try:
        context_docs = retrieve_context(user_text, top_k=4)
        rag_used = len(context_docs) > 0
        if rag_used:
            logger.debug("RAG retrieved %d chunks.", len(context_docs))
    except Exception as exc:
        logger.warning("RAG retrieval failed (non-fatal): %s", exc)
        context_docs = []

    # Trim context for response metadata (only return source name + topic)
    source_docs = [
        {"source": d.get("source", ""), "topic": d.get("topic", "")}
        for d in context_docs
    ]

    # ── Steps 4 + 5: Build Prompt & Call LLM ─────────────────────────────────
    ai_response: str | None = None

    if settings.has_openai:
        try:
            ai_response = await _get_openai_response(
                user_text, emotion, conversation_history, context_docs
            )
            logger.debug("OpenAI response generated (RAG=%s).", rag_used)
        except Exception as exc:
            logger.warning("OpenAI call failed: %s", exc)
            ai_response = None

    if ai_response is None and settings.has_gemini:
        try:
            ai_response = await _get_gemini_response(
                user_text, emotion, conversation_history, context_docs
            )
            logger.debug("Gemini response generated (RAG=%s).", rag_used)
        except Exception as exc:
            logger.warning("Gemini call failed: %s", exc)
            ai_response = None

    if ai_response is None:
        try:
            ai_response = await _get_ollama_response(
                user_text, emotion, conversation_history, context_docs
            )
            logger.debug("Ollama response generated (RAG=%s).", rag_used)
        except Exception as exc:
            logger.warning("Ollama call failed: %s", exc)
            ai_response = None

    # ── Step 6: Rule-based Fallback (EXISTING) ────────────────────────────────
    if ai_response is None:
        ai_response = _get_rule_based_response(emotion, user_text, conversation_history)
        logger.debug("Using rule-based fallback response (emotion=%s).", emotion)

    # ── Determine confidence level ────────────────────────────────────────────
    abs_compound = abs(sentiment["compound"])
    if abs_compound > 0.5:
        confidence = "high"
    elif abs_compound > 0.2:
        confidence = "medium"
    else:
        confidence = "low"

    return {
        "response": ai_response,
        "emotion_detected": emotion,
        "sentiment_score": sentiment["compound"],
        "is_crisis": False,
        "resources": None,
        "source_docs": source_docs,
        "rag_used": rag_used,
        "confidence": confidence,
    }
