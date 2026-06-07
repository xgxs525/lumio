(function () {
    if (window.__xuguangHoverNavReady) return;
    window.__xuguangHoverNavReady = true;

    function navItems() {
        return Array.from(document.querySelectorAll('.nav-item.has-dropdown'));
    }

    function clearNav(except) {
        navItems().forEach(function (item) {
            if (item !== except) item.classList.remove('open', 'is-hovering');
        });
    }

    function openNav(item) {
        clearNav(item);
        item.classList.remove('open');
        item.classList.add('is-hovering');
    }

    function closeNav(item) {
        window.setTimeout(function () {
            if (!item.matches(':hover') && !item.contains(document.activeElement)) {
                item.classList.remove('open', 'is-hovering');
            }
        }, 90);
    }

    function bindHoverNavigation() {
        navItems().forEach(function (item) {
            if (item.dataset.hoverNavReady === '1') return;
            item.dataset.hoverNavReady = '1';

            item.addEventListener('mouseenter', function () { openNav(item); });
            item.addEventListener('mouseleave', function () { closeNav(item); });
            item.addEventListener('focusin', function () { openNav(item); });
            item.addEventListener('focusout', function () { closeNav(item); });

            const trigger = item.querySelector('.tools-menu-trigger');
            if (trigger) {
                trigger.addEventListener('click', function (event) {
                    clearNav();
                    event.stopImmediatePropagation();
                }, true);
            }
        });
    }

    document.addEventListener('pointerover', function (event) {
        const item = event.target.closest && event.target.closest('.nav-item.has-dropdown');
        if (item) openNav(item);
    }, true);

    document.addEventListener('click', function (event) {
        if (!event.target.closest || !event.target.closest('.nav-item.has-dropdown')) clearNav();
    }, true);

    document.addEventListener('keydown', function (event) {
        if (event.key === 'Escape') clearNav();
    });

    bindHoverNavigation();
    window.addEventListener('pageshow', function () {
        clearNav();
        bindHoverNavigation();
    });
    document.addEventListener('DOMContentLoaded', bindHoverNavigation);
})();
