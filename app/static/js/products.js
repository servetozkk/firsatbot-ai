(() => {
    "use strict";

    const PRODUCT_API_URL = "/api/products";
    const CATEGORY_API_URL = "/api/categories";

    const REQUEST_TIMEOUT = 30000;

    let products = [];
    let categories = [];

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

    let categoryScanForm;
    let categoryUrlInput;
    let categoryLimitInput;
    let categoryScanButton;
    let categoryScanStatus;

    let categoryForm;
    let savedCategoryNameInput;
    let savedCategoryUrlInput;
    let savedCategoryLimitInput;
    let addCategoryButton;
    let scanAllCategoriesButton;
    let categoryManagementStatus;
    let categoryList;

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
            document.getElementById(
                "activePercentageStat"
            );

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
            document.getElementById(
                "refreshProductsButton"
            );

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

        categoryScanForm =
            document.getElementById("categoryScanForm");

        categoryUrlInput =
            document.getElementById("categoryUrl");

        categoryLimitInput =
            document.getElementById("categoryLimit");

        categoryScanButton =
            document.getElementById(
                "categoryScanButton"
            );

        categoryScanStatus =
            document.getElementById(
                "categoryScanStatus"
            );

        categoryForm =
            document.getElementById("categoryForm");

        savedCategoryNameInput =
            document.getElementById(
                "savedCategoryName"
            );

        savedCategoryUrlInput =
            document.getElementById(
                "savedCategoryUrl"
            );

        savedCategoryLimitInput =
            document.getElementById(
                "savedCategoryLimit"
            );

        addCategoryButton =
            document.getElementById(
                "addCategoryButton"
            );

        scanAllCategoriesButton =
            document.getElementById(
                "scanAllCategoriesButton"
            );

        categoryManagementStatus =
            document.getElementById(
                "categoryManagementStatus"
            );

        categoryList =
            document.getElementById("categoryList");
    }

    function escapeHtml(value) {
        const element =
            document.createElement("div");

        element.textContent =
            value === null ||
            value === undefined
                ? ""
                : String(value);

        return element.innerHTML;
    }

    function formatNumber(value) {
        const numericValue = Number(value);

        if (!Number.isFinite(numericValue)) {
            return "-";
        }

        return new Intl.NumberFormat("tr-TR").format(
            numericValue
        );
    }

    function formatPrice(value) {
        const numericValue = Number(value);

        if (!Number.isFinite(numericValue)) {
            return "-";
        }

        return new Intl.NumberFormat("tr-TR", {
            style: "currency",
            currency: "TRY",
            minimumFractionDigits: 2,
            maximumFractionDigits: 2
        }).format(numericValue);
    }

    function formatPercentage(value) {
        const numericValue = Number(value);

        if (!Number.isFinite(numericValue)) {
            return "%0";
        }

        return `%${new Intl.NumberFormat(
            "tr-TR",
            {
                maximumFractionDigits: 1
            }
        ).format(numericValue)}`;
    }

    function isValidUrl(value) {
        try {
            const url = new URL(value);

            return (
                url.protocol === "http:" ||
                url.protocol === "https:"
            );
        } catch {
            return false;
        }
    }

    function isTrendyolUrl(value) {
        if (!isValidUrl(value)) {
            return false;
        }

        try {
            const url = new URL(value);

            return (
                url.hostname === "trendyol.com" ||
                url.hostname.endsWith(
                    ".trendyol.com"
                )
            );
        } catch {
            return false;
        }
    }

    function normalizeBoolean(value) {
        if (typeof value === "boolean") {
            return value;
        }

        if (typeof value === "number") {
            return value === 1;
        }

        if (typeof value === "string") {
            return [
                "true",
                "1",
                "yes",
                "active",
                "aktif"
            ].includes(value.toLowerCase());
        }

        return false;
    }

    async function getErrorMessage(response) {
        try {
            const data = await response.json();

            if (typeof data?.detail === "string") {
                return data.detail;
            }

            if (Array.isArray(data?.detail)) {
                return data.detail
                    .map((item) => {
                        const location =
                            Array.isArray(item.loc)
                                ? item.loc.join(" → ")
                                : "";

                        return location
                            ? `${location}: ${item.msg}`
                            : item.msg;
                    })
                    .join(", ");
            }

            if (typeof data?.message === "string") {
                return data.message;
            }

            if (typeof data?.error === "string") {
                return data.error;
            }
        } catch {
            // JSON olmayan hata cevapları burada yok sayılır.
        }

        return (
            `Sunucu hatası: ${response.status} ` +
            `${response.statusText || ""}`
        ).trim();
    }

    async function apiRequest(
        url,
        options = {},
        timeout = REQUEST_TIMEOUT
    ) {
        const controller =
            new AbortController();

        const timeoutId =
            window.setTimeout(
                () => controller.abort(),
                timeout
            );

        try {
            const headers = {
                Accept: "application/json",
                ...(options.headers || {})
            };

            const response = await fetch(url, {
                cache: "no-store",
                ...options,
                headers,
                signal: controller.signal
            });

            if (!response.ok) {
                throw new Error(
                    await getErrorMessage(response)
                );
            }

            if (response.status === 204) {
                return {};
            }

            const contentType =
                response.headers.get(
                    "content-type"
                ) || "";

            if (
                !contentType.includes(
                    "application/json"
                )
            ) {
                return {};
            }

            return await response.json();
        } catch (error) {
            if (error.name === "AbortError") {
                throw new Error(
                    "Sunucu belirtilen süre içinde cevap vermedi."
                );
            }

            throw error;
        } finally {
            window.clearTimeout(timeoutId);
        }
    }

    function showAlert(
        message,
        type = "success",
        duration = 5000
    ) {
        if (!alertArea || !message) {
            return;
        }

        const alert =
            document.createElement("div");

        alert.className =
            `alert alert-${type} ` +
            "alert-dismissible fade show";

        alert.setAttribute("role", "alert");

        const messageArea =
            document.createElement("span");

        messageArea.textContent =
            String(message);

        const closeButton =
            document.createElement("button");

        closeButton.type = "button";
        closeButton.className = "btn-close";
        closeButton.setAttribute(
            "data-bs-dismiss",
            "alert"
        );
        closeButton.setAttribute(
            "aria-label",
            "Kapat"
        );

        alert.appendChild(messageArea);
        alert.appendChild(closeButton);

        alertArea.prepend(alert);

        if (duration > 0) {
            window.setTimeout(() => {
                if (!alert.isConnected) {
                    return;
                }

                if (
                    window.bootstrap?.Alert
                ) {
                    const instance =
                        bootstrap.Alert.getOrCreateInstance(
                            alert
                        );

                    instance.close();
                } else {
                    alert.remove();
                }
            }, duration);
        }
    }

    function setStatusText(
        element,
        message,
        type = "secondary"
    ) {
        if (!element) {
            return;
        }

        element.className =
            `small text-${type} mt-3`;

        element.textContent =
            message || "";
    }

    function setButtonLoading(
        button,
        loading,
        loadingText,
        normalText
    ) {
        if (!button) {
            return;
        }

        button.disabled = loading;

        if (loading) {
            if (
                button.dataset.originalText ===
                undefined
            ) {
                button.dataset.originalText =
                    button.textContent;
            }

            button.textContent =
                loadingText || "İşleniyor...";
        } else {
            button.textContent =
                normalText ||
                button.dataset.originalText ||
                button.textContent;

            delete button.dataset.originalText;
        }
    }

    function loadTheme() {
        const storedTheme =
            localStorage.getItem(
                "firsatAiTheme"
            );

        const darkMode =
            storedTheme === "dark";

        document.body.classList.toggle(
            "dark-mode",
            darkMode
        );

        updateThemeButton();
    }

    function updateThemeButton() {
        if (!themeToggleButton) {
            return;
        }

        const darkMode =
            document.body.classList.contains(
                "dark-mode"
            );

        themeToggleButton.textContent =
            darkMode
                ? "☀️ Aydınlık Mod"
                : "🌙 Karanlık Mod";
    }

    function toggleTheme() {
        const darkMode =
            document.body.classList.toggle(
                "dark-mode"
            );

        localStorage.setItem(
            "firsatAiTheme",
            darkMode ? "dark" : "light"
        );

        updateThemeButton();
    }

    function setProductLoading(loading) {
        if (loadingArea) {
            loadingArea.classList.toggle(
                "d-none",
                !loading
            );

            loadingArea.style.display =
                loading ? "" : "none";
        }

        if (
            loading &&
            emptyArea
        ) {
            emptyArea.classList.add("d-none");
            emptyArea.style.display = "none";
        }

        if (
            loading &&
            productList
        ) {
            productList.innerHTML = "";
        }
    }

    function updateProductStats() {
        const total = products.length;

        const active = products.filter(
            (product) =>
                normalizeBoolean(product.active)
        ).length;

        const passive =
            total - active;

        const percentage =
            total > 0
                ? (active / total) * 100
                : 0;

        if (totalProductStat) {
            totalProductStat.textContent =
                String(total);
        }

        if (activeProductStat) {
            activeProductStat.textContent =
                String(active);
        }

        if (passiveProductStat) {
            passiveProductStat.textContent =
                String(passive);
        }

        if (activePercentageStat) {
            activePercentageStat.textContent =
                formatPercentage(percentage);
        }
    }

    function createDetailItem(
        label,
        value,
        extraClass = ""
    ) {
        const item =
            document.createElement("div");

        item.className =
            `small ${extraClass}`.trim();

        const labelElement =
            document.createElement("strong");

        labelElement.textContent =
            `${label}: `;

        const valueElement =
            document.createElement("span");

        valueElement.textContent =
            value === null ||
            value === undefined ||
            value === ""
                ? "-"
                : String(value);

        item.appendChild(labelElement);
        item.appendChild(valueElement);

        return item;
    }

    function createProductElement(product) {
        const productItem =
            document.createElement("article");

        productItem.className =
            "product-item";

        const searchText = [
            product.name,
            product.url,
            product.seller
        ]
            .filter(Boolean)
            .join(" ")
            .toLocaleLowerCase("tr-TR");

        productItem.dataset.searchText =
            searchText;

        const infoArea =
            document.createElement("div");

        infoArea.className =
            "product-info";

        const header =
            document.createElement("div");

        header.className =
            "d-flex flex-wrap " +
            "align-items-center gap-2 mb-2";

        const name =
            document.createElement("h3");

        name.className =
            "product-name mb-0";

        name.textContent =
            product.name ||
            "İsimsiz ürün";

        const active =
            normalizeBoolean(product.active);

        const status =
            document.createElement("span");

        status.className =
            active
                ? "status-badge status-active"
                : "status-badge status-passive";

        status.textContent =
            active ? "Aktif" : "Pasif";

        header.appendChild(name);
        header.appendChild(status);

        const productLink =
            document.createElement("a");

        productLink.className =
            "product-url mb-3";

        productLink.href =
            product.url || "#";

        productLink.target = "_blank";
        productLink.rel =
            "noopener noreferrer";

        productLink.textContent =
            product.url ||
            "Bağlantı bulunamadı";

        infoArea.appendChild(header);
        infoArea.appendChild(productLink);

        const detailArea =
            document.createElement("div");

        detailArea.className =
            "product-details";

        if (product.image) {
            const image =
                document.createElement("img");

            image.className =
                "product-image";

            image.src = product.image;

            image.alt =
                product.name ||
                "Ürün görseli";

            image.loading = "lazy";

            image.addEventListener(
                "error",
                () => {
                    image.remove();
                },
                { once: true }
            );

            detailArea.appendChild(image);
        }

        detailArea.appendChild(
            createDetailItem(
                "Güncel fiyat",
                formatPrice(product.price)
            )
        );

        detailArea.appendChild(
            createDetailItem(
                "Eski fiyat",
                formatPrice(product.old_price)
            )
        );

        detailArea.appendChild(
            createDetailItem(
                "İndirim",
                formatPercentage(
                    product.discount_percentage
                )
            )
        );

        detailArea.appendChild(
            createDetailItem(
                "Satıcı",
                product.seller || "-"
            )
        );

        detailArea.appendChild(
            createDetailItem(
                "Puan",
                product.rating ?? "-"
            )
        );

        detailArea.appendChild(
            createDetailItem(
                "Yorum",
                product.review_count !== null &&
                product.review_count !== undefined
                    ? formatNumber(
                        product.review_count
                    )
                    : "-"
            )
        );

        detailArea.appendChild(
            createDetailItem(
                "AI fırsat puanı",
                product.ai_score !== null &&
                product.ai_score !== undefined
                    ? product.ai_score
                    : "-"
            )
        );

        infoArea.appendChild(detailArea);

        const actions =
            document.createElement("div");

        actions.className =
            "product-actions";

        const openButton =
            document.createElement("a");

        openButton.className =
            "btn btn-sm btn-outline-primary";

        openButton.href =
            product.url || "#";

        openButton.target = "_blank";
        openButton.rel =
            "noopener noreferrer";

        openButton.textContent =
            "Ürünü Aç";

        const scanButton =
            document.createElement("button");

        scanButton.type = "button";

        scanButton.className =
            "btn btn-sm btn-primary";

        scanButton.textContent =
            "Şimdi Tara";

        scanButton.disabled =
            !product.url;

        scanButton.addEventListener(
            "click",
            () => {
                scanProduct(
                    product.url,
                    scanButton
                );
            }
        );

        const statusButton =
            document.createElement("button");

        statusButton.type = "button";

        statusButton.className =
            active
                ? "btn btn-sm btn-outline-warning"
                : "btn btn-sm btn-outline-success";

        statusButton.textContent =
            active
                ? "Durdur"
                : "Aktifleştir";

        statusButton.disabled =
            !product.url;

        statusButton.addEventListener(
            "click",
            () => {
                updateProductStatus(
                    product.url,
                    !active,
                    statusButton
                );
            }
        );

        const deleteButton =
            document.createElement("button");

        deleteButton.type = "button";

        deleteButton.className =
            "btn btn-sm btn-outline-danger";

        deleteButton.textContent =
            "Sil";

        deleteButton.disabled =
            !product.url;

        deleteButton.addEventListener(
            "click",
            () => {
                removeProduct(
                    product.name ||
                    "İsimsiz ürün",
                    product.url,
                    deleteButton
                );
            }
        );

        actions.appendChild(openButton);
        actions.appendChild(scanButton);
        actions.appendChild(statusButton);
        actions.appendChild(deleteButton);

        productItem.appendChild(infoArea);
        productItem.appendChild(actions);

        return productItem;
    }

    function renderProducts() {
        if (!productList) {
            return;
        }

        productList.innerHTML = "";

        if (products.length === 0) {
            if (emptyArea) {
                emptyArea.classList.remove(
                    "d-none"
                );

                emptyArea.style.display = "";
            }

            if (productCount) {
                productCount.textContent =
                    "Takip listesinde ürün bulunmuyor.";
            }

            return;
        }

        if (emptyArea) {
            emptyArea.classList.add("d-none");
            emptyArea.style.display = "none";
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
    }

    function filterProducts() {
        if (!productList) {
            return;
        }

        const query =
            productSearchInput?.value
                .trim()
                .toLocaleLowerCase("tr-TR") ||
            "";

        const productElements =
            Array.from(
                productList.querySelectorAll(
                    ".product-item"
                )
            );

        let visibleCount = 0;

        productElements.forEach(
            (productElement) => {
                const searchText =
                    productElement.dataset
                        .searchText || "";

                const visible =
                    !query ||
                    searchText.includes(query);

                productElement.style.display =
                    visible ? "" : "none";

                if (visible) {
                    visibleCount += 1;
                }
            }
        );

        if (productCount) {
            productCount.textContent =
                query
                    ? `${visibleCount} ürün bulundu`
                    : `${products.length} ürün takip listesinde`;
        }

        if (emptyArea) {
            if (
                products.length === 0
            ) {
                emptyArea.classList.remove(
                    "d-none"
                );

                emptyArea.style.display = "";
            } else {
                emptyArea.classList.add(
                    "d-none"
                );

                emptyArea.style.display = "none";
            }
        }
    }

    function clearSearch() {
        if (!productSearchInput) {
            return;
        }

        productSearchInput.value = "";
        filterProducts();
        productSearchInput.focus();
    }

    async function loadProducts() {
        setProductLoading(true);

        if (refreshProductsButton) {
            setButtonLoading(
                refreshProductsButton,
                true,
                "Yenileniyor..."
            );
        }

        try {
            const data = await apiRequest(
                PRODUCT_API_URL
            );

            products =
                Array.isArray(data)
                    ? data
                    : Array.isArray(data.products)
                        ? data.products
                        : [];

            renderProducts();
            updateProductStats();
        } catch (error) {
            console.error(
                "Ürün yükleme hatası:",
                error
            );

            products = [];

            if (productList) {
                productList.innerHTML = "";
            }

            if (productCount) {
                productCount.textContent =
                    "Ürünler yüklenemedi.";
            }

            updateProductStats();

            showAlert(
                `Ürün listesi yüklenemedi: ${error.message}`,
                "danger"
            );
        } finally {
            setProductLoading(false);

            if (refreshProductsButton) {
                setButtonLoading(
                    refreshProductsButton,
                    false,
                    "",
                    "Listeyi Yenile"
                );
            }
        }
    }

    async function addProduct(event) {
        event.preventDefault();

        const name =
            productNameInput?.value.trim() ||
            "";

        const url =
            productUrlInput?.value.trim() ||
            "";

        const active =
            Boolean(
                productActiveInput?.checked
            );

        if (!name) {
            showAlert(
                "Ürün adını yazmalısın.",
                "warning"
            );

            productNameInput?.focus();
            return;
        }

        if (!url) {
            showAlert(
                "Ürün bağlantısını yazmalısın.",
                "warning"
            );

            productUrlInput?.focus();
            return;
        }

        if (!isValidUrl(url)) {
            showAlert(
                "Geçerli bir ürün bağlantısı gir.",
                "warning"
            );

            productUrlInput?.focus();
            return;
        }

        if (!isTrendyolUrl(url)) {
            showAlert(
                "Lütfen bir Trendyol ürün bağlantısı gir.",
                "warning"
            );

            productUrlInput?.focus();
            return;
        }

        setButtonLoading(
            addProductButton,
            true,
            active
                ? "Ekleniyor ve taranıyor..."
                : "Ekleniyor..."
        );

        try {
            const data = await apiRequest(
                PRODUCT_API_URL,
                {
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
                },
                60000
            );

            addProductForm?.reset();

            if (productActiveInput) {
                productActiveInput.checked = true;
            }

            const baseMessage =
                data.message ||
                "Ürün başarıyla eklendi.";

            if (
                active &&
                data.scan_success === false
            ) {
                showAlert(
                    `${baseMessage} Otomatik tarama başarısız: ` +
                    `${data.scan_message || "Bilinmeyen hata"}`,
                    "warning",
                    8000
                );
            } else if (data.scan_message) {
                showAlert(
                    `${baseMessage} ${data.scan_message}`.trim()
                );
            } else {
                showAlert(baseMessage);
            }

            await loadProducts();
        } catch (error) {
            showAlert(
                error.message ||
                "Ürün eklenemedi.",
                "danger"
            );
        } finally {
            setButtonLoading(
                addProductButton,
                false,
                "",
                "Ürün Ekle"
            );
        }
    }

    async function scanProduct(
        url,
        button
    ) {
        if (!url) {
            showAlert(
                "Ürün bağlantısı bulunamadı.",
                "warning"
            );

            return;
        }

        setButtonLoading(
            button,
            true,
            "Taranıyor..."
        );

        try {
            const data = await apiRequest(
                `${PRODUCT_API_URL}/scan`,
                {
                    method: "POST",
                    headers: {
                        "Content-Type":
                            "application/json"
                    },
                    body: JSON.stringify({
                        url
                    })
                },
                90000
            );

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
            setButtonLoading(
                button,
                false,
                "",
                "Şimdi Tara"
            );
        }
    }

    async function updateProductStatus(
        url,
        active,
        button
    ) {
        if (!url) {
            return;
        }

        setButtonLoading(
            button,
            true,
            "Güncelleniyor..."
        );

        try {
            const data = await apiRequest(
                `${PRODUCT_API_URL}/status`,
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
            setButtonLoading(
                button,
                false,
                "",
                active
                    ? "Aktifleştir"
                    : "Durdur"
            );
        }
    }

    async function removeProduct(
        name,
        url,
        button
    ) {
        const confirmed =
            window.confirm(
                `"${name}" adlı ürün takip listesinden silinsin mi?`
            );

        if (!confirmed) {
            return;
        }

        setButtonLoading(
            button,
            true,
            "Siliniyor..."
        );

        try {
            const data = await apiRequest(
                PRODUCT_API_URL,
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

            showAlert(
                data.message ||
                "Ürün takip listesinden silindi."
            );

            await loadProducts();
        } catch (error) {
            showAlert(
                error.message ||
                "Ürün silinemedi.",
                "danger"
            );
        } finally {
            setButtonLoading(
                button,
                false,
                "",
                "Sil"
            );
        }
    }

    async function scanCategory(event) {
        event.preventDefault();

        const categoryUrl =
            categoryUrlInput?.value.trim() ||
            "";

        const limit =
            Number(
                categoryLimitInput?.value
            );

        if (!categoryUrl) {
            showAlert(
                "Kategori bağlantısını yazmalısın.",
                "warning"
            );

            categoryUrlInput?.focus();
            return;
        }

        if (!isTrendyolUrl(categoryUrl)) {
            showAlert(
                "Geçerli bir Trendyol kategori veya arama bağlantısı gir.",
                "warning"
            );

            categoryUrlInput?.focus();
            return;
        }

        if (
            !Number.isInteger(limit) ||
            limit < 1 ||
            limit > 50
        ) {
            showAlert(
                "Ürün sayısı 1 ile 50 arasında olmalıdır.",
                "warning"
            );

            categoryLimitInput?.focus();
            return;
        }

        setButtonLoading(
            categoryScanButton,
            true,
            "Taranıyor..."
        );

        setStatusText(
            categoryScanStatus,
            "Kategori taranıyor...",
            "primary"
        );

        try {
            const data = await apiRequest(
                `${PRODUCT_API_URL}/category-scan`,
                {
                    method: "POST",
                    headers: {
                        "Content-Type":
                            "application/json"
                    },
                    body: JSON.stringify({
                        category_url:
                            categoryUrl,
                        limit
                    })
                },
                180000
            );

            const message =
                data.message ||
                "Kategori taraması tamamlandı.";

            setStatusText(
                categoryScanStatus,
                message,
                "success"
            );

            showAlert(message);

            await loadProducts();
        } catch (error) {
            setStatusText(
                categoryScanStatus,
                error.message,
                "danger"
            );

            showAlert(
                error.message ||
                "Kategori taranamadı.",
                "danger",
                8000
            );
        } finally {
            setButtonLoading(
                categoryScanButton,
                false,
                "",
                "Trendyol'u Tara"
            );
        }
    }

        function createCategoryElement(category) {
        const item =
            document.createElement("article");

        item.className =
            "border rounded-3 p-3";

        const wrapper =
            document.createElement("div");

        wrapper.className =
            "d-flex flex-wrap " +
            "justify-content-between " +
            "align-items-start gap-3";

        const info =
            document.createElement("div");

        info.className =
            "flex-grow-1 min-w-0";

        const titleRow =
            document.createElement("div");

        titleRow.className =
            "d-flex flex-wrap " +
            "align-items-center gap-2 mb-2";

        const title =
            document.createElement("h3");

        title.className =
            "h6 fw-bold mb-0";

        title.textContent =
            category.name ||
            "İsimsiz kategori";

        const active =
            normalizeBoolean(category.active);

        const status =
            document.createElement("span");

        status.className =
            active
                ? "badge text-bg-success"
                : "badge text-bg-secondary";

        status.textContent =
            active ? "Aktif" : "Pasif";

        titleRow.appendChild(title);
        titleRow.appendChild(status);

        const link =
            document.createElement("a");

        link.href =
            category.url || "#";

        link.target = "_blank";
        link.rel = "noopener noreferrer";

        link.className =
            "small d-block mb-2 text-break";

        link.textContent =
            category.url ||
            "Bağlantı bulunamadı";

        const detail =
            document.createElement("div");

        detail.className =
            "small text-secondary";

        detail.textContent =
            `Tarama limiti: ${category.limit ?? 10}`;

        info.appendChild(titleRow);
        info.appendChild(link);
        info.appendChild(detail);

        const actions =
            document.createElement("div");

        actions.className =
            "d-flex flex-wrap gap-2";

        const scanButton =
            document.createElement("button");

        scanButton.type = "button";

        scanButton.className =
            "btn btn-sm btn-primary";

        scanButton.textContent =
            "Şimdi Tara";

        scanButton.disabled =
            !category.id;

        scanButton.addEventListener(
            "click",
            () => {
                scanSavedCategory(
                    category,
                    scanButton
                );
            }
        );

        const statusButton =
            document.createElement("button");

        statusButton.type = "button";

        statusButton.className =
            active
                ? "btn btn-sm btn-outline-warning"
                : "btn btn-sm btn-outline-success";

        statusButton.textContent =
            active
                ? "Durdur"
                : "Aktifleştir";

        statusButton.disabled =
            !category.id;

        statusButton.addEventListener(
            "click",
            () => {
                updateCategoryStatus(
                    category,
                    !active,
                    statusButton
                );
            }
        );

        const deleteButton =
            document.createElement("button");

        deleteButton.type = "button";

        deleteButton.className =
            "btn btn-sm btn-outline-danger";

        deleteButton.textContent = "Sil";

        deleteButton.disabled =
            !category.id;

        deleteButton.addEventListener(
            "click",
            () => {
                removeCategory(
                    category,
                    deleteButton
                );
            }
        );

        actions.appendChild(scanButton);
        actions.appendChild(statusButton);
        actions.appendChild(deleteButton);

        wrapper.appendChild(info);
        wrapper.appendChild(actions);

        item.appendChild(wrapper);

        return item;
    }

    function renderCategories() {
        if (!categoryList) {
            return;
        }

        categoryList.innerHTML = "";

        if (categories.length === 0) {
            const empty =
                document.createElement("div");

            empty.className =
                "text-secondary";

            empty.textContent =
                "Henüz kayıtlı kategori yok.";

            categoryList.appendChild(empty);
            return;
        }

        const fragment =
            document.createDocumentFragment();

        categories.forEach((category) => {
            fragment.appendChild(
                createCategoryElement(category)
            );
        });

        categoryList.appendChild(fragment);
    }

    async function loadCategories() {
        if (!categoryList) {
            return;
        }

        categoryList.innerHTML =
            '<div class="text-secondary">' +
            "Kategoriler yükleniyor..." +
            "</div>";

        try {
            const data = await apiRequest(
                CATEGORY_API_URL
            );

            categories =
                Array.isArray(data)
                    ? data
                    : Array.isArray(data.categories)
                        ? data.categories
                        : [];

            renderCategories();

            setStatusText(
                categoryManagementStatus,
                categories.length > 0
                    ? `${categories.length} kategori kayıtlı.`
                    : "Henüz kayıtlı kategori yok.",
                "secondary"
            );
        } catch (error) {
            categories = [];

            categoryList.innerHTML = "";

            const errorArea =
                document.createElement("div");

            errorArea.className =
                "text-danger";

            errorArea.textContent =
                `Kategoriler yüklenemedi: ${error.message}`;

            categoryList.appendChild(errorArea);

            setStatusText(
                categoryManagementStatus,
                error.message,
                "danger"
            );

            showAlert(
                `Kategori listesi yüklenemedi: ${error.message}`,
                "danger"
            );
        }
    }

    async function addCategory(event) {
        event.preventDefault();

        const name =
            savedCategoryNameInput
                ?.value.trim() || "";

        const url =
            savedCategoryUrlInput
                ?.value.trim() || "";

        const limit =
            Number(
                savedCategoryLimitInput
                    ?.value
            );

        if (!name) {
            showAlert(
                "Kategori adını yazmalısın.",
                "warning"
            );

            savedCategoryNameInput?.focus();
            return;
        }

        if (!url) {
            showAlert(
                "Kategori bağlantısını yazmalısın.",
                "warning"
            );

            savedCategoryUrlInput?.focus();
            return;
        }

        if (!isTrendyolUrl(url)) {
            showAlert(
                "Geçerli bir Trendyol kategori bağlantısı gir.",
                "warning"
            );

            savedCategoryUrlInput?.focus();
            return;
        }

        if (
            !Number.isInteger(limit) ||
            limit < 1 ||
            limit > 100
        ) {
            showAlert(
                "Kategori limiti 1 ile 100 arasında olmalıdır.",
                "warning"
            );

            savedCategoryLimitInput?.focus();
            return;
        }

        setButtonLoading(
            addCategoryButton,
            true,
            "Ekleniyor..."
        );

        setStatusText(
            categoryManagementStatus,
            "Kategori ekleniyor...",
            "primary"
        );

        try {
            const data = await apiRequest(
                CATEGORY_API_URL,
                {
                    method: "POST",
                    headers: {
                        "Content-Type":
                            "application/json"
                    },
                    body: JSON.stringify({
                        name,
                        url,
                        limit,
                        active: true
                    })
                }
            );

            categoryForm?.reset();

            if (savedCategoryLimitInput) {
                savedCategoryLimitInput.value =
                    "10";
            }

            const message =
                data.message ||
                "Kategori başarıyla eklendi.";

            setStatusText(
                categoryManagementStatus,
                message,
                "success"
            );

            showAlert(message);

            await loadCategories();
        } catch (error) {
            setStatusText(
                categoryManagementStatus,
                error.message,
                "danger"
            );

            showAlert(
                error.message ||
                "Kategori eklenemedi.",
                "danger"
            );
        } finally {
            setButtonLoading(
                addCategoryButton,
                false,
                "",
                "Kategori Ekle"
            );
        }
    }

    async function updateCategoryStatus(
        category,
        active,
        button
    ) {
        if (!category?.id) {
            showAlert(
                "Kategori kimliği bulunamadı.",
                "danger"
            );

            return;
        }

        setButtonLoading(
            button,
            true,
            "Güncelleniyor..."
        );

        try {
            const data = await apiRequest(
                `${CATEGORY_API_URL}/status`,
                {
                    method: "PATCH",
                    headers: {
                        "Content-Type":
                            "application/json"
                    },
                    body: JSON.stringify({
                        id: category.id,
                        active
                    })
                }
            );

            showAlert(
                data.message ||
                (
                    active
                        ? "Kategori aktifleştirildi."
                        : "Kategori durduruldu."
                )
            );

            await loadCategories();
        } catch (error) {
            showAlert(
                error.message ||
                "Kategori durumu değiştirilemedi.",
                "danger"
            );
        } finally {
            setButtonLoading(
                button,
                false,
                "",
                active
                    ? "Aktifleştir"
                    : "Durdur"
            );
        }
    }

    async function removeCategory(
        category,
        button
    ) {
        const confirmed =
            window.confirm(
                `"${category.name || "İsimsiz kategori"}" silinsin mi?`
            );

        if (!confirmed) {
            return;
        }

        if (!category?.id) {
            showAlert(
                "Kategori kimliği bulunamadı.",
                "danger"
            );

            return;
        }

        setButtonLoading(
            button,
            true,
            "Siliniyor..."
        );

        try {
            const data = await apiRequest(
                CATEGORY_API_URL,
                {
                    method: "DELETE",
                    headers: {
                        "Content-Type":
                            "application/json"
                    },
                    body: JSON.stringify({
                        id: category.id
                    })
                }
            );

            showAlert(
                data.message ||
                "Kategori silindi."
            );

            await loadCategories();
        } catch (error) {
            showAlert(
                error.message ||
                "Kategori silinemedi.",
                "danger"
            );
        } finally {
            setButtonLoading(
                button,
                false,
                "",
                "Sil"
            );
        }
    }

    async function scanSavedCategory(
        category,
        button
    ) {
        if (!category?.id) {
            showAlert(
                "Kategori kimliği bulunamadı.",
                "danger"
            );

            return;
        }

        setButtonLoading(
            button,
            true,
            "Taranıyor..."
        );

        setStatusText(
            categoryManagementStatus,
            `${category.name || "Kategori"} taranıyor...`,
            "primary"
        );

        try {
            const data = await apiRequest(
                `${CATEGORY_API_URL}/${category.id}/scan`,
                {
                    method: "POST",
                    headers: {
                        Accept:
                            "application/json"
                    }
                },
                180000
            );

            const message =
                data.message ||
                "Kategori taraması tamamlandı.";

            setStatusText(
                categoryManagementStatus,
                message,
                "success"
            );

            showAlert(message);

            await Promise.all([
                loadCategories(),
                loadProducts()
            ]);
        } catch (error) {
            setStatusText(
                categoryManagementStatus,
                error.message,
                "danger"
            );

            showAlert(
                error.message ||
                "Kategori taranamadı.",
                "danger",
                8000
            );
        } finally {
            setButtonLoading(
                button,
                false,
                "",
                "Şimdi Tara"
            );
        }
    }

    async function scanAllCategories() {
        const activeCategories =
            categories.filter(
                (category) =>
                    normalizeBoolean(
                        category.active
                    )
            );

        if (activeCategories.length === 0) {
            showAlert(
                "Taranacak aktif kategori bulunmuyor.",
                "warning"
            );

            return;
        }

        const confirmed =
            window.confirm(
                `${activeCategories.length} aktif kategori taransın mı?`
            );

        if (!confirmed) {
            return;
        }

        setButtonLoading(
            scanAllCategoriesButton,
            true,
            "Kategoriler Taranıyor..."
        );

        setStatusText(
            categoryManagementStatus,
            "Tüm aktif kategoriler taranıyor...",
            "primary"
        );

        try {
            const data = await apiRequest(
                `${CATEGORY_API_URL}/scan-all`,
                {
                    method: "POST",
                    headers: {
                        Accept:
                            "application/json"
                    }
                },
                300000
            );

            const message =
                data.message ||
                "Tüm kategori taramaları tamamlandı.";

            setStatusText(
                categoryManagementStatus,
                message,
                "success"
            );

            showAlert(
                message,
                "success",
                8000
            );

            await Promise.all([
                loadCategories(),
                loadProducts()
            ]);
        } catch (error) {
            setStatusText(
                categoryManagementStatus,
                error.message,
                "danger"
            );

            showAlert(
                error.message ||
                "Toplu kategori taraması başarısız oldu.",
                "danger",
                10000
            );
        } finally {
            setButtonLoading(
                scanAllCategoriesButton,
                false,
                "",
                "🚀 Tüm Kategorileri Tara"
            );
        }
    }

    function showMissingElementWarnings() {
        const requiredElements = [
            {
                name: "productList",
                element: productList
            },
            {
                name: "productCount",
                element: productCount
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
                name: "categoryList",
                element: categoryList
            },
            {
                name: "categoryForm",
                element: categoryForm
            }
        ];

        const missing =
            requiredElements
                .filter(
                    (item) =>
                        !item.element
                )
                .map(
                    (item) =>
                        item.name
                );

        if (missing.length > 0) {
            console.warn(
                "HTML içinde bulunamayan alanlar:",
                missing.join(", ")
            );
        }
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

        categoryScanForm?.addEventListener(
            "submit",
            scanCategory
        );

        categoryForm?.addEventListener(
            "submit",
            addCategory
        );

        scanAllCategoriesButton?.addEventListener(
            "click",
            scanAllCategories
        );
    }

    async function initializePage() {
        getElements();
        showMissingElementWarnings();
        loadTheme();
        bindEvents();

        try {
            await Promise.all([
                loadProducts(),
                loadCategories()
            ]);
        } catch (error) {
            console.error(
                "Sayfa başlatma hatası:",
                error
            );

            setProductLoading(false);

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
            initializePage,
            { once: true }
        );
    } else {
        initializePage();
    }
})();
