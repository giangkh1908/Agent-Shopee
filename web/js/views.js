// Render các vùng giao diện: Table, Modal Copilot, Drawer.
import { api } from "./api.js";
import { $, esc, money, pct, time, voucherCell, statCard, sparkline } from "./format.js";

let lastStatsSignature = null;
let lastRowsSignature = null;
let lastRunsSignature = null;

export function resetRenderCaches() {
  lastStatsSignature = null;
  lastRowsSignature = null;
  lastRunsSignature = null;
}

export function renderStats(items) {
  const counts = {
    flash: items.filter((i) => i.is_flash_sale).length,
    voucher: items.filter((i) => i.shop_voucher || i.platform_voucher).length,
    drops: items.filter((i) => (i.delta?.final_change_pct ?? 0) < 0).length,
    ups: items.filter((i) => (i.delta?.final_change_pct ?? 0) > 0).length,
    outOfStock: items.filter((i) => i.stock === 0).length,
  };
  const signature = [items.length, ...Object.values(counts)].join("|");
  if (signature === lastStatsSignature) return;
  lastStatsSignature = signature;

  $("stats").innerHTML = `
    <div class="stat-card">
      <span class="val">${items.length}</span>
      <span class="lbl">SKU Đang Theo Dõi</span>
    </div>
    <div class="stat-card">
      <span class="val" style="color: #fbbf24">${counts.flash}</span>
      <span class="lbl">⚡ Đang Flash Sale</span>
    </div>
    <div class="stat-card">
      <span class="val" style="color: #38bdf8">${counts.voucher}</span>
      <span class="lbl">🎟️ Có Voucher Áp Dụng</span>
    </div>
    <div class="stat-card">
      <span class="val" style="color: #34d399">${counts.drops}</span>
      <span class="lbl">📉 Giá Cuối Giảm (vs Trước)</span>
    </div>
    <div class="stat-card">
      <span class="val" style="color: #f87171">${counts.ups}</span>
      <span class="lbl">📈 Giá Cuối Tăng (vs Trước)</span>
    </div>
    <div class="stat-card">
      <span class="val" style="color: #ef4444">${counts.outOfStock}</span>
      <span class="lbl">⚠️ Hết Hàng (Stock 0)</span>
    </div>
  `;
}

