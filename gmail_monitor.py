"""
Gmail IMAP monitor for Garmin LiveTrack emails.

Polls the inbox for emails from Garmin containing LiveTrack session links
and yields each unique URL found.
"""

import asyncio
import email
import imaplib
import logging
import re
from email.header import decode_header

logger = logging.getLogger(__name__)

LIVETRACK_URL_RE = re.compile(
    r"https://livetrack\.garmin\.com/session/[0-9a-f\-]+/token/[0-9A-F]+"
)

# Garmin sends LiveTrack share emails from this address with this subject fragment
GARMIN_SENDER = "noreply@garmin.com"
LIVETRACK_SUBJECT_FRAGMENT = "livetrack"


def _decode_header_value(raw: str) -> str:
    parts = decode_header(raw)
    decoded = []
    for part, charset in parts:
        if isinstance(part, bytes):
            decoded.append(part.decode(charset or "utf-8", errors="replace"))
        else:
            decoded.append(part)
    return "".join(decoded)


def _extract_text(msg: email.message.Message) -> str:
    """Recursively extract plain text and HTML body from an email message."""
    body_parts = []
    if msg.is_multipart():
        for part in msg.walk():
            ctype = part.get_content_type()
            if ctype in ("text/plain", "text/html"):
                payload = part.get_payload(decode=True)
                if payload:
                    charset = part.get_content_charset() or "utf-8"
                    body_parts.append(payload.decode(charset, errors="replace"))
    else:
        payload = msg.get_payload(decode=True)
        if payload:
            charset = msg.get_content_charset() or "utf-8"
            body_parts.append(payload.decode(charset, errors="replace"))
    return "\n".join(body_parts)


def _is_livetrack_email(msg: email.message.Message) -> bool:
    sender = msg.get("From", "")
    subject = _decode_header_value(msg.get("Subject", ""))
    return GARMIN_SENDER in sender and LIVETRACK_SUBJECT_FRAGMENT in subject.lower()


class GmailMonitor:
    """
    Monitors a Gmail account via IMAP for Garmin LiveTrack emails.

    Parameters
    ----------
    email_address:
        The Gmail address to monitor.
    app_password:
        A Google App Password (not the regular account password).
    poll_interval:
        How often (in seconds) to check for new mail. Defaults to 60.
    callback:
        An async callable that receives a LiveTrack URL string whenever a new
        one is found.
    """

    IMAP_HOST = "imap.gmail.com"

    def __init__(
        self,
        email_address: str,
        app_password: str,
        callback,
        poll_interval: int = 60,
    ):
        self.email_address = email_address
        self.app_password = app_password
        self.callback = callback
        self.poll_interval = poll_interval
        self._seen_urls: set[str] = set()
        self._running = False

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _connect(self) -> imaplib.IMAP4_SSL:
        mail = imaplib.IMAP4_SSL(self.IMAP_HOST)
        mail.login(self.email_address, self.app_password)
        return mail

    def _fetch_unread_livetrack_urls(self) -> list[str]:
        """Connect, search INBOX for unread Garmin LiveTrack emails, return URLs."""
        urls: list[str] = []
        try:
            mail = self._connect()
            mail.select("INBOX")

            # Search for unread messages from Garmin
            _, data = mail.search(None, f'(UNSEEN FROM "{GARMIN_SENDER}")')
            message_ids = data[0].split()

            for mid in message_ids:
                _, msg_data = mail.fetch(mid, "(RFC822)")
                raw = msg_data[0][1]
                msg = email.message_from_bytes(raw)

                if not _is_livetrack_email(msg):
                    continue

                body = _extract_text(msg)
                found = LIVETRACK_URL_RE.findall(body)
                urls.extend(found)

            mail.logout()
        except imaplib.IMAP4.error as exc:
            logger.error("IMAP error while fetching mail: %s", exc)
        except Exception as exc:
            logger.error("Unexpected error in Gmail monitor: %s", exc)
        return urls

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def run(self):
        """Poll Gmail repeatedly and invoke the callback for each new URL."""
        self._running = True
        logger.info(
            "Gmail monitor started (account=%s, interval=%ds)",
            self.email_address,
            self.poll_interval,
        )
        while self._running:
            try:
                loop = asyncio.get_running_loop()
                urls = await loop.run_in_executor(
                    None, self._fetch_unread_livetrack_urls
                )
                for url in urls:
                    if url not in self._seen_urls:
                        self._seen_urls.add(url)
                        logger.info("New LiveTrack URL found: %s", url)
                        await self.callback(url)
            except Exception as exc:
                logger.error("Error during poll cycle: %s", exc)
            await asyncio.sleep(self.poll_interval)

    def stop(self):
        self._running = False
        logger.info("Gmail monitor stopped.")
