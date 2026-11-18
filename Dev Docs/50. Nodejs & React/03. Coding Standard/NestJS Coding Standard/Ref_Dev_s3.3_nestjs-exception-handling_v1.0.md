# NestJS Coding Standard 3.3 — Exception Handling

| Field | Value |
| :---- | :---- |
| Owner | Bắc PV — NodeJS BE Dev Lead |
| Audience | Dev (NodeJS BE) |
| Last reviewed | 2026-11-12 |
| Review cadence | Quarterly |
| Version | v1.0 |
| Linked from | Ref_Dev_nestjs-coding-standard_v1.0 |
| Status | Live |

Doc này là mục 3.3 của [NestJS Coding Standard](Ref_Dev_nestjs-coding-standard_v1.0.md), nhóm API & Data handling. Doc nêu quy tắc về Exception Handling trong dự án NestJS, kèm lý do, ví dụ và config. Dev NodeJS BE đọc doc này khi viết code, review code và onboarding.

---

## 1. Tóm tắt & Phạm vi

**Chủ đề:** Xử lý exceptions tập trung và nhất quán trong NestJS — đảm bảo error response có format chuẩn, logging đầy đủ, và không lộ thông tin nhạy cảm.

**Vấn đề giải quyết:**

- Error response format không nhất quán giữa các endpoints → frontend phải handle nhiều shape khác nhau.
- Throw `new Error('...')` thay vì `HttpException` → client nhận `500` cho mọi loại lỗi.
- Catch exception mà không re-throw (silent failure) → client không biết có lỗi.
- Lộ stack traces, DB queries, internal paths trong production → rủi ro bảo mật.
- Error messages mơ hồ (`"Invalid"`, `"Error"`) → khó debug, khó reproduce.

**Phạm vi áp dụng:** Tất cả exception handling trong NestJS applications: REST APIs, microservices, WebSocket gateways.

**Tại sao quan trọng:**

- Error format nhất quán giúp frontend viết 1 error handler dùng chung.
- Logging đúng level (error/warn) giúp monitoring phát hiện vấn đề nhanh.
- Custom exceptions với error code giúp track và categorize lỗi.
- Ẩn sensitive info trong production ngăn information disclosure attacks.

---

## 2. Quy tắc & Giải thích

### 2.1. Dùng built-in HttpException classes

**✅ NÊN:** Sử dụng các exception classes có sẵn của NestJS thay vì `throw new Error()`.

```ts
import {
  BadRequestException,
  NotFoundException,
  UnauthorizedException,
  ForbiddenException,
  ConflictException,
  InternalServerErrorException,
} from '@nestjs/common';

@Injectable()
export class ProductsService {
  async findOne(id: number): Promise<Product> {
    const product = await this.productsRepository.findOne({ where: { id } });
    if (!product) {
      throw new NotFoundException(`Product with ID ${id} not found`);
    }
    return product;
  }

  async create(dto: CreateProductDto): Promise<Product> {
    const existing = await this.productsRepository.findOne({
      where: { sku: dto.sku },
    });
    if (existing) {
      throw new ConflictException(`Product with SKU ${dto.sku} already exists`);
    }
    return this.productsRepository.save(dto);
  }
}
```

**❌ KHÔNG NÊN:** Dùng `throw new Error()` — không có HTTP status code.

```ts
// ❌ Bad — client luôn nhận 500 Internal Server Error
if (!user) {
  throw new Error('User not found');  // Không có status code!
}

// ✅ Good — client nhận 404 với message rõ ràng
if (!user) {
  throw new NotFoundException(`User with ID ${id} not found`);
}
```

*Tại sao:* Built-in exceptions tự động convert thành HTTP response đúng status code. `Error` bình thường luôn trả `500` — client không phân biệt được lỗi do input sai hay server crash.

**Mapping nhanh:**

| **Tình huống** | **Exception** | **Status** |
| --- | --- | --- |
| Input không hợp lệ | `BadRequestException` | 400 |
| Chưa xác thực | `UnauthorizedException` | 401 |
| Không có quyền | `ForbiddenException` | 403 |
| Resource không tồn tại | `NotFoundException` | 404 |
| Trùng lặp (duplicate) | `ConflictException` | 409 |
| Business logic reject | Custom exception có `type: 'DOMAIN_ERROR'` (mục 2.2) | 400 |
| Lỗi không xác định | `InternalServerErrorException` | 500 |

