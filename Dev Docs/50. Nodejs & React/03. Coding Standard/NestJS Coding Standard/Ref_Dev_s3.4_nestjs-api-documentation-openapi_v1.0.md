# NestJS Coding Standard 3.4 — API Documentation (OpenAPI)

| Field | Value |
| :---- | :---- |
| Owner | Bắc PV — NodeJS BE Dev Lead |
| Audience | Dev (NodeJS BE) |
| Last reviewed | 2026-11-12 |
| Review cadence | Quarterly |
| Version | v1.0 |
| Linked from | Ref_Dev_nestjs-coding-standard_v1.0 |
| Status | Live |

Doc này là mục 3.4 của [NestJS Coding Standard](Ref_Dev_nestjs-coding-standard_v1.0.md), nhóm API & Data handling. Doc nêu quy tắc về API Documentation (OpenAPI) trong dự án NestJS, kèm lý do, ví dụ và config. Dev NodeJS BE đọc doc này khi viết code, review code và onboarding.

---

## 1. Tóm tắt & Phạm vi

**Chủ đề:** Tổ chức và duy trì API documentation bằng OpenAPI/Swagger trong NestJS — từ schema generation, advanced decorators, documentation structure, đến tích hợp toolchain.

**Vấn đề giải quyết:**

- API docs viết tay (Postman collections, Confluence) nhanh chóng lỗi thời so với code thực tế.
- Swagger UI có nhưng thiếu thông tin: không có examples, descriptions mơ hồ, schema không đầy đủ.
- Không có chiến lược tổ chức docs: endpoints lộn xộn, không phân nhóm, không có mô tả module.
- Authentication schemes không được document — frontend/QA không biết cách authenticate trên Swagger UI.
- Response schema chỉ show happy path — thiếu error responses, edge cases.
- File upload, polymorphic responses, generic wrappers không biết cách document.

**Phạm vi áp dụng:** Tất cả NestJS projects có REST API. Tập trung vào `@nestjs/swagger` decorators, schema generation, và documentation workflows. Bài này bổ sung cho [NestJS Coding Standard 3.1 — REST API Design](Ref_Dev_s3.1_nestjs-rest-api-design_v1.0.md) (đã cover cơ bản Swagger setup và decorators cho endpoints/DTOs).

**Tại sao quan trọng:**

- Docs auto-generated từ code = luôn đồng bộ với implementation, zero maintenance cost.
- Swagger UI đầy đủ giúp frontend tự tích hợp, QA tự test, giảm back-and-forth communication.
- OpenAPI spec export cho phép auto-generate client SDKs, Postman collections, mock servers.
- Docs tốt là onboarding tool — member mới đọc Swagger UI hiểu ngay API contract.

---

## 2. Quy tắc & Giải thích

### 2.1. Swagger CLI Plugin — Auto-infer types, giảm boilerplate

**✅ NÊN:** Bật Swagger CLI Plugin trong `nest-cli.json` để tự động infer `@ApiProperty` từ TypeScript types.

```json
// nest-cli.json
{
  "compilerOptions": {
    "plugins": [
      {
        "name": "@nestjs/swagger",
        "options": {
          "classValidatorShim": true,
          "introspectComments": true,
          "dtoFileNameSuffix": [".dto.ts", ".entity.ts"]
        }
      }
    ]
  }
}
```

**Các options quan trọng:**

| **Option** | **Mục đích** | **Đề xuất** |
| --- | --- | --- |
| `classValidatorShim` | Auto-infer `required`, `enum`, `min/max` từ class-validator decorators | `true` |
| `introspectComments` | Dùng JSDoc comments làm `description` cho `@ApiProperty` | `true` |
| `dtoFileNameSuffix` | Files nào plugin sẽ scan | `[".dto.ts", ".entity.ts"]` |

**Khi nào vẫn cần explicit `@ApiProperty`:**

- Cần `example` cụ thể (plugin không auto-generate examples)
- Cần `description` chi tiết hơn JSDoc comment
- Enum types phức tạp hoặc union types
- Mapped types (`PartialType`, `PickType`) — plugin không always infer đúng

```ts
// Với plugin + JSDoc — không cần @ApiProperty cho simple fields
export class CreateProductDto {
  /** Tên hiển thị của sản phẩm */
  @IsString() @IsNotEmpty() @Length(3, 100)
  name: string;

  /** Giá bán (VND) */
  @IsNumber() @Min(0)
  price: number;

  // Vẫn cần explicit cho example và complex types
  @ApiProperty({ example: 'SKU-001', description: 'Mã SKU duy nhất' })
  @IsString() @Matches(/^[A-Z0-9-]+$/)
  sku: string;
}
```

