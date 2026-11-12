import unicodedata

# Each spelling is an explicit equivalence; descriptions remain significant.
ALIASES = {
    "tomates": "tomate",
    "tomato": "tomate",
    "tomatoes": "tomate",
    "huevos": "huevo",
    "egg": "huevo",
    "eggs": "huevo",
    "patatas": "patata",
    "potato": "patata",
    "potatoes": "patata",
}


def normalize_ingredient(name: str) -> str:
    decomposed = unicodedata.normalize("NFD", name.casefold())
    without_accents = "".join(character for character in decomposed if not unicodedata.combining(character))
    normalized = " ".join(without_accents.split())
    return ALIASES.get(normalized, normalized)
