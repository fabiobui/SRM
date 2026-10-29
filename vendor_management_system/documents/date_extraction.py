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
MAX_NATIVE_PAGES = 100  # PDF digitali: nessun costo OCR, si legge tutto
OCR_LANG = "ita"
MAX_FILE_SIZE = 20 * 1024 * 1024  # come il limite dei form di upload
OCR_SCALE = 2  # 2x ≈ 144 dpi: compromesso tra precisione e tempi di risposta
# Sotto questa soglia il PDF è considerato una scansione (senza testo utile)
MIN_NATIVE_CHARS = 50

MESI = {
    "gennaio": 1,
    "gen": 1,
    "febbraio": 2,
    "feb": 2,
    "marzo": 3,
    "mar": 3,
    "aprile": 4,
    "apr": 4,
    "maggio": 5,
    "mag": 5,
    "giugno": 6,
    "giu": 6,
    "luglio": 7,
    "lug": 7,
    "agosto": 8,
    "ago": 8,
    "settembre": 9,
    "set": 9,
    "sett": 9,
    "ottobre": 10,
    "ott": 10,
    "novembre": 11,
    "nov": 11,
    "dicembre": 12,
    "dic": 12,
    # documenti in inglese
    "january": 1,
    "jan": 1,
    "february": 2,
    "march": 3,
    "april": 4,
    "may": 5,
    "june": 6,
    "jun": 6,
    "july": 7,
    "jul": 7,
    "august": 8,
    "aug": 8,
    "september": 9,
    "sep": 9,
    "october": 10,
    "oct": 10,
    "december": 12,
    "dec": 12,
}
_MESE = "|".join(sorted(MESI, key=len, reverse=True))

# Formati riconosciuti: 14/07/2020, 14.07.20, 14-07-2020, 2020-07-14,
# 14 luglio 2020, 1° gennaio 2020, 14-lug-2020, 14 July 2020.
_NUM = r"\d{1,2}\s*[/.\-]\s*\d{1,2}\s*[/.\-]\s*(?:\d{4}|\d{2})(?!\d)"
_ISO = r"\d{4}\s*[/.\-]\s*\d{1,2}\s*[/.\-]\s*\d{1,2}(?!\d)"
_ESTESA = rf"\d{{1,2}}\s*[°º]?[\s\-/.]*(?:{_MESE})\b\.?[\s\-/.,]*\d{{4}}(?!\d)"
_DATA = rf"(?<![\d/])(?:{_ISO}|{_NUM}|{_ESTESA})"

# La data deve seguire la parola chiave entro pochi caratteri sulla stessa
# riga o su quella successiva (l'OCR spesso spezza "etichetta: valore").
_GAP = r"[^\d\n]{0,30}(?:\n[^\d\n]{0,15}){0,2}"
# "dal" ma non "dalla/dallo": nel testo "dalla data di sottoscrizione" non
# c'è nessuna data subito dopo.
_DAL = r"(?:dal\b|dall['’])"

# Le diciture sono ordinate per affidabilità: vince la prima che trova una
# data valida. Solo gruppi non catturanti (la data è l'unico gruppo).
_EMISSIONE_FORTE = (
    r"(?:data\s+(?:di\s+)?(?:emissione|rilascio)|emess[oa](?:\s+a\s+\w+(?:\s+\w+)?)?"
    r"\s+(?:il|in\s+data)"
    r"|rilasciat[oa]\s+(?:il|in\s+data)|emissione|rilascio|issue\s+date"
    r"|date\s+of\s+issue|issued(?:\s+on)?)"
)
_EMISSIONE_VIGORE = (
    rf"(?:(?:in\s+vigore|con\s+decorrenza|a\s+decorrere|decorre|valid[oa]"
    rf"|efficace|vigente)\s+{_DAL}(?:\s+giorno)?|decorrenza)"
)
# Intestazione dei contratti: "N. 202014012 DEL 14/07/2020". Solo nella
# parte iniziale del testo e non per i riferimenti normativi.
_EMISSIONE_INTESTAZIONE = (
    r"\bn(?:\.|°|r\.?)?\s*[\w./-]*\d[\w./-]*\s+del(?:l['’])?"
)
_EMISSIONE_FIRMA = (
    r"(?:sottoscritt[oa]|stipulat[oa]|firmat[oa]|sottoscrizione|stipula|firma)"
    r"\s+(?:il|in\s+data|del|:)"
)
_SCADENZA_FORTE = (
    r"(?:data\s+(?:di\s+)?scadenza|scadenza|scad\.|scade|scadr[àa]"
    r"|expir(?:y|ation)(?:\s+date)?|expires?|valid\s+(?:until|to|through)"
    r"|valid[oa]\s+(?:fino|sino)\s+al|validit[àa]\s+(?:fino|sino)\s+al"
    r"|valid[oa]\s+al|valid[oa]\s+entro\s+il)"
)
_SCADENZA_DEBOLE = r"(?:fino|sino)\s+al"
# "Valido/in vigore/durata dal 01/01/2025 al 31/12/2025": entrambe le date
_PERIODO = re.compile(
    rf"(?:valid[oa]|validit[àa]|vigore|vigenza|efficac\w*|durata|periodo"
    rf"|decorrenza)[^\d]{{0,80}}?{_DAL}\s*({_DATA})\s*[,;]?\s*"
    rf"(?:fino\s+al|sino\s+al|al\b|a\b|-|–)\s*({_DATA})",
    re.IGNORECASE,
)
# Riferimenti normativi ("D.P.R. n. 177 del 2011") non sono date del documento
_NORMATIVA = re.compile(
    r"(?:d\.?\s?p\.?\s?r|d\.?\s?lgs|legge|decreto|d\.?\s?m|art|c\.?c)\W*$",
    re.IGNORECASE,
)
INTESTAZIONE_CHARS = 1500


