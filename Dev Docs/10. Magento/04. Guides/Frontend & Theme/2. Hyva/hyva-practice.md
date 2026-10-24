---
title: Hyvä Practice — Cookbook & best practices
platform: magento
scope: frontend
status: current
owner: magento-team@
updated: 2026-10-22
tags: [hyva, best-practice, csp, pci-dss, view-utilities, performance, section-data]
---

# Hyvä Practice — Cookbook & best practices

Tổng hợp pattern thực hành khi code Hyvä: build theme, Tailwind, Alpine plugins, helper functions, tối ưu JS, View Utilities và **Alpine CSP (bắt buộc cho PCI-DSS)**.

---

## 1. Build Your Theme

Cấu trúc theme Hyvä thường kế thừa theo tầng:

| Parent theme | Styling | Content page (performance) |
|---|---|---|
| Default theme | Layout XML | Lazyload image |
| **CSP Theme** | Dummy Template | Defer libraries |
| **Reset Theme** | Safelist | Keeping layout stable |

**Nguyên tắc khi build (tránh layout shift & tối ưu tải):**
- Không dùng JavaScript để đổi hiển thị item ở **lần load đầu**.
- Không render element visible rồi lại ẩn đi sau khi JS init (gây nháy/CLS).
- Phần lớn trường hợp **không preload custom font**.

---

## 2. Tailwind CSS trong thực tế

- **Sharing common CSS between themes:** dùng chung config qua `share config [parent theme]`.
- **Defining / Using CSS variables:** khai báo biến CSS để tái sử dụng giữa các theme.
- **Optimize CSS:**
  - **Exclude module path** không dùng khỏi quá trình scan.
  - **Không dùng dynamic class** trong template (vd ghép chuỗi class) — Tailwind purge sẽ không nhận ra → class bị loại.
  - Ưu tiên **utility class** có sẵn.

> Xem thêm: [tailwind-css.md](tailwind-css.md).

---

## 3. Alpine plugins trong Hyvä

Hyvä đóng gói sẵn một số plugin Alpine hữu ích:

| Plugin | Công dụng |
|---|---|
| `x-intersect` | Trigger hành động khi element vào viewport (lazy load) |
| `x-ignore` | Loại 1 phần HTML khỏi xử lý của Alpine |
| `x-defer` | Hoãn khởi tạo component Alpine để cải thiện tốc độ load |
| `x-snap-slider` | Slider CSS-driven kèm JS |
| `x-collapse` | Animation mượt khi expand/collapse |
| `x-htmldialog` | Dùng native HTML `<dialog>` cho modal / offcanvas |

**Tích hợp thư viện bên thứ 3 với Alpine:**
- Kiểm tra lib **tương thích Alpine v3+**.
- **CSP compliance:** lib không được dùng inline script / `eval()` (bị CSP chặn) — chọn lib CSP-friendly.
- **Test** kỹ trên cả Luma (nếu có) lẫn Hyvä.

---

## 4. Hyvä helper functions (`window.hyva`)

| Hàm | Công dụng |
|---|---|
| `hyva.postForm(postParams)` | Submit form với params, tương thích kiến trúc Hyvä |
| `hyva.getFormKey()` | Lấy form key (token chống CSRF của Magento) |
| `hyva.formatPrice(value, showSign, options)` | Format số theo currency hiện tại |
| `hyva.replaceDomElement(selector, content)` | Thay 1 DOM element bằng HTML mới + chạy script nhúng |
| `hyva.activateScripts(node)` | Trích & chạy các thẻ `<script>` trong HTML được inject |

Ví dụ `formatPrice`:
```js
hyva.formatPrice(99.99)                 // "$99.99"
hyva.formatPrice(50, true)              // "+$50.00"  (showSign=true luôn hiện +/-)
hyva.formatPrice(12345.67, false, { groupSeparator: ' ', decimalSeparator: ',' }) // "$12 345,67"
```

---

## 5. Layout handles `hyva_*`

Hyvä tự động áp các layout handle tiền tố **`hyva_*`** **sau** các handle gốc → cho phép override riêng cho Hyvä mà không ảnh hưởng store Luma.

> VD: `checkout_index_index` → có thêm `hyva_checkout_index_index` áp sau. Thay đổi trong handle `hyva_` sẽ được ưu tiên cho theme Hyvä.

---

## 6. Form Validation

Hyvä dùng **native browser validation** cho performance, kèm hệ thống JS validation cho nhu cầu phức tạp.

