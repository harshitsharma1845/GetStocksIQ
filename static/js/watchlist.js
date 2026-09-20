document.addEventListener("DOMContentLoaded", () => {

    const searchInput = document.getElementById("stockSearchInput");
    const resultBox = document.getElementById("stockResults");
    const watchlistSearch = document.getElementById("watchlistSearch");
    const addStockHint = document.getElementById("addStockHint");

    /* -------------------------
       Search inside watchlist
    --------------------------*/

    if (watchlistSearch) {

        watchlistSearch.addEventListener("keyup", function () {

            const value = this.value.toLowerCase();

            document.querySelectorAll(".watchlist-card").forEach(card => {

                const symbol = card.dataset.symbol.toLowerCase();

                card.style.display = symbol.includes(value)
                    ? "block"
                    : "none";

            });

        });

    }

    /* -------------------------
       Live Stock Search
    --------------------------*/

    if (searchInput) {

        let timer;

        searchInput.addEventListener("keyup", function () {

            clearTimeout(timer);

            const query = this.value.trim();

            if (query.length < 2) {

                resultBox.innerHTML = "";
                if (addStockHint) addStockHint.textContent = "Start typing to find a stock.";

                return;

            }

            timer = setTimeout(async () => {

                if (addStockHint) addStockHint.textContent = "Searching live NSE listings…";
                const response = await fetch(`/api/search-stocks?q=${encodeURIComponent(query)}`);

                const stocks = await response.json();

                resultBox.innerHTML = "";

                if (!stocks.length) {

                    resultBox.innerHTML =
                        "<p class='text-center mt-3'>No stock found.</p>";

                    return;

                }

                if (addStockHint) addStockHint.textContent = `${stocks.length} matching stock${stocks.length === 1 ? "" : "s"} found`;

                stocks.forEach(stock => {

                    resultBox.innerHTML += `

                    <div class="search-item">

                        <div>

                            <strong>${stock.symbol}</strong>

                            <small>${stock.name}</small>

                        </div>

                        <button
                            class="btn btn-primary btn-sm add-stock"
                            data-symbol="${stock.symbol}">

                            Add

                        </button>

                    </div>

                    `;

                });

            }, 300);

        });

    }

    /* -------------------------
       Add Stock
    --------------------------*/

    document.addEventListener("click", async (e) => {

        if (!e.target.classList.contains("add-stock")) return;

        const symbol = e.target.dataset.symbol;

        const response = await fetch("/watchlist/add", {

            method: "POST",

            headers: {

                "Content-Type": "application/json"

            },

            body: JSON.stringify({

                symbol

            })

        });

        const result = await response.json();

        if (result.success) {

            location.reload();

        } else {

            alert(result.message);

        }

    });

    /* -------------------------
       Remove Stock
    --------------------------*/

    document.querySelectorAll(".remove-stock").forEach(btn => {

        btn.addEventListener("click", async function () {

            if (!confirm("Remove this stock?")) return;

            await fetch("/watchlist/remove", {

                method: "POST",

                headers: {

                    "Content-Type": "application/json"

                },

                body: JSON.stringify({

                    symbol: this.dataset.symbol

                })

            });

            this.closest(".watchlist-card").remove();

        });

    });

    /* -------------------------
       Load Live Data
    --------------------------*/


    const chart = document.getElementById("allocationChart");

    if (chart) {

        const legend = document.getElementById("portfolioLegend");

        async function loadWatchlistSummary() {

            const res = await fetch("/api/watchlist-summary");

            const data = await res.json();

            document.getElementById("summaryHoldings").innerText = data.holdings;

            document.getElementById("summaryGainers").innerText = data.gainers;

            document.getElementById("summaryLosers").innerText = data.losers;

            document.getElementById("summaryReturn").innerText =
                data.avg_return + "%";

            document.getElementById("gainersCount").innerText = data.gainers;

            document.getElementById("losersCount").innerText = data.losers;

            createPortfolioChart(data.allocation || []);

            updateCards(data.stocks || []);

            document.dispatchEvent(new CustomEvent("watchlist:data-ready"));

        }

        function createPortfolioChart(sectors) {

            if (window.portfolioChart) {
                window.portfolioChart.destroy();
            }

            const colors = [
                "#2563eb",
                "#16a34a",
                "#f59e0b",
                "#9333ea",
                "#ef4444",
                "#0ea5e9",
                "#14b8a6",
                "#64748b"
            ];

            window.portfolioChart = new Chart(chart, {
                type: "doughnut",

                data: {
                    labels: sectors.map(x => x.sector),

                    datasets: [{
                        data: sectors.map(x => x.percentage),
                        backgroundColor: colors.slice(0, sectors.length),
                        borderWidth: 0
                    }]
                },

                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    cutout: "72%",
                    plugins: {
                        legend: { display: false }
                    }
                }

            });

            legend.innerHTML = "";

            sectors.forEach((item, index) => {

                legend.innerHTML += `

        <div class="legend-item">

            <div class="legend-left">

                <span class="legend-color"
                style="background:${colors[index]}"></span>

                <strong>${item.sector}</strong>

            </div>

            <span>${item.percentage}%</span>

        </div>

        `;

            });

        }
        loadWatchlistSummary();
    }

    function updateCards(stocks) {

        stocks.forEach(stock => {

            const symbol = stock.symbol;

            const change = document.getElementById(`change-${symbol}`);

            if (change) {

                change.innerText = stock.price_change;

                change.classList.remove("green", "red");

                if (stock.price_change_value > 0)
                    change.classList.add("green");

                else if (stock.price_change_value < 0)
                    change.classList.add("red");

            }
            console.log(stock.symbol);

            console.log(document.getElementById(`company-${stock.symbol}`));

            console.log(document.getElementById(`price-${stock.symbol}`));

            const company = document.getElementById(`company-${symbol}`);
            if (company) {
                company.innerText = stock.name;
            }


            const price = document.getElementById(`price-${symbol}`);
            if (price) {
                price.innerText = "₹ " + stock.price;
            }

            const marketcap = document.getElementById(`marketcap-${symbol}`);
            if (marketcap) {
                marketcap.innerText = stock.market_cap;
            }

            const pe = document.getElementById(`pe-${symbol}`);
            if (pe) {
                pe.innerText = stock.pe;
            }

            const high = document.getElementById(`high-${symbol}`);
            if (high) {
                high.innerText = stock.high52;
            }

            const low = document.getElementById(`low-${symbol}`);
            if (low) {
                low.innerText = stock.low52;
            }

            const sector = document.getElementById(`sector-${symbol}`);
            if (sector) {
                sector.innerHTML = `<i class="bi bi-building"></i>${stock.sector}`;
            }

            const signal = document.getElementById(`signal-${symbol}`);

            if (!signal) return;

            if (stock.price_change_value >= 2) {

                signal.className = "signal-badge buy";
                signal.innerText = "BUY";

            }
            else if (stock.price_change_value <= -2) {

                signal.className = "signal-badge sell";
                signal.innerText = "SELL";

            }
            else {

                signal.className = "signal-badge hold";
                signal.innerText = "HOLD";

            }



        });

    }


});
function formatMarketCap(value) {

    if (!value) return "--";

    if (value >= 1e12)
        return (value / 1e12).toFixed(2) + " T";

    if (value >= 1e9)
        return (value / 1e9).toFixed(2) + " B";

    if (value >= 1e7)
        return (value / 1e7).toFixed(2) + " Cr";

    return value;

}

