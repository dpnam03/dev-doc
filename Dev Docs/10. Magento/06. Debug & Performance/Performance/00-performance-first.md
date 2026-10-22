---
title: Performance-first — Tư duy & nền tảng tối ưu hiệu năng web
platform: magento
scope: both
status: current
owner: magento-team@
updated: 2026-10-22
tags: [performance, mindset, critical-rendering-path, core-web-vitals, best-practice]
---

# Performance-first

> Nội dung từ buổi sharing BSSCommerce. Đây là doc mở đầu của series Performance — nên đọc trước [01-web-cache](01-web-cache.md) và [02-magento2-speed-optimization](02-magento2-speed-optimization.md).

## 1. Khái niệm Performance-first

Performance-first là **tư duy đặt hiệu suất làm ưu tiên hàng đầu ngay từ giai đoạn thiết kế, phát triển, kiểm thử và vận hành** một ứng dụng web.

Giúp tránh:
- Cấu trúc mã phức tạp, khó bảo trì.
- Thời gian tải trang chậm, giảm mức độ hài lòng của người dùng.
- Chi phí hạ tầng và vận hành tăng cao.

## 2. Vì sao Performance quan trọng?

- **Trải nghiệm người dùng:** 53% người dùng mobile rời đi nếu trang tải > 3 giây. Tốc độ chậm gây phản ứng căng thẳng tương tự khi xem phim kinh dị / giải toán.
- **Doanh thu:** hiệu suất ảnh hưởng trực tiếp đến tỷ lệ chuyển đổi.
- **Chi phí & khả năng truy cập:** tác động đến chi phí vận hành và khả năng tiếp cận.

## 3. Chỉ số đo lường

- **Core Web Vitals** (LCP, INP, CLS) — xem chi tiết trong [02-magento2-speed-optimization](02-magento2-speed-optimization.md).
- Các chỉ số phụ (TTFB, FCP...).

## 4. Cách browser render page — Critical Rendering Path

Browser cần biết **số lượng tài nguyên tối thiểu cần chờ** trước khi render lần đầu. Trình tự này gọi là **Critical Rendering Path (CRP)**:

1. **Loading resource.**
2. **Parse HTML → DOM.** Gặp `<script>` chưa có `async`/`defer` → browser **tạm dừng** parse HTML để tải & thực thi JS.
3. **Parse CSS → CSSOM.** Browser phải tải & parse toàn bộ CSS trước khi bắt đầu render.
4. **DOM + CSSOM → Render Tree.**
5. **Layout → Paint → Composite.**

Trong lần render đầu:
| Browser **bắt buộc đợi** | Browser **thường không đợi** |
|---|---|
| Một phần HTML | Toàn bộ HTML |
| CSS & JS trong `<head>` | Fonts, Images |
| | CSS/JS non-render-blocking ngoài `<head>` |

> Tool kiểm tra: https://www.webpagetest.org/

## 5. Best Practice

### Backend
Phần lớn thời gian chương trình là **chờ** input người dùng, **chờ truy vấn DB**, **chờ phản hồi mạng** → tối ưu BE chủ yếu nằm ở **cách tổ chức luồng xử lý, truy cập dữ liệu và giao tiếp mạng**, không phải chỉ thuật toán.
→ Tập trung **tối ưu query DB** thay vì "ám ảnh" tối ưu thuật toán.

### Frontend — HTML
- Giảm độ sâu của DOM.
- Dùng cache hợp lý (Magento 2: block `cacheable=false` khiến **cả trang** không được cache).
- Tối ưu thứ tự tải tài nguyên (`preload`/`prefetch` cho tài nguyên quan trọng).
- Dùng thẻ semantic (`<header>`, `<main>`, `<article>`, `<footer>`) → tốt cho render & SEO.

### Frontend — CSS
- **Mobile-first** → hạn chế code thừa, giảm CSS phải tải.
- Tuân thủ **style guide** thống nhất → giảm trùng lặp CSS.
- Hạn chế `!important`, giới hạn selector lồng nhau, ưu tiên chỉnh sửa thay vì ghi đè toàn bộ.

### Frontend — JavaScript
- Dùng `defer`/`async` để trì hoãn tải script.
- Tránh inline script chặn render; đưa script xuống cuối HTML.

### Design
- Thiết kế **mobile-first**: bắt đầu từ cấu trúc & nội dung cốt lõi.
- Tái sử dụng thành phần lặp lại; thống nhất hệ màu & style.
- Hạn chế hiệu ứng phức tạp không cần thiết.

> *"Mọi dòng code bạn viết đều có chi phí thời gian và tài nguyên — hãy đảm bảo nó xứng đáng."*