Các bước:
1. Bật bằng layout handle `hyva_form_validation`.
2. Khởi tạo: `x-data="hyva.formValidation($el)"`.
3. Khai báo rule bằng `data-validate` hoặc HTML5 attribute.
4. Trigger bằng `@submit` hoặc `@change`.

**Validators có sẵn:** `required`, `minlength/maxlength`, `min/max/step`, `email`, `password`, `equalTo`, `pattern`.

---

## 7. Hyvä JavaScript Events

Cho phép các component giao tiếp với nhau qua CustomEvent:
```js
// Dispatch
document.dispatchEvent(new CustomEvent('hyva:product:added', {
  detail: { productId: 123, quantity: 1 }
}));
// Listen
document.addEventListener('hyva:product:added', (event) => {
  console.log('Product added!', event.detail.productId);
});
```
Event phổ biến: product added, cart updated,...

---

## 8. ViewModels — tách logic

Lợi ích của ViewModel (so với Block truyền thống):
- **Decouple logic** khỏi template → code sạch, dễ bảo trì.
- **Boost performance:** cấp data thẳng cho template, bỏ overhead của Magento block.
- **Dễ unit test** (logic gom vào class riêng).
- **Tái sử dụng** nhiều template.

> Chi tiết dùng ViewModel Registry (`$viewModels->require(...)`): xem [alpine-js.md](alpine-js.md) mục "Làm việc với ViewModel".

---

## 9. Customer Section Data

Cách Magento đưa data session (server-side) ra JS trên các trang bị Full Page Cache. Hyvä đơn giản hoá nhiều so với Luma.

- Section data load qua Ajax, lưu ở **localStorage**.
- Mỗi lần load trang, broadcast qua event JS **`private-content-loaded`**.
- Data tự invalidate sau request **HTTP POST**.
- Sau Ajax POST, refresh thủ công bằng cách dispatch **`reload-customer-section-data`**.
- Ép refresh (không qua POST): `hyva.setCookie('mage-cache-sessid', '', -1, true)` trước khi dispatch `reload-customer-section-data`.

Nhận data trong Alpine:
```html
<div x-data="initComponent()"
     @private-content-loaded.window="receiveCustomerData($event.detail.data)">
  <template x-if="customer"><div>Welcome, <span x-text="customer.firstname"></span></div></template>
  <template x-if="!customer"><div>Welcome Guest</div></template>
</div>
```

---

## 10. Render JavaScript chỉ MỘT lần

Khi template render nhiều lần (vd product list), tránh nhân bản JS bằng **`hyva_js_block_dependencies`** *(có từ Hyvä 1.3.6)*:
```xml
<referenceBlock name="product_list">
  <arguments>
    <argument name="hyva_js_block_dependencies" xsi:type="array">
      <item name="wishlist-handler" xsi:type="string">Vendor_Module::exam.js.phtml</item>
    </argument>
  </arguments>
</referenceBlock>
```
JS block sẽ tự render **1 lần** trong container `before-body-end`, bất kể template chính render bao nhiêu lần.

> Khai báo qua **Layout XML** tin cậy hơn qua PHP trong template (do cache `block_html`).

---

## 11. Chạy code chỉ một lần — `{ once: true }`

Code setup (init, thư viện bên thứ 3) chỉ cần chạy 1 lần → dùng option `{ once: true }` cho listener (tự gỡ sau lần chạy đầu):
```js
const initGA = () => { /* Google Analytics */ };
window.addEventListener('load', initGA, { once: true });
```
Dùng `{ once: true }` cho init; với update reactive (vd cart count) thì dùng listener thường.

---

## 12. Load External JavaScript hiệu quả

Script ngoài (analytics, chat, tracking) block render → chỉ load khi cần.

| Khi nào load | Cách |
|---|---|
| Khi user tương tác (click/scroll/keyboard) | event `init-external-scripts` |
| Khi scroll tới section | plugin `x-intersect` |
| Khi tương tác element cụ thể | listener riêng (focus/click) |
| Trang order success (analytics) | tạo **facade** |

Ví dụ **facade** cho live chat (giữ chỗ, tránh layout shift):
```html
<button data-role="init-live-chat" class="btn btn-primary">Click to chat!</button>
<script>
  const btn = document.querySelector('[data-role="init-live-chat"]');
  btn.addEventListener('click', () => { /* load live chat script, rồi trigger */ }, { once: true });
</script>
```
→ Luôn **defer** script không critical để cải thiện Core Web Vitals.

---

## 13. Override JavaScript trong Hyvä

Copy nguyên `.phtml` để override JS khiến upgrade tốn kém. Cách tốt hơn: **chỉ override function/method cần đổi**, giữ code gốc active.

