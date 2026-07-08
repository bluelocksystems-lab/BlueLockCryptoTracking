// =============================================================================
// BlueLock Crypto Tracking V1.4 - Frontend JavaScript
// =============================================================================
// Handles all UI interactions, API calls, and rendering for the app.
// =============================================================================

"use strict";

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------
const API_BASE         = "";
const REFRESH_INTERVAL = 60 * 1000;

// ---------------------------------------------------------------------------
// State
// ---------------------------------------------------------------------------
let allCoinsData          = [];
let portfolioData         = [];
let portfolioFavorites    = [];
let activeFilter          = "all";
let activePortfolioFilter = "all";
let refreshTimer          = null;
let selectedCoins         = new Set();

// Live price cache for form preview (symbol -> price_usd)
let livePriceMap = {};

// ---------------------------------------------------------------------------
// Startup
// ---------------------------------------------------------------------------
document.addEventListener("DOMContentLoaded", () => {
  setupTabs();
  setupFilterButtons();
  setupPortfolioFilterButtons();
  loadAppVersion();
  refreshAll();
  startAutoRefresh();
});

// ---------------------------------------------------------------------------
// App Version (single source of truth: backend config.APP_VERSION)
// ---------------------------------------------------------------------------
async function loadAppVersion() {
  try {
    const health = await apiGet("/api/health");
    const label = "V" + health.version;
    const headerEl = document.getElementById("appVersionLabel");
    const footerEl = document.getElementById("appVersionLabelFooter");
    const aboutEl  = document.getElementById("appVersionLabelAbout");
    if (headerEl) headerEl.textContent = label;
    if (footerEl) footerEl.textContent = label;
    if (aboutEl)  aboutEl.textContent  = health.version;
    document.title = `${health.app} ${label}`;
  } catch (err) {
    // Fail silently — static fallback text already in the HTML covers this.
  }
}

// ---------------------------------------------------------------------------
// Tab Navigation
// ---------------------------------------------------------------------------
function setupTabs() {
  document.querySelectorAll(".nav-tab").forEach(btn => {
    btn.addEventListener("click", () => {
      const tab = btn.dataset.tab;
      document.querySelectorAll(".nav-tab").forEach(b => b.classList.remove("active"));
      document.querySelectorAll(".tab-content").forEach(s => s.classList.remove("active"));
      btn.classList.add("active");
      document.getElementById("tab-" + tab).classList.add("active");
      if (tab === "portfolio") loadPortfolio();
      if (tab === "watchlist") loadWatchlist();
    });
  });
}

// ---------------------------------------------------------------------------
// Filter Buttons (Prices tab)
// ---------------------------------------------------------------------------
function setupFilterButtons() {
  document.querySelectorAll(".filter-btn[data-filter]").forEach(btn => {
    btn.addEventListener("click", () => {
      document.querySelectorAll(".filter-btn[data-filter]").forEach(b => b.classList.remove("active"));
      btn.classList.add("active");
      activeFilter = btn.dataset.filter;
      renderPriceTable();
    });
  });
}

// ---------------------------------------------------------------------------
// Filter Buttons (Portfolio tab)
// ---------------------------------------------------------------------------
function setupPortfolioFilterButtons() {
  document.querySelectorAll(".filter-btn[data-portfolio-filter]").forEach(btn => {
    btn.addEventListener("click", () => {
      document.querySelectorAll(".filter-btn[data-portfolio-filter]").forEach(b => b.classList.remove("active"));
      btn.classList.add("active");
      activePortfolioFilter = btn.dataset.portfolioFilter;
      renderPortfolioTable();
    });
  });
}

// ---------------------------------------------------------------------------
// Populate Coin Select Dropdowns
// Driven dynamically from the /api/prices response so the frontend stays in
// sync with backend/config.py automatically — no manual list to maintain.
// ---------------------------------------------------------------------------
function populateCoinSelects(coins) {
  if (!coins || coins.length === 0) return;

  // Group by category for optgroups
  const groupOrder = ["Major", "Privacy", "Stablecoin"];
  const groups = { Major: [], Privacy: [], Stablecoin: [] };
  coins.forEach(c => {
    const cat = c.category || "Other";
    if (!groups[cat]) groups[cat] = [];
    groups[cat].push(c);
  });

  function buildOptions(includeBlank) {
    let html = includeBlank ? `<option value="">Select a coin...</option>` : "";
    for (const cat of groupOrder) {
      const list = groups[cat] || [];
      if (list.length === 0) continue;
      html += `<optgroup label="${cat}">`;
      list.forEach(c => {
        html += `<option value="${escHtml(c.symbol)}">${escHtml(c.symbol)} — ${escHtml(c.name)}</option>`;
      });
      html += `</optgroup>`;
    }
    return html;
  }

  const portfolio  = document.getElementById("portfolioCoin");
  const calc       = document.getElementById("calcCoin");
  const watchlist  = document.getElementById("watchlistCoin");
  if (portfolio)  portfolio.innerHTML  = buildOptions(true);
  if (calc)       calc.innerHTML       = buildOptions(false);
  if (watchlist)  watchlist.innerHTML  = buildOptions(true);

  // About page coin list
  const aboutList = document.getElementById("aboutCoinList");
  if (aboutList) {
    aboutList.innerHTML = coins.map(c =>
      `<div class="about-coin-item">
        <span class="about-coin-symbol">${escHtml(c.symbol)}</span>
        <span class="about-coin-name">${escHtml(c.name)}</span>
        <span class="category-badge ${escHtml(c.category)}">${escHtml(c.category)}</span>
      </div>`
    ).join("");
  }
}

// ---------------------------------------------------------------------------
// Data Loading
// ---------------------------------------------------------------------------
async function refreshAll() {
  await Promise.all([loadPrices(), loadPortfolio(), loadWatchlist()]);
}

async function loadPrices() {
  try {
    const data = await apiGet("/api/prices");
    allCoinsData       = data.coins || [];
    portfolioFavorites = allCoinsData.filter(c => c.is_favorite).map(c => c.symbol);
    populateCoinSelects(allCoinsData);

    // Build live price map for form preview
    livePriceMap = {};
    allCoinsData.forEach(c => { livePriceMap[c.symbol] = c.price_usd; });

    updateStatusIndicator(data.api_status, data.is_stale);
    updateLastUpdated(formatLocalTime(data.last_updated), data.is_stale);
    renderPriceTable();
    renderDashboardFavorites();

    // Refresh preview if form is open
    updatePurchasePreview();
  } catch (err) {
    updateStatusIndicator("OFFLINE");
    console.error("loadPrices failed:", err);
  }
}

