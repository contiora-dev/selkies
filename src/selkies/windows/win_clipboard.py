import logging
import threading

logger = logging.getLogger("win_clipboard")

_clipboard_lock = threading.Lock()

def get_clipboard_text():
    try:
        import pyperclip
        return pyperclip.paste()
    except Exception as e:
        logger.error(f"Error reading clipboard: {e}")
        return None

def set_clipboard_text(text):
    try:
        import pyperclip
        pyperclip.copy(text)
        return True
    except Exception as e:
        logger.error(f"Error writing clipboard: {e}")
        return False

def get_clipboard_data():
    text = get_clipboard_text()
    if text:
        return text, "text/plain"
    return None, None
