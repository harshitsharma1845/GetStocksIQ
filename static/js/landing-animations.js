/**
 * GetStockIQ — Landing Page Interactive & Entrance Animations
 * Handles:
 * 1. Number counting up from 0 on reveal
 * 2. SVG line chart automatic drawing
 * 3. IntersectionObserver scroll reveals
 * 4. Respects prefers-reduced-motion
 */

(function () {
    'use strict';

    const prefersReducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

    // Number counting animation
    function animateCounters() {
        const counters = document.querySelectorAll('.stat-count');
        if (!counters.length) return;

        const formatINR = (val) => {
            return new Intl.NumberFormat('en-IN', { maximumFractionDigits: 0 }).format(Math.round(val));
        };

        const counterObserver = new IntersectionObserver((entries, observer) => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    const el = entry.target;
                    const target = parseFloat(el.getAttribute('data-target') || '0');
                    const prefix = el.getAttribute('data-prefix') || '';
                    const suffix = el.getAttribute('data-suffix') || '';
                    const decimals = parseInt(el.getAttribute('data-decimals') || '0', 10);
                    const isCurrency = el.getAttribute('data-format') === 'inr';
                    const duration = prefersReducedMotion ? 0 : 1800; // ms

                    if (prefersReducedMotion || duration === 0) {
                        const formatted = isCurrency
                            ? formatINR(target)
                            : target.toFixed(decimals);
                        el.textContent = `${prefix}${formatted}${suffix}`;
                        observer.unobserve(el);
                        return;
                    }

                    let startTime = null;

                    function step(timestamp) {
                        if (!startTime) startTime = timestamp;
                        const progress = Math.min((timestamp - startTime) / duration, 1);
                        const easeProgress = 1 - Math.pow(1 - progress, 3);
                        const currentVal = easeProgress * target;

                        const formatted = isCurrency
                            ? formatINR(currentVal)
                            : currentVal.toFixed(decimals);

                        el.textContent = `${prefix}${formatted}${suffix}`;

                        if (progress < 1) {
                            window.requestAnimationFrame(step);
                        } else {
                            const finalFormatted = isCurrency
                                ? formatINR(target)
                                : target.toFixed(decimals);
                            el.textContent = `${prefix}${finalFormatted}${suffix}`;
                        }
                    }

                    window.requestAnimationFrame(step);
                    observer.unobserve(el);
                }
            });
        }, { threshold: 0.25 });

        counters.forEach(c => counterObserver.observe(c));
    }

    // Scroll reveal observer
    function initScrollReveals() {
        const reveals = document.querySelectorAll('.reveal-on-scroll');
        if (!reveals.length) return;

        if (prefersReducedMotion) {
            reveals.forEach(el => el.classList.add('is-revealed'));
            return;
        }

        const revealObserver = new IntersectionObserver((entries) => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    entry.target.classList.add('is-revealed');
                }
            });
        }, {
            threshold: 0.12,
            rootMargin: '0px 0px -40px 0px'
        });

        reveals.forEach(el => revealObserver.observe(el));
    }

    // SVG Chart path drawing trigger
    function initSvgDraw() {
        const chartSvgs = document.querySelectorAll('.mini-line-chart svg, .preview-card svg');
        if (!chartSvgs.length || prefersReducedMotion) return;

        const svgObserver = new IntersectionObserver((entries, observer) => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    entry.target.classList.add('draw-active');
                    observer.unobserve(entry.target);
                }
            });
        }, { threshold: 0.3 });

        chartSvgs.forEach(svg => svgObserver.observe(svg));
    }

    // Morphing Floating Pill Navbar on Scroll
    function initMorphingNavbar() {
        const nav = document.getElementById('landingNav') || document.querySelector('.landing-nav');
        const wrapper = document.getElementById('landingNavWrapper') || document.querySelector('.landing-nav-wrapper');
        if (!nav) return;

        let ticking = false;

        function updateNavState() {
            const scrollY = window.pageYOffset || document.documentElement.scrollTop;
            if (scrollY > 28) {
                nav.classList.add('is-scrolled');
                if (wrapper) wrapper.classList.add('is-scrolled');
            } else {
                nav.classList.remove('is-scrolled');
                if (wrapper) wrapper.classList.remove('is-scrolled');
            }
            ticking = false;
        }

        window.addEventListener('scroll', () => {
            if (!ticking) {
                window.requestAnimationFrame(updateNavState);
                ticking = true;
            }
        }, { passive: true });

        updateNavState();
    }

    // Bar Growth Animation on Scroll
    function initBarGrowthAnimations() {
        const barContainers = document.querySelectorAll('.bars');
        if (!barContainers.length) return;

        if (prefersReducedMotion) {
            barContainers.forEach(b => b.classList.add('bars-animated'));
            return;
        }

        const barObserver = new IntersectionObserver((entries, observer) => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    entry.target.classList.add('bars-animated');
                    observer.unobserve(entry.target);
                }
            });
        }, { threshold: 0.25 });

        barContainers.forEach(b => barObserver.observe(b));
    }

    // Interactive 3D Card Tilt for feature cards and preview cards
    function initCard3DTilt() {
        if (prefersReducedMotion || window.innerWidth < 992) return;

        const tiltCards = document.querySelectorAll('.feature-grid article, .assistant-map article, .preview-card, .floating-watchlist');
        tiltCards.forEach(card => {
            card.addEventListener('mousemove', (e) => {
                const rect = card.getBoundingClientRect();
                const x = e.clientX - rect.left;
                const y = e.clientY - rect.top;
                const centerX = rect.width / 2;
                const centerY = rect.height / 2;
                const rotateX = ((y - centerY) / centerY) * -5;
                const rotateY = ((x - centerX) / centerX) * 5;

                card.style.transform = `perspective(1000px) rotateX(${rotateX.toFixed(2)}deg) rotateY(${rotateY.toFixed(2)}deg) translateY(-4px)`;
            });

            card.addEventListener('mouseleave', () => {
                card.style.transform = '';
            });
        });
    }

    // Initialize on DOM Ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', () => {
            initMorphingNavbar();
            animateCounters();
            initScrollReveals();
            initSvgDraw();
            initBarGrowthAnimations();
            initCard3DTilt();
        });
    } else {
        initMorphingNavbar();
        animateCounters();
        initScrollReveals();
        initSvgDraw();
        initBarGrowthAnimations();
        initCard3DTilt();
    }
})();
