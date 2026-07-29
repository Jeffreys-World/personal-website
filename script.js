/**
 * Jeffrey De La Cruz — Portfolio
 *
 * Five small behaviours, all progressive enhancements. With JS disabled the
 * page is fully readable: content renders at rest, links work, nothing hides.
 *
 *   1. Theme toggle          persisted, follows the OS until the user chooses
 *   2. Scroll progress       document position as a hairline at the top
 *   3. Masthead reveal       appears once the hero has cleared
 *   4. Active section        IntersectionObserver, no scroll handler
 *   5. Reveal on scroll      fires once per element, staggered, never replays
 */

(function () {
  'use strict';

  var root = document.documentElement;
  var reduceMotion = window.matchMedia('(prefers-reduced-motion: reduce)');

  /* ======================================================================
     1. Theme toggle
     ====================================================================== */

  (function theme() {
    var toggle = document.getElementById('theme-toggle');
    var label = document.getElementById('theme-toggle-label');
    if (!toggle) return;

    var systemQuery = window.matchMedia('(prefers-color-scheme: dark)');

    function syncLabel() {
      var next = root.dataset.theme === 'dark' ? 'light' : 'dark';
      var text = 'Switch to ' + next + ' mode';
      if (label) label.textContent = text;
      toggle.setAttribute('aria-label', text);
      toggle.setAttribute('title', text);
    }

    function apply(mode, persist) {
      root.dataset.theme = mode;
      if (persist) {
        try {
          localStorage.setItem('theme', mode);
        } catch (e) {
          /* Private mode or storage disabled: the toggle still works per-session. */
        }
      }
      syncLabel();
    }

    toggle.addEventListener('click', function () {
      apply(root.dataset.theme === 'dark' ? 'light' : 'dark', true);
    });

    // Follow the OS only while the user has not made an explicit choice.
    var onSystemChange = function (e) {
      var stored = null;
      try {
        stored = localStorage.getItem('theme');
      } catch (err) {
        /* ignore */
      }
      if (!stored) apply(e.matches ? 'dark' : 'light', false);
    };

    if (systemQuery.addEventListener) {
      systemQuery.addEventListener('change', onSystemChange);
    } else if (systemQuery.addListener) {
      systemQuery.addListener(onSystemChange);
    }

    syncLabel();
  })();

  /* ======================================================================
     2 + 3. Scroll progress and masthead reveal
     Both derive from scroll position, so they share one rAF-throttled pass.
     ====================================================================== */

  (function scrollDriven() {
    var bar = document.getElementById('progress-bar');
    var masthead = document.getElementById('masthead');
    var hero = document.querySelector('.hero');
    if (!bar && !masthead) return;

    var ticking = false;

    function update() {
      ticking = false;

      if (bar) {
        var scrollable = document.documentElement.scrollHeight - window.innerHeight;
        var ratio = scrollable > 0 ? window.scrollY / scrollable : 0;
        bar.style.width = Math.min(Math.max(ratio, 0), 1) * 100 + '%';
      }

      if (masthead) {
        // Reveal once the hero is mostly out of view, so the header never
        // competes with the opening statement.
        var threshold = hero ? hero.offsetHeight * 0.65 : 400;
        masthead.classList.toggle('is-pinned', window.scrollY > threshold);
      }
    }

    function onScroll() {
      if (!ticking) {
        ticking = true;
        window.requestAnimationFrame(update);
      }
    }

    window.addEventListener('scroll', onScroll, { passive: true });
    window.addEventListener('resize', onScroll, { passive: true });
    update();
  })();

  /* ======================================================================
     4. Active section tracking
     ====================================================================== */

  (function scrollSpy() {
    var links = Array.prototype.slice.call(document.querySelectorAll('.nav-link'));
    if (!links.length || !('IntersectionObserver' in window)) return;

    var sections = links
      .map(function (link) {
        return document.getElementById(link.dataset.nav);
      })
      .filter(Boolean);

    if (!sections.length) return;

    var visible = Object.create(null);

    function setActive(id) {
      links.forEach(function (link) {
        var active = link.dataset.nav === id;
        link.classList.toggle('is-active', active);
        if (active) {
          link.setAttribute('aria-current', 'true');
        } else {
          link.removeAttribute('aria-current');
        }
      });
    }

    var observer = new IntersectionObserver(
      function (entries) {
        entries.forEach(function (entry) {
          visible[entry.target.id] = entry.isIntersecting;
        });

        // Topmost section currently crossing the detection band wins.
        for (var i = 0; i < sections.length; i++) {
          if (visible[sections[i].id]) {
            setActive(sections[i].id);
            return;
          }
        }
        setActive(null);
      },
      {
        // A band roughly a third down the viewport marks the "current" section.
        rootMargin: '-30% 0px -60% 0px',
        threshold: 0
      }
    );

    sections.forEach(function (section) {
      observer.observe(section);
    });
  })();

  /* ======================================================================
     5. Reveal on scroll
     ====================================================================== */

  (function reveal() {
    var items = Array.prototype.slice.call(document.querySelectorAll('.reveal'));
    if (!items.length) return;

    // No observer support, or the user asked for less motion: show everything.
    if (!('IntersectionObserver' in window) || reduceMotion.matches) {
      items.forEach(function (el) {
        el.classList.add('is-visible');
      });
      return;
    }

    var observer = new IntersectionObserver(
      function (entries, obs) {
        entries.forEach(function (entry) {
          if (!entry.isIntersecting) return;

          // Stagger siblings that enter together, capped so a long run
          // never leaves the last item waiting.
          var siblings = entry.target.parentElement
            ? Array.prototype.slice.call(entry.target.parentElement.children)
            : [];
          var index = Math.min(siblings.indexOf(entry.target), 4);
          entry.target.style.setProperty('--reveal-delay', Math.max(index, 0) * 70 + 'ms');

          entry.target.classList.add('is-visible');
          obs.unobserve(entry.target); // fires once, never replays
        });
      },
      { rootMargin: '0px 0px -12% 0px', threshold: 0.08 }
    );

    items.forEach(function (el) {
      observer.observe(el);
    });
  })();
})();
