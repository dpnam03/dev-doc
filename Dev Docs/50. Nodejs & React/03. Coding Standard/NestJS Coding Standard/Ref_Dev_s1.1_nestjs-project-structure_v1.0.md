# NestJS Coding Standard 1.1 — Cấu trúc dự án

| Field | Value |
| :---- | :---- |
| Owner | Bắc PV — NodeJS BE Dev Lead |
| Audience | Dev (NodeJS BE) |
| Last reviewed | 2026-11-12 |
| Review cadence | Quarterly |
| Version | v1.0 |
| Linked from | Ref_Dev_nestjs-coding-standard_v1.0 |
| Status | Live |

Doc này là mục 1.1 của [NestJS Coding Standard](Ref_Dev_nestjs-coding-standard_v1.0.md), nhóm Nền tảng NestJS. Doc nêu quy tắc về Cấu trúc dự án trong dự án NestJS, kèm lý do, ví dụ và config. Dev NodeJS BE đọc doc này khi viết code, review code và onboarding.

---

## 1. Tóm tắt & Phạm vi

Tài liệu này mô tả **kiến trúc tổng thể** và **cấu trúc thư mục chuẩn** cho dự án NestJS. Cấu trúc lấy theo thư mục `server/` của project v535, giống doc "Khởi tạo project NodeJS với NestJS" của team. Mục tiêu là thống nhất cách tổ chức code để dễ review, dễ mở rộng, và onboarding nhanh.

### 1.1. Scope áp dụng

- Toàn bộ code runtime của ứng dụng NestJS: process HTTP API, process worker, và các thư mục tài liệu, cấu hình liên quan.
- Không áp dụng cho service độc lập tách repo riêng (ví dụ: MCP server).

---

## 2. Quy tắc & Giải thích

### 2.1. Cấu trúc tổng thể tại thư mục gốc

✅ **Nên làm** — Tổ chức dự án theo khung sau:

| **Thư mục / file** | **Mục đích** | **Ghi chú** |
| --- | --- | --- |
| `src/main.ts`, `src/app.module.ts` | Process HTTP API | Đăng ký global pipes, interceptors, filters, guards; import các `*-api.module.ts` |
| `src/worker.ts`, `src/worker.module.ts` | Process riêng chạy cron và background job | Job nặng không làm chậm API, xem [NestJS Coding Standard 6.1 — Task Scheduling & Queues](Ref_Dev_s6.1_nestjs-task-scheduling-queues_v1.0.md) |
| `src/api/<caller>/` | Controller, chia theo đối tượng gọi API: `user/`, `admin/`, `public/`, `webhook/`, `system/` | Mỗi thư mục có một `<caller>-api.module.ts`. Không chứa business logic |
| `src/modules/<feature>/` | Business logic của từng feature: service, repository, DTO, exception, event handler | Không chứa controller |
| `src/contracts/<name>/` | Abstract class dùng chung giữa các module: gửi mail, lưu file, transaction | Không import từ `modules/` hay `infra/` |
| `src/infra/<name>/` | Implement contract bằng dịch vụ bên ngoài: Prisma, mail, logger, HTTP client | Module không import trực tiếp |
| `src/common/` | Building blocks ở mức framework: filters, guards, interceptors, pipes, decorators | **Không chứa logic nghiệp vụ** |
| `src/config/` | Config theo namespace (`registerAs`) và validation schema của env | Xem [NestJS Coding Standard 2.1 — Configuration & Environment Management](Ref_Dev_s2.1_nestjs-configuration-environment_v1.0.md) |
| `prisma/` | `schema.prisma` và `migrations/` | Chỉ có khi project dùng Prisma. v535 (Prisma 6) đặt schema ở `src/infra/prisma/`; Prisma 7 đọc đường dẫn từ `prisma.config.ts`, xem [NestJS Coding Standard 4.1 — Database & ORM](Ref_Dev_s4.1_nestjs-database-orm_v1.0.md) |
| `docs/` | Tài liệu kỹ thuật nội bộ | Markdown, ADR, checklist, guideline |

