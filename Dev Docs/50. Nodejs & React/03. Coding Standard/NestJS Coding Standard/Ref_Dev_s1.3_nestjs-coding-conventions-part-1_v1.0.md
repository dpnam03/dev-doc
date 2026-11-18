# NestJS Coding Standard 1.3 — Coding conventions (phần 1)

| Field | Value |
| :---- | :---- |
| Owner | Bắc PV — NodeJS BE Dev Lead |
| Audience | Dev (NodeJS BE) |
| Last reviewed | 2026-11-12 |
| Review cadence | Quarterly |
| Version | v1.0 |
| Linked from | Ref_Dev_nestjs-coding-standard_v1.0<br>Ref_Dev_s1.5_nestjs-coding-conventions-part-2_v1.0 |
| Status | Live |

Doc này là mục 1.3 của [NestJS Coding Standard](Ref_Dev_nestjs-coding-standard_v1.0.md), nhóm Nền tảng NestJS. Doc nêu coding conventions cho dự án NestJS, kèm lý do, ví dụ và config. Coding conventions chia làm hai doc để giữ độ dài dưới 2.000 từ; doc còn lại là [NestJS Coding Standard 1.5 — Coding conventions (phần 2)](Ref_Dev_s1.5_nestjs-coding-conventions-part-2_v1.0.md). Dev NodeJS BE đọc doc này khi viết code, review code và onboarding.

---

## 1. Tóm tắt & Phạm vi

Tài liệu này định nghĩa **coding standard và conventions** cho dự án NestJS. Nội dung bao gồm quy ước đặt tên, phân tầng trách nhiệm, TypeScript strict mode, và cách sử dụng decorators. Mục tiêu là thống nhất style code trong team để dễ review, dễ onboarding, và giảm friction khi cộng tác.

### 1.1. Scope áp dụng

- Toàn bộ code TypeScript trong `src/` của dự án NestJS.
- Áp dụng cho cả feature modules và common code.
- Không bao gồm config files (tsconfig, eslint) — xem trang **1.4 Project Setup & Build**.

---

## 2. Quy tắc & Giải thích

### 2.1. Quy ước đặt tên

✅ **Nên làm** — Tuân theo naming convention nhất quán:

| **Loại** | **Convention** | **Ví dụ** |
| --- | --- | --- |
| Module name | Số nhiều, lower-case, kebab-case | `products`, `order-items` |
| File name | `<name>.<type>.ts` | `products.controller.ts`, `create-product.dto.ts` |
| Class name | PascalCase, suffix theo type | `ProductsController`, `CreateProductDto`, `Product` |
| Variable / property | camelCase, tên gợi nghĩa | `totalPrice`, `isActive`, `createdAt` |
| Constant | UPPER\_SNAKE\_CASE (nếu primitive) hoặc camelCase (nếu object) | `MAX_RETRY_COUNT`, `defaultConfig` |
| Enum | PascalCase cho tên, UPPER\_SNAKE hoặc PascalCase cho value | `UserRole.ADMIN`, `OrderStatus.Pending` |
| Interface / Type | PascalCase, không prefix `I` | `UserPayload`, `PaginationOptions` |

**Tại sao**: Naming nhất quán giúp developer tìm file nhanh, hiểu vai trò của class/file ngay từ tên, và giảm cognitive load khi đọc code. Suffix `.controller.ts`, `.service.ts` giúp phân biệt ngay vai trò mà không cần mở file.

❌ **Không nên làm** — Dùng tên mơ hồ hoặc không theo convention:

```ts
// ❌ KHÔNG NÊN
utils.ts              // Mơ hồ — utils cho cái gì?
helper.service.ts     // Quá chung — helper cho module nào?
ProductManager.ts     // Thiếu suffix, không rõ là controller hay service
IUserService.ts       // Prefix "I" không cần thiết trong TypeScript

// ✅ NÊN
product-pricing.util.ts        // Rõ ràng scope
products.service.ts            // Đúng convention
products.controller.ts         // Rõ vai trò
user-service.interface.ts      // Nếu cần interface riêng
```

