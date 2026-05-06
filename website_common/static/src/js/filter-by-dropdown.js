/** @odoo-module **/

// Prevent dropdown from closing when clicking inside collapsible items
document.querySelectorAll('.dropdown-menu').forEach(dropdown => {
    dropdown.addEventListener('click', function(e) {
        if (e.target.closest('.has-submenu') || e.target.closest('.submenu')) {
            e.stopPropagation();
        }
    });
});