async function loadPortfolio() {
  try {
    const data    = await apiGet("/api/portfolio");
    portfolioData = data.coins || [];
    renderPortfolioTable();
    renderPortfolioSummary(data.summary, data.top_gainer, data.top_loser);
    renderDashboardPortfolio(data.summary);
    renderDashboardGainerLoser(data.top_gainer, data.top_loser);
    updateStatusIndicator(data.api_status, data.is_stale);
    updateLastUpdated(formatLocalTime(data.last_updated), data.is_stale);
  } catch (err) {
    console.error("loadPortfolio failed:", err);
  }
}

function startAutoRefresh() {
  if (refreshTimer) clearInterval(refreshTimer);
  // Only refresh when the tab is visible to avoid unnecessary API calls
  refreshTimer = setInterval(() => {
    if (!document.hidden) refreshAll();
  }, REFRESH_INTERVAL);
}

// ---------------------------------------------------------------------------
// Format UTC string to local time
// ---------------------------------------------------------------------------
function formatLocalTime(utcStr) {
  if (!utcStr) return "—";
  try {
    // e.g. "2026-06-01 14:30 UTC"
    const d = new Date(utcStr.replace(" UTC", "Z"));
    if (isNaN(d)) return utcStr;
    return d.toLocaleDateString(undefined, { month: "2-digit", day: "2-digit", year: "numeric" }) +
      " " + d.toLocaleTimeString(undefined, { hour: "2-digit", minute: "2-digit" });
  } catch {
    return utcStr;
  }
}

// ---------------------------------------------------------------------------
// Render: Price Table
// ---------------------------------------------------------------------------
function renderPriceTable() {
  const container = document.getElementById("priceTableContainer");
  if (!container) return;

  if (allCoinsData.length === 0) {
    container.innerHTML = `<div class="loading-state"><div class="spinner"></div><span>Loading prices...</span></div>`;
    return;
  }

  const search = (document.getElementById("searchInput")?.value || "").toLowerCase().trim();
  const favSymbols = new Set(portfolioFavorites);

  let filtered = allCoinsData.filter(coin => {
    if (activeFilter === "favorites" && !coin.is_favorite) return false;
    if (activeFilter !== "all" && activeFilter !== "favorites" && coin.category !== activeFilter) return false;
    if (search && !coin.symbol.toLowerCase().includes(search) && !coin.name.toLowerCase().includes(search)) return false;
    return true;
  });

  if (filtered.length === 0) {
    container.innerHTML = `<div class="empty-state" style="padding:2rem;">No coins match your filter.</div>`;
    return;
  }

  const table = document.createElement("table");
  table.className = "price-table";
  table.innerHTML = `
    <thead>
      <tr>
        <th></th>
        <th>Symbol</th>
        <th>Name</th>
        <th class="col-category">Category</th>
        <th>Price (USD)</th>
        <th class="col-updated">Last Updated</th>
        <th class="col-actions">Actions</th>
      </tr>
    </thead>
    <tbody id="priceTableBody"></tbody>
  `;

  const tbody = table.querySelector("#priceTableBody");
  filtered.forEach(coin => {
    const tr = document.createElement("tr");
    if (coin.is_favorite) tr.classList.add("is-favorite");

    const price = coin.price_usd != null
      ? "$" + formatPrice(coin.price_usd)
      : '<span class="price-unavailable">Unavailable</span>';

    tr.innerHTML = `
      <td>
        <button
          class="btn-star ${coin.is_favorite ? 'active' : ''}"
          title="${coin.is_favorite ? 'Remove from favorites' : 'Add to favorites'}"
          onclick="toggleFavorite('${escHtml(coin.symbol)}', ${!coin.is_favorite})"
        >★</button>
      </td>
      <td><span class="col-symbol">${escHtml(coin.symbol)}</span></td>
      <td class="col-name">${escHtml(coin.name)}</td>
      <td class="col-category">
        <span class="category-badge ${escHtml(coin.category)}">${escHtml(coin.category)}</span>
      </td>
      <td class="col-price">${price}</td>
      <td class="col-updated">${escHtml(coin.last_updated || "—")}</td>
      <td class="col-actions">
        <button
          class="btn btn-secondary"
          style="font-size:0.75rem;padding:0.3rem 0.7rem;"
          onclick="quickCalc('${escHtml(coin.symbol)}')"
        >Calc</button>
      </td>
    `;
    tbody.appendChild(tr);
  });

  container.innerHTML = "";
  container.appendChild(table);
}

