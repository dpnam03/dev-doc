# NestJS Coding Standard 1.2 — Request Lifecycle

| Field | Value |
| :---- | :---- |
| Owner | Bắc PV — NodeJS BE Dev Lead |
| Audience | Dev (NodeJS BE) |
| Last reviewed | 2026-11-12 |
| Review cadence | Quarterly |
| Version | v1.0 |
| Linked from | Ref_Dev_nestjs-coding-standard_v1.0 |
| Status | Live |

Doc này là mục 1.2 của [NestJS Coding Standard](Ref_Dev_nestjs-coding-standard_v1.0.md), nhóm Nền tảng NestJS. Doc nêu quy tắc về Request Lifecycle trong dự án NestJS, kèm lý do, ví dụ và config. Dev NodeJS BE đọc doc này khi viết code, review code và onboarding.

---

## 1. Tóm tắt & Phạm vi

Request Lifecycle trong NestJS mô tả **luồng xử lý một HTTP request** từ khi nhận được cho đến khi trả về response. Hiểu rõ lifecycle giúp developer đặt logic đúng chỗ — authentication, validation, transformation, logging, error handling — thay vì trộn lẫn trách nhiệm giữa các layer.

### 1.1. Scope áp dụng

- Tất cả REST API sử dụng NestJS.
- WebSocket gateway chỉ áp dụng phần Guards, Interceptors, Pipes, Exception Filters. Middleware không chạy trên gateway.
- Áp dụng cho cả global-level và route-level components.
- Không áp dụng cho microservices transport layer (có lifecycle riêng).

---

## 2. Quy tắc & Giải thích

### 2.1. Thứ tự thực thi Request Lifecycle

Mỗi HTTP request đi qua các layer theo thứ tự cố định:

1. **Middleware** (global → module → route)
2. **Guards** (global → controller → route)
3. **Interceptors — before** (global → controller → route)
4. **Pipes** (global → controller → route param)
5. **Controller Handler**
6. **Interceptors — after** (route → controller → global)
7. **Exception Filters** (route → controller → global)

> 💡 **Lưu ý quan trọng**: Thứ tự “global → controller → route” áp dụng cho Guards, Interceptors, Pipes. Riêng Exception Filters thì ngược lại: **route → controller → global** (filter gần nhất catch trước).

### 2.2. Middleware — Xử lý raw request/response

✅ **Nên làm** — Dùng Middleware cho các xử lý liên quan đến raw `req`/`res` objects: logging, CORS, compression, body parsing.

**Tại sao**: Middleware chạy đầu tiên trong lifecycle, có access trực tiếp đến Express/Fastify request/response objects. Đây là điểm duy nhất phù hợp cho các cross-cutting concerns không cần biết về NestJS context.

```ts
// common/middleware/request-logger.middleware.ts
@Injectable()
export class RequestLoggerMiddleware implements NestMiddleware {
  use(req: Request, res: Response, next: NextFunction) {
    const startTime = Date.now();
    const { method, originalUrl, ip } = req;

    res.on('finish', () => {
      const duration = Date.now() - startTime;
      console.log(`${method} ${originalUrl} ${res.statusCode} ${duration}ms - ${ip}`);
    });

    next();
  }
}
```

❌ **Không nên làm** — Xử lý business logic hoặc authorization trong Middleware.

**Tại sao**: Middleware không có access đến `ExecutionContext`, không biết handler nào sẽ chạy, không resolve được metadata từ decorators. Logic authorization cần những thông tin này nên phải đặt ở Guard.

```ts
// ❌ KHÔNG NÊN — check permission trong middleware
@Injectable()
export class BadMiddleware implements NestMiddleware {
  constructor(private usersService: UsersService) {}

  async use(req: Request, res: Response, next: NextFunction) {
    const user = await this.usersService.findById(req.user.id);
    if (!user.isActive) {
      return res.status(403).json({ message: 'Forbidden' });
    }
    next();
  }
}

// ✅ NÊN — dùng Guard, có access đến ExecutionContext
@Injectable()
export class ActiveUserGuard implements CanActivate {
  constructor(private usersService: UsersService) {}

  async canActivate(context: ExecutionContext): Promise<boolean> {
    const request = context.switchToHttp().getRequest();
    const user = await this.usersService.findById(request.user.id);
    return user.isActive;
  }
}
```

### 2.3. Guards — Authentication & Authorization

