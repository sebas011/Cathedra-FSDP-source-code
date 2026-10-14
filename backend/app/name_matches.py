import unicodedata
from difflib import SequenceMatcher


def name_key(name: str) -> str:
    text = unicodedata.normalize("NFKD", name.casefold())
    return " ".join("".join(character if character.isalnum() else " "
                            for character in text if not unicodedata.combining(character)).split())


def name_similarity(candidate: str, existing: str) -> tuple[float, str]:
    candidate_key, existing_key = name_key(candidate), name_key(existing)
    if not candidate_key or not existing_key:
        return 0, ""
    if candidate_key == existing_key:
        return 1, "Same name after punctuation and accent normalization"
    if sorted(candidate_key.split()) == sorted(existing_key.split()):
        return 0.99, "Same name words in a different order"
    score = SequenceMatcher(None, candidate_key, existing_key, autojunk=False).ratio()
    return (score, "Similar spelling") if score >= 0.86 else (0, "")
