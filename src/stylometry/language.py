"""Per-language settings: spaCy model, word lists for the heuristics, quote and dash conventions."""
import re

from spacy.lang.de.stop_words import STOP_WORDS as _DE_STOP
from spacy.lang.en.stop_words import STOP_WORDS as _EN_STOP

# Quotes open and close with different marks; English uses “ ” («» for French-style translations),
# German „ “ and the reversed guillemets » «.
LANGUAGES = {
    "en": {
        "name": "English",
        "model": "en_core_web_sm",
        "hedge": {"might", "perhaps", "maybe", "possibly", "could", "seem", "seems", "somewhat", "arguably"},
        "assertive": {"must", "always", "never", "certainly", "clearly", "obviously", "definitely"},
        "pronouns": {
            "first_person": {"i", "me", "my", "mine", "myself", "we", "us", "our", "ours", "ourselves"},
            "second_person": {"you", "your", "yours", "yourself", "yourselves",
                              "thou", "thee", "thy", "thine", "thyself", "ye"},
            "third_person": {"he", "him", "his", "himself", "she", "her", "hers", "herself",
                             "they", "them", "their", "theirs", "themselves"},
            "impersonal": {"it", "its", "itself"},
        },
        "open_quotes": {"“", "«"},
        "close_quotes": {"”", "»"},
        "em_dash": r"—|--",
        "conjunction": "and|or",
    },
    "de": {
        "name": "German",
        "model": "de_core_news_sm",
        "hedge": {"vielleicht", "möglicherweise", "eventuell", "wohl", "anscheinend", "scheinbar",
                  "gewissermaßen", "könnte", "könnten", "dürfte", "scheint", "scheinen", "vermutlich",
                  "wahrscheinlich"},
        "assertive": {"muss", "müssen", "immer", "nie", "niemals", "sicher", "gewiss", "zweifellos",
                      "offensichtlich", "bestimmt", "unbedingt"},
        # ponytail: the polite "Sie" and the plural "ihr" collide with third-person "sie"/"ihr",
        # and the possessive "sein" with the infinitive, so all three are counted as third person (or not at all).
        # Only the du/euch forms count as second person; add a parse-based rule if that matters.
        "pronouns": {
            "first_person": {"ich", "mich", "mir", "mein", "meine", "meinen", "meinem", "meiner", "meines",
                             "wir", "uns", "unser", "unsere", "unseren", "unserem", "unserer", "unseres"},
            "second_person": {"du", "dich", "dir", "dein", "deine", "deinen", "deinem", "deiner", "deines",
                              "euch", "euer", "eure", "euren", "eurem", "eurer", "eures"},
            "third_person": {"er", "ihn", "ihm", "seine", "seinen", "seinem", "seiner", "seines",
                             "sie", "ihr", "ihre", "ihren", "ihrem", "ihrer", "ihres", "ihnen", "sich"},
            "impersonal": {"es"},
        },
        "open_quotes": {"„", "»", "‚"},
        "close_quotes": {"“", "«", "‘"},
        # German sets a spaced en dash as the dash
        "em_dash": r"—|--|\s–\s",
        "conjunction": "und|oder",
    },
}

_WORD = re.compile(r"[^\W\d_]+")
_SAMPLE_CHARS = 20_000
# words both languages share ("in", "was", "an", "so", ...) say nothing about which one it is
_EN_ONLY = {w for w in _EN_STOP if w.isalpha()} - set(_DE_STOP)
_DE_ONLY = {w for w in _DE_STOP if w.isalpha()} - set(_EN_STOP)


def detect(text: str) -> str:
    """Pick the language whose stop words occur more often in the start of the text; English on a tie."""
    words = _WORD.findall(text[:_SAMPLE_CHARS].lower())
    en = sum(w in _EN_ONLY for w in words)
    de = sum(w in _DE_ONLY for w in words)
    return "de" if de > en else "en"


def resolve(lang: str, text: str) -> str:
    return detect(text) if lang == "auto" else lang
