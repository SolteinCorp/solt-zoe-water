/** @odoo-module **/

import publicWidget from "@web/legacy/js/public/public_widget";
import {renderToString} from "@web/core/utils/render";
import {throttleForAnimation} from "@web/core/utils/timing";
import { evaluateBooleanExpr } from "@web/core/py_js/py";

/**
 * @param {...HTMLElement} els
 */
export const hide = (...els) => els.forEach((el) => el.classList.add("d-none"));

/**
 * @param {...HTMLElement} els
 */
export const show = (...els) => els.forEach((el) => el.classList.remove("d-none"));

publicWidget.registry.statusField = publicWidget.Widget.extend({
    selector: '.o_field_statusbar.adjustable',
    events: {
        'click .o_arrow_button:not(.o_arrow_button_current, .dropdown-toggle, .dropdown)': '_onChangeValue',
        'click .dropdown-item:not(.active)': '_onClickDropdownItem',
    },
    /**
     * Inicializa el widget de la barra de estado.
     * Llama al método _super para la inicialización base y enlaza los servicios necesarios.
     * Define la estructura de los elementos de la barra de estado en `this.items`.
     *
     * Servicios enlazados:
     * - ui: Servicio de interfaz de usuario para bloquear/desbloquear la UI.
     * - orm: Servicio ORM para llamadas al backend.
     * - notification: Servicio para mostrar notificaciones al usuario.
     */
    init() {
        this._super.apply(this, arguments);
        this.ui = this.bindService("ui");
        this.orm = this.bindService("orm");
        this.items = {
            all: [],
            after: [],
            before: []
        };
        this.notification = this.bindService("notification");
    },
    /**
     * Método que se ejecuta antes de que el widget comience.
     * Inicializa las propiedades principales del widget a partir de los atributos de datos del elemento DOM.
     * También enlaza los elementos del DOM necesarios y obtiene la lista de todos los ítems de la barra de estado.
     * Además, agrega un listener para ajustar los elementos visibles al cambiar el tamaño de la ventana.
     *
     * @returns {Promise<void>} Una promesa que se resuelve cuando la inicialización ha finalizado.
     */
    willStart() {
        const self = this;
        return Promise.resolve(undefined).then(() => {
            self.method = self.el.dataset.resMethod || undefined;
            self.field = self.el.dataset.resField || undefined;
            self.model = self.el.dataset.resModel || undefined;
            self.id = self.el.dataset.resId || 0;
            self.readonly = evaluateBooleanExpr(self.el.dataset.readonly || 1);
            self.$root = self.$('#status-root');
            self.$after = self.$('#status-after');
            self.$before = self.$('#status-before');
            self.$dropdown = self.$('#status-dropdown');
            self.items.all = self._getAllItems();
            window.addEventListener('resize', throttleForAnimation(self._adjustVisibleElements.bind(self)));
        });
    },
    /**
     * Inicia el widget de la barra de estado.
     * Llama al método _super para la inicialización base y luego ajusta los elementos visibles,
     * oculta la superposición y muestra el componente.
     *
     * @returns {Promise<void>} Una promesa que se resuelve cuando la inicialización ha finalizado.
     */
    start() {
        const self = this;
        return this._super.apply(this, arguments).then(() => {
            self._adjustVisibleElements();
            self._hideOverlay();
            self._show();
        });
    },

    /**
     * Destruye el widget de la barra de estado.
     * Elimina el listener de redimensionamiento de ventana y llama al método _super para la destrucción base.
     */
    destroy() {
        window.removeEventListener('resize', throttleForAnimation(this._adjustVisibleElements.bind(this)));
        this._super.apply(this, arguments);
    },
    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------
    /**
     * El metodo _adjustVisibleElements ajusta la visibilidad de los elementos en el componente de la barra de estado.
     * Se asegura de que los elementos no se desborden y maneja la visibilidad de los botones y menús desplegables
     * según sea necesario
     * @private
     */
    _adjustVisibleElements() {
        const itemEls = [
            ...this.$root[0].querySelectorAll(".o_arrow_button:not(.dropdown-toggle)"),
        ];
        const selectedIndex = itemEls.findIndex((el) =>
            el.classList.contains("o_arrow_button_current")
        );
        const itemsBefore = itemEls.slice(selectedIndex + 1).reverse();
        const itemsAfter = itemEls.slice(0, Math.max(selectedIndex, 0)).reverse();
        show(...itemEls);
        hide(this.$dropdown[0], this.$before[0], this.$after[0]);
        itemEls[0]?.classList.add("o_first");
        // Reset items variables
        this.items.before = [];
        this.items.after = [];
        const itemsToAssign = [...this._getAllItems()];
        while (this._areItemsWrapping()) {
            if (itemsBefore.length) {
                // Case 1: elements before can be hidden
                show(this.$before[0]);
                hide(itemsBefore.shift());
                this.items.before.push(itemsToAssign.shift());
            } else if (itemsAfter.length) {
                // Case 2: elements before are hidden, elements after can be hidden
                show(this.$after[0]);
                hide(itemsAfter.pop());
                this.items.after.unshift(itemsToAssign.pop());
            } else {
                // Last resort: no elements can be hidden => fallback to single dropdown
                show(this.$dropdown[0]);
                hide(this.$before[0], this.$after[0], ...itemEls);
                break;
            }
        }
        this._renderAfterBeforeDropdowns(true);
        this._renderAfterBeforeDropdowns(false);
    },
    /**
     * Verifica si los elementos de la barra de estado se están desbordando.
     * Compara la altura del contenedor raíz con la altura del primer elemento visible.
     *
     * @private
     * @returns {boolean} Verdadero si los elementos se están desbordando, falso en caso contrario.
     */
    _areItemsWrapping() {
        const root = this.$root[0];
        const firstItem = root.querySelector(":scope > .o_arrow_button:not(.d-none)");
        if (!firstItem) {
            return false;
        }
        const {height: currentHeight} = root.getBoundingClientRect();
        const {height: targetHeight} = firstItem.getBoundingClientRect();
        return currentHeight > targetHeight;
    },
    async _changeElementAttribute(value) {
        if (this.model && this.field && this.method) {
            this.ui.block();
            const result = await this.orm.call(
                this.model,
                this.method,
                [
                    parseInt(this.id),
                    this.field,
                    value
                ],
                {}
            ).catch(error => {
                let title = "error title", message = "error message";
                if ("message" in error) {
                    title = error.message;
                }
                if ("data" in error && "message" in error.data) {
                    message = error.data.message;
                }
                return {'success': false, 'message': message, 'title': title};
            });
            this.ui.unblock();
            if (!result.success) {
                this.notification.add(
                    result.message,
                    {
                        title: result.title,
                        type: "danger",
                    });
            }
            return result.success;
        }
    },
    /**
     * Obtiene todos los elementos de la barra de estado.
     * Si ya se han cargado previamente, los devuelve directamente.
     * De lo contrario, los obtiene del DOM y los devuelve en orden inverso.
     *
     * @returns {Array} Lista de elementos de la barra de estado.
     */
    _getAllItems() {
        if (this.items.all.length > 0) {
            return this.items.all;
        } else {
            const items = [];
            this.$('.o_arrow_button[data-value]').each((i, e) => {
                items.push({
                    value: parseInt(e.dataset.value),
                    label: $(e).html().trim(),
                    isSelected: $(e).hasClass("o_arrow_button_current"),
                });
            });
            return items.reverse();
        }
    },
    /**
     * Oculta la superposición en la barra de estado.
     * Añade la clase `d-none` al elemento de superposición para hacerlo invisible.
     */
    _hideOverlay() {
        this.$root.find('.overlay').addClass('d-none');
    },
    /**
     * Renderiza los elementos del menú desplegable "after" y "before" en la barra de estado.
     *
     * @param {boolean} [after=true] - Indica si se deben renderizar los elementos del menú "after" (true) o "before" (false).
     */
    _renderAfterBeforeDropdowns(after = true) {
        this.$('.dropdown-menu.' + (after ? 'after' : 'before')).empty().html(renderToString('website_common.status_dropdown', {
            readonly: this.readonly,
            items: after ? this.items.after : this.items.before,
        }));
    },
    /**
     * Marca el elemento seleccionado en la barra de estado.
     * Actualiza la propiedad `isSelected` de cada elemento en `this.items.all`
     * para reflejar el valor seleccionado.
     *
     * @param {number|string} value - El valor del elemento que se va a seleccionar.
     * @returns {Array} Lista vacía (reservado para posibles usos futuros).
     */
    _selectElement(value) {
        for (const allElement of this.items.all) {
            allElement.isSelected = allElement.value === value;
        }
        return [...this.items.all];
    },
    /**
     * Muestra el elemento raíz de la barra de estado.
     * Establece la opacidad del elemento raíz a 1 para hacerlo visible.
     */
    _show() {
        this.$root.css('opacity', '1');
    },
    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------
    /**
     * Maneja el evento de cambio de valor en la barra de estado.
     * Actualiza el valor del elemento seleccionado y realiza una llamada para cambiar el atributo del elemento.
     *
     * @param {Event} ev - El evento de clic que desencadena el cambio de valor.
     */
    async _onChangeValue(ev) {
        ev.preventDefault();
        let value = parseInt(ev.target.dataset.value);
        if (Number.isNaN(value)) {
            value = ev.target.dataset.value;
        }
        const success = await this._changeElementAttribute(value);
        if (success) {
            this.items.all = this._selectElement(value);
            this.$('.o_arrow_button').removeClass('o_arrow_button_current').removeAttr('disabled');
            $(ev.target).addClass('o_arrow_button_current').attr('disabled', 'disabled');
        }
    },
    /**
     * Maneja el evento de clic en un elemento del menú desplegable.
     * Actualiza el valor del elemento seleccionado y ajusta la visibilidad de los elementos.
     *
     * @param {Event} ev - El evento de clic que desencadena la selección del elemento del menú desplegable.
     */
    async _onClickDropdownItem(ev) {
        ev.preventDefault();
        let value = parseInt(ev.target.dataset.value);
        if (Number.isNaN(value)) {
            value = ev.target.dataset.value;
        }
        const success = await this._changeElementAttribute(value);
        if (success) {
            this.items.all = this._selectElement(value);
            this.$('.o_arrow_button').removeClass('o_arrow_button_current').removeAttr('disabled');
            this.$('.o_arrow_button[data-value=' + value + ']').addClass('o_arrow_button_current').attr('disabled', 'disabled');
            this._adjustVisibleElements();
        }
    },
});
