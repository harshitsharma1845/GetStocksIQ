document.addEventListener("DOMContentLoaded", () => {

    const progressBars = document.querySelectorAll("[data-width]");
    const shouldReduceMotion = window.matchMedia(
        "(prefers-reduced-motion: reduce)"
    ).matches;

    const setProgressWidths = () => {
        progressBars.forEach((element) => {
            const width = Number(element.dataset.width);
            element.style.width = `${Math.max(0, Math.min(100, width || 0))}%`;
        });
    };

    if (shouldReduceMotion) {
        setProgressWidths();
    } else {
        requestAnimationFrame(() => requestAnimationFrame(setProgressWidths));
    }

});
