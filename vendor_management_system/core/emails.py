"""Invio email del progetto.

Tutte le email applicative passano da `send_templated_email`, così il
dirottamento dei destinatari (`settings.EMAIL_REDIRECT_TO`, usato in
locale/test per non scrivere ai fornitori reali) vale ovunque senza doverlo
ripetere in ogni punto di invio.
"""

import logging

from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string

logger = logging.getLogger(__name__)


def send_templated_email(*, subject, template_name, context, to):
    """Invia un'email testo + HTML resa da `emails/<template_name>.txt|.html`.

    Restituisce la lista dei destinatari effettivi (quelli di redirect, se
    attivo). Gli errori di invio NON vengono silenziati: li gestisce il
    chiamante, che sa come avvisare l'utente.
    """
    original_recipients = list(to)
    redirect_to = list(getattr(settings, "EMAIL_REDIRECT_TO", []) or [])
    recipients = redirect_to or original_recipients

    context = {
        **context,
        "original_recipients": original_recipients if redirect_to else [],
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
    try:
        message.send()
    except Exception:
        logger.exception(
            "Invio email '%s' a %s non riuscito", template_name, recipients
        )
        raise
    return recipients
