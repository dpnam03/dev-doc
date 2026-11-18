# NestJS Coding Standard 3.1 — REST API Design

| Field | Value |
| :---- | :---- |
| Owner | Bắc PV — NodeJS BE Dev Lead |
| Audience | Dev (NodeJS BE) |
| Last reviewed | 2026-11-12 |
| Review cadence | Quarterly |
| Version | v1.0 |
| Linked from | Ref_Dev_nestjs-coding-standard_v1.0<br>Ref_Dev_s3.4_nestjs-api-documentation-openapi_v1.0 |
| Status | Live |

Doc này là mục 3.1 của [NestJS Coding Standard](Ref_Dev_nestjs-coding-standard_v1.0.md), nhóm API & Data handling. Doc nêu quy tắc về REST API Design trong dự án NestJS, kèm lý do, ví dụ và config. Dev NodeJS BE đọc doc này khi viết code, review code và onboarding.

---

## 1. Tóm tắt & Phạm vi

**Chủ đề:** Thiết kế REST API và tích hợp Swagger/OpenAPI documentation trong NestJS.

**Vấn đề giải quyết:**

- API endpoint đặt tên không nhất quán, khó hiểu, khó maintain giữa các modules.
- Sử dụng HTTP methods và status codes sai ngữ nghĩa, gây nhầm lẫn cho frontend và third-party consumers.
- Response format không thống nhất giữa các endpoints — frontend phải handle nhiều format khác nhau.
- Thiếu API documentation hoặc docs lỗi thời so với code thực tế.
- Query, filter, pagination mỗi endpoint thiết kế một kiểu.

**Phạm vi áp dụng:** Tất cả REST API endpoints trong NestJS applications. Áp dụng từ giai đoạn thiết kế API đến khi viết code controller, DTO, và Swagger decorators.

**Tại sao quan trọng:**

- API nhất quán giúp frontend tích hợp nhanh, giảm bugs liên quan đến format/status.
- Swagger auto-generated từ code đảm bảo docs luôn đồng bộ với implementation.
- Chuẩn hoá response/error format giúp viết error handler chung ở frontend, dễ logging/monitoring.
- API versioning rõ ràng tránh breaking changes ảnh hưởng production.

---

## 2. Quy tắc & Giải thích

### 2.1. Endpoint URL: danh từ số nhiều, lowercase, tối đa 2 cấp nesting

**✅ NÊN:** Dùng resource dạng **danh từ, số nhiều, lowercase**. Hành động thể hiện qua HTTP method, không qua URL.

```txt
GET    /products              → Danh sách products
GET    /products/:id          → Chi tiết 1 product
POST   /products              → Tạo product mới
PATCH  /products/:id          → Cập nhật một phần
DELETE /products/:id          → Xoá product

GET    /orders/:id/items      → Sub-resource (tối đa 2 cấp)
```

**❌ KHÔNG NÊN:** Dùng động từ trong URL hoặc nesting quá sâu.

```txt
❌ GET  /getProducts
❌ POST /createOrder
❌ GET  /users/:id/orders/:orderId/items/:itemId/reviews   → quá sâu

✅ GET  /products
✅ POST /orders
✅ GET  /order-item-reviews?orderId=123                     → flatten qua query
```

*Tại sao:* URL dạng danh từ + HTTP method là chuẩn REST, giúp API predictable. Nesting quá sâu khiến URL dài, khó cache, và tạo coupling chặt giữa resources. Nếu cần, dùng query string để filter thay vì nesting.

