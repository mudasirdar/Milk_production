/** @odoo-module **/

import { Component, onMounted, useState } from "@odoo/owl";
import publicWidget from "@web/legacy/js/public/public_widget";

/**
 * Property Filter Widget
 * Handles property search filtering and interactions
 */
publicWidget.registry.PropertyFilter = publicWidget.Widget.extend({
    selector: '.property-listing-page',
    events: {
        'click .property-card': '_onPropertyCardClick',
        'submit .property-search-form': '_onSearchSubmit',
        'change .property-filter-select': '_onFilterChange',
        'click .clear-filters': '_onClearFilters',
    },

    /**
     * @override
     */
    start: function () {
        this._super.apply(this, arguments);
        this._initializeFilters();
    },

    /**
     * Initialize filter interactions
     * @private
     */
    _initializeFilters: function () {
        // Auto-submit form on filter change (optional)
        const autoSubmit = this.$el.data('auto-submit');
        if (autoSubmit) {
            this.$('.property-filter-select').on('change', () => {
                this.$('.property-search-form').submit();
            });
        }

        // Store filter state in session storage
        this._restoreFilterState();
    },

    /**
     * Handle property card click
     * @private
     * @param {Event} ev
     */
    _onPropertyCardClick: function (ev) {
        const $card = $(ev.currentTarget);
        const propertyUrl = $card.data('property-url');
        if (propertyUrl && !$(ev.target).is('a, button')) {
            window.location.href = propertyUrl;
        }
    },

    /**
     * Handle search form submission
     * @private
     * @param {Event} ev
     */
    _onSearchSubmit: function (ev) {
        // Save filter state before submission
        this._saveFilterState();
    },

    /**
     * Handle filter change
     * @private
     * @param {Event} ev
     */
    _onFilterChange: function (ev) {
        // Save to session storage
        this._saveFilterState();
    },

    /**
     * Handle clear filters click
     * @private
     * @param {Event} ev
     */
    _onClearFilters: function (ev) {
        ev.preventDefault();
        sessionStorage.removeItem('property_filters');
        window.location.href = '/properties';
    },

    /**
     * Save filter state to session storage
     * @private
     */
    _saveFilterState: function () {
        const filterData = {};
        this.$('.property-search-form').find('input, select').each(function () {
            const $input = $(this);
            if ($input.val()) {
                filterData[$input.attr('name')] = $input.val();
            }
        });
        sessionStorage.setItem('property_filters', JSON.stringify(filterData));
    },

    /**
     * Restore filter state from session storage
     * @private
     */
    _restoreFilterState: function () {
        const filterData = sessionStorage.getItem('property_filters');
        if (filterData) {
            try {
                const filters = JSON.parse(filterData);
                Object.keys(filters).forEach(key => {
                    const $input = this.$(`[name="${key}"]`);
                    if ($input.length) {
                        $input.val(filters[key]);
                    }
                });
            } catch (e) {
                console.error('Error restoring filter state:', e);
            }
        }
    },
});

/**
 * Property Image Gallery Widget
 * Handles property image gallery interactions
 */
publicWidget.registry.PropertyImageGallery = publicWidget.Widget.extend({
    selector: '.property-detail-page',
    events: {
        'click .property-image-thumbnail': '_onThumbnailClick',
    },

    /**
     * Handle thumbnail click to change main image
     * @private
     * @param {Event} ev
     */
    _onThumbnailClick: function (ev) {
        ev.preventDefault();
        const $thumbnail = $(ev.currentTarget);
        const imageUrl = $thumbnail.data('image-url');

        if (imageUrl) {
            this.$('.property-main-image').attr('src', imageUrl);

            // Update active state
            this.$('.property-image-thumbnail').removeClass('active');
            $thumbnail.addClass('active');
        }
    },
});

/**
 * Property Inquiry Form Widget
 * Handles property inquiry form interactions
 */
publicWidget.registry.PropertyInquiryForm = publicWidget.Widget.extend({
    selector: '.property-inquiry-form',
    events: {
        'submit form': '_onFormSubmit',
    },

    /**
     * Handle form submission
     * @private
     * @param {Event} ev
     */
    _onFormSubmit: function (ev) {
        const $form = $(ev.currentTarget);
        const $submitBtn = $form.find('button[type="submit"]');

        // Disable submit button to prevent double submission
        $submitBtn.prop('disabled', true).text('Sending...');

        // Form will submit normally, this just provides UX feedback
        setTimeout(() => {
            if (!$form.data('submitted')) {
                $submitBtn.prop('disabled', false).html('<i class="fa fa-envelope me-2"></i>Send Inquiry');
            }
        }, 5000);
    },
});

/**
 * Property Price Range Slider (optional enhancement)
 */
publicWidget.registry.PropertyPriceRange = publicWidget.Widget.extend({
    selector: '.property-price-range-slider',

    /**
     * @override
     */
    start: function () {
        this._super.apply(this, arguments);
        this._initializePriceSlider();
    },

    /**
     * Initialize price range slider
     * @private
     */
    _initializePriceSlider: function () {
        const $minPrice = this.$('#min_price');
        const $maxPrice = this.$('#max_price');
        const $display = this.$('.price-range-display');

        const updateDisplay = () => {
            const min = $minPrice.val() || 'Any';
            const max = $maxPrice.val() || 'Any';
            $display.text(`${min} - ${max}`);
        };

        $minPrice.on('input', updateDisplay);
        $maxPrice.on('input', updateDisplay);

        updateDisplay();
    },
});

export default {
    PropertyFilter: publicWidget.registry.PropertyFilter,
    PropertyImageGallery: publicWidget.registry.PropertyImageGallery,
    PropertyInquiryForm: publicWidget.registry.PropertyInquiryForm,
    PropertyPriceRange: publicWidget.registry.PropertyPriceRange,
};
