document.addEventListener("DOMContentLoaded", () => {

    window.addEventListener("load", () => {

        const graph =
            document.querySelector(".js-plotly-plot");

        if (graph) {

            Plotly.relayout(graph, {
                height: 390
            });

        }

    });

    const marketChart = document.getElementById("market-chart");
    const rangeButtons = document.querySelectorAll(".market-range-button");
    const rangeDescription = document.getElementById("marketRangeDescription");

    function runChartScripts(container) {
        container.querySelectorAll("script").forEach((script) => {
            const executableScript = document.createElement("script");

            Array.from(script.attributes).forEach((attribute) => {
                executableScript.setAttribute(attribute.name, attribute.value);
            });

            executableScript.text = script.textContent;
            script.replaceWith(executableScript);
        });
    }

    async function loadMarketChart(button) {
        if (!marketChart || !button || button.classList.contains("loading")) {
            return;
        }

        const period = button.dataset.period;
        const label = button.dataset.label;

        rangeButtons.forEach((rangeButton) => {
            rangeButton.classList.remove("active");
            rangeButton.disabled = true;
        });

        button.classList.add("active", "loading");
        marketChart.classList.add("is-loading");

        if (window.getTradingSpinnerHTML) {
            marketChart.innerHTML = window.getTradingSpinnerHTML({
                size: 'md',
                text: `Loading ${label || 'Live'} Market Chart`,
                subtext: 'Syncing NIFTY 50 and SENSEX data...'
            });
        }

        try {
            const response = await fetch(
                `/api/dashboard-market-chart?period=${encodeURIComponent(period)}`
            );

            const data = await response.json();

            if (!response.ok || !data.success) {
                throw new Error(data.message || "Chart unavailable");
            }

            marketChart.innerHTML = data.chart_html;
            runChartScripts(marketChart);

            if (rangeDescription) {
                rangeDescription.textContent =
                    `NIFTY 50 and SENSEX performance over the last ${label}`;
            }
        } catch (error) {
            marketChart.innerHTML = `
                <div class="chart-placeholder">
                    <i class="bi bi-wifi-off"></i>
                    <h5>Market chart unavailable</h5>
                    <p>Unable to load ${label} market data. Please try again.</p>
                </div>
            `;
        } finally {
            button.classList.remove("loading");
            marketChart.classList.remove("is-loading");

            rangeButtons.forEach((rangeButton) => {
                rangeButton.disabled = false;
            });
        }
    }

    rangeButtons.forEach((button) => {
        button.addEventListener("click", () => loadMarketChart(button));
    });

    const activeMarketRange = document.querySelector(".market-range-button.active");

    if (
        marketChart &&
        activeMarketRange &&
        marketChart.querySelector(".chart-loading-state")
    ) {
        loadMarketChart(activeMarketRange);
    }

    const askAiForm = document.getElementById("askAiForm");
    const askAiQuestion = document.getElementById("askAiQuestion");
    const askAiAnswer = document.getElementById("askAiAnswer");
    const askAiToggle = document.getElementById("askAiToggle");
    const askAiWidget = document.getElementById("askAiWidget");
    const askAiClose = document.getElementById("askAiClose");
    function addChatMessage(message, type = "bot", state = "idle") {
        if (!askAiAnswer) {
            return;
        }

        const chatMessage = document.createElement("div");
        chatMessage.className = `chat-message ${type} ${state}`;

        if (state === "loading" && window.getTradingSpinnerHTML) {
            chatMessage.innerHTML = window.getTradingSpinnerHTML({
                size: 'sm',
                text: 'GetStockIQ is analyzing market context...',
                centered: false
            });
            askAiAnswer.append(chatMessage);
            askAiAnswer.scrollTop = askAiAnswer.scrollHeight;
            return chatMessage;
        }

        const icon =
            state === "error"
                ? "bi-exclamation-triangle"
                : "bi-lightning-charge";

        if (type === "bot") {
            const iconElement = document.createElement("i");
            iconElement.className = `bi ${icon}`;
            chatMessage.append(iconElement);
        }

        const messageElement = document.createElement("span");
        messageElement.textContent = type === "bot"
            ? cleanAiResponse(message)
            : message;
        chatMessage.append(messageElement);
        askAiAnswer.append(chatMessage);
        askAiAnswer.scrollTop = askAiAnswer.scrollHeight;
        return chatMessage;
    }

    function cleanAiResponse(message) {
        return String(message || "")
            .replace(/\*{1,3}/g, "")
            .replace(/#{1,6}\s*/g, "")
            .replace(/[\t ]{2,}/g, " ")
            .replace(/\n{3,}/g, "\n\n")
            .trim();
    }

    function setChatOpen(isOpen) {
        if (!askAiWidget || !askAiToggle) return;
        askAiWidget.classList.toggle("is-open", isOpen);
        askAiWidget.setAttribute("aria-hidden", String(!isOpen));
        askAiToggle.setAttribute("aria-expanded", String(isOpen));
        if (isOpen && askAiQuestion) askAiQuestion.focus();
    }

    function resetChat() {
        if (!askAiAnswer) return;
        askAiAnswer.replaceChildren();
        addChatMessage(
            "Hello! Ask me about a stock, NIFTY 50, SENSEX, market trends, or investment risks.",
            "bot"
        );
    }

    async function askGetStockIQ(question) {
        if (!question || !askAiForm) {
            return;
        }

        const submitButton = askAiForm.querySelector("button[type='submit']");

        if (!submitButton) {
            return;
        }

        submitButton.disabled = true;
        addChatMessage(question, "user");
        const loadingMessage = addChatMessage(
            "GetStockIQ is checking the latest market context...",
            "bot",
            "loading"
        );

        try {
            const response = await fetch("/api/ask-ai", {
                method: "POST",
                headers: {
                    "Content-Type": "application/json"
                },
                body: JSON.stringify({ question })
            });

            const data = await response.json();

            if (!data.answer) {
                throw new Error(data.message || "AI answer unavailable");
            }

            loadingMessage.remove();
            addChatMessage(data.answer, "bot", data.success ? "ready" : "error");
        } catch (error) {
            loadingMessage.remove();
            addChatMessage("The AI assistant is unavailable right now. Please try again shortly.", "bot", "error");
        } finally {
            submitButton.disabled = false;
        }
    }

    if (askAiForm && askAiQuestion && askAiAnswer) {
        askAiForm.addEventListener("submit", (event) => {
            event.preventDefault();
            const question = askAiQuestion.value.trim();

            if (!question) {
                return;
            }

            askAiQuestion.value = "";
            askGetStockIQ(question);
        });
    }

    if (askAiToggle) {
        askAiToggle.addEventListener("click", () => {
            const shouldOpen = !askAiWidget.classList.contains("is-open");
            if (shouldOpen) resetChat();
            setChatOpen(shouldOpen);
        });
    }

    if (askAiClose) {
        askAiClose.addEventListener("click", () => setChatOpen(false));
    }

    const chart = document.getElementById("allocationChart");

    if (chart) {

        const legend = document.getElementById("portfolioLegend");
        const bestStock = document.getElementById("bestStock");
        const bestGain = document.getElementById("bestGain");
        const worstStock = document.getElementById("worstStock");
        const worstLoss = document.getElementById("worstLoss");

        if (!legend) {
            return;
        }

        const sectors = [

            ["Technology", 45, "#2563eb"],

            ["Finance", 35, "#16a34a"],

            ["Energy", 20, "#f59e0b"]

        ];

        new Chart(chart, {

            type: "doughnut",

            data: {

                labels: sectors.map(s => s[0]),

                datasets: [{

                    data: sectors.map(s => s[1]),

                    backgroundColor: sectors.map(s => s[2]),

                    borderWidth: 0

                }]

            },

            options: {

                responsive: true,

                maintainAspectRatio: false,

                cutout: "70%",

                plugins: {

                    legend: { display: false }

                }

            }

        });
        if (bestStock) bestStock.innerText = "TCS";
        if (bestGain) bestGain.innerText = "+4.82%";
        if (worstStock) worstStock.innerText = "RELIANCE";
        if (worstLoss) worstLoss.innerText = "-1.43%";

        legend.innerHTML = "";

        sectors.forEach(item => {

            legend.innerHTML += `

<div class="legend-item">

<div class="legend-left">

<span class="legend-color"
style="background:${item[2]}"></span>

<strong>${item[0]}</strong>

</div>

<span>${item[1]}%</span>

</div>

`;

        });

    }
});
