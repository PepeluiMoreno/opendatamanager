"""Envío best-effort de webhooks de gobernanza (push de resoluciones).

Se firma sobre los BYTES EXACTOS que se envían (HMAC-SHA256, header
``X-ODM-Signature``), de modo que el receptor —que valida sobre el body crudo—
los acepte sin depender del orden de claves de la serialización.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import logging
from typing import Optional, Tuple

import requests

logger = logging.getLogger(__name__)


def post_webhook(url: Optional[str], secret: Optional[str], payload: dict,
                 timeout: int = 10) -> Tuple[Optional[int], Optional[str]]:
    """POST firmado a ``url``. Devuelve (status_code|None, error|None). Nunca lanza."""
    if not url:
        return None, "sin url"
    body = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    sig = hmac.new((secret or "").encode("utf-8"), body, hashlib.sha256).hexdigest()
    try:
        r = requests.post(url, data=body,
                          headers={"X-ODM-Signature": sig,
                                   "Content-Type": "application/json"},
                          timeout=timeout)
        return r.status_code, None
    except Exception as e:  # noqa: BLE001
        logger.warning("post_webhook a %s falló: %s", url, e)
        return None, str(e)