### 2.2. Phân tầng trách nhiệm (Layering)

✅ **Nên làm** — Mỗi layer có trách nhiệm rõ ràng, không xâm phạm layer khác:

- **Controller**: mapping HTTP routes + validate input + gọi service. **Không** chứa business logic.
- **Service**: chứa business logic, tính toán, orchestrate repository/external calls.
- **Repository** (nếu tách): chỉ lo truy vấn DB, không chứa business rules.
- **Guard / Interceptor / Filter / Pipe**: cross-cutting concerns (auth, logging, format response).

**Tại sao**: Tách layer giúp test dễ (mock service khi test controller), thay đổi DB layer không ảnh hưởng business logic, và code dễ navigate.

```ts
// ✅ NÊN — Controller chỉ delegate, không có logic
@Controller('products')
export class ProductsController {
  constructor(private readonly productsService: ProductsService) {}

  @Post()
  async create(@Body() dto: CreateProductDto) {
    return this.productsService.create(dto);
  }

  @Get()
  async findAll(@Query() query: ListProductDto) {
    return this.productsService.findAll(query);
  }
}
```

```ts
// ❌ KHÔNG NÊN — Controller chứa business logic
@Controller('products')
export class ProductsController {
  constructor(
    @InjectRepository(Product) private repo: Repository<Product>,
  ) {}

  @Post()
  async create(@Body() dto: CreateProductDto) {
    // Business logic trong controller — sai layer!
    const existingProduct = await this.repo.findOne({ where: { sku: dto.sku } });
    if (existingProduct) {
      throw new ConflictException(`Product with SKU ${dto.sku} already exists`);
    }
    const price = dto.basePrice * (1 - dto.discount / 100);
    const product = this.repo.create({ ...dto, finalPrice: price });
    return this.repo.save(product);
  }
}
```

### 2.3. TypeScript Strict Mode

✅ **Nên làm** — Bật `strict: true` trong `tsconfig.json` và tuân thủ:

- Luôn khai báo type cho function parameters và return type (ít nhất cho public methods).
- Không dùng `any` trừ trường hợp bất khả kháng — ưu tiên `unknown` rồi narrowing.
- Dùng `readonly` cho properties không cần thay đổi.
- Dùng optional chaining (`?.`) và nullish coalescing (`??`) thay vì check thủ công.

**Tại sao**: Strict mode bắt lỗi tại compile time thay vì runtime. Tránh `any` giúp IDE gợi ý chính xác, refactor an toàn, và giảm bug. Đây là lợi thế lớn nhất của TypeScript so với JavaScript.

```ts
// ✅ NÊN — type rõ ràng, dùng unknown + narrowing
async function parseConfig(raw: unknown): Promise<AppConfig> {
  if (!isValidConfig(raw)) {
    throw new BadRequestException('Invalid config format');
  }
  return raw; // TypeScript biết raw là AppConfig sau narrowing
}

// Dùng readonly cho DI dependencies
@Injectable()
export class ProductsService {
  constructor(
    private readonly productsRepository: ProductsRepository,
    private readonly configService: ConfigService,
  ) {}
}
```

```ts
// ❌ KHÔNG NÊN — dùng any, thiếu type
async function parseConfig(raw: any) {  // any = mất hết type safety
  return raw.database.host;             // runtime error nếu structure sai
}

// Thiếu readonly, thiếu access modifier
@Injectable()
export class ProductsService {
  constructor(
    productsRepository: ProductsRepository,  // Thiếu private readonly
  ) {}
}
```

### 2.4. Sử dụng Decorators đúng cách

✅ **Nên làm** — Dùng decorators của NestJS theo đúng mục đích, tạo custom decorator khi logic lặp lại:

```ts
// ✅ Custom decorator thay vì lặp logic extract user trong mọi handler
export const CurrentUser = createParamDecorator(
  (data: unknown, ctx: ExecutionContext) => {
    const request = ctx.switchToHttp().getRequest();
    return request.user;
  },
);

// Sử dụng — clean và reusable
@Get('profile')
async getProfile(@CurrentUser() user: UserPayload) {
  return this.usersService.getProfile(user.id);
}
```

