# SPF Custom App Solution Library 9 — Tutorial chính thức theo use case

| Field | Value |
| :---- | :---- |
| Owner | Bắc PV — NodeJS BE Dev Lead |
| Audience | Dev (NodeJS BE) |
| Last reviewed | 2026-11-18 |
| Review cadence | Quarterly |
| Version | v1.0 |
| Linked from | Ref_Dev_spf-custom-app-solution-library_v1.0 |
| Status | Live |

Doc này là mục 9 của [SPF Custom App Solution Library](Ref_Dev_spf-custom-app-solution-library_v1.0.md). Doc liệt kê tutorial chính thức trong [shopify.dev/docs/apps/build](https://shopify.dev/docs/apps/build) theo use case, kèm công cụ và điều kiện của từng tutorial. Dev dùng bảng này làm điểm bắt đầu khi build một giải pháp trong các doc nghiệp vụ.

## 1. Bảng tutorial

Cột "Điều kiện" ghi đúng điều kiện nêu trên trang tutorial.

| Nhóm | Tutorial | Công cụ | Điều kiện |
| :---- | :---- | :---- | :---- |
| Admin | [Build an admin action UI extension](https://shopify.dev/docs/apps/build/admin/actions-blocks/build-admin-action) | `admin.product-details.action.render`, `metafieldsSet` | `write_products` |
| Admin | [Build an admin block UI extension](https://shopify.dev/docs/apps/build/admin/actions-blocks/build-admin-block) | `admin.product-details.block.render` | `write_products` |
| Admin | [Build an admin print action UI extension](https://shopify.dev/docs/apps/build/admin/actions-blocks/build-admin-print-action) | `admin.order-details.print-action.render` | `read_orders`, xin `read_all_orders`, protected customer data |
| Admin | [Connect UI extensions to your app's backend](https://shopify.dev/docs/apps/build/admin/actions-blocks/connect-app-backend) | `fetch()` từ extension tới route của app | — |
| Admin | [Create admin link extensions](https://shopify.dev/docs/apps/build/admin/admin-links/create-admin-links) | Extension loại `admin_link` | `write_products` |
| Admin | [Admin intents](https://shopify.dev/docs/apps/build/admin/admin-intents) | `shopify.intents.invoke()` mở màn tạo, sửa của Shopify từ app | Admin UI extension API `2026-04` trở lên |
| Checkout | [Build a pre-purchase product offer](https://shopify.dev/docs/apps/build/checkout/product-offers/build-a-pre-purchase-offer) | `purchase.checkout.block.render`, `applyCartLinesChange` | Chỉ Plus |
| Checkout | [Build a post-purchase product offer](https://shopify.dev/docs/apps/build/checkout/product-offers/build-a-post-purchase-offer) | `Checkout::PostPurchase::Render` | Beta. Store live phải xin quyền. Custom app chỉ cài được trên Plus |
| Checkout | [Add a survey to Thank you and Order status pages](https://shopify.dev/docs/apps/build/checkout/thank-you-order-status/add-survey) | `purchase.thank-you.block.render`, `customer-account.order-status.block.render` | Mọi plan trừ Starter |
| Checkout | [Add a banner to checkout](https://shopify.dev/docs/apps/build/checkout/fields-banners/add-banner) | `purchase.checkout.block.render` | Chỉ Plus |
| Checkout | [Add a field to checkout](https://shopify.dev/docs/apps/build/checkout/fields-banners/add-field) | `purchase.checkout.shipping-option-list.render-after`, `applyMetafieldChange` | Chỉ Plus |
| Checkout | [Build customized address autocomplete](https://shopify.dev/docs/apps/build/checkout/delivery-shipping/address-autocomplete/build-autocomplete) | `purchase.address-autocomplete.suggest` | Plus, protected customer data |
| Checkout | [Build a date picker for a specific shipping rate](https://shopify.dev/docs/apps/build/checkout/delivery-shipping/delivery-methods/date-picker) | `purchase.checkout.shipping-option-list.render-after` | Chỉ Plus |
| Checkout | [Checkout and Accounts Configuration API](https://shopify.dev/docs/apps/build/checkout/styling/checkout-and-accounts-configuration) | `checkoutAndAccountsConfigurationUpdate` | Chỉ Plus |
| Checkout | [Create cart permalinks](https://shopify.dev/docs/apps/build/checkout/create-cart-permalinks) | Link dẫn thẳng tới checkout với cart dựng sẵn | Không dùng với selling plan |
| Function | [Create checkout validation](https://shopify.dev/docs/apps/build/checkout/cart-checkout-validation/create-checkout-validation) | `cart.validations.generate.run` | Function API `2025-07` trở lên |
| Function | [Create an admin UI extension for a validation function](https://shopify.dev/docs/apps/build/checkout/cart-checkout-validation/create-admin-ui-validation) | `admin.settings.validation.render` | `read_products` |
| Function | [Create the payments function](https://shopify.dev/docs/apps/build/checkout/payments/create-payments-function) | `cart.payment-methods.transform.run`, `paymentCustomizationCreate` | Ẩn theo placement chỉ có trên Plus |
| Function | [Set payment terms](https://shopify.dev/docs/apps/build/checkout/payments/payment-terms) | `paymentTermsSet` | Chỉ Plus |
| Function | [Build the delivery options function](https://shopify.dev/docs/apps/build/checkout/delivery-shipping/delivery-options/build-function) | `cart.delivery-options.transform.run`, `deliveryCustomizationCreate` | Function API `2025-07` trở lên |
| Function | [Generate pickup points](https://shopify.dev/docs/apps/build/checkout/delivery-shipping/delivery-methods/generate-pickup-points) | Pickup Point Delivery Option Generator | Chỉ custom app trên dev store hoặc Plus, early access |
| Function | [Build a fulfillment constraints function](https://shopify.dev/docs/apps/build/orders-fulfillment/order-routing-apps/build-fulfillment-constraints-function) | `fulfillmentConstraintRuleCreate` | `write_fulfillment_constraint_rules` |
| Discount | [Build a Discount Function](https://shopify.dev/docs/apps/build/discounts/build-discount-function) | `cart.lines.discounts.generate.run`, `discountAutomaticAppCreate` | `write_discounts`, `read_products` |
| Discount | [Build a discounts UI with admin UI extensions](https://shopify.dev/docs/apps/build/discounts/build-ui-extension) | `admin.discount-details.function-settings.render` | `write_discounts`, `read_products` |
| Discount | [Build a Discount Function that has network access](https://shopify.dev/docs/apps/build/discounts/network-access) | `cart.lines.discounts.generate.fetch` | Chỉ plan Enterprise |
| Customer account | [Build an inline order status UI extension](https://shopify.dev/docs/apps/build/customer-accounts/inline-extensions/build-order-status) | `customer-account.order-status.block.render` | Chỉ customer accounts mới |
| Customer account | [Build for order action menus](https://shopify.dev/docs/apps/build/customer-accounts/order-action-extensions/build-for-order-action-menus) | `customer-account.order.action.menu-item.render` | `customer_read_customers`, `customer_read_orders` |
| Customer account | [Build an inline profile UI extension](https://shopify.dev/docs/apps/build/customer-accounts/inline-extensions/build-profile) | `customer-account.profile.block.render` | — |
| Customer account | [Build new pages in customer accounts](https://shopify.dev/docs/apps/build/customer-accounts/full-page-extensions/build-new-pages) | `customer-account.page.render` | — |
| Customer account | [Build self-serve returns](https://shopify.dev/docs/apps/build/orders-fulfillment/returns-apps/build-self-serve-returns) | `orderRequestReturn`, `returnCalculate` | Customer Account API `2025-04` trở lên, protected customer data |
| Online store | [Build theme app extensions](https://shopify.dev/docs/apps/build/online-store/theme-app-extensions/build) | App block, app embed block | Theme Online Store 2.0 |
| Online store | [App proxies](https://shopify.dev/docs/apps/build/online-store/app-proxies) | App proxy | `write_app_proxy` |
| POS | [Getting started with POS UI extensions](https://shopify.dev/docs/apps/build/pos/getting-started) | Tile ở smart grid và modal | — |
| POS | [Build a print UI extension](https://shopify.dev/docs/apps/build/pos/tutorials/build-print-extension) | `pos.home.tile.render`, `shopify.print.print()` | — |
| POS | [Build a discount UI extension](https://shopify.dev/docs/apps/build/pos/tutorials/build-discount-extension) | `shopify.cart.applyCartDiscount` | — |
| Product | [Add a customized bundle function](https://shopify.dev/docs/apps/build/product-merchandising/bundles/add-customized-bundle-function) | Cart Transform Function, `cartTransformCreate` | `write_cart_transforms`, `write_products` |
| Product | [Create and query nested cart lines](https://shopify.dev/docs/apps/build/product-merchandising/nested-cart-lines/create-nested-cart-lines) | Storefront `cartLinesAdd` với `parent` | API `2025-10` trở lên |
| Product | [Build for combined listings](https://shopify.dev/docs/apps/build/product-merchandising/combined-listings/build-for-combined-listings) | `productSet`, `combinedListingUpdate` | Chỉ Plus |
| Purchase option | [Build a selling plan](https://shopify.dev/docs/apps/build/purchase-options/subscriptions/selling-plans/build-a-selling-plan) | `sellingPlanGroupCreate` | Phải xin API access |
| Purchase option | [Build a subscription contract](https://shopify.dev/docs/apps/build/purchase-options/subscriptions/contracts/build-a-subscription-contract) | `subscriptionContractCreateCalculate`, `subscriptionBillingAttemptCreate` | Phải xin API access, Admin API `2026-10` trở lên |
| Purchase option | [Build a Pre-order and Try Before You Buy solution](https://shopify.dev/docs/apps/build/purchase-options/deferred/build-deferment-solution) | `sellingPlanGroupCreate` | Phải xin API access. Không chạy trên POS |
| Markets | [Build a catalog](https://shopify.dev/docs/apps/build/markets/build-catalog) | `priceListCreate`, `priceListFixedPricesAdd` | `write_products` |
| Markets | [Manage translations](https://shopify.dev/docs/apps/build/markets/manage-translated-content) | `translationsRegister`, `shopLocaleEnable` | `write_translations`, `write_locales` |
| B2B | [Start building for B2B](https://shopify.dev/docs/apps/build/b2b/start-building) | `companyCreate`, `catalogCreate`, `draftOrderCreate` | Plan có B2B |
| B2B | [Use draft orders](https://shopify.dev/docs/apps/build/b2b/draft-orders) | `draftOrderCalculate`, `draftOrderCreate`, `draftOrderComplete` | `write_draft_orders` |
| Đơn hàng | [Edit existing orders](https://shopify.dev/docs/apps/build/orders-fulfillment/order-management-apps/edit-orders) | `orderEditBegin` đến `orderEditCommit` | `write_order_edits` |
| Đơn hàng | [Build fulfillment solutions](https://shopify.dev/docs/apps/build/orders-fulfillment/order-management-apps/build-fulfillment-solutions) | `fulfillmentOrderMove`, `fulfillmentCreate` | Scope fulfillment order, protected customer data |
| Đơn hàng | [Build for fulfillment services](https://shopify.dev/docs/apps/build/orders-fulfillment/fulfillment-service-apps/build-for-fulfillment-services) | `fulfillmentServiceCreate` | `write_fulfillments`, `write_assigned_fulfillment_orders` |
| Đơn hàng | [Build for return management](https://shopify.dev/docs/apps/build/orders-fulfillment/returns-apps/build-return-management) | `returnRequest`, `returnCreate`, `returnProcess` | — |
| Marketing | [Build web pixels](https://shopify.dev/docs/apps/build/marketing-analytics/build-web-pixels) | `web_pixel_extension`, `webPixelCreate` | `write_pixels`, `read_customer_events` |
| Flow | [Create a Flow trigger](https://shopify.dev/docs/apps/build/flow/triggers/create) | `flow_trigger`, `flowTriggerReceive` | Với custom app: chỉ store Plus |
| Flow | [Create a Flow action](https://shopify.dev/docs/apps/build/flow/actions/create) | `flow_action` | Với custom app: chỉ store Plus |

## References

- [Build apps trên shopify.dev](https://shopify.dev/docs/apps/build)

## Changelog

| Date | Version | Change | By |
| :---- | :---- | :---- | :---- |
| 2026-11-18 | v1.0 | Bản đầu tiên. Owner duyệt trong chat ngày 2026-11-18. | Bắc PV |
