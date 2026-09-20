document.addEventListener("DOMContentLoaded", () => {
    // DOM Elements
    const buyModalEl = document.getElementById("buyModal");
    const sellModalEl = document.getElementById("sellModal");
    const buyModal = buyModalEl ? new bootstrap.Modal(buyModalEl) : null;
    const sellModal = sellModalEl ? new bootstrap.Modal(sellModalEl) : null;

    const openBuyBtn = document.getElementById("openBuyModalBtn");
    const openSellBtn = document.getElementById("openSellModalBtn");
    const tableAddBtn = document.getElementById("tableAddBtn");
    const emptyStateAddBtn = document.getElementById("emptyStateAddBtn");

    const buyForm = document.getElementById("buyForm");
    const sellForm = document.getElementById("sellForm");
    const buySymbolInput = document.getElementById("buySymbolInput");
    const buyQtyInput = document.getElementById("buyQtyInput");
    const buyPriceInput = document.getElementById("buyPriceInput");
    const buyFeesInput = document.getElementById("buyFeesInput");
    const buyTotalPreview = document.getElementById("buyTotalPreview");
    const fetchBuyPriceBtn = document.getElementById("fetchBuyPriceBtn");
    const buyStockMeta = document.getElementById("buyStockMeta");
    const buySuggestions = document.getElementById("buySymbolSuggestions");

    const sellSymbolSelect = document.getElementById("sellSymbolSelect");
    const sellQtyInput = document.getElementById("sellQtyInput");
    const sellPriceInput = document.getElementById("sellPriceInput");
    const sellFeesInput = document.getElementById("sellFeesInput");
    const sellPnlPreview = document.getElementById("sellPnlPreview");
    const sellMaxQtyText = document.getElementById("sellMaxQtyText");

    const analyzeBtn = document.getElementById("analyzePortfolioAiBtn");
    const aiPanel = document.getElementById("aiAdvisorPanel");
    const aiContent = document.getElementById("aiAdvisorContent");
    const closeAdvisorBtn = document.getElementById("closeAdvisorBtn");

    const alertArea = document.getElementById("portfolioAlertArea");
    const searchInput = document.getElementById("holdingSearchInput");

    function showAlert(message, type = "success") {
        if (!alertArea) return;
        alertArea.innerHTML = `
            <div class="alert alert-${type} alert-dismissible fade show" role="alert">
                ${message}
                <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
            </div>
        `;
        window.scrollTo({ top: 0, behavior: "smooth" });
    }

    // Open Buy Modal
    function showBuyModal(symbol = "", price = "") {
        if (buySymbolInput) buySymbolInput.value = symbol;
        if (buyPriceInput) buyPriceInput.value = price;
        if (buyQtyInput) buyQtyInput.value = "";
        if (buyStockMeta) buyStockMeta.textContent = "";
        updateBuyTotal();
        if (buyModal) buyModal.show();
        if (symbol && !price) fetchPriceForBuy(symbol);
    }

    // Open Sell Modal
    function showSellModal(symbol = "", maxQty = "", price = "") {
        if (sellSymbolSelect && symbol) {
            sellSymbolSelect.value = symbol;
            const selectedOpt = sellSymbolSelect.options[sellSymbolSelect.selectedIndex];
            if (selectedOpt) {
                maxQty = selectedOpt.dataset.qty || maxQty;
                price = selectedOpt.dataset.price || price;
            }
        }
        if (sellMaxQtyText) sellMaxQtyText.textContent = `Max: ${maxQty || 0} shares`;
        if (sellQtyInput) {
            sellQtyInput.value = "";
            sellQtyInput.max = maxQty || 999999;
        }
        if (sellPriceInput) sellPriceInput.value = price || "";
        updateSellPnl();
        if (sellModal) sellModal.show();
    }

    if (openBuyBtn) openBuyBtn.addEventListener("click", () => showBuyModal());
    if (tableAddBtn) tableAddBtn.addEventListener("click", () => showBuyModal());
    if (emptyStateAddBtn) emptyStateAddBtn.addEventListener("click", () => showBuyModal());
    if (openSellBtn) openSellBtn.addEventListener("click", () => showSellModal());

    // Row Quick Buttons
    document.querySelectorAll(".quick-buy-btn").forEach(btn => {
        btn.addEventListener("click", () => {
            showBuyModal(btn.dataset.symbol, btn.dataset.price);
        });
    });

    document.querySelectorAll(".quick-sell-btn").forEach(btn => {
        btn.addEventListener("click", () => {
            showSellModal(btn.dataset.symbol, btn.dataset.qty, btn.dataset.price);
        });
    });

    // Buy Price Fetch
    async function fetchPriceForBuy(symbol) {
        if (!symbol) return;
        if (buyStockMeta) buyStockMeta.textContent = "Fetching live price...";
        try {
            const clean = symbol.replace(".NS", "").trim().toUpperCase();
            const res = await fetch(`/api/stock-live/${clean}`);
            const data = await res.json();
            if (data && data.price && data.price !== "--") {
                const numericPrice = parseFloat(data.price.replace(/,/g, ""));
                if (buyPriceInput && !isNaN(numericPrice)) {
                    buyPriceInput.value = numericPrice.toFixed(2);
                }
                if (buyStockMeta) buyStockMeta.textContent = `${data.company} • Live ₹${data.price} (${data.change > 0 ? "+" : ""}${data.change}%)`;
                updateBuyTotal();
            } else {
                if (buyStockMeta) buyStockMeta.textContent = "Live price not available. Please enter manually.";
            }
        } catch (e) {
            if (buyStockMeta) buyStockMeta.textContent = "Unable to fetch live price.";
        }
    }

    if (fetchBuyPriceBtn && buySymbolInput) {
        fetchBuyPriceBtn.addEventListener("click", () => {
            fetchPriceForBuy(buySymbolInput.value.trim());
        });
    }

    // Autocomplete stock search inside Buy modal
    let searchDebounce;
    if (buySymbolInput && buySuggestions) {
        buySymbolInput.addEventListener("input", () => {
            clearTimeout(searchDebounce);
            const query = buySymbolInput.value.trim();
            if (query.length < 2) {
                buySuggestions.innerHTML = "";
                return;
            }
            searchDebounce = setTimeout(async () => {
                try {
                    const res = await fetch(`/api/search-stocks?q=${encodeURIComponent(query)}`);
                    const stocks = await res.json();
                    if (!stocks || !stocks.length) {
                        buySuggestions.innerHTML = "";
                        return;
                    }
                    let html = '<div class="suggestion-list">';
                    stocks.slice(0, 5).forEach(s => {
                        html += `
                            <div class="suggestion-item" data-symbol="${s.symbol}">
                                <strong>${s.display_symbol}</strong>
                                <small class="text-muted">${s.name}</small>
                            </div>
                        `;
                    });
                    html += '</div>';
                    buySuggestions.innerHTML = html;

                    buySuggestions.querySelectorAll(".suggestion-item").forEach(item => {
                        item.addEventListener("click", () => {
                            buySymbolInput.value = item.dataset.symbol;
                            buySuggestions.innerHTML = "";
                            fetchPriceForBuy(item.dataset.symbol);
                        });
                    });
                } catch (e) {
                    buySuggestions.innerHTML = "";
                }
            }, 250);
        });
    }

    // Real-time calculation previews
    function updateBuyTotal() {
        if (!buyTotalPreview) return;
        const qty = parseFloat(buyQtyInput ? buyQtyInput.value : 0) || 0;
        const price = parseFloat(buyPriceInput ? buyPriceInput.value : 0) || 0;
        const fees = parseFloat(buyFeesInput ? buyFeesInput.value : 0) || 0;
        const total = (qty * price) + fees;
        buyTotalPreview.textContent = `₹${total.toLocaleString("en-IN", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
    }

    if (buyQtyInput) buyQtyInput.addEventListener("input", updateBuyTotal);
    if (buyPriceInput) buyPriceInput.addEventListener("input", updateBuyTotal);
    if (buyFeesInput) buyFeesInput.addEventListener("input", updateBuyTotal);

    function updateSellPnl() {
        if (!sellPnlPreview || !sellSymbolSelect) return;
        const selectedOpt = sellSymbolSelect.options[sellSymbolSelect.selectedIndex];
        if (!selectedOpt || !selectedOpt.value) {
            sellPnlPreview.textContent = "₹0.00";
            return;
        }

        const avgPrice = parseFloat(selectedOpt.dataset.avg) || 0;
        const qty = parseFloat(sellQtyInput ? sellQtyInput.value : 0) || 0;
        const price = parseFloat(sellPriceInput ? sellPriceInput.value : 0) || 0;
        const fees = parseFloat(sellFeesInput ? sellFeesInput.value : 0) || 0;

        const realized = (price - avgPrice) * qty - fees;
        const sign = realized >= 0 ? "+" : "";
        sellPnlPreview.textContent = `${sign}₹${realized.toLocaleString("en-IN", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
        sellPnlPreview.className = `form-control-plaintext font-monospace fw-bold ${realized >= 0 ? "text-success" : "text-danger"}`;
    }

    if (sellSymbolSelect) {
        sellSymbolSelect.addEventListener("change", () => {
            const selectedOpt = sellSymbolSelect.options[sellSymbolSelect.selectedIndex];
            if (selectedOpt && selectedOpt.value) {
                const maxQty = selectedOpt.dataset.qty || 0;
                const price = selectedOpt.dataset.price || 0;
                if (sellMaxQtyText) sellMaxQtyText.textContent = `Max: ${maxQty} shares`;
                if (sellQtyInput) sellQtyInput.max = maxQty;
                if (sellPriceInput) sellPriceInput.value = price;
            }
            updateSellPnl();
        });
    }
    if (sellQtyInput) sellQtyInput.addEventListener("input", updateSellPnl);
    if (sellPriceInput) sellPriceInput.addEventListener("input", updateSellPnl);
    if (sellFeesInput) sellFeesInput.addEventListener("input", updateSellPnl);

    // Form Submissions
    if (buyForm) {
        buyForm.addEventListener("submit", async (e) => {
            e.preventDefault();
            const submitBtn = document.getElementById("submitBuyBtn");
            if (submitBtn) { submitBtn.disabled = true; submitBtn.textContent = "Recording..."; }

            try {
                const res = await fetch("/api/portfolio/buy", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({
                        symbol: buySymbolInput.value.trim(),
                        quantity: parseFloat(buyQtyInput.value),
                        price: parseFloat(buyPriceInput.value),
                        fees: parseFloat(buyFeesInput.value || 0),
                        notes: document.getElementById("buyNotesInput").value.trim()
                    })
                });
                const data = await res.json();
                if (data.success) {
                    if (buyModal) buyModal.hide();
                    window.location.reload();
                } else {
                    alert(data.message || "Failed to record purchase.");
                }
            } catch (err) {
                alert("Network error. Please try again.");
            } finally {
                if (submitBtn) { submitBtn.disabled = false; submitBtn.textContent = "Confirm Purchase"; }
            }
        });
    }

    if (sellForm) {
        sellForm.addEventListener("submit", async (e) => {
            e.preventDefault();
            const submitBtn = document.getElementById("submitSellBtn");
            if (submitBtn) { submitBtn.disabled = true; submitBtn.textContent = "Processing..."; }

            try {
                const res = await fetch("/api/portfolio/sell", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({
                        symbol: sellSymbolSelect.value,
                        quantity: parseFloat(sellQtyInput.value),
                        price: parseFloat(sellPriceInput.value),
                        fees: parseFloat(sellFeesInput.value || 0),
                        notes: document.getElementById("sellNotesInput").value.trim()
                    })
                });
                const data = await res.json();
                if (data.success) {
                    if (sellModal) sellModal.hide();
                    window.location.reload();
                } else {
                    alert(data.message || "Failed to execute sale.");
                }
            } catch (err) {
                alert("Network error. Please try again.");
            } finally {
                if (submitBtn) { submitBtn.disabled = false; submitBtn.textContent = "Confirm Sell"; }
            }
        });
    }

    // AI Portfolio Diagnosis
    if (analyzeBtn && aiPanel && aiContent) {
        analyzeBtn.addEventListener("click", async () => {
            aiPanel.style.display = "block";
            aiContent.innerHTML = window.getTradingSpinnerHTML ? window.getTradingSpinnerHTML({
                size: 'md',
                text: 'Analyzing Portfolio Health',
                subtext: 'Evaluating asset allocation, sector concentration, and risk parameters...'
            }) : `
                <div class="ai-loading-state">
                    <p class="mt-2">Analyzing portfolio asset allocation, concentration risks, and performance...</p>
                </div>
            `;
            aiPanel.scrollIntoView({ behavior: "smooth" });

            try {
                const res = await fetch("/api/portfolio/analyze-ai", { method: "POST" });
                const data = await res.json();
                if (data && data.success) {
                    let strengthsHtml = (data.strengths || []).map(s => `<li>${s}</li>`).join("");
                    let risksHtml = (data.risks || []).map(r => `<li>${r}</li>`).join("");
                    let recsHtml = (data.recommendations || []).map(rc => `<li>${rc}</li>`).join("");

                    aiContent.innerHTML = `
                        <p class="lead" style="font-size: 0.95rem; color: #334155; line-height: 1.6;">${data.summary}</p>
                        <div class="ai-grid">
                            <div class="ai-box strengths">
                                <h5><i class="bi bi-check-circle-fill"></i> Core Strengths</h5>
                                <ul>${strengthsHtml || '<li>Good foundation established</li>'}</ul>
                            </div>
                            <div class="ai-box risks">
                                <h5><i class="bi bi-exclamation-triangle-fill"></i> Concentration &amp; Risks</h5>
                                <ul>${risksHtml || '<li>Market-wide fluctuations</li>'}</ul>
                            </div>
                            <div class="ai-box recs">
                                <h5><i class="bi bi-lightbulb-fill"></i> Rebalancing Recommendations</h5>
                                <ul>${recsHtml || '<li>Maintain quarterly reviews</li>'}</ul>
                            </div>
                        </div>
                    `;
                } else {
                    aiContent.innerHTML = `<div class="alert alert-warning">AI analysis is temporarily unavailable.</div>`;
                }
            } catch (e) {
                aiContent.innerHTML = `<div class="alert alert-danger">Error loading AI analysis. Please try again.</div>`;
            }
        });
    }

    if (closeAdvisorBtn && aiPanel) {
        closeAdvisorBtn.addEventListener("click", () => {
            aiPanel.style.display = "none";
        });
    }

    // Holdings Table Search Filter
    if (searchInput) {
        searchInput.addEventListener("input", function() {
            const query = this.value.toLowerCase().trim();
            document.querySelectorAll("#holdingsTable tbody tr").forEach(row => {
                const sym = row.dataset.symbol ? row.dataset.symbol.toLowerCase() : "";
                const name = row.dataset.name ? row.dataset.name.toLowerCase() : "";
                if (sym.includes(query) || name.includes(query)) {
                    row.style.display = "";
                } else {
                    row.style.display = "none";
                }
            });
        });
    }

    // Check URL parameters for direct actions (e.g. from analysis page)
    const urlParams = new URLSearchParams(window.location.search);
    if (urlParams.get("action") === "buy") {
        const targetSym = urlParams.get("symbol") || "";
        showBuyModal(targetSym);
    }
});
