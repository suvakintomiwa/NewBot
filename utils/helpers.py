def clean_text(text: str) -> str:
    return text.strip().replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