❌ **Không nên làm** — Đưa business logic của 1 feature vào `src/common/` chỉ vì “dùng ở vài nơi”.

**Tại sao**: `common/` là nơi chứa *building blocks* tái sử dụng độc lập (filter, interceptor, pipe, guard generic). Business logic theo bounded context phải ở đúng feature module để giữ ranh giới kiến trúc. Nếu `common/` chứa code theo feature, về lâu dài sẽ biến thành “thùng rác kiến trúc”, khó refactor, và dễ phát sinh circular dependencies.

### 2.2. Controller ở `api/<caller>/`, logic ở `modules/<feature>/`

✅ **Nên làm** — Controller nhận request, gọi service của module rồi trả kết quả. Feature có endpoint cho cả user và admin thì có hai controller, ở `api/user/` và `api/admin/`, cùng gọi một module.

```ts
// src/api/admin/admin-api.module.ts — controllers for the admin panel; the logic stays in modules/
@Module({
  imports: [OrdersModule, ProductsModule],
  controllers: [AdminOrdersController, AdminProductsController],
})
export class AdminApiModule {}
```

❌ **Không nên làm** — Đặt controller trong `modules/<feature>/`, hoặc viết query và rule nghiệp vụ trong controller.

**Tại sao**: Guard, rate limit và Swagger tag thường khác nhau theo đối tượng gọi. Gom controller theo caller thì cấu hình một lần cho cả nhóm. Module không phụ thuộc HTTP, nên process worker dùng lại được cùng service.

### 2.3. `contracts/` và `infra/` — hướng phụ thuộc

✅ **Nên làm** — Module cần dịch vụ bên ngoài thì inject abstract class trong `contracts/`. Class trong `infra/` implement contract đó, và `ContractsModule` là chỗ duy nhất chọn implementation.

```ts
// src/contracts/mail/gateway.ts — the abstract class is also the DI token
export abstract class MailGateway {
  abstract send(options: SendMailOptions): Promise<void>;
}

// src/contracts.module.ts — binds every contract to its infra implementation, as in v535
@Global()
@Module({
  providers: [{ provide: MailGateway, useClass: MailService }], // MailService: src/infra/mail/
  exports: [MailGateway],
})
export class ContractsModule {}
```

Hướng import: `api/` → `modules/` → `contracts/` ← `infra/`. `common/` và `config/` dùng được ở mọi tầng.

❌ **Không nên làm** — Module import thẳng class trong `infra/` (ví dụ `MailService`).

**Tại sao**: Đổi nhà cung cấp mail hay storage chỉ sửa `infra/` và `ContractsModule`. Unit test của module mock abstract class, không cần biết implementation.

### 2.4. Quy tắc cho `src/common/`

✅ **Nên làm** — Chỉ đặt những thành phần dùng lại cho **nhiều** module và không gắn với nghiệp vụ cụ thể:

- `filters/` — chuẩn hóa format lỗi (global, HTTP)
- `interceptors/` — chuẩn hóa response, logging, tracing
- `guards/` — guard generic dùng lại cho nhiều module
- `pipes/` — pipe generic (parse, transform, validate cross-module)
- `decorators/` — decorator generic (`@Public()`, `@CurrentUser()`)

❌ **Không nên làm** — Tạo folder `common/<feature>/...` (ví dụ: `common/orders/*`).

**Tại sao**: Feature-specific code phải nằm trong `src/modules/<feature>/`. Khi `common/` bắt đầu có subfolder theo feature, ranh giới giữa common và module bị mờ, dẫn tới coupling sai hướng và tăng rủi ro circular dependencies.

### 2.5. Cấu trúc chuẩn của một feature module

✅ **Nên làm**:

- Mỗi module có **entry points** rõ ràng: `.module.ts`, `.service.ts`. Controller nằm ở `api/<caller>/` (mục 2.2).
- DTO tách riêng folder `dto/` để review dễ và giảm coupling.
- Project dùng TypeORM tách entity ra folder `entities/`. Project dùng Prisma không có folder này, model nằm trong `schema.prisma`.

