// App Logic: Scan, Dán link của bạn, và AI Copilot (Gemini 3.8 Flash).
import { api } from "./api.js";
import { $, esc, time } from "./format.js";
import { renderStats, renderRows, renderRuns, resetRenderCaches } from "./views.js";

const AUTO_REFRESH_MS = 300000;
let cachedItems = [];

async function refresh({ force = false } = {}) {
  if (force) resetRenderCaches();

  try {
    const health = await api("/api/health");
    $("health").textContent = `${health.provider ? 'Zen Studio' : 'Chưa kết nối'} · ${health.snapshots} snapshots`;
    $("budget").textContent = `${health.items} SKU`;
  } catch (error) {
    $("health").textContent = "Backend mất kết nối";
    return;
  }

  const [data, runs] = await Promise.all([api("/api/items"), api("/api/runs")]);
  cachedItems = data.items || [];
  renderStats(cachedItems);
  renderRows(cachedItems);
  renderRuns(runs.runs || []);

  const latest = cachedItems.map((i) => i.captured_at).sort().pop();
  $("lastScan").textContent = latest ? "Đồng bộ lần cuối: " + time(latest) : "";
}

// Lưu link shop của bạn khi thay đổi
window.savePricing = async function (itemId) {
  const lInput = $(`input-link-${itemId}`);
  const my_link = lInput && lInput.value ? lInput.value.trim() : null;

  try {
    await api(`/api/items/${itemId}/my-pricing`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ my_link }),
    });
    const it = cachedItems.find((x) => x.item_id === itemId);
    if (it) {
      it.my_link = my_link;
    }
  } catch (e) {
    console.error("Lỗi lưu link:", e);
  }
};

// Kích hoạt AI Copilot với Gemini 3.8 Flash: Tự động cào link của bạn nếu chưa cào, rồi phân tích
window.triggerAiCopilot = async function (itemId) {
  const item = cachedItems.find((x) => x.item_id === itemId);
  if (!item) return;

  const lInput = $(`input-link-${itemId}`);
  const my_link = lInput && lInput.value ? lInput.value.trim() : item.my_link;

  if (!my_link) {
    alert("Vui lòng dán link Shopee sản phẩm của shop bạn vào ô trước!");
    if (lInput) lInput.focus();
    return;
  }

  const btn = $(`btn-copilot-${itemId}`);
  if (btn) {
    btn.disabled = true;
    btn.innerHTML = '<span class="spin"></span>';
  }

  // Mở modal AI
  const modal = $("aiModal");
  modal.classList.add("open");
  $("modalProductName").textContent = `AI Copilot: ${item.name || item.item_id}`;
  $("modalProductMeta").textContent = `Đối thủ: ${item.shop_name || 'Shop đối thủ'} · Giá cuối: $${item.final_price || item.promo_price}`;

  $("modalAiBody").innerHTML = `
    <div class="ai-loading">
      <span class="spin"></span>
      <span>Đang cào dữ liệu từ link của bạn & Gemini 3.8 Flash đang đối chiếu chiến thuật...</span>
    </div>
  `;

  try {
    // 1. Tự động cào link của bạn nếu chưa có hoặc vừa dán mới
    let myPrice = item.my_price;
    if (!myPrice || item.my_link !== my_link) {
      try {
        const fetchRes = await api(`/api/items/${itemId}/fetch-my-product`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ item_id: itemId, my_link }),
        });
        myPrice = fetchRes.my_final_price;
      } catch (err) {
        console.warn("Lỗi cào link của bạn:", err);
      }
    }

    // 2. Gọi AI phân tích chiến thuật
    const res = await api("/api/analyze-pricing", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        item_id: itemId,
        my_link: my_link,
        my_price: myPrice,
      }),
    });

    // Render kết quả phân tích AI
    renderAiAnalysis(res, item, myPrice || (item.final_price || item.promo_price) + res.diff);
    await refresh({ force: true });
  } catch (err) {
    $("modalAiBody").innerHTML = `
      <div style="color:#f87171; padding:20px; text-align:center">
        ❌ Phân tích thất bại: ${esc(err.message)}
      </div>
    `;
  } finally {
    if (btn) {
      btn.disabled = false;
      btn.innerHTML = "<span>⚡ AI Phân Tích</span>";
    }
  }
};