```ts
// ❌ KHÔNG NÊN — lặp lại logic extract user ở mọi handler
@Get('profile')
async getProfile(@Req() req: Request) {
  const user = req.user; // Lặp lại ở mọi handler
  return this.usersService.getProfile(user.id);
}

@Get('settings')
async getSettings(@Req() req: Request) {
  const user = req.user; // Lại lặp...
  return this.usersService.getSettings(user.id);
}
```

✅ **Nên làm** — Compose decorators khi một route cần nhiều decorators lặp lại:

```ts
// ✅ Compose decorator cho admin-only endpoints
export function AdminOnly() {
  return applyDecorators(
    Roles(Role.ADMIN), // Global JwtAuthGuard + RolesGuard check it (5.1 section 2.4)
    ApiCookieAuth(),
    ApiUnauthorizedResponse({ description: 'Unauthorized' }),
  );
}

// Sử dụng — 1 decorator thay vì 3
@AdminOnly()
@Delete(':id')
async remove(@Param('id') id: string) {
  return this.productsService.remove(id);
}
```

### 2.5. Độ phức tạp file & method

✅ **Nên làm** — Giữ file và method ở kích thước hợp lý:

- 1 file controller/service: **\< 300–400 dòng** (định hướng, không phải hard limit).
- 1 method: **\< 40–50 dòng**. Nếu dài hơn → tách helper/private method.
- 1 file chỉ export **1 class chính** (single responsibility).

**Tại sao**: File/method ngắn dễ đọc, dễ review, dễ test. Khi file vượt ngưỡng, đó là tín hiệu cần refactor — tách service con, tách utility, hoặc chia module.

❌ **Không nên làm** — Một service “thần” chứa mọi logic:

```ts
// ❌ KHÔNG NÊN — OrdersService 800+ dòng, chứa mọi thứ
@Injectable()
export class OrdersService {
  async create() { /* 80 dòng CRUD */ }
  async calculatePrice() { /* 60 dòng pricing */ }
  async processPayment() { /* 100 dòng payment */ }
  async syncToERP() { /* 70 dòng integration */ }
  async cancelExpiredOrders() { /* 50 dòng cron logic */ }
  // ... còn nữa
}
```

```ts
// ✅ NÊN — tách service con theo nhóm logic
// core/orders.service.ts — entry point, CRUD
// core/order-pricing.service.ts — logic tính giá, discount
// core/order-payment.service.ts — logic thanh toán/refund
// integrations/order-external.service.ts — gọi hệ thống ngoài
// cron/order-timeout.job.ts — cron xử lý đơn timeout
```

### 2.6. Format response & error chuẩn

✅ **Nên làm** — Thống nhất format response cho toàn bộ API:

**Response thành công** (xử lý bởi global interceptor):

```json
{
  "data": { ... },
  "requestId": "abc-123",
  "timestamp": "2026-11-17T10:00:00.000Z"
}
```

**Response lỗi** (xử lý bởi global exception filter):

```json
{
  "error": {
    "type": "VALIDATION_ERROR",
    "code": "VALIDATION_ERROR",
    "message": "email must be an email",
    "param": "email",
    "details": [{ "field": "email", "message": "email must be an email" }],
    "path": "/api/products",
    "requestId": "abc-123",
    "timestamp": "2026-11-17T10:00:00.000Z"
  }
}
```

Response không có field `success`, vì HTTP status đã cho biết thành công hay lỗi. Format đầy đủ ở [NestJS Coding Standard 3.1 — REST API Design](Ref_Dev_s3.1_nestjs-rest-api-design_v1.0.md) mục 2.4.

**Tại sao**: Format nhất quán giúp frontend dễ handle, dễ viết error handler chung. Global interceptor + filter đảm bảo mọi endpoint đều tuân thủ mà không cần developer nhớ format thủ công.

