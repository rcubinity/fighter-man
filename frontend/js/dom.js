/**
 * @file dom.js
 * @description DOM caching utility for efficient element access
 */

/**
 * DOM cache helper - caches elements on first access to avoid repeated getElementById calls
 * @type {Object}
 */
const DOM = {
    _cache: {},

    /**
     * Get a cached DOM element by ID
     * @param {string} id - Element ID
     * @returns {HTMLElement|null}
     */
    get(id) {
        if (!this._cache[id]) {
            this._cache[id] = document.getElementById(id);
        }
        return this._cache[id];
    },

    /**
     * Clear the cache (useful if DOM changes dynamically)
     */
    clear() {
        this._cache = {};
    }
};
