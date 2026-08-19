(() => {
  const revealItems = document.querySelectorAll('.market-summary-card,.featured-category-compact,.market-product-section,.sidebar-card,.home-details');
  if ('IntersectionObserver' in window) {
    const observer = new IntersectionObserver((entries) => {
      entries.forEach((entry) => {
        if (!entry.isIntersecting) return;
        entry.target.classList.add('v80-visible');
        observer.unobserve(entry.target);
      });
    }, { threshold: .08, rootMargin: '0px 0px -30px 0px' });
    revealItems.forEach((item, index) => {
      item.classList.add('v80-reveal');
      item.style.setProperty('--v80-delay', `${Math.min(index % 5, 4) * 45}ms`);
      observer.observe(item);
    });
  }

  document.querySelectorAll('.market-product-rail').forEach((rail) => {
    rail.addEventListener('wheel', (event) => {
      if (Math.abs(event.deltaY) <= Math.abs(event.deltaX) || rail.scrollWidth <= rail.clientWidth) return;
      event.preventDefault();
      rail.scrollLeft += event.deltaY;
    }, { passive: false });
  });
})();

(() => {
  const liveRail = document.querySelector('[data-live-deals]');
  if (!liveRail || window.matchMedia('(prefers-reduced-motion: reduce)').matches) return;
  let direction = 1;
  let timer = window.setInterval(() => {
    const max = liveRail.scrollWidth - liveRail.clientWidth;
    if (max <= 0) return;
    if (liveRail.scrollLeft >= max - 4) direction = -1;
    if (liveRail.scrollLeft <= 4) direction = 1;
    liveRail.scrollBy({ left: 210 * direction, behavior: 'smooth' });
  }, 3200);
  liveRail.addEventListener('mouseenter', () => window.clearInterval(timer), { once: true });
})();
