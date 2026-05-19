import logging
from operator import itemgetter
from typing import Any

import werkzeug
from odoo import _, http
from odoo.addons.payment.controllers import portal as payment_portal
from odoo.addons.portal.controllers.portal import pager as portal_pager
from odoo.addons.website_common.controllers.portal import CommonPortalController
from odoo.addons.website_common.utils.urls import get_url
from odoo.exceptions import AccessError, MissingError
from odoo.http import request
from odoo.osv.expression import AND, OR
from odoo.tools import groupby as groupbyelem
from werkzeug.urls import url_encode

_logger = logging.getLogger(__name__)


def _check_message_type(message_type: str) -> str:
    """
    Check if the provided message type is valid and return it. If the message type
    is not valid, return "info" as the default message type.

    Args:
        message_type (str): The message type to check.

    Returns:
        str: The valid message type or "info" if the provided type is not valid.
    """
    return (
        message_type
        if message_type
        in [
            "primary",
            "secondary",
            "success",
            "danger",
            "warning",
            "info",
            "light",
            "dark",
        ]
        else "info"
    )


def set_flash_message(message: str, message_type: str = "info"):
    """
    Set a flash message in the user's session.

    This method adds a flash message to the session, which can be used to
    display temporary messages to the user. Flash messages are stored in
    the session under the key "flash_messages".

    Args:
        message (str): The message to be displayed.
        message_type (str, optional): The type of the message. Defaults to "info".
            Possible values are "info", "warning", "error", etc.

    Raises:
        ValueError: If the message_type is not a valid type.
    """

    if "flash_messages" not in request.session:
        request.session["flash_messages"] = []
    request.session["flash_messages"].append(
        {
            "message": message,
            "type": _check_message_type(message_type),
        }
    )
    request.session.is_dirty = True


