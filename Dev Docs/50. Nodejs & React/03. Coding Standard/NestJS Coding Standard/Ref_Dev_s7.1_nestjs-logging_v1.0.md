# NestJS Coding Standard 7.1 — Logging

| Field | Value |
| :---- | :---- |
| Owner | Bắc PV — NodeJS BE Dev Lead |
| Audience | Dev (NodeJS BE) |
| Last reviewed | 2026-11-12 |
| Review cadence | Quarterly |
| Version | v1.0 |
| Linked from | Ref_Dev_nestjs-coding-standard_v1.0<br>Ref_Dev_s7.3_nestjs-monitoring-observability_v1.0 |
| Status | Live |

Doc này là mục 7.1 của [NestJS Coding Standard](Ref_Dev_nestjs-coding-standard_v1.0.md), nhóm Observability. Doc nêu quy tắc về Logging trong dự án NestJS, kèm lý do, ví dụ và config. Dev NodeJS BE đọc doc này khi viết code, review code và onboarding.

---

## 1. Tóm tắt & Phạm vi

Logging, Debugging & Monitoring là ba trụ cột của **Observability**. Observability là khả năng quan sát và hiểu hệ thống đang hoạt động như thế nào mà không cần can thiệp trực tiếp vào code đang chạy.

- **Logging**: Ghi lại các sự kiện quan trọng (errors, business events, request flow) dưới dạng có cấu trúc để phục vụ điều tra, audit, và monitoring.
- **Debugging**: Kỹ thuật tìm và sửa lỗi — từ local (debugger, breakpoints) đến production (log-based investigation, tracing).
- **Monitoring**: Theo dõi metrics (error rate, latency, throughput) và thiết lập alerts khi hệ thống bất thường.

**Phạm vi áp dụng**: Mọi service NestJS — từ local development đến staging/production. Đặc biệt quan trọng khi hệ thống có nhiều services, nhiều team, hoặc phục vụ lượng traffic lớn.

**Tại sao quan trọng?**

- Không có logging tốt → không thể điều tra bug production → downtime kéo dài.
- Không có monitoring → không biết hệ thống đang chậm/lỗi cho đến khi user phàn nàn.
- Log thiếu cấu trúc → grep/search không hiệu quả → mất hàng giờ để tìm root cause.

---

## 2. Quy tắc & Giải thích

### 2.1. Dùng NestJS Logger, không dùng `console` trần

**Nên làm**: Dùng `Logger` class của NestJS (hoặc custom logger như Winston/Pino) cho mọi log statement.

```ts
import { Logger } from '@nestjs/common';

const logger = new Logger(OrdersService.name);

logger.log({ message: 'Order created', orderId, userId, total });
logger.warn({ message: 'Payment processing slow', orderId, duration });
logger.error('Payment failed', err.stack);
```

**Không nên**: Dùng `console.log` / `console.error` trực tiếp.

```ts
// ❌ Bad
console.log('order created', order);
console.error('something went wrong', err);
```

**Tại sao?**

- `Logger` của NestJS tích hợp sẵn log levels, context (tên class), và có thể swap implementation (Winston, Pino) mà không đổi code.
- `console.log` không có level, không có context, không thể filter theo môi trường, và không thể redirect sang file/log server.
- Khi dùng custom logger (Winston/Pino), `Logger` của NestJS sẽ delegate sang implementation đó — nhất quán toàn bộ app.