| **Exception** | **Status** | **`type`** | **`code`** |
| --- | --- | --- | --- |
| Custom exception (body có `code`) | Từ exception | Từ body, nếu không có thì theo status | Từ body |
| `HttpException` built-in | Từ exception | Theo status | Tên HTTP status, ví dụ `NOT_FOUND` |
| ValidationPipe với `validationExceptionFactory` | 400 | `VALIDATION_ERROR` | `VALIDATION_ERROR` |
| Exception không xác định | 500 | `SERVER_ERROR` | `INTERNAL_SERVER_ERROR` |

### 2.7. Import & Module organization

✅ **Nên làm** — Sắp xếp imports theo nhóm, dùng barrel exports khi hợp lý:

```ts
// 1. NestJS / framework imports
import { Injectable, NotFoundException } from '@nestjs/common';
import { InjectRepository } from '@nestjs/typeorm';

// 2. Third-party imports
import { Repository } from 'typeorm';

// 3. Internal imports — common
import { PaginationDto } from '../../common/dto/pagination.dto';

// 4. Internal imports — same module
import { Product } from './entities/product.entity';
import { CreateProductDto } from './dto/create-product.dto';
```

**Tại sao**: Nhóm imports giúp nhanh chóng nhận ra dependencies của file — framework, third-party, hay internal. ESLint có thể enforce tự động.

### 2.8. Comments & Documentation

✅ **Nên làm** — Viết JSDoc cho public methods của service, đặc biệt khi method có side effects hoặc logic phức tạp:

```ts
// ✅ NÊN — JSDoc cho public method có logic không hiển nhiên
@Injectable()
export class OrderPricingService {
  /**
   * Tính giá cuối cùng sau khi áp dụng discount và thuế VAT.
   * Discount được áp dụng trước thuế.
   * Nếu customer là VIP, cộng thêm 5% discount.
   */
  calculateFinalPrice(
    basePrice: number,
    discountPercent: number,
    customer: Customer,
  ): number {
    const vipBonus = customer.isVip ? 5 : 0;
    const discounted = basePrice * (1 - (discountPercent + vipBonus) / 100);
    return Math.round(discounted * 1.1); // VAT 10%
  }
}
```

✅ **Nên làm** — Dùng `TODO`, `FIXME`, `HACK` với format chuẩn kèm tên người và context:

```ts
// TODO(bacpv): Thêm retry logic khi payment gateway timeout — ticket #234
// FIXME(bacpv): Race condition khi 2 request cùng update stock — cần pessimistic lock
// HACK(bacpv): Workaround cho bug TypeORM cascade delete — remove khi upgrade v0.4
```

❌ **Không nên làm** — Comment giải thích điều hiển nhiên, hoặc TODO không có context:

```ts
// ❌ KHÔNG NÊN
// Lấy user theo id
const user = await this.usersService.findById(id);

// TODO: fix later   ← fix cái gì? khi nào? ai?
// Set price
product.price = dto.price;
```

**Tại sao:** Comment tốt giải thích *tại sao* chứ không phải *cái gì*. Code tốt tự giải thích cái gì. TODO/FIXME có context giúp team track được technical debt — không có context thì sẽ bị bỏ quên mãi mãi.

---

### 2.9. Async/Await patterns

✅ **Nên làm** — Dùng `Promise.all` khi các async calls không phụ thuộc nhau:

```ts
// ✅ NÊN — chạy song song, nhanh hơn đáng kể
async getOrderSummary(orderId: string): Promise<OrderSummary> {
  const [order, customer, payments] = await Promise.all([
    this.ordersRepository.findById(orderId),
    this.customersService.findByOrderId(orderId),
    this.paymentsService.findByOrderId(orderId),
  ]);

  return { order, customer, payments };
}
```

❌ **Không nên làm** — Await tuần tự khi các calls độc lập nhau:

```ts
// ❌ KHÔNG NÊN — 3 calls tuần tự, tổng thời gian = sum(3 calls)
async getOrderSummary(orderId: string): Promise<OrderSummary> {
  const order = await this.ordersRepository.findById(orderId);
  const customer = await this.customersService.findByOrderId(orderId);
  const payments = await this.paymentsService.findByOrderId(orderId);

  return { order, customer, payments };
}
```

