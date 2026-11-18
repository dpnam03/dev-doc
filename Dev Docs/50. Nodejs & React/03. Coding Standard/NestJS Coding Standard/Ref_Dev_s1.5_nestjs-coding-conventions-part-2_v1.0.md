# NestJS Coding Standard 1.5 — Coding conventions (phần 2)

| Field | Value |
| :---- | :---- |
| Owner | Bắc PV — NodeJS BE Dev Lead |
| Audience | Dev (NodeJS BE) |
| Last reviewed | 2026-11-12 |
| Review cadence | Quarterly |
| Version | v1.0 |
| Linked from | Ref_Dev_nestjs-coding-standard_v1.0<br>Ref_Dev_s1.3_nestjs-coding-conventions-part-1_v1.0 |
| Status | Live |

Doc này là mục 1.5 của [NestJS Coding Standard](Ref_Dev_nestjs-coding-standard_v1.0.md), nhóm Nền tảng NestJS. Doc nêu coding conventions cho dự án NestJS, kèm lý do, ví dụ và config. Coding conventions chia làm hai doc để giữ độ dài dưới 2.000 từ; doc còn lại là [NestJS Coding Standard 1.3 — Coding conventions (phần 1)](Ref_Dev_s1.3_nestjs-coding-conventions-part-1_v1.0.md). Dev NodeJS BE đọc doc này khi viết code, review code và onboarding.

---

## 1. Tóm tắt & Phạm vi

Tài liệu này là phần 2 của coding standard và conventions cho dự án NestJS. Phần này gồm magic numbers, barrel exports, Git commit, Dependency Injection và circular dependency. Phần này cũng gồm generic types, null/undefined và immutability.

Phần 1 (đặt tên, phân tầng, TypeScript strict mode, decorators) nằm ở [NestJS Coding Standard 1.3 — Coding conventions (phần 1)](Ref_Dev_s1.3_nestjs-coding-conventions-part-1_v1.0.md).

### 1.1 Scope áp dụng

- Toàn bộ code TypeScript trong `src/` của dự án NestJS.
- Áp dụng cho cả feature modules và common code.
- Không bao gồm config files (tsconfig, eslint) — xem trang **1.4 Project Setup & Build**.

---

## 2. Quy tắc & Giải thích

### 2.1. Magic numbers & string literals

✅ **Nên làm** — Extract magic numbers và string literals ra constants hoặc enums:

```ts
// ✅ NÊN — constants có tên gợi nghĩa
// modules/orders/constants/order.constants.ts
export const ORDER_CONSTANTS = {
  MAX_ITEMS_PER_ORDER: 50,
  PAYMENT_TIMEOUT_MS: 30_000,
  AUTO_CANCEL_AFTER_HOURS: 24,
} as const;

export enum OrderStatus {
  PENDING = 'pending',
  CONFIRMED = 'confirmed',
  SHIPPED = 'shipped',
  DELIVERED = 'delivered',
  CANCELLED = 'cancelled',
}

// Sử dụng
if (order.items.length > ORDER_CONSTANTS.MAX_ITEMS_PER_ORDER) {
  throw new BadRequestException(
    `An order cannot have more than ${ORDER_CONSTANTS.MAX_ITEMS_PER_ORDER} items`,
  );
}
```

❌ **Không nên làm** — Hardcode giá trị trực tiếp trong logic:

```ts
// ❌ KHÔNG NÊN — 50 là gì? 30000 là gì? 'pending' có bao nhiêu chỗ dùng?
if (order.items.length > 50) {
  throw new BadRequestException('Too many items');
}

setTimeout(() => cancelOrder(orderId), 30000);

if (order.status === 'pending') { ... }
```

**Tại sao:** Magic numbers/strings khiến code khó hiểu (50 nghĩa là gì?), khó refactor (thay đổi limit phải tìm tất cả chỗ dùng), và dễ typo (`'pendding'` vs `'pending'`). Constants và enums giải quyết cả 3 vấn đề.

---

### 2.2. Barrel exports (index.ts)

✅ **Nên làm** — Dùng barrel export cho public API của module, đặc biệt thư mục `dto/`, `entities/`, `exceptions/`:

