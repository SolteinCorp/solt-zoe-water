/** @odoo-module **/

/**
 * Analiza un error y extrae el título y el mensaje.
 *
 * @param {Object} error - El objeto de error a analizar.
 * @param {string} [error.message] - El mensaje de error principal.
 * @param {Object} [error.data] - Datos adicionales del error.
 * @param {string} [error.data.message] - Mensaje de error adicional.
 * @returns {Object} Un objeto que contiene el título y el mensaje del error.
 */
export function parseError(error) {
    let title = "Error", message = "error message";
    if ("message" in error) {
        title = error.message;
    }
    if ("data" in error && "message" in error.data) {
        message = error.data.message;
    }
    return {title, message};
}
