document.addEventListener("DOMContentLoaded", () => {
    const toggles = document.querySelectorAll(".settings-toggle");

    toggles.forEach((toggle) => {
        const storageKey = `getStockIQ.${toggle.dataset.setting}`;
        const savedValue = localStorage.getItem(storageKey);

        if (savedValue !== null) {
            toggle.checked = savedValue === "true";
        }

        toggle.addEventListener("change", () => {
            localStorage.setItem(storageKey, String(toggle.checked));
        });
    });
});
