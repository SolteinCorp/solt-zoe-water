# -*- coding: utf-8 -*-
from odoo import _, api, fields, models
from odoo.exceptions import AccessError
from odoo.tools import is_html_empty


class SoltSaleSubscriptionCloseReason(models.Model):
    _name = 'solt.subscription.close.reason'
    _description = 'Subscription Close Reason'
    _order = 'sequence, id'

    name = fields.Char(
        string='Reason',
        required=True,
        translate=True,
        help="The name of the reason for closing a subscription."
    )
    sequence = fields.Integer(
        string='Sequence',
        default=10,
        help="Determines the display order of the reasons."
    )
    visible_in_portal = fields.Boolean(
        string='Visible in Portal',
        default=True,
        required=True,
        help="If enabled, this reason will be visible to customers in the portal."
    )
    retention_message = fields.Html(
        string='Retention Message',
        translate=True,
        help="Message to display when customer tries to close subscription."
    )
    retention_button_text = fields.Char(
        string='Button Text',
        translate=True,
        help="Text for the button shown with the retention message."
    )
    retention_button_link = fields.Char(
        string='Button Link',
        translate=True,
        help="URL to open when the retention button is clicked."
    )
    empty_retention_message = fields.Boolean(
        string='Empty Retention Message',
        compute='_compute_empty_retention_message',
        help="Indicates if the retention message is empty."
    )
    is_protected = fields.Boolean(
        string='Is Protected',
        default=False,
        help="Protected reasons cannot be deleted.",
    )

    @api.depends('retention_message')
    def _compute_empty_retention_message(self):
        for reason in self:
            reason.empty_retention_message = is_html_empty(reason.retention_message)

    def write(self, vals):
        """
        Override the write method to prevent updating the 'is_protected' field.

        Args:
            vals (dict): The values to write to the record.

        Returns:
            bool: True if the write was successful.
        """
        vals.pop('is_protected', None)
        return super().write(vals)

    @api.ondelete(at_uninstall=False)
    def _unlink_close_reasons(self):
        for reason in self:
            if reason.is_protected:
                raise AccessError(_(
                    "The reason '%s' is required by the Subscription application and cannot be deleted.",
                    reason.name
                ))
