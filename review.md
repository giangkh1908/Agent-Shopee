# BÁO CÁO PHÂN TÍCH & ĐÁNH GIÁ KỸ THUẬT (REVIEW.MD)
## Hệ Thống Giám Sát Giá Đối Thủ & Chiến Thuật Định Giá Shopee (Shopee Copilot)

---

### 1. Bối cảnh & Bản chất bài toán (Problem Statement)

Bài toán đặt ra: **Xây dựng hệ thống tự động bám đuổi giá đối thủ trên sàn thương mại điện tử Shopee, tính toán "Giá Cuối" (Final Price thực trả của người mua) và dùng AI đưa ra kế sách định giá cạnh tranh.**

Để giải quyết bài toán này, thách thức kỹ thuật lớn nhất không nằm ở giao diện hay prompt AI, mà nằm ở **tầng thu thập dữ liệu (Data Extraction)**:

1. **Shopee đã chặn hoàn toàn truy cập ẩn danh (Anonymous Scraping Wall):**
   - Từ cuối tháng 09/2026 trên tất cả 9 thị trường (bao gồm `.vn`, `.sg`, `.my`,...), Shopee chuyển toàn bộ dữ liệu quan trọng (`price`, `promoPrice`, `voucher`, `stock`, `sold`) vào sau bức tường đăng nhập (`Login Required`).
   - Gọi HTTP thông thường (`curl`, `requests`, `httpx`) chỉ nhận về shell HTML rỗng (~163 KB) không chứa SSR data (`__NEXT_DATA__` hay `ld+json`).
   - Gọi trực tiếp API nội bộ (như `/api/v4/pdp/get_pc`) bị trả lỗi `{"is_login": false, "error": 90309999}`.
   - Headless browser không có session lập tức bị redirect về `/verify/traffic/error?is_logged_in=false`.
   - Cơ chế chặn là **Token-based (chữ ký JS client-side)**, không phải thuần IP-based ⇒ Kỹ thuật xoay Proxy / User-Agent thông thường hoàn toàn vô hiệu.

2. **Bài toán "Giá Cuối" (Final Price Waterfall) phức tạp:**
   - Người mua trên Shopee hầu như không bao giờ mua với giá niêm yết (`price`) hay giá gạch (`strikethrough`).
   - Giá thực trả phụ thuộc vào: **Giá Flash Sale / Promo** $\rightarrow$ Trừ **Voucher Shop** (có điều kiện `min_spend`) $\rightarrow$ Trừ **Voucher Sàn (Shopee Platform)** $\rightarrow$ Ra **Final Price**.
   - Nếu chỉ cào giá thô mà không có thông tin voucher, hệ thống định giá sẽ sai lệch hoàn toàn.

---

### 2. Quá trình khảo sát & Lựa chọn giải pháp API (Search & Benchmark)

Để tìm ra giải pháp tối ưu nhất, toàn bộ các phương án trên thị trường đã được rà soát và đo kiểm thực tế:

```
                          ┌───────────────────────────────┐
                          │    Nhu cầu lấy dữ liệu Shopee  │
                          └──────────────┬────────────────┘
                                         │
                 ┌───────────────────────┴───────────────────────┐
                 ▼                                               ▼
     [ Dữ liệu shop của chính mình ]                 [ Dữ liệu shop đối thủ ]
                 │                                               │
    Shopee Open Platform API                        ┌────────────┴────────────┐
    (order, business_insights, ads)                 ▼                         ▼
                                           Affiliate Open API        Scraping / Crawling
                                           (productOfferV2)                   │
                                                    │             ┌───────────┴───────────┐
                                              Chỉ có min/max      ▼                       ▼
                                              Không có Voucher  Tự crawl (Playwright)  Apify Actor
                                                                (Rủi ro khoá acc)      (Zen Studio)
                                                                                          │
                                                                                 Khảo sát & Chọn lọc:
                                                                                 • kazkn: 38% pass (FAIL)
                                                                                 • gio21: Thiếu voucher
                                                                                 • zen-studio: 96% pass,
                                                                                   186 fields, đủ voucher
                                                                                   ==> CHỌN LÀM PRIMARY
```

