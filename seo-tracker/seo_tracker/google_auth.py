"""Construction des identifiants Google (compte de service) partagés GSC + GA4."""

from __future__ import annotations

import json

from google.oauth2 import service_account

from .config import Config

# GSC en lecture + GA4 en lecture. Un seul compte de service pour les deux.
SCOPES = [
    "https://www.googleapis.com/auth/webmasters.readonly",
    "https://www.googleapis.com/auth/analytics.readonly",
]


def build_credentials(config: Config) -> service_account.Credentials:
    """Retourne des identifiants de compte de service, depuis le JSON brut
    (GOOGLE_CREDENTIALS_JSON) ou depuis un fichier (GOOGLE_APPLICATION_CREDENTIALS)."""
    if config.google_credentials_json:
        info = json.loads(config.google_credentials_json)
        return service_account.Credentials.from_service_account_info(
            info, scopes=SCOPES
        )
    return service_account.Credentials.from_service_account_file(
        config.google_credentials_path, scopes=SCOPES
    )
