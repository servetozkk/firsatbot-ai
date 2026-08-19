(() => {
  "use strict";
  const endpoint = "/api/analytics/v13/events";
  const send = (payload) => {
    try {
      const body = JSON.stringify(payload);
      if (navigator.sendBeacon) {
        navigator.sendBeacon(endpoint, new Blob([body], {type: "application/json"}));
      } else {
        fetch(endpoint, {method: "POST", headers: {"Content-Type": "application/json"}, body, keepalive: true}).catch(() => {});
      }
    } catch (_) {}
  };
  const path = location.pathname;
  send({event_type: "page_view", page_path: path});
  if (path.startsWith("/urun/")) {
    send({event_type: "product_view", page_path: path, product_key: path.split("/").filter(Boolean).pop()});
  }
  document.addEventListener("click", (event) => {
    const link = event.target.closest("a[href]");
    if (!link) return;
    const store = link.dataset.store || link.dataset.storeCode;
    if (store || link.classList.contains("store-link") || link.rel === "nofollow sponsored") {
      send({event_type: "store_click", page_path: path, store_code: store || "unknown"});
    }
  }, {capture: true});
})();
