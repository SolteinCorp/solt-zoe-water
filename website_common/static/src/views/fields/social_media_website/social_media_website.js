/** @odoo-module **/

import { Component, onWillStart, reactive, useChildSubEnv, useState } from '@odoo/owl';
import { useChildRef, useService } from "@web/core/utils/hooks";
import {CharField,charField} from "@web/views/fields/char/char_field";
import { registry } from "@web/core/registry";
import { _t } from "@web/core/l10n/translation";

export default class SocialMediaWebsiteField extends CharField {
    static template = "website_common.SocialMediaWebsiteField";

    /**
     * Sets up the component by initializing required services and fetching website data.
     *
     * Services used:
     * - `website`: Service to interact with website-related functionalities.
     * - `orm`: Service to interact with the Odoo ORM.
     * - `ui`: Service to manage UI-related functionalities.
     * - `notification`: Service to display notifications to the user.
     *
     * Lifecycle hooks:
     * - `onWillStart`: Fetches website data before the component starts.
     */
    setup() {
        super.setup();

        this.website = useService("website");
        this.orm = useService("orm");
        this.ui = useService("ui");
        this.notification = useService("notification");

        onWillStart(async () => {
            await this.website.fetchWebsites();
        });
    }

    /**
     * Gets the current website object.
     *
     * @returns {Object} The current website object.
     */
    get currentWebsite() {
        return this.website.currentWebsite;
    }

    /**
     * Getter for the URL value of the social media website field.
     * Retrieves the value of the field specified by `this.props.name`
     * from the record's data.
     *
     * @returns {string} The URL value of the social media website field.
     */
    get urlValue() {
        return this.props.record.data[this.props.name];
    }

    /**
     * Getter method to retrieve the list of websites associated with the current website instance.
     *
     * @returns {Array} An array of website objects.
     */
    get websites() {
        return this.website.websites;
    }

    /**
     * Applies a new value to a field in the model instance and handles the result.
     *
     * This method sends the updated value to the server, processes the response,
     * and displays appropriate notifications based on the outcome.
     *
     * @async
     * @param {any} value - The new value to apply. If not an array, it will be wrapped in an array.
     * @returns {Promise<void>} Resolves when the operation is complete.
     *
     * @throws {Error} Logs an error to the console if the server call fails.
     *
     * Notifications:
     * - Displays a success message if the field value is updated successfully.
     * - Displays an error message if the field does not exist or if the update fails.
     */
    async _applyValue(value) {
        if (!Array.isArray(value)) {
            value = [value];
        }
        this.ui.block();
        const result = await this.orm.call(
            'website', 'apply_field_value', [value, this.props.name, this.urlValue]
        ).catch(error => {
            console.error(error);
            return 0;
        });
        this.ui.unblock();
        if (result === -1) {
            this.notification.add(
                _t("The field to change in model instance doesn’t exist."),
                {
                    title: _t("Error"),
                    type: "danger",
                }
            );
        } else if (result === 0) {
            this.notification.add(
                _t('Error trying to update the field value.'),
                {
                    title: _t("Error"),
                    type: "danger",
                }
            );
        } else {
            this.notification.add(
                _t('Field value updated successfully.'),
                {
                    title: _t("Success"),
                    type: "success",
                }
            );
        }
    }

    /**
     * Applies the current value to all websites.
     * This method retrieves the IDs of all websites and applies the value to each of them.
     *
     * @async
     * @returns {Promise<void>} Resolves when the value has been applied to all websites.
     */
    async applyToAll() {
        await this._applyValue(this.websites.map(w => w.id));
    }

    /**
     * Applies the current value to the specified website.
     *
     * @param {Object} website - The website object to which the value will be applied.
     * @param {number} website.id - The unique identifier of the website.
     * @returns {Promise<void>} A promise that resolves when the value has been successfully applied.
     */
    async applyToWebsite(website) {
        await this._applyValue([website.id]);
    }
}

export const socialMediaWebsiteField = {
    ...charField,
    component: SocialMediaWebsiteField,
};

registry.category("fields").add("social_media_website", socialMediaWebsiteField);
