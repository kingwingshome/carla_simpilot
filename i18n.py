import json
import os


_current_language = "zh-CN"
_translations = {}
_listeners = []


def load_translations():
    global _translations
    base_dir = os.path.dirname(__file__)
    path = os.path.join(base_dir, "i18n.json")
    try:
        with open(path, "r", encoding="utf-8") as f:
            _translations = json.load(f)
    except Exception:
        _translations = {}


def set_language(lang):
    global _current_language
    _current_language = lang
    for callback in _listeners:
        callback(lang)


def get_language():
    return _current_language


def t(key):
    lang_dict = _translations.get(_current_language, {})
    return lang_dict.get(key, key)


def add_language_listener(callback):
    _listeners.append(callback)


load_translations()

