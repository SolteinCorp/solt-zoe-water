# Copyright 2026 Soltein SA. de CV.
# License LGPL-3 or later (http://www.gnu.org/licenses/lgpl.html)

from odoo import http
from odoo.addons.web.controllers.binary import Binary
from odoo.exceptions import UserError
from odoo.http import request
from odoo.tools.image import image_guess_size_from_field_name
from werkzeug.wrappers import Response


class BinaryFallback(Binary):
    @http.route()
    def content_image(
        self,
        xmlid: str | None = None,
        model: str = "ir.attachment",
        id: str | int | None = None,
        field: str = "raw",
        filename_field: str = "name",
        filename: str | None = None,
        mimetype: str | None = None,
        unique: bool = False,
        download: bool = False,
        width: int = 0,
        height: int = 0,
        crop: bool = False,
        access_token: str | None = None,
        nocache: bool = False,
        **kwargs: dict,
    ) -> Response:
        """
        Controla la entrega de imágenes desde registros de la base de datos.

        Este método maneja la recuperación y entrega de imágenes almacenadas en campos
        binarios de registros de Odoo, con soporte para redimensionamiento, recorte y
        manejo de errores con imágenes de respaldo.

        Args:
            xmlid (str | None): ID XML del registro para buscar la imagen.
            model (str): Modelo del registro que contiene la imagen. Por defecto 'ir.attachment'.
            id (str | int | None): ID del registro que contiene la imagen.
            field (str): Campo que contiene los datos binarios de la imagen. Por defecto 'raw'.
            filename_field (str): Campo que contiene el nombre del archivo. Por defecto 'name'.
            filename (str | None): Nombre específico del archivo para la respuesta.
            mimetype (str | None): Tipo MIME específico para la respuesta.
            unique (bool): Si es True, habilita el cacheo a largo plazo. Por defecto False.
            download (bool): Si es True, fuerza la descarga como archivo adjunto. Por defecto False.
            width (int): Ancho deseado para redimensionar la imagen. Por defecto 0.
            height (int): Alto deseado para redimensionar la imagen. Por defecto 0.
            crop (bool): Si es True, recorta la imagen al tamaño especificado. Por defecto False.
            access_token (str | None): Token de acceso para validación de permisos.
            nocache (bool): Si es True, deshabilita el cacheo. Por defecto False.
            **kwargs (dict): Argumentos adicionales, incluyendo 'sudo_load' y 'fallback'.

        Returns:
            Response: Respuesta HTTP con la imagen solicitada o imagen de respaldo.

        Raises:
            NotFound: Si download es True y no se puede encontrar la imagen.

        Note:
            En caso de error, se utiliza una imagen de respaldo especificada en 'fallback'
            o 'web.image_placeholder' por defecto. Se aplican políticas de seguridad
            de contenido restrictivas a la respuesta.
        """
        try:
            binary_obj = (
                request.env["ir.binary"].sudo()
                if "sudo_load" in kwargs
                else request.env["ir.binary"]
            )
            record = binary_obj._find_record(xmlid, model, id and int(id), access_token)
            stream = binary_obj._get_image_stream_from(
                record,
                field,
                filename=filename,
                filename_field=filename_field,
                mimetype=mimetype,
                width=int(width),
                height=int(height),
                crop=crop,
            )
            if request.httprequest.args.get("access_token"):
                stream.public = True
        except UserError as exc:
            if download:
                raise request.not_found() from exc
            if (int(width), int(height)) == (0, 0):
                width, height = image_guess_size_from_field_name(field)
            fallback: str = str(kwargs.get("fallback", "web.image_placeholder"))
            try:
                record = request.env.ref(fallback, raise_if_not_found=False)
                if record:
                    record = record.sudo()
                else:
                    record = request.env.ref("web.image_placeholder").sudo()
            except Exception:
                record = request.env.ref("web.image_placeholder").sudo()
            stream = request.env["ir.binary"]._get_image_stream_from(
                record,
                "raw",
                width=int(width),
                height=int(height),
                crop=crop,
            )
            stream.public = False

        send_file_kwargs = {}
        if unique:
            send_file_kwargs["immutable"] = True
            send_file_kwargs["max_age"] = http.STATIC_CACHE_LONG
        if nocache:
            send_file_kwargs["max_age"] = None

        res = stream.get_response(as_attachment=download, **send_file_kwargs)
        res.headers["Content-Security-Policy"] = "default-src 'none'"
        return res
