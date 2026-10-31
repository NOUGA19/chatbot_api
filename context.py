"""Récupération du contexte. Aujourd'hui : tout le fichier (4 procédures = ~2 000 tokens).
Si le corpus grossit, seule cette fonction change (recherche vectorielle / RAG)."""
from pathlib import Path

PROCEDURES_FILE = Path(__file__).parent / "procedures.md"


def get_context(question: str = "") -> str:
    return PROCEDURES_FILE.read_text(encoding="utf-8")
