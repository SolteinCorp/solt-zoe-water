# Copyright 2026 Soltein SA. de CV.
# License LGPL-3 or later (http://www.gnu.org/licenses/lgpl.html)

from odoo import _
from werkzeug.datastructures import FileStorage

from ..models.upload_profile import UploadProfile


def check_file(file_storage: FileStorage | None, upload_profile: UploadProfile) -> dict:
    """
    Verifica la validez de un archivo subido según el perfil de carga especificado.

    Args:
        file_storage (FileStorage | None): El archivo subido.
        upload_profile (UploadProfile): El perfil de carga que define las restricciones.

    Returns:
        dict: Un diccionario con la validez del archivo, errores encontrados e información del archivo.
    """
    result = {
        "valid": True,  # Indica si el archivo es válido
        "errors": [],  # Lista de errores encontrados
        "file_info": {},  # Información del archivo
    }

    # Verifica si no se ha proporcionado un archivo o si el nombre del archivo está vacío
    if not file_storage or file_storage.filename == "":
        result["valid"] = False
        result["errors"].append(_("No file provided"))
        return result

    filename = file_storage.filename  # Obtiene el nombre del archivo
    content_type = file_storage.content_type  # Obtiene el tipo de contenido del archivo

    # Lee el archivo para obtener su tamaño
    file_storage.seek(0, 2)  # Mueve el puntero al final del archivo
    size_bytes = (
        file_storage.tell()
    )  # Obtiene la posición actual (tamaño del archivo en bytes)
    file_storage.seek(0)  # Restablece el puntero del archivo al inicio
    size_mb = size_bytes / (1024 * 1024)  # Convierte el tamaño a MB

    # Obtiene la extensión del archivo
    extension = (
        filename.rsplit(".", 1)[1].lower() if filename and "." in filename else None
    )

    # Almacena la información del archivo
    result["file_info"] = {
        "filename": filename,
        "content_type": content_type,
        "size_bytes": size_bytes,
        "size_mb": size_mb,
        "extension": extension,
    }

    # Verifica el tamaño del archivo
    if size_mb > upload_profile.maximum_size_mb:
        result["valid"] = False
        result["errors"].append(
            _(
                "File size exceeds the maximum allowed size of %sMB",
                upload_profile.maximum_size_mb,
            )
        )

    # Verifica el tipo de archivo si se especifican tipos permitidos
    mime_types = (
        upload_profile.allowed_mime_type_ids.mapped("mime_type")
        if upload_profile.allowed_mime_type_ids
        else []
    )
    if content_type not in mime_types:
        result["valid"] = False
        result["errors"].append(
            _(
                "File type %s is not allowed. Allowed types: %s",
                content_type,
                ", ".join(mime_types),
            )
        )

    return result