async function loadMarketWidget() {

    try {

        const res = await fetch("/dashboard-market");

        const data = await res.json();

        const niftyValue = document.getElementById("niftyValue");
        const sensexValue = document.getElementById("sensexValue");
        const niftyChange = document.getElementById("niftyChange");
        const sensexChange = document.getElementById("sensexChange");

        if (!niftyValue || !sensexValue || !niftyChange || !sensexChange) return;

        niftyValue.innerHTML = data.nifty;

        sensexValue.innerHTML = data.sensex;

        niftyChange.innerHTML = data.nifty_change;

        sensexChange.innerHTML = data.sensex_change;

    }

    catch (e) {

        console.log(e);

    }



}

loadMarketWidget();

document.addEventListener("DOMContentLoaded", function () {
    const grid = document.getElementById("watchlistGrid");
    const search = document.getElementById("watchlistSearch");
    const sort = document.getElementById("watchlistSort");
    const filter = document.getElementById("watchlistFilter");

    function cardValue(card, selector) {
        const node = card.querySelector(selector);
        return node ? node.textContent.trim() : "";
    }

    function numericValue(value) {
        const match = String(value).replace(/,/g, "").match(/-?[\d.]+/);
        return match ? Number(match[0]) : 0;
    }

    function refreshWatchlist() {
        if (!grid) return;
        const query = (search ? search.value : "").trim().toLowerCase();
        const filterMode = filter ? filter.selectedIndex : 0;
        const sortMode = sort ? sort.selectedIndex : 0;
        const cards = Array.from(grid.querySelectorAll(".watchlist-card"));

        cards.forEach(function (card) {
            const symbol = (card.dataset.symbol || "").toLowerCase();
            const company = cardValue(card, ".company-name").toLowerCase();
            const change = numericValue(cardValue(card, ".stock-change"));
            const matchesSearch = !query || symbol.includes(query) || company.includes(query);
            const matchesFilter = filterMode === 0 || (filterMode === 1 && change > 0) || (filterMode === 2 && change < 0);
            card.hidden = !(matchesSearch && matchesFilter);
        });

        cards.sort(function (a, b) {
            const symbolA = a.dataset.symbol || "";
            const symbolB = b.dataset.symbol || "";
            const priceA = numericValue(cardValue(a, ".stock-price"));
            const priceB = numericValue(cardValue(b, ".stock-price"));
            const changeA = numericValue(cardValue(a, ".stock-change"));
            const changeB = numericValue(cardValue(b, ".stock-change"));
            if (sortMode === 1) return symbolA.localeCompare(symbolB);
            if (sortMode === 2) return symbolB.localeCompare(symbolA);
            if (sortMode === 3) return priceB - priceA;
            if (sortMode === 4) return priceA - priceB;
            if (sortMode === 5) return changeB - changeA;
            if (sortMode === 6) return changeA - changeB;
            return 0;
        }).forEach(function (card) { grid.appendChild(card); });
    }

    if (search) search.addEventListener("input", refreshWatchlist);
    if (sort) sort.addEventListener("change", refreshWatchlist);
    if (filter) filter.addEventListener("change", refreshWatchlist);
    document.addEventListener("watchlist:data-ready", refreshWatchlist);
});