// ---------------------------------------------------------------------------
// Render: Portfolio Table
// ---------------------------------------------------------------------------
function renderPortfolioTable() {
  const container = document.getElementById("portfolioTableContainer");
  if (!container) return;

  const search = (document.getElementById("portfolioSearchInput")?.value || "").toLowerCase().trim();
  const favSymbols = new Set(portfolioFavorites);

  let coins = portfolioData.filter(coin => {
    if (activePortfolioFilter === "favorites" && !favSymbols.has(coin.symbol)) return false;
    if (activePortfolioFilter !== "all" && activePortfolioFilter !== "favorites" && coin.category !== activePortfolioFilter) return false;
    if (search && !coin.symbol.toLowerCase().includes(search) && !coin.name.toLowerCase().includes(search)) return false;
    return true;
  });

  if (coins.length === 0) {
    container.innerHTML = `<div class="empty-state" style="padding:2rem;">
      ${portfolioData.length === 0
        ? "No holdings yet. Add your first purchase above."
        : "No coins match your filter."}
    </div>`;
    return;
  }

  const rows = coins.map(coin => {
    const priceStr  = coin.current_price !== null && coin.current_price !== undefined
      ? "$" + formatPrice(coin.current_price) : `<span class="price-unavailable">Price Unavailable</span>`;
    const valueStr  = coin.current_value !== null ? formatUSD(coin.current_value) : "—";
    const costStr   = formatUSD(coin.total_cost);
    const avgStr    = "$" + formatPrice(coin.average_cost);
    const amountStr = formatAmount(coin.total_amount);

    let pnlStr  = "—";
    let roiStr  = "—";
    if (coin.profit_loss !== null) {
      const pnlClass = coin.profit_loss >= 0 ? "positive" : "negative";
      const sign     = coin.profit_loss >= 0 ? "+" : "";
      pnlStr = `<span class="${pnlClass}">${sign}${formatUSD(coin.profit_loss)}</span>`;
    }
    if (coin.roi_percent !== null) {
      const roiClass = coin.roi_percent >= 0 ? "positive" : "negative";
      const sign     = coin.roi_percent >= 0 ? "+" : "";
      roiStr = `<span class="${roiClass}">${sign}${formatROI(coin.roi_percent)}</span>`;
    }

    const checked = selectedCoins.has(coin.symbol) ? "checked" : "";

    return `<tr class="portfolio-row clickable-row" onclick="openCoinDetail('${coin.symbol}')">
      <td onclick="event.stopPropagation()">
        <input type="checkbox" class="row-checkbox" ${checked}
               onchange="toggleCoinSelection('${coin.symbol}', this.checked)">
      </td>
      <td>
        <span class="coin-symbol">${coin.symbol}</span>
        <span class="category-badge cat-${(coin.category||"").toLowerCase()}">${coin.category||""}</span>
      </td>
      <td>${coin.name}</td>
      <td>${amountStr}</td>
      <td>${avgStr}</td>
      <td class="price-cell">${priceStr}</td>
      <td>${costStr}</td>
      <td>${valueStr}</td>
      <td>${pnlStr}</td>
      <td>${roiStr}</td>
      <td onclick="event.stopPropagation()">
        <button class="btn-icon-sm" onclick="openCoinDetail('${coin.symbol}')" title="View Details">👁</button>
        <button class="btn-icon-sm" onclick="prefillEditForm('${coin.symbol}')" title="Add Purchase">➕</button>
        <button class="btn-icon-sm btn-danger" onclick="openDeleteCoinDialog('${coin.symbol}')" title="Delete Holdings">🗑</button>
      </td>
    </tr>`;
  }).join("");

  // Drop selections for coins no longer present in the list (e.g. after a delete)
  const visibleSymbols = new Set(coins.map(c => c.symbol));
  for (const sym of Array.from(selectedCoins)) {
    if (!visibleSymbols.has(sym)) selectedCoins.delete(sym);
  }
  updateDeleteSelectedButton();

  const allChecked = coins.length > 0 && coins.every(c => selectedCoins.has(c.symbol));

  container.innerHTML = `
    <div class="table-scroll">
    <table class="data-table portfolio-table">
      <thead>
        <tr>
          <th><input type="checkbox" class="select-all-checkbox" ${allChecked ? "checked" : ""}
                     onchange="toggleSelectAllCoins(this.checked)"></th>
          <th>Symbol</th>
          <th>Name</th>
          <th>Amount</th>
          <th>Avg Cost</th>
          <th>Price</th>
          <th>Cost Basis</th>
          <th>Value</th>
          <th>P&amp;L</th>
          <th>ROI</th>
          <th></th>
        </tr>
      </thead>
      <tbody>${rows}</tbody>
    </table>
    </div>`;
}

// ---------------------------------------------------------------------------
// Portfolio: Multi-select & Delete
// ---------------------------------------------------------------------------
function toggleCoinSelection(symbol, isChecked) {
  if (isChecked) selectedCoins.add(symbol);
  else selectedCoins.delete(symbol);
  updateDeleteSelectedButton();
}

function toggleSelectAllCoins(isChecked) {
  if (isChecked) {
    portfolioData.forEach(c => selectedCoins.add(c.symbol));
  } else {
    selectedCoins.clear();
  }
  renderPortfolioTable();
}

function updateDeleteSelectedButton() {
  const btn = document.getElementById("deleteSelectedBtn");
  const countEl = document.getElementById("selectedCount");
  if (!btn || !countEl) return;
  countEl.textContent = selectedCoins.size;
  btn.style.display = selectedCoins.size > 0 ? "inline-flex" : "none";
}

let pendingDeleteSymbol = null;

function openDeleteCoinDialog(symbol) {
  const coin = portfolioData.find(c => c.symbol === symbol);
  const count = coin ? (coin.entry_count || 0) : 0;

  pendingDeleteSymbol = symbol;
  setEl("deleteCoinSymbol", symbol);
  setEl("deleteCoinEntryCount", count);
  setEl("deleteCoinEntryWord", count === 1 ? "entry" : "entries");
  document.getElementById("deleteCoinModal").classList.add("active");
}

function closeDeleteCoinModal(event) {
  if (event && event.target !== document.getElementById("deleteCoinModal")) return;
  document.getElementById("deleteCoinModal").classList.remove("active");
  pendingDeleteSymbol = null;
}

async function confirmDeleteAllForCoin() {
  const symbol = pendingDeleteSymbol;
  if (!symbol) return;

  try {
    await apiDelete(`/api/portfolio/symbol/${symbol}`);
    selectedCoins.delete(symbol);
    showToast(`${symbol} removed.`, "success");
    closeDeleteCoinModal();
    await loadPortfolio();
  } catch (err) {
    showToast("Network error while removing asset.", "error");
  }
}

function manageCoinIndividually() {
  const symbol = pendingDeleteSymbol;
  closeDeleteCoinModal();
  if (symbol) openCoinDetail(symbol);
}

async function deleteSelectedCoins() {
  const symbols = Array.from(selectedCoins);
  if (symbols.length === 0) return;

  const label = symbols.length === 1 ? symbols[0] : `${symbols.length} assets`;
  if (!confirm(`Remove ${label} and ALL their purchase entries from your portfolio? This cannot be undone.`)) return;

  let failedCount = 0;
  for (const symbol of symbols) {
    try {
      await apiDelete(`/api/portfolio/symbol/${symbol}`);
    } catch (err) {
      failedCount++;
    }
  }

  selectedCoins.clear();

  if (failedCount === 0) {
    showToast(`${label} removed.`, "success");
  } else {
    showToast(`Removed with ${failedCount} error(s). Check console.`, "error");
  }

  await loadPortfolio();
}

