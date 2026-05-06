/** @odoo-module **/

import {Component} from "@odoo/owl";
import {localization} from "@web/core/l10n/localization";
import {registry} from "@web/core/registry";
import {standardWidgetProps} from "@web/views/widgets/standard_widget_props";
import {_t} from "@web/core/l10n/translation";

/**
 * Take a string that represents a JSON and parse it before trying to convert it to an object.
 * Replace single quotes with double quotes and try to convert.
 * @param {String} labels string that represents a JSON
 * @returns {{}}
 */
function parseLabels(labels) {
    try {
        labels = JSON.parse(labels.replace(/'/g, '"'));
    } catch (e) {
        console.error(e);
        labels = {};
    }
    return labels;
}

/**
 * Create a range of numbers from zero to the previous number of length
 * @param {Number} length the maximum number of elements
 * @returns {number[]}
 */
function range(length, start = 0) {
    return Array.from({length: length}, (_, index) => index + start);
}

/**
 * Base component for management of char fields that will handle multiple values and store
 * as value 1,value 2,...,value n
 */
export class StringSeparated extends Component {
    /**
     * @override
     */
    setup() {
        super.setup();
        this.previousSelection = [];
    }

    //--------------------------------------------------------------------------
    // Properties
    //--------------------------------------------------------------------------

    /**
     * Returns true if all labels are selected, false otherwise
     * @property
     * @returns {this is any[]}
     */
    get allSelected() {
        return Object.values(this.data).every(i => i);
    }

    /**
     * Returns an object with keys representing labels and value representing whether they are selected or not.
     * @property
     * @returns {{[p: string]: any}}
     */
    get data() {
        return Object.fromEntries(this.labelKeys.map(k => [k.toString(), this.selectedValues.includes(k.toString())]));
    }

    /**
     * Returns an object with keys representing the label value and value representing the title
     * @property
     * @returns {*}
     */
    get labels() {
        return this.props.labels;
    }

    /**
     * Get all label object keys (values)
     * @property
     * @returns {string[]}
     */
    get labelKeys() {
        return Object.keys(this.props.labels).map(k => k.trim());
    }

    /**
     * Takes the value from the record data and parses it, splitting it by comma.
     * e.x. 1,2,3,4 => ['1', '2', '3', '4']
     * @property
     * @returns {*|*[]}
     */
    get selectedValues() {
        const v = this.props.record.data[this.props.field_name];
        if ([undefined, false, ''].includes(v)) {
            return [];
        }
        return this.props.record.data[this.props.field_name].split(',').map(e => e.trim());
    }

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * Take an array of values and store them in the record data
     * @param selectedValues
     * @private
     */
    _saveValues(selectedValues) {
        this.props.record.update({[this.props.field_name]: selectedValues.join(',')});
    }

    //--------------------------------------------------------------------------
    // Publiix
    //--------------------------------------------------------------------------

    /**
     * Clear the values from the record data
     * @public
     */
    clear() {
        this._saveValues([]);
    }

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * Method executed when the user clicks the Select All button.
     */
    onAllSelectedChange() {
        let toApply;
        if (this.allSelected) {
            toApply = this.previousSelection;
        } else {
            this.previousSelection = this.selectedValues;
            toApply = this.labelKeys.map(k => k.toString());
        }
        this._saveValues(toApply);
    }

    /**
     * Method that is executed when the user clicks an item in the list and the selected value of that selected
     * item in the record data. element in the record data
     * @param v
     */
    onChange(v) {
        let selectedValues = this.selectedValues;
        if (selectedValues.includes(v.toString())) {
            selectedValues = selectedValues.filter(s => s !== v.toString());
        } else {
            selectedValues.push(v.toString());
        }
        this._saveValues(selectedValues);
    }
}

StringSeparated.template = "website_solt_procedure.StringSeparated";
StringSeparated.props = {
    ...standardWidgetProps,
    field_name: String,
    labels: {type: Object, optional: true},
    title: {type: String, optional: true},
};

/**
 * Días de la semana en formato abreviado.
 * @type {string[]}
 */
const WEEKDAYS = ["MO", "TU", "WE", "TH", "FR", "SA", "SU"];

/**
 * Componente para gestionar campos de tipo string separados para días de la semana.
 * Extiende de StringSeparated.
 */
export class WeekDaysStringSeparated extends StringSeparated {
    /**
     * Devuelve las claves de las etiquetas (días de la semana).
     * @returns {string[]}
     */
    get labelKeys() {
        return WEEKDAYS;
    }

    /**
     * Devuelve un objeto con las claves y los nombres de los días de la semana.
     * @returns {Object}
     */
    get labels() {
        return this.zipObject(this.labelKeys, this.weekDays);
    }

    /**
     * Devuelve el array de días de la semana.
     * @returns {string[]}
     */
    get weekDays() {
        return WEEKDAYS;
    }

    /**
     * Une dos arrays en un array de pares clave-valor.
     * @param {Array} keys
     * @param {Array} values
     * @returns {Array}
     */
    zip(keys, values) {
        return Array.from({length: Math.min(keys.length, values.length)}, (_, i) => [keys[i], values[i]]);
    }

    /**
     * Convierte dos arrays en un objeto usando los elementos de keys como claves y values como valores.
     * @param {Array} keys
     * @param {Array} values
     * @returns {Object}
     */
    zipObject(keys, values) {
        return keys.reduce((obj, key, index) => (obj[key] = values[index], obj), {});
    }
}

/**
 * Meses del año en formato abreviado.
 * @type {string[]}
 */
const MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];

/**
 * Componente para gestionar campos de tipo string separados para meses.
 * Extiende de StringSeparated.
 */
export class MonthsStringSeparated extends StringSeparated {
    /**
     * Devuelve las claves de las etiquetas (números de mes iniciando en 1).
     * @returns {number[]}
     */
    get labelKeys() {
        return range(12, 1);
    }

    /**
     * Devuelve un objeto con las claves y los nombres de los meses.
     * @returns {Object}
     */
    get labels() {
        return this.zipObject(this.labelKeys, MONTHS);
    }

    /**
     * Une dos arrays en un array de pares clave-valor.
     * @param {Array} keys
     * @param {Array} values
     * @returns {Array}
     */
    zip(keys, values) {
        return Array.from({length: Math.min(keys.length, values.length)}, (_, i) => [keys[i], values[i]]);
    }

    /**
     * Convierte dos arrays en un objeto usando los elementos de keys como claves y values como valores.
     * @param {Array} keys
     * @param {Array} values
     * @returns {Object}
     */
    zipObject(keys, values) {
        return keys.reduce((obj, key, index) => (obj[key] = values[index], obj), {});
    }
}

/**
 * Componente para gestionar campos de tipo string separados para días del mes.
 * Extiende de StringSeparated.
 */
export class MonthDaysStringSeparated extends StringSeparated {
    /**
     * Devuelve las claves de las etiquetas (números de día del 1 al 31).
     * @returns {number[]}
     */
    get labelKeys() {
        return range(31, 1);
    }

    /**
     * Devuelve un objeto con las claves y los números de los días del mes.
     * @returns {Object}
     */
    get labels() {
        return this.zipObject(this.labelKeys, range(31).map(k => k + 1));
    }

    /**
     * Une dos arrays en un array de pares clave-valor.
     * @param {Array} keys
     * @param {Array} values
     * @returns {Array}
     */
    zip(keys, values) {
        return Array.from({length: Math.min(keys.length, values.length)}, (_, i) => [keys[i], values[i]]);
    }

    /**
     * Convierte dos arrays en un objeto usando los elementos de keys como claves y values como valores.
     * @param {Array} keys
     * @param {Array} values
     * @returns {Object}
     */
    zipObject(keys, values) {
        return keys.reduce((obj, key, index) => (obj[key] = values[index], obj), {});
    }
}

/**
 * Configuración base para el widget stringSeparated.
 * @type {Object}
 */
export const stringSeparated = {
    component: StringSeparated, extractProps: ({attrs}) => {
        return {
            field_name: attrs.field_name || '',
            labels: [undefined, ''].includes(attrs.labels) ? {} : parseLabels(attrs.labels),
            title: attrs.string.trim() || _t('Select Elements'),
        };
    },
};

/**
 * Configuración para el widget de días de la semana.
 * @type {Object}
 */
export const weekDaysstringSeparated = {
    ...stringSeparated, component: WeekDaysStringSeparated,
};

/**
 * Configuración para el widget de meses.
 * @type {Object}
 */
export const monthsStringSeparated = {
    ...stringSeparated, component: MonthsStringSeparated,
};

/**
 * Configuración para el widget de días del mes.
 * @type {Object}
 */
export const monthDaysStringSeparated = {
    ...stringSeparated, component: MonthDaysStringSeparated,
};

/**
 * Registro de los widgets personalizados en la categoría view_widgets.
 */
registry.category("view_widgets").add("string_separated", stringSeparated);
registry.category("view_widgets").add("weekdays_string_separated", weekDaysstringSeparated);
registry.category("view_widgets").add("months_string_separated", monthsStringSeparated);
registry.category("view_widgets").add("month_days_string_separated", monthDaysStringSeparated);
