# Copyright 2026 Soltein SA. de CV.
# License LGPL-3 or later (http://www.gnu.org/licenses/lgpl.html)

from odoo import api, fields, models

from ..utils.collections import objects_to_dict


class IrAttachment(models.Model):
    _inherit = "ir.attachment"

    auth_user_is_related_model_follower = fields.Boolean(
        string="Authenticated user is related model follower",
        compute="_compute_auth_user_is_related_model_follower",
        search="_search_auth_user_is_related_model_follower",
        help="If the authenticated user is following the attachment related model",
    )

    @api.depends("res_model", "res_id")
    @api.depends_context("uid")
    def _compute_auth_user_is_related_model_follower(self):
        """
        Compute whether the authenticated user is a follower of the related model for each attachment.

        This method determines if the current user (via their partner record) is following each
        attachment in the recordset. It retrieves all attachment IDs that are followed by the user's
        partner and sets the `auth_user_is_related_model_follower` field accordingly for each attachment.

        Sets:
            auth_user_is_related_model_follower (bool): True if the attachment is followed by the
                authenticated user's partner, False otherwise.
        """
        attachment_ids = self.env.user.partner_id.attachment_ids_followed_by_partner()
        for attachment in self:
            attachment.auth_user_is_related_model_follower = (
                attachment.id in attachment_ids
            )

    def _search_auth_user_is_related_model_follower(self, operator, operand):
        """
        Search method to filter attachments based on whether the current user's partner
        is following them.

        This method is used as a custom search implementation for a computed field that
        determines if the current user's partner is a follower of the attachment.

        Args:
            operator (str): The search operator ('=' or '!=').
                           '=' returns attachments the user is following.
                           '!=' returns attachments the user is not following.
            operand (bool): The operand value to compare against.
                           True searches for followed attachments.
                           False searches for unfollowed attachments.

        Returns:
            list: A domain expression as a list of tuples for filtering attachments.
                 Returns [('id', 'in', attachment_ids)] or [('id', 'not in', attachment_ids)]
                 depending on the operator and operand combination.
        """
        attachment_ids = self.env.user.partner_id.attachment_ids_followed_by_partner()
        if (operator == "=" and operand) or (operator == "!=" and not operand):
            return [("id", "in", attachment_ids)]
        else:
            return [("id", "not in", attachment_ids)]

    def _attachment_format(self) -> list:
        """
        Format attachments with optional access token generation.

        Extends the parent class's _attachment_format method to conditionally add
        access tokens to attachment data based on a system configuration parameter.

        When the 'website_common.add_access_token_to_attachment_format' parameter
        is set to 'True', this method generates and includes an access token for
        each attachment in the formatted output.

        Returns:
            list: A list of formatted attachment dictionaries. Each dictionary contains
                  the standard attachment format data, and optionally includes an
                  'accessToken' key if the configuration parameter is enabled.
        """
        attachment_format = super()._attachment_format()

        if (
            self.env["ir.config_parameter"]
            .sudo()
            .get_param("website_common.add_access_token_to_attachment_format", "False")
            == "True"
        ):
            attachment_dict = objects_to_dict(attachment_format, "id")
            for attachment in self:
                attachment.generate_access_token()
                attachment_dict[attachment.id]["accessToken"] = attachment.access_token
            return list(attachment_dict.values())

        return attachment_format
