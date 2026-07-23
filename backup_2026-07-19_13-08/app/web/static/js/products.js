(() => {
    "use strict";

    const API_URL = "/api/products";

    let productSearchInput;
    let clearSearchButton;
    let totalProductStat;
    let activeProductStat;
    let passiveProductStat;
    let activePercentageStat;
    let themeToggleButton;
    let addProductForm;
    let productNameInput;
    let productUrlInput;
    let productActiveInput;
    let addProductButton;
    let refreshProductsButton;
    let productList;
    let productCount;
    let loadingArea;
    let emptyArea;
    let alertArea;

    function getElements() {
        productSearchInput =
            document.getElementById("productSearchInput");

        clearSearchButton =
            document.getElementById("clearSearchButton");

        totalProductStat =
            document.getElementById("totalProductStat");

        activeProductStat =
            document.getElementById("activeProductStat");

        passiveProductStat =
            document.getElementById("passiveProductStat");

        activePercentageStat =
            document.getElementById("activePercentageStat");

        themeToggleButton =
            document.getElementById("themeToggleButton");

        addProductForm =
            document.getElementById("addProductForm");

        productNameInput =
            document.getElementById("productName");

        productUrlInput =
            document.getElementById("productUrl");

        productActiveInput =
            document.getElementById("productActive");

        addProductButton =
            document.getElementById("addProductButton");

        refreshProductsButton =
            document.getElementById("refreshProductsButton");

        productList =
            document.getElementById("productList");

        productCount =
            document.getElementById("productCount");

        loadingArea =
            document.getElementById("loadingArea");

        emptyArea =
            document.getElementById("emptyArea");

        alertArea =
            document.getElementById("alertArea");
    }

    function escapeHtml(value) {
        const element = document.createElement("div");
        element.textContent = value ?? "";
        return element.innerHTML;
    }

    function applyTheme(theme) {
        const darkMode = theme === "dark";

        document.body.classList.toggle(
            "dark-mode",
            darkMode
        );

        if (themeToggleButton) {
            themeToggleButton.textContent = darkMode
                ? "☀️ Aydınlık Mod"
                : "🌙 Karanlık Mod";
        }
    }

    function loadTheme() {
        const savedTheme = localStorage.getItem(
            "firsat-ai-theme"
        );

        if (savedTheme) {
            applyTheme(savedTheme);
            return;
        }

        const prefersDark = window.matchMedia(
            "(prefers-color-scheme: dark)"
        ).matches;

        applyTheme(
            prefersDark ? "dark" : "light"
        );
    }

    function toggleTheme() {
        const darkMode =
            document.body.classList.contains(
                "dark-mode"
            );

        const newTheme = darkMode
            ? "light"
            : "dark";

        localStorage.setItem(
            "firsat-ai-theme",
            newTheme
        );

        applyTheme(newTheme);
    }

    function showAlert(message, type = "success") {
        if (!alertArea) {
            console.log(message);
            return;
        }

        alertArea.innerHTML = `
            <div
                class="alert alert-${type} alert-dismissible fade show"
                role="alert"
            >
                ${escapeHtml(message)}

                <button
                    type="button"
                    class="btn-close"
                    data-bs-dismiss="alert"
                    aria-label="Kapat"
                ></button>
            </div>
        `;

        window.scrollTo({
            top: 0,
            behavior: "smooth"
        });

        window.setTimeout(() => {
            if (alertArea) {
                alertArea.innerHTML = "";
            }
        }, 6000);
    }

    async function getErrorMessage(response) {
        try {
            const data = await response.json();

            if (typeof data.detail === "string") {
                return data.detail;
            }

            return (
                data.message ||
                `İşlem gerçekleştirilemedi (${response.status}).`
            );

        } catch {
            return `Sunucudan geçersiz cevap alındı (${response.status}).`;
        }
    }

    function setLoading(isLoading) {
        if (loadingArea) {
            loadingArea.classList.toggle(
                "d-none",
                !isLoading
            );

            loadingArea.style.display =
                isLoading ? "" : "none";
        }

        if (productList) {
            productList.style.display =
                isLoading ? "none" : "";
        }

        if (refreshProductsButton) {
            refreshProductsButton.disabled =
                isLoading;
        }
    }

    function createProductElement(product) {
        const item =
            document.createElement("article");

        item.className = "product-item";

        const isActive =
            Boolean(product.active);

        const price =
            product.price != null
                ? `${Number(product.price).toLocaleString("tr-TR")} TL`
                : "-";

        const oldPrice =
            product.old_price != null
                ? `${Number(product.old_price).toLocaleString("tr-TR")} TL`
                : "-";

        const discountPercentage =
            product.discount_percentage != null
                ? `%${product.discount_percentage}`
                : "-";

        const aiScore =
            product.ai_score != null
                ? `${product.ai_score}/100`
                : "-";

        item.innerHTML = `
            <div class="product-info">
                <div class="product-name">
                    ${escapeHtml(product.name)}
                </div>

                <a
                    class="product-url"
                    href="${escapeHtml(product.url)}"
                    target="_blank"
                    rel="noopener noreferrer"
                >
                    ${escapeHtml(product.url)}
                </a>

                ${
                    product.has_details
                        ? `
                    <div class="product-details mt-3">
                        ${
                            product.image
                                ? `
                            <img
                                class="product-image"
                                src="${escapeHtml(product.image)}"
                                alt="${escapeHtml(product.name)}"
                                loading="lazy"
                            >
                            `
                                : ""
                        }

                        <div>
                            💰 <strong>Fiyat:</strong>
                            ${price}
                        </div>

                        <div>
                            🏷️ <strong>Eski:</strong>
                            ${oldPrice}
                        </div>

                        <div>
                            📉 <strong>İndirim:</strong>
                            ${discountPercentage}
                        </div>

                        <div>
                            🤖 <strong>AI Skoru:</strong>
                            ${aiScore}
                        </div>

                        <div>
                            ⭐ <strong>Puan:</strong>
                            ${product.rating ?? "-"}
                            (${product.review_count ?? 0} yorum)
                        </div>

                        <div>
                            🏪 <strong>Satıcı:</strong>
                            ${escapeHtml(product.seller ?? "-")}
                        </div>
                    </div>
                    `
                        : `
                    <div class="text-muted mt-3">
                        Henüz tarama yapılmadı.
                    </div>
                    `
                }
            </div>

            <div class="product-actions">
                <span
                    class="status-badge ${
                        isActive
                            ? "status-active"
                            : "status-passive"
                    }"
                >
                    ${isActive ? "Aktif" : "Pasif"}
                </span>

                <button
                    class="btn btn-sm btn-outline-primary"
                    type="button"
                    data-action="scan"
                >
                    Şimdi Tara
                </button>

                <button
                    class="btn btn-sm ${
                        isActive
                            ? "btn-outline-warning"
                            : "btn-outline-success"
                    }"
                    type="button"
                    data-action="toggle"
                >
                    ${isActive ? "Durdur" : "Aktifleştir"}
                </button>

                <button
                    class="btn btn-sm btn-outline-danger"
                    type="button"
                    data-action="delete"
                >
                    Sil
                </button>
            </div>
        `;

        const scanButton =
            item.querySelector('[data-action="scan"]');

        const toggleButton =
            item.querySelector('[data-action="toggle"]');

        const deleteButton =
            item.querySelector('[data-action="delete"]');

        scanButton?.addEventListener(
            "click",
            () => {
                scanProduct(
                    product.url,
                    scanButton
                );
            }
        );

        toggleButton?.addEventListener(
            "click",
            () => {
                updateProductStatus(
                    product.url,
                    !isActive,
                    toggleButton
                );
            }
        );

        deleteButton?.addEventListener(
            "click",
            () => {
                removeProduct(
                    product.name,
                    product.url,
                    deleteButton
                );
            }
        );

        return item;
    }
    function filterProducts() {
        if (
            !productSearchInput ||
            !productList
        ) {
            return;
        }

        const searchText =
            productSearchInput.value
                .trim()
                .toLocaleLowerCase("tr-TR");

        const productItems =
            productList.querySelectorAll(
                ".product-item"
            );

        let visibleCount = 0;

        productItems.forEach(
            (productItem) => {
                const productText =
                    productItem.textContent
                        .toLocaleLowerCase(
                            "tr-TR"
                        );

                const isVisible =
                    productText.includes(
                        searchText
                    );

                productItem.style.display =
                    isVisible ? "" : "none";

                if (isVisible) {
                    visibleCount += 1;
                }
            }
        );

        if (productCount) {
            productCount.textContent =
                searchText
                    ? `${visibleCount} ürün bulundu`
                    : `${productItems.length} ürün takip listesinde`;
        }
    }

    async function loadProductStats() {
        try {
            const response = await fetch(
                `${API_URL}/stats`,
                {
                    cache: "no-store"
                }
            );

            if (!response.ok) {
                throw new Error(
                    await getErrorMessage(response)
                );
            }

            const data =
                await response.json();

            if (totalProductStat) {
                totalProductStat.textContent =
                    data.total_count ?? 0;
            }

            if (activeProductStat) {
                activeProductStat.textContent =
                    data.active_count ?? 0;
            }

            if (passiveProductStat) {
                passiveProductStat.textContent =
                    data.passive_count ?? 0;
            }

            if (activePercentageStat) {
                activePercentageStat.textContent =
                    `%${data.active_percentage ?? 0}`;
            }

        } catch (error) {
            console.error(
                "İstatistik yükleme hatası:",
                error
            );
        }
    }

    async function loadProducts() {
        if (!productList) {
            console.error(
                'HTML içinde id="productList" bulunamadı.'
            );

            showAlert(
                'Sayfada "productList" alanı bulunamadı.',
                "danger"
            );

            return;
        }

        setLoading(true);
        productList.innerHTML = "";

        if (emptyArea) {
            emptyArea.classList.add("d-none");
            emptyArea.style.display = "none";
        }

        const controller =
            new AbortController();

        const timeoutId =
            window.setTimeout(
                () => controller.abort(),
                10000
            );

        try {
            const response = await fetch(
                API_URL,
                {
                    method: "GET",
                    headers: {
                        Accept: "application/json"
                    },
                    cache: "no-store",
                    signal: controller.signal
                }
            );

            if (!response.ok) {
                throw new Error(
                    await getErrorMessage(response)
                );
            }

            const data =
                await response.json();

            const products =
                Array.isArray(data)
                    ? data
                    : Array.isArray(data.products)
                        ? data.products
                        : [];

            if (productCount) {
                productCount.textContent =
                    `${products.length} ürün takip listesinde`;
            }

            if (products.length === 0) {
                if (emptyArea) {
                    emptyArea.classList.remove(
                        "d-none"
                    );

                    emptyArea.style.display = "";
                }

                return;
            }

            const fragment =
                document.createDocumentFragment();

            products.forEach((product) => {
                fragment.appendChild(
                    createProductElement(product)
                );
            });

            productList.appendChild(fragment);
            filterProducts();

        } catch (error) {
            console.error(
                "Ürün yükleme hatası:",
                error
            );

            if (productCount) {
                productCount.textContent =
                    "Ürünler yüklenemedi.";
            }

            const message =
                error.name === "AbortError"
                    ? "API 10 saniye içinde cevap vermedi."
                    : `Ürün listesi yüklenemedi: ${error.message}`;

            showAlert(
                message,
                "danger"
            );

        } finally {
            window.clearTimeout(timeoutId);
            setLoading(false);
            await loadProductStats();
        }
    }

    async function addProduct(event) {
        event.preventDefault();

        const name =
            productNameInput?.value.trim();

        const url =
            productUrlInput?.value.trim();

        const active =
            Boolean(
                productActiveInput?.checked
            );

        if (!name || !url) {
            showAlert(
                "Ürün adı ve bağlantısı zorunludur.",
                "warning"
            );

            return;
        }

        if (addProductButton) {
            addProductButton.disabled = true;
            addProductButton.textContent =
                active
                    ? "Ekleniyor ve taranıyor..."
                    : "Ekleniyor...";
        }

        try {
            const response =
                await fetch(API_URL, {
                    method: "POST",
                    headers: {
                        "Content-Type":
                            "application/json"
                    },
                    body: JSON.stringify({
                        name,
                        url,
                        active
                    })
                });

            if (!response.ok) {
                throw new Error(
                    await getErrorMessage(
                        response
                    )
                );
            }

            const data =
                await response.json();

            addProductForm?.reset();

            if (productActiveInput) {
                productActiveInput.checked =
                    true;
            }

            if (data.scan_success) {
                showAlert(
                    `${data.message ?? ""} ${data.scan_message ?? ""}`.trim()
                );

            } else if (active) {
                showAlert(
                    `${data.message ?? "Ürün eklendi."} Ancak otomatik tarama başarısız: ${data.scan_message ?? "Bilinmeyen hata"}`,
                    "warning"
                );

            } else {
                showAlert(
                    data.message ||
                    "Ürün eklendi."
                );
            }

            await loadProducts();

        } catch (error) {
            showAlert(
                error.message ||
                "Ürün eklenemedi.",
                "danger"
            );

        } finally {
            if (addProductButton) {
                addProductButton.disabled =
                    false;

                addProductButton.textContent =
                    "Ürün Ekle";
            }
        }
    }

    async function scanProduct(
        url,
        button
    ) {
        const oldText =
            button?.textContent ||
            "Şimdi Tara";

        if (button) {
            button.disabled = true;
            button.textContent =
                "Taranıyor...";
        }

        try {
            const response =
                await fetch(
                    `${API_URL}/scan`,
                    {
                        method: "POST",
                        headers: {
                            "Content-Type":
                                "application/json"
                        },
                        body: JSON.stringify({
                            url
                        })
                    }
                );

            if (!response.ok) {
                throw new Error(
                    await getErrorMessage(
                        response
                    )
                );
            }

            const data =
                await response.json();

            showAlert(
                data.message ||
                "Ürün başarıyla tarandı."
            );

            await loadProducts();

        } catch (error) {
            showAlert(
                error.message ||
                "Ürün taranamadı.",
                "danger"
            );

        } finally {
            if (
                button &&
                button.isConnected
            ) {
                button.disabled = false;
                button.textContent = oldText;
            }
        }
    }
        async function updateProductStatus(
        url,
        active,
        button
    ) {
        const oldText =
            button?.textContent ||
            (active
                ? "Aktifleştir"
                : "Durdur");

        if (button) {
            button.disabled = true;
            button.textContent =
                "Güncelleniyor...";
        }

        try {
            const response =
                await fetch(
                    `${API_URL}/status`,
                    {
                        method: "PATCH",
                        headers: {
                            "Content-Type":
                                "application/json"
                        },
                        body: JSON.stringify({
                            url,
                            active
                        })
                    }
                );

            if (!response.ok) {
                throw new Error(
                    await getErrorMessage(
                        response
                    )
                );
            }

            const data =
                await response.json();

            showAlert(
                data.message ||
                (
                    active
                        ? "Ürün aktifleştirildi."
                        : "Ürün durduruldu."
                )
            );

            await loadProducts();

        } catch (error) {
            showAlert(
                error.message ||
                "Ürün durumu değiştirilemedi.",
                "danger"
            );

        } finally {
            if (
                button &&
                button.isConnected
            ) {
                button.disabled = false;
                button.textContent = oldText;
            }
        }
    }

    async function removeProduct(
        name,
        url,
        button
    ) {
        const confirmed =
            window.confirm(
                `"${name}" adlı ürünü silmek istediğine emin misin?`
            );

        if (!confirmed) {
            return;
        }

        const oldText =
            button?.textContent ||
            "Sil";

        if (button) {
            button.disabled = true;
            button.textContent =
                "Siliniyor...";
        }

        try {
            const response =
                await fetch(
                    API_URL,
                    {
                        method: "DELETE",
                        headers: {
                            "Content-Type":
                                "application/json"
                        },
                        body: JSON.stringify({
                            url
                        })
                    }
                );

            if (!response.ok) {
                throw new Error(
                    await getErrorMessage(
                        response
                    )
                );
            }

            const data =
                await response.json();

            showAlert(
                data.message ||
                "Ürün silindi."
            );

            await loadProducts();

        } catch (error) {
            showAlert(
                error.message ||
                "Ürün silinemedi.",
                "danger"
            );

        } finally {
            if (
                button &&
                button.isConnected
            ) {
                button.disabled = false;
                button.textContent = oldText;
            }
        }
    }

    function clearSearch() {
        if (!productSearchInput) {
            return;
        }

        productSearchInput.value = "";
        productSearchInput.focus();
        filterProducts();
    }

    function bindEvents() {
        themeToggleButton?.addEventListener(
            "click",
            toggleTheme
        );

        addProductForm?.addEventListener(
            "submit",
            addProduct
        );

        refreshProductsButton?.addEventListener(
            "click",
            loadProducts
        );

        productSearchInput?.addEventListener(
            "input",
            filterProducts
        );

        clearSearchButton?.addEventListener(
            "click",
            clearSearch
        );
    }

    function showMissingElementWarnings() {
        const requiredElements = [
            {
                name: "productList",
                element: productList
            },
            {
                name: "loadingArea",
                element: loadingArea
            },
            {
                name: "emptyArea",
                element: emptyArea
            },
            {
                name: "productCount",
                element: productCount
            }
        ];

        const missingElements =
            requiredElements
                .filter(
                    (item) => !item.element
                )
                .map(
                    (item) => item.name
                );

        if (
            missingElements.length > 0
        ) {
            console.warn(
                "HTML içinde bulunamayan alanlar:",
                missingElements.join(", ")
            );
        }
    }

    async function initializePage() {
        getElements();
        showMissingElementWarnings();
        loadTheme();
        bindEvents();

        try {
            await loadProducts();

        } catch (error) {
            console.error(
                "Sayfa başlatma hatası:",
                error
            );

            setLoading(false);

            showAlert(
                `Sayfa başlatılamadı: ${error.message}`,
                "danger"
            );
        }
    }

    if (
        document.readyState === "loading"
    ) {
        document.addEventListener(
            "DOMContentLoaded",
            initializePage
        );

    } else {
        initializePage();
    }
})();