**Template tối thiểu**:

```txt
src/modules/<feature>/
├── <feature>.module.ts
├── <feature>.service.ts
├── <feature>.repository.ts
├── dto/
│   ├── create-*.dto.ts
│   ├── update-*.dto.ts
│   └── list-*.dto.ts
└── entities/                 # TypeORM only
    └── <feature>.entity.ts
```

✅ **Khi module phức tạp** — mở rộng ngay trong module đó, như các module của v535:

- `services/`, `repositories/`, `mappers/` — khi mỗi loại có từ 2 file trở lên
- `exceptions/` — exception riêng cho module
- `constants/` — hằng số, literal (error code, type string, …)
- `events/` — event và event handler của module

❌ **Không nên làm** — Tạo folder khi chưa có lý do kiến trúc rõ ràng.

**Tại sao**: Folder là “API tổ chức” cho codebase. Quá nhiều folder mơ hồ làm tìm kiếm và review khó hơn. Chỉ tạo folder khi có từ 2 file trở lên thuộc cùng nhóm chức năng.

### 2.6. So sánh approach: Flat vs Nested module structure

| **Approach** | **Ưu điểm** | **Nhược điểm** | **Khi nào dùng** |
| --- | --- | --- | --- |
| **Flat** (ít subfolder) | Dễ tìm file, nhanh khi module nhỏ | Khó quản lý khi module > 10 files | Module đơn giản, CRUD |
| **Nested** (có subfolder) | Phân loại rõ ràng, scale tốt | Overhead khi module nhỏ | Module phức tạp, nhiều nhóm logic |

**Đề xuất**: Bắt đầu **Flat**. Khi module có khoảng **8 đến 10 files trở lên**, refactor sang **Nested** bằng cách tách thêm subfolder (ví dụ: `services/`, `repositories/`, `exceptions/`).

---

## 3. Ví dụ minh họa thực tế

### 3.1. Tổng quan cấu trúc dự án

```txt
server/
├── src/
│   ├── main.ts                  # HTTP API process
│   ├── app.module.ts
│   ├── worker.ts                # Cron and background job process
│   ├── worker.module.ts
│   ├── contracts.module.ts      # Binds contracts/ to infra/
│   ├── api/
│   │   ├── user/
│   │   │   ├── user-api.module.ts
│   │   │   ├── auth.controller.ts
│   │   │   └── orders.controller.ts
│   │   ├── admin/
│   │   ├── public/
│   │   ├── webhook/
│   │   └── system/              # health check
│   ├── modules/
│   │   ├── auth/
│   │   ├── products/
│   │   └── orders/
│   ├── contracts/
│   │   └── mail/
│   ├── infra/
│   │   ├── prisma/
│   │   ├── mail/
│   │   └── logger/
│   ├── common/
│   │   ├── filters/
│   │   ├── interceptors/
│   │   ├── guards/
│   │   ├── pipes/
│   │   └── decorators/
│   └── config/
├── prisma/                      # Prisma projects only
│   ├── schema.prisma
│   └── migrations/
└── docs/
```

### 3.2. Module đơn giản — Products (Flat)

Module CRUD cơ bản, ít logic, giữ flat và chỉ dùng các folder cần thiết.

```txt
src/api/user/products.controller.ts     # GET list, detail
src/api/admin/products.controller.ts    # create, update, delete
src/modules/products/
├── products.module.ts
├── products.service.ts
├── products.repository.ts
├── dto/
│   ├── create-product.dto.ts
│   ├── update-product.dto.ts
│   └── list-product.dto.ts
└── entities/                           # TypeORM only
    └── product.entity.ts
```

**Walkthrough**:

- `products.module.ts`: khai báo và export `ProductsService`; project TypeORM import thêm entity
- `api/user/products.controller.ts`, `api/admin/products.controller.ts`: chỉ xử lý HTTP, gọi `ProductsService`
- `products.service.ts`: business logic
- `products.repository.ts`: đọc, ghi DB qua Prisma hoặc TypeORM
- `dto/`: validate input từ client (create, update, list)
- `entities/`: TypeORM entity, map 1:1 với database table. Project dùng Prisma không có folder này.

