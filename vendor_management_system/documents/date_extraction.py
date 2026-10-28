"""Lettura automatica delle date di rilascio/scadenza da un documento.

Il file viene letto con Tesseract (OCR, lingua italiana): i PDF sono prima
resi in immagini con pypdfium2. Il risultato è solo un suggerimento per
pre-compilare i campi, che il fornitore resta libero di cambiare.
"""

import io
import logging
import re
from datetime import date

logger = logging.getLogger(__name__)

# Pagine PDF lette: scadenza ed emissione stanno quasi sempre all'inizio.
MAX_PAGES = 3
OCR_LANG = "ita"
MAX_FILE_SIZE = 20 * 1024 * 1024  # come il limite dei form di upload
OCR_SCALE = 2  # 2x ≈ 144 dpi, sufficiente per testo a corpo normale

MESI = {
    "gennaio": 1,
    "febbraio": 2,
    "marzo": 3,
    "aprile": 4,
    "maggio": 5,
    "giugno": 6,
    "luglio": 7,
    "agosto": 8,
    "settembre": 9,
    "ottobre": 10,
    "novembre": 11,
    "dicembre": 12,
}

_DATA_NUMERICA = r"(\d{1,2})\s*[/.\-]\s*(\d{1,2})\s*[/.\-]\s*(\d{4}|\d{2})"
_DATA_ESTESA = r"(\d{1,2})\s+(" + "|".join(MESI) + r")\s+(\d{4})"
_DATA = rf"(?:{_DATA_NUMERICA}|{_DATA_ESTESA})"

# La data deve seguire la parola chiave entro pochi caratteri sulla stessa
# riga o su quella successiva (l'OCR spesso spezza "etichetta: valore").
_KEYWORD_SCADENZA = (
    r"(?:scadenza|scade|valid[oa]\s+(?:fino|sino)\s+al|valid[oa]\s+al"
    r"|data\s+di\s+scadenza|validit[àa]\s+fino)"
)
_KEYWORD_EMISSIONE = (
    r"(?:data\s+di\s+(?:emissione|rilascio|decorrenza)|emess[oa]\s+il"
    r"|rilasciat[oa]\s+il|data\s+emissione|decorrenza|stipulat[oa]\s+il)"
)


def _build_date(giorno, mese, anno):
    anno = int(anno)
    if anno < 100:
        anno += 2000
    try:
        return date(anno, int(mese), int(giorno))
    except ValueError:
        return None


def _parse_match(match):
    """Converte un match di `_DATA` (numerica o estesa) in `date`."""
    g = match.groups()
    if g[0] is not None:
        return _build_date(g[0], g[1], g[2])
    return _build_date(g[3], MESI[g[4]], g[5])


def _first_date_after(keyword_pattern, text):
    pattern = re.compile(
        keyword_pattern + r"[^\d\n]{0,25}\n?[^\d\n]{0,10}" + _DATA,
        re.IGNORECASE,
    )
    for match in pattern.finditer(text):
        # Il gruppo della keyword non cattura: i gruppi sono quelli di _DATA.
        parsed = _parse_match(match)
        if parsed:
            return parsed
    return None


def extract_dates_from_text(text):
    """Cerca data di rilascio e di scadenza in un testo già letto.

    Ritorna {"issue_date": date|None, "expiry_date": date|None}. Se la
    scadenza risulta precedente al rilascio le due date sono considerate
    inaffidabili e scartate.
    """
    issue = _first_date_after(_KEYWORD_EMISSIONE, text or "")
    expiry = _first_date_after(_KEYWORD_SCADENZA, text or "")
    if issue and expiry and expiry < issue:
        return {"issue_date": None, "expiry_date": None}
    return {"issue_date": issue, "expiry_date": expiry}


def _images_from_file(file_obj, filename):
    """Immagini PIL (max MAX_PAGES) dal file caricato: PDF o immagine."""
    from PIL import Image

    content = file_obj.read()
    if (filename or "").lower().endswith(".pdf") or content[:4] == b"%PDF":
        import pypdfium2

        pdf = pypdfium2.PdfDocument(content)
        try:
            for index in range(min(len(pdf), MAX_PAGES)):
                yield pdf[index].render(scale=OCR_SCALE).to_pil()
        finally:
            pdf.close()
    else:
        yield Image.open(io.BytesIO(content))


def read_text(file_obj, filename=""):
    """Testo OCR del file; stringa vuota se Tesseract non è disponibile o il
    file non è leggibile (il suggerimento delle date è facoltativo)."""
    try:
        import pytesseract

        return "\n".join(
            pytesseract.image_to_string(image, lang=OCR_LANG)
            for image in _images_from_file(file_obj, filename)
        )
    except Exception:
        logger.warning("OCR date non riuscito per %s", filename, exc_info=True)
        return ""


def extract_dates(file_obj, filename=""):
    """Date suggerite per un file caricato (vedi `extract_dates_from_text`)."""
    return extract_dates_from_text(read_text(file_obj, filename))


def suggested_dates(upload):
    """Date suggerite in formato ISO (o None) per un file ricevuto da una
    view; file assente o troppo grande restituiscono solo valori vuoti.
    Condivisa dagli endpoint del portale e dell'admin."""
    dates = {"issue_date": None, "expiry_date": None}
    if upload and upload.size <= MAX_FILE_SIZE:
        found = extract_dates(upload, upload.name)
        dates = {k: v.isoformat() if v else None for k, v in found.items()}
    return dates
