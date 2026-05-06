/** @odoo-module **/

import publicWidget from "@web/legacy/js/public/public_widget";

publicWidget.registry.portalSolteinSearchPanel = publicWidget.Widget.extend({
    selector: '.dropdown-menu-searchbar',
    events: {
        'click .dropdown-item': '_onDropdownItemClick',
        'submit': '_onSubmit',
    },

    /**
     * @override
     */
    start: function () {
        var def = this._super.apply(this, arguments);
        this._adaptSearchLabel(this.$('.dropdown-item.active'));
        return def;
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @private
     */
    _adaptSearchLabel: function (elem) {
        var $label = $(elem).clone();
        $label.find('span.nolabel').remove();
        this.$('input[name="search"]').attr('placeholder', $label.text().trim());
    },
    /**
     * @private
     */
    _search: function () {
        var search = new URL(window.location).searchParams;
        search.set("search_in", this.$('.dropdown-item.active').attr('href')?.replace('#', '') || "");
        search.set("search", this.$('input[name="search"]').val());
        window.location.search = search.toString();
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @private
     */
    _onDropdownItemClick: function (ev) {
        ev.preventDefault();
        ev.stopPropagation();
        var $item = $(ev.currentTarget);
        $item.closest('.dropdown-menu').find('.dropdown-item').removeClass('active');
        $item.addClass('active');

        this._adaptSearchLabel(ev.currentTarget);
    },
    /**
     * @private
     */
    _onSubmit: function (ev) {
        ev.preventDefault();
        this._search();
    },
});