### 3.3. Module phức tạp — Auth (Nested)

Module có nhiều guard, decorator, exception riêng, nên tách subfolder để phân loại.

```txt
src/api/user/auth.controller.ts         # login, refresh, logout
src/modules/auth/
├── auth.module.ts
├── auth.service.ts
├── constants/
│   └── error-codes.const.ts
├── exceptions/
│   ├── base/
│   │   └── auth.exception.ts
│   └── auth.exceptions.ts
├── guards/
│   └── api-key.guard.ts
├── decorators/
│   └── api-key.decorator.ts
└── dto/
    └── response.dto.ts
```

**Walkthrough**:

- `guards/api-key.guard.ts`: guard **riêng** cho auth module, không phải global, nên đặt trong module (không đặt ở `common/`)
- `exceptions/`: custom exceptions cho auth flow
- `constants/`: error codes, tránh magic strings
- `decorators/`: custom decorator dùng kèm guard

### 3.4. Module trung bình — Orders (Flat)

```txt
src/api/user/orders.controller.ts
src/modules/orders/
├── orders.module.ts
├── orders.service.ts
├── orders.repository.ts
├── dto/
│   ├── create-order.dto.ts
│   └── list-order.dto.ts
└── entities/                           # TypeORM only
    └── order.entity.ts
```

### 3.5. Bên trong `src/common/` — Ví dụ thực tế

| **File** | **Chức năng** | **Dùng ở đâu** |
| --- | --- | --- |
| `common/interceptors/global-response.interceptor.ts` | Wrap response thành format chuẩn | Tất cả controllers |
| `common/filters/global-exception.filter.ts` | Catch exception và format lỗi chuẩn | Global (đăng ký ở `main.ts`) |

**Before/After — Tại sao cần global response interceptor**:

❌ **Before** (mỗi controller tự format):

```ts
// api/user/products.controller.ts
@Get()
async findAll() {
  const products = await this.productsService.findAll();
  return { data: products, timestamp: new Date().toISOString() }; // Lặp lại ở mọi endpoint
}
```

✅ **After** (dùng global interceptor):

```ts
// api/user/products.controller.ts
@Get()
async findAll() {
  return this.productsService.findAll(); // Clean, interceptor tự wrap
}
```

`GlobalResponseInterceptor` bọc kết quả thành `{ data, requestId, timestamp }`. Code ở [NestJS Coding Standard 3.1 — REST API Design](Ref_Dev_s3.1_nestjs-rest-api-design_v1.0.md) mục 2.4.

---

## 4. Tooling & Config

- **Nest CLI** — Dùng `nest generate` để tạo file đúng cấu trúc:

```bash
# Tạo feature module mới
nest g module modules/loyalty
nest g service modules/loyalty
nest g controller loyalty api/user --flat   # src/api/user/loyalty.controller.ts, added to UserApiModule
```

Sau lệnh cuối, thêm `LoyaltyModule` vào `imports` của `UserApiModule`: Nest CLI chỉ khai báo controller.

- **ESLint** — Có thể dùng `eslint-plugin-boundaries` để enforce hướng import ở mục 2.3 (ngăn `modules/` import `infra/`, ngăn module A import trực tiếp từ module B).

---

## References

- [NestJS Documentation](https://docs.nestjs.com/)
- [NestJS CLI](https://docs.nestjs.com/cli/overview)
- [NestJS Controllers](https://docs.nestjs.com/controllers)
- [NestJS Providers & DI](https://docs.nestjs.com/providers)
- [NestJS Modules](https://docs.nestjs.com/modules)

## Changelog

| Date | Version | Change | By |
| :---- | :---- | :---- | :---- |
| 2026-11-18 | v1.0 | Chuyển từ Notion "NestJS Document" (page `33d71a38d3b28158aa52e341938eea4a`, sửa 2026-04-09). Review và sửa nội dung, code trước khi publish. Owner duyệt trong chat ngày 2026-11-18. | Bắc PV |