// ---------------------------------------------------------------------------
// Render: Portfolio Summary Card
// ---------------------------------------------------------------------------
function renderPortfolioSummary(summary, topGainer, topLoser) {
  if (!summary) return;

  const card = document.getElementById("portfolioSummaryCard");
  if (portfolioData.length > 0 && card) card.style.display = "grid";

  setEl("summaryTotalValue", formatUSD(summary.total_value));
  setEl("summaryCostBasis",  formatUSD(summary.total_cost));

  if (summary.total_profit_loss !== null) {
    const sign = summary.total_profit_loss >= 0 ? "+" : "";
    const cls  = summary.total_profit_loss >= 0 ? "positive" : "negative";
    setEl("summaryPnl", `<span class="${cls}">${sign}${formatUSD(summary.total_profit_loss)}</span>`);
  } else {
    setEl("summaryPnl", "—");
  }

  if (summary.overall_roi !== null) {
    const sign = summary.overall_roi >= 0 ? "+" : "";
    const cls  = summary.overall_roi >= 0 ? "positive" : "negative";
    setEl("summaryRoi", `<span class="${cls}">${sign}${formatROI(summary.overall_roi)}</span>`);
  } else {
    setEl("summaryRoi", "—");
  }
}

// ---------------------------------------------------------------------------
// Render: Dashboard
// ---------------------------------------------------------------------------
function renderDashboardFavorites() {
  const container = document.getElementById("dashFavorites");
  if (!container) return;

  const favCoins = allCoinsData.filter(c => c.is_favorite);
  if (favCoins.length === 0) {
    container.innerHTML = `<div class="empty-state">Star coins in the Prices tab to see them here.</div>`;
    return;
  }

  container.innerHTML = favCoins.map(coin => {
    const priceStr = coin.price_usd !== null ? "$" + formatPrice(coin.price_usd) : "N/A";
    return `<div class="coin-card">
      <div class="coin-card-symbol">${coin.symbol}</div>
      <div class="coin-card-name">${coin.name}</div>
      <div class="coin-card-price">${priceStr}</div>
    </div>`;
  }).join("");
}

function renderDashboardPortfolio(summary) {
  const container = document.getElementById("dashPortfolio");
  if (!container) return;

  if (portfolioData.length === 0) {
    container.innerHTML = `<div class="empty-state">Add holdings in the Portfolio tab to see them here.</div>`;
    setEl("dashTotalValue", "—");
    setEl("dashCostBasis",  "—");
    setEl("dashPnl",        "—");
    setEl("dashRoi",        "—");
    const g = document.getElementById("gainerLoserGrid");
    if (g) g.style.display = "none";
    return;
  }

  container.innerHTML = portfolioData.map(coin => {
    const priceStr = coin.current_price !== null ? "$" + formatPrice(coin.current_price) : "N/A";
    const valueStr = coin.current_value !== null ? formatUSD(coin.current_value) : "N/A";
    let pnlHtml = "";
    if (coin.profit_loss !== null) {
      const cls  = coin.profit_loss >= 0 ? "positive" : "negative";
      const sign = coin.profit_loss >= 0 ? "+" : "";
      pnlHtml = `<div class="coin-card-pnl ${cls}">${sign}${formatUSD(coin.profit_loss)}</div>`;
    }
    return `<div class="coin-card">
      <div class="coin-card-symbol">${coin.symbol}</div>
      <div class="coin-card-name">${coin.name}</div>
      <div class="coin-card-price">${priceStr}</div>
      <div class="coin-card-value">${valueStr}</div>
      ${pnlHtml}
    </div>`;
  }).join("");

  if (summary) {
    setEl("dashTotalValue", formatUSD(summary.total_value));
    setEl("dashCostBasis",  formatUSD(summary.total_cost));

    if (summary.total_profit_loss !== null) {
      const sign = summary.total_profit_loss >= 0 ? "+" : "";
      const cls  = summary.total_profit_loss >= 0 ? "positive" : "negative";
      document.getElementById("dashPnl").innerHTML = `<span class="${cls}">${sign}${formatUSD(summary.total_profit_loss)}</span>`;
    }
    if (summary.overall_roi !== null) {
      const sign = summary.overall_roi >= 0 ? "+" : "";
      const cls  = summary.overall_roi >= 0 ? "positive" : "negative";
      document.getElementById("dashRoi").innerHTML = `<span class="${cls}">${sign}${formatROI(summary.overall_roi)}</span>`;
    }
  }
}

function renderDashboardGainerLoser(topGainer, topLoser) {
  const grid = document.getElementById("gainerLoserGrid");
  if (!grid) return;

  if (!topGainer && !topLoser) {
    grid.style.display = "none";
    return;
  }

  grid.style.display = "grid";

  if (topGainer) {
    setEl("dashTopGainer", topGainer.symbol || "—");
    const sign = (topGainer.roi_percent || 0) >= 0 ? "+" : "";
    setEl("dashTopGainerRoi", topGainer.roi_percent !== null
      ? `<span class="positive">${sign}${formatROI(topGainer.roi_percent)}</span>` : "—");
  }
  if (topLoser) {
    setEl("dashTopLoser", topLoser.symbol || "—");
    const sign = (topLoser.roi_percent || 0) >= 0 ? "+" : "";
    const cls  = (topLoser.roi_percent || 0) >= 0 ? "positive" : "negative";
    setEl("dashTopLoserRoi", topLoser.roi_percent !== null
      ? `<span class="${cls}">${sign}${formatROI(topLoser.roi_percent)}</span>` : "—");
  }
}

// ---------------------------------------------------------------------------
// Live Purchase Preview
// ---------------------------------------------------------------------------
function onFormChange() {
  updatePurchasePreview();
}