class WebsiteSubscriptionCustomerPortal(payment_portal.PaymentPortal):
    view_data = {}

    def solt_subscription_stage_name(self, first_solt_subscription, groupby_field: str) -> tuple[int | str, str]:
        """
        Returns a tuple representing the display value and label for a given groupby field
        of a `solt.subscription` record, based on the field type.

        Args:
            first_solt_subscription: The first subscription record in the group.
            groupby_field (str): The field name to group by.

        Returns:
            tuple[int | str, str]: A tuple containing the value (id or string) and its display label.
        """
        field_name = self._solt_subscriptions_get_groupby_mapping()[groupby_field]
        field = request.env["solt.subscription"]._fields.get(field_name, None)
        if field is False:
            return "false", groupby_field
        value = first_solt_subscription[field_name]
        if not value:
            return "false", _("Not assigned")
        if field.type == "selection":
            if value == first_solt_subscription[field_name]:
                selection = dict(field._description_selection(request.env))
                value = selection.get(value, value)
            return value, value
        elif field.type == "many2one":
            return first_solt_subscription[field_name].id, first_solt_subscription[field_name].name
        elif field.type in ["date", "datetime"]:
            formatted_value = value.strftime("%Y-%m-%d %H:%M:%S") if field.type == "datetime" else value.strftime("%Y-%m-%d")
            return formatted_value, formatted_value
        elif field.type == "boolean":
            return ("yes" if first_solt_subscription[field_name] else "no", _("Yes") if first_solt_subscription[field_name] else _("No"))
        elif field.type in ["many2many", "one2many"]:
            return (
                ",".join(str(rec.id) for rec in first_solt_subscription[field_name]),
                ", ".join(rec.name for rec in first_solt_subscription[field_name]),
            )
        else:
            return first_solt_subscription[field_name], first_solt_subscription[field_name]

    @staticmethod
    def _get_searchbar_listings() -> dict[int, dict[str, Any]]:
        """
        Returns a dictionary of available listing options for the searchbar.

        Each key is the number of elements per page, and the value is a dict containing:
            - 'input': the string representation of the number of elements
            - 'label': the display label for the option
            - 'order': the order value for sorting

        Returns:
            dict: Sorted dictionary of listing options for the searchbar.
        """
        values = {
            1: {"input": "1", "label": _("1 element"), "order": 1},
            10: {"input": "10", "label": _("10 elements"), "order": 10},
            20: {"input": "20", "label": _("20 elements"), "order": 20},
            40: {"input": "40", "label": _("40 elements"), "order": 40},
            80: {"input": "80", "label": _("80 elements"), "order": 80},
            160: {"input": "160", "label": _("160 elements"), "order": 160},
        }
        return dict(sorted(values.items(), key=lambda item: item[1]["order"]))

    @staticmethod
    def _get_portal_solt_subscription_default_domain(partner) -> list:
        """
        Returns the default domain for filtering `solt.subscription` records
        for the portal view, based on the given partner.

        Args:
            partner: The partner record for which to generate the domain.

        Returns:
            list: A domain list to filter subscriptions by partner and state.
        """
        return [
            ("partner_id", "in", [partner.id, partner.commercial_partner_id.id]),
            ("state", "in", ["active", "closed"]),
        ]

    def _prepare_home_portal_values(self, counters: dict) -> dict:
        """
        Prepare the values to be displayed on the portal home page.

        This method extends the parent implementation to include the subscription count
        for the current user, if the user has read access to `solt.subscription`.
        The count is based on the default domain for the user's partner.

        Args:
            counters (dict): A dictionary of counters to be included in the portal values.

        Returns:
            dict: The updated values dictionary including the subscription count if applicable.
        """
        values = super()._prepare_home_portal_values(counters)
        if "subscription_count" in counters:
            if request.env["solt.subscription"].check_access_rights("read", raise_exception=False):
                partner = request.env.user.partner_id
                values["subscription_count"] = request.env["solt.subscription"].search_count(
                    self._get_portal_solt_subscription_default_domain(partner)
                )
            else:
                values["subscription_count"] = 0
        return values

    def _solt_subscriptions_get_searchbar_filters(self) -> dict[str, dict]:
        """
        Build and return the searchbar filters for the `solt.subscription` portal view.

        This method combines a default "All" filter, date-based filters (added via
        `CommonPortalController.add_date_searchbar_filters`), and any additional filters
        defined in `self.view_data['filters']`.

        Returns:
            dict[str, dict]: A dictionary mapping filter keys to their filter definitions.
        """
        searchbar_filters = {
            "all": {"label": _("All"), "domain": [], "sequence": 1},
        }
        filters, date_filters = self.view_data["filters"]
        for date_filter in date_filters.values():
            searchbar_filters.update(
                CommonPortalController.add_date_searchbar_filters(
                    date_filter["name"], date_filter["label"], date_filter["sequence"], request.env.context.get("lang", "en_US")
                )
            )
        searchbar_filters.update(filters)
        return searchbar_filters

    def _get_solt_subscriptions_search_domain(self, search_in: str, search: str) -> list:
        """
        Build a search domain for `solt.subscription` records based on the search input.

        Args:
            search_in (str): The search field or option to filter by.
            search (str): The search string to match.
        Returns:
            list: The constructed Odoo domain for searching subscriptions.
        """
        search_domain = []
        for search_in_option, search_field in self.view_data["inputs_mapping"].items():
            if search_in in search_in_option:
                search_domain = OR([search_domain, [(search_field, "ilike", search)] if isinstance(search_field, str) else search_field])
        return search_domain

    def _solt_subscriptions_get_groupby_mapping(self) -> dict:
        """
        Returns the mapping dictionary for groupby fields used in `solt.subscription` views.

        Returns:
            dict: A dictionary mapping groupby keys to their corresponding field names.
        """
        return {k: v for k, v in self.view_data["group_by_mapping"].items() if ":month" not in k}

    @staticmethod
    def _change_previous_next_record_url(values: dict, solt_subscription, url: str = "/my/subscriptions") -> dict:
        """
        Update the `values` dictionary with URLs for the previous and next subscription records.

        This method uses the session history of viewed `solt.subscription` records to determine
        the previous and next records relative to the current one. It then constructs URLs for navigation
        and adds them to the `values` dictionary under the keys `prev_record` and `next_record`.

        Args:
            values (dict): The dictionary to update with navigation URLs.
            solt_subscription: The current subscription record.
            url (str, optional): The base URL for the subscription detail page. Defaults to "/my/subscriptions".

        Returns:
            dict: The updated `values` dictionary with `prev_record` and `next_record` URLs if applicable.
        """
        history = request.session.get("my_solt_subscriptions_history", [])
        try:
            current_solt_subscription_index = history.index(solt_subscription.id)
        except ValueError:
            return values

        total_solt_subscriptions = len(history)
        solt_subscription_url = "%s/%s"

        values["prev_record"] = current_solt_subscription_index != 0 and solt_subscription_url % (
            url,
            history[current_solt_subscription_index - 1],
        )
        values["next_record"] = current_solt_subscription_index < total_solt_subscriptions - 1 and solt_subscription_url % (
            url,
            history[current_solt_subscription_index + 1],
        )
        return values

    def _solt_subscription_get_page_view_values(self, solt_subscription, access_token: str | None = None, **kwargs: dict) -> dict:
        """
        Prepare and return the values dictionary for rendering the page view of a `solt.subscription` record.

        Args:
            solt_subscription: The subscription record to display.
            access_token (str, optional): Access token for authentication, if required.
            **kwargs (dict): Additional keyword arguments, such as 'tab' to specify the active tab.

        Returns:
            dict: The values dictionary to be used in the page view template.
        """
        history = "my_solt_subscriptions_history"
        values = {
            "page_name": "support_issue",
            "support_issue": solt_subscription,
            "user": request.env.user,
            "preview_object": solt_subscription,
            "tab": kwargs.get("tab", "information"),
        }
        values = self._get_page_view_values(solt_subscription, access_token, values, history, False, **kwargs)
        return values

    def _get_solt_subscription(self, access_token: str, subscription_id: int) -> tuple[Any, Any]:
        """
        Retrieve a `solt.subscription` record with access control and error handling.

        Args:
            access_token (str): The access token for authentication.
            subscription_id (int): The ID of the subscription to retrieve.

        Returns:
            tuple: (solt_subscription_sudo, redirect or None)
                - The subscription record (or an empty recordset if not found).
                - A redirect response if access is denied or the record is missing, otherwise None.

        Raises:
            werkzeug.exceptions.NotFound: If the record is not found and the user is logged in.
        """
        logged_in = not request.env.user.sudo()._is_public()
        solt_subscription_sudo = request.env["solt.subscription"]
        try:
            solt_subscription_sudo = self._document_check_access("solt.subscription", subscription_id, access_token)
        except AccessError:
            if not logged_in:
                url = f"/my/subscriptions/{subscription_id}"
                return solt_subscription_sudo, werkzeug.utils.redirect(f"/web/login?redirect={werkzeug.urls.url_quote(url)}")
            else:
                raise werkzeug.exceptions.NotFound()
        except MissingError:
            set_flash_message(
                _("The selected subscription dont exists."),
                "danger",
            )
            return solt_subscription_sudo, request.redirect("/my/subscriptions")
        return solt_subscription_sudo, None

    @staticmethod
    def _get_solt_subscription_payment_values(solt_subscription_sudo) -> dict:
        """
        Retrieve payment provider and token information for a given subscription.

        Args:
            solt_subscription_sudo: The subscription record (with sudo access).

        Returns:
            dict: A dictionary containing:
                - 'providers': Compatible payment providers for the subscription.
                - 'tokens': Available payment tokens for the partner.
                - 'fees_by_provider': An empty dict (placeholder for provider fees).
        """
        providers_sudo = (
            request.env["payment.provider"]
            .sudo()
            ._get_compatible_providers(
                company_id=solt_subscription_sudo.company_id.id,
                partner_id=solt_subscription_sudo.partner_id.id,
                amount=solt_subscription_sudo.recurring_total,
                currency_id=solt_subscription_sudo.currency_id.id,
            )
        )
        tokens_sudo = (
            request.env["payment.token"]
            .sudo()
            ._get_available_tokens(
                providers_sudo.ids,
                solt_subscription_sudo.partner_id.id,
            )
        )
        return {
            "providers": providers_sudo,
            "tokens": tokens_sudo,
            "fees_by_provider": {},
        }

    def _solt_subscription_entries_display(
        self,
        page: int = 1,
        date_begin: str | None = None,
        date_end: str | None = None,
        sortby: str | None = None,
        filterby: str | None = None,
        search: str | None = None,
        search_in: str = "all",
        groupby: str | None = None,
        listing: int = 80,
        template: str = "website_solt_recurring_payment.portal_my_solt_subscriptions",
        query_with_sudo: bool = False,
        **kw,
    ) -> http.Response:
        base_url = "/my/subscriptions"
        values = self._prepare_portal_layout_values()
        solt_subscription_object = request.env["solt.subscription"].sudo() if query_with_sudo else request.env["solt.subscription"]
        domain = self._get_portal_solt_subscription_default_domain(request.env.user.partner_id)
        self.view_data = CommonPortalController.extract_search_view_to_searchbar(
            "solt.subscription", include_fields_on_search_panel=True, include_first_level_filters_only=True, search=search
        )
        searchbar_sortings = {
            "name": {"label": _("Name"), "order": "name, id"},
            "company": {"label": _("Company"), "order": "company_id desc, id"},
            "customer": {"label": _("Customer"), "order": "partner_id, id"},
            "price_list": {"label": _("Price List"), "order": "pricelist_id, id"},
            "plan": {"label": _("Plan"), "order": "plan_id, id"},
            "state": {"label": _("State"), "order": "state, id"},
            "start": {"label": _("Start Date"), "order": "start_date, id"},
            "next_invoice": {"label": _("Next Invoice Date"), "order": "next_invoice_date, id"},
        }
        searchbar_inputs = {
            "all": {"label": _("Search in All"), "input": "all"},
        }
        searchbar_inputs.update(self.view_data["inputs"])
        searchbar_groupby = {
            "none": {"label": _("None"), "input": "none"},
        }
        searchbar_groupby.update({k: v for k, v in self.view_data["group_by"].items() if ":month" not in k})
        # Listing Items Settings
        listings = self._get_searchbar_listings()
        try:
            listing = int(listing)
        except ValueError:
            listing = 80
        default_items_per_page = 80
        self._items_per_page = listing if listing in listings else default_items_per_page
        layout = kw.get("layout", "list")
        tab = kw.get("tab", "solt_subscriptions")
        if not sortby:
            sortby = "start"
        sort_order = searchbar_sortings[sortby]["order"]
        groupby_mapping = self._solt_subscriptions_get_groupby_mapping()
        groupby_field = groupby_mapping.get(groupby, None)
        group_by_field = solt_subscription_object._fields.get(groupby_field, False) if groupby_field else False
        if groupby_field is not None and groupby_field not in solt_subscription_object._fields:
            raise ValueError(_("The field '%s' does not exist in the targeted model", groupby_field))
        order = f"{groupby_field}, {sort_order}" if groupby_field else sort_order
        searchbar_filters = self._solt_subscriptions_get_searchbar_filters()
        filterby = filterby or "all"
        filter_data: dict = searchbar_filters.get(filterby, searchbar_filters["all"])
        if date_begin and date_end:
            domain += [("create_date", ">", date_begin), ("create_date", "<=", date_end)]
        if filter_data and "domain" in filter_data:
            domain += filter_data["domain"]
        if search and search_in:
            domain = AND([domain, self._get_solt_subscriptions_search_domain(search_in, search)])
        solt_subscriptions_count = solt_subscription_object.search_count(domain)
        pager = portal_pager(
            url=base_url,
            url_args={
                "sortby": sortby,
                "search_in": search_in,
                "search": search,
                "groupby": groupby,
                "filterby": filterby,
                "listing": listing,
                "layout": layout,
            },
            total=solt_subscriptions_count,
            page=page,
            step=self._items_per_page,
        )
        solt_subscriptions = solt_subscription_object.search(domain, order=order, limit=self._items_per_page, offset=pager["offset"])
        request.session["my_solt_subscriptions_history"] = solt_subscriptions.ids[:100]
        group = groupby_mapping.get(groupby)
        if group:
            grouped_solt_subscriptions = [solt_subscription_object.concat(*g) for k, g in groupbyelem(solt_subscriptions, itemgetter(group))]
        else:
            grouped_solt_subscriptions = [solt_subscriptions] if solt_subscriptions else []

        def keep_the_url(**kwargs: dict) -> str:
            """
            Build a URL with the current page and filter parameters, preserving or overriding them with kwargs.

            Args:
                **kwargs (dict): Optional keyword arguments to override or add URL parameters.
                    - 'url' (str, optional): The base URL to use. Defaults to base_url if not provided or not a string.

            Returns:
                str: The constructed URL with all relevant query parameters.
            """
            url = kwargs.get("url", base_url)
            if not isinstance(url, str):
                url = base_url
            return get_url(
                url,
                page,
                {
                    "date_begin": date_begin,
                    "date_end": date_end,
                    "sortby": sortby,
                    "search": search,
                    "search_in": search_in,
                    "groupby": groupby,
                    "listing": listing,
                    "layout": layout,
                }
                | kwargs,
            )

        values.update(
            {
                "solt_subscriptions": solt_subscriptions,
                "grouped_solt_subscriptions": grouped_solt_subscriptions,
                "page_name": "all_solt_subscriptions",
                "pager": pager,
                "default_url": base_url,
                "groupby_mapping": groupby_mapping,
                "searchbar_sortings": searchbar_sortings,
                "search_in": search_in,
                "search": search,
                "sortby": sortby,
                "groupby": groupby or "none",
                "groupby_type": group_by_field.type if group_by_field else "char",
                "filterby": filterby,
                "searchbar_inputs": searchbar_inputs,
                "searchbar_groupby": searchbar_groupby,
                "searchbar_filters": searchbar_filters,
                "layout": layout,
                "solt_subscriptions_count": solt_subscriptions_count,
                "listing": listing,
                "searchbar_listings": listings,
                "keep_the_url": keep_the_url,
                "type": type,
                "additional_title": _("My Subscriptions"),
                "tab": tab,
                "stage_name": self.solt_subscription_stage_name,
            }
        )
        return request.render(template, values)

    @http.route(["/my/subscriptions", "/my/subscriptions/page/<int:page>"], type="http", auth="user", website=True)
    def my_solt_subscriptions(
        self,
        page: int = 1,
        date_begin: str | None = None,
        date_end: str | None = None,
        sortby: str | None = None,
        filterby: str | None = None,
        search: str | None = None,
        search_in: str = "all",
        groupby: str | None = None,
        listing: int = 80,
        **kw,
    ) -> http.Response:
        """
        Handles the portal route for displaying a paginated list of `solt.subscription` records.

        Args:
            page (int): The current page number.
            date_begin (str, optional): Filter subscriptions created after this date.
            date_end (str, optional): Filter subscriptions created before or on this date.
            sortby (str, optional): Field to sort the results by.
            filterby (str, optional): Filter to apply to the results.
            search (str, optional): Search string to filter subscriptions.
            search_in (str): Field or option to search in.
            groupby (str, optional): Field to group the results by.
            listing (int): Number of items per page.
            **kw: Additional keyword arguments.

        Returns:
            http.Response: The rendered portal page with the list of subscriptions.
        """
        return self._solt_subscription_entries_display(page, date_begin, date_end, sortby, filterby, search, search_in, groupby, listing, **kw)

    @http.route(
        ["/my/subscriptions/<int:subscription_id>", "/my/subscriptions/<int:subscription_id>/<access_token>"],
        type="http",
        auth="public",
        website=True,
    )
    def my_solt_subscription(
        self, subscription_id: int, access_token: str | None = None, message: str = "", message_class: str = "", **kw
    ) -> http.Response:
        solt_subscription_sudo, redirection = self._get_solt_subscription(access_token, subscription_id)
        if redirection:
            return redirection
        partner = request.env.user.partner_id
        enable_token_management = partner in (solt_subscription_sudo.partner_id.child_ids | solt_subscription_sudo.partner_id)
        display_close = solt_subscription_sudo.user_closable and solt_subscription_sudo.state == "active"
        is_follower = partner in solt_subscription_sudo.message_follower_ids.partner_id
        # Get unpaid invoices
        unpaid_invoices = solt_subscription_sudo.invoice_ids.filtered(
            lambda inv: inv.state == "posted" and inv.move_type == "out_invoice" and inv.payment_state not in ["paid", "in_payment", "reversed"]
        )
        first_unpaid_invoice = unpaid_invoices[:1] if unpaid_invoices else False

        # Check if online payment is enabled
        # payment_providers = (
        #     request.env["payment.provider"]
        #     .sudo()
        #     .search(
        #         [
        #             ("state", "=", "enabled"),
        #             ("code", "!=", "manual"),
        #         ]
        #     )
        # )
        # online_payment_enabled = bool(payment_providers)

        token_management_url_params = {
            "manage_subscription": True,
            "subscription_id": subscription_id,
            "access_token": access_token,
        }

        backend_url = "/web#" + url_encode(
            {
                "model": solt_subscription_sudo._name,
                "id": solt_subscription_sudo.id,
                "action": solt_subscription_sudo._get_portal_return_action().id,
                "view_type": "form",
            }
        )

        portal_page_values = {
            "page_name": "subscription",
            "subscription": solt_subscription_sudo,
            "display_close": display_close,
            "is_follower": is_follower,
            "close_reasons": request.env["solt.subscription.close.reason"].search([("visible_in_portal", "=", True)]),
            "user": request.env.user,
            "message": message,
            "message_class": message_class,
            "enable_token_management": enable_token_management,
            "token_management_url": f"/my/payment_method?{url_encode(token_management_url_params)}",
            "backend_url": backend_url,
            "unpaid_invoices": unpaid_invoices,
            "first_unpaid_invoice": first_unpaid_invoice,
            "online_payment_enabled": False,
        }

        portal_page_values = self._get_page_view_values(
            solt_subscription_sudo, access_token, portal_page_values, "my_solt_subscriptions_history", False
        )

        payment_form_values = {
            "default_token_id": solt_subscription_sudo.payment_token_id.id,
            "subscription_id": solt_subscription_sudo.id,
        }

        payment_context = {
            "amount": solt_subscription_sudo.recurring_total,
            "partner_id": solt_subscription_sudo.partner_id.id,
        }

        rendering_context = {
            **self._get_solt_subscription_payment_values(solt_subscription_sudo),
            **portal_page_values,
            **payment_form_values,
            **payment_context,
        }
        return request.render("website_solt_recurring_payment.portal_my_solt_subscription", rendering_context)

    @http.route(["/my/subscriptions/<int:subscription_id>/close"], type="http", methods=["POST"], auth="public", website=True)
    def portal_subscription_close(self, subscription_id, access_token=None, **kw):
        subscription_sudo, redirection = self._get_solt_subscription(access_token, subscription_id)
        if redirection:
            return redirection

        # Helper function to build redirect URL without empty token
        def _redirect_url(sub_id, token):
            url = f"/my/subscriptions/{sub_id}"
            if token:
                url += f"?access_token={token}"
            return url

        if subscription_sudo.user_closable:
            close_reason_id = int(kw.get("close_reason_id", 0))
            close_reason = request.env["solt.subscription.close.reason"].browse(close_reason_id)
            cancel_mode = kw.get("cancel_mode", "honor")
            if cancel_mode not in ("honor", "refund", "bulk_ship"):
                cancel_mode = "honor"
            # Non-prepaid subscriptions can only use 'honor' mode.
            if cancel_mode != "honor" and not subscription_sudo.is_prepaid:
                cancel_mode = "honor"
            if close_reason:
                try:
                    subscription_sudo.sudo().action_cancel_subscription(
                        cancel_mode=cancel_mode,
                        close_reason_id=close_reason.id,
                        closing_note=kw.get("closing_text") or None,
                    )
                except Exception:
                    _logger.exception(
                        "Error cancelling subscription %s (mode=%s)",
                        subscription_sudo.id,
                        cancel_mode,
                    )

        return request.redirect(_redirect_url(subscription_id, access_token))

    @http.route(["/my/subscriptions/<int:subscription_id>/renew"], type="http", methods=["POST"], auth="public", website=True)
    def portal_subscription_renew(self, subscription_id, access_token=None, **kw):
        subscription_sudo, redirection = self._get_solt_subscription(access_token, subscription_id)
        if redirection:
            return redirection

        action_type = kw.get("action_type", "renew")

        # Helper function to build redirect URL without empty token
        def _redirect_url(sub_id, token):
            url = f"/my/subscriptions/{sub_id}"
            if token:
                url += f"?access_token={token}"
            return url

        # Renew: reactivate directly via action_reopen (next_invoice_date = today).
        if action_type == "renew":
            if not subscription_sudo.user_extend or subscription_sudo.state != "closed":
                return request.redirect(_redirect_url(subscription_id, access_token))
            try:
                subscription_sudo.sudo().action_reopen()
            except Exception as e:
                _logger.exception("Error reactivating subscription: %s", str(e))
            return request.redirect(_redirect_url(subscription_id, access_token))

        # Change plan: keep the existing wizard flow.
        if action_type == "change_plan":
            if not subscription_sudo.plan_id.related_plan_ids or subscription_sudo.state != "active":
                return request.redirect(_redirect_url(subscription_id, access_token))
            wizard = (
                request.env["solt.subscription.renew.wizard"]
                .sudo()
                .create(
                    {
                        "subscription_id": subscription_sudo.id,
                        "action_type": action_type,
                        "new_plan_id": int(kw.get("new_plan_id")) if kw.get("new_plan_id") else False,
                    }
                )
            )
            try:
                wizard.sudo().action_confirm()
            except Exception as e:
                _logger.exception("Error executing subscription action: %s", str(e))
            return request.redirect(_redirect_url(subscription_id, access_token))

        return request.redirect(_redirect_url(subscription_id, access_token))

    @http.route("/my/subscriptions/assign_token/<int:subscription_id>", type="json", auth="user")
    def portal_subscription_assign_token(self, subscription_id, token_id, access_token=None):
        subscription_sudo, redirection = self._get_solt_subscription(access_token, subscription_id)
        if redirection:
            return redirection

        partner_id = request.env.user.partner_id

        token_sudo = (
            request.env["payment.token"]
            .sudo()
            .search(
                [
                    ("id", "=", token_id),
                    ("partner_id", "child_of", partner_id.commercial_partner_id.id),
                    ("active", "=", True),
                ]
            )
        )

        if not token_sudo:
            raise werkzeug.exceptions.NotFound()

        subscription_sudo.payment_token_id = token_sudo
        return True

    @http.route(["/my/subscriptions/<int:subscription_id>/assign_payment_method"], type="http", methods=["POST"], auth="public", website=True)
    def portal_subscription_assign_payment_method(self, subscription_id, access_token=None, token_id=None, **kw):
        """Assign a payment method to subscription."""
        subscription_sudo, redirection = self._get_solt_subscription(access_token, subscription_id)
        if redirection:
            return redirection

        # Helper function to build redirect URL without empty token
        def _redirect_url(sub_id, token):
            url = f"/my/subscriptions/{sub_id}"
            if token:
                url += f"?access_token={token}"
            return url

        if token_id:
            try:
                token_sudo = request.env["payment.token"].sudo().browse(int(token_id))
                if token_sudo and token_sudo.partner_id.id == subscription_sudo.partner_id.commercial_partner_id.id:
                    subscription_sudo.sudo().payment_token_id = token_sudo
                    subscription_sudo.message_post(body=_("Payment method updated from portal"))
            except (ValueError, TypeError) as e:
                _logger.warning("Failed to assign payment method token %s: %s", token_id, str(e))

        return request.redirect(_redirect_url(subscription_id, access_token))
