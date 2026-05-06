/** @odoo-module **/

import {Component} from "@odoo/owl";
import {registry} from "@web/core/registry";
import {sprintf} from "@web/core/utils/strings";
import {_t} from "@web/core/l10n/translation";

/**
 * Componente OWL que muestra una regla recursiva en formato legible por humanos.
 * Utiliza la librería rrule para interpretar la cadena de la regla.
 */
export class RecursiveRule extends Component{
    /**
     * Devuelve una representación legible de la regla recursiva.
     * @returns {string} Texto descriptivo de la regla.
     */
    get humanReadable(){
        const rule = rrule.RRule.fromString(this.props.record.data.recursive_rule_string);
        return sprintf(_t('Available: %s'), rule.toText());
    }
}

/**
 * Asigna la plantilla OWL al componente RecursiveRule.
 */
RecursiveRule.template = "website_solt_procedure.RecursiveRule";

/**
 * Registro del widget personalizado para el campo de regla recursiva.
 * Define las dependencias de campo y el componente asociado.
 */
export const recursiveRule = {
    component: RecursiveRule,
    fieldDependencies: [
        { name: "recursive_rule_string", type: "char", string: _t("Rule"), readonly: true },
    ],
};

/**
 * Añade el widget 'recursive_rule' a la categoría 'view_widgets' del registro de Odoo.
 */
registry.category("view_widgets").add("recursive_rule", recursiveRule);