```ts
// modules/products/dto/index.ts
export { CreateProductDto } from './create-product.dto';
export { UpdateProductDto } from './update-product.dto';
export { ListProductDto } from './list-product.dto';

// Import gọn gàng từ bên ngoài module
import { CreateProductDto, ListProductDto } from '../products/dto';
```

❌ **Không nên làm** — Barrel export ở cấp module root khi module có circular dependencies:

```ts
// ❌ KHÔNG NÊN — barrel ở root module dễ gây circular import
// modules/orders/index.ts
export * from './orders.service';     // Service import từ products
export * from './orders.controller';
export * from './entities/order.entity';
// Nếu products cũng export * và import từ orders → circular!
```

**Tại sao:** Barrel exports giúp import gọn gàng và ẩn internal structure. Nhưng dùng ở cấp module root khi modules import lẫn nhau sẽ gây circular dependency — Node.js resolve được nhưng có thể trả về `undefined` tại runtime. **Đề xuất**: chỉ barrel export ở cấp subfolder (`dto/`, `entities/`), không ở cấp module root.

---

### 2.3. Git commit conventions

✅ **Nên làm** — Tuân theo Conventional Commits format:

```txt
<type>(<scope>): <description>

[optional body]
[optional footer]
```

**Các type thường dùng:**

| Type | Khi nào dùng | Ví dụ |
| --- | --- | --- |
| `feat` | Thêm feature mới | `feat(products): add bulk import API` |
| `fix` | Sửa bug | `fix(orders): fix race condition on stock update` |
| `refactor` | Refactor không đổi behavior | `refactor(auth): extract token validation to guard` |
| `chore` | Maintenance, config, deps | `chore: upgrade @nestjs/core to 11.2.7` |
| `docs` | Cập nhật tài liệu | `docs(readme): add setup instructions` |
| `test` | Thêm/sửa test | `test(orders): add unit tests for pricing service` |
| `style` | Format, whitespace | `style: run prettier on all files` |

❌ **Không nên làm** — Commit message mơ hồ hoặc gộp nhiều thay đổi:

```txt
❌ "fix bug"
❌ "update code"
❌ "wip"
❌ "fix bug + add feature + refactor service"  ← nên tách 3 commits
```

**Tại sao:** Conventional Commits giúp tự động generate changelog, dễ `git log` tìm kiếm, và dễ revert khi cần. Mỗi commit = 1 thay đổi logic, giúp bisect nhanh khi tìm bug.

