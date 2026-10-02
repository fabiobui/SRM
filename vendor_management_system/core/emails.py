"""Invio email del progetto.

Tutte le email applicative passano da `send_templated_email`, così il
dirottamento dei destinatari (`settings.EMAIL_REDIRECT_TO`, usato in
locale/test per non scrivere ai fornitori reali) vale ovunque senza doverlo
ripetere in ogni punto di invio.
"""

import logging
from email.message import MIMEPart
from email.mime.image import MIMEImage

import django
from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string

logger = logging.getLogger(__name__)

# Logo in fondo a tutte le email HTML, allegato inline (CID) e non come URL
# remoto: non dipende dagli static pubblicati e Outlook non lo blocca.
LOGO_PATH = settings.BASE_DIR / "static" / "img" / "fulgard-logo.jpg"
LOGO_CID = "fulgard-logo"


def _logo_image():
    """Parte MIME del logo, o None se il file non c'è (l'email parte senza)."""
    try:
        data = LOGO_PATH.read_bytes()
    except OSError:
        logger.warning("Logo email non trovato in %s", LOGO_PATH)
        return None
    if django.VERSION >= (6, 0):
        # Django 6 accetta solo MIMEPart come allegato già costruito.
        image = MIMEPart()
        image.set_content(
            data,
            maintype="image",
            subtype="jpeg",
            disposition="inline",
            filename=LOGO_PATH.name,
            cid=f"<{LOGO_CID}>",
        )
        return image
    image = MIMEImage(data, _subtype="jpeg")
    image.add_header("Content-ID", f"<{LOGO_CID}>")
    image.add_header("Content-Disposition", "inline", filename=LOGO_PATH.name)
    return image


def send_templated_email(*, subject, template_name, context, to):
    """Invia un'email testo + HTML resa da `emails/<template_name>.txt|.html`.

    Restituisce la lista dei destinatari effettivi (quelli di redirect, se
    attivo). Gli errori di invio NON vengono silenziati: li gestisce il
    chiamante, che sa come avvisare l'utente.
    """
    original_recipients = list(to)
    redirect_to = list(getattr(settings, "EMAIL_REDIRECT_TO", []) or [])
    recipients = redirect_to or original_recipients

    logo = _logo_image()
    context = {
        **context,
        "original_recipients": original_recipients if redirect_to else [],
        "logo_cid": LOGO_CID if logo else "",
    }
    if redirect_to:
        subject = f"[REDIRECT → {', '.join(original_recipients)}] {subject}"

    text_body = render_to_string(f"emails/{template_name}.txt", context)
    html_body = render_to_string(f"emails/{template_name}.html", context)

    message = EmailMultiAlternatives(
        subject=subject,
        body=text_body,
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=recipients,
    )
    message.attach_alternative(html_body, "text/html")
    if logo:
        if django.VERSION < (6, 0):
            # "related" lega l'immagine all'HTML che la referenzia via cid:
            # (Django 6 ha rimosso l'opzione e usa sempre "mixed").
            message.mixed_subtype = "related"
        message.attach(logo)
    try:
        message.send()
    except Exception:
        logger.exception(
            "Invio email '%s' a %s non riuscito", template_name, recipients
        )
        raise
    return recipients
