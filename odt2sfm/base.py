import unicodedata
from datetime import datetime

SFM_PLACEHOLDERS = {
    "~": "\u00a0",
}


def get_timestamp():
    return datetime.today().strftime("%Y-%m-%d")


def normalize_text(normalization_form, text):
    return unicodedata.normalize(normalization_form, text)


def do_paratext_replacements(text):
    for sfm_str, odt_str in SFM_PLACEHOLDERS.items():
        text = text.replace(odt_str, sfm_str)
    return text


def undo_paratext_replacements(text):
    for sfm_str, odt_str in SFM_PLACEHOLDERS.items():
        text = text.replace(sfm_str, odt_str)
    return text
