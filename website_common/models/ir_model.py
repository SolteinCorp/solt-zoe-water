# -*- coding: utf-8 -*-
# Copyright 2026 Soltein SA. de CV.
# License LGPL-3 or later (http://www.gnu.org/licenses/lgpl.html)
from odoo import models
from odoo.http import request
from werkzeug.urls import iri_to_uri


class BaseModel(models.AbstractModel):
    _inherit = "base"

    def get_base_url(self):
        """Return the base URL for the current request.

        - Prioritizes `request.httprequest.url_root` to support multi-website setups.
        - Converts IRI hostnames to URI (punycode) via `werkzeug.urls.iri_to_uri` for compatibility with external APIs.
        - Falls back to `super().get_base_url()` when no HTTP request context is available.

        Returns:
            str: Normalized base URL without a trailing slash.
        """
        # Give priority to url_root to handle multi-website cases
        if request and request.httprequest.url_root:
            # Some domain names can use non-Latin script or alphabet or the Latin
            # alphabet-based characters with diacritics or ligatures. They are
            # stored as ASCII strings using Punycode transcription in the DNS
            # system and need to be converted to send to external APIs.
            return iri_to_uri(request.httprequest.url_root).rstrip("/")
        return super().get_base_url()
