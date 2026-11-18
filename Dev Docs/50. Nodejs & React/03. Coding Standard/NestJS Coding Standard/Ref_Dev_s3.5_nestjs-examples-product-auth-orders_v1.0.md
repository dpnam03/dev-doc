# NestJS Coding Standard 3.5 — Ví dụ (Product, Auth, Orders)

| Field | Value |
| :---- | :---- |
| Owner | Bắc PV — NodeJS BE Dev Lead |
| Audience | Dev (NodeJS BE) |
| Last reviewed | 2026-11-12 |
| Review cadence | Quarterly |
| Version | v1.0 |
| Linked from | Ref_Dev_nestjs-coding-standard_v1.0 |
| Status | Live |

Doc này là mục 3.5 của [NestJS Coding Standard](Ref_Dev_nestjs-coding-standard_v1.0.md), nhóm API & Data handling. Doc tóm tắt ví dụ module Product, Auth, Orders và lệnh chạy thử nhanh. Dev NodeJS BE đọc doc này khi cần một mẫu module hoàn chỉnh.

---

Các ví dụ tóm tắt về module Product, Auth, Orders và cách chạy thử nhanh.

---

## 1. Global response & exception

**1.1 Response thành công**

- Bọc response thành công: `{ data, requestId, timestamp }`.
- Service trả `PaginatedResult` thì response có thêm `meta`, đặt cạnh `data`.
- Format: [NestJS Coding Standard 3.1 — REST API Design](Ref_Dev_s3.1_nestjs-rest-api-design_v1.0.md), mục 2.4.

**1.2 Format lỗi**

- Format: `{ error: { type, code, message, param?, details?, path, requestId, timestamp } }`.
- Code `GlobalExceptionFilter`: [NestJS Coding Standard 3.3 — Exception Handling](Ref_Dev_s3.3_nestjs-exception-handling_v1.0.md), mục 2.3.

---

## 2. Ví dụ: Product (CRUD)

- Endpoints, DTOs, controller: [NestJS Coding Standard 3.1 — REST API Design](Ref_Dev_s3.1_nestjs-rest-api-design_v1.0.md), mục 3.1.
- Validation và response DTO: [NestJS Coding Standard 3.2 — Validation & Serialization](Ref_Dev_s3.2_nestjs-validation-serialization_v1.0.md), mục 3.1.

---

## 3. Ví dụ: Auth (ApiKeyGuard)

- `ApiKeyGuard` và error code `MISSING_API_KEY`, `INVALID_API_KEY`: [NestJS Coding Standard 5.1 — Authentication](Ref_Dev_s5.1_nestjs-authentication_v1.0.md), mục 2.2.
- Auth module đầy đủ (JWT, guards, decorators): cùng doc, mục 3.1.

Ví dụ:

```ts
@Get('me')
@UseGuards(ApiKeyGuard)
me() {
  // Plain data: the global interceptor wraps it. Never return the API key.
  return { ok: true };
}
```

Không trả API key trong response.

---

## 4. Ví dụ: Orders (CRUD + guard)

- Controller và DTO (`JwtAuthGuard`, Swagger): [NestJS Coding Standard 3.4 — API Documentation (OpenAPI)](Ref_Dev_s3.4_nestjs-api-documentation-openapi_v1.0.md), mục 3.1.
- Service với transaction: [NestJS Coding Standard 4.1 — Database & ORM](Ref_Dev_s4.1_nestjs-database-orm_v1.0.md), mục 3.1.
- Custom exceptions: [NestJS Coding Standard 3.3 — Exception Handling](Ref_Dev_s3.3_nestjs-exception-handling_v1.0.md), mục 3.1.

---

## 5. Chạy & test nhanh

**5.1 Cài dependency**

```bash
pnpm install
```

**5.2 Chạy app HTTP**

```bash
pnpm run start:dev
```

**5.3 Test API (Products — GET public, POST cần JWT)**

```bash
# Login once: the auth cookies (Coding Standard 5.1) are saved to cookies.txt
curl -c cookies.txt -X POST http://localhost:3000/v1/auth/login \
  -H "Content-Type: application/json" \
  -d "{\"email\":\"$EMAIL\",\"password\":\"$PASSWORD\"}"

curl -b cookies.txt -X POST http://localhost:3000/v1/products \
  -H "Content-Type: application/json" \
  -d '{"name":"Áo thun","sku":"SKU-001","price":199000}'

curl http://localhost:3000/v1/products
```

**5.4 Test API (Auth cần `x-api-key`, Orders cần JWT)**

```bash
# Auth — the key must be listed in API_KEYS
curl -H "x-api-key: sample-api-key" http://localhost:3000/v1/auth/me

# Orders
curl -b cookies.txt http://localhost:3000/v1/orders
curl -b cookies.txt -X POST http://localhost:3000/v1/orders \
  -H "Content-Type: application/json" \
  -d '{"items":[{"productId":1,"quantity":2}],"shippingAddressId":5}'
```

## Changelog

| Date | Version | Change | By |
| :---- | :---- | :---- | :---- |
| 2026-11-18 | v1.0 | Chuyển từ Notion "NestJS Document" (page `33d71a38d3b28105b027ffda64727d9f`, sửa 2026-04-09). Review và sửa nội dung, code trước khi publish. Owner duyệt trong chat ngày 2026-11-18. | Bắc PV |