def _to_date(token):
    """Converte il testo di una data in `date` (None se non plausibile)."""
    numeri = re.findall(r"\d+", token)
    parola = re.search(r"[A-Za-z]+", token)
    try:
        if parola:
            giorno, mese, anno = (
                int(numeri[0]),
                MESI[parola.group(0).lower()],
                int(numeri[-1]),
            )
        elif len(numeri[0]) == 4:
            anno, mese, giorno = (int(n) for n in numeri[:3])
        else:
            giorno, mese, anno = (int(n) for n in numeri[:3])
            if anno < 100:
                anno += 2000
        parsed = date(anno, mese, giorno)
    except (ValueError, IndexError, KeyError):
        return None
    # scarta numeri casuali letti come date (es. codici, protocolli)
    return parsed if 1990 <= parsed.year <= 2100 else None


def _dates_after(keyword_pattern, text, head_only=False):
    pattern = re.compile(
        keyword_pattern + _GAP + "(" + _DATA + ")", re.IGNORECASE
    )
    for match in pattern.finditer(text):
        if head_only:
            if match.start() > INTESTAZIONE_CHARS:
                break
            if _NORMATIVA.search(
                text[max(0, match.start() - 30) : match.start()]
            ):
                continue
        parsed = _to_date(match.group(1))
        if parsed:
            yield parsed


def _normalize(text):
    text = (text or "").replace("\r", "")
    return re.sub(r"[ \t\xa0]+", " ", text)


def extract_dates_from_text(text):
    """Cerca data di rilascio e di scadenza in un testo già letto.

    Ritorna {"issue_date": date|None, "expiry_date": date|None}. Le
    diciture sono provate per affidabilità decrescente; se nessuna coppia
    emissione/scadenza è coerente (scadenza non precedente all'emissione)
    le due date sono considerate inaffidabili e scartate.
    """
    text = _normalize(text)
    periodo = _PERIODO.search(text)
    inizio = fine = None
    if periodo:
        inizio, fine = _to_date(periodo.group(1)), _to_date(periodo.group(2))

    issue_candidates = [
        *_dates_after(_EMISSIONE_FORTE, text),
        *([inizio] if inizio else []),
        *_dates_after(_EMISSIONE_VIGORE, text),
        *_dates_after(_EMISSIONE_INTESTAZIONE, text, head_only=True),
        *_dates_after(_EMISSIONE_FIRMA, text),
    ]
    expiry_candidates = [
        *_dates_after(_SCADENZA_FORTE, text),
        *([fine] if fine else []),
        *_dates_after(_SCADENZA_DEBOLE, text),
    ]
    if not expiry_candidates:
        return {
            "issue_date": issue_candidates[0] if issue_candidates else None,
            "expiry_date": None,
        }
    if not issue_candidates:
        return {"issue_date": None, "expiry_date": expiry_candidates[0]}
    for issue in issue_candidates:
        for expiry in expiry_candidates:
            if expiry >= issue:
                return {"issue_date": issue, "expiry_date": expiry}
    return {"issue_date": None, "expiry_date": None}


def _is_pdf(content, filename):
    return (filename or "").lower().endswith(".pdf") or content[:4] == b"%PDF"


def _pdf_native_text(content):
    """Testo incorporato nel PDF (vuoto se scansione). Si leggono tutte le
    pagine: è quasi gratis e la scadenza di un contratto sta spesso
    nell'articolo "Durata", ben oltre le prime pagine."""
    import pypdfium2

    pdf = pypdfium2.PdfDocument(content)
    try:
        return "\n".join(
            pdf[index].get_textpage().get_text_range()
            for index in range(min(len(pdf), MAX_NATIVE_PAGES))
        )
    finally:
        pdf.close()


def _images_from_content(content, filename):
    """Immagini PIL (max MAX_PAGES) dal contenuto: PDF o immagine."""
    from PIL import Image

    if _is_pdf(content, filename):
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
    """Testo del file: quello incorporato nei PDF digitali, altrimenti OCR.

    Ritorna None se la lettura fallisce (Tesseract o lingua mancanti, file
    illeggibile), per distinguerlo da un documento senza testo ("")."""
    try:
        content = file_obj.read()
        if _is_pdf(content, filename):
            native = _pdf_native_text(content)
            if len(native.strip()) >= MIN_NATIVE_CHARS:
                return native
        import pytesseract

        return "\n".join(
            pytesseract.image_to_string(image, lang=OCR_LANG)
            for image in _images_from_content(content, filename)
        )
    except Exception:
        logger.warning("OCR date non riuscito per %s", filename, exc_info=True)
        return None


def extract_dates(file_obj, filename=""):
    """Date suggerite per un file caricato (vedi `extract_dates_from_text`).

    Se la lettura fallisce aggiunge `error`, così la UI può dirlo
    all'utente invece di mostrare "nessuna data"."""
    text = read_text(file_obj, filename)
    if text is None:
        return {
            "issue_date": None,
            "expiry_date": None,
            "error": "ocr_non_riuscito",
        }
    return extract_dates_from_text(text)


def suggested_dates(upload):
    """Date suggerite in formato ISO (o None) per un file ricevuto da una
    view; file assente o troppo grande restituiscono solo valori vuoti.
    Condivisa dagli endpoint del portale e dell'admin."""
    dates = {"issue_date": None, "expiry_date": None}
    if upload and upload.size <= MAX_FILE_SIZE:
        found = extract_dates(upload, upload.name)
        dates = {
            k: v.isoformat() if hasattr(v, "isoformat") else v
            for k, v in found.items()
        }
    return dates
