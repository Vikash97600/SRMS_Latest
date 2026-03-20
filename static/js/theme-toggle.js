/**
 * Theme Toggle JavaScript
 * Handles Light/Dark/System theme switching for Student Management System
 */

(function() {
    'use strict';

    // Theme configuration
    const THEME_KEY = 'theme';
    const THEMES = {
        LIGHT: 'light',
        DARK: 'dark',
        SYSTEM: 'system'
    };

    // Icons for each theme
    const ICONS = {
        light: 'fa-sun',
        dark: 'fa-moon',
        system: 'fa-laptop'
    };

    /**
     * Get the system preferred theme
     * @returns {string} 'light' or 'dark'
     */
    function getSystemTheme() {
        return window.matchMedia('(prefers-color-scheme: dark)').matches ? THEMES.DARK : THEMES.LIGHT;
    }

    /**
     * Get saved theme from localStorage
     * @returns {string|null} Saved theme or null
     */
    function getSavedTheme() {
        return localStorage.getItem(THEME_KEY);
    }

    /**
     * Save theme to localStorage
     * @param {string} theme - Theme to save
     */
    function saveTheme(theme) {
        localStorage.setItem(THEME_KEY, theme);
    }

    /**
     * Apply theme to the document
     * @param {string} theme - Theme to apply
     */
    function applyTheme(theme) {
        let effectiveTheme = theme;

        // If system theme, determine the actual theme
        if (theme === THEMES.SYSTEM) {
            effectiveTheme = getSystemTheme();
        }

        // Set data-theme attribute on html element
        document.documentElement.setAttribute('data-theme', effectiveTheme);

        // Update toggle button icon
        updateToggleIcon(effectiveTheme);

        // Update dropdown active state
        updateDropdownActiveState(theme);
    }

    /**
     * Update the toggle button icon based on current theme
     * @param {string} theme - Current theme
     */
    function updateToggleIcon(theme) {
        const toggleBtn = document.getElementById('theme-toggle-btn');
        if (!toggleBtn) return;

        const iconElement = toggleBtn.querySelector('i');
        if (!iconElement) return;

        // Add animation class
        toggleBtn.classList.add('animating');

        // Update icon
        iconElement.className = 'fas ' + ICONS[theme];

        // Remove animation class after animation completes
        setTimeout(() => {
            toggleBtn.classList.remove('animating');
        }, 500);
    }

    /**
     * Update dropdown active state
     * @param {string} theme - Current theme
     */
    function updateDropdownActiveState(theme) {
        const dropdownItems = document.querySelectorAll('.theme-dropdown .dropdown-item');
        dropdownItems.forEach(item => {
            const itemTheme = item.getAttribute('data-theme');
            if (itemTheme === theme) {
                item.classList.add('active');
            } else {
                item.classList.remove('active');
            }
        });
    }

    /**
     * Initialize the theme system
     */
    function init() {
        // Get saved theme or default to system
        const savedTheme = getSavedTheme();
        const theme = savedTheme || THEMES.SYSTEM;

        // Apply the theme
        applyTheme(theme);

        // Listen for system theme changes
        const mediaQuery = window.matchMedia('(prefers-color-scheme: dark)');
        mediaQuery.addEventListener('change', (e) => {
            // Only update if current theme is system
            const currentTheme = getSavedTheme() || THEMES.SYSTEM;
            if (currentTheme === THEMES.SYSTEM) {
                applyTheme(THEMES.SYSTEM);
            }
        });

        // Set up event listeners for theme buttons
        setupThemeButtons();
    }

    /**
     * Set up click handlers for theme toggle buttons
     */
    function setupThemeButtons() {
        const dropdownItems = document.querySelectorAll('.theme-dropdown .dropdown-item');
        
        dropdownItems.forEach(item => {
            item.addEventListener('click', function(e) {
                e.preventDefault();
                const theme = this.getAttribute('data-theme');
                
                if (theme) {
                    saveTheme(theme);
                    applyTheme(theme);
                }
            });
        });
    }

    // Initialize when DOM is ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }

    // Export functions for external use
    window.ThemeToggle = {
        setTheme: function(theme) {
            saveTheme(theme);
            applyTheme(theme);
        },
        getTheme: function() {
            return getSavedTheme() || THEMES.SYSTEM;
        },
        getSystemTheme: getSystemTheme
    };

})();