✅ **Nên làm** — Luôn handle errors trong Promise.all khi cần partial results:

```ts
// ✅ NÊN — dùng Promise.allSettled khi cho phép partial failure
const results = await Promise.allSettled([
  this.emailService.send(order.customerEmail, template),
  this.smsService.send(order.customerPhone, message),
  this.slackService.notify(channel, notification),
]);

const failures = results.filter((r) => r.status === 'rejected');
if (failures.length > 0) {
  this.logger.warn({ message: 'Some notifications failed', failures });
}
```

**Tại sao:** Sequential await cho independent calls lãng phí thời gian. Nếu mỗi call mất 100ms, 3 calls tuần tự = 300ms, song song = \~100ms. Với `Promise.allSettled`, một call fail không block các calls khác.

---

## 3. Ví dụ minh họa thực tế

### 3.1. Module đơn giản — Product (áp dụng đầy đủ conventions)

```ts
// api/admin/products.controller.ts
@Controller('products')
@ApiTags('Products')
export class ProductsController {
  constructor(private readonly productsService: ProductsService) {}

  @Post()
  @ApiOperation({ summary: 'Tạo sản phẩm mới' })
  async create(@Body() createProductDto: CreateProductDto): Promise<Product> {
    return this.productsService.create(createProductDto);
  }

  @Get()
  @ApiOperation({ summary: 'Danh sách sản phẩm' })
  async findAll(@Query() query: ListProductDto): Promise<PaginatedResult<Product>> {
    return this.productsService.findAll(query);
  }

  @Get(':id')
  @ApiOperation({ summary: 'Chi tiết sản phẩm' })
  async findOne(@Param('id', ParseIntPipe) id: number): Promise<Product> {
    return this.productsService.findOne(id);
  }

  @Patch(':id')
  @AdminOnly()
  @ApiOperation({ summary: 'Cập nhật sản phẩm (admin)' })
  async update(
    @Param('id', ParseIntPipe) id: number,
    @Body() updateProductDto: UpdateProductDto,
  ): Promise<Product> {
    return this.productsService.update(id, updateProductDto);
  }
}
```

**Walkthrough**:

- **Naming**: `ProductsController` (PascalCase + suffix), `create-product.dto.ts` (kebab-case + suffix).
- **Layering**: Controller chỉ delegate cho service, không có business logic.
- **TypeScript**: Return types khai báo rõ ràng (`Promise<Product>`).
- **Decorators**: Swagger decorators cho documentation, `@AdminOnly()` composed decorator cho authorization.
- **Pipes**: `ParseIntPipe` cho param transformation.

### 3.2. Tách module phức tạp — Orders

Khi module Orders có nhiều nhóm logic, tách service con:

```txt
src/api/user/orders.controller.ts    # Controller lives in api/ (1.1 section 2.2)
src/modules/orders/
├── orders.module.ts
├── entities/
│   └── order.entity.ts
├── dto/
│   ├── create-order.dto.ts
│   └── list-order.dto.ts
├── core/
│   ├── orders.service.ts           # CRUD cơ bản, entry point
│   ├── order-pricing.service.ts    # Logic tính giá, discount
│   ├── order-payment.service.ts    # Logic thanh toán/refund
│   └── order-status.service.ts     # Đổi trạng thái, rule trạng thái
├── integrations/
│   └── order-external.service.ts   # Gọi hệ thống ngoài (ERP, payment)
└── cron/
    └── order-timeout.job.ts        # Cron xử lý đơn timeout
```

**Nguyên tắc**:

- `OrdersService` (core) là entry point — controller chỉ biết service này.
- Các service con inject lẫn nhau nhưng tránh phụ thuộc vòng.
- Mỗi file chịu trách nhiệm 1 nhóm logic rõ ràng.

### 3.3. Before/After — Custom exception thay vì throw trực tiếp

❌ **Before** (throw generic exception, message lặp lại):