✅ **Nên làm** — Dùng Guards để quyết định request có được phép tiếp tục hay không (authn/authz).

**Tại sao**: Guards chạy sau Middleware, có access đến `ExecutionContext` và DI container đầy đủ. Return `true` để cho phép, `false` hoặc throw exception để từ chối. Đây là layer duy nhất được thiết kế cho access control.

Guard đăng ký global (xem 4.2) phải bỏ qua route gắn `@Public()`, nếu không health check và login cũng bị chặn.

```ts
// modules/auth/decorators/public.decorator.ts
export const IS_PUBLIC_KEY = 'isPublic';
export const Public = () => SetMetadata(IS_PUBLIC_KEY, true);

// modules/auth/guards/jwt-auth.guard.ts
@Injectable()
export class JwtAuthGuard implements CanActivate {
  constructor(
    private jwtService: JwtService,
    private reflector: Reflector,
  ) {}

  canActivate(context: ExecutionContext): boolean {
    // Routes marked @Public() (health check, login) skip token verification
    const isPublic = this.reflector.getAllAndOverride<boolean>(IS_PUBLIC_KEY, [
      context.getHandler(),
      context.getClass(),
    ]);
    if (isPublic) return true;

    const request = context.switchToHttp().getRequest();
    const token: unknown = request.cookies?.accessToken; // HttpOnly cookie set at login (5.1 section 2.3)

    if (typeof token !== 'string') {
      throw new UnauthorizedException('Missing access token');
    }

    try {
      const payload = this.jwtService.verify(token);
      request.user = payload;
      return true;
    } catch (error) {
      throw new UnauthorizedException('Invalid or expired access token');
    }
  }
}
```

❌ **Không nên làm** — Transform request data trong Guard.

**Tại sao**: Guard chỉ nên return boolean (cho phép / từ chối). Transformation là trách nhiệm của Pipe — nếu Guard sửa data, developer khác sẽ không biết data bị thay đổi ở đâu.

```ts
// ❌ KHÔNG NÊN — transform data trong guard
@Injectable()
export class BadGuard implements CanActivate {
  canActivate(context: ExecutionContext): boolean {
    const request = context.switchToHttp().getRequest();
    request.body.email = request.body.email.toLowerCase(); // Sai chỗ!
    return true;
  }
}

// ✅ NÊN — dùng Pipe cho transformation
@Injectable()
export class NormalizeEmailPipe implements PipeTransform {
  transform(value: any) {
    if (value.email) {
      value.email = value.email.toLowerCase();
    }
    return value;
  }
}
```

### 2.4. Pipes — Validation & Transformation

✅ **Nên làm** — Dùng Pipes để validate và transform input data trước khi vào handler.

**Tại sao**: Pipes chạy ngay trước handler, đảm bảo data đã đúng format. Kết hợp với `class-validator` và DTO để khai báo validation rules declarative, dễ đọc và maintain.

```ts
// modules/orders/dto/create-order.dto.ts
export class CreateOrderDto {
  @IsArray()
  @ValidateNested({ each: true })
  @Type(() => OrderItemDto)
  items: OrderItemDto[];

  @IsString()
  @IsOptional()
  note?: string;

  @IsEnum(PaymentMethod)
  paymentMethod: PaymentMethod;
}

// api/user/orders.controller.ts
@Post()
async create(@Body() createOrderDto: CreateOrderDto) {
  // Tới đây data đã được validate bởi global ValidationPipe
  return this.ordersService.create(createOrderDto);
}
```

**Đề xuất**: Đăng ký `ValidationPipe` ở global level trong `main.ts` thay vì từng route — đảm bảo mọi endpoint đều được validate.

### 2.5. Interceptors — Transform response & Cross-cutting logic

✅ **Nên làm** — Dùng Interceptors cho response transformation, logging, caching. Interceptors có **2 phase**: before handler và after handler.

**Tại sao**: Interceptors wrap quanh handler execution (dùng RxJS Observable), có thể biến đổi cả request lẫn response. Phù hợp cho các concern cần chạy ở cả 2 phía.

Ví dụ: `GlobalResponseInterceptor` bọc kết quả của handler thành format response chuẩn ở [NestJS Coding Standard 3.1 — REST API Design](Ref_Dev_s3.1_nestjs-rest-api-design_v1.0.md) mục 2.4.

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

❌ **Không nên làm** — Throw authorization exception trong Interceptor before phase.

