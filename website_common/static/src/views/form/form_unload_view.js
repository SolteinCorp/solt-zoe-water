/** @odoo-module **/

import {formView} from "@web/views/form/form_view";
import {registry} from "@web/core/registry";
import {FormUnloadController} from "@website_common/views/form/form_unload_controller";

/**
 * Vista personalizada de formulario con soporte para eventos de descarga.
 * Extiende la vista de formulario estándar y utiliza un controlador específico.
 *
 * @const
 * @type {Object}
 * @property {Object} Controller - Controlador personalizado para gestionar eventos de descarga del formulario.
 */
export const formUnloadView = {
    ...formView,
    Controller: FormUnloadController,
};

/**
 * Registra la vista personalizada de formulario en la categoría "views" del registro.
 */
registry.category("views").add("form_unload", formUnloadView);
