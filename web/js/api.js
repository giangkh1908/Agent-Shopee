// Gọi API backend (mặc định cổng 8000; nếu trang mở từ cổng khác thì gọi chéo origin).
const isLocal = ["localhost", "127.0.0.1", ""].includes(location.hostname);
export const API_BASE = !isLocal || location.port === "8000" ? "" : "http://127.0.0.1:8000";

export async function api(path, options) {
  const response = await fetch(API_BASE + path, options);
  const text = await response.text();
  let data;
  try { data = JSON.parse(text); } catch { data = { detail: text }; }
  if (!response.ok) {
    throw new Error(typeof data.detail === "string" ? data.detail : JSON.stringify(data.detail));
  }
  return data;
}
