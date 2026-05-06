/** @odoo-module **/

import {FormController} from "@web/views/form/form_controller";


/**
 * Controlador personalizado para manejar el evento de descarga de formulario.
 * Extiende FormController para agregar una advertencia si hay cambios no guardados.
 */
export class FormUnloadController extends FormController {
    /**
     * Se ejecuta antes de descargar la página.
     * Si el formulario tiene cambios no guardados, muestra una advertencia al usuario.
     * @param {Event} ev - El evento beforeunload del navegador.
     */
    async beforeUnload(ev) {
        const dirty = await this.model.root.isDirty();
        if (dirty) {
            ev.returnValue = "Unsaved changes";
        }
    }
}