*Tại sao:* Plugin giảm \~60% boilerplate `@ApiProperty` cho simple fields. Nhưng không thay thế hoàn toàn — `example` values và complex descriptions vẫn cần explicit. Kết hợp plugin + explicit decorators cho fields quan trọng là cách tối ưu.

> **Tham khảo:** [NestJS CLI Plugin](https://docs.nestjs.com/openapi/cli-plugin)

---

### 2.2. Tổ chức documentation với Tags và Module descriptions

**✅ NÊN:** Tổ chức endpoints theo tags có mô tả rõ ràng. Dùng `addTag()` trong `DocumentBuilder` để thêm description cho mỗi tag.

```ts
// main.ts — Tags với descriptions
const config = new DocumentBuilder()
  .setTitle('E-Commerce API')
  .setDescription('Backend API for e-commerce platform')
  .setVersion('1.0')
  .addTag('products', 'Quản lý sản phẩm — CRUD, tìm kiếm, phân loại')
  .addTag('orders', 'Quản lý đơn hàng — tạo, cập nhật trạng thái, lịch sử')
  .addTag('customers', 'Quản lý khách hàng — profile, địa chỉ, loyalty points')
  .addTag('auth', 'Xác thực — đăng nhập, đăng ký, refresh token')
  .addTag('admin', 'Admin operations — reports, settings, user management')
  .addCookieAuth('accessToken')
  .build();
```

```ts
// Controller — tag mapping
@ApiTags('products')
@Controller('products')
export class ProductsController { ... }

// Controller có thể thuộc nhiều tags
@ApiTags('products', 'admin')
@Controller('admin/products')
export class AdminProductsController { ... }
```

**❌ KHÔNG NÊN:**

- Controller không có `@ApiTags` — endpoints hiện ở “default” group, lộn xộn.
- Tag name không khớp giữa `addTag()` và `@ApiTags()` — description sẽ không hiện.

*Tại sao:* Swagger UI nhóm endpoints theo tags. Khi có 50+ endpoints, tags là cách duy nhất để navigate docs hiệu quả. Description cho mỗi tag giúp người đọc hiểu scope mà không cần mở từng endpoint.

---

### 2.3. Authentication Schemes documentation

**✅ NÊN:** Khai báo đầy đủ các authentication schemes trong `DocumentBuilder` và gắn đúng vào endpoints.

```ts
// main.ts — Khai báo auth schemes
const config = new DocumentBuilder()
  .setTitle('API')
  .setVersion('1.0')
  // JWT in the HttpOnly accessToken cookie (5.1 section 2.3); security name 'cookie' matches @ApiCookieAuth()
  .addCookieAuth('accessToken', {
    type: 'apiKey',
    in: 'cookie',
    name: 'accessToken',
    description: 'Gọi POST /v1/auth/login trong Swagger UI trước, browser giữ cookie cho các request sau',
  })
  // API Key
  .addApiKey(
    {
      type: 'apiKey',
      name: 'x-api-key',
      in: 'header',
      description: 'API key cho service-to-service calls',
    },
    'api-key',
  )
  .build();
```

```ts
// Controller — gắn auth scheme
@ApiCookieAuth()  // Default name 'cookie' — must match the name used in addCookieAuth()
@Controller('products') // JwtAuthGuard runs globally (5.1 section 2.4)
export class ProductsController {
  @Get()
  @ApiOperation({ summary: 'List products (public)' })
  @Public() // Custom decorator — bỏ guard
  findAll() { ... }

  @Post()
  @ApiOperation({ summary: 'Create product (requires JWT)' })
  create(@Body() dto: CreateProductDto) { ... }
}

// API Key cho internal endpoints
@ApiSecurity('api-key')
@Public() // Skips the global JWT guard; ApiKeyGuard checks the key instead
@UseGuards(ApiKeyGuard)
@Controller('internal')
export class InternalController { ... }
```

Security name ở `addCookieAuth()` và `@ApiCookieAuth()` phải khớp, dùng tên mặc định `cookie` ở cả hai chỗ. Swagger UI không tự đặt cookie `HttpOnly`: gọi endpoint login trong Swagger UI trên cùng origin, browser giữ cookie và gửi kèm các request sau.

Cần OAuth2 thì dùng flow `authorizationCode` kèm PKCE. Không dùng flow `implicit`: OAuth 2.0 Security BCP (RFC 9700) khuyên không dùng và bản draft OAuth 2.1 đã bỏ flow này.

*Tại sao:* Frontend/QA cần biết chính xác auth method cho mỗi endpoint. Swagger UI cho phép nhập token và test trực tiếp — nếu auth scheme không được khai báo, nút “Authorize” sẽ không hiện.

> **Tham khảo:** [NestJS OpenAPI Security](https://docs.nestjs.com/openapi/security)

---

### 2.4. Response schemas đầy đủ — success, error, và edge cases

**✅ NÊN:** Document tất cả possible responses, không chỉ happy path.

```ts
@Post()
@ApiOperation({ summary: 'Tạo đơn hàng' })
@ApiCreatedResponse({
  description: 'Đơn hàng tạo thành công',
  type: OrderResponseDto,
})
// Validation and business errors share 400, so one decorator lists both examples
@ApiBadRequestResponse({
  description: 'Validation failed, hoặc business logic reject — stock không đủ, coupon hết hạn',
  examples: {
    validation: {
      summary: 'Thiếu field hoặc sai format',
      value: {
        error: {
          type: 'VALIDATION_ERROR',
          code: 'VALIDATION_ERROR',
          message: 'quantity must be a positive number',
          param: 'quantity',
          details: [{ field: 'quantity', message: 'quantity must be a positive number' }],
          path: '/v1/orders',
          requestId: 'abc-123',
          timestamp: '2026-11-17T10:00:00.000Z',
        },
      },
    },
    insufficientStock: {
      summary: 'Stock không đủ',
      value: {
        error: {
          type: 'DOMAIN_ERROR',
          code: 'INSUFFICIENT_STOCK',
          message: 'Product SKU-001 only has 2 items in stock',
          path: '/v1/orders',
          requestId: 'abc-123',
          timestamp: '2026-11-17T10:00:00.000Z',
        },
      },
    },
  },
})
@ApiNotFoundResponse({
  description: 'Product không tồn tại',
})
@ApiConflictResponse({
  description: 'Duplicate order — idempotency key đã được sử dụng',
})
async createOrder(@Body() dto: CreateOrderDto): Promise<OrderResponseDto> { ... }
```

**❌ KHÔNG NÊN:** Chỉ document `@ApiOkResponse` — thiếu error cases.

*Tại sao:* Frontend cần biết tất cả error codes có thể xảy ra để hiển thị message phù hợp. QA dựa vào đây để viết test cases. Nếu chỉ document success, khi API trả 400, không ai biết đó là lỗi validate hay lỗi business.

---

### 2.5. Generic Response Wrapper với `@ApiExtraModels` và `getSchemaPath`

**✅ NÊN:** Khi dùng generic response wrapper (`{ data, meta, requestId, timestamp }`), dùng `@ApiExtraModels` + `$ref` để document đúng schema.

```ts
// dto/api-response.dto.ts
export class ApiResponseDto<T> {
  @ApiProperty()
  data: T;

  @ApiPropertyOptional({ example: 'abc-123' })
  requestId?: string;

  @ApiProperty({ example: '2026-11-17T10:00:00.000Z' })
  timestamp: string;
}

export class PaginatedMetaDto {
  @ApiProperty({ example: 150 }) total: number;
  @ApiProperty({ example: 1 }) page: number;
  @ApiProperty({ example: 20 }) limit: number;
  @ApiProperty({ example: 8 }) totalPages: number;
  @ApiProperty({ example: true }) hasNextPage: boolean;
  @ApiProperty({ example: false }) hasPrevPage: boolean;
}
```

```ts
// Controller — document wrapped response
@ApiExtraModels(ProductResponseDto, PaginatedMetaDto)
@Get()
@ApiOperation({ summary: 'Danh sách sản phẩm' })
@ApiOkResponse({
  description: 'Danh sách sản phẩm (paginated)',
  schema: {
    allOf: [
      {
        properties: {
          data: {
            type: 'array',
            items: { $ref: getSchemaPath(ProductResponseDto) },
          },
          meta: { $ref: getSchemaPath(PaginatedMetaDto) },
          requestId: { type: 'string', example: 'abc-123' },
          timestamp: { type: 'string', format: 'date-time' },
        },
      },
    ],
  },
})
async findAll(@Query() query: ListProductDto) { ... }
```

**Approach đơn giản hơn — Custom decorator:**

```ts
// decorators/api-paginated-response.decorator.ts
export const ApiPaginatedResponse = (model: Type<any>) =>
  applyDecorators(
    ApiExtraModels(model, PaginatedMetaDto),
    ApiOkResponse({
      schema: {
        allOf: [
          {
            properties: {
              data: {
                type: 'array',
                items: { $ref: getSchemaPath(model) },
              },
              meta: { $ref: getSchemaPath(PaginatedMetaDto) },
              requestId: { type: 'string', example: 'abc-123' },
              timestamp: { type: 'string', format: 'date-time' },
            },
          },
        ],
      },
    }),
  );

// Sử dụng
@Get()
@ApiPaginatedResponse(ProductResponseDto)
async findAll(@Query() query: ListProductDto) { ... }
```

*Tại sao:* Nếu dùng interceptor wrap response nhưng Swagger schema chỉ show `ProductResponseDto`, docs sẽ không khớp actual response. `@ApiExtraModels` + `getSchemaPath` cho phép compose schema đúng. Custom decorator giảm lặp code cho pattern paginated.

> **Tham khảo:** [NestJS Advanced — Generic Models](https://docs.nestjs.com/openapi/operations#advanced-generic-apiresponse)

---

### 2.6. File Upload documentation

**✅ NÊN:** Dùng `@ApiConsumes` và `@ApiBody` với `format: 'binary'` cho file upload endpoints.

```ts
@Post('upload')
@ApiOperation({ summary: 'Upload ảnh sản phẩm' })
@ApiConsumes('multipart/form-data')
@ApiBody({
  description: 'File ảnh sản phẩm (JPEG/PNG, max 5MB)',
  schema: {
    type: 'object',
    properties: {
      file: {
        type: 'string',
        format: 'binary',
        description: 'File ảnh (JPEG, PNG)',
      },
      alt: {
        type: 'string',
        description: 'Alt text cho ảnh',
        example: 'Product front view',
      },
    },
    required: ['file'],
  },
})
@UseInterceptors(FileInterceptor('file'))
async uploadImage(
  @UploadedFile(new ParseFilePipe({
    validators: [
      new MaxFileSizeValidator({ maxSize: 5 * 1024 * 1024 }),
      new FileTypeValidator({ fileType: /(jpg|jpeg|png)$/ }),
    ],
  })) file: Express.Multer.File,
  @Body('alt') alt?: string,
): Promise<FileResponseDto> { ... }
```

```ts
// Multiple files upload
@Post('upload-multiple')
@ApiConsumes('multipart/form-data')
@ApiBody({
  schema: {
    type: 'object',
    properties: {
      files: {
        type: 'array',
        items: { type: 'string', format: 'binary' },
        description: 'Nhiều file ảnh (max 10 files)',
      },
    },
  },
})
@UseInterceptors(FilesInterceptor('files', 10))
async uploadMultiple(
  @UploadedFiles() files: Express.Multer.File[],
): Promise<FileResponseDto[]> { ... }
```

*Tại sao:* File upload endpoints cần `multipart/form-data` content type, khác với JSON default. Nếu không có `@ApiConsumes('multipart/form-data')`, Swagger UI sẽ gửi JSON — API sẽ fail.

> **Tham khảo:** [NestJS File Upload](https://docs.nestjs.com/techniques/file-upload) · [OpenAPI File Upload](https://swagger.io/docs/specification/v3_0/describing-request-body/file-upload/)

---

### 2.7. Enum documentation và `@ApiProperty({ enum })`

**✅ NÊN:** Khai báo enum rõ ràng trong `@ApiProperty` — Swagger sẽ hiện dropdown thay vì free text.

```ts
// enums/order-status.enum.ts
export enum OrderStatus {
  PENDING = 'pending',
  CONFIRMED = 'confirmed',
  SHIPPING = 'shipping',
  DELIVERED = 'delivered',
  CANCELLED = 'cancelled',
}

// DTO
export class UpdateOrderDto {
  @ApiProperty({
    enum: OrderStatus,
    example: OrderStatus.CONFIRMED,
    description: 'Trạng thái mới của đơn hàng',
    enumName: 'OrderStatus', // Tạo named schema thay vì inline
  })
  @IsEnum(OrderStatus)
  status: OrderStatus;
}
```

**`enumName` vs inline enum:**

- Không có `enumName` → Swagger inline enum values vào mỗi nơi sử dụng (duplicate).
- Có `enumName` → Swagger tạo `$ref` schema riêng, reuse across endpoints.

**❌ KHÔNG NÊN:**

```ts
// ❌ Bad — enum dạng string[], mất type-safety và docs không rõ
@ApiProperty({ enum: ['pending', 'confirmed', 'shipping'] })
status: string;

// ✅ Good — TypeScript enum, có intellisense và docs rõ ràng
@ApiProperty({ enum: OrderStatus, enumName: 'OrderStatus' })
status: OrderStatus;
```

*Tại sao:* `enumName` tạo reusable schema component — khi enum thay đổi, cập nhật 1 chỗ. Swagger UI hiện dropdown cho enum fields, giúp QA test nhanh hơn.

---

### 2.8. Deprecation — đánh dấu endpoints/fields sắp bỏ

**✅ NÊN:** Dùng `@ApiOperation({ deprecated: true })` cho endpoints và `@ApiProperty({ deprecated: true })` cho DTO fields.

```ts
// Deprecated endpoint — sắp bỏ, chuyển sang v2
@Get('search')
@ApiOperation({
  summary: 'Tìm kiếm sản phẩm (deprecated)',
  description: 'Sử dụng GET /v2/products với query params thay thế',
  deprecated: true,
})
async search(@Query() query: SearchDto) { ... }

// Deprecated DTO field
export class ProductResponseDto {
  @ApiProperty({ example: 'Áo thun' }) @Expose()
  name: string;

  @ApiProperty({
    deprecated: true,
    description: 'Dùng field "sku" thay thế',
  })
  @Expose()
  productCode: string;

  @ApiProperty({ example: 'SKU-001' }) @Expose()
  sku: string;
}
```

*Tại sao:* `deprecated: true` hiện visual indicator trên Swagger UI (strikethrough). Consumers biết endpoint/field sắp bị remove, có thời gian migrate.

---

### 2.9. Swagger `description` dạng Markdown và examples

**✅ NÊN:** Dùng Markdown trong `description` để format documentation phong phú. Dùng `@ApiBody({ examples })` cho multiple request examples.

```ts
@Post()
@ApiOperation({
  summary: 'Tạo đơn hàng',
  description: `
## Tạo đơn hàng mới

Endpoint tạo đơn hàng từ giỏ hàng. Quy trình:
1. Validate sản phẩm còn hàng
2. Tính tổng tiền (áp dụng coupon nếu có)
3. Tạo đơn với status \`pending\`
4. Gửi email xác nhận

**Lưu ý:**
- Mỗi coupon chỉ dùng được 1 lần
- Tối đa 50 items per order
  `,
})
@ApiBody({
  type: CreateOrderDto,
  examples: {
    basic: {
      summary: 'Đơn hàng cơ bản',
      value: {
        items: [{ productId: 1, quantity: 2 }],
        shippingAddressId: 5,
      },
    },
    withCoupon: {
      summary: 'Đơn hàng có coupon',
      value: {
        items: [{ productId: 1, quantity: 2 }],
        shippingAddressId: 5,
        couponCode: 'SALE20',
      },
    },
  },
})
async create(@Body() dto: CreateOrderDto) { ... }
```

*Tại sao:* Multiple examples giúp frontend và QA hiểu các use cases khác nhau mà không cần đọc source code. Markdown description cung cấp context mà summary ngắn không cover được.

---

### 2.10. Multiple Swagger Documents — tách docs theo audience

**✅ NÊN:** Tạo nhiều Swagger documents khi API phục vụ nhiều audiences (public, admin, internal).

```ts
// main.ts — Multiple docs
async function bootstrap() {
  const app = await NestFactory.create(AppModule);

  // Public API docs — cho frontend, partners
  const publicConfig = new DocumentBuilder()
    .setTitle('Public API')
    .setVersion('1.0')
    .addCookieAuth('accessToken')
    .build();
  const publicDoc = SwaggerModule.createDocument(app, publicConfig, {
    include: [ProductsModule, OrdersModule, AuthModule],
  });
  SwaggerModule.setup('api-docs', app, publicDoc);

  // Admin API docs — cho internal admin panel
  const adminConfig = new DocumentBuilder()
    .setTitle('Admin API')
    .setVersion('1.0')
    .addCookieAuth('accessToken')
    .build();
  const adminDoc = SwaggerModule.createDocument(app, adminConfig, {
    include: [AdminModule, ReportsModule],
  });
  SwaggerModule.setup('admin-docs', app, adminDoc);

  // Internal API docs — cho service-to-service
  const internalConfig = new DocumentBuilder()
    .setTitle('Internal API')
    .setVersion('1.0')
    .addApiKey({ type: 'apiKey', name: 'x-api-key', in: 'header' }, 'api-key')
    .build();
  const internalDoc = SwaggerModule.createDocument(app, internalConfig, {
    include: [InternalModule, WebhooksModule],
  });
  SwaggerModule.setup('internal-docs', app, internalDoc);

  await app.listen(3000);
}
```

*Tại sao:* Admin API thường chứa endpoints nhạy cảm (delete users, export data). Tách docs tránh expose admin endpoints cho public consumers. Mỗi audience chỉ thấy endpoints relevant.

> **Tham khảo:** [NestJS Multiple OpenAPI Documents](https://docs.nestjs.com/openapi/other-features#multiple-specifications)

---

### 2.11. `@ApiHeader` và `@ApiCookieAuth` cho custom headers

**✅ NÊN:** Document tất cả custom headers mà API yêu cầu.

```ts
@ApiHeader({
  name: 'x-request-id',
  description: 'Request tracing ID (UUID) — tự generate nếu không gửi',
  required: false,
  example: '550e8400-e29b-41d4-a716-446655440000',
})
@ApiHeader({
  name: 'x-tenant-id',
  description: 'Tenant ID cho multi-tenant apps',
  required: true,
  example: 'tenant-001',
})
@Controller('products')
export class ProductsController { ... }
```

*Tại sao:* Custom headers (tracing, tenant, locale) dễ bị bỏ sót trong docs. Thiếu header documentation → frontend gửi request thiếu header → 400/500 mà không biết tại sao.

---

### 2.12. Disable Swagger trong Production

**✅ NÊN:** Chỉ enable Swagger UI trong development/staging.

```ts
// main.ts — conditional Swagger
if (process.env.NODE_ENV !== 'production') {
  const config = new DocumentBuilder()
    .setTitle('API')
    .setVersion('1.0')
    .build();
  const document = SwaggerModule.createDocument(app, config);
  SwaggerModule.setup('api-docs', app, document);
}
```

Nếu cần Swagger trong production (cho partners), bảo vệ bằng authentication:

```ts
// main.ts — protect Swagger UI with basic auth
import { timingSafeEqual } from 'node:crypto';
import { ConfigService } from '@nestjs/config';
import type { NextFunction, Request, Response } from 'express';

const configService = app.get(ConfigService);
const docsUser = configService.getOrThrow<string>('SWAGGER_USER');
const docsPassword = configService.getOrThrow<string>('SWAGGER_PASSWORD');

const matches = (input: string, expected: string) => {
  const a = Buffer.from(input);
  const b = Buffer.from(expected);
  return a.length === b.length && timingSafeEqual(a, b);
};

// Register BEFORE SwaggerModule.setup(): setup() adds its routes immediately
app.use(['/api-docs', '/api-docs-json', '/api-docs-yaml'], (req: Request, res: Response, next: NextFunction) => {
  const [scheme, encoded = ''] = (req.headers.authorization ?? '').split(' ');
  const [user, ...rest] = Buffer.from(encoded, 'base64').toString('utf8').split(':');
  if (scheme === 'Basic' && matches(user, docsUser) && matches(rest.join(':'), docsPassword)) {
    return next();
  }
  res.setHeader('WWW-Authenticate', 'Basic realm="api-docs"');
  res.status(401).send('Unauthorized');
});

SwaggerModule.setup('api-docs', app, document, {
  swaggerOptions: {
    persistAuthorization: true,
  },
  customSiteTitle: 'API Documentation',
});
```

Middleware phải đăng ký trước `SwaggerModule.setup()`, vì `setup()` gắn route vào Express ngay lúc gọi. `/api-docs-json` và `/api-docs-yaml` là path riêng, `app.use('/api-docs')` không che được.

*Tại sao:* Swagger UI expose toàn bộ API contract, parameter names, response shapes. Attacker có thể dùng để tìm attack vectors. Production nên disable hoặc protect.

---

## 3. Ví dụ minh họa thực tế

### 3.1. Walkthrough: Setup API Documentation cho E-Commerce project

**Bước 1 — Cài đặt và cấu hình cơ bản**

```bash
pnpm add @nestjs/swagger
```

```json
// nest-cli.json — bật CLI plugin
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

**Bước 2 — Setup Swagger module trong `main.ts`**

```ts
import { VersioningType } from '@nestjs/common';
import { SwaggerModule, DocumentBuilder } from '@nestjs/swagger';

async function bootstrap() {
  const app = await NestFactory.create(AppModule);
  app.enableVersioning({ type: VersioningType.URI, defaultVersion: '1' }); // → /v1/... (see 3.1)

  if (process.env.NODE_ENV !== 'production') {
    const config = new DocumentBuilder()
      .setTitle('E-Commerce API')
      .setDescription(`
## Overview
Backend API for e-commerce platform.

## Authentication
- **JWT trong cookie `accessToken`**: Cho user-facing endpoints
- **API Key**: Cho service-to-service calls

## Rate Limiting
- Public endpoints: 100 req/min
- Authenticated endpoints: 500 req/min
      `)
      .setVersion('1.0')
      .setContact('Backend Team', 'https://internal.docs', 'backend@company.com')
      .addCookieAuth('accessToken') // security name: 'cookie'
      .addApiKey(
        { type: 'apiKey', name: 'x-api-key', in: 'header' },
        'api-key',
      )
      .addTag('auth', 'Authentication — login, register, refresh token')
      .addTag('products', 'Product management — CRUD, search, categories')
      .addTag('orders', 'Order management — create, status, history')
      .addTag('customers', 'Customer profiles — addresses, preferences')
      .build();

    const document = SwaggerModule.createDocument(app, config);
    SwaggerModule.setup('api-docs', app, document, {
      swaggerOptions: {
        persistAuthorization: true,
        tagsSorter: 'alpha',
        operationsSorter: 'alpha',
      },
    });
  }

  await app.listen(3000);
}
```

**Bước 3 — DTO với documentation đầy đủ**

```ts
// dto/create-order.dto.ts
export class OrderItemDto {
  @ApiProperty({ example: 1, description: 'Product ID' })
  @IsNumber() @IsPositive()
  productId: number;

  @ApiProperty({ example: 2, description: 'Số lượng', minimum: 1, maximum: 50 })
  @IsNumber() @Min(1) @Max(50)
  quantity: number;
}

export class CreateOrderDto {
  @ApiProperty({
    type: [OrderItemDto],
    description: 'Danh sách sản phẩm trong đơn',
    minItems: 1,
    maxItems: 50,
  })
  @ValidateNested({ each: true })
  @Type(() => OrderItemDto)
  @ArrayMinSize(1)
  @ArrayMaxSize(50)
  items: OrderItemDto[];

  @ApiProperty({ example: 5, description: 'ID địa chỉ giao hàng' })
  @IsNumber() @IsPositive()
  shippingAddressId: number;

  @ApiPropertyOptional({
    example: 'SALE20',
    description: 'Mã coupon giảm giá (optional)',
  })
  @IsString() @IsOptional()
  couponCode?: string;

  @ApiPropertyOptional({
    example: 'Giao giờ hành chính',
    description: 'Ghi chú giao hàng',
  })
  @IsString() @IsOptional() @MaxLength(500)
  note?: string;
}
```

**Bước 4 — Controller với response documentation đầy đủ**

```ts
@ApiTags('orders')
@ApiCookieAuth()
@Controller('orders')
export class OrdersController {
  constructor(private readonly ordersService: OrdersService) {}

  @Post()
  @ApiOperation({
    summary: 'Tạo đơn hàng',
    description: 'Tạo đơn hàng từ cart items. Validate stock, tính giá, áp dụng coupon.',
  })
  @ApiBody({
    type: CreateOrderDto,
    examples: {
      basic: {
        summary: 'Đơn hàng cơ bản',
        value: {
          items: [{ productId: 1, quantity: 2 }],
          shippingAddressId: 5,
        },
      },
      withCoupon: {
        summary: 'Đơn hàng có coupon',
        value: {
          items: [
            { productId: 1, quantity: 2 },
            { productId: 3, quantity: 1 },
          ],
          shippingAddressId: 5,
          couponCode: 'SALE20',
          note: 'Giao giờ hành chính',
        },
      },
    },
  })
  @ApiCreatedResponse({ type: OrderResponseDto, description: 'Tạo đơn thành công' })
  @ApiBadRequestResponse({ description: 'Validation failed, stock không đủ hoặc coupon không hợp lệ' })
  @ApiNotFoundResponse({ description: 'Product hoặc address không tồn tại' })
  async create(
    @CurrentUser() user: UserPayload,
    @Body() dto: CreateOrderDto,
  ): Promise<OrderResponseDto> {
    return this.ordersService.create(user.id, dto);
  }

  @Get()
  @ApiOperation({ summary: 'Lịch sử đơn hàng' })
  @ApiPaginatedResponse(OrderResponseDto)
  async findAll(
    @CurrentUser() user: UserPayload,
    @Query() query: ListOrderDto,
  ) {
    return this.ordersService.findByCustomer(user.id, query);
  }
}
```

**Bước 5 — Verify và export**

```bash
# Start dev server
pnpm start:dev

# Mở Swagger UI
open http://localhost:3000/api-docs

# Export OpenAPI JSON spec
curl http://localhost:3000/api-docs-json > openapi.json

# Export YAML (nếu cần)
curl http://localhost:3000/api-docs-yaml > openapi.yaml
```

---

### 3.2. Before/After: Từ docs nghèo nàn đến docs đầy đủ

**Before** — Swagger thiếu thông tin:

```ts
// ❌ Không có tags, không có auth scheme, không có examples
@Controller('orders')
export class OrdersController {
  @Post()
  async create(@Body() dto: CreateOrderDto) {
    return this.ordersService.create(dto);
  }

  @Get(':id')
  async findOne(@Param('id') id: string) {
    return this.ordersService.findOne(+id);
  }
}

// DTO không có @ApiProperty
export class CreateOrderDto {
  items: OrderItemDto[];  // Swagger không hiện
  shippingAddressId: number;  // Swagger không hiện
}
```

*Kết quả:* Swagger UI hiện endpoints nhưng: không có input schema, không có response schema, không có authentication, không có examples. Frontend phải hỏi backend mọi thứ.

**After** — Swagger đầy đủ:

```ts
// ✅ Tags, auth, full docs
@ApiTags('orders')
@ApiCookieAuth()
@Controller('orders')
export class OrdersController {
  @Post()
  @ApiOperation({ summary: 'Tạo đơn hàng' })
  @ApiBody({ type: CreateOrderDto, examples: { ... } })
  @ApiCreatedResponse({ type: OrderResponseDto })
  @ApiBadRequestResponse({ description: 'Validation failed hoặc stock không đủ' })
  async create(
    @CurrentUser() user: UserPayload,
    @Body() dto: CreateOrderDto,
  ): Promise<OrderResponseDto> { ... }
}

// DTO với @ApiProperty
export class CreateOrderDto {
  @ApiProperty({ type: [OrderItemDto], minItems: 1 })
  @ValidateNested({ each: true })
  @Type(() => OrderItemDto) // Without @Type, nested items are not validated
  items: OrderItemDto[];

  @ApiProperty({ example: 5 })
  @IsNumber()
  shippingAddressId: number;

  @ApiPropertyOptional({ example: 'SALE20' })
  @IsString()
  @IsOptional()
  couponCode?: string;
}
```

*Kết quả:* Swagger UI hiện đầy đủ: input schema với examples, response schema, auth button, error cases. Frontend tự tích hợp, QA tự test.

---

## 4. Tooling & Config

### 4.1. Checklist setup API Documentation

- [ ] Cài `@nestjs/swagger`: `pnpm add @nestjs/swagger`
- [ ] Bật CLI Plugin trong `nest-cli.json` (`classValidatorShim`, `introspectComments`)
- [ ] Setup `DocumentBuilder` trong `main.ts` (title, description, version, tags, auth schemes)
- [ ] Gọi `SwaggerModule.setup('api-docs', app, document)` — verify tại `http://localhost:3000/api-docs`
- [ ] `@ApiTags` cho mọi controller
- [ ] `@ApiOperation({ summary })` cho mọi endpoint
- [ ] `@ApiResponse` cho success, 400, 404 (ít nhất)
- [ ] `@ApiProperty({ example, description })` cho DTO fields quan trọng
- [ ] `@ApiCookieAuth` / `@ApiSecurity` cho protected endpoints
- [ ] `@ApiBody({ examples })` cho POST/PATCH endpoints có nhiều use cases
- [ ] Enum fields dùng `{ enum: EnumType, enumName: 'EnumName' }`
- [ ] Disable Swagger trong production (hoặc protect bằng auth)
- [ ] Export `openapi.json` cho frontend code generation

### 4.2. Useful SwaggerModule options

```ts
SwaggerModule.setup('api-docs', app, document, {
  swaggerOptions: {
    persistAuthorization: true,    // Giữ token sau reload
    tagsSorter: 'alpha',           // Sắp xếp tags A-Z
    operationsSorter: 'alpha',     // Sắp xếp endpoints A-Z
    docExpansion: 'none',          // Thu gọn mặc định (none/list/full)
    filter: true,                  // Search bar
    showRequestDuration: true,     // Hiện thời gian response
  },
  customSiteTitle: 'My API Documentation',
  customfavIcon: '/favicon.ico',
  customCss: '.swagger-ui .topbar { display: none }',
});
```

### 4.3. Export OpenAPI spec cho toolchain

```bash
# Export JSON
curl http://localhost:3000/api-docs-json > openapi.json

# Generate TypeScript client (dùng openapi-generator)
pnpm dlx @openapitools/openapi-generator-cli generate \
  -i openapi.json \
  -g typescript-axios \
  -o ./generated-client

# Import vào Postman
# Postman > Import > File > openapi.json
```

---

## References

- [NestJS OpenAPI Introduction](https://docs.nestjs.com/openapi/introduction) — Setup guide chính thức
- [NestJS OpenAPI Types and Parameters](https://docs.nestjs.com/openapi/types-and-parameters) — `@ApiProperty`, `@ApiQuery`, `@ApiParam`
- [NestJS OpenAPI Operations](https://docs.nestjs.com/openapi/operations) — `@ApiOperation`, `@ApiResponse`, `@ApiBody`
- [NestJS OpenAPI Security](https://docs.nestjs.com/openapi/security) — Bearer, API Key, OAuth2
- [NestJS CLI Plugin](https://docs.nestjs.com/openapi/cli-plugin) — Auto-infer types
- [NestJS Multiple Specifications](https://docs.nestjs.com/openapi/other-features#multiple-specifications) — Tách docs theo audience
- [NestJS Mapped Types](https://docs.nestjs.com/openapi/mapped-types) — `PartialType`, `PickType`, `OmitType`, `IntersectionType`
- [OpenAPI 3.0 Specification](https://swagger.io/specification/) — Full spec reference
- [OpenAPI File Upload](https://swagger.io/docs/specification/v3_0/describing-request-body/file-upload/) — File upload schema
- [Swagger UI Configuration](https://swagger.io/docs/open-source-tools/swagger-ui/usage/configuration/) — UI customization options

## Changelog

| Date | Version | Change | By |
| :---- | :---- | :---- | :---- |
| 2026-11-18 | v1.0 | Chuyển từ Notion "NestJS Document" (page `33d71a38d3b2813fabfafc3b6aa7804b`, sửa 2026-04-09). Review và sửa nội dung, code trước khi publish. Owner duyệt trong chat ngày 2026-11-18. | Bắc PV |
