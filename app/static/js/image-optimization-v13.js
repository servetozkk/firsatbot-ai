/* FırsatAI v13.7.2 - Image Optimization */
(function () {
  "use strict";
  const PLACEHOLDER = "/static/img/product-placeholder-v1372.svg";

  function supportsFormat(mime, dataUri) {
    try {
      const canvas = document.createElement("canvas");
      if (!canvas.getContext) return false;
      return canvas.toDataURL(mime).indexOf(dataUri) === 0;
    } catch (_) {
      return false;
    }
  }

  document.documentElement.dataset.webp = supportsFormat("image/webp", "data:image/webp") ? "1" : "0";
  document.documentElement.dataset.avif = supportsFormat("image/avif", "data:image/avif") ? "1" : "0";

  function isHero(img, index) {
    return img.hasAttribute("data-firsatai-hero") ||
      img.classList.contains("product-main-image") ||
      img.id === "mainProductImage" ||
      (index === 0 && img.closest("main"));
  }

  function optimize(img, index) {
    if (img.dataset.firsataiOptimized === "1") return;
    const hero = isHero(img, index);

    if (!img.getAttribute("loading")) img.setAttribute("loading", hero ? "eager" : "lazy");
    if (!img.getAttribute("decoding")) img.setAttribute("decoding", "async");
    if (!img.getAttribute("fetchpriority")) img.setAttribute("fetchpriority", hero ? "high" : "auto");

    if (!img.getAttribute("width") && !img.style.width) img.setAttribute("width", img.dataset.width || "320");
    if (!img.getAttribute("height") && !img.style.height) img.setAttribute("height", img.dataset.height || "240");

    if (/^https?:\/\//i.test(img.currentSrc || img.src || "")) {
      if (!img.getAttribute("referrerpolicy")) img.setAttribute("referrerpolicy", "no-referrer");
    }

    const deferred = img.getAttribute("data-src");
    if (deferred && !img.getAttribute("src")) img.setAttribute("src", deferred);
    const deferredSrcset = img.getAttribute("data-srcset");
    if (deferredSrcset && !img.getAttribute("srcset")) img.setAttribute("srcset", deferredSrcset);
    if (img.getAttribute("srcset") && !img.getAttribute("sizes")) {
      img.setAttribute("sizes", "(max-width: 576px) 92vw, (max-width: 992px) 46vw, 320px");
    }

    img.addEventListener("error", function onImageError() {
      img.removeEventListener("error", onImageError);
      img.removeAttribute("srcset");
      img.src = PLACEHOLDER;
      img.classList.add("firsatai-image-placeholder");
    }, { once: true });

    img.dataset.firsataiOptimized = "1";
  }

  function scan(root) {
    const images = Array.from((root || document).querySelectorAll("img"));
    images.forEach(optimize);
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", () => scan(document), { once: true });
  } else {
    scan(document);
  }

  if ("MutationObserver" in window) {
    const observer = new MutationObserver((mutations) => {
      mutations.forEach((mutation) => mutation.addedNodes.forEach((node) => {
        if (!(node instanceof Element)) return;
        if (node.tagName === "IMG") optimize(node, 99);
        else scan(node);
      }));
    });
    observer.observe(document.documentElement, { childList: true, subtree: true });
  }
})();