```ts
// Lặp lại ở nhiều nơi, message không nhất quán
throw new NotFoundException('Product not found');
throw new NotFoundException('Không tìm thấy sản phẩm');
throw new NotFoundException('product not found with id: ' + id);
```

✅ **After** (custom exception, code + message chuẩn):

```ts
// modules/products/exceptions/product.exceptions.ts
export class ProductNotFoundException extends NotFoundException {
  constructor(id: number) {
    super({
      code: 'PRODUCT_NOT_FOUND',
      message: `Product ${id} not found`,
    });
  }
}

// Sử dụng — nhất quán, dễ trace
throw new ProductNotFoundException(id);
```

## 4. Tooling & Config

### 4.1. TypeScript config

```json
// tsconfig.json — các option quan trọng
{
  "compilerOptions": {
    "strict": true,
    "strictNullChecks": true,
    "strictPropertyInitialization": false,
    "noImplicitAny": true,
    "noUnusedLocals": true,
    "noUnusedParameters": true,
    "forceConsistentCasingInFileNames": true,
    "esModuleInterop": true,
    "skipLibCheck": true,
    "declaration": true,
    "removeComments": true,
    "emitDecoratorMetadata": true,
    "experimentalDecorators": true
  }
}
```

`strictPropertyInitialization: false` vì property của DTO và entity không có initializer, giá trị do class-transformer hoặc ORM gán lúc runtime. Bật option này thì mọi DTO lỗi TS2564.

### 4.2. ESLint & Prettier

- **ESLint**: enforce naming conventions, import order, no-any rule.
- **Prettier**: format code tự động, không cần tranh luận về style.

```bash
# Cài đặt
pnpm add -D eslint @eslint/js typescript-eslint globals prettier eslint-config-prettier eslint-plugin-prettier  # nest new (NestJS 11) already adds these

# Scripts trong package.json
"lint": "eslint 'src/**/*.ts' --fix",
"format": "prettier --write 'src/**/*.ts'"
```

### 4.3. EditorConfig

Tạo file `.editorconfig` ở root project để đồng nhất indent, EOL, charset giữa các IDE (VS Code, WebStorm, Vim, etc.):

```txt
# .editorconfig
root = true

[*]
charset = utf-8
indent_style = space
indent_size = 2
end_of_line = lf
insert_final_newline = true
trim_trailing_whitespace = true

[*.md]
trim_trailing_whitespace = false

[*.{json,yml,yaml}]
indent_size = 2
```

**Mục đích:** Đảm bảo mọi editor dùng cùng indent (2 spaces), cùng line ending (LF), cùng charset (UTF-8) — tránh diff noise do mixed tabs/spaces hoặc CRLF/LF.

**Yêu cầu:** Cài extension EditorConfig cho IDE (`editorconfig.editorconfig` trên VS Code).

---

### 4.4. Path aliases (tsconfig.paths)

Cấu hình path aliases để tránh import dài `../../../common/...`:

```json
// tsconfig.json
{
  "compilerOptions": {
    "paths": {
      "@common/*": ["./src/common/*"],
      "@modules/*": ["./src/modules/*"],
      "@config/*": ["./src/config/*"]
    }
  }
}
```

Không khai báo `baseUrl`: TypeScript 6 báo deprecated, TypeScript 7 báo lỗi. Target trong `paths` viết dạng tương đối `./src/...`.

**Trước và sau:**

```ts
// ❌ Trước — relative path dài, khó refactor
import { PaginationDto } from '../../../common/dto/pagination.dto';
import { Product } from '../../products/entities/product.entity';

// ✅ Sau — rõ ràng, dễ đọc, không thay đổi khi move file
import { PaginationDto } from '@common/dto/pagination.dto';
import { Product } from '@modules/products/entities/product.entity';
```

**Lưu ý:** Nếu dùng Jest, cần cấu hình thêm `moduleNameMapper` trong `jest.config.ts`:

```ts
// jest.config.ts
moduleNameMapper: {
  '^@common/(.*)$': '<rootDir>/src/common/$1',
  '^@modules/(.*)$': '<rootDir>/src/modules/$1',
  '^@config/(.*)$': '<rootDir>/src/config/$1',
}
```

