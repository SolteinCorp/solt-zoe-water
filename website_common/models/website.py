# Copyright 2026 Soltein SA. de CV.
# License LGPL-3 or later (http://www.gnu.org/licenses/lgpl.html)
import logging

from odoo import _, api, fields, models, tools

_logger = logging.getLogger(__name__)


class Website(models.Model):
    _inherit = "website"

    upload_profile_ids = fields.One2many(
        "website.upload.profile",
        "website_id",
        string="Upload Profiles",
        help="Upload profiles managed in the website",
    )
    side_menu_ids = fields.Many2many(
        comodel_name="website.menu",
        string="Side Menu",
        compute="_compute_side_menu_ids",
        help="Side menus managed by the website",
    )
    all_menu_id = fields.Many2one(
        "website.menu",
        compute="_compute_menu_all",
        string="Main Menu All",
        help="Main menus managed by the website",
    )

    @api.model
    def get_website_upload_profile(
        self, upload_profile_slug: str, website_id: int
    ) -> dict:
        """
        Obtiene el perfil de carga del sitio web basado en el slug y el ID del sitio web.

        :param upload_profile_slug: El slug del perfil de carga.
        :param website_id: El ID del sitio web.
        :return: Un diccionario con los detalles del perfil de carga o un diccionario vacío si no se encuentra.
        """
        upload_profile = self.env["website.upload.profile"].search(
            [("slug", "=", upload_profile_slug), ("website_id", "=", website_id)],
            limit=1,
        )
        if len(upload_profile) == 0:
            return {}
        data = upload_profile.read(
            [
                "slug",
                "maximum_size_mb",
                "minimum_width",
                "minimum_height",
                "maximum_width",
                "maximum_height",
                "allowed_mime_type_ids",
            ]
        )[0]
        data["allowed_mime_type_ids"] = (
            self.env["website.upload.mime"]
            .browse(data["allowed_mime_type_ids"])
            .read(["mime_type"])
        )
        return data

    def get_upload_profile(self, upload_profile_slug: str) -> dict:
        """
        Obtiene el perfil de carga del sitio web basado en el slug.

        :param upload_profile_slug: El slug del perfil de carga.
        :return: Un diccionario con los detalles del perfil de carga.
        """
        self.ensure_one()
        data = self.upload_profile_ids.filtered(
            lambda r: r.slug == upload_profile_slug
        ).read(
            [
                "slug",
                "maximum_size_mb",
                "minimum_width",
                "minimum_height",
                "maximum_width",
                "maximum_height",
                "allowed_mime_type_ids",
            ]
        )[0]
        data["allowed_mime_type_ids"] = (
            self.env["website.upload.mime"]
            .browse(data["allowed_mime_type_ids"])
            .read(["mime_type"])
        )
        return data

    def apply_field_value(self, field_name, field_value) -> int:
        """
        Applies a value to a specified field in the current record.

        This method ensures that the operation is performed on a single record.
        It checks if the given field name exists in the model's fields and attempts
        to write the provided value to the field. If the field does not exist, or
        if an error occurs during the write operation, appropriate error handling
        is performed.

        Args:
            field_name (str): The name of the field to update.
            field_value (any): The value to assign to the specified field.

        Returns:
            int:
                - 1 if the field value was successfully applied.
                - 0 if an error occurred during the write operation.
                - -1 if the specified field does not exist in the model.

        Logs:
            Logs an error message if an exception occurs during the write operation.
        """
        # self.ensure_one()
        if field_name not in self._fields:
            return -1
        try:
            self.write({field_name: field_value})
            return 1
        except Exception as exc:
            _logger.error(
                _("Error applying website model field %s value: %s", field_name, exc)
            )
            return 0

    @tools.ormcache("self.env.uid", "self.id", cache="templates")
    def _get_menu_ids(self) -> list[int]:
        """
        Returns the IDs of main menu items for the current website.

        Returns:
            list[int]: List of menu IDs where display_on_main_menu is True.
        """
        return (
            self.env["website.menu"]
            .search([("website_id", "=", self.id), ("display_on_main_menu", "=", True)])
            .ids
        )

    @tools.ormcache("self.env.uid", "self.id", cache="templates")
    def _get_menu_all_ids(self) -> list[int]:
        """
        Returns the IDs of all menu items for the current website.

        Returns:
            list[int]: List of all menu IDs for the website.
        """
        return self.env["website.menu"].search([("website_id", "=", self.id)]).ids

    @tools.ormcache("self.env.uid", "self.id", cache="templates")
    def _get_side_menu_ids(self) -> list[int]:
        """
        Returns the IDs of side menu items for the current website.

        Returns:
            list[int]: List of menu IDs where is_side_menu_item is True.
        """
        return (
            self.env["website.menu"]
            .search([("website_id", "=", self.id), ("is_side_menu_item", "=", True)])
            .ids
        )

    def _compute_menu_all(self) -> None:
        """
        Computes and assigns the main menu for each website record.

        This method sets the all_menu_id field to the top-level menu
        (menu without a parent) for each website.
        """
        for website in self:
            menus = self.env["website.menu"].browse(website._get_menu_all_ids())

            # use field parent_id (1 query) to determine field child_id (2 queries by level)"
            for menu in menus:
                menu._cache["child_id"] = ()
            for menu in menus:
                # don't add child menu if parent is forbidden
                if menu.parent_id and menu.parent_id in menus:
                    menu.parent_id._cache["child_id"] += (menu.id,)

            # prefetch every website.page and ir.ui.view at once
            menus.mapped("is_visible")

            top_menus = menus.filtered(lambda m: not m.parent_id)
            website.all_menu_id = top_menus and top_menus[0].id or False

    def _compute_side_menu_ids(self) -> None:
        """
        Computes and assigns the side menu items for each website record.

        This method sets the side_menu_ids field to the child menus of
        top-level side menu items for each website.
        """
        for website in self:
            menus = self.env["website.menu"].browse(website._get_side_menu_ids())
            # use field parent_id (1 query) to determine field child_id (2 queries by level)"
            for menu in menus:
                menu._cache["child_id"] = ()
            for menu in menus:
                # don't add child menu if parent is forbidden
                if menu.parent_id and menu.parent_id in menus:
                    menu.parent_id._cache["child_id"] += (menu.id,)
            # prefetch every website.page and ir.ui.view at once
            menus.mapped("is_visible")
            top_menus = menus.filtered(lambda m: not m.parent_id)
            website.side_menu_ids = top_menus.child_id
