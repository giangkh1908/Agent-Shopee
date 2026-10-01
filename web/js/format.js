// Tiện ích hiển thị: DOM, tiền tệ, thời gian, escape HTML.
export const $ = (id) => document.getElementById(id);

export const money = (value, currency) =>
  (value === null || value === undefined)
    ? "—"
    : `${Number(value).toLocaleString("en-SG", { maximumFractionDigits: 2 })} ${currency || ""}`.trim();

export const pct = (value) =>
  (value === null || value === undefined) ? "" : `${value > 0 ? "+" : ""}${value}%`;

export const esc = (value) =>
  String(value ?? "").replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));

export const time = (iso) =>
  iso ? new Date(iso).toLocaleString("vi-VN", { hour12: false }) : "—";

export function voucherCell(voucher) {
  if (!voucher || !voucher.voucherCode) return '<span class="muted">—</span>';
  const min = voucher.minSpend ? ` · min ${voucher.minSpend}` : "";
  return `<span class="voucher"><span class="code">${esc(voucher.voucherCode)}</span> −${voucher.voucherDiscount}${min}</span>`;
}

export function statCard(value, label, color) {
  return `<div class="stat"><b style="color:${color || "var(--text)"}">${value}</b><span>${label}</span></div>`;
}

// Biểu đồ đường nhỏ từ chuỗi final_price.
export function sparkline(history) {
  const points = history.map((h) => h.final_price).filter((v) => typeof v === "number");
  if (points.length < 2) return '<div class="muted">Cần ≥2 lần quét để vẽ biểu đồ.</div>';
  const min = Math.min(...points);
  const max = Math.max(...points);
  const span = max - min || 1;
  const step = 100 / (points.length - 1);
  const path = points
    .map((v, i) => `${(i * step).toFixed(2)},${(28 - ((v - min) / span) * 24).toFixed(2)}`)
    .join(" ");
  const color = points[points.length - 1] > points[0] ? "var(--bad)" : "var(--ok)";
  return `<svg class="chart" viewBox="0 0 100 30" preserveAspectRatio="none">
      <polyline fill="none" stroke="${color}" stroke-width="1.2" points="${path}" />
    </svg>
    <div class="legend">${points.length} điểm · thấp nhất ${min} · cao nhất ${max} · hiện tại ${points[points.length - 1]}</div>`;
}
