/** @odoo-module **/

/**
 * Retrieves the value of a CSS variable from the specified target element.
 *
 * @param {string} name - The name of the CSS variable (e.g., '--my-var').
 * @param {Element} [target=document.documentElement] - The target element to get the variable from.
 * @returns {string} The trimmed value of the CSS variable, or an empty string if not found.
 */
export function getCssVar(name, target = document.documentElement) {
    const val = getComputedStyle(target).getPropertyValue(name);
    return val ? val.trim() : '';
}
