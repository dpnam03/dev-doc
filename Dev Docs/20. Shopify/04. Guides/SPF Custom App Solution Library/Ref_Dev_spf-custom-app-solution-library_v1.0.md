# SPF Custom App Solution Library

| Field | Value |
| :---- | :---- |
| Owner | Bắc PV — NodeJS BE Dev Lead |
| Audience | Dev (NodeJS BE) |
| Last reviewed | 2026-11-18 |
| Review cadence | Quarterly |
| Version | v1.0 |
| Linked from | Ref_Dev_shopify-custom-app-overview_v1.0 |
| Status | Live |

SPF Custom App Solution Library là bộ doc tra giải pháp cho yêu cầu của khách trong dự án Shopify custom app, gồm 15 doc. Với từng nghiệp vụ, bộ doc nêu tính năng mặc định của Shopify, các yêu cầu tùy chỉnh, và giải pháp kèm ràng buộc cho từng yêu cầu. Doc này liệt kê các doc, nêu cách tra cứu và điều kiện chung. Tổng quan về từng surface và công cụ nằm ở [Shopify Custom App — Tổng quan](Ref_Dev_shopify-custom-app-overview_v1.0.md).

## 1. Danh sách doc

| Mục | Nhóm nghiệp vụ | Doc | Số yêu cầu |
| :---- | :---- | :---- | :---- |
| 1.1 | Giá và khuyến mãi | [Discount](Ref_Dev_s1.1_spf-solution-discounts_v1.0.md) | 14 |
| 1.2 | Giá và khuyến mãi | [Giá bán](Ref_Dev_s1.2_spf-solution-pricing_v1.0.md) | 5 |
| 2.1 | Checkout và thanh toán | [Phương thức thanh toán](Ref_Dev_s2.1_spf-solution-payment_v1.0.md) | 8 |
| 2.2 | Checkout và thanh toán | [Field và rule trong checkout](Ref_Dev_s2.2_spf-solution-checkout-fields-validation_v1.0.md) | 11 |
| 2.3 | Checkout và thanh toán | [Nội dung checkout và trang Thank you](Ref_Dev_s2.3_spf-solution-checkout-content_v1.0.md) | 7 |
| 3.1 | Vận chuyển và fulfillment | [Phí ship và phương thức giao](Ref_Dev_s3.1_spf-solution-shipping-rates-delivery_v1.0.md) | 13 |
| 3.2 | Vận chuyển và fulfillment | [Fulfillment và kho](Ref_Dev_s3.2_spf-solution-fulfillment-inventory_v1.0.md) | 6 |
| 4.1 | Đơn hàng, tích hợp và vận hành admin | [Tích hợp với hệ thống ngoài](Ref_Dev_s4.1_spf-solution-integration_v1.0.md) | 7 |
| 4.2 | Đơn hàng, tích hợp và vận hành admin | [Vận hành trong admin](Ref_Dev_s4.2_spf-solution-admin-operations_v1.0.md) | 17 |
| 5.1 | Khách hàng, B2B và subscription | [Tài khoản khách và loyalty](Ref_Dev_s5.1_spf-solution-customer-accounts-loyalty_v1.0.md) | 16 |
| 5.2 | Khách hàng, B2B và subscription | [B2B và subscription](Ref_Dev_s5.2_spf-solution-b2b-subscription_v1.0.md) | 10 |
| 6 | Storefront và catalog | [Storefront và catalog](Ref_Dev_s6_spf-solution-storefront-catalog_v1.0.md) | 24 |
| 7 | Tracking và SEO | [Tracking và SEO](Ref_Dev_s7_spf-solution-tracking-seo_v1.0.md) | 5 |
| 8 | POS | [POS](Ref_Dev_s8_spf-solution-pos_v1.0.md) | 7 |
| 9 | Tutorial chính thức theo use case | [Tutorial chính thức theo use case](Ref_Dev_s9_spf-solution-official-tutorials_v1.0.md) | — |

Tổng cộng 150 yêu cầu trong 14 doc nghiệp vụ.

## 2. Cách tra cứu

Mỗi doc nghiệp vụ (mục 1.1 đến mục 8) có 3 phần và References:

- **Tính năng mặc định**: tính năng native của Shopify và giới hạn. Đọc phần này trước để biết yêu cầu có cần app hay không.
- **Yêu cầu tùy chỉnh**: từng yêu cầu mà tính năng mặc định không đáp ứng, kèm giải pháp.
- **Ràng buộc kỹ thuật**: giới hạn của công cụ và các trường hợp không hỗ trợ.
- **References**: trang Shopify đã đọc.

Cuối mục Yêu cầu tùy chỉnh của một số doc có hình minh họa lấy từ shopify.dev. File ảnh nằm ở folder `images/`.

Cột của bảng yêu cầu:

- **Yêu cầu**: yêu cầu của khách.
- **Giới hạn mặc định**: lý do tính năng native không đáp ứng.
- **Giải pháp**: surface, công cụ, target, mutation.
- **Ràng buộc / fallback**: plan, scope, giới hạn số lượng, và phương án cho store non-Plus.
- **Public app**: app trên Shopify App Store có listing ghi đáp ứng yêu cầu. "Một phần" nghĩa là listing chỉ đáp ứng một phần.

Bộ doc chưa ghi dự án nào đã làm các giải pháp này. Làm PoC trước khi báo giá cho khách.

Yêu cầu chưa có trong bảng thì thêm dòng mới vào đúng doc nghiệp vụ.

Cột Public app lấy từ apps.shopify.com ngày 2026-11-18:

