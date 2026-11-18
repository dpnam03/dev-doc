# NestJS Coding Standard

| Field | Value |
| :---- | :---- |
| Owner | Bắc PV — NodeJS BE Dev Lead |
| Audience | Dev (NodeJS BE) |
| Last reviewed | 2026-11-12 |
| Review cadence | Quarterly |
| Version | v1.0 |
| Linked from | Các doc chủ đề của NestJS Coding Standard (28 doc) |
| Status | Live |

NestJS Coding Standard là bộ chuẩn code NestJS của team NodeJS BE, gồm 28 doc chủ đề. Dev dùng bộ chuẩn này để thống nhất cách viết code, review code và onboarding member mới. Doc này liệt kê các chủ đề và cấu trúc chung của từng doc.

## 1. Cấu trúc mỗi doc chủ đề

Mỗi doc chủ đề có header, đoạn mục đích, phần thân đánh số và Changelog theo Foundation 0 — How this KB Works. Phần thân gồm 4 phần:

1. **Tóm tắt & Phạm vi**: chủ đề giải quyết vấn đề gì, áp dụng cho scope nào
2. **Quy tắc & Giải thích**: nên làm (✅) / không nên làm (❌), mỗi quy tắc có lý do và code ví dụ
3. **Ví dụ minh họa thực tế**: walkthrough một feature thật, before/after
4. **Tooling & Config**: setup, config file, automation

Sau phần thân là References. Doc 3.5 là trang ví dụ, không theo cấu trúc này.

## 2. Danh sách doc

