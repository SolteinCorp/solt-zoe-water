# Copyright 2026 Soltein SA. de CV.
# License LGPL-3 or later (http://www.gnu.org/licenses/lgpl.html)

import logging

from odoo import _, api, SUPERUSER_ID

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    """Post-migration script to create default upload profiles for websites."""
    env = api.Environment(cr, SUPERUSER_ID, {})
    websites = env["website"].search([])
    for website in websites:
        try:
            profile = env["website.upload.profile"].create(
                {
                    "name": "Avatar Profile",
                    "website_id": website.id,
                    "sequence": 1,
                    "minimum_width": 128,
                    "minimum_height": 128,
                    "maximum_width": 1920,
                    "maximum_height": 1920,
                    "maximum_size_mb": 1,
                    "allowed_mime_type_ids": [
                        (
                            6,
                            0,
                            [
                                env.ref("website_common.mime_jpeg").id,
                                env.ref("website_common.mime_jpg").id,
                                env.ref("website_common.mime_png").id,
                                env.ref("website_common.mime_svg").id,
                                env.ref("website_common.mime_webp").id,
                            ],
                        )
                    ],
                }
            )
            _logger.info(
                _("Created upload profile for website %s: %s", website.id, profile.name)
            )
        except Exception as exc:
            _logger.error(
                _(
                    "Error creating upload profile for website %s: %s",
                    website.id,
                    str(exc),
                )
            )
