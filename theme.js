const THEME_STORAGE_KEY = 'theme-preference';

function getPreferredTheme() {
    const savedTheme = localStorage.getItem(THEME_STORAGE_KEY);
    if (savedTheme === 'light' || savedTheme === 'dark') {
        return savedTheme;
    }

    return window.matchMedia('(prefers-color-scheme: light)').matches ? 'light' : 'dark';
}

function applyTheme(theme) {
    document.documentElement.setAttribute('data-theme', theme);

    const toggle = document.querySelector('[data-theme-toggle]');
    if (toggle) {
        const isLight = theme === 'light';
        toggle.setAttribute('aria-pressed', String(isLight));
        toggle.setAttribute('aria-label', isLight ? 'Switch to dark theme' : 'Switch to light theme');
        toggle.textContent = isLight ? 'Dark mode' : 'Light mode';
    }
}

function toggleTheme() {
    const currentTheme = document.documentElement.getAttribute('data-theme') || getPreferredTheme();
    const nextTheme = currentTheme === 'light' ? 'dark' : 'light';
    localStorage.setItem(THEME_STORAGE_KEY, nextTheme);
    applyTheme(nextTheme);
}

function initializeThemeToggle() {
    applyTheme(getPreferredTheme());

    const toggle = document.querySelector('[data-theme-toggle]');
    if (!toggle) {
        return;
    }

    toggle.addEventListener('click', toggleTheme);
    applyTheme(document.documentElement.getAttribute('data-theme') || getPreferredTheme());
}

window.initializeThemeToggle = initializeThemeToggle;
