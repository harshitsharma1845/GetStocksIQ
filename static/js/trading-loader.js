/**
 * Trading Platform Loading Spinner Utility - Purple Theme
 * Generates animated candlestick & orbital radar trading spinners.
 */

(function () {
    'use strict';

    /**
     * Generate HTML markup for the animated purple trading platform spinner.
     * @param {Object} options
     * @param {string} [options.size='md'] - 'sm' | 'md' | 'lg'
     * @param {string} [options.text='Loading Market Intelligence...']
     * @param {string} [options.subtext='']
     * @param {boolean} [options.centered=true]
     * @returns {string} HTML markup string
     */
    function getTradingSpinnerHTML(options = {}) {
        const size = options.size || 'md';
        const text = options.text !== undefined ? options.text : 'Loading Market Intelligence...';
        const subtext = options.subtext || '';
        const centered = options.centered !== false ? 'is-centered' : '';
        const sizeClass = size === 'sm' ? 'trading-spinner-sm' : size === 'lg' ? 'trading-spinner-lg' : '';

        const candleCount = size === 'sm' ? 3 : 5;
        let candlesHtml = '';
        for (let i = 1; i <= candleCount; i++) {
            candlesHtml += `<div class="candlestick c${i}"><div class="wick"></div><div class="body"></div></div>`;
        }

        const labelHtml = text ? `<div class="trading-spinner-label">${text}</div>` : '';
        const subtextHtml = subtext ? `<div class="trading-spinner-subtext">${subtext}</div>` : '';

        return `
            <div class="trading-spinner-container ${sizeClass} ${centered}">
                <div class="trading-spinner">
                    <div class="trading-spinner-ring"></div>
                    <div class="trading-spinner-bars">
                        ${candlesHtml}
                    </div>
                    <div class="trading-spinner-glow"></div>
                </div>
                ${labelHtml}
                ${subtextHtml}
            </div>
        `;
    }

    /**
     * Show trading spinner overlay on a container or entire viewport.
     * @param {HTMLElement|string} [target] - Target container element or selector, default is document.body
     * @param {string} [message='Loading...']
     */
    function showTradingOverlay(target, message = 'Loading Market Intelligence...') {
        const el = typeof target === 'string' ? document.querySelector(target) : (target || document.body);
        if (!el) return;

        // Remove existing overlay if present
        hideTradingOverlay(el);

        const overlay = document.createElement('div');
        overlay.className = 'trading-spinner-overlay' + (el === document.body ? ' is-fixed' : '');
        overlay.innerHTML = getTradingSpinnerHTML({ size: 'lg', text: message });
        el.style.position = el.style.position || (el === document.body ? '' : 'relative');
        el.appendChild(overlay);
    }

    /**
     * Hide and remove trading spinner overlay from a container or entire viewport.
     * @param {HTMLElement|string} [target]
     */
    function hideTradingOverlay(target) {
        const el = typeof target === 'string' ? document.querySelector(target) : (target || document.body);
        if (!el) return;
        const overlay = el.querySelector(':scope > .trading-spinner-overlay');
        if (overlay) {
            overlay.style.opacity = '0';
            setTimeout(() => overlay.remove(), 250);
        }
    }

    // Expose global methods
    window.getTradingSpinnerHTML = getTradingSpinnerHTML;
    window.showTradingOverlay = showTradingOverlay;
    window.hideTradingOverlay = hideTradingOverlay;
})();