Hai cách (đều ổn): **giữ reference** hàm gốc, hoặc dùng **JS Proxy**. Thêm template render **SAU** template gốc.
```js
const origFormatPrice = hyva.formatPrice;              // giữ reference gốc
hyva.formatPrice = function (value, showSign, options = {}) {
  if (value > 0) return origFormatPrice.apply(this, arguments);
  return 'FREE!';                                       // custom
};
```

---

## 14. Chạy JavaScript chỉ trên Mobile

Ẩn bằng CSS vẫn giữ DOM (tốn tài nguyên). Nên dùng `window.matchMedia()` + Alpine `x-if` để **gỡ hẳn element khỏi DOM**:
```js
init() {
  const mq = window.matchMedia('(max-width: 768px)');
  this.isMobile = mq.matches;
  mq.addEventListener('change', (e) => this.isMobile = e.matches);
}
```

---

## 15. View Utilities

Component dựng sẵn, tái sử dụng (PHP view model + Alpine + Tailwind, **CSP compliant**, accessible):

| Utility | Mô tả |
|---|---|
| **Loading Indicator** | Full-page loader cho async (bật/tắt bằng property `isLoading`) |
| **Custom Sliders** | Slider qua layout XML (`Hyva_Theme::elements/slider.phtml`) hoặc plugin `x-snap-slider` |
| **Modal Dialogs** | `hyva.modal()` + `\Hyva\Theme\ViewModel\Modal` — accessible (keyboard, focus, ARIA) |
| **SVG Icons** | `\Hyva\Theme\ViewModel\SvgIcons` — HeroIcons v1 (mặc định) & v2, Payment icons, pack cộng đồng |
| **reCAPTCHA** | Tích hợp cho custom form |

Ví dụ Modal:
```php
<?php $modalViewModel = $viewModels->require(\Hyva\Theme\ViewModel\Modal::class); ?>
<div x-data="hyva.modal()">
  <?= $modalViewModel->createModal()->withContent('<h1>Title</h1><p>...</p>')->positionBottom() ?>
</div>
```
Render icon:
```php
<?php $svgIcons = $viewModels->require(\Hyva\Theme\ViewModel\SvgIcons::class); ?>
<?= $svgIcons->renderIcon('heroicons/outline/check', 'w-6 h-6') ?>
```

---

## 16. Alpine CSP — Content Security Policy ⚠️ (bắt buộc PCI-DSS)

**Alpine CSP** là bản Alpine.js tuân thủ CSP, **loại bỏ `unsafe-eval`** → giảm mạnh rủi ro bảo mật. **Bắt buộc cho PCI-DSS trên trang payment (deadline 01/04/2025).**

**Vấn đề của Alpine thường:** cần `unsafe-eval` vì đánh giá biểu thức JS ngay trên HTML attribute (vd `:class="{'hidden': !open}"`) → tăng attack surface, không đạt PCI-DSS.

**Khác biệt chính của Alpine CSP:**
| | Alpine CSP |
|---|---|
| Đọc giá trị | ✅ đọc property, gọi method; ❌ không inline expression / transform |
| Mutation | ✅ chỉ trong method; ❌ không inline mutation |
| Directive | ✅ `x-if`, `x-for`, `x-text`, `x-html`, event handler; ❌ **`x-model` không hỗ trợ** |
| Khai báo state | **bắt buộc** qua constructor đăng ký bằng `Alpine.data()` |

**Chuyển từ Alpine thường → CSP:**
```html
<!-- Thường: inline init -->
<div x-data="{ open: false }">...</div>

<!-- CSP: phải đăng ký constructor -->
<div x-data="initMyComponent">...</div>
```
```js
function initMyComponent() {
  return { open: false, toggle() { this.open = !this.open; } };
}
window.addEventListener('alpine:init',
  () => Alpine.data('initMyComponent', initMyComponent), { once: true });
```
Merge object (CSP-compatible):
```js
function exampleCspComponent() {
  return Object.assign(hyva.modal.call(this), { myValue: '' });
}
window.addEventListener('alpine:init',
  () => Alpine.data('exampleCspComponent', exampleCspComponent), { once: true });
```

- Data name trong `Alpine.data()` phải **duy nhất**.
- Dùng `call()`/`apply()` khi merge object cần Alpine context.
- Code Alpine CSP **tương thích ngược** với Alpine thường → Hyvä hỗ trợ cả 2 trong giai đoạn migrate.

> Tham khảo: https://alpinejs.dev/advanced/csp · Magento 2.4.7+ siết CSP mặc định.
