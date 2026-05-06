# Copyright 2026 Soltein SA. de CV.
# License LGPL-3 or later (http://www.gnu.org/licenses/lgpl.html)

from collections import defaultdict

from odoo import models
from psycopg2 import sql


class ResPartner(models.Model):
    _inherit = "res.partner"

    def signup_get_auth_param(self):
        """
        Returns authentication parameters for portal user signup.

        If the current user belongs to the portal group and the
        'website_common.allow_portal_users_chatter_messaging' config parameter is enabled,
        returns a defaultdict for authentication parameters.
        Otherwise, delegates to the parent implementation.
        """
        params = self.env["ir.config_parameter"].sudo()
        value = (
            params.get_param(
                "website_common.allow_portal_users_chatter_messaging", "False"
            )
            == "True"
        )
        if self.env.user.has_group("base.group_portal") and value:
            return defaultdict(dict)
        return super().signup_get_auth_param()

    def attachment_ids_followed_by_partner(self):
        """
        Retrieve attachment IDs that are related to records followed by the current partner.

        This method finds all attachments (ir_attachment) that are associated with records
        (identified by res_id and res_model) that the current partner is following via
        mail followers.

        :return: List of attachment IDs (integers) that match the criteria
        :rtype: list[int]
        :raises: AccessError if the user doesn't have permissions to access attachments
        :note: This method uses ensure_one() and requires a single partner record context
        """
        self.ensure_one()
        query = sql.SQL("""
            select ia.id
            from ir_attachment ia
            inner join mail_followers mf
            on ia.res_id=mf.res_id and ia.res_model=mf.res_model
            where mf.partner_id={pid}
        """).format(pid=sql.Literal(self.id))
        self.env.cr.execute(query)
        return [row[0] for row in self.env.cr.fetchall()]
