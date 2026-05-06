/** @odoo-module **/

import publicWidget from "@web/legacy/js/public/public_widget";


publicWidget.registry.FullScreenHeight.include({
    /**
     * Computes the ideal height for an element based on the window height and its position
     * within the DOM structure. This method accounts for various scenarios such as modals,
     * fixed headers, hidden headers, and connected users.
     *
     * @returns {number} The calculated ideal height in pixels.
     */
    _computeIdealHeight() {
        const windowHeight = $(window).outerHeight();
        if (this.inModal) {
            return (windowHeight - $('#wrapwrap').position().top);
        }
        // Doing it that way allows to considerer fixed headers, hidden headers,
        // connected users, ...
        let firstContentEl = $('#wrapwrap > #main-content #main-content-right > main > :first-child')[0]; // first child to consider the padding-top of main
        if (!firstContentEl) {
            firstContentEl = $('#wrapwrap main > :first-child')[0];
        }
        // When a modal is open, we remove the "modal-open" class from the body.
        // This is because this class sets "#wrapwrap" and "<body>" to
        // "overflow: hidden," preventing the "closestScrollable" function from
        // correctly recognizing the scrollable element closest to the element
        // for which the height needs to be calculated. Without this, the
        // "mainTopPos" variable would be incorrect.
        const modalOpen = document.body.classList.contains("modal-open");
        document.body.classList.remove("modal-open");
        const mainTopPos = firstContentEl.getBoundingClientRect().top + $(firstContentEl.parentNode).closestScrollable()[0].scrollTop;
        document.body.classList.toggle("modal-open", modalOpen);
        return (windowHeight - mainTopPos);
    },
});