> Tham khảo: [NestJS Logger Documentation](https://docs.nestjs.com/techniques/logger)

### 2.2. Log có cấu trúc (Structured Logging)

**Nên làm**: Log dạng JSON với các fields cố định, dùng event name thay vì text tự do.

```ts
// ✅ Good — structured, dễ grep/search
logger.log({ message: 'order.created', orderId, userId, total });
logger.error({ message: 'order.payment_failed', orderId, provider, errorCode });
logger.warn({ message: 'order.shipping_delayed', orderId, expectedDate, reason });
```

**Không nên**: Log text tự do, không có cấu trúc.

```ts
// ❌ Bad — khó grep, không parse được
logger.log(`Order ${orderId} was created by user ${userId} with total ${total}`);
logger.error(`Payment failed for order ${orderId} with error: ${err.message}`);
```

**Tại sao?**

- Truyền một object có field `message`. Object đặt ở tham số thứ hai bị `Logger` hiểu là context, nên log mất tên class: nest-winston ghi `"context":{"orderId":1}`.
- Structured log cho phép search/filter theo field cụ thể trong ELK/Loki/Datadog: `event:order.payment_failed AND provider:stripe`.
- Text tự do phải dùng regex, dễ sai, khó maintain khi format thay đổi.
- JSON log dễ parse bằng machine → aggregation, alerting, dashboard tự động.

### 2.3. Log level đúng mục đích

**Nên làm**: Phân loại log theo severity rõ ràng.

| **Level** | **Mục đích** | **Ví dụ** | **Env** |
| --- | --- | --- | --- |
| `error` | Lỗi cần xử lý ngay, ảnh hưởng user | Payment failed, DB connection lost | All |
| `warn` | Bất thường nhưng chưa hẳn lỗi | Slow query, retry thành công, cache miss cao | All |
| `log` / `info` | Event bình thường quan trọng | Service started, order created, user login | All |
| `debug` | Thông tin chi tiết khi debug | Input/output của function, SQL generated | Dev, Staging |
| `verbose` | Chi tiết rất nhiều, trace flow | Mọi step trong 1 flow phức tạp | Dev only |

**Không nên**:

- Log 4xx errors ở `error` level → gây alert noise trong monitoring.
- Log mọi thứ ở `info` level → không thể filter khi cần.

**Cấu hình theo môi trường**: level đặt bằng biến `LOG_LEVEL` (`error`, `warn`, `info`, `debug`), schema ở [NestJS Coding Standard 2.1 — Configuration & Environment Management](Ref_Dev_s2.1_nestjs-configuration-environment_v1.0.md) mục 2.3. `LoggerModule` ở mục 3.2 truyền giá trị này cho Winston, mặc định `info`. Level `log` của NestJS ghi ra Winston thành `info`.

### 2.4. Kèm context đầy đủ trong mỗi log

**Nên làm**: Mỗi log phải kèm đủ context để reconstruct lại flow khi điều tra.

```ts
// ✅ Good — đủ context
logger.log({ message: 'order.created', orderId, userId, total, itemCount: items.length });
logger.error({ message: 'order.payment_failed', orderId, provider: 'stripe', errorCode: 'card_declined', requestId });
```

**Không nên**:

```ts
// ❌ Bad — thiếu context, không biết order nào, user nào
logger.log('Order created');
logger.error('Payment failed');
```

**Các fields nên kèm theo**:

- `requestId` / `traceId`: Liên kết mọi log trong cùng 1 request.
- `userId`: Ai thực hiện action.
- Entity IDs: `orderId`, `productId`, v.v.
- `service` / `method`: Nơi phát sinh log (Logger context tự handle).

### 2.5. Request ID (Correlation ID)

**Nên làm**: Mỗi request có 1 unique `requestId`, kèm theo mọi log trong request đó.

```ts
// middleware/request-id.middleware.ts
import { v4 as uuid } from 'uuid';

@Injectable()
export class RequestIdMiddleware implements NestMiddleware {
  use(req: Request & { requestId?: string }, res: Response, next: NextFunction) {
    const header = req.headers['x-request-id'];
    req.requestId = typeof header === 'string' && header !== '' ? header : uuid();
    res.setHeader('x-request-id', req.requestId);
    next();
  }
}
```

Kết hợp `AsyncLocalStorage` (Node.js) để tự động inject `requestId` vào mọi log mà không cần truyền tay:

```ts
// common/async-context.ts
import { AsyncLocalStorage } from 'async_hooks';

export const asyncLocalStorage = new AsyncLocalStorage<Map<string, string>>();

// Trong middleware:
asyncLocalStorage.run(new Map([['requestId', req['requestId']]]), () => next());

// Trong custom logger:
const requestId = asyncLocalStorage.getStore()?.get('requestId');
```

**Tại sao?**

- Khi 1 request đi qua nhiều services/layers, `requestId` cho phép grep tất cả log liên quan trong 1 lần.
- Đặc biệt quan trọng trong microservices — trace 1 request xuyên suốt nhiều service.

### 2.6. Không log dữ liệu nhạy cảm

**Nên làm**:

- Chỉ log prefix/hash của sensitive data: `apiKey: 'sk-...abc'`.
- Chỉ log các fields chính của request/response (id, status, total), không log full body.

**Không nên**:

- Log passwords, JWT tokens, full API keys, credit card numbers.
- Log toàn bộ request body (có thể chứa PII).
- Log binary/attachment (file, image).

```ts
// ❌ Bad — lộ token và password
logger.log({ message: 'User login', email, password, token });
logger.log({ message: 'API call', headers: req.headers }); // chứa Authorization header

// ✅ Good — chỉ log cần thiết
logger.log({ message: 'user.login_success', userId });
logger.log({ message: 'api.outbound_call', url, method, statusCode, duration });
```

### 2.7. Không log trong loop lớn ở production

**Nên làm**: Log tổng kết sau loop, hoặc log mỗi N items.

```ts
// ✅ Good — log tổng kết
const results = await Promise.all(items.map(processItem));
logger.log({ message: 'batch.processed', total: items.length, success: results.filter(r => r.ok).length });
```

**Không nên**:

```ts
// ❌ Bad — 10,000 items = 10,000 log lines → IO bottleneck
for (const item of items) {
  logger.log({ message: 'processing item', itemId: item.id });
  await processItem(item);
}
```

---

## 3. Ví dụ minh họa thực tế

### 3.1. Triển khai Logger module với Winston

**Before** — Dùng console.log rải rác, không có cấu trúc:

```ts
// ❌ Before
@Injectable()
export class OrdersService {
  async create(dto: CreateOrderDto) {
    console.log('Creating order...', dto);
    try {
      const order = await this.repo.save(dto);
      console.log('Order created:', order.id);
      return order;
    } catch (err) {
      console.error('Error creating order', err);
      throw err;
    }
  }
}
```

**After** — Dùng NestJS Logger + structured logging:

```ts
// ✅ After
import { Logger, Injectable } from '@nestjs/common';

@Injectable()
export class OrdersService {
  private readonly logger = new Logger(OrdersService.name);

  async create(dto: CreateOrderDto): Promise<Order> {
    this.logger.log({ message: 'order.creating', userId: dto.userId, itemCount: dto.items.length });
    try {
      const order = await this.repo.save(dto);
      this.logger.log({ message: 'order.created', orderId: order.id, userId: dto.userId, total: order.total });
      return order;
    } catch (err) {
      this.logger.error(
        { message: 'order.create_failed', userId: dto.userId },
        err instanceof Error ? err.stack : String(err),
      );
      throw err;
    }
  }
}
```

### 3.2. Winston Logger Setup cho NestJS

```ts
// common/logger/logger.module.ts — same setup as v535 (infra/logger/logger.module.ts)
import { Global, Module } from '@nestjs/common';
import { WinstonModule } from 'nest-winston';
import * as winston from 'winston';
import DailyRotateFile from 'winston-daily-rotate-file';

// Read at import time, before ConfigModule loads; the schema is in 2.1 section 2.3
const logsDir = process.env.LOG_DIR ?? 'logs';
const level = process.env.LOG_LEVEL ?? 'info';
// API and worker are separate processes: one shared file would get two rotators racing on it
const processType = process.env.PROCESS_TYPE ?? 'api';

// Files hold one JSON object per line, so log tools can parse them
const jsonFormat = winston.format.combine(
  winston.format.timestamp(),
  winston.format.errors({ stack: true }),
  winston.format.json(),
);

const dailyFile = (name: string, maxFiles: string, fileLevel?: string) =>
  new DailyRotateFile({
    dirname: logsDir,
    filename: `${name}-${processType}-%DATE%.log`,
    datePattern: 'YYYY-MM-DD',
    level: fileLevel,
    maxFiles,
    maxSize: '20m', // A crash loop can fill one dated file, so cap it
    zippedArchive: true,
    format: jsonFormat,
  });

@Global()
@Module({
  imports: [
    WinstonModule.forRoot({
      level,
      transports: [
        // Console: readable text for local development
        new winston.transports.Console({
          format: winston.format.combine(
            winston.format.timestamp({ format: 'YYYY-MM-DD HH:mm:ss' }),
            winston.format.colorize(),
            winston.format.printf(({ timestamp, level, message, context, ...meta }) => {
              const ctx = typeof context === 'string' ? `[${context}] ` : '';
              const extra = Object.keys(meta).length ? ` ${JSON.stringify(meta)}` : '';
              return `${String(timestamp)} ${level} ${ctx}${String(message)}${extra}`;
            }),
          ),
        }),
        // Errors: the smallest file, kept longest because incidents get reported days later
        dailyFile('error', '30d', 'error'),
        // Every line, including per-request logs: the largest file, kept shortest
        dailyFile('combined', '7d'),
      ],
      // Uncaught exceptions that crash the process
      exceptionHandlers: [dailyFile('exceptions', '30d')],
    }),
  ],
})
export class LoggerModule {}
```

`main.ts` gắn Winston vào NestJS `Logger`. Thiếu `useLogger`, mọi `new Logger(X.name)` vẫn in bằng logger mặc định và không ghi file.

```ts
// main.ts
import { NestFactory } from '@nestjs/core';
import { WINSTON_MODULE_NEST_PROVIDER } from 'nest-winston';
import { AppModule } from './app.module'; // imports LoggerModule

async function bootstrap() {
  const app = await NestFactory.create(AppModule, {
    bufferLogs: true, // Hold startup logs until Winston is attached below
  });
  // From here every new Logger(X.name) writes through Winston
  app.useLogger(app.get(WINSTON_MODULE_NEST_PROVIDER));
  await app.listen(process.env.PORT ?? 3000);
}
bootstrap();
```

### 3.3. Request Logging Interceptor

```ts
// common/interceptors/logging.interceptor.ts
@Injectable()
export class LoggingInterceptor implements NestInterceptor {
  private readonly logger = new Logger('HTTP');

  intercept(context: ExecutionContext, next: CallHandler): Observable<any> {
    const req = context.switchToHttp().getRequest();
    const { method, url, requestId } = req;
    const startTime = Date.now();

    return next.handle().pipe(
      tap(() => {
        const duration = Date.now() - startTime;
        this.logger.log({
          message: 'request.completed',
          requestId,
          method,
          url,
          statusCode: context.switchToHttp().getResponse().statusCode,
          duration: `${duration}ms`,
        });
      }),
      catchError((err) => {
        const duration = Date.now() - startTime;
        this.logger.error({
          message: 'request.failed',
          requestId,
          method,
          url,
          error: err.message,
          duration: `${duration}ms`,
        });
        throw err;
      }),
    );
  }
}
```

---

## 4. Debugging & Monitoring

### 4.1. Debugging

**Local development**:

- Dùng **VSCode Debugger** hoặc **Chrome DevTools** với `--inspect` flag:

```json
// .vscode/launch.json
{
  "type": "node",
  "request": "launch",
  "name": "Debug NestJS",
  "runtimeExecutable": "pnpm",
  "runtimeArgs": ["run", "start:debug"],
  "sourceMaps": true,
  "console": "integratedTerminal"
}
```

- Kết hợp `Logger.debug()` cho các flow phức tạp, nhưng **xoá/disable sau khi fix xong**.

**Staging / Production**:

- Dựa vào **structured logs** + `requestId` để reconstruct flow.
- Kết hợp **distributed tracing** (OpenTelemetry) nếu hệ thống microservices.
- Có thể bật `debug` level tạm thời cho 1 service cụ thể, sau đó tắt lại.

### 4.2. Monitoring

**Metrics cần theo dõi**:

- **Request metrics**: Số request, latency (p50, p95, p99), error rate cho từng endpoint.
- **Business metrics**: Số orders, payment success/fail rate, user signups.
- **System metrics**: CPU, memory, disk, DB connection pool.

**Alert strategy**:

- Error rate tăng đột biến (ví dụ: `order.payment_failed` > 5% trong 5 phút).
- Latency p99 vượt ngưỡng (ví dụ: > 2s cho API endpoint).
- Health check fail.

**Tech stack phổ biến**:

| **Mục đích** | **Tools** | **Ghi chú** |
| --- | --- | --- |
| Log aggregation | ELK Stack, Grafana Loki, Datadog | Tập trung log từ nhiều services |
| Metrics | Prometheus + Grafana, Datadog | Dashboard + alerting |
| Tracing | OpenTelemetry, Jaeger, Zipkin | Distributed tracing cho microservices |
| Health checks | `@nestjs/terminus` | `/health/liveness` không check dependency, `/health/readiness` check DB, Redis, disk |

**Health check example**:

```ts
// health/health.controller.ts
@Controller({ path: 'health', version: VERSION_NEUTRAL }) // Probes call /health, outside /v1
export class HealthController {
  constructor(
    private health: HealthCheckService,
    private db: TypeOrmHealthIndicator, // Prisma: PrismaHealthIndicator, see 7.3 section 3.1
  ) {}

  // Liveness: answers while the process runs; no dependency checks, so a DB outage never restarts the pod
  @Get('liveness')
  @HealthCheck()
  liveness() {
    return this.health.check([
      () => ({ app: { status: 'up' } }),
    ]);
  }

  // Readiness: dependencies the app needs to serve traffic (full version in 7.3 section 3.1)
  @Get('readiness')
  @HealthCheck()
  readiness() {
    return this.health.check([
      () => this.db.pingCheck('database', { timeout: 3000 }),
    ]);
  }
}
```

---

## 5. Tooling & Config

### 5.1. Log rotation — tránh full disk

Dùng `winston-daily-rotate-file` (xem ví dụ ở Section 3.2):

- `maxSize: '20m'` — rotate khi file đạt 20MB.
- `maxFiles` — file `error-*` giữ 30 ngày, file `combined-*` giữ 7 ngày.
- `zippedArchive: true` — nén file đã rotate.
- Image chạy user non-root phải tạo sẵn thư mục `logs/` cho user đó, xem Dockerfile ở [NestJS Coding Standard 9.3 — Build & Deployment](Ref_Dev_s9.3_nestjs-build-deployment_v1.0.md) mục 2.2.
- Hoặc dùng cron job + S3 lifecycle rules cho long-term storage.

### 5.2. Pino — alternative nhanh hơn Winston

Nếu performance là ưu tiên (high-throughput services), dùng Pino thay Winston:

```ts
// main.ts
import { Logger } from 'nestjs-pino';

app.useLogger(app.get(Logger));
```

**Trade-off**: Pino nhanh hơn \~5x so với Winston nhờ async write, nhưng ít transport plugins hơn. Winston phổ biến hơn, ecosystem rộng hơn.

### 5.3. Environment-based log config

| Biến | Mặc định | Ý nghĩa |
| --- | --- | --- |
| `LOG_LEVEL` | `info` | Level thấp nhất được ghi |
| `LOG_DIR` | `logs` | Thư mục chứa file log |
| `PROCESS_TYPE` | `api` | `api` hoặc `worker`, nằm trong tên file log |

---

## 6. Tóm tắt nguyên tắc

> 📌 **Dev**: Dùng console/Logger nhiều hơn, ưu tiên tốc độ debug. Bật `debug`/`verbose` level.
>
> **Staging**: Log structured (JSON), bật `debug` level, test log pipeline.
>
> **Production**: Bắt buộc **logger có cấu trúc**, log đủ nhưng không thừa, có chiến lược rotation, monitoring & alerting rõ ràng.

---

## References

- [NestJS Logger Documentation](https://docs.nestjs.com/techniques/logger)
- [Winston Documentation](https://github.com/winstonjs/winston)
- [Pino Documentation](https://github.com/pinojs/pino)
- [NestJS Terminus (Health Checks)](https://docs.nestjs.com/recipes/terminus)
- [OpenTelemetry for Node.js](https://opentelemetry.io/docs/languages/js/)
- [Node.js AsyncLocalStorage](https://nodejs.org/docs/latest/api/async_context.html#class-asynclocalstorage)
- [12-Factor App: Logs](https://12factor.net/logs)

## Changelog

| Date | Version | Change | By |
| :---- | :---- | :---- | :---- |
| 2026-11-18 | v1.0 | Chuyển từ Notion "NestJS Document" (page `33d71a38d3b281fa9d89fd9651dc233b`, sửa 2026-04-09). Review và sửa nội dung, code trước khi publish. Owner duyệt trong chat ngày 2026-11-18. | Bắc PV |