export function renderRows(items) {
  const signature = items
    .map((i) => [i.item_id, i.final_price, i.stock, i.my_link, i.captured_at, i.is_flash_sale].join(":"))
    .join("|");
  if (signature === lastRowsSignature) return;
  lastRowsSignature = signature;

  const body = $("rows");
  if (!items.length) {
    body.innerHTML = '<tr><td colspan="12" class="empty-state">Chưa có sản phẩm nào. Dán link ở trên và bấm "Quét Đối Thủ".</td></tr>';
    return;
  }

  body.innerHTML = items.map((item) => {
    const delta = item.delta || {};
    const cls = delta.final_change_pct > 0 ? "text-accent-red" : delta.final_change_pct < 0 ? "text-accent-green" : "text-muted";
    const change = delta.is_new
      ? '<span class="badge" style="background:#1e293b; color:#94a3b8">mới</span>'
      : (delta.final_change_pct === null || delta.final_change_pct === undefined)
        ? '<span class="text-muted">—</span>'
        : `<span class="${cls}" style="font-weight:600">${pct(delta.final_change_pct)}</span>`;

    const myLinkVal = item.my_link || "";

    return `<tr data-item="${item.item_id}">
      <td>
        ${item.image ? `<img class="prod-thumb" src="${esc(item.image)}" loading="lazy" alt="">` : ""}
      </td>
      <td>
        <div class="prod-cell">
          <div class="prod-meta">
            <span class="prod-name" title="${esc(item.name || item.item_id)}">${esc(item.name || item.item_id)}</span>
            <div class="prod-id">
              ID: ${item.item_id}
              ${item.url ? `<a class="prod-link" href="${esc(item.url)}" target="_blank" rel="noreferrer">Mở link ↗</a>` : ""}
            </div>
          </div>
        </div>
      </td>
      <td><span style="font-weight:500">${esc(item.shop_name || "—")}</span></td>
      <td>
        <div>${item.price_before_discount ? `<span class="price-strike">${money(item.price_before_discount)}</span>` : '<span class="text-muted">—</span>'}</div>
        <div style="font-size:11.5px; color:var(--text-dim)">${item.price_min !== item.price_max ? `${money(item.price_min)}–${money(item.price_max)}` : ""}</div>
      </td>
      <td>
        <span class="price-promo">${money(item.promo_price, item.currency)}</span>
        ${item.discount_percent ? `<div style="font-size:11px; color:#f87171">−${item.discount_percent}%</div>` : ""}
      </td>
      <td>${voucherCell(item.shop_voucher)}</td>
      <td>${voucherCell(item.platform_voucher)}</td>
      <td>
        <div class="price-final-comp">${money(item.final_price, item.currency)}</div>
        <span class="badge ${item.card_match ? 'badge-exact' : 'badge-warning'}" style="font-size:10px">
          ${item.card_match ? "✓ Khớp card" : esc(item.final_confidence || "tính")}
        </span>
      </td>

      <!-- CỘT DÁN LINK SHOP CỦA BẠN (GỘP GỌN GÀNG) -->
      <td style="border-left: 1px solid #334155; border-right: 1px solid #334155; background: #161a24" onclick="event.stopPropagation()">
        <div style="display:flex; flex-direction:column; gap:4px">
          <input type="text" class="input-copilot" style="width:100%; font-size:11.5px" 
                 id="input-link-${item.item_id}"
                 placeholder="Dán link sản phẩm của bạn..." 
                 value="${esc(myLinkVal)}"
                 onchange="window.savePricing(${item.item_id})">
          ${item.my_price ? `
            <div style="font-size:11px; color:#34d399; display:flex; justify-content:space-between">
              <span>Đã cào giá bạn: <b>$${item.my_price}</b></span>
              ${item.url && item.my_link ? `<a href="${esc(item.my_link)}" target="_blank" style="color:#38bdf8; text-decoration:none">Xem ↗</a>` : ''}
            </div>
          ` : `
            <div style="font-size:11px; color:#94a3b8">Bấm AI Phân Tích để tự cào & đối chiếu</div>
          `}
        </div>
      </td>

      <!-- NÚT AI COPILOT ĐỀ XUẤT CHIẾN THUẬT -->
      <td class="text-center" onclick="event.stopPropagation()">
        <button class="btn btn-ai-copilot" id="btn-copilot-${item.item_id}" onclick="window.triggerAiCopilot(${item.item_id})">
          <span>⚡ AI Phân Tích</span>
        </button>
      </td>

      <td>
        <span style="font-weight:600; color:${item.stock < 50 ? '#f87171' : 'var(--text-main)'}">
          ${item.stock ?? "—"}
        </span>
      </td>
      <td>
        <div style="font-weight:600">⭐ ${item.rating ? item.rating.toFixed(2) : "—"}</div>
        <div style="font-size:11px; color:var(--text-dim)">(${Number(item.rating_count || 0).toLocaleString()} đánh giá)</div>
      </td>
    </tr>`;
  }).join("");

  // Bấm vào hàng để mở Drawer chi tiết (trừ khi bấm nút/input)
  for (const row of body.querySelectorAll("tr[data-item]")) {
    row.addEventListener("click", (event) => {
      if (event.target.closest("input") || event.target.closest("button") || event.target.closest("a")) return;
      const itemId = Number(row.dataset.item);
      openDetail(itemId, items.find((i) => i.item_id === itemId));
    });
  }
}

export function renderRuns(runs) {
  const signature = JSON.stringify(runs.map((r) => [r.id, r.status, r.ok_count, r.failed_count, r.usage_usd]));
  if (signature === lastRunsSignature) return;
  lastRunsSignature = signature;

  $("runs").innerHTML = runs.map((run) => `<tr>
      <td>#${run.id}</td>
      <td>${time(run.started_at)}</td>
      <td><code>${esc(run.kind)}</code></td>
      <td>${run.url_count}</td>
      <td style="color:#34d399; font-weight:600">${run.ok_count}</td>
      <td style="color:#f87171">${run.failed_count}</td>
      <td>
        <span class="badge ${run.status === 'done' ? 'badge-exact' : 'badge-danger'}">
          ${esc(run.status)}
        </span>
      </td>
      <td><span style="font-family:var(--font-mono); font-size:11px; color:#94a3b8">${esc(run.provider_run_id || "—")}</span></td>
      <td><b>${run.usage_usd != null ? "$" + Number(run.usage_usd).toFixed(4) : "—"}</b></td>
    </tr>`).join("") || '<tr><td colspan="9" class="empty-state">Chưa có lần chạy nào.</td></tr>';
}