---

### 4.5. ESLint rules khuyến nghị chi tiết

Ngoài config cơ bản ở [NestJS Coding Standard 1.4 — Project Setup & Build](Ref_Dev_s1.4_nestjs-project-setup-build_v1.0.md) mục 2.3, thêm các rules sau vào `eslint.config.mjs` để enforce coding standards tự động:

```javascript
// eslint.config.mjs — add these to the config of 1.4 section 2.3
import importPlugin from 'eslint-plugin-import';

export default tseslint.config(
  // ...config from 1.4 section 2.3
  {
    plugins: { import: importPlugin },
    settings: {
      // Resolves tsconfig path aliases, so @common/* is grouped as internal
      'import/resolver': { typescript: true, node: true },
    },
    rules: {
      // === TypeScript ===
      '@typescript-eslint/no-explicit-any': 'error',
      '@typescript-eslint/no-unused-vars': ['error', { argsIgnorePattern: '^_' }],
      '@typescript-eslint/no-floating-promises': 'error',
      '@typescript-eslint/prefer-nullish-coalescing': 'warn',
      '@typescript-eslint/prefer-optional-chain': 'warn',
      // Replaces the deprecated core rule no-return-await
      '@typescript-eslint/return-await': ['error', 'in-try-catch'],

      // === Import order ===
      'import/order': [
        'error',
        {
          groups: [
            'builtin',       // Node.js built-in
            'external',      // npm packages
            'internal',      // path aliases (@common, @modules)
            'parent',        // ../
            'sibling',       // ./
          ],
          'newlines-between': 'always',
          alphabetize: { order: 'asc' },
        },
      ],

      // === General ===
      'no-console': ['warn', { allow: ['warn', 'error'] }],
      'prefer-const': 'error',
      'no-var': 'error',
    },
  },
);
```

**Cài đặt plugin import:**

```bash
pnpm add -D eslint-plugin-import eslint-import-resolver-typescript
```

**Giải thích các rules chính:**

| Rule | Mục đích |
| --- | --- |
| `no-explicit-any` | Buộc dùng type cụ thể thay vì `any` |
| `no-floating-promises` | Bắt promise không được await hoặc handle |
| `prefer-nullish-coalescing` | Gợi ý dùng `??` thay `\|\|` |
| `import/order` | Tự động sắp xếp imports theo nhóm |
| `no-console` | Ngăn `console.log` lọt vào code (dùng Logger) |
| `prefer-const` | Buộc dùng `const` khi không reassign |

---

## References

- [NestJS Documentation](https://docs.nestjs.com/)
- [NestJS Custom Decorators](https://docs.nestjs.com/custom-decorators)
- [NestJS Controllers](https://docs.nestjs.com/controllers)
- [NestJS Providers & DI](https://docs.nestjs.com/providers)
- [NestJS Circular Dependency](https://docs.nestjs.com/fundamentals/circular-dependency)
- [NestJS Mapped Types](https://docs.nestjs.com/openapi/mapped-types)
- [TypeScript Handbook — Strict Mode](https://www.typescriptlang.org/tsconfig#strict)
- [ESLint TypeScript Plugin](https://typescript-eslint.io/)
- [eslint-plugin-import](https://github.com/import-js/eslint-plugin-import)
- [Prettier Documentation](https://prettier.io/docs/en/)
- [EditorConfig](https://editorconfig.org/)
- [Conventional Commits](https://www.conventionalcommits.org/)
- [pnpm — Motivation](https://pnpm.io/motivation)

## Changelog

| Date | Version | Change | By |
| :---- | :---- | :---- | :---- |
| 2026-11-18 | v1.0 | Chuyển từ Notion "NestJS Document" (page `33d71a38d3b281248d9cfe1b307dd36c`, sửa 2026-04-09). Tách từ trang "1 3 Coding standard & Coding conventions" thành 1.3 và 1.5. Review và sửa nội dung, code trước khi publish. Owner duyệt trong chat ngày 2026-11-18. | Bắc PV |
