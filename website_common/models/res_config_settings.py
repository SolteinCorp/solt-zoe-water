# -*- coding: utf-8 -*-
# Copyright 2026 Soltein SA. de CV.
# License LGPL-3 or later (http://www.gnu.org/licenses/lgpl.html)
import logging

from odoo import api, fields, models

_logger = logging.getLogger(__name__)


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    display_compact_search_bar = fields.Boolean(
        string="Activate Portal Small Search Bar",
        help="If marked a small search bar will be shown in the portal",
        config_parameter="website_common.display_compact_search_bar",
    )
    display_search_bar_at_top = fields.Boolean(
        string="Display Search Bar at Top",
        help="If marked the search bar will be displayed at the top of the portal pages",
        default=True,
        config_parameter="website_common.display_search_bar_at_top",
    )
    attachment_models_managed_by_group_portal_ids = fields.Many2many(
        comodel_name="ir.model",
        string="Attachment models managed by group portal",
        help="Attachment models managed by group portal",
    )
    allow_portal_users_chatter_messaging = fields.Boolean(
        string="Allow portal users chatter messaging",
        default=False,
        config_parameter="website_common.allow_portal_users_chatter_messaging",
        help="Allow portal users chatter messaging on my account backend views",
    )
    add_access_token_to_attachment_format = fields.Boolean(
        string="Add access token value to attachment format",
        default=False,
        help="If checked the value of access token in attachments will be added to attributes readed",
        config_parameter="website_common.add_access_token_to_attachment_format",
    )

    def get_parsed_attribute_value(self) -> bool:
        """
        Retrieves and parses the value of the 'website_common.display_compact_search_bar' parameter.

        This method fetches the parameter value from the system parameters and handles type conversion.
        If the value is already a boolean, it returns it directly. Otherwise, it converts the string
        value 'true' (case-insensitive) to True, and any other string value to False.

        Returns:
            bool: The parsed boolean value of the parameter.
        """
        # Fetch the parameter value from the system parameters
        # using the 'sudo' method to bypass access rights
        # and ensure the value is retrieved even if the user lacks permissions.
        value = (
            self.env["ir.config_parameter"]
            .sudo()
            .get_param("website_common.display_compact_search_bar", False)
        )
        # Check if the value is already a boolean
        # If it is, return it directly
        # Otherwise, convert the string value to a boolean
        if isinstance(value, bool):
            return value
        return value.lower() == "true"

    @api.onchange("display_compact_search_bar")
    def _onchange_display_compact_search_bar(self) -> None:
        """
        Método llamado automáticamente cuando el campo `display_compact_search_bar` cambia en la vista de configuración.

        Si el valor del campo es diferente al valor almacenado en los parámetros del sistema,
        busca la plantilla `website_common.portal_searchbar` y actualiza su estado de activación
        según el valor actual del campo.

        Esto permite activar o desactivar dinámicamente la barra de búsqueda compacta en el portal.
        """
        if self.display_compact_search_bar != self.get_parsed_attribute_value():
            # Este código se ejecuta cuando el campo cambia y el valor es diferente al almacenado
            template = self.env.ref(
                "website_common.portal_searchbar", raise_if_not_found=False
            )
            if template:
                template.active = self.display_compact_search_bar

    def get_default_managed_model(self) -> str:
        """
        Returns the ID of the default managed model as a string.

        This method searches for the `mail.compose.message` model in the `ir.model` table.
        If found, it returns the ID of the first matching record as a string.
        If not found or if an exception occurs, it returns an empty string.

        Returns:
            str: The ID of the default managed model, or an empty string if not found.
        """
        try:
            default_model = (
                self.env["ir.model"]
                .sudo()
                .search([("model", "=", "mail.compose.message")], limit=1)
            )
            if default_model.exists():
                return str(default_model[0].id)
            return ""
        except Exception as e:
            _logger.exception("Error fetching default managed model: %s", e)
            return ""

    def get_values(self) -> dict:
        """
        Obtiene y actualiza los valores de configuración del sitio web.

        Este método recupera los parámetros de configuración almacenados en la base de datos
        y los procesa para retornarlos en formato de diccionario. Realiza las siguientes operaciones:

        1. Obtiene los valores de configuración base del modelo padre
        2. Recupera parámetros de configuración específicos de 'website_common' tales como:
            - Modelos de adjuntos gestionados por el grupo portal
            - Visibilidad de la barra de búsqueda compacta
            - Posición de la barra de búsqueda
            - Permisos de mensajería en el chatter para usuarios del portal
            - Inclusión de tokens de acceso en el formato de adjuntos
        3. Convierte valores booleanos de cadena a tipo bool
        4. Transforma IDs de modelos de adjuntos en una lista de tuplas para actualización

        Returns:
             dict: Diccionario con los parámetros de configuración del sitio web,
                     incluyendo la configuración de búsqueda, permisos de portal y
                     modelos de adjuntos gestionados por grupos.
        """
        res = super().get_values()
        params = self.env["ir.config_parameter"].sudo()
        model_ids = params.get_param(
            "website_common.attachment_models_managed_by_group_portal",
            default=self.get_default_managed_model(),
        )
        res.update(
            display_compact_search_bar=self.get_parsed_attribute_value(),
            display_search_bar_at_top=params.get_param(
                "website_common.display_search_bar_at_top"
            ),
            allow_portal_users_chatter_messaging=params.get_param(
                "website_common.allow_portal_users_chatter_messaging", "False"
            )
            == "True",
            add_access_token_to_attachment_format=params.get_param(
                "website_common.add_access_token_to_attachment_format", "False"
            )
            == "True",
            attachment_models_managed_by_group_portal_ids=[
                (6, 0, [int(id_) for id_ in model_ids.split(",") if id_])
            ],
        )
        return res

    def set_values(self) -> None:
        """
        Establece los valores de configuración del sitio web común.

        Este método guarda los parámetros de configuración en la base de datos mediante
        el modelo ir.config_parameter. También activa o desactiva la plantilla del buscador
        del portal según la configuración especificada.

        Los parámetros guardados incluyen:
        - website_common.attachment_models_managed_by_group_portal: Modelos de adjuntos
            gestionados por el grupo portal.
        - website_common.display_compact_search_bar: Indica si se muestra la barra de
            búsqueda compacta.
        - website_common.display_search_bar_at_top: Indica si la barra de búsqueda se
            muestra en la parte superior.
        - website_common.allow_portal_users_chatter_messaging: Indica si los usuarios del
            portal pueden usar mensajería en el chatter.
        - website_common.add_access_token_to_attachment_format: Indica si se agrega un
            token de acceso al formato de adjuntos.

        Además, activa o desactiva la plantilla "website_common.portal_searchbar" según
        el valor de display_compact_search_bar.

        Returns:
                None
        """
        res = super().set_values()
        params = self.env["ir.config_parameter"].sudo()
        params.set_param(
            "website_common.attachment_models_managed_by_group_portal",
            ",".join(map(str, self.attachment_models_managed_by_group_portal_ids.ids)),
        )
        params.set_param(
            "website_common.display_compact_search_bar",
            str(self.display_compact_search_bar),
        )
        params.set_param(
            "website_common.display_search_bar_at_top",
            bool(self.display_search_bar_at_top),
        )
        params.set_param(
            "website_common.allow_portal_users_chatter_messaging",
            bool(self.allow_portal_users_chatter_messaging),
        )
        params.set_param(
            "website_common.add_access_token_to_attachment_format",
            bool(self.add_access_token_to_attachment_format),
        )
        # Activa o desactiva la plantilla según el valor de display_compact_search_bar
        template = self.env.ref(
            "website_common.portal_searchbar", raise_if_not_found=False
        )
        if template:
            template.active = self.display_compact_search_bar
        return res