> **Tham khảo:** [NestJS Controllers](https://docs.nestjs.com/controllers)

---

### 2.2. HTTP Methods đúng ngữ nghĩa

**✅ NÊN:** Dùng đúng HTTP method theo semantics:

| **Method** | **Mục đích** | **Idempotent** | **Response** |
| --- | --- | --- | --- |
| `GET` | Đọc resource (list hoặc detail) | ✅ Có | `200 OK` |
| `POST` | Tạo resource mới | ❌ Không | `201 Created` • body resource |
| `PATCH` | Cập nhật **một phần** resource | ❌ Không | `200 OK` • body updated |
| `PUT` | Thay thế **toàn bộ** resource | ✅ Có | `200 OK` • body updated |
| `DELETE` | Xoá resource | ✅ Có | `204 No Content` (không body) |

**Đề xuất:** Ưu tiên `PATCH` hơn `PUT` cho update — trong thực tế, phần lớn updates chỉ thay đổi một số fields, không cần gửi toàn bộ resource.

*Tại sao:* HTTP methods có semantics rõ ràng trong RFC. `GET` phải idempotent (gọi nhiều lần kết quả giống nhau), `POST` tạo mới mỗi lần gọi. Frontend, CDN, và API gateway dựa vào method để cache, retry, và log đúng.

> **Tham khảo:** [MDN HTTP Methods](https://developer.mozilla.org/en-US/docs/Web/HTTP/Methods)

---

### 2.3. Status Codes đúng ý nghĩa

**✅ NÊN:** Trả status code phản ánh đúng kết quả xử lý.

**Success (2xx):**

| **Code** | **Khi nào dùng** | **Ví dụ** |
| --- | --- | --- |
| `200 OK` | Request thành công, có body trả về | GET, PATCH, PUT |
| `201 Created` | Tạo resource mới thành công | POST |
| `204 No Content` | Thành công nhưng không có body | DELETE |

**Client Error (4xx):**

| **Code** | **Khi nào dùng** |
| --- | --- |
| `400 Bad Request` | Input không hợp lệ (validation failed), hoặc business logic reject (stock không đủ, etc.) |
| `401 Unauthorized` | Chưa xác thực (thiếu/sai token) |
| `403 Forbidden` | Đã xác thực nhưng không có quyền |
| `404 Not Found` | Resource không tồn tại |
| `409 Conflict` | Trùng lặp (duplicate email, SKU, etc.) |

Team không dùng 422. Lỗi business trả 400 với `type: 'DOMAIN_ERROR'`, client phân biệt với lỗi validate bằng `type` (mục 2.4).

**Server Error (5xx):**

| **Code** | **Khi nào dùng** |
| --- | --- |
| `500 Internal Server Error` | Lỗi không xác định, unexpected |
| `503 Service Unavailable` | Service tạm không khả dụng (maintenance, overload) |

**❌ KHÔNG NÊN:** Trả mọi thứ `200` rồi embed error trong body.

```ts
// ❌ Bad — frontend không biết request thất bại qua status code
return { status: 200, error: 'Product not found' };

// ✅ Good — status code rõ ràng
throw new NotFoundException(`Product with ID ${id} not found`);
// → Response: 404 { error: { type: 'NOT_FOUND', code: 'NOT_FOUND', message: '...', ... } }
```

*Tại sao:* HTTP clients, load balancers, monitoring tools đều dựa vào status code để phân loại request. Trả `200` cho error khiến monitoring không phát hiện lỗi, retry logic sai, và frontend phải parse body mới biết kết quả.

> **Tham khảo:** [HTTP Status Codes — MDN](https://developer.mozilla.org/en-US/docs/Web/HTTP/Status)

---

### 2.4. Response Format chuẩn hoá

**✅ NÊN:** Thống nhất format response cho toàn bộ API thông qua global interceptor và exception filter.

- Response không có field `success`. HTTP status đã cho biết request thành công (2xx) hay lỗi (4xx, 5xx).
- Mọi response có `requestId` và `timestamp` để tìm request trong log.
- Ngày giờ trả dạng ISO 8601 theo UTC, ví dụ `2026-11-17T10:00:00.000Z`. Client tự đổi sang múi giờ của user khi hiển thị.
- ID trả dạng string, kể cả khi DB lưu số. Số nguyên lớn hơn 2^53 bị JavaScript làm tròn mà không báo lỗi. Response DTO đổi ID bằng `@Transform` ([NestJS Coding Standard 3.2 — Validation & Serialization](Ref_Dev_s3.2_nestjs-validation-serialization_v1.0.md) mục 2.7).

**Success response** (xử lý bởi `GlobalResponseInterceptor`):

```json
{
  "data": { "id": "1", "name": "Áo thun nam", "price": 199000 },
  "requestId": "abc-123",
  "timestamp": "2026-11-17T10:00:00.000Z"
}
```

**Paginated response:** service trả `PaginatedResult` ([NestJS Coding Standard 1.5 — Coding conventions (phần 2)](Ref_Dev_s1.5_nestjs-coding-conventions-part-2_v1.0.md) mục 2.6), interceptor giữ `meta` cạnh `data`. Cursor pagination dùng `meta: { hasMore, nextCursor }` ([NestJS Coding Standard 4.1 — Database & ORM](Ref_Dev_s4.1_nestjs-database-orm_v1.0.md) mục 2.6).

```json
{
  "data": [
    { "id": "1", "name": "Áo thun" },
    { "id": "2", "name": "Quần jeans" }
  ],
  "meta": {
    "total": 150,
    "page": 1,
    "limit": 20,
    "totalPages": 8,
    "hasNextPage": true,
    "hasPrevPage": false
  },
  "requestId": "abc-123",
  "timestamp": "2026-11-17T10:00:00.000Z"
}
```

```ts
// common/interceptors/global-response.interceptor.ts
import {
  CallHandler, ExecutionContext, Injectable, NestInterceptor, StreamableFile,
} from '@nestjs/common';
import { Request } from 'express';
import { Observable, map } from 'rxjs';

@Injectable()
export class GlobalResponseInterceptor implements NestInterceptor {
  intercept(context: ExecutionContext, next: CallHandler): Observable<unknown> {
    if (context.getType() !== 'http') return next.handle(); // WebSocket and RPC keep their own format

    // requestId is set by RequestIdMiddleware (Coding Standard 7.1, section 2.5)
    const { requestId } = context.switchToHttp().getRequest<Request & { requestId?: string }>();

    return next.handle().pipe(
      map((result: unknown) => {
        if (result instanceof StreamableFile) return result; // File download: send as is
        const timestamp = new Date().toISOString();
        // PaginatedResult (Coding Standard 1.5, section 2.6): keep meta next to data
        if (isPage(result)) return { data: result.data, meta: result.meta, requestId, timestamp };
        return { data: result, requestId, timestamp };
      }),
    );
  }
}

function isPage(value: unknown): value is { data: unknown; meta: unknown } {
  return typeof value === 'object' && value !== null && 'data' in value && 'meta' in value;
}
```

**Error response** (xử lý bởi `GlobalExceptionFilter`, code ở [NestJS Coding Standard 3.3 — Exception Handling](Ref_Dev_s3.3_nestjs-exception-handling_v1.0.md) mục 2.3). Ví dụ tạo product với `name` quá ngắn và `price` âm:

```json
{
  "error": {
    "type": "VALIDATION_ERROR",
    "code": "VALIDATION_ERROR",
    "message": "name must be longer than or equal to 3 characters; price must not be less than 0",
    "param": "name",
    "details": [
      { "field": "name", "message": "name must be longer than or equal to 3 characters" },
      { "field": "price", "message": "price must not be less than 0" }
    ],
    "path": "/v1/products",
    "requestId": "abc-123",
    "timestamp": "2026-11-17T10:00:00.000Z"
  }
}
```

| **Field** | **Ý nghĩa** |
| --- | --- |
| `type` | Nhóm lỗi: `VALIDATION_ERROR`, `NOT_FOUND`, `AUTH_ERROR`, `DOMAIN_ERROR`, `CONFLICT`, `RATE_LIMIT`, `SERVER_ERROR` |
| `code` | Mã lỗi cụ thể để client xử lý, ví dụ `INSUFFICIENT_STOCK`. Mỗi custom exception khai báo một `code` |
| `message` | Mô tả lỗi bằng tiếng Anh, cho log và developer gọi API. Client không hiển thị thẳng cho user |
| `param` | Field lỗi đầu tiên, chỉ có khi có `details` |
| `details` | Mọi field lỗi, mỗi phần tử gồm `field`, `message` và có thể có `code` |
| `path`, `requestId`, `timestamp` | Dùng để tìm request trong log |

*Tại sao:* Format nhất quán giúp frontend viết 1 response handler dùng chung cho mọi API. Client xử lý lỗi theo `error.code` và hiện lỗi dưới từng ô nhập theo `details`, không cần parse từng endpoint riêng.

---

### 2.5. Query, Filter & Pagination chuẩn

**✅ NÊN:** Dùng query string cho filter, sort, và pagination.

```txt
GET /products?status=active&category=electronics&sorting=-price&page=1&limit=20
GET /orders?customerId=123&status=pending&fromDate=2025-01-01&toDate=2025-12-31
```

**DTO cho query params:**

```ts
export class ListProductDto {
  @IsOptional()
  @IsEnum(ProductStatus)
  status?: ProductStatus;

  @IsOptional()
  @IsString()
  category?: string;

  // Field name; a leading "-" sorts descending, e.g. sorting=-createdAt
  @IsOptional()
  @IsString()
  @Matches(/^-?(name|price|createdAt)$/)
  sorting?: string;

  @IsOptional()
  @Type(() => Number)
  @IsNumber()
  @Min(1)
  page?: number = 1;

  @IsOptional()
  @Type(() => Number)
  @IsNumber()
  @Min(1)
  @Max(100)
  limit?: number = 20;
}
```

**❌ KHÔNG NÊN:** Encode filter phức tạp trong URL path hoặc request body cho GET.

```txt
❌ GET /products/status/active/category/electronics/page/1
❌ POST /products/search { "filters": { ... } }   → dùng GET + query string
```

*Tại sao:* Query string là chuẩn HTTP cho filter — cacheable, bookmarkable, dễ log. POST body cho search chỉ nên dùng khi filter quá phức tạp (full-text search, elasticsearch query).

---

### 2.6. API Versioning

**✅ NÊN:** Dùng URL prefix cho versioning khi API phục vụ nhiều clients.

```ts
// main.ts — URI versioning, no global prefix → /v1/products
import { VersioningType, VERSION_NEUTRAL } from '@nestjs/common';

app.enableVersioning({
  type: VersioningType.URI,
  defaultVersion: '1', // controllers without `version` are served under /v1
});

// Per-controller version when mixed versions are needed → /v1/products, /v2/products
@Controller({ path: 'products', version: '1' })
export class ProductsV1Controller { ... }

@Controller({ path: 'products', version: '2' })
export class ProductsV2Controller { ... }

// Not versioned → /health
@Controller({ path: 'health', version: VERSION_NEUTRAL })
export class HealthController { ... }
```

**❌ KHÔNG NÊN:** Breaking change trên version đang production mà không có migration plan.

*Tại sao:* URL-based versioning (`/v1/`, `/v2/`) đơn giản, dễ hiểu, dễ route. Khi cần breaking change, tạo version mới và deprecate version cũ với timeline rõ ràng. Không đặt version vào global prefix (`setGlobalPrefix('v1')`): thiếu `enableVersioning()` thì `version: '2'` không route được, có thì route thành `/v1/v2/...`. Health controller khai báo `VERSION_NEUTRAL` để probe gọi `/health` ở mọi version.

> **Tham khảo:** [NestJS Versioning](https://docs.nestjs.com/techniques/versioning)

---

### 2.7. Swagger / OpenAPI Documentation

**✅ NÊN:** Tích hợp `@nestjs/swagger` để auto-generate API docs từ code.

**Setup trong `main.ts`:**

```ts
import { SwaggerModule, DocumentBuilder } from '@nestjs/swagger';

async function bootstrap() {
  const app = await NestFactory.create(AppModule);

  // Swagger config
  const config = new DocumentBuilder()
    .setTitle('NestJS API')
    .setDescription('API documentation cho project')
    .setVersion('1.0')
    .addCookieAuth('accessToken') // JWT in the HttpOnly cookie (5.1 section 2.3)
    .addApiKey(                // API Key authentication
      { type: 'apiKey', name: 'x-api-key', in: 'header' },
      'api-key',
    )
    .build();

  const document = SwaggerModule.createDocument(app, config);
  SwaggerModule.setup('api-docs', app, document);

  await app.listen(3000);
}
```

*Tại sao:* Swagger UI (`/api-docs`) cho phép QA, frontend, và AI tools xem và thử API trực tiếp. Docs auto-generated từ code nên luôn đồng bộ — không bao giờ lỗi thời.

---

### 2.8. Swagger Decorators cho Controller

**✅ NÊN:** Thêm Swagger decorators cho mọi controller và endpoint.

```ts
@ApiTags('products')           // Nhóm endpoints trên Swagger UI
@Controller('products')
export class ProductsController {
  constructor(private readonly productsService: ProductsService) {}

  @Post()
  @ApiOperation({ summary: 'Tạo sản phẩm mới' })
  @ApiCreatedResponse({
    description: 'Tạo thành công',
    type: ProductResponseDto,
  })
  @ApiBadRequestResponse({ description: 'Validation failed' })
  async create(@Body() dto: CreateProductDto): Promise<ProductResponseDto> {
    return this.productsService.create(dto);
  }

  @Get()
  @ApiOperation({ summary: 'Danh sách sản phẩm' })
  @ApiOkResponse({ type: [ProductResponseDto] })
  @ApiQuery({ name: 'status', required: false, enum: ProductStatus })
  @ApiQuery({ name: 'page', required: false, type: Number })
  async findAll(@Query() query: ListProductDto): Promise<PaginatedResult<ProductResponseDto>> {
    return this.productsService.findAll(query);
  }

  @Get(':id')
  @ApiOperation({ summary: 'Chi tiết sản phẩm' })
  @ApiParam({ name: 'id', description: 'Product ID' })
  @ApiOkResponse({ type: ProductResponseDto })
  @ApiNotFoundResponse({ description: 'Product not found' })
  async findOne(@Param('id', ParseIntPipe) id: number): Promise<ProductResponseDto> {
    return this.productsService.findOne(id);
  }

  @Patch(':id')
  @AdminOnly()                 // Composed decorator (auth + role)
  @ApiOperation({ summary: 'Cập nhật sản phẩm (admin)' })
  @ApiOkResponse({ type: ProductResponseDto })
  async update(
    @Param('id', ParseIntPipe) id: number,
    @Body() dto: UpdateProductDto,
  ): Promise<ProductResponseDto> {
    return this.productsService.update(id, dto);
  }

  @Delete(':id')
  @AdminOnly()
  @ApiOperation({ summary: 'Xoá sản phẩm (admin)' })
  @ApiNoContentResponse({ description: 'Xoá thành công' })
  @HttpCode(HttpStatus.NO_CONTENT)
  async remove(@Param('id', ParseIntPipe) id: number): Promise<void> {
    return this.productsService.remove(id);
  }
}
```

**❌ KHÔNG NÊN:** Controller không có Swagger decorators — docs sẽ thiếu thông tin.

*Tại sao:* Swagger decorators vừa là documentation vừa là contract. Frontend dựa vào đây để generate types, QA dựa vào để test. Thiếu decorators = API undocumented = khó tích hợp.

---

### 2.9. Swagger Decorators cho DTO

**✅ NÊN:** Thêm `@ApiProperty` với `example` và `description` cho mọi DTO field.

```ts
export class CreateProductDto {
  @ApiProperty({
    example: 'Áo thun nam',
    description: 'Tên hiển thị của sản phẩm',
  })
  @IsString()
  @IsNotEmpty()
  @Length(3, 100)
  name: string;

  @ApiProperty({
    example: 'SKU-001',
    description: 'Mã SKU duy nhất',
  })
  @IsString()
  @Matches(/^[A-Z0-9-]+$/)
  sku: string;

  @ApiProperty({
    example: 199000,
    description: 'Giá bán (VND)',
    minimum: 0,
  })
  @IsNumber()
  @Min(0)
  price: number;

  @ApiPropertyOptional({
    example: 'Áo thun cotton 100%, form regular fit',
    description: 'Mô tả sản phẩm',
  })
  @IsString()
  @IsOptional()
  description?: string;

  @ApiProperty({
    enum: ProductStatus,
    example: ProductStatus.ACTIVE,
    description: 'Trạng thái sản phẩm',
  })
  @IsEnum(ProductStatus)
  status: ProductStatus;
}
```

**❌ KHÔNG NÊN:** DTO field không có `@ApiProperty` — Swagger UI sẽ không hiển thị field đó.

```ts
// ❌ Bad — thiếu @ApiProperty, Swagger không biết field này
export class CreateProductDto {
  name: string;  // Không hiện trên Swagger UI
  price: number; // Không hiện trên Swagger UI
}
```

*Tại sao:* `@ApiProperty` cung cấp `example` giúp Swagger UI hiện payload mẫu — QA/frontend copy-paste test ngay mà không cần đoán format. `description` giải thích business meaning của field.

---

### 2.10. DTO tách Input / Output

**✅ NÊN:** Tách riêng DTO cho input và output — không trả thẳng entity.

```ts
// Input DTO — validate client input
export class CreateProductDto {
  @ApiProperty({ example: 'Áo thun nam' })
  @IsString() @IsNotEmpty()
  name: string;

  @ApiProperty({ example: 199000 })
  @IsNumber() @Min(0)
  price: number;
}

// Output DTO — kiểm soát response shape
export class ProductResponseDto {
  @Expose() id: number;
  @Expose() name: string;
  @Expose() price: number;
  @Expose() sku: string;
  @Expose() status: string;
  @Expose() createdAt: Date;
  // Không expose: internalNotes, costPrice, supplierInfo
}

// Update DTO — extends PartialType cho DRY
export class UpdateProductDto extends PartialType(CreateProductDto) {}
```

**❌ KHÔNG NÊN:** Trả raw entity từ database.

```ts
// ❌ Bad — entity có thể chứa field nhạy cảm
@Get(':id')
async findOne(@Param('id') id: number) {
  return this.productRepository.findOne({ where: { id } });
  // Có thể trả về: costPrice, supplierInfo, internalNotes, deletedAt...
}
```

*Tại sao:* Entity thường chứa internal fields không nên expose (cost price, supplier info, soft delete flags). Output DTO kiểm soát chính xác những gì client nhận được — bảo mật và API stability.

> **Tham khảo:** [NestJS Serialization](https://docs.nestjs.com/techniques/serialization) · [NestJS Mapped Types](https://docs.nestjs.com/openapi/mapped-types)

---

### 2.11. `Idempotency-Key` cho POST/PATCH

**✅ NÊN:** Endpoint tạo hoặc đổi dữ liệu quan trọng (tạo order, thanh toán) nhận header `Idempotency-Key`. Client gửi một UUID cho mỗi thao tác và gửi lại đúng key đó khi retry.

```ts
// common/interceptors/idempotency.interceptor.ts — replays the stored result when a POST/PATCH repeats its Idempotency-Key
@Injectable()
export class IdempotencyInterceptor implements NestInterceptor {
  constructor(@Inject(CACHE_MANAGER) private readonly cache: Cache) {}

  async intercept(context: ExecutionContext, next: CallHandler): Promise<Observable<unknown>> {
    const req = context.switchToHttp().getRequest<Request & { user?: UserPayload }>();
    const key = req.headers['idempotency-key'];
    if (typeof key !== 'string' || !['POST', 'PATCH'].includes(req.method)) return next.handle();

    // Scoped per user, so one client cannot read another client's result with a guessed key
    const cacheKey = `idempotency:${req.user?.sub ?? 'anonymous'}:${req.method}:${req.path}:${key}`;
    const stored = await this.cache.get(cacheKey);
    if (stored !== undefined) return of(stored);

    return next.handle().pipe(
      tap((result) => void this.cache.set(cacheKey, result, 24 * 60 * 60 * 1000)), // 24h; cache-manager 7 takes ms
    );
  }
}
```

```ts
// Usage — on the endpoints a client may retry
@Post()
@UseInterceptors(IdempotencyInterceptor)
create(@Body() dto: CreateOrderDto) { ... }
```

Cache dùng `CACHE_MANAGER` ở [NestJS Coding Standard 4.2 — Caching](Ref_Dev_s4.2_nestjs-caching_v1.0.md). Hai request cùng key đến cùng lúc vẫn chạy cả hai. Cần chặn hẳn thì lưu key vào cột có unique constraint trong cùng transaction với dữ liệu.

*Tại sao:* Mạng chập chờn làm client không nhận được response và gửi lại request. Không có key thì server tạo hai order và trừ tiền hai lần.

---

## 3. Ví dụ minh họa thực tế

### 3.1. Walkthrough: Thiết kế Product API hoàn chỉnh

**Bước 1 — Định nghĩa endpoints**

```txt
GET    /v1/products              → List (có filter, pagination)
GET    /v1/products/:id          → Detail
POST   /v1/products              → Create (admin)
PATCH  /v1/products/:id          → Update partial (admin)
DELETE /v1/products/:id          → Delete (admin)
```

**Bước 2 — Tạo DTOs**

```ts
// dto/create-product.dto.ts
export class CreateProductDto {
  @ApiProperty({ example: 'Áo thun nam' })
  @IsString() @IsNotEmpty() @Length(3, 100)
  name: string;

  @ApiProperty({ example: 'SKU-001' })
  @IsString() @Matches(/^[A-Z0-9-]+$/)
  sku: string;

  @ApiProperty({ example: 199000, minimum: 0 })
  @IsNumber() @Min(0)
  price: number;

  @ApiPropertyOptional({ example: 'Mô tả sản phẩm' })
  @IsString() @IsOptional()
  description?: string;
}

// dto/update-product.dto.ts
export class UpdateProductDto extends PartialType(CreateProductDto) {}

// dto/list-product.dto.ts
export class ListProductDto {
  @ApiPropertyOptional({ enum: ProductStatus })
  @IsOptional() @IsEnum(ProductStatus)
  status?: ProductStatus;

  @ApiPropertyOptional({ default: 1, minimum: 1 })
  @IsOptional() @Type(() => Number) @IsNumber() @Min(1)
  page?: number = 1;

  @ApiPropertyOptional({ default: 20, minimum: 1, maximum: 100 })
  @IsOptional() @Type(() => Number) @IsNumber() @Min(1) @Max(100)
  limit?: number = 20;
}

// dto/product-response.dto.ts
export class ProductResponseDto {
  @ApiProperty({ example: 1 })
  @Expose() id: number;

  @ApiProperty({ example: 'Áo thun nam' })
  @Expose() name: string;

  @ApiProperty({ example: 'SKU-001' })
  @Expose() sku: string;

  @ApiProperty({ example: 199000 })
  @Expose() price: number;

  @ApiProperty({ enum: ProductStatus })
  @Expose() status: ProductStatus;

  @ApiProperty()
  @Expose() createdAt: Date;
}
```

**Bước 3 — Controller với đầy đủ Swagger decorators**

```ts
@ApiTags('products')
@Controller('products')
export class ProductsController {
  constructor(private readonly productsService: ProductsService) {}

  @Post()
  @ApiOperation({ summary: 'Tạo sản phẩm mới' })
  @ApiCreatedResponse({ type: ProductResponseDto })
  @ApiBadRequestResponse({ description: 'Validation failed' })
  async create(@Body() dto: CreateProductDto): Promise<ProductResponseDto> {
    const product = await this.productsService.create(dto);
    return plainToInstance(ProductResponseDto, product, {
      excludeExtraneousValues: true,
    });
  }

  @Get()
  @ApiOperation({ summary: 'Danh sách sản phẩm' })
  @ApiOkResponse({ type: [ProductResponseDto] })
  async findAll(@Query() query: ListProductDto) {
    return this.productsService.findAll(query);
  }

  @Get(':id')
  @ApiOperation({ summary: 'Chi tiết sản phẩm' })
  @ApiOkResponse({ type: ProductResponseDto })
  @ApiNotFoundResponse({ description: 'Product not found' })
  async findOne(@Param('id', ParseIntPipe) id: number): Promise<ProductResponseDto> {
    const product = await this.productsService.findOne(id);
    return plainToInstance(ProductResponseDto, product, {
      excludeExtraneousValues: true,
    });
  }

  @Patch(':id')
  @AdminOnly()
  @ApiOperation({ summary: 'Cập nhật sản phẩm' })
  @ApiOkResponse({ type: ProductResponseDto })
  async update(
    @Param('id', ParseIntPipe) id: number,
    @Body() dto: UpdateProductDto,
  ): Promise<ProductResponseDto> {
    const product = await this.productsService.update(id, dto);
    return plainToInstance(ProductResponseDto, product, {
      excludeExtraneousValues: true,
    });
  }

  @Delete(':id')
  @AdminOnly()
  @ApiOperation({ summary: 'Xoá sản phẩm' })
  @ApiNoContentResponse({ description: 'Xoá thành công' })
  @HttpCode(HttpStatus.NO_CONTENT)
  async remove(@Param('id', ParseIntPipe) id: number): Promise<void> {
    await this.productsService.remove(id);
  }
}
```

**Bước 4 — Setup Swagger trong `main.ts`**

```ts
import { VersioningType } from '@nestjs/common';
import { SwaggerModule, DocumentBuilder } from '@nestjs/swagger';

async function bootstrap() {
  const app = await NestFactory.create(AppModule);
  app.enableVersioning({ type: VersioningType.URI, defaultVersion: '1' }); // → /v1/products

  const config = new DocumentBuilder()
    .setTitle('NestJS API')
    .setDescription('Product & Orders API')
    .setVersion('1.0')
    .addCookieAuth('accessToken')
    .build();

  const document = SwaggerModule.createDocument(app, config);
  SwaggerModule.setup('api-docs', app, document);

  await app.listen(3000);
  // Swagger UI: http://localhost:3000/api-docs
}
```

---

### 3.2. Before/After: Từ API không chuẩn đến API chuẩn REST

**Before** — Thiết kế sai chuẩn:

```ts
// ❌ Động từ trong URL
@Post('createProduct')
async createProduct(@Body() body: any) {
  // Không validate input
  const product = await this.repo.save(body);
  return { status: 200, data: product }; // Mọi thứ trả 200
}

// ❌ Dùng POST cho đọc dữ liệu
@Post('searchProducts')
async search(@Body() filters: any) {
  return this.repo.find(filters);
}

// ❌ Không có Swagger decorators
@Get(':id')
async getProduct(@Param('id') id: string) {
  return this.repo.findOne(id); // Trả raw entity
}
```

**After** — Áp dụng chuẩn REST + Swagger:

```ts
// ✅ Danh từ + đúng HTTP method
@Post()
@ApiOperation({ summary: 'Tạo sản phẩm mới' })
@ApiCreatedResponse({ type: ProductResponseDto })
async create(@Body() dto: CreateProductDto): Promise<ProductResponseDto> {
  const product = await this.productsService.create(dto);
  return plainToInstance(ProductResponseDto, product);
}

// ✅ GET + query string cho search
@Get()
@ApiOperation({ summary: 'Tìm kiếm sản phẩm' })
@ApiOkResponse({ type: [ProductResponseDto] })
async findAll(@Query() query: ListProductDto) {
  return this.productsService.findAll(query);
}

// ✅ Swagger decorators + Response DTO
@Get(':id')
@ApiOperation({ summary: 'Chi tiết sản phẩm' })
@ApiOkResponse({ type: ProductResponseDto })
@ApiNotFoundResponse({ description: 'Product not found' })
async findOne(@Param('id', ParseIntPipe) id: number): Promise<ProductResponseDto> {
  const product = await this.productsService.findOne(id);
  return plainToInstance(ProductResponseDto, product);
}
```

---

## 4. Tooling & Config

### 4.1. Checklist setup REST API + Swagger

- [ ] Cài đặt Swagger: `pnpm add @nestjs/swagger`
- [ ] Setup `DocumentBuilder` + `SwaggerModule.setup('api-docs', ...)` trong `main.ts`
- [ ] Bật versioning, không đặt global prefix: `app.enableVersioning({ type: VersioningType.URI, defaultVersion: '1' })`
- [ ] Thêm `@ApiTags` cho mọi controller
- [ ] Thêm `@ApiOperation` + `@ApiResponse` cho mọi endpoint
- [ ] Thêm `@ApiProperty` cho mọi DTO field
- [ ] Tạo Response DTO riêng — không trả raw entity
- [ ] Dùng đúng HTTP method và status code
- [ ] Tạo ListDto chuẩn cho pagination (page, limit, sorting)
- [ ] Verify Swagger UI tại `http://localhost:3000/api-docs`

### 4.2. Swagger CLI Plugin (tự động infer types)

```json
// nest-cli.json — tự động thêm @ApiProperty dựa trên TypeScript types
{
  "compilerOptions": {
    "plugins": [
      {
        "name": "@nestjs/swagger",
        "options": {
          "classValidatorShim": true,
          "introspectComments": true
        }
      }
    ]
  }
}
```

*Lưu ý:* Plugin giúp giảm boilerplate `@ApiProperty`, nhưng vẫn nên explicit `@ApiProperty` cho fields quan trọng có `example` và `description`.

### 4.3. Export OpenAPI spec

```bash
# Export ra file JSON để share cho frontend/QA
pnpm start -- --entryFile main
curl http://localhost:3000/api-docs-json > openapi.json
```

---

## References

- [NestJS Controllers](https://docs.nestjs.com/controllers) — Routing, HTTP methods, status codes
- [NestJS OpenAPI (Swagger)](https://docs.nestjs.com/openapi/introduction) — Swagger integration guide
- [NestJS Serialization](https://docs.nestjs.com/techniques/serialization) — class-transformer, Expose/Exclude
- [NestJS Mapped Types](https://docs.nestjs.com/openapi/mapped-types) — PartialType, PickType, OmitType
- [NestJS Versioning](https://docs.nestjs.com/techniques/versioning) — URL, Header, Media Type versioning
- [MDN HTTP Methods](https://developer.mozilla.org/en-US/docs/Web/HTTP/Methods) — RFC semantics
- [MDN HTTP Status Codes](https://developer.mozilla.org/en-US/docs/Web/HTTP/Status) — Full reference
- [REST API Design Best Practices](https://stackoverflow.blog/2020/03/02/best-practices-for-rest-api-design/) — Stack Overflow Blog

## Changelog

| Date | Version | Change | By |
| :---- | :---- | :---- | :---- |
| 2026-11-18 | v1.0 | Chuyển từ Notion "NestJS Document" (page `33d71a38d3b2811797f4ef7ea667f156`, sửa 2026-04-09). Review và sửa nội dung, code trước khi publish. Owner duyệt trong chat ngày 2026-11-18. | Bắc PV |
