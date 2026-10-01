# 🚀 HƯỚNG DẪN TỪ ĐẦU: CÀI ĐẶT & CHẠY DỰ ÁN SHOPEE COPILOT
> **Dành cho người mới bắt đầu từ con số 0 (Zero to Hero)**  
> Không cần biết lập trình trước đó, chỉ cần làm theo từng bước bấm chuột dưới đây.

---

## 📑 MỤC LỤC
1. [Bước 1: Tải & Cài đặt VS Code (Trình soạn thảo mã nguồn)](#-bước-1-tải--cài-đặt-visual-studio-code)
2. [Bước 2: Tải & Cài đặt Python (Cực kỳ quan trọng: Tích chọn Add to PATH)](#-bước-2-tải--cài-đặt-python)
3. [Bước 3: Mở Dự Án Bằng VS Code](#-bước-3-mở-dự-án-trong-vs-code)
4. [Bước 4: Cài đặt Extension Python trong VS Code](#-bước-4-cài-extension-python-trên-vs-code)
5. [Bước 5: Cài đặt Thư viện cho Dự án](#-bước-5-cài-đặt-thư-viện-cần-thiết)
6. [Bước 6: Khởi động Server & Mở Web trên Trình duyệt](#-bước-6-chạy-dự-án--mở-trang-web)
7. [Bước 7: Hướng dẫn Sử dụng Web Thực tế](#-bước-7-hướng-dẫn-sử-dụng-thực-tế)
8. [❓ Xử lý Lỗi Thường Gặp](#-xử-lý-lỗi-thường-gặp)

---

## 💻 BƯỚC 1: Tải & Cài Đặt Visual Studio Code

VS Code là phần mềm miễn phí dùng để mở thư mục dự án và gõ lệnh chạy web.

1. **Link tải chính thức:** 👉 [https://code.visualstudio.com/Download](https://code.visualstudio.com/Download)
2. Bấm vào nút **Windows** (User Installer x64) để tải file cài đặt (dạng `.exe`).
3. Mở file vừa tải về lên:
   - Chọn **"I accept the agreement"** (Tôi đồng ý) → Bấm **Next**.
   - Bấm **Next** tiếp tục cho đến màn hình **Select Additional Tasks**.
   - ⚠️ **LƯU Ý:** Tích chọn vào cả 2 ô:
     - `Add "Open with Code" action to Windows Explorer file context menu`
     - `Add "Open with Code" action to Windows Explorer directory context menu`
     - `Add to PATH` (mặc định đã chọn).
   - Bấm **Install** → Đợi chạy xong bấm **Finish**.

---

## 🐍 BƯỚC 2: Tải & Cài Đặt Python

Python là môi trường để chạy máy chủ và xử lý dữ liệu.

1. **Khuyến nghị phiên bản:** **Python 3.11.x** hoặc **Python 3.12.x** (Chạy ổn định nhất với mọi thư viện AI).
2. **Link tải trực tiếp bản ổn định (Windows 64-bit):**
   - 👉 [Trang chủ tải Python cho Windows](https://www.python.org/downloads/windows/)
   - Hoặc tải trực tiếp bản **Python 3.11.9 (Installer 64-bit)**: [Tải Python 3.11.9 exe](https://www.python.org/ftp/python/3.11.9/python-3.11.9-amd64.exe)
3. **CÁC BƯỚC BẤM CÀI ĐẶT (ĐỌC KỸ TRÁNH LỖI):**
   - Click đúp mở file cài đặt Python vừa tải về.
   - 🔴 **BƯỚC SỐNG CÒN:** Ở ngay màn hình đầu tiên phía dưới cùng, hãy **TÍCH CHỌN VÀO Ô:**
     > ☑️ **Add python.exe to PATH** *(Nếu quên tích ô này, máy tính sẽ báo lỗi không nhận lệnh python!)*
   - Sau đó bấm vào nút trên cùng: **Install Now**. *(Mặc định gói cài đặt chính hãng này đã tự động tích hợp sẵn `pip` bên trong).*
   - Đợi thanh chạy báo *Setup was successful*.
   - Nếu xuất hiện dòng chữ `Disable path length limit`, hãy bấm vào đó 1 lần rồi bấm **Close**.

### 🔍 Kiểm tra xem Python và pip đã cài đặt thành công chưa:
1. Bấm phím **Windows** trên bàn phím, gõ chữ `cmd` và bấm **Enter** để mở Command Prompt.
2. Gõ lệnh:
   ```bash
   python --version
   ```
   👉 Màn hình hiện `Python 3.11.x` (hoặc 3.12.x) là chuẩn!
3. Gõ tiếp lệnh kiểm tra `pip`:
   ```bash
   pip --version
   ```
   👉 Màn hình hiện `pip 24.x... from ... (python 3.11)` là bạn đã có sẵn pip!

*(Nếu gõ `pip --version` mà máy báo không nhận diện được, xem mục [Cách cài/sửa lỗi pip thủ công](#-cách-cài--kích-hoạt-pip-nếu-bị-thiếu) ở cuối bài).*
---

## 📂 BƯỚC 3: Mở Dự Án Trong VS Code

Dự án đang nằm ở đường dẫn: `D:\Agent-Shopee`

### Cách 1: Mở từ thanh tìm kiếm máy tính
1. Mở phần mềm **Visual Studio Code**.
2. Trên thanh menu trên cùng, chọn **File** → Chọn **Open Folder...** (hoặc phím tắt `Ctrl + K, Ctrl + O`).
3. Tìm đến ổ đĩa **D:** → Click chọn thư mục **Agent-Shopee** → Bấm **Select Folder**.
4. Nếu VS Code hiện bảng hỏi *"Do you trust the authors of the files in this folder?"*, bấm chọn **Yes, I trust the authors**.

### Cách 2: Mở nhanh bằng chuột phải
1. Mở ổ đĩa **D:** trên máy tính của bạn.
2. Click chuột phải vào thư mục **Agent-Shopee** → Chọn **Open with Code**.

---

## 🧩 BƯỚC 4: Cài Extension Python Trên VS Code

Để VS Code hỗ trợ chạy Python mượt nhất:
1. Nhìn sang thanh biểu tượng bên mép trái của VS Code, bấm vào icon **4 ô vuông (Extensions)** hoặc bấm tổ hợp phím `Ctrl + Shift + X`.
2. Ở ô tìm kiếm phía trên, gõ chữ: `Python`.
3. Tìm extension **Python** do chính hãng **Microsoft** phát hành (thường ở ngay dòng đầu tiên) → Bấm nút **Install**.

---

## 📦 BƯỚC 5: Cài Đặt Thư Viện Cần Thiết Bằng pip

`pip` là công cụ chuyên dùng của Python để tải các gói thư viện trên mạng về máy.

Mở cửa sổ dòng lệnh (Terminal) ngay trong VS Code:
1. Trên thanh menu VS Code, bấm vào **Terminal** → Chọn **New Terminal** (hoặc bấm phím tắt: `` Ctrl + ` `` - dấu huyền cạnh phím số 1).
2. Lúc này ở góc dưới màn hình sẽ xuất hiện một bảng gõ lệnh màu đen. Đảm bảo đường dẫn đang hiển thị là:
   ```text
   D:\Agent-Shopee>
   ```
3. Gõ lệnh sau vào Terminal rồi bấm **Enter** để cài đặt toàn bộ thư viện cần thiết:
   ```bash
   pip install -r requirements.txt
   ```
   *(Mẹo: nếu máy bạn báo lệnh `pip` không chạy, hãy gõ thay bằng: `python -m pip install -r requirements.txt`)*
4. Đợi khoảng 10-20 giây để hệ thống tải xong (hiện chữ *Successfully installed...* là hoàn tất).

---

## 🌐 BƯỚC 6: Chạy Dự Án & Mở Trang Web
1. Vẫn tại cửa sổ Terminal ở góc dưới VS Code, gõ chính xác dòng lệnh sau rồi bấm **Enter**:
   ```bash
   python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
   ```
2. Khi thấy màn hình hiện thông báo tương tự như sau:
   ```text
   INFO:     Started server process [...]
   INFO:     Waiting for application startup.
   INFO:     Application startup complete.
   INFO:     Uvicorn running on http://127.0.0.1:8000 (Press CTRL+C to quit)
   ```
   👉 Nghĩa là máy chủ đã chạy thành công!
3. **Mở Web:**
   - Mở trình duyệt bất kỳ (Google Chrome, Cốc Cốc, Edge).
   - Truy cập vào địa chỉ: 👉 **`http://127.0.0.1:8000`** (hoặc `http://localhost:8000`).
   - Màn hình giao diện **Shopee Copilot** sẽ xuất hiện!

> 🛑 **Lưu ý:** Muốn tắt web, quay lại màn hình Terminal của VS Code bấm tổ hợp phím `Ctrl + C`. Khi nào muốn dùng lại thì chỉ cần gõ lại lệnh ở Bước 6.

---

## 🎯 BƯỚC 7: Hướng Dẫn Sử Dụng Thực Tế

1. **Quét đối thủ:**
   - Copy link sản phẩm Shopee của đối thủ (ví dụ: `https://shopee.sg/product/34229630/2591950137/`).
   - Dán vào ô textarea lớn ở trên cùng (có thể dán nhiều link, mỗi dòng 1 link).
   - Bấm nút **"Quét Đối Thủ"**. Chờ 4-5 giây dữ liệu sẽ nhảy vào bảng bên dưới.
2. **Đối chiếu & Bật AI Hiến Kế:**
   - Tại cột **"Link shop của bạn"** trên dòng sản phẩm, dán link sản phẩm tương ứng của shop bạn vào.
   - Bấm nút **"⚡ AI Phân Tích"**.
   - Cửa sổ phân tích sẽ hiện ra ngay lập tức: Báo cho bạn biết giá bên nào rẻ hơn, chênh lệch bao nhiêu % và đưa ra **3 kế sách thực chiến** để shop bạn đối phó mà không bị lỗ vốn.

---

## ❓ XỬ LÝ LỖI THƯỜNG GẶP

### 1. Lỗi `'python'` hoặc `'pip'` không được nhận diện (`is not recognized as an internal or external command...`)
* **Nguyên nhân:** Khi cài đặt Python ở Bước 2, bạn quên chưa tích vào ô `Add python.exe to PATH`.
* **Cách sửa:**
  - Chạy lại file cài đặt Python `.exe` đã tải về.
  - Chọn **Modify** → Bấm **Next** (đảm bảo ô `pip` đã được tích chọn) → Ở màn hình kế tiếp, tích chọn vào ô **Add Python to environment variables** → Bấm **Install**.
  - Tắt hoàn toàn VS Code đi rồi mở lại.

### 2. Cách cài / kích hoạt pip nếu bị thiếu (Cực kỳ hiếm gặp)
Nếu máy tính đã nhận lệnh `python` nhưng gõ `pip` vẫn báo lỗi, chỉ cần mở Terminal trong VS Code và gõ lệnh sau để kích hoạt lại pip có sẵn:
```bash
python -m ensurepip --upgrade
```
Hoặc nâng cấp pip lên bản mới nhất:
```bash
python -m pip install --upgrade pip
```

### 3. Lỗi cổng 8000 bị chiếm dụng (`Address already in use`)
* **Nguyên nhân:** Đang có một cửa sổ khác chạy ngầm máy chủ này.
* **Cách sửa:** Đổi sang cổng 8001 bằng lệnh:
  ```bash
  python -m uvicorn app.main:app --host 127.0.0.1 --port 8001
  ```
  Sau đó vào trình duyệt bằng địa chỉ: `http://127.0.0.1:8001`.

### 4. File cấu hình mã API (`.env`)
* Dự án đã được cấu hình sẵn file bí mật `.env` chứa chìa khóa kết nối dữ liệu Shopee và AI. Bạn không cần chỉnh sửa hay xóa file này.