- Mỗi yêu cầu ghi tối đa 2 app. Thứ tự ưu tiên: app của Shopify, app có badge Built for Shopify, app có rating từ 4.5 và nhiều review.
- Yêu cầu gắn với một nền tảng (Google, Meta, TikTok, HubSpot, Odoo, ZaloPay, Klaviyo, Mailchimp) ghi app chính chủ của nền tảng đó trước. App chính chủ không tính vào giới hạn 2 app.
- Developer, rating, số review và badge Built for Shopify của từng app đọc từ listing ngày 2026-11-18. App chưa có review, dưới 10 review hoặc rating dưới 4.0 có ghi chú trong ô.
- Không tìm thấy app chính chủ của Zalo, KiotViet, Sapo, MISA, SAP, GHN, GHTK, Viettel Post, J&T Việt Nam, VNPay, MoMo, Slack.
- Team chưa dùng thử các app này. Kiểm tra giá, plan và tính năng trên listing trước khi đề xuất cho khách.
- "Không tìm thấy" nghĩa là hai lượt tìm trên App Store không ra app phù hợp.

Nội dung kỹ thuật lấy từ shopify.dev và help.shopify.com, đọc ngày 2026-11-18, API version `2026-10`. Tên target, mutation và scope được trích qua công cụ đọc trang có tóm tắt. Kiểm tra lại trên trang gốc trước khi đưa vào spec. Chỗ ghi "chưa xác nhận" là chỗ không tìm thấy trên trang chính thức.

## 3. Điều kiện chung

Kiểm tra các điều kiện sau trước khi chọn giải pháp:

- Custom app chứa Shopify Function chỉ chạy trên store Shopify Plus. Public app chứa Function chạy trên mọi plan nhưng phải qua duyệt của Shopify.
- Checkout UI extension ở bước information, shipping, payment chỉ có trên Plus. Extension ở trang Thank you, Order status và customer account chạy từ Basic trở lên.
- Flow trigger và action của custom app chỉ dùng được trên store Plus.
- Function không gọi được API ngoài, trừ custom app trên store Enterprise.
- Các công cụ sau chạy trên mọi plan: theme app extension, app proxy, webhook, Admin API, admin UI extension, web pixel.
- Đọc dữ liệu cá nhân của khách cần protected customer data. Custom app tạo trong Dev Dashboard có sẵn level 1 và 2.
- Custom app cài lên store ngoài organization của team cần IP allowlist từ 2026-11-20.

## 4. App first-party của Shopify

Các app dưới đây do Shopify làm. Kiểm tra app có đáp ứng yêu cầu không trước khi đề xuất build custom app.

| App | Phạm vi | Giới hạn |
| :---- | :---- | :---- |
| [Shopify Flow](https://apps.shopify.com/flow) | Workflow tự động: gắn tag, hold đơn, hủy đơn, gửi cảnh báo | Send HTTP request cần Grow trở lên |
| [Checkout Blocks](https://apps.shopify.com/checkout-blocks) | Custom field, payment và delivery customization, giới hạn giá trị đơn, content block | Đủ tính năng chỉ trên Plus. Plan khác chỉ có content block ở Thank you, Order status |
| Shopify Bundles | Fixed bundle, multipack | 30 component, không có mix-and-match, không dùng với subscription |
| Shopify Subscriptions | Subscription theo tuần, tháng, năm | Phụ thuộc cổng thanh toán được hỗ trợ |
| Shopify Search & Discovery | Filter, gợi ý sản phẩm | 25 filter mỗi store |
| Shopify Forms | Form popup, inline, form đăng ký company B2B | 31 field mỗi form |
| Shopify Translate & Adapt | Dịch nội dung store | Dịch tự động 2 ngôn ngữ với store Việt Nam |
| Shopify Order Printer | Invoice, packing slip, pick list theo template | 50 đơn mỗi lần in. Listing trên App Store ghi app hiện không khả dụng (2026-11-18) |
| Shopify Combined Listings | Gộp nhiều product thành một listing | Chỉ Plus |

## References

- [Build apps trên shopify.dev](https://shopify.dev/docs/apps/build): danh mục use case và tutorial
- [Shopify Functions](https://shopify.dev/docs/apps/build/functions): điều kiện Plus với custom app
- [Checkout technologies](https://shopify.dev/docs/apps/build/checkout/technologies): plan của từng loại checkout extension
- [Access scopes](https://shopify.dev/docs/api/usage/access-scopes): scope nào phải xin
- [Shopify Help Center](https://help.shopify.com/en/manual): tính năng có sẵn cho merchant
- [Shopify App Store](https://apps.shopify.com): nguồn của cột Public app

## Changelog

| Date | Version | Change | By |
| :---- | :---- | :---- | :---- |
| 2026-11-18 | v1.0 | Tách 5 doc vượt cap 2.000 từ (mục 1 đến mục 5) thành 11 doc con, đánh số mục 1.1 đến mục 5.2. Thêm cột Nhóm nghiệp vụ vào mục 1. Thêm rule app chính chủ cho cột Public app ở mục 2. Bỏ cột Trạng thái khỏi bảng yêu cầu. Kiểm tra developer và số review của các app ở cột Public app. Thêm 26 hình minh họa từ shopify.dev vào 13 doc nghiệp vụ. Owner duyệt trong chat ngày 2026-11-18. | Bắc PV |
| 2026-11-18 | v1.0 | Viết lại theo nghiệp vụ và tách thành 9 doc: 8 doc nghiệp vụ với 150 yêu cầu và 1 doc tutorial. Doc này giữ danh sách doc, cách tra cứu, điều kiện chung và bảng app first-party. Thêm cột Public app. Owner duyệt trong chat ngày 2026-11-18. | Bắc PV |
| 2026-11-12 | v1.0 | Chuyển lên Live. Owner duyệt trong chat ngày 2026-11-12. | Bắc PV |
| 2026-11-12 | v0.1 | Draft đầu tiên. | Bắc PV |