#### 2.1. Khảo sát Shopee Open Platform (API chính thức)
- Đã rà soát toàn bộ **32 modules / 465 endpoints** của Shopee Open Platform.
- **Kết luận:** Shopee chỉ cung cấp API quản lý shop của chính người bán (Order, Business Insights, Ads, Item Base Info). **Không có bất kỳ endpoint chính thức nào cho phép đọc dữ liệu của shop đối thủ.**

#### 2.2. Khảo sát Shopee Affiliate Open API (`productOfferV2`)
- Tìm kiếm endpoint GraphQL: `https://open-api.affiliate.shopee.sg/graphql`.
- Cho phép lấy `priceMin`, `priceMax`, `sales`, `ratingStar` của sản phẩm bất kỳ.
- **Hạn chế:** Không chứa thông tin Voucher ngăn xếp và Flash Sale; yêu cầu duyệt tài khoản affiliate và whitelist. Chỉ phù hợp làm lớp quét diện rộng, không dùng để tính giá thực chiến.

#### 2.3. Khảo sát thị trường Scraper & Dịch vụ trích xuất (Search & Evaluation)
Thực hiện benchmark các actor phổ biến trên nền tảng Apify:

| Nhà cung cấp / Actor | Tỷ lệ thành công (30 ngày) | Chi phí / 1.000 SKU | Tình trạng Voucher & Final Price | Đánh giá |
|---|---|---|---|---|
| **DataKazKN / `kazkn`** (`shopee-product-scraper-no-login`) | **38.4%** (53 runs thất bại, gắn cờ `UNDER_MAINTENANCE`) | $4.80 | ❌ Không có voucher, không có flash-sale, không có tồn kho variant. | **Loại** (Không đáp ứng chất lượng). |
| **gio21 / `shopee-scraper`** | 99.4% | $1.00 | ❌ Thiếu voucher chi tiết, thiếu campaign. | Dùng làm dự phòng giá rẻ. |
| **xtracto / `shopee-scraper`** | 97.8% | $20.00 | ⚠️ Bị giới hạn field sau đợt cập nhật của Shopee. | Quá đắt, không tối ưu. |
| **Zen Studio (`zen-studio/shopee-product-detail-scraper`)** | **96.0%** (8.209 / 8.552 runs thành công) | ~$3.99 – $7.99 | ✅ **186 fields**: `price`, `promoPrice`, `cardDisplayPrice`, `shopVoucher`, `platformVoucher`, `stock`, `variants`. | **Lựa chọn số 1 (Primary Source)** |

#### 2.4. Kiểm chứng thực nghiệm (P0 Proof-of-Concept)
- Chạy thử nghiệm thực tế với 8 link sản phẩm Shopee phức tạp (nhiều biến thể, có flash sale, có đồng thời voucher shop và voucher sàn Shopee).
- **Kết quả 8/8 thành công:**
  - Lấy đầy đủ 186 trường dữ liệu.
  - Công thức Waterfall:
    $$\text{Final Price} = \text{Promo Price} - \text{Shop Voucher} - \text{Platform Voucher}$$
  - Kết quả sau khi tính toán đối chiếu **khớp 100% với trường `cardDisplayPrice`** do Shopee hiển thị trực quan cho người dùng.

---

### 3. Kiến trúc hệ thống & Cách tiếp cận kỹ thuật

Dự án được thiết kế theo nguyên lý **Phân tách trách nhiệm (Separation of Concerns)** và **Kỷ luật dữ liệu**:

```
[Người dùng dán link Shopee]
            │
            ▼
┌───────────────────────────────────────┐
│ 1. Deterministic Parser (Regex)       │ ──> Tách Shop ID, Item ID, Region (SG, VN,...)
└───────────────────┬───────────────────┘     (Không dùng LLM để parse link)
                    │
                    ▼
┌───────────────────────────────────────┐
│ 2. Data Provider (Apify Zen Studio)   │ ──> Chạy Async Run, nhận payload 186 fields
└───────────────────┬───────────────────┘
                    │
                    ▼
┌───────────────────────────────────────┐
│ 3. Pricing Waterfall Engine (Python)  │ ──> Tính giá cuối, kiểm tra điều kiện min_spend,
└───────────────────┬───────────────────┘     so sánh đối soát cardDisplayPrice
                    │
                    ▼
┌───────────────────────────────────────┐
│ 4. Snapshot Storage (SQLite)          │ ──> Lưu lịch sử giá, biến động tồn kho,
└───────────────────┬───────────────────┘     lịch sử cào
                    │
                    ▼
┌───────────────────────────────────────┐
│ 5. AI Copilot (Gemini 3.8 Flash)      │ ──> Tiếp nhận số liệu ĐÃ TÍNH TOÁN,
└───────────────────────────────────────┘     đưa ra 3 kế sách định giá thực chiến
```