function updatePurchasePreview() {
  const symbol    = document.getElementById("portfolioCoin")?.value;
  const amountStr = document.getElementById("portfolioAmount")?.value;
  const priceStr  = document.getElementById("portfolioPurchasePrice")?.value;

  const previewPanel = document.getElementById("purchasePreview");
  if (!previewPanel) return;

  const amount        = parseFloat(amountStr);
  const purchasePrice = parseFloat(priceStr);
  const hasAmount     = !isNaN(amount) && amount > 0;
  const hasPrice      = !isNaN(purchasePrice) && purchasePrice > 0;

  // Show preview once at least coin + one field is filled
  if (!symbol || (!hasAmount && !hasPrice)) {
    previewPanel.style.display = "none";
    return;
  }

  previewPanel.style.display = "block";

  // Cost Basis
  if (hasAmount && hasPrice) {
    const costBasis = amount * purchasePrice;
    setEl("previewCostBasis", formatUSD(costBasis));
    setEl("previewCostBasisFormula",
      `<span class="formula">${formatAmount(amount)} × $${formatPrice(purchasePrice)}</span>`);
  } else {
    setEl("previewCostBasis", "—");
    setEl("previewCostBasisFormula", "");
  }

  // Current Market Price (from live cache)
  const currentPrice = livePriceMap[symbol];
  if (currentPrice !== undefined && currentPrice !== null) {
    setEl("previewCurrentPrice", "$" + formatPrice(currentPrice));
  } else {
    setEl("previewCurrentPrice", '<span class="price-unavailable">Price Unavailable</span>');
  }

  // Current Value, P&L, ROI
  if (hasAmount && currentPrice !== undefined && currentPrice !== null) {
    const currentValue = amount * currentPrice;
    setEl("previewCurrentValue", formatUSD(currentValue));
    setEl("previewCurrentValueFormula",
      `<span class="formula">${formatAmount(amount)} × $${formatPrice(currentPrice)}</span>`);

    if (hasPrice) {
      const costBasis = amount * purchasePrice;
      const pnl       = currentValue - costBasis;
      const sign      = pnl >= 0 ? "+" : "";
      const pnlCls    = pnl >= 0 ? "positive" : "negative";
      setEl("previewPnl", `<span class="${pnlCls}">${sign}${formatUSD(pnl)}</span>`);

      if (costBasis > 0) {
        const roi    = ((currentValue - costBasis) / costBasis) * 100;
        const roiSign = roi >= 0 ? "+" : "";
        const roiCls  = roi >= 0 ? "positive" : "negative";
        setEl("previewRoi", `<span class="${roiCls}">${roiSign}${formatROI(roi)}</span>`);
      } else {
        setEl("previewRoi", "—");
      }
    } else {
      setEl("previewPnl", "—");
      setEl("previewRoi", "—");
    }
  } else {
    setEl("previewCurrentValue", "—");
    setEl("previewCurrentValueFormula", "");
    setEl("previewPnl", "—");
    setEl("previewRoi", "—");
  }
}

// ---------------------------------------------------------------------------
// Coin Detail Modal
// ---------------------------------------------------------------------------
async function openCoinDetail(symbol) {
  const modal = document.getElementById("coinDetailModal");
  modal.classList.add("active");

  setEl("modalSymbol",       symbol);
  setEl("modalName",         "Loading...");
  setEl("modalCurrentPrice", "—");
  setEl("modalAmount",       "—");
  setEl("modalAvgCost",      "—");
  setEl("modalCostBasis",    "—");
  setEl("modalCurrentValue", "—");
  setEl("modalPnl",          "—");
  setEl("modalRoi",          "—");
  setEl("modalEntryCount",   "—");
  document.getElementById("modalPurchaseHistory").innerHTML =
    `<div class="loading-state"><div class="spinner"></div><span>Loading...</span></div>`;

  try {
    const res  = await fetch(`${API_BASE}/api/portfolio/${symbol}`);
    if (!res.ok) throw new Error("Not found");
    const data = await res.json();

    setEl("modalName",         data.name);
    setEl("modalCurrentPrice", data.current_price !== null ? "$" + formatPrice(data.current_price) : "Price Unavailable");
    setEl("modalAmount",       formatAmount(data.total_amount) + " " + symbol);
    setEl("modalAvgCost",      "$" + formatPrice(data.average_cost));
    setEl("modalCostBasis",    formatUSD(data.total_cost));
    setEl("modalCurrentValue", data.current_value !== null ? formatUSD(data.current_value) : "—");
    setEl("modalEntryCount",   data.entry_count + " purchase(s)");

    if (data.profit_loss !== null) {
      const sign = data.profit_loss >= 0 ? "+" : "";
      const cls  = data.profit_loss >= 0 ? "positive" : "negative";
      document.getElementById("modalPnl").innerHTML = `<span class="${cls}">${sign}${formatUSD(data.profit_loss)}</span>`;
    }
    if (data.roi_percent !== null) {
      const sign = data.roi_percent >= 0 ? "+" : "";
      const cls  = data.roi_percent >= 0 ? "positive" : "negative";
      document.getElementById("modalRoi").innerHTML = `<span class="${cls}">${sign}${formatROI(data.roi_percent)}</span>`;
    }

    if (!data.purchase_history || data.purchase_history.length === 0) {
      document.getElementById("modalPurchaseHistory").innerHTML =
        `<div class="empty-state">No purchase entries found.</div>`;
    } else {
      const histRows = data.purchase_history.map(e => {
        const dateStr = e.purchase_date || e.created_at?.split("T")[0] || "—";
        return `<tr>
          <td>${dateStr}</td>
          <td>${formatAmount(e.amount)}</td>
          <td>$${formatPrice(e.purchase_price)}</td>
          <td>${formatUSD(e.cost)}</td>
          <td onclick="event.stopPropagation()">
            <button class="btn-icon-sm danger" onclick="deleteEntry(${e.id}, '${symbol}')" title="Delete this entry">🗑</button>
            <button class="btn-icon-sm" onclick="editEntry(${e.id}, '${symbol}', ${e.amount}, ${e.purchase_price}, '${e.purchase_date||''}')" title="Edit this entry">✏</button>
          </td>
        </tr>`;
      }).join("");

      document.getElementById("modalPurchaseHistory").innerHTML = `
        <table class="data-table history-table">
          <thead>
            <tr><th>Date</th><th>Amount</th><th>Buy Price</th><th>Cost Basis</th><th></th></tr>
          </thead>
          <tbody>${histRows}</tbody>
        </table>`;
    }
  } catch (err) {
    document.getElementById("modalPurchaseHistory").innerHTML =
      `<div class="error-state">Failed to load details.</div>`;
  }
}

function closeCoinDetailModal(event) {
  if (event && event.target !== document.getElementById("coinDetailModal")) return;
  document.getElementById("coinDetailModal").classList.remove("active");
}