function renderAiAnalysis(data, item, my_price) {
  const badgeColors = {
    warning: "#fbbf24",
    danger: "#f87171",
    success: "#34d399",
    info: "#38bdf8",
  };
  const color = badgeColors[data.badge] || "#d97706";

  $("modalAiBody").innerHTML = `
    <!-- Summary Header -->
    <div class="ai-summary-box" style="border-left-color: ${color}">
      <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:8px">
        <span class="badge" style="background:${color}22; color:${color}; font-size:12px; font-weight:700">
          ${data.badge.toUpperCase()}
        </span>
        <span style="font-size:11px; color:#94a3b8; font-family:var(--font-mono)">
          Powered by ${esc(data.generated_by || "Gemini 3.8 Flash")}
        </span>
      </div>
      <div class="ai-summary-text">${esc(data.summary)}</div>
      ${data.margin_info ? `<div class="ai-margin-text">📊 ${esc(data.margin_info)}</div>` : ''}
    </div>

    <!-- So sánh số học trực quan -->
    <div style="display:grid; grid-template-columns: repeat(3, 1fr); gap:10px; text-align:center">
      <div style="background:#131720; border:1px solid #283142; border-radius:10px; padding:12px">
        <div style="font-size:11.5px; color:#94a3b8">Giá cuối Đối thủ</div>
        <div style="font-size:18px; font-weight:800; color:#38bdf8">$${item.final_price || item.promo_price}</div>
      </div>
      <div style="background:#131720; border:1px solid #4338ca; border-radius:10px; padding:12px">
        <div style="font-size:11.5px; color:#c4b5fd">Giá cuối của Bạn</div>
        <div style="font-size:18px; font-weight:800; color:#fff">$${my_price ? my_price.toFixed(2) : '—'}</div>
      </div>
      <div style="background:#131720; border:1px solid #283142; border-radius:10px; padding:12px">
        <div style="font-size:11.5px; color:#94a3b8">Chênh lệch ($)</div>
        <div style="font-size:18px; font-weight:800; color:${data.diff > 0 ? '#f87171' : '#34d399'}">
          ${data.diff > 0 ? '+' : ''}${data.diff} (${data.diff_pct}%)
        </div>
      </div>
    </div>

    <!-- Tactics List -->
    <div style="display:flex; flex-direction:column; gap:12px; margin-top:6px">
      <div style="font-size:13px; font-weight:700; color:#fff">💡 Đề Xuất Chiến Thuật Từ Gemini 3.8:</div>
      ${(data.tactics || []).map((t, idx) => `
        <div class="tactic-item">
          <div class="tactic-action">
            <span>🎯 ${idx + 1}. ${esc(t.action)}</span>
          </div>
          <div class="tactic-reason">${esc(t.reason)}</div>
          <div class="tactic-suggestion">
            <b>👉 Khuyến nghị thực thi:</b> ${esc(t.suggestion)}
          </div>
        </div>
      `).join("")}
    </div>
  `;
}

// Scanner Logic
async function scan(text) {
  const button = $("btnScan");
  button.disabled = true;
  const started = Date.now();
  $("scanStatus").innerHTML = '<span class="spin"></span> Đang cào dữ liệu Shopee qua Zen Studio (~4-6s/SKU)...';
  $("scanErrors").innerHTML = "";

  try {
    const result = await api("/api/scan", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ text }),
    });
    const seconds = ((Date.now() - started) / 1000).toFixed(1);
    $("scanStatus").innerHTML = `✅ Hoàn thành Run #${result.run_id} · ${result.ok} SKU OK · ${seconds}s`;
    if (result.errors?.length) {
      $("scanErrors").innerHTML = result.errors
        .map((e) => `<div style="background:#451a1a; color:#fca5a5; padding:8px 12px; border-radius:6px; margin-top:6px; font-size:12px">${esc(e.input)}: ${esc(e.error)}</div>`).join("");
    }
    await refresh({ force: true });
  } catch (error) {
    $("scanStatus").innerHTML = `<span style="color:#f87171">✗ ${esc(error.message)}</span>`;
  } finally {
    button.disabled = false;
  }
}

// Modal closing
$("btnAiModalClose").onclick = () => $("aiModal").classList.remove("open");
$("aiModalBackdrop").onclick = () => $("aiModal").classList.remove("open");
$("btnClose").onclick = () => $("drawer").classList.remove("open");

// Action Buttons
$("btnScan").onclick = () => {
  const text = $("paste").value.trim();
  if (!text) {
    alert("Vui lòng dán link Shopee vào ô nhập.");
    return;
  }
  scan(text);
};

$("btnRescan").onclick = async () => {
  const button = $("btnRescan");
  button.disabled = true;
  $("scanStatus").innerHTML = '<span class="spin"></span> Đang quét lại toàn bộ danh sách...';
  try {
    await api("/api/scan/all", { method: "POST" });
    await refresh({ force: true });
    $("scanStatus").innerHTML = '✅ Đã cập nhật giá mới nhất.';
  } catch (e) {
    $("scanStatus").innerHTML = `<span style="color:#f87171">✗ ${esc(e.message)}</span>`;
  } finally {
    button.disabled = false;
  }
};

$("btnRefresh").onclick = async () => {
  const btn = $("btnRefresh");
  btn.disabled = true;
  try {
    await refresh({ force: true });
  } finally {
    btn.disabled = false;
  }
};

let autoTimer = null;
$("chkAuto").onchange = (event) => {
  if (autoTimer) {
    clearInterval(autoTimer);
    autoTimer = null;
  }
  if (event.target.checked) autoTimer = setInterval(() => refresh(), AUTO_REFRESH_MS);
};

refresh();
