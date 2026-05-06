# -*- coding: utf-8 -*-
# Copyright 2026 Soltein SA. de CV.
# License LGPL-3 or later (http://www.gnu.org/licenses/lgpl.html)
from odoo import _, api, fields, models
from odoo.http import request

MIME_TYPES = [
    ("image/jpeg", "JPEG"),
    ("image/jpg", "JPG"),
    ("image/png", "PNG"),
    ("image/gif", "GIF"),
    ("image/svg+xml", "SVG"),
    ("image/webp", "WebP"),
    ("image/tiff", "TIFF"),
    ("image/bmp", "BMP"),
    ("application/pdf", "PDF"),
    ("application/msword", "DOC Microsoft Word"),
    (
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "DOCX Microsoft Word",
    ),
    ("application/vnd.ms-excel", "XLS Microsoft Excel"),
    (
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        "XLSX Microsoft Excel",
    ),
    ("application/vnd.ms-powerpoint", "PPT Microsoft PowerPoint"),
    (
        "application/vnd.openxmlformats-officedocument.presentationml.presentation",
        "PPTX Microsoft PowerPoint",
    ),
    ("text/plain", "TXT"),
    ("text/csv", "CSV"),
    ("application/rtf", "RTF"),
    ("audio/mpeg", "MP3"),
    ("audio/wav", "WAV"),
    ("audio/ogg", "OGG"),
    ("audio/aac", "AAC"),
    ("audio/webm", "WebM"),
    ("video/mp4", "MP4"),
    ("video/webm", "WebM"),
    ("video/ogg", "OGG"),
    ("video/x-msvideo", "AVI"),
    ("video/quicktime", "MOV"),
    ("application/zip", "ZIP"),
    ("application/x-rar-compressed", "RAR"),
    ("application/x-7z-compressed", "7z"),
    ("application/gzip", "GZIP"),
    ("application/x-tar", "TAR"),
    ("application/json", "JSON"),
    ("application/xml", "XML"),
    ("application/octet-stream", "Binary"),
]

MIME_TYPES_CATEGORIES = [
    ("image", "Image"),
    ("document", "Document"),
    ("audio", "Audio"),
    ("video", "Video"),
    ("archive", "Archive"),
    ("other", "Other"),
]


class UploadMime(models.Model):
    _name = "website.upload.mime"
    _description = "Upload Mime to check types"
    _order = "sequence"

    name = fields.Char("Name", required=True, translate=True)
    sequence = fields.Integer("Sequence", default=1)
    category = fields.Selection(
        MIME_TYPES_CATEGORIES,
        string="Category",
        default="other",
        help="Categoría del tipo MIME.",
    )
    mime_type = fields.Selection(
        MIME_TYPES,
        string="Mime Type",
        default="application/octet-stream",
        help="Tipo MIME del archivo.",
    )

    _sql_constraints = [
        ("mime_type_unique", "unique (mime_type)", "The Mime Type must be unique!"),
    ]


class UploadProfile(models.Model):
    """
    Modelo para gestionar los perfiles de carga, verificando tamaños, tipos o dimensiones de los archivos subidos.
    """

    _name = "website.upload.profile"
    _description = "Upload Profile to check sizes, types or dimensions"
    _order = "sequence"

    name = fields.Char(
        "Name", required=True, translate=True, help="Nombre del perfil de carga."
    )
    slug = fields.Char(
        "Slug",
        compute="_compute_slug",
        store=True,
        required=True,
        help="Slug único generado a partir del nombre.",
    )
    sequence = fields.Integer(
        "Sequence", default=1, help="Secuencia para ordenar los perfiles de carga."
    )
    minimum_width = fields.Integer(
        "Minimum Width", default=0, help="Ancho mínimo permitido para la imagen."
    )
    maximum_width = fields.Integer(
        "Maximum Width", default=0, help="Ancho máximo permitido para la imagen."
    )
    minimum_height = fields.Integer(
        "Minimum Height", default=0, help="Altura mínima permitida para la imagen."
    )
    maximum_height = fields.Integer(
        "Maximum Height", default=0, help="Altura máxima permitida para la imagen."
    )
    maximum_size_mb = fields.Integer(
        "Maximum Size (MB)",
        default=5,
        help="Tamaño máximo permitido para el archivo en MB.",
    )
    allowed_mime_type_ids = fields.Many2many(
        "website.upload.mime",
        "website_upload_profile_mime_rel",
        "profile_id",
        "mime_type_id",
        string="Allowed Mime Types",
        help="Tipos MIME permitidos para los archivos subidos.",
    )
    website_id = fields.Many2one(
        "website",
        string="Website",
        required=True,
        ondelete="cascade",
        default=lambda self: request.website.id,
        help="Sitio web asociado al perfil de carga.",
    )

    _sql_constraints = [
        (
            "slug_website_id_unique",
            "unique (slug, website_id)",
            _("There is a upload profile with the same slug in this website!"),
        ),
    ]

    @api.depends("name")
    def _compute_slug(self):
        """
        Computa el campo slug a partir del nombre del perfil de carga.
        """
        for record in self:
            record.slug = record.name and slugify_one(record.name) or False

    @api.model_create_multi
    def create(self, vals_list) -> models.BaseModel:
        """
        Create multiple upload profile records.
        Ensures that the `slug` field is generated from the `name` if not provided in each record.
        """
        index = 0
        while index < len(vals_list):
            if "slug" not in vals_list[index] and "name" in vals_list[index]:
                vals_list[index]["slug"] = slugify_one(vals_list[index]["name"])
            index += 1
        return super().create(vals_list)

    def write(self, vals) -> bool:
        """
        Update upload profile records.
        If the `name` is updated and `slug` is not provided, generates a new `slug` from the `name`.
        """
        if "slug" not in vals and "name" in vals:
            vals["slug"] = slugify_one(vals["name"])
        return super().write(vals)