// ---------------------------------------------------------------------------
// Portfolio Entry CRUD
// ---------------------------------------------------------------------------
async function savePortfolioEntry() {
  const symbol        = document.getElementById("portfolioCoin").value;
  const amount        = parseFloat(document.getElementById("portfolioAmount").value);
  const purchasePrice = parseFloat(document.getElementById("portfolioPurchasePrice").value);
  const date          = document.getElementById("portfolioDate").value || "";
  const editId        = document.getElementById("entryEditId").value;

  clearFormMsg("portfolioFormMsg");

  // Friendly validation
  if (!symbol)
    return showFormMsg("portfolioFormMsg", "Please select a coin.", "error");
  if (isNaN(amount) || amount <= 0)
    return showFormMsg("portfolioFormMsg", "Please enter the amount of coins you own.", "error");
  if (isNaN(purchasePrice) || purchasePrice <= 0)
    return showFormMsg("portfolioFormMsg", "Please enter the purchase price per coin.", "error");

  const btn = document.getElementById("entrySubmitBtn");
  if (btn) { btn.disabled = true; btn.textContent = "Saving..."; }

  try {
    if (editId) {
      await apiPut(`/api/portfolio/${editId}`, { amount, purchase_price: purchasePrice, purchase_date: date });
    } else {
      await apiPost("/api/portfolio", { symbol, amount, purchase_price: purchasePrice, purchase_date: date });
    }

    showToast(editId ? `Entry updated for ${symbol}!` : `Purchase added for ${symbol}!`, "success");
    cancelEditEntry();
    await loadPortfolio();

  } catch (err) {
    showFormMsg("portfolioFormMsg", err.message || "Error saving entry.", "error");
  } finally {
    if (btn) {
      btn.disabled    = false;
      btn.textContent = document.getElementById("entryEditId").value ? "Update Purchase" : "Add Purchase";
    }
  }
}

function prefillEditForm(symbol) {
  cancelEditEntry();
  document.getElementById("portfolioCoin").value = symbol;
  document.getElementById("portfolioAmount").focus();
  onFormChange();
  document.getElementById("entryFormTitle").scrollIntoView({ behavior: "smooth", block: "start" });
}

function editEntry(id, symbol, amount, purchasePrice, purchaseDate) {
  closeCoinDetailModal();

  document.getElementById("entryEditId").value                  = id;
  document.getElementById("portfolioCoin").value                = symbol;
  document.getElementById("portfolioAmount").value              = amount;
  document.getElementById("portfolioPurchasePrice").value       = purchasePrice;
  document.getElementById("portfolioDate").value                = purchaseDate || "";
  document.getElementById("entryFormTitle").textContent         = `✏ Edit Purchase #${id}`;
  document.getElementById("entrySubmitBtn").textContent         = "Update Purchase";
  document.getElementById("entryCancelBtn").style.display       = "inline-flex";

  document.querySelectorAll(".nav-tab").forEach(b => b.classList.remove("active"));
  document.querySelectorAll(".tab-content").forEach(s => s.classList.remove("active"));
  document.querySelector('.nav-tab[data-tab="portfolio"]').classList.add("active");
  document.getElementById("tab-portfolio").classList.add("active");
  onFormChange();
  document.getElementById("entryFormTitle").scrollIntoView({ behavior: "smooth" });
}

function cancelEditEntry() {
  document.getElementById("entryEditId").value                  = "";
  document.getElementById("portfolioCoin").selectedIndex        = 0;
  document.getElementById("portfolioAmount").value              = "";
  document.getElementById("portfolioPurchasePrice").value       = "";
  document.getElementById("portfolioDate").value                = "";
  document.getElementById("entryFormTitle").textContent         = "➕ Add Purchase";
  document.getElementById("entrySubmitBtn").textContent         = "Add Purchase";
  document.getElementById("entryCancelBtn").style.display       = "none";
  clearFormMsg("portfolioFormMsg");
  const previewPanel = document.getElementById("purchasePreview");
  if (previewPanel) previewPanel.style.display = "none";
}

async function deleteEntry(id, symbol) {
  if (!confirm(`Delete this purchase entry for ${symbol}? This cannot be undone.`)) return;

  try {
    await apiDelete(`/api/portfolio/${id}`);
    showToast("Entry deleted.", "success");
    await loadPortfolio();
    const remaining = portfolioData.find(c => c.symbol === symbol);
    if (remaining) {
      openCoinDetail(symbol);
    } else {
      document.getElementById("coinDetailModal").classList.remove("active");
    }
  } catch (err) {
    showToast("Network error.", "error");
  }
}

// ---------------------------------------------------------------------------
// Export Portfolio CSV
// ---------------------------------------------------------------------------
function exportPortfolioCSV() {
  if (portfolioData.length === 0) {
    showToast("Nothing to export. Add some holdings first.", "error");
    return;
  }
  const link = document.createElement("a");
  link.href  = `${API_BASE}/api/portfolio/export/csv`;
  link.click();
  showToast("CSV export started.", "success");
}

// ---------------------------------------------------------------------------
// Favorites
// ---------------------------------------------------------------------------
async function toggleFavorite(symbol, addFavorite) {
  try {
    if (addFavorite) {
      await apiPost("/api/favorites", { symbol });
      showToast("★ " + symbol + " added to favorites", "success");
    } else {
      await apiDelete("/api/favorites/" + encodeURIComponent(symbol));
      showToast(symbol + " removed from favorites", "info");
    }
    await loadPrices();
  } catch (err) {
    showToast("Failed to update favorites: " + err.message, "error");
  }
}

// ---------------------------------------------------------------------------
// Watchlist
// ---------------------------------------------------------------------------
async function loadWatchlist() {
  const container = document.getElementById("watchlistContainer");

  try {
    const data = await apiGet("/api/watchlist");
    const items = data.watchlist || [];
    if (container) renderWatchlist(items);
    renderDashboardWatchlist(items);

    // Watchlist has its own "Refresh" button independent of Dashboard/Prices/
    // Portfolio, so keep the shared status indicator in sync here too.
    // /api/health is the canonical source for api_status + is_stale together.
    try {
      const health = await apiGet("/api/health");
      updateStatusIndicator(health.api_status, health.is_stale);
    } catch { /* status indicator just won't update this cycle - non-fatal */ }
  } catch (err) {
    if (container) {
      container.innerHTML = `<div class="empty-state" style="padding:2rem;">
        Could not load watchlist. ${escHtml(err.message || "")}
      </div>`;
    }
  }
}

function renderDashboardWatchlist(items) {
  const container = document.getElementById("dashWatchlist");
  if (!container) return;

  if (!items || items.length === 0) {
    container.innerHTML = `<div class="empty-state">Add coins in the Watchlist tab to see them here.</div>`;
    return;
  }

  container.innerHTML = items.map(item => {
    const priceStr = item.price_usd !== null && item.price_usd !== undefined
      ? "$" + formatPrice(item.price_usd)
      : "N/A";
    const noteHtml = item.notes
      ? `<div class="coin-card-note" title="${escHtml(item.notes)}">${escHtml(item.notes)}</div>`
      : "";
    return `<div class="coin-card">
      <div class="coin-card-symbol">${escHtml(item.symbol)}</div>
      <div class="coin-card-name">${escHtml(item.name)}</div>
      <div class="coin-card-price">${priceStr}</div>
      ${noteHtml}
    </div>`;
  }).join("");
}

