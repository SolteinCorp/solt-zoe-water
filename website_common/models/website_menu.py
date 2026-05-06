# Copyright 2026 Soltein SA. de CV.
# License LGPL-3 or later (http://www.gnu.org/licenses/lgpl.html)

import logging

from odoo import _, api, fields, models
from odoo.http import request
from werkzeug.urls import url_parse

_logger = logging.getLogger(__name__)

ICON_FONT_FAMILY = [
    ("none", "None"),
    ("font_awesome", "Font Awesome"),
    ("material_icons", "Material Icons"),
]


class WebsiteMenu(models.Model):
    _inherit = "website.menu"

    is_side_menu_item = fields.Boolean(
        string="Is Side Menu Item",
        default=False,
        help="Indica si este elemento del menú debe mostrarse en el menú lateral.",
    )
    display_on_main_menu = fields.Boolean(
        string="Display on Main Menu",
        default=False,
        help="Indica si este elemento del menú debe mostrarse en el menú principal.",
    )
    icon_font_family = fields.Selection(
        ICON_FONT_FAMILY,
        string="Font Family",
        default="none",
        help="Familia de fuente de iconos a utilizar (Font Awesome, Material Icons o ninguno).",
    )
    icon_name = fields.Char(
        string="Icon Name",
        default="Home",
        help="Nombre del icono a mostrar en el elemento del menú.",
    )

    @api.model
    def get_tree(self, website_id, menu_id=None) -> dict:
        """
        Devuelve la estructura de árbol del menú para un sitio web dado.

        Args:
            website_id (int): ID del sitio web.
            menu_id (int, opcional): ID del menú raíz. Si no se proporciona, se usa el menú principal del sitio web.

        Returns:
            dict: Representación en árbol del menú.
        """
        website = self.env["website"].browse(website_id)

        def make_tree(node):
            """
            Construye recursivamente el árbol de menús a partir de un nodo dado.

            Args:
                node (website.menu): Nodo actual del menú.

            Returns:
                dict: Nodo del menú con sus hijos.
            """
            menu_url = node.page_id.url if node.page_id else node.url
            menu_node = {
                "fields": {
                    "id": node.id,
                    "name": node.name,
                    "url": menu_url,
                    "new_window": node.new_window,
                    "is_mega_menu": node.is_mega_menu,
                    "sequence": node.sequence,
                    "parent_id": node.parent_id.id,
                    "is_side_menu_item": node.is_side_menu_item,
                    "display_on_main_menu": node.display_on_main_menu,
                    "icon_font_family": node.icon_font_family,
                    "icon_name": node.icon_name,
                },
                "children": [],
                "is_homepage": menu_url == (website.homepage_url or "/"),
            }
            for child in node.child_id:
                menu_node["children"].append(make_tree(child))
            return menu_node

        menu = menu_id and self.browse(menu_id) or website.all_menu_id
        return make_tree(menu)

    @api.model
    def toggle_lateral_menu(self, website_id, menu_id) -> tuple:
        """
        Alterna el estado de 'is_side_menu_item' para un elemento de menú específico.

        Args:
            website_id (int): ID del sitio web.
            menu_id (int): ID del menú a modificar.

        Returns:
            tuple: (bool, dict/str) Resultado de la operación y el árbol actualizado o mensaje de error.
        """
        menu = self.browse(menu_id).exists()
        if not menu:
            return False, _("The selected menu item does not exist")
        try:
            return menu.write(
                {"is_side_menu_item": not menu.is_side_menu_item}
            ), self.get_tree(website_id)
        except Exception as e:
            _logger.error(str(e))
            return False, _("Error toggling lateral menu on selected item")

    @api.model
    def toggle_display_menu(self, website_id, menu_id) -> tuple:
        """
        Alterna el estado de 'display_on_main_menu' para un elemento de menú específico.

        Args:
            website_id (int): ID del sitio web.
            menu_id (int): ID del menú a modificar.

        Returns:
            tuple: (bool, dict/str) Resultado de la operación y el árbol actualizado o mensaje de error.
        """
        menu = self.browse(menu_id).exists()
        if not menu:
            return False, _("The selected menu item does not exist")
        try:
            return menu.write(
                {"display_on_main_menu": not menu.display_on_main_menu}
            ), self.get_tree(website_id)
        except Exception as e:
            _logger.error(str(e))
            return False, _("Error toggling display menu on selected item")

    def _is_child_active(self) -> bool:
        """
        Verifica si alguno de los hijos del menú está activo.

        Returns:
            bool: True si algún hijo está activo, False en caso contrario.
        """
        self.ensure_one()
        child = self.env["website.menu"].search(
            [("parent_id", "child_of", self.ids), ("id", "not in", self.ids)]
        )
        return any(m._is_active() for m in child)

    def _is_active(self) -> bool:
        """To be considered active, a menu should either:

        - have its URL matching the request's URL and have no children
        - or have a children menu URL matching the request's URL

        Matching an URL means, either:

        - be equal, eg ``/contact/on-site`` vs ``/contact/on-site``
        - be equal after unslug, eg ``/shop/1`` and ``/shop/my-super-product-1``

        Note that saving a menu URL with an anchor or a query string is
        considered a corner case, and the following applies:

        - anchor/fragment are ignored during the comparison (it would be
          impossible to compare anyway as the client is not sending the anchor
          to the server as per RFC)
        - query string parameters should be the same to be considered equal, as
          those could drasticaly alter a page result
        """
        if not request or self.is_mega_menu:
            # There is no notion of `active` if we don't have a request to
            # compare the url to.
            # Also, mega menu are never considered active.
            return self._is_child_active() if self.is_mega_menu else False

        request_url = url_parse(request.httprequest.url)

        if not self.child_id:
            # Don't compare to `url` as it could be shadowed by the linked
            # website page's URL
            menu_url = self._clean_url()
            if not menu_url:
                return False

            menu_url = url_parse(menu_url)
            unslug_url = self.env["ir.http"]._unslug_url
            if unslug_url(menu_url.path) == unslug_url(request_url.path):
                if not (
                    set(menu_url.decode_query().items(multi=True))
                    <= set(request_url.decode_query().items(multi=True))
                ):
                    # correct path but query arguments does not match
                    return False
                if menu_url.netloc and menu_url.netloc != request_url.netloc:
                    # correct path but not correct domain
                    return False
                return True
        else:
            # Child match (dropdown menu), `self` is just a parent/container,
            # don't check its URL, consider only its children
            if any(child._is_active() for child in self.child_id):
                return True

        return False
