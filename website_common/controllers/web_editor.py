# Copyright 2026 Soltein SA. de CV.
# License LGPL-3 or later (http://www.gnu.org/licenses/lgpl.html)

from odoo import _, http, tools
from odoo.addons.web_editor.controllers.main import Web_Editor, get_existing_attachment
from odoo.exceptions import UserError
from odoo.http import request


class WebEditorProjectController(Web_Editor):
    def _attachment_create(
        self, name="", data=False, url=False, res_id=False, res_model="ir.ui.view"
    ):
        """
        Create and return a new attachment.

        This method creates an `ir.attachment` record from raw binary data or a URL.
        It normalizes the name (e.g., strips the `.bmp` extension to avoid content-type
        mismatches), infers a name from the URL if missing, and determines whether the
        attachment should be public based on the target model.

        Parameters:
            name (str): The filename to use for the attachment. If empty and `url` is provided,
                the filename is derived from the trailing part of the URL.
            data (bytes|bool): Raw binary content for the attachment. If provided, the attachment
                is stored with its binary payload. Set to `False` if not used.
            url (str|bool): A URL pointing to the resource. If `data` is not provided, the
                attachment is stored as a URL type. Can be set alongside `data` to keep the
                original source URL. Set to `False` if not used.
            res_id (int|bool): The record ID the attachment should be linked to. Ignored unless
                `res_model` differs from `ir.ui.view`. Set to `False` to create an unlinked attachment.
            res_model (str): The model the attachment belongs to. Attachments targeting
                `ir.ui.view` or `project.task` are public by default to support website usage.

        Returns:
            odoo.models.ir_attachment: The created or existing attachment record.

        Raises:
            odoo.exceptions.UserError: If neither `data` nor `url` is provided.

        Security:
            - Non-admin users may bypass creation rights for media dialog flows via
              `IrAttachment._can_bypass_rights_on_media_dialog`.
            - When the attachment is not public and created by a portal user, an access
              token is generated with sudo to allow use in the web editor.

        Notes:
            - `res_id` is forced to `False` when `res_model` is `ir.ui.view` to avoid
              unintended linkage.
            - Public visibility includes `project.task` to enable image usage in website task editing.
        """
        IrAttachment = request.env["ir.attachment"]

        if name.lower().endswith(".bmp"):
            # Avoid mismatch between content type and mimetype, see commit msg
            name = name[:-4]

        if not name and url:
            name = url.split("/").pop()

        if res_model != "ir.ui.view" and res_id:
            res_id = int(res_id)
        else:
            res_id = False
        # Modify to include the project.task model between the models tha make the attachment public by default
        # this is because is used in task edition in website
        attachment_data = {
            "name": name,
            "public": res_model in ["ir.ui.view", "project.task"],
            "res_id": res_id,
            "res_model": res_model,
        }

        if data:
            attachment_data["raw"] = data
            if url:
                attachment_data["url"] = url
        elif url:
            attachment_data.update(
                {
                    "type": "url",
                    "url": url,
                }
            )
        else:
            raise UserError(
                _("You need to specify either data or url to create an attachment.")
            )

        # Despite the user having no right to create an attachment, he can still
        # create an image attachment through some flows
        if (
            not request.env.is_admin()
            and IrAttachment._can_bypass_rights_on_media_dialog(**attachment_data)
        ):
            attachment = IrAttachment.sudo().create(attachment_data)
            # When portal users upload an attachment with the wysiwyg widget,
            # the access token is needed to use the image in the editor. If
            # the attachment is not public, the user won't be able to generate
            # the token, so we need to generate it using sudo
            if not attachment_data["public"]:
                attachment.sudo().generate_access_token()
        else:
            attachment = get_existing_attachment(
                IrAttachment, attachment_data
            ) or IrAttachment.create(attachment_data)

        return attachment

    @http.route()
    def remove(self, ids, **kwargs):
        """
        Remove web-based image attachments if they are unused in any view (template).

        This endpoint inspects attachments and checks whether their `local_url` is referenced
        in any `ir.ui.view` record. If an attachment is referenced, it will not be removed
        and will be reported in the return value. Otherwise, the attachment is scheduled
        for deletion and unlinked with sudo to ensure proper access rights.

        Parameters:
            ids (list[int]|list[str]): List of attachment IDs to check and potentially remove.
            **kwargs: Additional parameters passed to the route (unused).

        Returns:
            dict[int, list[dict]]: A mapping of attachment IDs which could not be removed
            to the list of views (with their names) preventing removal.

        Side Effects:
            - Calls `self._clean_context()` to sanitize the request context.
            - Unlinks attachments via `attachments_to_remove.sudo().unlink()` for those
              not referenced in any view.

        Notes:
            - HTML escaping is applied to attachment URLs to match the representation found
              in view XML (`arch_db`).
            - The search on views uses a case where the URL may appear quoted in templates.
            - Only attachments with no view references are deleted.
        """
        self._clean_context()
        Attachment = attachments_to_remove = request.env["ir.attachment"]
        Views = request.env["ir.ui.view"].sudo()

        # views blocking removal of the attachment
        removal_blocked_by = {}

        for attachment in Attachment.browse(ids):
            # in-document URLs are html-escaped, a straight search will not
            # find them
            url = tools.html_escape(attachment.local_url)
            views = Views.search(
                ["|", ("arch_db", "like", f'"{url}"'), ("arch_db", "like", f'"{url}"')]
            )

            if views:
                removal_blocked_by[attachment.id] = views.read(["name"])
            else:
                attachments_to_remove += attachment
        if attachments_to_remove:
            attachments_to_remove.sudo().unlink()
        return removal_blocked_by