function renderWatchlist(items) {
  const container = document.getElementById("watchlistContainer");
  if (!container) return;

  if (items.length === 0) {
    container.innerHTML = `<div class="empty-state" style="padding: 2rem;">
      Not watching anything yet. Add a coin above.
    </div>`;
    return;
  }

  const rows = items.map(item => {
    const priceStr = item.price_usd !== null && item.price_usd !== undefined
      ? "$" + formatPrice(item.price_usd)
      : `<span class="price-unavailable">Price Unavailable</span>`;
    const noteStr = item.notes ? escHtml(item.notes) : `<span class="text-muted">No note</span>`;

    return `<tr>
      <td>
        <span class="coin-symbol">${escHtml(item.symbol)}</span>
        <span class="category-badge cat-${(item.category||"").toLowerCase()}">${escHtml(item.category||"")}</span>
      </td>
      <td>${escHtml(item.name)}</td>
      <td class="price-cell">${priceStr}</td>
      <td class="watchlist-note-cell" id="watchNote-${item.symbol}" ondblclick="editWatchlistNote('${item.symbol}')" title="Double-click to edit">
        ${noteStr}
      </td>
      <td>
        <button class="btn-icon-sm" onclick="quickCalc('${item.symbol}')" title="Calculate value">🧮</button>
        <button class="btn-icon-sm btn-danger" onclick="removeFromWatchlist('${item.symbol}')" title="Remove from watchlist">🗑</button>
      </td>
    </tr>`;
  }).join("");

  container.innerHTML = `
    <div class="table-scroll">
    <table class="data-table watchlist-table">
      <thead>
        <tr>
          <th>Symbol</th>
          <th>Name</th>
          <th>Price</th>
          <th>Note</th>
          <th></th>
        </tr>
      </thead>
      <tbody>${rows}</tbody>
    </table>
    </div>`;
}

async function addToWatchlist() {
  const select = document.getElementById("watchlistCoin");
  const noteInput = document.getElementById("watchlistNote");
  const symbol = select?.value;
  const notes = (noteInput?.value || "").trim();

  clearFormMsg("watchlistFormMsg");

  if (!symbol) {
    return showFormMsg("watchlistFormMsg", "Please select a coin.", "error");
  }

  try {
    await apiPost("/api/watchlist", { symbol, notes });
    showToast(`☆ ${symbol} added to watchlist.`, "success");
    if (select) select.selectedIndex = 0;
    if (noteInput) noteInput.value = "";
    await loadWatchlist();
  } catch (err) {
    showFormMsg("watchlistFormMsg", err.message || "Error adding to watchlist.", "error");
  }
}

async function removeFromWatchlist(symbol) {
  if (!confirm(`Stop watching ${symbol}?`)) return;
  try {
    await apiDelete(`/api/watchlist/${encodeURIComponent(symbol)}`);
    showToast(`${symbol} removed from watchlist.`, "info");
    await loadWatchlist();
  } catch (err) {
    showToast("Failed to remove: " + err.message, "error");
  }
}

function editWatchlistNote(symbol) {
  const cell = document.getElementById(`watchNote-${symbol}`);
  if (!cell || cell.querySelector("input")) return;

  const currentText = cell.textContent.trim() === "No note" ? "" : cell.textContent.trim();

  cell.innerHTML = `<input type="text" class="inline-edit-input" maxlength="280" value="${escHtml(currentText)}"
    onkeydown="if(event.key==='Enter') this.blur(); if(event.key==='Escape') this.dataset.cancel='1', this.blur();"
    onblur="saveWatchlistNote('${symbol}', this)" />`;
  const input = cell.querySelector("input");
  input.focus();
  input.select();
}

async function saveWatchlistNote(symbol, inputEl) {
  if (inputEl.dataset.cancel === "1") {
    await loadWatchlist();
    return;
  }
  const notes = inputEl.value.trim();
  try {
    await apiPut(`/api/watchlist/${encodeURIComponent(symbol)}`, { notes });
    showToast("Note updated.", "success");
  } catch (err) {
    showToast("Failed to save note: " + err.message, "error");
  }
  await loadWatchlist();
}

function quickCalc(symbol) {
  const select = document.getElementById("calcCoin");
  if (select) select.value = symbol;
  document.querySelectorAll(".nav-tab").forEach(b => b.classList.remove("active"));
  document.querySelectorAll(".tab-content").forEach(s => s.classList.remove("active"));
  document.querySelector('.nav-tab[data-tab="prices"]').classList.add("active");
  document.getElementById("tab-prices").classList.add("active");
  runCalculator();
  setTimeout(() => {
    const calcEl = document.querySelector(".calculator");
    if (calcEl) calcEl.scrollIntoView({ behavior: "smooth", block: "center" });
  }, 100);
}

// ---------------------------------------------------------------------------
// Price Calculator
// ---------------------------------------------------------------------------
async function runCalculator() {
  const symbol = document.getElementById("calcCoin")?.value;
  const amount = parseFloat(document.getElementById("calcAmount")?.value);
  const result = document.getElementById("calcResult");
  if (!result) return;

  if (!symbol || isNaN(amount) || amount <= 0) {
    result.innerHTML = `<span class="calc-placeholder">Enter a coin and amount above to calculate value.</span>`;
    return;
  }

  try {
    const data = await apiPost("/api/calculate", { symbol, amount });
    result.innerHTML = `
      <div class="calc-output">
        <div class="calc-line">
          <span class="calc-key">Coin</span>
          <span class="calc-val">${escHtml(data.symbol)} — ${escHtml(data.name)}</span>
        </div>
        <div class="calc-line">
          <span class="calc-key">Current Price</span>
          <span class="calc-val">$${escHtml(formatPrice(data.price_usd))}</span>
        </div>
        <div class="calc-line">
          <span class="calc-key">Amount</span>
          <span class="calc-val">${escHtml(String(data.amount))}</span>
        </div>
        <div class="calc-line">
          <span class="calc-key">Total Value</span>
          <span class="calc-total">$${escHtml(formatNumber(data.total_usd))}</span>
        </div>
      </div>
    `;
  } catch (err) {
    result.innerHTML = `<span style="color:var(--accent-red)">Error: could not reach server.</span>`;
  }
}

