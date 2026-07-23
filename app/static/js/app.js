const searchInput = document.getElementById("search");
const scoreFilter = document.getElementById("scoreFilter");
const sortSelect = document.getElementById("sortSelect");
const noResults = document.getElementById("noResults");
const productList = document.getElementById("productList");

function filterAndSortProducts() {
    const searchValue = searchInput.value
        .toLocaleLowerCase("tr-TR")
        .trim();

    const minimumScore = Number(scoreFilter.value);
    const sortValue = sortSelect.value;

    const cards = Array.from(
        document.querySelectorAll(".product-card")
    );

    let visibleCount = 0;

    cards.forEach(card => {
        const cardText = card.innerText
            .toLocaleLowerCase("tr-TR");

        const score = Number(card.dataset.score);

        const matchesSearch =
            cardText.includes(searchValue);

        const matchesScore =
            score >= minimumScore;

        const isVisible =
            matchesSearch && matchesScore;

        card.style.display =
            isVisible ? "" : "none";

        if (isVisible) {
            visibleCount++;
        }
    });

    cards.sort((firstCard, secondCard) => {
        const firstScore =
            Number(firstCard.dataset.score);

        const secondScore =
            Number(secondCard.dataset.score);

        const firstPrice =
            Number(firstCard.dataset.price);

        const secondPrice =
            Number(secondCard.dataset.price);

        const firstRating =
            Number(firstCard.dataset.rating);

        const secondRating =
            Number(secondCard.dataset.rating);

        const firstIndex =
            Number(firstCard.dataset.index);

        const secondIndex =
            Number(secondCard.dataset.index);

        switch (sortValue) {
            case "score-desc":
                return secondScore - firstScore;

            case "score-asc":
                return firstScore - secondScore;

            case "price-asc":
                return firstPrice - secondPrice;

            case "price-desc":
                return secondPrice - firstPrice;

            case "rating-desc":
                return secondRating - firstRating;

            default:
                return firstIndex - secondIndex;
        }
    });

    cards.forEach(card => {
        productList.appendChild(card);
    });

    noResults.style.display =
        visibleCount === 0
            ? "block"
            : "none";
}

searchInput.addEventListener(
    "input",
    filterAndSortProducts
);

scoreFilter.addEventListener(
    "change",
    filterAndSortProducts
);

sortSelect.addEventListener(
    "change",
    filterAndSortProducts
);

let chart = null;

const historyModalElement =
    document.getElementById("historyModal");

const historyModal =
    new bootstrap.Modal(historyModalElement);

function showHistoryFromButton(button) {
    const productId = button.dataset.productId;
    const productName = button.dataset.productName;

    showHistory(productId, productName);
}

async function showHistory(id, name) {
    const modalTitle =
        document.getElementById("modalTitle");

    const loading =
        document.getElementById("historyLoading");

    const historyMessage =
        document.getElementById("historyMessage");

    const chartContainer =
        document.getElementById("chartContainer");

    modalTitle.innerText =
        name + " — Fiyat Geçmişi";

    loading.style.display = "block";
    historyMessage.style.display = "none";
    chartContainer.style.display = "none";

    if (chart) {
        chart.destroy();
        chart = null;
    }

    historyModal.show();

    try {
        const response = await fetch(
            `/history/${encodeURIComponent(id)}`
        );

        if (!response.ok) {
            throw new Error(
                `Sunucu hatası: ${response.status}`
            );
        }

        const data = await response.json();

        loading.style.display = "none";

        if (!Array.isArray(data) || data.length === 0) {
            historyMessage.innerText =
                "Bu ürün için henüz fiyat geçmişi bulunmuyor.";

            historyMessage.style.display = "block";
            return;
        }

        const labels = data.map(item => item.date);
        const prices = data.map(item => Number(item.price));

        chartContainer.style.display = "block";

        const context =
            document.getElementById("chart")
                .getContext("2d");

        chart = new Chart(context, {
            type: "line",

            data: {
                labels: labels,

                datasets: [
                    {
                        label: "Fiyat",

                        data: prices,

                        borderColor: "#0d6efd",

                        backgroundColor:
                            "rgba(13, 110, 253, 0.15)",

                        borderWidth: 3,

                        pointRadius: 5,

                        pointHoverRadius: 7,

                        fill: true,

                        tension: 0.3
                    }
                ]
            },

            options: {
                responsive: true,

                maintainAspectRatio: false,

                interaction: {
                    mode: "index",
                    intersect: false
                },

                plugins: {
                    legend: {
                        display: true
                    },

                    tooltip: {
                        callbacks: {
                            label: function (context) {
                                return new Intl.NumberFormat(
                                    "tr-TR",
                                    {
                                        style: "currency",
                                        currency: "TRY"
                                    }
                                ).format(context.raw);
                            }
                        }
                    }
                },

                scales: {
                    y: {
                        beginAtZero: false,

                        ticks: {
                            callback: function (value) {
                                return new Intl.NumberFormat(
                                    "tr-TR"
                                ).format(value) + " TL";
                            }
                        }
                    }
                }
            }
        });

    } catch (error) {
        console.error(error);

        loading.style.display = "none";

        historyMessage.innerText =
            "Fiyat geçmişi yüklenirken bir hata oluştu.";

        historyMessage.className =
            "alert alert-danger text-center";

        historyMessage.style.display = "block";
    }
}

historyModalElement.addEventListener(
    "hidden.bs.modal",
    function () {
        if (chart) {
            chart.destroy();
            chart = null;
        }

        const historyMessage =
            document.getElementById("historyMessage");

        historyMessage.className =
            "alert alert-info text-center";
    }
);
