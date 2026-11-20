(function () {
    'use strict';

    const root = document.documentElement;
    const reduceMotion = window.matchMedia('(prefers-reduced-motion: reduce)');
    const finePointer = window.matchMedia('(hover: hover) and (pointer: fine)');

    const store = {
        get(key) { try { return localStorage.getItem(key); } catch (e) { return null; } },
        set(key, value) { try { localStorage.setItem(key, value); } catch (e) {  } },
    };


    function initDialogs() {
        document.addEventListener('click', function (e) {
            const opener = e.target.closest('.js-open-auth, [data-open-dialog]');
            if (opener) {
                const id = opener.dataset.openDialog || 'modal-' + opener.dataset.modal;
                const dialog = document.getElementById(id);
                if (!dialog || typeof dialog.showModal !== 'function') return;
                e.preventDefault();
                document.querySelectorAll('dialog[open]').forEach(function (d) { d.close(); });
                dialog.showModal();
                return;
            }

            const dialog = e.target;
            if (dialog instanceof HTMLDialogElement && dialog.open) {
                const r = dialog.getBoundingClientRect();
                const inside = e.clientX >= r.left && e.clientX <= r.right &&
                               e.clientY >= r.top && e.clientY <= r.bottom;
                if (!inside) dialog.close();
            }
        });
    }


    function initPasswordReveal() {
        document.addEventListener('click', function (e) {
            const btn = e.target.closest('.js-reveal');
            if (!btn) return;
            const input = document.getElementById(btn.getAttribute('aria-controls'));
            if (!input) return;
            const show = input.type === 'password';
            input.type = show ? 'text' : 'password';
            btn.setAttribute('aria-pressed', String(show));
            btn.textContent = show ? 'скрыть' : 'показать';
        });
    }


    function initMarquees() {
        const marquees = document.querySelectorAll('[data-marquee]');
        if (!marquees.length) return;

        function fill(m) {
            const track = m.querySelector('.marquee-track');
            const first = track && track.querySelector('.marquee-group');
            if (!first || !first.offsetWidth) return;

            let groups = track.querySelectorAll('.marquee-group').length;
            const need = Math.max(2, Math.ceil((m.offsetWidth * 2) / first.offsetWidth));
            while (groups < need && groups < 12) {
                const clone = first.cloneNode(true);
                clone.setAttribute('aria-hidden', 'true');
                track.appendChild(clone);
                groups++;
            }
            track.style.setProperty('--groups', groups);

            const speed = Number(m.dataset.speed) || 55;
            track.style.setProperty('--marquee-dur', (first.offsetWidth / speed).toFixed(2) + 's');
        }

        marquees.forEach(fill);
        let timer = 0;
        window.addEventListener('resize', function () {
            clearTimeout(timer);
            timer = setTimeout(function () { marquees.forEach(fill); }, 200);
        });

        if (document.fonts && document.fonts.ready) {
            document.fonts.ready.then(function () { marquees.forEach(fill); });
        }
    }


    function initMotionToggle() {
        const buttons = document.querySelectorAll('.js-motion-toggle');
        function apply(paused) {
            if (paused) root.dataset.motion = 'paused';
            else delete root.dataset.motion;
            buttons.forEach(function (b) { b.setAttribute('aria-pressed', String(paused)); });
        }
        apply(store.get('qx-motion') === 'paused');
        buttons.forEach(function (b) {
            b.addEventListener('click', function () {
                const paused = root.dataset.motion !== 'paused';
                apply(paused);
                store.set('qx-motion', paused ? 'paused' : 'running');
            });
        });
    }


    function initReveal() {
        const elements = document.querySelectorAll('[data-reveal]');
        if (!elements.length) return;
        if (reduceMotion.matches || !('IntersectionObserver' in window)) {
            elements.forEach(function (el) { el.classList.add('is-visible'); });
            return;
        }
        const observer = new IntersectionObserver(function (entries) {
            let i = 0;
            entries.forEach(function (entry) {
                if (!entry.isIntersecting) return;

                entry.target.style.setProperty('--reveal-delay', (i++ * 70) + 'ms');
                entry.target.classList.add('is-visible');
                observer.unobserve(entry.target);
            });
        }, { threshold: 0.12, rootMargin: '0px 0px -40px 0px' });
        elements.forEach(function (el) { observer.observe(el); });
    }


    function initToTop() {
        const button = document.querySelector('.to-top');
        let ticking = false;
        function update() {
            if (button) button.classList.toggle('is-visible', window.scrollY > 900);
            ticking = false;
        }
        window.addEventListener('scroll', function () {
            if (!ticking) { ticking = true; requestAnimationFrame(update); }
        }, { passive: true });
        update();

        document.addEventListener('click', function (e) {
            if (!e.target.closest('.js-to-top')) return;
            window.scrollTo({ top: 0, behavior: reduceMotion.matches ? 'auto' : 'smooth' });
            const main = document.getElementById('main');
            if (main) main.focus({ preventScroll: true });
        });
    }


    function initSizePicker() {
        const form = document.querySelector('[data-size-form]');
        if (!form) return;
        function set(selector, fn) { document.querySelectorAll(selector).forEach(fn); }
        form.addEventListener('change', function (e) {
            const input = e.target;
            if (input.name !== 'variant') return;
            const d = input.dataset;
            set('[data-price-now], [data-price-btn], [data-price-bar]', function (el) { el.textContent = d.price; });
            set('[data-price-old]', function (el) { el.hidden = !d.old; });
            set('[data-price-old-value]', function (el) { el.textContent = d.old; });
            set('[data-price-off]', function (el) { el.hidden = !d.off; });
            set('[data-price-off-value]', function (el) { el.textContent = d.off; });
            set('[data-stock-value]', function (el) { el.textContent = d.stock; });
            set('[data-sku-value]', function (el) { el.textContent = d.sku; });
        });
    }


    function initSlider() {
        const root = document.querySelector('[data-slider]');
        if (!root) return;
        const track = root.querySelector('[data-slider-track]');
        const slides = Array.from(track.children);
        const out = root.querySelector('[data-slider-current]');
        if (slides.length < 2) return;
        let index = 0;

        function go(i) {
            index = (i + slides.length) % slides.length;
            track.style.transform = 'translateX(' + (-index * 100) + '%)';
            slides.forEach(function (slide, k) {
                const hidden = k !== index;
                slide.inert = hidden;
                slide.setAttribute('aria-hidden', String(hidden));
            });
            if (out) out.textContent = String(index + 1).padStart(2, '0');
        }

        root.querySelector('[data-slider-prev]').addEventListener('click', function () { go(index - 1); });
        root.querySelector('[data-slider-next]').addEventListener('click', function () { go(index + 1); });

        root.addEventListener('keydown', function (e) {
            if (e.target.closest('model-viewer')) return;
            if (e.key === 'ArrowLeft') { e.preventDefault(); go(index - 1); }
            if (e.key === 'ArrowRight') { e.preventDefault(); go(index + 1); }
        });

        let startX = null;
        let startY = 0;
        track.addEventListener('pointerdown', function (e) {
            startX = e.target.closest('model-viewer, button') ? null : e.clientX;
            startY = e.clientY;
        });
        track.addEventListener('pointerup', function (e) {
            if (startX === null) return;
            const dx = e.clientX - startX;
            const dy = e.clientY - startY;
            startX = null;
            if (Math.abs(dx) > 40 && Math.abs(dx) > Math.abs(dy) * 1.2) go(index + (dx < 0 ? 1 : -1));
        });
        track.addEventListener('pointercancel', function () { startX = null; });

        function preload() {
            root.querySelectorAll('img[loading="lazy"]').forEach(function (img) { img.loading = 'eager'; });
        }
        if (document.readyState === 'complete') preload();
        else window.addEventListener('load', preload);

        go(0);
    }


    function initModelViewers() {
        document.querySelectorAll('[data-mv]').forEach(function (mv) {
            if (reduceMotion.matches) mv.removeAttribute('auto-rotate');
            const bar = mv.querySelector('.mv-progress');
            if (!bar) return;
            mv.addEventListener('progress', function (e) {
                const p = e.detail.totalProgress;
                bar.style.setProperty('--p', p);
                bar.classList.toggle('is-done', p >= 1);
            });
        });
    }


    function initBuybar() {
        const bar = document.querySelector('[data-buybar]');
        const main = document.querySelector('[data-buy-main]');
        if (!bar || !main || !('IntersectionObserver' in window)) return;

        new IntersectionObserver(function (entries) {
            bar.classList.toggle('is-visible', !entries[0].isIntersecting);
        }).observe(main);
    }


    function initAvatarPreview() {
        const input = document.querySelector('[data-avatar-input]');
        const preview = document.querySelector('[data-avatar-preview]');
        const name = document.querySelector('[data-avatar-name]');
        if (!input || !preview) return;
        input.addEventListener('change', function () {
            const file = input.files && input.files[0];
            if (!file) return;
            if (name) name.textContent = file.name;
            const img = document.createElement('img');
            img.alt = 'новый аватар';
            img.src = URL.createObjectURL(file);
            img.onload = function () { URL.revokeObjectURL(img.src); };
            preview.replaceChildren(img);
        });
    }


    function initToasts() {
        const region = document.querySelector('.toasts');
        if (!region) return;
        const toasts = Array.from(region.querySelectorAll('[data-toast]'));

        function dismiss(toast) {
            if (!toast || !toast.isConnected || toast.classList.contains('is-leaving')) return;
            toast.classList.add('is-leaving');
            setTimeout(function () { toast.remove(); }, reduceMotion.matches ? 0 : 220);
        }

        toasts.forEach(function (t) { t.remove(); });
        toasts.forEach(function (toast, i) {
            setTimeout(function () {
                region.appendChild(toast);
                let timer = setTimeout(function () { dismiss(toast); }, 4500);
                toast.addEventListener('mouseenter', function () { clearTimeout(timer); });
                toast.addEventListener('focusin', function () { clearTimeout(timer); });
                toast.addEventListener('mouseleave', function () {
                    timer = setTimeout(function () { dismiss(toast); }, 2000);
                });
            }, 150 + i * 120);
        });

        region.addEventListener('click', function (e) {
            const close = e.target.closest('[data-toast-close]');
            if (close) dismiss(close.closest('[data-toast]'));
        });
    }


    function initClock() {
        const clocks = document.querySelectorAll('[data-clock]');
        if (!clocks.length) return;
        let format;
        try {
            format = new Intl.DateTimeFormat('ru-RU', {
                timeZone: 'Europe/Moscow', hour: '2-digit', minute: '2-digit', second: '2-digit', hour12: false,
            });
        } catch (e) { return; }
        function tick() {
            const text = format.format(new Date());
            clocks.forEach(function (c) { c.textContent = text; });
        }
        tick();
        setInterval(tick, 1000);
    }


    function initCursorTag() {
        const tag = document.querySelector('.cursor-tag');
        if (!tag || !finePointer.matches || reduceMotion.matches) return;
        const label = tag.querySelector('span');
        let x = -200, y = -200, tx = -200, ty = -200, raf = 0, active = null;

        function loop() {
            x += (tx - x) * 0.22;
            y += (ty - y) * 0.22;
            tag.style.transform = 'translate3d(' + x + 'px,' + y + 'px,0)';
            raf = Math.abs(tx - x) + Math.abs(ty - y) > 0.3 ? requestAnimationFrame(loop) : 0;
        }

        document.addEventListener('pointermove', function (e) {
            tx = e.clientX;
            ty = e.clientY;
            const target = e.target.closest('[data-cursor]');
            if (target !== active) {
                active = target;
                if (target) label.textContent = target.dataset.cursor;
                tag.classList.toggle('is-on', Boolean(target));
            }
            if (!raf) raf = requestAnimationFrame(loop);
        }, { passive: true });

        root.addEventListener('mouseleave', function () {
            active = null;
            tag.classList.remove('is-on');
        });
    }


    initDialogs();
    initPasswordReveal();
    initMarquees();
    initMotionToggle();
    initReveal();
    initToTop();
    initSizePicker();
    initSlider();
    initModelViewers();
    initBuybar();
    initAvatarPreview();
    initToasts();
    initClock();
    initCursorTag();
})();