// ---------------------------------------------------------------------------
// Search & Filter
// ---------------------------------------------------------------------------
function filterCoins()    { renderPriceTable(); }
function clearSearch()    { document.getElementById("searchInput").value = ""; renderPriceTable(); }
function filterPortfolio(){ renderPortfolioTable(); }
function clearPortfolioSearch() { document.getElementById("portfolioSearchInput").value = ""; renderPortfolioTable(); }

// ---------------------------------------------------------------------------
// Status Indicator
// ---------------------------------------------------------------------------
function updateStatusIndicator(status, isStale = false) {
  const dot      = document.getElementById("statusDot");
  const label    = document.getElementById("statusLabel");
  const dashStatus = document.getElementById("dashApiStatus");

  if (!dot || !label) return;

  // Stale takes visual priority over ONLINE: the cache is old enough that
  // what's on screen may not reflect the live market, even though the last
  // successful fetch technically succeeded.
  if (status === "ONLINE" && isStale) {
    dot.className     = "status-dot stale";
    label.textContent = "API Online (cached)";
    if (dashStatus) {
      dashStatus.textContent = "CACHED";
      dashStatus.className   = "stat-value api-status-value stale";
    }
  } else if (status === "ONLINE") {
    dot.className     = "status-dot online";
    label.textContent = "API Online";
    if (dashStatus) {
      dashStatus.textContent = "ONLINE";
      dashStatus.className   = "stat-value api-status-value online";
    }
  } else if (status === "OFFLINE") {
    dot.className     = "status-dot offline";
    label.textContent = "API Offline";
    if (dashStatus) {
      dashStatus.textContent = "OFFLINE";
      dashStatus.className   = "stat-value api-status-value offline";
    }
  } else {
    dot.className     = "status-dot";
    label.textContent = "Connecting...";
    if (dashStatus) {
      dashStatus.textContent = "—";
      dashStatus.className   = "stat-value api-status-value";
    }
  }
}

function updateLastUpdated(ts, isStale = false) {
  const el1 = document.getElementById("footerLastUpdated");
  const el2 = document.getElementById("dashLastUpdated");
  const suffix = isStale ? " (stale)" : "";
  if (el1) el1.textContent = ts ? ts + suffix : "—";
  if (el2) el2.textContent = ts ? ts + suffix : "—";
}

// ---------------------------------------------------------------------------
// Toast Notifications
// ---------------------------------------------------------------------------
function showToast(message, type = "info") {
  const container = document.getElementById("toastContainer");
  if (!container) return;
  const icons = { success: "✓", error: "✕", info: "ℹ" };
  const toast = document.createElement("div");
  toast.className = `toast ${type}`;
  toast.innerHTML = `<span>${icons[type] || "•"}</span><span>${escHtml(message)}</span>`;
  container.appendChild(toast);
  setTimeout(() => toast.remove(), 3500);
}

// ---------------------------------------------------------------------------
// Form Message Helpers
// ---------------------------------------------------------------------------
function showFormMsg(id, message, type = "info") {
  const el = document.getElementById(id);
  if (!el) return;
  el.textContent = message;
  el.className   = `form-msg form-msg-${type}`;
}

function clearFormMsg(id) {
  const el = document.getElementById(id);
  if (!el) return;
  el.textContent = "";
  el.className   = "form-msg";
}

// ---------------------------------------------------------------------------
// Formatting Helpers
// ---------------------------------------------------------------------------

/** Format a price with appropriate decimals for any magnitude. */
function formatPrice(price) {
  if (price === null || price === undefined) return "—";
  const n = Number(price);
  if (isNaN(n)) return "—";
  if (n === 0)           return "0.00";
  if (n >= 1000)         return n.toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
  if (n >= 1)            return n.toFixed(4);
  if (n >= 0.0001)       return n.toFixed(6);
  if (n >= 0.00000001)   return n.toFixed(10);
  return n.toExponential(4);
}

/** Format a USD total (2dp with commas). */
function formatUSD(value) {
  if (value === null || value === undefined) return "—";
  const n = Number(value);
  if (isNaN(n)) return "—";
  return "$" + n.toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

/** Format a coin amount. */
function formatAmount(amount) {
  if (amount === null || amount === undefined) return "—";
  const n = Number(amount);
  if (isNaN(n)) return "—";
  if (n >= 1) return n.toLocaleString("en-US", { maximumFractionDigits: 4 });
  return n.toFixed(8).replace(/\.?0+$/, "");
}

/** Format ROI percentage — shows up to 2 decimals, but handles huge numbers. */
function formatROI(roi) {
  if (roi === null || roi === undefined) return "—";
  const n = Number(roi);
  if (isNaN(n)) return "—";
  if (Math.abs(n) >= 10000) return n.toLocaleString("en-US", { maximumFractionDigits: 0 }) + "%";
  if (Math.abs(n) >= 100)   return n.toFixed(1) + "%";
  return n.toFixed(2) + "%";
}

/** Set innerHTML of element by ID. */
function setEl(id, content) {
  const el = document.getElementById(id);
  if (el) el.innerHTML = content;
}

function formatNumber(num) {
  if (num == null || isNaN(num)) return "N/A";
  return num.toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

/** Escape HTML to prevent XSS. */
function escHtml(str) {
  if (str == null) return "";
  return String(str)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#39;");
}

// ---------------------------------------------------------------------------
// API Helpers
// ---------------------------------------------------------------------------
async function apiGet(endpoint) {
  const res = await fetch(API_BASE + endpoint);
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || "HTTP " + res.status);
  }
  return res.json();
}

async function apiPost(endpoint, body) {
  const res = await fetch(API_BASE + endpoint, {
    method:  "POST",
    headers: { "Content-Type": "application/json" },
    body:    JSON.stringify(body),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || "HTTP " + res.status);
  }
  return res.json();
}

async function apiPut(endpoint, body) {
  const res = await fetch(API_BASE + endpoint, {
    method:  "PUT",
    headers: { "Content-Type": "application/json" },
    body:    JSON.stringify(body),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || "HTTP " + res.status);
  }
  return res.json();
}

async function apiDelete(endpoint) {
  const res = await fetch(API_BASE + endpoint, { method: "DELETE" });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || "HTTP " + res.status);
  }
  return res.json();
}