export async function openDetail(itemId, item) {
  const drawer = $("drawer");
  drawer.classList.add("open");
  $("drawerBody").innerHTML = `
    <h2>${esc(item?.name || itemId)}</h2>
    <div class="subtitle" style="margin-bottom:16px">Đang tải lịch sử giá & phân tích biến thể...</div>
  `;

  const [history, raw] = await Promise.all([
    api(`/api/items/${itemId}/history`),
    api(`/api/items/${itemId}/raw`).catch(() => null),
  ]);

  const breakdown = item?.breakdown || [];
  const variants = item?.variants || [];
  const seller = item?.seller || {};

  $("drawerBody").innerHTML = `
    <div style="display:flex; justify-content:space-between; align-items:flex-start; margin-bottom:14px">
      <div>
        <h2 style="font-size:17px; font-weight:700; color:#fff">${esc(item?.name || itemId)}</h2>
        <div style="font-size:12px; color:var(--text-muted); margin-top:4px">
          Shop: <b>${esc(item?.shop_name || "—")}</b> · SKU ID: <code>${itemId}</code> · Cập nhật: ${time(item?.captured_at)}
        </div>
      </div>
    </div>

    <!-- Waterfall chi tiết -->
    <div class="card" style="margin-bottom:16px; background:#181d26">
      <div style="font-size:13px; font-weight:700; margin-bottom:10px; color:#fbbf24">⚡ Cấu Trúc Waterfall Giá Cuối</div>
      <div style="display:flex; flex-direction:column; gap:6px">
        ${breakdown.map((step) => `
          <div style="display:flex; justify-content:space-between; padding:8px 12px; border-radius:6px; background:#0f131a; border:1px solid #283142; font-size:12.5px">
            <span style="color:var(--text-muted)">
              ${esc(step.label)}
              ${step.code ? `<code style="color:#38bdf8; margin-left:6px">${esc(step.code)}</code>` : ""}
              ${step.reason ? `<span style="color:#94a3b8; font-size:11px">(${esc(step.reason)})</span>` : ""}
            </span>
            <span style="font-weight:700; color:${step.step === 'final_price' ? '#38bdf8' : '#fff'}">
              ${step.amount !== undefined ? money(step.amount, item?.currency) : (step.applied ? "Đã áp dụng" : "Không áp dụng")}
            </span>
          </div>
        `).join("")}
      </div>
    </div>

    <!-- Biểu đồ lịch sử giá -->
    <div class="card" style="margin-bottom:16px; background:#181d26">
      <div style="font-size:13px; font-weight:700; margin-bottom:8px">📈 Lịch Sử Biến Động Giá Cuối</div>
      ${sparkline(history.history)}
    </div>

    <!-- Danh sách biến thể -->
    <div class="card" style="background:#181d26">
      <div style="font-size:13px; font-weight:700; margin-bottom:10px">📦 Danh Sách Biến Thể & Tồn Kho (${variants.length})</div>
      <div class="table-responsive" style="max-height:300px">
        <table class="copilot-table" style="font-size:12px">
          <thead>
            <tr>
              <th>Tên biến thể</th>
              <th>Giá biến thể</th>
              <th>Tồn kho</th>
            </tr>
          </thead>
          <tbody>
            ${variants.slice(0, 50).map((v) => `
              <tr>
                <td>${esc(v.name || v.model_id)}</td>
                <td><b style="color:#38bdf8">${money(v.price, item?.currency)}</b></td>
                <td>${v.stock ?? "—"}</td>
              </tr>
            `).join("")}
          </tbody>
        </table>
      </div>
    </div>
  `;
}
