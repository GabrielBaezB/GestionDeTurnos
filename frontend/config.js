document.addEventListener("DOMContentLoaded", async () => {
    try {
        const response = await fetch('/api/v1/config/');
        if (!response.ok) {
            console.error("Failed to load config");
            return;
        }
        const config = await response.json();

        // Update Document Title (Handled by Jinja2 SSR now)
        // Only redundant logic removed.

        // Apply Theme Color
        if (config.theme_color) {
            document.documentElement.style.setProperty('--bs-primary', config.theme_color);
            // You can add more complex logic here to update gradients if needed
        }

        console.log("✅ Config loaded:", config);
        console.log("🎯 Applying Project Name:", config.project_name);

    } catch (error) {
        console.error("❌ Error loading config:", error);
        // Fallback: Check if we can find the default text and highlight error
        const brandTitles = document.querySelectorAll('.brand-title');
        brandTitles.forEach(el => el.style.color = 'red'); // Visual debug
    }

    // Register Service Worker for PWA
    if ('serviceWorker' in navigator) {
        navigator.serviceWorker.register('/sw.js')
            .then(reg => console.log('✅ SW registered, scope:', reg.scope))
            .catch(err => console.warn('SW registration failed:', err));
    }
});