**Tham khảo:** [Conventional Commits](https://www.conventionalcommits.org/)

### 2.4. Dependency Injection conventions

✅ **Nên làm** — Luôn inject qua constructor với `private readonly`, giới hạn số lượng dependencies:

```ts
// ✅ NÊN — clean DI, ≤ 5 dependencies
@Injectable()
export class OrdersService {
  // Logger is created, not injected: Nest has no provider for it
  private readonly logger = new Logger(OrdersService.name);

  constructor(
    private readonly ordersRepository: OrdersRepository,
    private readonly pricingService: OrderPricingService,
    private readonly paymentService: OrderPaymentService,
  ) {}
}
```

❌ **Không nên làm** — Inject quá nhiều dependencies (>5) hoặc inject trực tiếp repository vào controller:

```ts
// ❌ KHÔNG NÊN — 7 dependencies = signal cần tách service
@Injectable()
export class OrdersService {
  constructor(
    private readonly ordersRepo: OrdersRepository,
    private readonly productsRepo: ProductsRepository,
    private readonly customersService: CustomersService,
    private readonly paymentService: PaymentService,
    private readonly shippingService: ShippingService,
    private readonly notificationService: NotificationService,
    private readonly analyticsService: AnalyticsService,
  ) {}
}

// ❌ KHÔNG NÊN — Controller inject repository trực tiếp
@Controller('orders')
export class OrdersController {
  constructor(
    @InjectRepository(Order) private repo: Repository<Order>, // Sai layer!
  ) {}
}
```

**Tại sao:** Quá nhiều dependencies cho thấy class làm quá nhiều việc (vi phạm Single Responsibility). Ngưỡng 5 là hướng dẫn — khi vượt, hãy tách thành orchestrator + service con. Controller không nên biết DB layer.

---

### 2.5. Circular dependency & module coupling

✅ **Nên làm** — Tách shared logic ra một feature module riêng và export service, tránh hai feature module import lẫn nhau. Không đặt vào `common/` vì `common/` không chứa logic nghiệp vụ (mục 2.1 của [1.1 Cấu trúc dự án](Ref_Dev_s1.1_nestjs-project-structure_v1.0.md)):

```ts
// ✅ NÊN — shared logic lives in its own feature module
// modules/notifications/notifications.service.ts
@Injectable()
export class NotificationsService {
  async notify(userId: string, message: string): Promise<void> {
    // send via email / push provider
  }
}

// modules/notifications/notifications.module.ts
@Module({
  providers: [NotificationsService],
  exports: [NotificationsService],
})
export class NotificationsModule {}

// orders.module.ts — imports NotificationsModule, not ProductsModule
@Module({
  imports: [NotificationsModule],
  providers: [OrdersService],
})
export class OrdersModule {}
```

❌ **Không nên làm** — Hai module import lẫn nhau trực tiếp:

```ts
// ❌ KHÔNG NÊN — circular dependency
// orders.module.ts
@Module({ imports: [ProductsModule] }) // Orders depends on Products
export class OrdersModule {}

// products.module.ts
@Module({ imports: [OrdersModule] })   // Products depends on Orders → CIRCULAR!
export class ProductsModule {}
```

✅ **Nếu bắt buộc phải circular** — dùng `forwardRef()` và comment rõ lý do:

```ts
// ✅ Chấp nhận được nếu có lý do chính đáng
@Module({
  imports: [
    forwardRef(() => ProductsModule), // Circular: Orders cần check stock từ Products
  ],
})
export class OrdersModule {}
```

**Tại sao:** Circular dependencies làm code khó test, khó refactor, và có thể gây `undefined` tại runtime. `forwardRef` là workaround, không phải giải pháp — ưu tiên tách shared logic.

**Tham khảo:** [NestJS Circular Dependency](https://docs.nestjs.com/fundamentals/circular-dependency)

---

### 2.6. Generic types & utility types

✅ **Nên làm** — Dùng TypeScript utility types thay vì duplicate type definitions:

```ts
// ✅ NÊN — dùng utility types của NestJS và TypeScript
import { PartialType, PickType, OmitType, IntersectionType } from '@nestjs/swagger';

// UpdateDto = tất cả fields của CreateDto nhưng optional
export class UpdateProductDto extends PartialType(CreateProductDto) {}

// LoginDto = chỉ lấy email và password từ CreateUserDto
export class LoginDto extends PickType(CreateUserDto, ['email', 'password']) {}

// Tạo generic wrapper cho paginated response
// Paginated list: { data, meta }. GlobalResponseInterceptor keeps meta next to data (see 3.1 section 2.4)
export class PaginatedResult<T> {
  data: T[];
  meta: {
    total: number;
    page: number;
    limit: number;
    totalPages: number; // plain property, not a getter: JSON.stringify drops getters
    hasNextPage: boolean;
    hasPrevPage: boolean;
  };

  constructor(data: T[], total: number, page: number, limit: number) {
    const totalPages = Math.ceil(total / limit);
    this.data = data;
    this.meta = { total, page, limit, totalPages, hasNextPage: page < totalPages, hasPrevPage: page > 1 };
  }
}

// Body written by GlobalResponseInterceptor (see 3.1 section 2.4)
// Not named ApiResponse: that name is the @nestjs/swagger decorator
export class ApiResponseBody<T> {
  data: T;
  requestId?: string;
  timestamp: string;
}
```

❌ **Không nên làm** — Duplicate type definitions giữa các DTOs:

```ts
// ❌ KHÔNG NÊN — copy-paste fields giữa DTOs
export class CreateProductDto {
  @IsString() name: string;
  @IsNumber() price: number;
  @IsString() sku: string;
}

export class UpdateProductDto {
  @IsString() @IsOptional() name?: string;   // Duplicate!
  @IsNumber() @IsOptional() price?: number;  // Duplicate!
  @IsString() @IsOptional() sku?: string;    // Duplicate!
}
```

**Tại sao:** Utility types giữ DRY — khi thêm field vào `CreateDto`, `UpdateDto` tự động có. Copy-paste DTOs dẫn đến inconsistency khi một bên được update mà bên kia quên.

**Tham khảo:** [NestJS Mapped Types](https://docs.nestjs.com/openapi/mapped-types)

---

### 2.7. Null/Undefined handling

✅ **Nên làm** — Phân biệt rõ `null` (intentional absence) và `undefined` (not set), dùng `??` thay `||`:

```ts
// ✅ NÊN — dùng ?? (nullish coalescing) cho default values
const pageSize = query.limit ?? 20;     // Chỉ fallback khi null/undefined
const sortBy = query.sortBy ?? 'createdAt';

// ✅ NÊN — dùng optional chaining cho nested access
const customerName = order.customer?.profile?.displayName ?? 'Unknown';

// ✅ NÊN — quy ước null vs undefined trong API
// A class, not an interface: ValidationPipe only validates classes
export class UpdateProductDto extends PartialType(CreateProductDto) {
  // name?: string comes from PartialType: undefined = leave the field unchanged

  @IsOptional() // null and undefined skip the other validators
  @IsString()
  description?: string | null; // null = clear the field's value
}
```

❌ **Không nên làm** — Dùng `||` cho default values (falsy trap):

```ts
// ❌ KHÔNG NÊN — || coi 0, '', false là falsy → bug
const pageSize = query.limit || 20;  // query.limit = 0 → pageSize = 20 (SAI!)
const name = user.nickname || 'Anonymous'; // nickname = '' → 'Anonymous' (SAI!)
```

**Tại sao:** `||` coi `0`, `''`, `false` là falsy, gây bug khi giá trị hợp lệ là `0` hoặc empty string. `??` chỉ fallback khi `null` hoặc `undefined`, đúng với ý định “giá trị chưa được set”.

---

### 2.8. Immutability & side effects

✅ **Nên làm** — Ưu tiên `const`, không mutate input params, dùng spread tạo object mới:

```ts
// ✅ NÊN — không mutate input, tạo object mới
async update(id: number, dto: UpdateProductDto): Promise<Product> {
  const existing = await this.productsRepository.findById(id);
  if (!existing) throw new ProductNotFoundException(id);

  // Spread tạo object mới, không sửa trực tiếp existing
  const updated = { ...existing, ...dto, updatedAt: new Date() };
  return this.productsRepository.save(updated);
}

// ✅ NÊN — dùng const, không reassign
const filteredOrders = orders.filter((o) => o.status === OrderStatus.PENDING);
const totalAmount = filteredOrders.reduce((sum, o) => sum + o.amount, 0);
```

❌ **Không nên làm** — Mutate input params hoặc dùng `let` không cần thiết:

```ts
// ❌ KHÔNG NÊN — mutate input param gây side effect khó debug
async update(id: number, dto: UpdateProductDto): Promise<Product> {
  const existing = await this.productsRepository.findById(id);
  existing.name = dto.name;        // Mutate entity trực tiếp
  existing.updatedAt = new Date(); // Caller không biết existing bị thay đổi
  return this.productsRepository.save(existing);
}

// ❌ KHÔNG NÊN — let không cần thiết
let total = 0;
for (const order of orders) {
  total += order.amount; // Imperative, khó đọc hơn reduce
}
```

**Tại sao:** Mutating input params gây side effects khó predict — caller không biết object của mình bị thay đổi. `const` + spread + functional methods (`map`, `filter`, `reduce`) giúp code dễ reason about, dễ test, và ít bug hơn.

---

## 3. Ví dụ minh họa thực tế

### 3.1. Before/After — DI refactor: từ “god service” đến orchestrator + service con

❌ **Before** — `OrdersService` inject 8 dependencies, làm tất cả mọi việc:

```ts
// ❌ 8 dependencies, 600+ dòng, vi phạm Single Responsibility
@Injectable()
export class OrdersService {
  constructor(
    private readonly ordersRepo: OrdersRepository,
    private readonly productsRepo: ProductsRepository,
    private readonly customersService: CustomersService,
    private readonly paymentGateway: PaymentGateway,
    private readonly shippingService: ShippingService,
    private readonly emailService: EmailService,
    private readonly smsService: SmsService,
    private readonly analyticsService: AnalyticsService,
  ) {}

  async create(dto: CreateOrderDto, userId: string): Promise<Order> {
    // 1. Validate stock (40 dòng)
    for (const item of dto.items) {
      const product = await this.productsRepo.findById(item.productId);
      if (product.stock < item.quantity) { throw ... }
    }

    // 2. Tính giá + discount (30 dòng)
    let totalPrice = 0;
    for (const item of dto.items) { ... }
    const discount = await this.customersService.getDiscount(userId);
    totalPrice = totalPrice * (1 - discount / 100);

    // 3. Thanh toán (20 dòng)
    const payment = await this.paymentGateway.charge(totalPrice);

    // 4. Tạo order + trừ stock (20 dòng)
    const order = await this.ordersRepo.create({ ...dto, totalPrice });
    for (const item of dto.items) {
      await this.productsRepo.decreaseStock(item.productId, item.quantity);
    }

    // 5. Gửi notification (15 dòng)
    await this.emailService.send(...);
    await this.smsService.send(...);

    // 6. Track analytics (10 dòng)
    await this.analyticsService.track('order_created', { orderId: order.id });

    return order;
  }
}
```

✅ **After** — Tách thành orchestrator + 4 service con, mỗi service ≤ 4 dependencies:

```txt
src/modules/orders/
├── orders.module.ts
├── orders.controller.ts
├── core/
│   ├── orders.service.ts              # Orchestrator — 4 deps, ~80 dòng
│   ├── order-pricing.service.ts       # Tính giá, discount — 2 deps
│   └── order-inventory.service.ts     # Check & trừ stock — 1 dep
├── integrations/
│   └── order-payment.service.ts       # Gọi payment gateway — 1 dep
└── notifications/
    └── order-notification.service.ts  # Email + SMS — 2 deps
```

```ts
// core/orders.service.ts — Orchestrator, chỉ coordinate
@Injectable()
export class OrdersService {
  constructor(
    private readonly ordersRepository: OrdersRepository,
    private readonly pricingService: OrderPricingService,
    private readonly inventoryService: OrderInventoryService,
    private readonly paymentService: OrderPaymentService,
  ) {} // 4 dependencies — clean

  async create(dto: CreateOrderDto, userId: string): Promise<Order> {
    // 1. Validate & reserve stock
    await this.inventoryService.reserveItems(dto.items);

    // 2. Calculate price
    const totalPrice = await this.pricingService.calculate(dto.items, userId);

    // 3. Process payment
    const paymentResult = await this.paymentService.charge(totalPrice, userId);

    // 4. Create order
    const order = await this.ordersRepository.create({
      ...dto,
      totalPrice,
      transactionId: paymentResult.transactionId,
    });

    return order;
  }
}
```

**Giải thích từng bước refactor:**

1. **Nhận diện vấn đề**: 8 dependencies, 600+ dòng, method `create()` làm 6 việc khác nhau.
2. **Nhóm logic**: pricing, inventory, payment, notification — mỗi nhóm thành 1 service.
3. **OrdersService trở thành orchestrator**: chỉ gọi các service con theo thứ tự, không chứa logic chi tiết.
4. **Notification tách riêng**: gửi async (fire-and-forget) qua event hoặc queue, không block flow chính.
5. **Kết quả**: mỗi file \< 150 dòng, mỗi class ≤ 4 dependencies, dễ test và dễ review.

---

## 4. Tooling & Config

### 4.1. Pre-commit hook

Pre-commit dùng `bss-cli` giống project v535, setup ở [NestJS Coding Standard 1.4 — Project Setup & Build](Ref_Dev_s1.4_nestjs-project-setup-build_v1.0.md) mục 2.7. Không cài thêm husky + lint-staged: hai hook cùng chạy ESLint trên mỗi commit.

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