**Tại sao**: Logic kiểm tra quyền truy cập thuộc về Guard. Interceptor before phase nên dùng cho transformation/logging. Nếu đặt auth check ở interceptor, thứ tự thực thi sẽ gây nhầm lẫn.

```ts
// ❌ KHÔNG NÊN — check auth trong interceptor
@Injectable()
export class BadInterceptor implements NestInterceptor {
  intercept(context: ExecutionContext, next: CallHandler) {
    const request = context.switchToHttp().getRequest();
    if (!request.headers['x-api-key']) {
      throw new UnauthorizedException('API key required'); // Sai layer!
    }
    return next.handle();
  }
}

// ✅ NÊN — dùng Guard
@Injectable()
export class ApiKeyGuard implements CanActivate {
  canActivate(context: ExecutionContext): boolean {
    const request = context.switchToHttp().getRequest();
    return !!request.headers['x-api-key'];
  }
}
```

### 2.6. Exception Filters — Xử lý lỗi tập trung

✅ **Nên làm** — Dùng Exception Filters để catch mọi exception và trả về error response format nhất quán.

**Tại sao**: Exception Filters là layer cuối cùng, catch mọi lỗi không được handle ở các layer trước. Đảm bảo client luôn nhận được response format chuẩn, không bao giờ leak stack trace hay thông tin nhạy cảm.

Team dùng `GlobalExceptionFilter`: filter `@Catch()` trả mọi lỗi theo format chuẩn, log lỗi 5xx kèm stack trace và không trả stack ra ngoài trừ khi `NODE_ENV=development`. Code và cách đăng ký cùng filter DB ở [NestJS Coding Standard 3.3 — Exception Handling](Ref_Dev_s3.3_nestjs-exception-handling_v1.0.md) mục 2.3 và 2.4.

### 2.7. So sánh: Chọn đúng layer cho từng loại logic

| **Logic cần xử lý** | **Layer phù hợp** | **Tại sao** |
| --- | --- | --- |
| Request logging, compression | Middleware | Cần raw req/res, chạy sớm nhất |
| Authentication, authorization | Guards | Có ExecutionContext, quyết định allow/deny |
| Input validation, data transform | Pipes | Chạy trước handler, đảm bảo data đúng format |
| Response wrapping, caching, timing | Interceptors | Wrap quanh handler, access cả request và response |
| Error formatting, error logging | Exception Filters | Catch mọi exception, đảm bảo response nhất quán |

---

## 3. Ví dụ minh họa thực tế

### 3.1. Scenario: API tạo đơn hàng — Full lifecycle walkthrough

Dưới đây là ví dụ hoàn chỉnh kết hợp tất cả các layer trong một request tạo đơn hàng:

```ts
// api/user/orders.controller.ts
// Layer 2: Authentication — JwtAuthGuard runs globally (APP_GUARD, 5.1 section 2.4)
@Controller('orders')
export class OrdersController {
  constructor(private ordersService: OrdersService) {}

  @Post()
  @UseGuards(ActiveUserGuard)       // Layer 2: Authorization
  @UseInterceptors(LoggingInterceptor) // Layer 3/6: Logging before & after
  async create(
    @Body() createOrderDto: CreateOrderDto, // Layer 4: Validation (global pipe)
    @CurrentUser() user: User,
  ) {
    return this.ordersService.create(createOrderDto, user.id); // Layer 5: Handler
  }
}
```

### 3.2. Luồng xử lý khi `POST /orders` đến

1. **Helmet middleware** → thêm security headers
2. **Compression middleware** → chuẩn bị nén response
3. **RequestLoggerMiddleware** → log request info
4. **JwtAuthGuard** → verify JWT token, attach `user` vào request
5. **ActiveUserGuard** → check `user.isActive === true`
6. **LoggingInterceptor (before)** → log request details
7. **ValidationPipe (global)** → validate `CreateOrderDto` theo class-validator decorators
8. **Controller handler** → gọi `ordersService.create()`
9. **LoggingInterceptor (after)** → log response details + duration
10. **GlobalResponseInterceptor** → wrap response theo format chuẩn `{ data, requestId, timestamp }`
11. Nếu có lỗi ở bất kỳ bước nào → **GlobalExceptionFilter** catch và format error response

### 3.3. Before/After — Middleware registration

❌ **Before** (đăng ký middleware rời rạc, không rõ thứ tự):

