import unicodedata
from typing import Literal, Annotated
from pydantic import Field, BaseModel
from src.models.cantons import Cantons

DATA = (
    ("ZH", "Zürich", "Zürich", ("de",)),
    ("BE", "Bern / Berne", "Bern", ("de", "fr")),
    ("LU", "Luzern", "Luzern", ("de",)),
    ("UR", "Uri", "Altdorf", ("de",)),
    ("SZ", "Schwyz", "Schwyz", ("de",)),
    ("OW", "Obwalden", "Sarnen", ("de",)),
    ("NW", "Nidwalden", "Stans", ("de",)),
    ("GL", "Glarus", "Glarus", ("de",)),
    ("ZG", "Zug", "Zug", ("de",)),
    ("FR", "Fribourg / Freiburg", "Fribourg", ("fr", "de")),
    ("SO", "Solothurn", "Solothurn", ("de",)),
    ("BS", "Basel-Stadt", "Basel", ("de",)),
    ("BL", "Basel-Landschaft", "Liestal", ("de",)),
    ("SH", "Schaffhausen", "Schaffhausen", ("de",)),
    ("AR", "Appenzell Ausserrhoden", "Herisau", ("de",)),
    ("AI", "Appenzell Innerrhoden", "Appenzell", ("de",)),
    ("SG", "St. Gallen", "St. Gallen", ("de",)),
    ("GR", "Graubünden / Grigioni / Grischun", "Chur", ("de", "it", "rm")),
    ("AG", "Aargau", "Aarau", ("de",)),
    ("TG", "Thurgau", "Frauenfeld", ("de",)),
    ("TI", "Ticino", "Bellinzona", ("it",)),
    ("VD", "Vaud", "Lausanne", ("fr",)),
    ("VS", "Valais / Wallis", "Sion", ("fr", "de")),
    ("NE", "Neuchâtel", "Neuchâtel", ("fr",)),
    ("GE", "Genève", "Genève", ("fr",)),
    ("JU", "Jura", "Delémont", ("fr",)),
)


class Canton(BaseModel):
    """Basic reference information about a Swiss canton."""

    # Canton identity and administrative information.
    code: Cantons
    name: str
    capital: str
    languages: tuple[Literal["de", "fr", "it", "rm"], ...]


class CantonResults(BaseModel):
    """Matching cantons with their reference source."""

    # Reference records and provenance.
    items: list[Canton]
    source: str = "https://en.wikipedia.org/wiki/Cantons_of_Switzerland#List"


async def cantons(query: Annotated[str, Field(max_length=100)] = "") -> CantonResults:
    """List all 26 Swiss cantons or search by code, native/English name, or capital.

    Search is case- and accent-insensitive. Returns official language codes and
    administrative capitals (Herisau for Appenzell Ausserrhoden).
    An exact canton code returns only that canton, before considering partial names.
    """

    # Normalize accents, punctuation, and case for reference lookups.
    normalized = unicodedata.normalize("NFKD", query).casefold()
    query = "".join(character for character in normalized if character.isalnum())

    # Match both native names and the existing English canton identifiers.
    items = []
    for code, name, capital, languages in DATA:
        canton = Canton.model_validate({"code": code, "name": name, "capital": capital, "languages": languages})
        if query == code.casefold():
            return CantonResults(items=[canton])
        normalized = unicodedata.normalize("NFKD", f"{code} {name} {capital} {canton.code.name}").casefold()
        searchable = "".join(character for character in normalized if character.isalnum())
        if query in searchable:
            items.append(canton)
    return CantonResults(items=items)
