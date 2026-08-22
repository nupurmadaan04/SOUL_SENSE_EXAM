ADVICE_TONES = {
    "professional": {"name": "Professional", "description": "Formal, evidence-based"},
    "friendly": {"name": "Friendly", "description": "Warm, conversational"},
    "direct": {"name": "Direct", "description": "Straightforward, concise"},
    "empathetic": {"name": "Empathetic", "description": "Compassionate, understanding"}
}

ADVICE_LANGUAGES = {"en": "English", "hi": "हिंदी", "es": "Español"}

def get_advice_template(tone, language="en"):
    templates = {
        "professional": {"en": "Based on assessment: {advice}", "hi": "मूल्यांकन के आधार पर: {advice}", "es": "Según evaluación: {advice}"},
        "friendly": {"en": "Here's what might help: {advice}", "hi": "यह मदद कर सकता है: {advice}", "es": "Esto podría ayudar: {advice}"},
        "direct": {"en": "Action: {advice}", "hi": "कार्रवाई: {advice}", "es": "Acción: {advice}"},
        "empathetic": {"en": "We understand. Consider: {advice}", "hi": "हम समझते हैं। विचार करें: {advice}", "es": "Entendemos. Considera: {advice}"}
    }
    return templates.get(tone, templates["friendly"]).get(language, templates[tone]["en"])