```ts
// app.module.ts — khó theo dõi thứ tự, middleware nằm rải rác
@Module({})
export class AppModule {
  configure(consumer: MiddlewareConsumer) {
    consumer.apply(CorsMiddleware).forRoutes('*');
  }
}
// Ở file khác lại đăng ký thêm middleware khác...
```

✅ **After** (tập trung, rõ ràng thứ tự):

```ts
// main.ts — global middleware tập trung tại bootstrap
async function bootstrap() {
  const app = await NestFactory.create(AppModule);

  // Global middleware (thứ tự từ trên xuống)
  app.use(helmet());
  app.use(compression());

  // Global pipes
  app.useGlobalPipes(new ValidationPipe({
    whitelist: true,
    forbidNonWhitelisted: true,
    transform: true,
    exceptionFactory: validationExceptionFactory, // Error body with details, see 3.2 section 2.6
  }));

  // Global interceptors
  app.useGlobalInterceptors(new GlobalResponseInterceptor());

  // Global filters
  app.useGlobalFilters(new GlobalExceptionFilter());

  await app.listen(3000);
}
```

---

## 4. Tooling & Config

### 4.1. Đăng ký global components trong `main.ts`

**Đề xuất thứ tự đăng ký** trong `main.ts` để dễ đọc và match với lifecycle:

```ts
async function bootstrap() {
  const app = await NestFactory.create(AppModule);

  // 1. Global middleware
  app.use(helmet());
  app.use(compression());

  // 2. Global guards: register via APP_GUARD in AppModule (see 4.2).
  //    ThrottlerGuard and JwtAuthGuard need DI, so app.useGlobalGuards(new ThrottlerGuard()) cannot work.

  // 3. Global interceptors
  app.useGlobalInterceptors(new GlobalResponseInterceptor());

  // 4. Global pipes
  app.useGlobalPipes(new ValidationPipe({
    whitelist: true,           // Strip unknown properties
    forbidNonWhitelisted: true, // Throw if unknown properties
    transform: true,           // Auto-transform payloads to DTO instances
    exceptionFactory: validationExceptionFactory, // Error body with details, see 3.2 section 2.6
  }));

  // 5. Global filters
  app.useGlobalFilters(new GlobalExceptionFilter());

  await app.listen(3000);
}
```

### 4.2. Đăng ký global components với DI support

Khi global Guard/Interceptor/Filter cần inject dependencies, đăng ký qua provider trong `AppModule`:

```ts
// app.module.ts
@Module({
  providers: [
    { provide: APP_GUARD, useClass: ThrottlerGuard }, // Needs ThrottlerModule.forRoot() in imports, see 5.3
    { provide: APP_GUARD, useClass: JwtAuthGuard }, // Skips @Public() routes (see 2.3)
    { provide: APP_INTERCEPTOR, useClass: GlobalResponseInterceptor },
    { provide: APP_FILTER, useClass: GlobalExceptionFilter },
    { provide: APP_PIPE, useValue: new ValidationPipe({ whitelist: true, exceptionFactory: validationExceptionFactory }) },
  ],
})
export class AppModule {}
```

### 4.3. Module-level middleware registration

```ts
// app.module.ts
@Module({})
export class AppModule implements NestModule {
  configure(consumer: MiddlewareConsumer) {
    consumer
      .apply(RequestLoggerMiddleware)
      .forRoutes('*'); // Áp dụng cho tất cả routes
  }
}
```

---

## References

- [NestJS Official — Request Lifecycle](https://docs.nestjs.com/faq/request-lifecycle)
- [NestJS Official — Middleware](https://docs.nestjs.com/middleware)
- [NestJS Official — Guards](https://docs.nestjs.com/guards)
- [NestJS Official — Interceptors](https://docs.nestjs.com/interceptors)
- [NestJS Official — Pipes](https://docs.nestjs.com/pipes)
- [NestJS Official — Exception Filters](https://docs.nestjs.com/exception-filters)
- [NestJS Official — Custom Decorators](https://docs.nestjs.com/custom-decorators)

## Changelog

| Date | Version | Change | By |
| :---- | :---- | :---- | :---- |
| 2026-11-18 | v1.0 | Chuyển từ Notion "NestJS Document" (page `33d71a38d3b28157adfddc85ad1a4481`, sửa 2026-04-09). Review và sửa nội dung, code trước khi publish. Owner duyệt trong chat ngày 2026-11-18. | Bắc PV |
