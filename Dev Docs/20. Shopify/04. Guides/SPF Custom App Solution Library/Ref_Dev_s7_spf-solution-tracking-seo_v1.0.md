# SPF Custom App Solution Library 7 — Tracking và SEO

| Field | Value |
| :---- | :---- |
| Owner | Bắc PV — NodeJS BE Dev Lead |
| Audience | Dev (NodeJS BE) |
| Last reviewed | 2026-11-18 |
| Review cadence | Quarterly |
| Version | v1.0 |
| Linked from | Ref_Dev_spf-custom-app-solution-library_v1.0 |
| Status | Live |

Doc này là mục 7 của [SPF Custom App Solution Library](Ref_Dev_spf-custom-app-solution-library_v1.0.md), nghiệp vụ tracking và SEO. Doc nêu tính năng mặc định của Shopify, các yêu cầu tùy chỉnh kèm giải pháp, và ràng buộc kỹ thuật. Cách đọc các cột và điều kiện chung nằm ở [doc index](Ref_Dev_spf-custom-app-solution-library_v1.0.md).

## 1. Tính năng mặc định

| Tính năng | Mô tả | Giới hạn |
| :---- | :---- | :---- |
| Pixel | App pixel và custom pixel, quản lý ở Customer events | Custom pixel chạy trong sandbox, Shopify không hỗ trợ khi lỗi |
| Meta | App Meta: mức Standard chỉ có pixel, mức Enhanced và Maximum có thêm Conversions API | TikTok: chưa xác nhận |
| Cookie banner | Cài ở Settings > Customer privacy, hiện ở storefront, cart, checkout, customer account | Chỉ điều khiển công cụ của Shopify. Banner bên thứ ba phải đồng bộ qua Customer Privacy API |
| Structured data | Filter `structured_data` | Chỉ có cho Product, ProductGroup, Article |

## 2. Yêu cầu tùy chỉnh

| Yêu cầu | Giới hạn mặc định | Giải pháp | Ràng buộc | Public app |
| :---- | :---- | :---- | :---- | :---- |
| Tracking server-side: Meta CAPI, TikTok Events API, GA4 | App Meta: CAPI ở mức Enhanced, Maximum. Kênh khác: chưa xác nhận | Web pixel extension → event về backend app. Event mua hàng: từ webhook `orders/paid` | Scope `write_pixels`, `read_customer_events`. Bật pixel: `webPixelCreate` | [Facebook & Instagram](https://apps.shopify.com/facebook) (app của Meta: CAPI theo mục 1, listing chỉ ghi pixel, rating 3.9/5, 5886 review). [TikTok](https://apps.shopify.com/tiktok) (app của TikTok: listing chỉ ghi pixel). [Google & YouTube](https://apps.shopify.com/google) (app của Google: listing chỉ ghi conversion tracking). Bên thứ ba, listing ghi server-side: [TagFly](https://apps.shopify.com/tagfly), [Multifeed Google Shopping Feed](https://apps.shopify.com/multiple-google-shopping-feeds) |
| Custom event cho pixel | Custom pixel không truy cập được DOM, top frame | Gọi `Shopify.analytics.publish` từ theme hoặc theme app extension | Chỉ publish được custom event, không publish standard event | [Trackify](https://apps.shopify.com/trackify-1) (một phần: listing chỉ nêu tên tính năng) |
| Tracking theo consent | Banner Shopify: chỉ điều khiển công cụ Shopify | Customer Privacy API: `setTrackingConsent`, `visitorConsentCollected`. Khai báo `customer_privacy` trong TOML pixel. Banner riêng: app embed target `compliance_head` | Không gọi được Customer Privacy API từ bên trong web pixel extension | [Pandectes GDPR Compliance](https://apps.shopify.com/gdpr-cookie-consent). [Avada GDPR Cookie Consent](https://apps.shopify.com/avada-cookie-bar) |
| Feed sản phẩm cho Google, Facebook theo rule riêng | App của Google, Meta: đồng bộ product sang Merchant Center, shop Facebook, Instagram. Listing không ghi rule riêng | `productFeedCreate`, scope `read_product_listings`. Kèm webhook `product_feeds/incremental_sync`, `product_feeds/full_sync` | Trang API không ghi yêu cầu về sales channel | [Google & YouTube](https://apps.shopify.com/google) (app của Google, không ghi rule riêng). [Facebook & Instagram](https://apps.shopify.com/facebook) (app của Meta, không ghi rule riêng, rating 3.9/5, 5886 review). Bên thứ ba, listing ghi rule riêng: [Multifeed Google Shopping Feed](https://apps.shopify.com/multiple-google-shopping-feeds), [Mulwi Shopping Feeds](https://apps.shopify.com/mulwi-shopping-feeds) |
| Structured data riêng, redirect hàng loạt | `structured_data`: chỉ 3 loại | JSON-LD trong app embed target `head`. Redirect: `urlRedirectImportCreate` → `urlRedirectImportSubmit`, scope `write_online_store_navigation` | — | [SearchPie: SEO, AI & Schema](https://apps.shopify.com/seo-booster) (phần schema). [Redirect Hero](https://apps.shopify.com/redirect-hero) (phần redirect) |

## 3. Ràng buộc kỹ thuật

- App pixel chạy trong strict sandbox (web worker). Custom pixel chạy trong lax sandbox (iframe). Cả hai không truy cập được DOM.
- Pixel có 15 standard event, gồm `page_viewed`, `product_viewed`, `product_added_to_cart`, `checkout_started`, `payment_info_submitted`, `checkout_completed`.
- Setting của pixel chỉ hỗ trợ kiểu `single_line_text_field`.
- Ở vùng yêu cầu opt-in, callback của pixel chỉ chạy sau khi khách đồng ý.

## References

- [Web pixels](https://shopify.dev/docs/apps/build/marketing-analytics/pixels) và [build web pixel](https://shopify.dev/docs/apps/build/marketing-analytics/build-web-pixels)
- [Standard events](https://shopify.dev/docs/api/web-pixels-api/standard-events)
- [Customer Privacy API](https://shopify.dev/docs/api/customer-privacy)

## Changelog

| Date | Version | Change | By |
| :---- | :---- | :---- | :---- |
| 2026-11-18 | v1.0 | Bản đầu tiên. Owner duyệt trong chat ngày 2026-11-18. | Bắc PV |