#### 3.1. Kỷ luật phân tách: "Code tính toán, AI tư vấn"
- **Nguyên tắc cốt lõi:** Tuyệt đối không để LLM làm phép tính toán học (cộng trừ phần trăm, trừ voucher, tính độ lệch giá). LLM dễ bị hallucination làm sai lệch số thập phân tài chính.
- Mọi con số (giá sau voucher, độ lệch `diff`, `% chênh lệch`, biên độ lợi nhuận với giá vốn `cost`) đều do Python tính toán chính xác với làm tròn 2 chữ số (`round(..., 2)`).
- **Vai trò của AI Copilot:** Đóng vai trò là Giám đốc chiến lược định giá (Pricing Strategy Director):
  - Phân tích tương quan giữa giá đối thủ và shop mình.
  - Nhận diện bẫy giá (đối thủ đang chạy Flash Sale ngắn hạn hay giảm giá xả kho vì tồn ít).
  - Đưa ra 3 kế sách đối phó cụ thể: giữ giá tặng quà, tạo combo/bundle, hạ giá bám đuổi kèm voucher tương đương, hoặc tăng ngân sách ads khi đối thủ sắp hết hàng.

#### 3.2. Chuẩn hóa & Lưu vết lịch sử (Snapshot Disciplines)
- Giữ nguyên `shop_id` và `item_id` dạng chuỗi/nguyên bản, không ép kiểu số thực (tránh mất độ chính xác của 64-bit ID).
- Từ chối so sánh giá nếu khác đơn vị tiền tệ (`SGD`, `VND`, `MYR`).
- Thiếu sản phẩm trong một lần quét không được tự ý suy diễn là "hết hàng" (`missing != out of stock`), chỉ ghi nhận trạng thái khi trường `stock == 0`.

---

### 4. Đánh giá ưu điểm, hạn chế & Hướng phát triển

#### 4.1. Ưu điểm (Strengths)
1. **Tính khả thi & ổn định cao:** Vượt qua được bức tường chặn login của Shopee mà không cần duy trì hệ thống proxy/farm tài khoản phức tạp.
2. **Độ chính xác vượt trội:** Nhờ bóc tách được cả 2 tầng voucher (Shop Voucher + Platform Voucher), phản ánh đúng 100% giá người mua thực trả.
3. **Chi phí tối ưu:** Chi phí chỉ khoảng ~$0.004 - $0.008 trên mỗi lượt quét sản phẩm; có thể kiểm soát và lập lịch quét linh hoạt.
4. **UX tinh gọn:** Giao diện một trang trực quan, dán link hàng loạt, có đối chiếu trực tiếp giữa link đối thủ và link shop mình.

#### 4.2. Hạn chế & Rủi ro (Risks & Limitations)
1. **Phụ thuộc bên thứ ba:** Phụ thuộc vào tốc độ cập nhật của Zen Studio khi Shopee thay đổi thuật toán mã hóa client-side.
2. **Thời gian phản hồi:** Vì là async scraper thông qua Apify, mỗi lượt quét mất khoảng 4 - 8 giây/SKU, không phải real-time tức thì.
3. **Phí duy trì:** Cần nạp credit Apify khi quét số lượng lớn (thay vì miễn phí hoàn toàn).

#### 4.3. Kế hoạch mở rộng (Next Steps)
- Tích hợp thêm **Affiliate Open API** làm lớp lọc sơ bộ miễn phí (quét biến động giá cơ bản 1 tiếng/lần); khi phát hiện biến động mới kích hoạt Apify cào sâu voucher.
- Tự động hóa webhook gửi cảnh báo tức thì qua **Telegram Bot** khi đối thủ undercut giá quá 5% hoặc khi đối thủ hết hàng.
- Bổ sung module kết nối chính thức **Shopee Open Platform** của shop mình để tự động sync giá vốn và doanh thu hằng ngày.