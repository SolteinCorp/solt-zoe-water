/** @odoo-module */

import publicWidget from "@web/legacy/js/public/public_widget";

publicWidget.registry.tableAccountResize = publicWidget.Widget.extend({
    selector: '.o_portal_my_doc_table',
    /**
     * Inicializa la funcionalidad de redimensionamiento de columnas
     * en la tabla seleccionada. Utiliza el plugin colResizable para
     * permitir el ajuste dinámico del ancho de las columnas mediante
     * arrastre en vivo.
     *
     * @returns {Promise} Promesa que resuelve cuando el widget ha iniciado.
     */
    start: function () {
        const def = this._super.apply(this, arguments);
        this.$el.colResizable({
            liveDrag: true,
            draggingClass: 'col-dragging',
            gripInnerHtml: "<div class='grip'></div>",
            minWidth: 30
        });
        return def;
    }
});