| Mục | Doc | Nhóm |
| :---- | :---- | :---- |
| 1.1 | [NestJS Coding Standard 1.1 — Cấu trúc dự án](Ref_Dev_s1.1_nestjs-project-structure_v1.0.md) | 1. Nền tảng NestJS |
| 1.2 | [NestJS Coding Standard 1.2 — Request Lifecycle](Ref_Dev_s1.2_nestjs-request-lifecycle_v1.0.md) | 1. Nền tảng NestJS |
| 1.3 | [NestJS Coding Standard 1.3 — Coding conventions (phần 1)](Ref_Dev_s1.3_nestjs-coding-conventions-part-1_v1.0.md) | 1. Nền tảng NestJS |
| 1.4 | [NestJS Coding Standard 1.4 — Project Setup & Build](Ref_Dev_s1.4_nestjs-project-setup-build_v1.0.md) | 1. Nền tảng NestJS |
| 1.5 | [NestJS Coding Standard 1.5 — Coding conventions (phần 2)](Ref_Dev_s1.5_nestjs-coding-conventions-part-2_v1.0.md) | 1. Nền tảng NestJS |
| 2.1 | [NestJS Coding Standard 2.1 — Configuration & Environment Management](Ref_Dev_s2.1_nestjs-configuration-environment_v1.0.md) | 2. Configuration & Environment |
| 3.1 | [NestJS Coding Standard 3.1 — REST API Design](Ref_Dev_s3.1_nestjs-rest-api-design_v1.0.md) | 3. API & Data handling |
| 3.2 | [NestJS Coding Standard 3.2 — Validation & Serialization](Ref_Dev_s3.2_nestjs-validation-serialization_v1.0.md) | 3. API & Data handling |
| 3.3 | [NestJS Coding Standard 3.3 — Exception Handling](Ref_Dev_s3.3_nestjs-exception-handling_v1.0.md) | 3. API & Data handling |
| 3.4 | [NestJS Coding Standard 3.4 — API Documentation (OpenAPI)](Ref_Dev_s3.4_nestjs-api-documentation-openapi_v1.0.md) | 3. API & Data handling |
| 3.5 | [NestJS Coding Standard 3.5 — Ví dụ (Product, Auth, Orders)](Ref_Dev_s3.5_nestjs-examples-product-auth-orders_v1.0.md) | 3. API & Data handling |
| 4.1 | [NestJS Coding Standard 4.1 — Database & ORM](Ref_Dev_s4.1_nestjs-database-orm_v1.0.md) | 4. Database |
| 4.2 | [NestJS Coding Standard 4.2 — Caching](Ref_Dev_s4.2_nestjs-caching_v1.0.md) | 4. Database |
| 5.1 | [NestJS Coding Standard 5.1 — Authentication](Ref_Dev_s5.1_nestjs-authentication_v1.0.md) | 5. Security |
| 5.2 | [NestJS Coding Standard 5.2 — Authorization](Ref_Dev_s5.2_nestjs-authorization_v1.0.md) | 5. Security |
| 5.3 | [NestJS Coding Standard 5.3 — Security Best Practices](Ref_Dev_s5.3_nestjs-security-best-practices_v1.0.md) | 5. Security |
| 6.1 | [NestJS Coding Standard 6.1 — Task Scheduling & Queues](Ref_Dev_s6.1_nestjs-task-scheduling-queues_v1.0.md) | 6. Async & Integration |
| 6.2 | [NestJS Coding Standard 6.2 — Event System](Ref_Dev_s6.2_nestjs-event-system_v1.0.md) | 6. Async & Integration |
| 6.3 | [NestJS Coding Standard 6.3 — HTTP Client & Third-party Integration](Ref_Dev_s6.3_nestjs-http-client-integration_v1.0.md) | 6. Async & Integration |
| 6.4 | [NestJS Coding Standard 6.4 — WebSockets & Real-time](Ref_Dev_s6.4_nestjs-websockets-realtime_v1.0.md) | 6. Async & Integration |
| 6.5 | [NestJS Coding Standard 6.5 — Microservices & Message Queues](Ref_Dev_s6.5_nestjs-microservices-message-queues_v1.0.md) | 6. Async & Integration |
| 7.1 | [NestJS Coding Standard 7.1 — Logging](Ref_Dev_s7.1_nestjs-logging_v1.0.md) | 7. Observability |
| 7.2 | [NestJS Coding Standard 7.2 — Debugging](Ref_Dev_s7.2_nestjs-debugging_v1.0.md) | 7. Observability |
| 7.3 | [NestJS Coding Standard 7.3 — Monitoring & Observability](Ref_Dev_s7.3_nestjs-monitoring-observability_v1.0.md) | 7. Observability |
| 8.1 | [NestJS Coding Standard 8.1 — Testing](Ref_Dev_s8.1_nestjs-testing_v1.0.md) | 8. Testing |
| 9.1 | [NestJS Coding Standard 9.1 — Performance & Resource Management](Ref_Dev_s9.1_nestjs-performance-resource-management_v1.0.md) | 9. Performance & Operations |
| 9.2 | [NestJS Coding Standard 9.2 — Streams & File Handling](Ref_Dev_s9.2_nestjs-streams-file-handling_v1.0.md) | 9. Performance & Operations |
| 9.3 | [NestJS Coding Standard 9.3 — Build & Deployment](Ref_Dev_s9.3_nestjs-build-deployment_v1.0.md) | 9. Performance & Operations |

## 3. Version mục tiêu

Code trong bộ chuẩn viết cho NestJS 11, Node ≥22.12 và Jest, giống project v535. Docker image dùng `node:22-alpine`, CI dùng `node-version: 22`.

Code ví dụ chưa được kiểm tra hết trên NestJS 12. Jest config ở [NestJS Coding Standard 8.1 — Testing](Ref_Dev_s8.1_nestjs-testing_v1.0.md) chỉ chạy với NestJS 11: NestJS 12 chỉ có bản ESM, Jest cần Node ≥24.9 mới load được.

## Changelog

| Date | Version | Change | By |
| :---- | :---- | :---- | :---- |
| 2026-11-18 | v1.0 | Chuyển từ README theo format Foundation 0 v3.0. Review và sửa nội dung, code trước khi publish. Owner duyệt trong chat ngày 2026-11-18. | Bắc PV |
