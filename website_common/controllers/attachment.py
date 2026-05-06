# Copyright 2026 Soltein SA. de CV.
# License LGPL-3 or later (http://www.gnu.org/licenses/lgpl.html)

from odoo import _, http
from odoo.addons.mail.controllers.attachment import AttachmentController
from odoo.addons.mail.models.discuss.mail_guest import add_guest_to_context
from odoo.exceptions import UserError
from odoo.http import request
from odoo.tools import consteq
from werkzeug.exceptions import NotFound


class AttachmentControllerCommon(AttachmentController):
    @http.route()
    @add_guest_to_context
    def mail_attachment_delete(self, attachment_id, access_token=None):
        """
        Delete an attachment with proper access control for internal and portal/guest users.

        For internal users, standard access rights and rules are applied.
        For non-internal users, deletion is allowed if:
        - The attachment is linked to a message and the current user or guest is the author.
        - A valid access token is provided and the attachment belongs to a model managed by the portal group,
          and was created by the current user.

        Parameters:
            attachment_id (int): The ID of the attachment to delete.
            access_token (str|None): Optional token for portal/guest validation.

        Raises:
            werkzeug.exceptions.NotFound: If the attachment does not exist or the user lacks permission.

        Side Effects:
            Sends a bus notification on deletion and calls `_delete_and_notify` on the attachment.

        """
        attachment = request.env["ir.attachment"].browse(int(attachment_id)).exists()
        if not attachment:
            target = request.env.user.partner_id
            request.env["bus.bus"]._sendone(
                target, "ir.attachment/delete", {"id": attachment_id}
            )
            return
        message = request.env["mail.message"].search(
            [("attachment_ids", "in", attachment.ids)], limit=1
        )
        if not request.env.user.share:
            # Check through standard access rights/rules for internal users.
            attachment._delete_and_notify(message)
            return
        # For non-internal users 2 cases are supported:
        #   - Either the attachment is linked to a message: verify the request is made by the author of the message (portal user or guest).
        #   - Either a valid access token is given: also verify the message is pending (because unfortunately in portal a token is also provided to guest for viewing others' attachments).
        # sudo: ir.attachment: access is validated below with membership of message or access token
        attachment_sudo = attachment.sudo()
        if message:
            if not message.is_current_user_or_guest_author:
                raise UserError(_("You can only delete your own messages attachments."))
        else:
            if (
                not access_token
                or not attachment_sudo.access_token
                or not consteq(access_token, attachment_sudo.access_token)
            ):
                raise NotFound()
            # obtain the list of model names managed by portal group
            params = request.env["ir.config_parameter"].sudo()
            model_names = (
                request.env["ir.model"]
                .browse(
                    [
                        int(id_)
                        for id_ in params.get_param(
                            "website_common.attachment_models_managed_by_group_portal",
                            default="",
                        ).split(",")
                        if id_
                    ]
                )
                .mapped("model")
            )
            # if the attachment is not linked to one of these models raise NotFound
            # if the attachment was not created by the current user, raise UserError
            if attachment_sudo.res_model not in model_names:
                raise NotFound()
            elif attachment_sudo.create_uid.id != request.env.user.id:
                raise UserError(_("You can only delete your own attachments."))
        attachment_sudo._delete_and_notify(message)
