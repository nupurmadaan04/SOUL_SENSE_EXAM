def get_welcome(settings) -> str:
    if settings and getattr(settings, "welcome_message", None):
        return settings.welcome_message
    return "Welcome!"