> **Tham khảo:** [NestJS Exception Filters](https://docs.nestjs.com/exception-filters)

---

### 2.2. Custom Exception Classes cho Business Errors

**✅ NÊN:** Tạo custom exceptions kế thừa `HttpException`, mỗi class một `code` riêng dạng `SCREAMING_SNAKE_CASE`. `message` viết tiếng Anh, chứa context đủ để debug. Client hiển thị text cho user theo `code`.

```ts
// modules/orders/exceptions/order.exceptions.ts
import { HttpException, HttpStatus } from '@nestjs/common';

// Body: { type?, code, message }. GlobalExceptionFilter (section 2.3) adds path, requestId, timestamp.
export class OrderNotFoundException extends HttpException {
  constructor(orderId: string) {
    super(
      { code: 'ORDER_NOT_FOUND', message: `Order ${orderId} not found` },
      HttpStatus.NOT_FOUND,
    );
  }
}

export class InsufficientStockException extends HttpException {
  constructor(productName: string, available: number, requested: number) {
    super(
      {
        type: 'DOMAIN_ERROR', // Without it, a 400 would be typed VALIDATION_ERROR
        code: 'INSUFFICIENT_STOCK',
        message: `Insufficient stock for ${productName}: requested ${requested}, available ${available}`,
      },
      HttpStatus.BAD_REQUEST,
    );
  }
}

export class PaymentFailedException extends HttpException {
  constructor(orderId: string, reason: string, transactionId?: string) {
    super(
      {
        code: 'PAYMENT_FAILED',
        message: `Payment for order ${orderId} failed: ${reason}`
          + (transactionId ? ` (transaction ${transactionId})` : ''),
      },
      HttpStatus.PAYMENT_REQUIRED,
    );
  }
}
```

**Sử dụng trong service:**

```ts
async processOrder(orderId: string): Promise<Order> {
  const order = await this.ordersRepository.findOne({ where: { id: orderId } });
  if (!order) {
    throw new OrderNotFoundException(orderId);
  }
  if (order.status !== 'pending') {
    throw new InvalidOrderStateException(orderId, order.status, ['pending']);
  }
  // ...
}
```

**❌ KHÔNG NÊN:** Throw generic exception không có context.

```ts
// ❌ Bad — thiếu context, khó debug
throw new BadRequestException('Invalid status');
throw new BadRequestException('Invalid order');

// ✅ Good — chi tiết, có context để debug
throw new InvalidOrderStateException(orderId, order.status, ['pending']);
throw new InsufficientStockException('Ao thun', 5, 10);
```

*Tại sao:* Error code riêng (`ORDER_NOT_FOUND`, `INSUFFICIENT_STOCK`) giúp: (1) frontend handle từng loại lỗi, (2) monitoring categorize errors, (3) debug nhanh nhờ context đầy đủ.

---

### 2.3. Global Exception Filter cho error format nhất quán

**✅ NÊN:** Implement global `@Catch()` filter để chuẩn hoá error response.

```ts
// common/filters/global-exception.filter.ts
import {
  ArgumentsHost, Catch, ExceptionFilter,
  HttpException, HttpStatus, Logger,
} from '@nestjs/common';
import { Request, Response } from 'express';

// One entry per invalid field, e.g. { field: 'items.0.quantity', message: '...' }
export interface ErrorDetail {
  field: string;
  message: string;
  code?: string; // Rule code, so the client can show its own text
}

// Error type by HTTP status. Any other 4xx means the request broke a business rule.
const ERROR_TYPES: Record<number, string> = {
  400: 'VALIDATION_ERROR',
  401: 'AUTH_ERROR',
  403: 'AUTH_ERROR',
  404: 'NOT_FOUND',
  409: 'CONFLICT',
  429: 'RATE_LIMIT',
};

@Catch()
export class GlobalExceptionFilter implements ExceptionFilter {
  private readonly logger = new Logger(GlobalExceptionFilter.name);

  catch(exception: unknown, host: ArgumentsHost) {
    const ctx = host.switchToHttp();
    const response = ctx.getResponse<Response>();
    // requestId is set by RequestIdMiddleware (Coding Standard 7.1, section 2.5)
    const request = ctx.getRequest<Request & { requestId?: string }>();

    const status = exception instanceof HttpException
      ? exception.getStatus()
      : HttpStatus.INTERNAL_SERVER_ERROR;

    // Custom exceptions (section 2.2) pass { type?, code, message, details? }.
    // Built-in ones pass a string or { statusCode, message, error }.
    const body = exception instanceof HttpException ? exception.getResponse() : undefined;
    const fields = typeof body === 'object' && body !== null ? (body as Record<string, unknown>) : {};
    const details = Array.isArray(fields.details) ? (fields.details as ErrorDetail[]) : [];

    const error = {
      type: typeof fields.type === 'string' ? fields.type : this.getType(status),
      code: typeof fields.code === 'string' ? fields.code : (HttpStatus[status] ?? 'INTERNAL_SERVER_ERROR'),
      message: this.getMessage(exception, body),
      ...(details.length > 0 && { param: details[0].field, details }),
      path: request.url,
      requestId: request.requestId,
      timestamp: new Date().toISOString(),
    };

    if (status >= 500) {
      // Never log request.body: it may contain passwords, tokens or PII
      // Fields go in the message object: an object as the last argument becomes the context
      this.logger.error(
        { message: `${request.method} ${request.url} - ${status}`, requestId: request.requestId },
        exception instanceof Error ? exception.stack : String(exception),
      );
    } else {
      this.logger.warn(`${request.method} ${request.url} - ${status} ${error.code}: ${error.message}`);
    }

    // Stack trace only in local development — never in staging or production
    const stack = process.env.NODE_ENV === 'development' && exception instanceof Error
      ? exception.stack
      : undefined;

    response.status(status).json({ error: { ...error, ...(stack && { stack }) } });
  }

  private getType(status: number): string {
    if (status >= 500) return 'SERVER_ERROR';
    return ERROR_TYPES[status] ?? 'DOMAIN_ERROR';
  }

  private getMessage(exception: unknown, body: unknown): string {
    if (!(exception instanceof HttpException)) return 'Internal server error';
    if (typeof body === 'string') return body;
    const { message } = body as { message?: string | string[] };
    if (Array.isArray(message)) return message.join('; ');
    return message ?? exception.message;
  }
}
```

**Đăng ký trong `main.ts`:**

```ts
async function bootstrap() {
  const app = await NestFactory.create(AppModule);
  app.useGlobalFilters(new GlobalExceptionFilter());
  await app.listen(3000);
}
```

*Tại sao:* Global filter đảm bảo mọi error response có cùng format, mô tả ở [NestJS Coding Standard 3.1 — REST API Design](Ref_Dev_s3.1_nestjs-rest-api-design_v1.0.md) mục 2.4. Frontend chỉ cần 1 error handler. Exception built-in không có `code` nên filter dùng tên HTTP status, ví dụ `NOT_FOUND`. Logging tập trung giúp monitoring phát hiện vấn đề nhanh.

---

### 2.4. Database Exception Filter

**✅ NÊN:** Tạo domain-specific filter cho database errors. Mỗi filter import package của một ORM, nên project chỉ đăng ký filter của ORM mình dùng. Hai filter kế thừa `GlobalExceptionFilter`, đổi lỗi DB thành `HttpException` rồi gọi `super.catch()`, nên body và log giống mục 2.3.

```ts
// common/filters/database-exception.filter.ts
import { ArgumentsHost, BadRequestException, Catch, ConflictException } from '@nestjs/common';
import { QueryFailedError } from 'typeorm';
import { GlobalExceptionFilter } from './global-exception.filter';

// Extends the global filter, so the body and the logging stay the same (section 2.3)
@Catch(QueryFailedError)
export class DatabaseExceptionFilter extends GlobalExceptionFilter {
  catch(exception: QueryFailedError, host: ArgumentsHost) {
    const { code } = exception as QueryFailedError & { code?: string };

    // Unique constraint violation (PostgreSQL 23505, MySQL ER_DUP_ENTRY)
    if (code === '23505' || code === 'ER_DUP_ENTRY') {
      return super.catch(
        new ConflictException({ code: 'DUPLICATE_ENTRY', message: 'Resource already exists' }),
        host,
      );
    }

    // Foreign key constraint violation (PostgreSQL 23503; MySQL: missing parent, or parent still referenced)
    if (['23503', 'ER_NO_REFERENCED_ROW_2', 'ER_ROW_IS_REFERENCED_2'].includes(code ?? '')) {
      return super.catch(
        new BadRequestException({ code: 'FOREIGN_KEY_VIOLATION', message: 'Referenced resource does not exist' }),
        host,
      );
    }

    // Any other database error: 500, and the original error is logged with its stack
    return super.catch(exception, host);
  }
}
```

Project dùng Prisma:

```ts
// common/filters/prisma-exception.filter.ts — Prisma version of DatabaseExceptionFilter
import {
  ArgumentsHost, BadRequestException, Catch, ConflictException, NotFoundException,
} from '@nestjs/common';
import { Prisma } from '../../generated/prisma/client'; // generator output, see 4.1 section 4.2
import { GlobalExceptionFilter } from './global-exception.filter';

@Catch(Prisma.PrismaClientKnownRequestError)
export class PrismaExceptionFilter extends GlobalExceptionFilter {
  catch(exception: Prisma.PrismaClientKnownRequestError, host: ArgumentsHost) {
    switch (exception.code) {
      // Unique constraint violation
      case 'P2002':
        return super.catch(
          new ConflictException({ code: 'DUPLICATE_ENTRY', message: 'Resource already exists' }),
          host,
        );

      // Foreign key constraint violation
      case 'P2003':
        return super.catch(
          new BadRequestException({ code: 'FOREIGN_KEY_VIOLATION', message: 'Referenced resource does not exist' }),
          host,
        );

      // update/delete on a record that does not exist
      case 'P2025':
        return super.catch(
          new NotFoundException({ code: 'NOT_FOUND', message: 'Resource not found' }),
          host,
        );

      // Any other database error: 500, and the original error is logged with its stack
      default:
        return super.catch(exception, host);
    }
  }
}
```

Đăng ký `GlobalExceptionFilter` trước filter DB. Nest thử filter đăng ký sau cùng trước, nên nếu đảo thứ tự thì lỗi DB rơi vào catch-all và thành 500.

```ts
// main.ts — TypeORM project: DatabaseExceptionFilter instead of PrismaExceptionFilter
app.useGlobalFilters(new GlobalExceptionFilter(), new PrismaExceptionFilter());
```

*Tại sao:* Database errors (unique constraint, foreign key) cần được translate thành HTTP response có nghĩa. Không nên expose raw SQL error cho client.

---

### 2.5. Không catch mà không re-throw (Silent Failure)

**❌ KHÔNG NÊN:** Catch exception rồi return null/default mà không throw.

```ts
// ❌ Bad — silent failure, client không biết có lỗi
async findUser(id: string): Promise<User | null> {
  try {
    return await this.usersRepository.findOne({ where: { id } });
  } catch (error) {
    console.log('Error finding user:', error);
    return null;  // Client không biết DB đang down!
  }
}
```

**✅ NÊN:** Re-throw business exceptions, wrap unexpected errors.

```ts
// ✅ Good — re-throw properly
async findUser(id: string): Promise<User> {
  try {
    const user = await this.usersRepository.findOne({ where: { id } });
    if (!user) {
      throw new NotFoundException(`User with ID ${id} not found`);
    }
    return user;
  } catch (error) {
    // Re-throw business exceptions
    if (error instanceof HttpException) {
      throw error;
    }
    // Wrap unexpected errors
    this.logger.error(`Failed to find user ${id}`, error.stack);
    throw new InternalServerErrorException('Failed to retrieve user');
  }
}
```

*Tại sao:* Silent failures là bug ẩn — client nhận response như bình thường nhưng data sai. Lỗi chỉ được phát hiện khi business logic downstream fail.

---

### 2.6. Không expose sensitive info trong errors

**❌ KHÔNG NÊN:** Lộ database structure, internal paths, stack traces.

```ts
// ❌ Bad — lộ DB structure
throw new NotFoundException(
  `No user found with email ${email} in database table 'users'`
);

// ❌ Bad — lộ password hash
throw new UnauthorizedException(
  `Password hash ${user.passwordHash} does not match`
);
```

**✅ NÊN:** Generic messages cho auth, chi tiết messages cho non-sensitive errors.

```ts
// ✅ Good — auth: cùng message cho wrong email và wrong password
throw new UnauthorizedException('Invalid credentials');

// ✅ Good — non-auth: chi tiết đủ để debug
throw new BadRequestException(
  `Cannot process order ${orderId} with status '${order.status}'. Expected: 'pending'`,
);
```

*Tại sao:* Auth errors phải generic để không lộ thông tin (attacker biết email tồn tại hay không). Non-auth errors có thể chi tiết để giúp debug, nhưng không bao giờ chứa DB structure hay credentials.

> **Tham khảo:** [OWASP Error Handling](https://owasp.org/www-community/Improper_Error_Handling)

---

### 2.7. Không dùng Exceptions cho Control Flow

**❌ KHÔNG NÊN:** Dùng exceptions để điều khiển logic bình thường.

```ts
// ❌ Bad — empty array là valid result, không phải error
async getUsers(filters: FilterDto): Promise<User[]> {
  try {
    const users = await this.usersRepository.find({ where: filters });
    if (users.length === 0) {
      throw new NotFoundException('No users found');  // Không phải error!
    }
    return users;
  } catch (error) {
    if (error instanceof NotFoundException) {
      return [];  // Đã throw rồi lại catch → vô nghĩa
    }
    throw error;
  }
}
```

**✅ NÊN:** Return empty array/null cho valid empty results.

```ts
// ✅ Good — empty array là valid response
async getUsers(filters: FilterDto): Promise<User[]> {
  return this.usersRepository.find({ where: filters });
  // Empty array → 200 OK với data: []
}

// ✅ Exception chỉ cho truly exceptional cases
async getUserById(id: string): Promise<User> {
  const user = await this.usersRepository.findOne({ where: { id } });
  if (!user) {
    throw new NotFoundException(`User with ID ${id} not found`);
  }
  return user;
}
```

*Tại sao:* Exceptions có performance overhead và làm code khó đọc. Dùng cho *exceptional* cases (resource không tồn tại khi expect có), không dùng cho *normal* cases (search không có kết quả).

---

### 2.8. Error Logging theo Severity

**✅ NÊN:** Log level phù hợp với severity.

```ts
// 5xx → logger.error (cần investigate ngay)
this.logger.error(
  { message: `${request.method} ${request.url} - 500`, requestId, userId: request.user?.id }, // never the request body
  exception.stack,
);

// 4xx → logger.warn (client error, có thể là normal)
this.logger.warn(
  `${request.method} ${request.url} - 404: Product not found`,
);

// Notification failure → logger.warn (không block flow chính)
this.notificationService
  .sendOrderConfirmation(order)
  .catch((error) => {
    this.logger.warn(
      `Failed to send confirmation for order ${orderId}: ${error instanceof Error ? error.message : String(error)}`,
    );
  });
```

*Tại sao:* `error` level trigger alerts trong monitoring (PagerDuty, Slack). Nếu mọi 404 đều `error` → alert noise, team bỏ qua alerts thật. `warn` cho 4xx giúp track trends mà không gây noise.

---

### 2.9. TypeScript Config cho Error Handling

**✅ NÊN:** Bật `useUnknownInCatchVariables` trong tsconfig.

```json
// tsconfig.json
{
  "compilerOptions": {
    "useUnknownInCatchVariables": true  // TS 4.4+
  }
}
```

```ts
// Với useUnknownInCatchVariables: true
try {
  await this.externalService.call();
} catch (error) {
  // error là `unknown`, buộc phải narrow type
  if (error instanceof HttpException) {
    throw error;
  }
  if (error instanceof Error) {
    this.logger.error(error.message, error.stack);
  }
  throw new InternalServerErrorException('External service failed');
}
```

*Tại sao:* Mặc định `catch (error)` có type `any` → mất type safety. `useUnknownInCatchVariables` buộc developer narrow type trước khi access properties, tránh runtime errors khi error không phải `Error` instance.

---

## 3. Ví dụ minh họa thực tế

### 3.1. Walkthrough: Order Processing — Exception Handling đầy đủ

**Bước 1 — Định nghĩa Custom Exceptions**

```ts
// modules/orders/exceptions/order.exceptions.ts
export class OrderNotFoundException extends HttpException {
  constructor(orderId: string) {
    super(
      { code: 'ORDER_NOT_FOUND', message: `Order ${orderId} not found` },
      HttpStatus.NOT_FOUND,
    );
  }
}

export class InvalidOrderStateException extends HttpException {
  constructor(orderId: string, currentState: string, expectedStates: string[]) {
    super(
      {
        type: 'DOMAIN_ERROR',
        code: 'INVALID_ORDER_STATE',
        message: `Order ${orderId} is ${currentState}, expected ${expectedStates.join(' or ')}`,
      },
      HttpStatus.BAD_REQUEST,
    );
  }
}
```

**Bước 2 — Service với Error Handling**

```ts
// modules/orders/orders.service.ts
@Injectable()
export class OrdersService {
  private readonly logger = new Logger(OrdersService.name);

  constructor(
    private readonly ordersRepository: OrdersRepository,
    private readonly inventoryService: InventoryService,
    private readonly paymentService: PaymentService,
  ) {}

  async processOrder(orderId: string): Promise<Order> {
    // 1. Find order
    const order = await this.ordersRepository.findOne({
      where: { id: orderId },
      relations: ['items', 'customer'],
    });
    if (!order) {
      throw new OrderNotFoundException(orderId);
    }

    // 2. Validate state
    if (order.status !== 'pending') {
      throw new InvalidOrderStateException(
        orderId, order.status, ['pending'],
      );
    }

    // 3. Reserve inventory
    try {
      await this.inventoryService.reserveItems(order.items);
    } catch (error) {
      this.logger.error(
        `Inventory reservation failed for order ${orderId}`,
        error instanceof Error ? error.stack : String(error),
      );
      order.status = 'failed';
      order.failureReason = 'Insufficient inventory';
      await this.ordersRepository.save(order);

      if (error instanceof InsufficientStockException) {
        throw error;  // Re-throw business exception
      }
      throw new InternalServerErrorException(
        'Failed to reserve inventory',
      );
    }

    // 4. Process payment
    try {
      const paymentResult = await this.paymentService.charge({
        amount: order.totalAmount,
        customerId: order.customer.id,
      });

      if (!paymentResult.success) {
        throw new PaymentFailedException(
          orderId,
          paymentResult.errorMessage,
          paymentResult.transactionId,
        );
      }

      // Update order
      order.status = 'paid';
      order.transactionId = paymentResult.transactionId;
      return this.ordersRepository.save(order);

    } catch (error) {
      // Rollback inventory
      await this.inventoryService.releaseItems(order.items)
        .catch((releaseError) => {
          this.logger.error(
            `Failed to release inventory for order ${orderId}`,
            releaseError instanceof Error ? releaseError.stack : String(releaseError),
          );
        });

      if (error instanceof HttpException) throw error;
      this.logger.error(`Unexpected error processing order ${orderId}`,
        error instanceof Error ? error.stack : String(error));
      throw new InternalServerErrorException(
        'An unexpected error occurred while processing your order',
      );
    }
  }
}
```

**Bước 3 — Controller**

```ts
@Controller('orders')
@ApiTags('orders')
@UseFilters(DatabaseExceptionFilter)
export class OrdersController {
  constructor(private readonly ordersService: OrdersService) {}

  @Post(':id/process')
  @ApiOperation({ summary: 'Process pending order' })
  @ApiOkResponse({ type: OrderResponseDto })
  @ApiNotFoundResponse({ description: 'Order not found' })
  @ApiBadRequestResponse({ description: 'Invalid order state' })
  async processOrder(@Param('id') orderId: string): Promise<OrderResponseDto> {
    const order = await this.ordersService.processOrder(orderId);
    return plainToInstance(OrderResponseDto, order, {
      excludeExtraneousValues: true,
    });
  }
}
```

**Bước 4 — Response Examples**

```json
// Success (200)
{
  "data": {
    "id": "order_123",
    "status": "paid",
    "totalAmount": 15000,
    "transactionId": "txn_abc123"
  },
  "requestId": "abc-123",
  "timestamp": "2026-11-17T10:00:00.000Z"
}

// Order not found (404)
{
  "error": {
    "type": "NOT_FOUND",
    "code": "ORDER_NOT_FOUND",
    "message": "Order order_999 not found",
    "path": "/orders/order_999/process",
    "requestId": "abc-123",
    "timestamp": "2026-11-17T10:00:00.000Z"
  }
}

// Invalid state (400)
{
  "error": {
    "type": "DOMAIN_ERROR",
    "code": "INVALID_ORDER_STATE",
    "message": "Order order_123 is shipped, expected pending",
    "path": "/orders/order_123/process",
    "requestId": "abc-123",
    "timestamp": "2026-11-17T10:00:00.000Z"
  }
}

// Payment failed (402)
{
  "error": {
    "type": "DOMAIN_ERROR",
    "code": "PAYMENT_FAILED",
    "message": "Payment for order order_123 failed: Insufficient funds (transaction txn_failed_456)",
    "path": "/orders/order_123/process",
    "requestId": "abc-123",
    "timestamp": "2026-11-17T10:00:00.000Z"
  }
}
```

---

## 4. Tooling & Config

### 4.1. Checklist setup Exception Handling

- [ ] Tạo `GlobalExceptionFilter` trong `common/filters/`
- [ ] Đăng ký global filter, catch-all trước filter DB: `app.useGlobalFilters(new GlobalExceptionFilter(), new PrismaExceptionFilter())`
- [ ] Tạo `DatabaseExceptionFilter` cho TypeORM errors, hoặc `PrismaExceptionFilter` nếu project dùng Prisma
- [ ] Tạo folder `exceptions/` trong mỗi feature module cho custom exceptions
- [ ] Bật `useUnknownInCatchVariables: true` trong `tsconfig.json`
- [ ] Error response format chuẩn: `{ error: { type, code, message, param?, details?, path, requestId, timestamp } }`
- [ ] `ValidationPipe` dùng `validationExceptionFactory` ([NestJS Coding Standard 3.2 — Validation & Serialization](Ref_Dev_s3.2_nestjs-validation-serialization_v1.0.md) mục 2.6) để lỗi validate có `details`
- [ ] Đăng ký `RequestIdMiddleware` ([NestJS Coding Standard 7.1 — Logging](Ref_Dev_s7.1_nestjs-logging_v1.0.md) mục 2.5) để body có `requestId`
- [ ] Log: `error` cho 5xx, `warn` cho 4xx
- [ ] Chỉ trả stack trace trong response khi `NODE_ENV=development`
- [ ] Không log request body
- [ ] Test: verify error responses cho các scenarios (not found, validation, auth)

### 4.2. ESLint rules cho exception handling

```javascript
// eslint.config.mjs — add to the config of 1.4 section 2.3
export default tseslint.config(
  // ...config from 1.4 section 2.3
  {
    rules: {
      'no-empty': ['error', { allowEmptyCatch: false }],
      'no-console': ['error', { allow: ['warn', 'error'] }],
      '@typescript-eslint/no-floating-promises': 'error',
      'no-throw-literal': 'error',
    },
  },
);
```

### 4.3. Jest helpers cho testing exceptions

```ts
// test/helpers/exception-matchers.ts
export const expectHttpException = async (
  fn: () => Promise<unknown>,
  status: number,
  errorCode?: string,
) => {
  let error: unknown;
  try {
    await fn();
  } catch (e) {
    error = e;
  }
  // Jest 30 has no global fail(): if fn resolves, this line fails with "Received: undefined"
  expect(error).toBeInstanceOf(HttpException);
  expect((error as HttpException).getStatus()).toBe(status);
  if (errorCode) {
    const response = (error as HttpException).getResponse() as { code?: string };
    expect(response.code).toBe(errorCode);
  }
};

// Usage
describe('OrdersService', () => {
  it('should throw OrderNotFoundException', async () => {
    await expectHttpException(
      () => service.processOrder('non-existent'),
      404,
      'ORDER_NOT_FOUND',
    );
  });

  it('should throw InvalidOrderStateException', async () => {
    // Setup: order with status 'shipped'
    await expectHttpException(
      () => service.processOrder('order_shipped'),
      400,
      'INVALID_ORDER_STATE',
    );
  });
});
```

---

## References

- [NestJS Exception Filters](https://docs.nestjs.com/exception-filters) — Tài liệu chính thức về exception handling
- [NestJS Validation](https://docs.nestjs.com/techniques/validation) — ValidationPipe và auto-validation
- [Node.js Error Handling](https://nodejs.org/api/errors.html) — Error classes và best practices
- [HTTP Status Codes — MDN](https://developer.mozilla.org/en-US/docs/Web/HTTP/Status) — Full reference
- [Stripe API Errors](https://docs.stripe.com/api/errors) — Mô hình `type` + `code` mà format lỗi của team dựa theo
- [OWASP Error Handling](https://owasp.org/www-community/Improper_Error_Handling) — Security best practices
- [TypeScript useUnknownInCatchVariables](https://www.typescriptlang.org/tsconfig#useUnknownInCatchVariables) — TS 4.4+ config

## Changelog

| Date | Version | Change | By |
| :---- | :---- | :---- | :---- |
| 2026-11-18 | v1.0 | Chuyển từ Notion "NestJS Document" (page `33d71a38d3b2811bb364f5a95a35e716`, sửa 2026-04-09). Review và sửa nội dung, code trước khi publish. Owner duyệt trong chat ngày 2026-11-18. | Bắc PV |
