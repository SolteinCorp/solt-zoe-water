/** @odoo-module **/

import {_t} from "@web/core/l10n/translation";

/**
 * Valida una imagen según las opciones proporcionadas.
 *
 * @param {File} file - El archivo de imagen a validar.
 * @param {Object} [options={}] - Opciones de validación.
 * @param {number} [options.maximum_size_mb=5242880] - Tamaño máximo permitido en bytes.
 * @param {string[]} [options.allowed_mime_type_ids=['image/jpeg', 'image/png', 'image/gif', 'image/webp']] - Tipos de archivo permitidos.
 * @param {number} [options.minimum_width=0] - Ancho mínimo permitido en píxeles.
 * @param {number} [options.minimum_height=0] - Altura mínima permitida en píxeles.
 * @param {number} [options.maximum_width=Infinity] - Ancho máximo permitido en píxeles.
 * @param {number} [options.maximum_height=Infinity] - Altura máxima permitida en píxeles.
 * @returns {Promise<Object>} - Promesa que resuelve con un objeto que indica si la validación fue exitosa y un mensaje.
 */
export function validateImage(file, options = {}) {
    // Opciones predeterminadas de validación
    const defaultOptions = {
        maximum_size_mb: 5 * 1024 * 1024,
        allowed_mime_type_ids: ['image/jpeg', 'image/png', 'image/gif', 'image/webp'],
        minimum_width: 0,
        minimum_height: 0,
        maximum_width: Infinity,
        maximum_height: Infinity
    };

    // Combina las opciones predeterminadas con las opciones proporcionadas
    const config = {...defaultOptions, ...options};

    // Retorna una promesa para la validación de la imagen
    return new Promise((resolve) => {
        // Verifica si se proporcionó un archivo
        if (!file) {
            resolve({valid: false, message: _t('No file provided')});
            return;
        }
        // Verifica si el tipo de archivo es permitido
        if (!config.allowed_mime_type_ids.includes(file.type)) {
            resolve({
                valid: false,
                message: _t('Invalid file type. Allowed types: %s', config.allowed_mime_type_ids.join(', '))
            });
            return;
        }
        // Verifica si el tamaño del archivo excede el tamaño máximo permitido
        if (file.size > config.maximum_size_mb) {
            resolve({
                valid: false,
                message: _t('File size exceeds the maximum allowed size of %sMB', (config.maximum_size_mb / (1024 * 1024)).toFixed(2)),
            });
            return;
        }

        // Verifica las dimensiones de la imagen si se especificaron restricciones
        if (config.minimum_width > 0 || config.minimum_height > 0 || config.maximum_width < Infinity || config.maximum_height < Infinity) {
            const objectUrl = URL.createObjectURL(file);
            const img = new Image();
            img.onload = () => {
                URL.revokeObjectURL(objectUrl);
                const width = img.width;
                const height = img.height;
                // Verifica si las dimensiones de la imagen son demasiado pequeñas
                if (width < config.minimum_width || height < config.minimum_height) {
                    resolve({
                        valid: false,
                        message: _t('Image dimensions too small. Minimum required: %sx%spx', config.minimum_width, config.minimum_height),
                        dimensions: {width, height}
                    });
                    return;
                }
                // Verifica si las dimensiones de la imagen son demasiado grandes
                if (width > config.maximum_width || height > config.maximum_height) {
                    resolve({
                        valid: false,
                        message: _t('Image dimensions too large. Maximum allowed: %sx%spx',config.maximum_width, config.maximum_height),
                        dimensions: {width, height}
                    });
                    return;
                }
                // La imagen es válida
                resolve({
                    valid: true,
                    message: _t('Image validation successful'),
                    dimensions: {width, height}
                });
            };
            // Maneja el error de carga de la imagen
            img.onerror = () => {
                URL.revokeObjectURL(objectUrl);
                resolve({valid: false, message: _t('Failed to load image for validation')});
            };
            img.src = objectUrl;
        } else {
            // La imagen es válida si no hay restricciones de dimensiones
            resolve({valid: true, message: _t('Image validation successful')});
        }
    });
}
