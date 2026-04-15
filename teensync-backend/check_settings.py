from app.config import settings
print(f"Gemini API Key defined: {bool(settings.gemini_api_key)}")
print(f"Gemini API Key value starts with: {settings.gemini_api_key[:5] if settings.gemini_api_key else 'None'}")
