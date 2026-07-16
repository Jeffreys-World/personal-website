/**
 * Jeffrey De La Cruz — Portfolio
 * ScrollSpy: tracks scroll position on desktop viewports and highlights
 * the matching sidebar nav item using the Intersection Observer API.
 * (Smooth scrolling itself is handled in CSS via `scroll-behavior: smooth`.)
 */

(function () {
  'use strict';

  var navLinks = Array.prototype.slice.call(document.querySelectorAll('.nav-link'));

  var sections = navLinks
    .map(function (link) {
      return document.getElementById(link.dataset.nav);
    })
    .filter(Boolean);

  var desktopQuery = window.matchMedia('(min-width: 1001px)');

  function setActive(id) {
    navLinks.forEach(function (link) {
      var isActive = link.dataset.nav === id;
      link.classList.toggle('active', isActive);
      if (isActive) {
        link.setAttribute('aria-current', 'true');
      } else {
        link.removeAttribute('aria-current');
      }
    });
  }

  if ('IntersectionObserver' in window && sections.length) {
    var observer = new IntersectionObserver(
      function (entries) {
        if (!desktopQuery.matches) {
          return;
        }
        entries.forEach(function (entry) {
          if (entry.isIntersecting) {
            setActive(entry.target.id);
          }
        });
      },
      {
        root: null,
        // A thin horizontal detection band roughly a third of the way
        // down the viewport — the section crossing it is "current".
        rootMargin: '-35% 0px -55% 0px',
        threshold: 0
      }
    );

    sections.forEach(function (section) {
      observer.observe(section);
    });
  }

  // Default to the first nav item until the observer reports otherwise.
  if (navLinks.length) {
    setActive(navLinks[0].dataset.nav);
  }
})();
