/** @odoo-module **/

import publicWidget from "@web/legacy/js/public/public_widget";
import {renderToString} from "@web/core/utils/render";
import {throttleForAnimation} from "@web/core/utils/timing";
import {hide, show} from "./status";

/**
 * Widget para manejar la funcionalidad de colapso de pestañas en la barra de navegación.
 */
publicWidget.registry.tabCollapse = publicWidget.Widget.extend({
    selector: '.o_tab_collapse',
    events: {
        'click .nav-link:not(.dropdown-toggle)': '_onActiveChange',
        'click .dropdown-item': '_onActiveChange',
    },
    /**
     * Inicializa el widget y sus propiedades.
     */
    init() {
        this.items = {
            all: [],
            after: [],
            before: []
        };
        this.supportNavItem = true;
        this.$after = undefined;
        this.$before = undefined;
        this.$dropdown = undefined;
    },
    /**
     * Método que se ejecuta antes de que el widget comience.
     * Configura los elementos de navegación y agrega los menús desplegables si es necesario.
     */
    willStart() {
        const self = this;
        return this._super.apply(this, arguments).then(() => {
            self.supportNavItem = self.hasNavItem();
            self.items.all = self._getAllItems();
            if (self.supportNavItem && !self.$before) {
                self._addDropdownElement(false);
            }
            if (self.supportNavItem && !self.$after) {
                self._addDropdownElement(true);
            }
            window.addEventListener('resize', throttleForAnimation(self._adjustVisibleElements.bind(self)));
        });
    },
    /**
     * Método que se ejecuta cuando el widget comienza.
     * Ajusta la visibilidad de los elementos de navegación.
     */
    start() {
        const self = this;
        return this._super.apply(this, arguments).then(() => {
            self._adjustVisibleElements();
        });
    },
    /**
     * Método que se ejecuta cuando el widget se destruye.
     * Elimina el evento de redimensionamiento de la ventana.
     */
    destroy() {
        window.removeEventListener('resize', throttleForAnimation(this._adjustVisibleElements.bind(this)));
        this._super.apply(this, arguments);
    },
    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------
    /**
     * Agrega un elemento de menú desplegable a la barra de navegación.
     * Dependiendo del parámetro `after`, el elemento se agrega antes o después de los elementos existentes.
     *
     * @param {boolean} [after=true] - Indica si el elemento se agrega después (true) o antes (false) de los elementos existentes.
     */
    _addDropdownElement(after = true) {
        if (!after) {
            this.$before = $(renderToString('website_common.tabs_dropdown', {
                positionClass: after ? 'after' : 'before',
                readonly: false,
                items: after ? this.items.after : this.items.before,
            }));
            this.$before.insertBefore(this.$('.nav-item:not(.after, .before, .dropdown):first-child'));
        } else {
            this.$after = $(renderToString('website_common.tabs_dropdown', {
                positionClass: after ? 'after' : 'before',
                readonly: false,
                items: after ? this.items.after : this.items.before,
            }));
            this.$after.insertBefore(this.$('.nav-item:not(.after, .before, .dropdown):first-child'));
            this.$after.appendTo(this.$el);
        }
    },
    /**
     * Ajusta la visibilidad de los elementos en la barra de navegación.
     * Asegura que los elementos no se desborden y maneja la visibilidad de los botones y menús desplegables según sea necesario.
     *
     * @private
     */
    _adjustVisibleElements() {
        const itemEls = [
            ...this.el.querySelectorAll(".nav-item:not(.dropdown, .after, .before)"),
        ];
        const selectedIndex = this.items.all.findIndex((el) => el.isSelected);
        const itemsBefore = itemEls.slice(0, Math.max(selectedIndex, 0));
        const itemsAfter = itemEls.slice(selectedIndex + 1);
        show(...itemEls);
        hide(this.$before[0], this.$after[0]);
        // Reiniciar variables de elementos
        this.items.before = [];
        this.items.after = [];
        const itemsToAssign = [...this._getAllItems()];
        while (this._areItemsWrapping()) {
            if (itemsBefore.length) {
                // Caso 1: los elementos anteriores pueden ocultarse
                show(this.$before[0]);
                hide(itemsBefore.shift());
                this.items.before.unshift(itemsToAssign.shift());
            } else if (itemsAfter.length) {
                // Caso 2: los elementos anteriores están ocultos, los elementos posteriores pueden ocultarse
                show(this.$after[0]);
                hide(itemsAfter.pop());
                this.items.after.push(itemsToAssign.pop());
            } else {
                // Último recurso: no se pueden ocultar elementos => recurrir a un único menú desplegable
                show(this.$before[0]);
                hide(this.$after[0], ...itemEls);
                this.items.before = this.items.all;
                break;
            }
        }
        this._renderAfterBeforeDropdowns(true);
        this._renderAfterBeforeDropdowns(false);
    },
    /**
     * Verifica si los elementos de la barra de navegación se están desbordando.
     * Compara la altura del contenedor raíz con la altura del primer elemento visible.
     *
     * @private
     * @returns {boolean} Verdadero si los elementos se están desbordando, falso en caso contrario.
     */
    _areItemsWrapping() {
        const firstItem = this.el.querySelector(":scope > .nav-item:not(.d-none)");
        if (!firstItem) {
            return false;
        }
        const {height: currentHeight} = this.el.getBoundingClientRect();
        const {height: targetHeight} = firstItem.getBoundingClientRect();
        return currentHeight > targetHeight;
    },
    /**
     * Obtiene todos los elementos de navegación que no son menús desplegables.
     * Si los elementos ya han sido cargados previamente, los devuelve directamente.
     * De lo contrario, los obtiene del DOM y los devuelve en forma de una lista de objetos.
     *
     * @returns {Array} Lista de objetos que representan los elementos de navegación.
     * Cada objeto contiene las siguientes propiedades:
     * - `value` {number|string}: El ID del elemento o 0 si no tiene ID.
     * - `label` {string}: El texto del elemento.
     * - `isSelected` {boolean}: Indica si el elemento está seleccionado.
     * - `href` {string}: El enlace del elemento.
     */
    _getAllItems() {
        if (this.items.all.length > 0) {
            return this.items.all;
        } else {
            const items = [];
            this.$('a.nav-link:not(.dropdown-toggle)').each((i, e) => {
                items.push({
                    value: e.id || 0,
                    label: e.textContent.trim(),
                    isSelected: e.classList.contains("active"),
                    href: $(e).attr('href'),
                });
            });
            return items;
        }
    },
    /**
     * Renderiza los elementos de los menús desplegables antes y después de los elementos visibles.
     *
     * @param {boolean} [after=true] - Indica si se renderizan los elementos después (true) o antes (false) de los elementos visibles.
     */
    _renderAfterBeforeDropdowns(after = true) {
        this.$('.dropdown-menu.' + (after ? 'after' : 'before')).empty().html(renderToString('website_common.tabs_dropdown.items', {
            readonly: false,
            items: after ? this.items.after : this.items.before,
        }));
    },
    /**
     * Selecciona un elemento de navegación basado en su valor.
     * Marca el elemento correspondiente como seleccionado y actualiza la clase CSS `active`.
     *
     * @param {string} value - El valor del elemento a seleccionar (enlace).
     * @returns {Array} Lista actualizada de todos los elementos de navegación.
     */
    _selectElement(value) {
        for (const allElement of this.items.all) {
            allElement.isSelected = allElement.href === value;
        }
        this.$('.nav-item:not(.after, .before, .dropdown) > .nav-link').removeClass('active');
        this.$('.nav-link[href="' + value + '"]').addClass('active');
        return [...this.items.all];
    },
    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------
    /**
     * Verifica si hay elementos de navegación en el componente.
     *
     * @returns {boolean} Verdadero si hay al menos un elemento de navegación, falso en caso contrario.
     */
    hasNavItem() {
        return this.$('.nav-item').length > 0;
    },
    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------
    /**
     * Maneja el evento de cambio de pestaña activa.
     * Previene el comportamiento predeterminado del evento, selecciona el elemento correspondiente
     * y ajusta la visibilidad de los elementos en la barra de navegación.
     *
     * @param {Event} ev - El evento de clic que desencadena el cambio de pestaña activa.
     */
    _onActiveChange(ev) {
        ev.preventDefault();
        const href = $(ev.target).attr('href');
        this.items.all = this._selectElement(href);
        this._adjustVisibleElements();
    },
});
