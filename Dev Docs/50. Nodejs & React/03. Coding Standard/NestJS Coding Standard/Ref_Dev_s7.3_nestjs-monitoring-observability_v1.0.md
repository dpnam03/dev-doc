# NestJS Coding Standard 7.3 — Monitoring & Observability

| Field | Value |
| :---- | :---- |
| Owner | Bắc PV — NodeJS BE Dev Lead |
| Audience | Dev (NodeJS BE) |
| Last reviewed | 2026-11-12 |
| Review cadence | Quarterly |
| Version | v1.0 |
| Linked from | Ref_Dev_nestjs-coding-standard_v1.0 |
| Status | Live |

Doc này là mục 7.3 của [NestJS Coding Standard](Ref_Dev_nestjs-coding-standard_v1.0.md), nhóm Observability. Doc nêu quy tắc về Monitoring & Observability trong dự án NestJS, kèm lý do, ví dụ và config. Dev NodeJS BE đọc doc này khi viết code, review code và onboarding.

---

---

## 1. Tóm tắt & Phạm vi

> 📡 **Monitoring & Observability** giải quyết bài toán: *“Hệ thống đang hoạt động tốt không? Nếu có vấn đề, vấn đề ở đâu?”*

Trong khi **Logging** (xem [NestJS Coding Standard 7.1 — Logging](Ref_Dev_s7.1_nestjs-logging_v1.0.md)) tập trung vào việc ghi lại sự kiện, **Monitoring & Observability** mở rộng hơn với 3 trụ cột:

- **Health Checks** — Kiểm tra sức khỏe app + dependencies (DB, Redis, external APIs) liên tục.
- **Metrics** — Đo lường định lượng: request rate, latency (p50/p95/p99), error rate, resource usage.
- **Distributed Tracing** — Theo dõi hành trình của một request xuyên suốt nhiều services/layers.
- **Diagnostics Channel** (Node.js) — Pub/sub channel nội bộ, low-overhead, dùng cho instrumentation.

**Phạm vi áp dụng:**

- Mọi NestJS app triển khai staging/production.
- Đặc biệt quan trọng với microservices hoặc hệ thống nhiều external dependencies.
- Kết hợp với logging (7.1) để có bức tranh observability hoàn chỉnh.

**Tại sao quan trọng?**

- Phát hiện sự cố sớm trước khi user bị ảnh hưởng.
- Giảm MTTR (Mean Time To Recovery) — từ hàng giờ xuống phút nhờ trace + metrics.
- Kubernetes/load balancer cần health check để routing traffic đúng cách.
- Production không có debugger — observability là “đôi mắt” duy nhất.

---

## 2. Quy tắc & Giải thích

### 2.1. Health Checks (`@nestjs/terminus`)

> 💚 **Health check** = endpoint HTTP trả về trạng thái sức khỏe của app và dependencies.

**✅ NÊN:**

- **Tách biệt liveness và readiness probes:**
- `GET /health/liveness` — App đang chạy? (chỉ check process alive)
- `GET /health/readiness` — App sẵn sàng nhận traffic? (check DB, Redis, external services)
- *Tại sao:* Kubernetes dùng liveness để restart pod bị stuck, readiness để ngừng route traffic đến pod chưa sẵn sàng. Gộp chung → restart loop khi chỉ DB tạm down.
- **Dùng `@nestjs/terminus` — thư viện chính thống của NestJS:**
- Cung cấp sẵn health indicators cho TypeORM, Mongoose, Redis, HTTP, Disk, Memory.
- `HealthCheckService` orchestrate nhiều checks cùng lúc.
- *Tại sao:* Chuẩn hóa response format, tích hợp sẵn với NestJS DI, community maintained.
- **Đặt timeout cho mỗi health indicator:**
- DB ping timeout 3–5s, external API timeout 5–10s.
- *Tại sao:* Health check endpoint chậm → Kubernetes coi app là unhealthy → restart loop.
- **Tạo custom health indicator cho business-critical dependencies:**
- Dùng `HealthIndicatorService` (v11+) hoặc extend `HealthIndicator` (v10).
- *Tại sao:* Built-in indicators không cover hết (message queue, custom cache, third-party API).

**❌ KHÔNG NÊN:**

- **Không gọi heavy query trong health check** — chỉ ping/simple query. Health check chạy mỗi 5–30s, query nặng tạo load không cần thiết.
- **Không check external services trong liveness** — liveness chỉ check app process. External dependency down không phải lý do restart app.
- **Không check heap bằng mốc cố định trong readiness** — mốc lệch với `--max-old-space-size` ([NestJS Coding Standard 9.1 — Performance & Resource Management](Ref_Dev_s9.1_nestjs-performance-resource-management_v1.0.md) mục 2.x) làm pod bị rút khỏi traffic dù vẫn chạy bình thường.
- **Không expose health check ra public** — nên protect hoặc chỉ expose nội bộ (internal network/k8s).

### 2.2. Metrics (Prometheus + Grafana)

> 📊 **Metrics** = dữ liệu số đo lường theo thời gian (time-series). Dùng để detect anomalies, set alerts, và capacity planning.

**✅ NÊN:**

- **Expose metrics endpoint `/metrics` theo Prometheus format:**
- Dùng `prom-client` (official Prometheus client cho Node.js) hoặc `@opentelemetry/exporter-prometheus`.
- *Tại sao:* Prometheus là de facto standard cho metrics trong Kubernetes ecosystem. Grafana đọc trực tiếp từ Prometheus.
- **Track 4 golden signals (RED + Saturation):**
- **Rate** — Requests per second (total + per endpoint).
- **Errors** — Error rate (4xx, 5xx) per endpoint.
- **Duration** — Latency histogram với p50, p95, p99.
- **Saturation** — CPU, memory, event loop lag, connection pool usage.
- *Tại sao:* Google SRE golden signals — cover 80% monitoring needs.
- **Dùng Histogram cho latency, không dùng Summary:**
- Histogram cho phép aggregate qua nhiều instances. Summary thì không.
- Buckets mặc định: `[0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1, 2.5, 5, 10]` (seconds).
- **Naming convention theo Prometheus best practices:**
- `<app>_<unit>_<suffix>`: `http_request_duration_seconds`, `orders_created_total`.
- Counter suffix `_total`, Histogram suffix `_seconds` hoặc `_bytes`.
- **Tạo custom metrics cho business KPIs:**
- `orders_created_total`, `payment_failed_total`, `queue_depth`.
- *Tại sao:* Infrastructure metrics (CPU, memory) chưa đủ — cần biết business đang healthy không.

**❌ KHÔNG NÊN:**

- **Không tạo metric với high cardinality labels** — ví dụ label `userId`, `orderId`. Prometheus không chịu nổi millions of time series.
- **Không tạo mới `PrometheusClient` mỗi request** — dùng singleton, register metrics một lần khi bootstrap.
- **Không expose `/metrics` ra public** — chỉ internal scraping.

### 2.3. Distributed Tracing (OpenTelemetry)

> 🔭 **Distributed tracing** = theo dõi một request từ đầu đến cuối, xuyên qua nhiều services, DB calls, HTTP calls, message queues.

**✅ NÊN:**

- **Dùng OpenTelemetry (OTel) — tiêu chuẩn vendor-neutral của CNCF:**
- OTel SDK auto-instrument HTTP, Express, TypeORM, Redis, gRPC mà không cần sửa code.
- Export traces đến Jaeger, Zipkin, Grafana Tempo, Datadog, AWS X-Ray, v.v.
- *Tại sao:* Vendor-neutral → đổi backend tracing không cần đổi code. Community lớn nhất.
- **Init OTel tracing TRƯỚC khi import NestJS:**
- Tạo file `tracing.ts` riêng, import nó ở dòng đầu tiên của `main.ts`.
- *Tại sao:* OTel monkey-patch các thư viện (http, express, pg, redis) khi require. Nếu import sau → miss instrumentation.
- **Propagate trace context (W3C Trace Context):**
- Auto-propagation qua HTTP headers (`traceparent`, `tracestate`).
- Với message queues (Kafka, RabbitMQ): inject trace context vào message headers.
- *Tại sao:* Không propagate → trace bị đứt giữa các services, mất ý nghĩa distributed tracing.
- **Thêm custom spans cho business operations quan trọng:**
- `tracer.startSpan('process-payment')` cho logic phức tạp.
- Thêm attributes: `span.setAttribute('order.id', orderId)`.
- *Tại sao:* Auto-instrumentation chỉ bắt HTTP/DB. Business logic cần manual spans để debug.
- **Dùng sampling trong production:**
- `TraceIdRatioBasedSampler(0.1)` — sample 10% traces.
- Hoặc `ParentBasedSampler` để respect upstream sampling decision.
- Chọn sampler qua env `OTEL_TRACES_SAMPLER` / `OTEL_TRACES_SAMPLER_ARG` (mục 4.4), không hardcode trong code.
- *Tại sao:* 100% traces trong high-traffic = rất tốn storage + bandwidth. 10% đủ để phát hiện patterns.

**❌ KHÔNG NÊN:**

- **Không record sensitive data trong spans** — không log password, token, PII vào span attributes.
- **Không tạo span cho mọi function** — chỉ span cho I/O operations hoặc business logic quan trọng. Quá nhiều spans → trace quá dài, tốn resource.
- **Không bỏ qua error recording** — `span.recordException(error)` + `span.setStatus({ code: SpanStatusCode.ERROR })`.

### 2.4. Diagnostics Channel (Node.js)

> 🔬 **`node:diagnostics_channel`** = pub/sub API có sẵn trong Node.js core, overhead cực thấp khi không có subscriber. Dùng để instrument modules mà không cần monkey-patching.

**✅ NÊN:**

- **Dùng `diagnostics_channel` để publish diagnostic events từ shared modules:**
- Channel name convention: `<module>.<action>` — `db.query`, `http.request.start`.
- *Tại sao:* Zero overhead khi không có subscriber. Không cần dependency, có sẵn trong Node.js core (v15+, stable từ v19.2).
- **Kết hợp với `AsyncLocalStorage` cho request context:**
- Dùng `channel.bindStore(asyncLocalStorage)` để tự động gắn context.
- *Tại sao:* Request ID, user ID được propagate xuyên suốt async operations mà không cần pass params.
- **Check `channel.hasSubscribers` trước khi publish data đắt:**
- *Tại sao:* Tránh serialize/prepare data khi không ai lắng nghe.
- **Dùng `tracingChannel` (Node.js v19.9+) cho start/end/error lifecycle:**
- Tự động tạo `start`, `end`, `asyncStart`, `asyncEnd`, `error` channels.
- *Tại sao:* Chuẩn hóa tracing pattern, tích hợp tốt với OpenTelemetry.

**❌ KHÔNG NÊN:**

- **Không dùng `diagnostics_channel` thay thế logging** — nó dành cho instrumentation, không phải application logging.
- **Không publish objects lớn** — subscribers chạy synchronous, object lớn block event loop.

---

## 3. Ví dụ minh họa thực tế

### 3.1. Health Check Module hoàn chỉnh

```ts
// src/api/system/system-api.module.ts — health check is a system endpoint (1.1 section 2.2)
import { Module } from '@nestjs/common';
import { TerminusModule } from '@nestjs/terminus';
import { HttpModule } from '@nestjs/axios';
import { HealthController } from './health.controller';
import { RedisHealthIndicator } from './indicators/redis.health';

@Module({
  imports: [TerminusModule, HttpModule],
  controllers: [HealthController],
  providers: [RedisHealthIndicator],
})
export class SystemApiModule {}
```

```ts
// src/api/system/health.controller.ts
import { Controller, Get, VERSION_NEUTRAL } from '@nestjs/common';
import { ApiTags, ApiOperation } from '@nestjs/swagger';
import {
  HealthCheck,
  HealthCheckService,
  TypeOrmHealthIndicator,
  HttpHealthIndicator,
  DiskHealthIndicator,
} from '@nestjs/terminus';
import { RedisHealthIndicator } from './indicators/redis.health';

@ApiTags('health')
@Controller({ path: 'health', version: VERSION_NEUTRAL }) // Probes call /health, outside /v1
export class HealthController {
  constructor(
    private readonly health: HealthCheckService,
    private readonly db: TypeOrmHealthIndicator,
    private readonly http: HttpHealthIndicator,
    private readonly disk: DiskHealthIndicator,
    private readonly redis: RedisHealthIndicator,
  ) {}

  // Liveness — chỉ check app process alive
  @Get('liveness')
  @HealthCheck()
  @ApiOperation({ summary: 'Liveness probe — app đang chạy?' })
  liveness() {
    return this.health.check([
      () => ({ app: { status: 'up' } }),
    ]);
  }

  // Readiness — check tất cả dependencies
  @Get('readiness')
  @HealthCheck()
  @ApiOperation({ summary: 'Readiness probe — app sẵn sàng nhận traffic?' })
  readiness() {
    return this.health.check([
      () => this.db.pingCheck('database', { timeout: 3000 }),
      () => this.redis.isHealthy('redis'),
      () => this.disk.checkStorage('disk', {
        path: '/',
        thresholdPercent: 0.9, // 90%
      }),
    ]);
  }
}
```

Project dùng Prisma chỉ đổi DB indicator: `PrismaHealthIndicator` thay cho `TypeOrmHealthIndicator`, truyền thêm `PrismaService`.

```ts
// health.controller.ts — Prisma projects: only the database indicator changes
constructor(
  private readonly health: HealthCheckService,
  private readonly db: PrismaHealthIndicator, // from '@nestjs/terminus'
  private readonly prisma: PrismaService, // global DatabaseModule, 4.1 section 2.7
  // ...other indicators as above
) {}

// in readiness()
() => this.db.pingCheck('database', this.prisma, { timeout: 3000 }),
```

```ts
// src/api/system/indicators/redis.health.ts — Custom health indicator (v11+)
import { Injectable } from '@nestjs/common';
import { HealthIndicatorService } from '@nestjs/terminus';
import { InjectRedis } from '@nestjs-modules/ioredis';
import Redis from 'ioredis';

@Injectable()
export class RedisHealthIndicator {
  constructor(
    private readonly healthIndicatorService: HealthIndicatorService,
    @InjectRedis() private readonly redis: Redis,
  ) {}

  async isHealthy(key: string) {
    const indicator = this.healthIndicatorService.check(key);
    try {
      const result = await this.redis.ping();
      if (result !== 'PONG') {
        return indicator.down({ message: 'Redis ping failed' });
      }
      return indicator.up();
    } catch (error) {
      return indicator.down({ message: error.message });
    }
  }
}
```

**Response khi healthy:**

```json
{
  "status": "ok",
  "info": {
    "database": { "status": "up" },
    "redis": { "status": "up" },
    "memory_heap": { "status": "up" },
    "disk": { "status": "up" }
  },
  "error": {},
  "details": { ... }
}
```

**Response khi unhealthy (HTTP 503):**

```json
{
  "status": "error",
  "info": { "database": { "status": "up" } },
  "error": { "redis": { "status": "down", "message": "Connection refused" } },
  "details": { ... }
}
```

### 3.2. Prometheus Metrics Setup

```ts
// src/common/metrics/metrics.module.ts
import { Global, Module } from '@nestjs/common';
import { MetricsService } from './metrics.service';
import { MetricsController } from './metrics.controller';
import { MetricsInterceptor } from './metrics.interceptor';
import { APP_INTERCEPTOR } from '@nestjs/core';

@Global()
@Module({
  controllers: [MetricsController],
  providers: [
    MetricsService,
    { provide: APP_INTERCEPTOR, useClass: MetricsInterceptor },
  ],
  exports: [MetricsService],
})
export class MetricsModule {}
```

```ts
// src/common/metrics/metrics.service.ts
import { Injectable, OnModuleInit } from '@nestjs/common';
import * as client from 'prom-client';

@Injectable()
export class MetricsService implements OnModuleInit {
  private readonly register = new client.Registry();

  // HTTP metrics
  readonly httpRequestDuration = new client.Histogram({
    name: 'http_request_duration_seconds',
    help: 'Duration of HTTP requests in seconds',
    labelNames: ['method', 'route', 'status_code'] as const,
    buckets: [0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1, 2.5, 5, 10],
  });

  readonly httpRequestTotal = new client.Counter({
    name: 'http_requests_total',
    help: 'Total number of HTTP requests',
    labelNames: ['method', 'route', 'status_code'] as const,
  });

  // Business metrics
  readonly ordersCreatedTotal = new client.Counter({
    name: 'orders_created_total',
    help: 'Total orders created',
    labelNames: ['status'] as const,
  });

  readonly activeConnections = new client.Gauge({
    name: 'active_connections',
    help: 'Number of active connections',
  });

  onModuleInit() {
    // Collect default Node.js metrics (CPU, memory, event loop lag, GC)
    client.collectDefaultMetrics({ register: this.register });
    this.register.registerMetric(this.httpRequestDuration);
    this.register.registerMetric(this.httpRequestTotal);
    this.register.registerMetric(this.ordersCreatedTotal);
    this.register.registerMetric(this.activeConnections);
  }

  async getMetrics(): Promise<string> {
    return this.register.metrics();
  }

  getContentType(): string {
    return this.register.contentType;
  }
}
```

```ts
// src/common/metrics/metrics.interceptor.ts
import { Injectable, NestInterceptor, ExecutionContext, CallHandler } from '@nestjs/common';
import { Observable, tap } from 'rxjs';
import { MetricsService } from './metrics.service';

@Injectable()
export class MetricsInterceptor implements NestInterceptor {
  constructor(private readonly metrics: MetricsService) {}

  intercept(context: ExecutionContext, next: CallHandler): Observable<any> {
    const req = context.switchToHttp().getRequest();
    const { method } = req;
    const route = req.route?.path || req.url;
    const timer = this.metrics.httpRequestDuration.startTimer({ method, route });

    return next.handle().pipe(
      tap({
        next: () => {
          const statusCode = context.switchToHttp().getResponse().statusCode;
          timer({ status_code: statusCode });
          this.metrics.httpRequestTotal.inc({ method, route, status_code: statusCode });
        },
        error: (error) => {
          const statusCode = error.status || 500;
          timer({ status_code: statusCode });
          this.metrics.httpRequestTotal.inc({ method, route, status_code: statusCode });
        },
      }),
    );
  }
}
```

```ts
// src/common/metrics/metrics.controller.ts
import { Controller, Get, Header } from '@nestjs/common';
import { ApiExcludeController } from '@nestjs/swagger';
import { MetricsService } from './metrics.service';

@ApiExcludeController()
@Controller('metrics')
export class MetricsController {
  constructor(private readonly metrics: MetricsService) {}

  @Get()
  @Header('Content-Type', 'text/plain')
  async getMetrics(): Promise<string> {
    return this.metrics.getMetrics();
  }
}
```

**Sử dụng business metrics trong service:**

```ts
// src/modules/orders/orders.service.ts
@Injectable()
export class OrdersService {
  constructor(
    private readonly ordersRepo: OrdersRepository,
    private readonly metrics: MetricsService,
  ) {}

  async create(dto: CreateOrderDto): Promise<Order> {
    try {
      const order = await this.ordersRepo.create(dto);
      this.metrics.ordersCreatedTotal.inc({ status: 'success' });
      return order;
    } catch (error) {
      this.metrics.ordersCreatedTotal.inc({ status: 'failed' });
      throw error;
    }
  }
}
```

### 3.3. OpenTelemetry Tracing Setup

```ts
// src/tracing.ts — PHẢI import TRƯỚC mọi thứ khác
import { NodeSDK } from '@opentelemetry/sdk-node';
import { getNodeAutoInstrumentations } from '@opentelemetry/auto-instrumentations-node';
import { OTLPTraceExporter } from '@opentelemetry/exporter-trace-otlp-http';
import { OTLPMetricExporter } from '@opentelemetry/exporter-metrics-otlp-http';
import { PeriodicExportingMetricReader } from '@opentelemetry/sdk-metrics';
import { resourceFromAttributes } from '@opentelemetry/resources';
import {
  ATTR_SERVICE_NAME,
  ATTR_SERVICE_VERSION,
  ATTR_DEPLOYMENT_ENVIRONMENT_NAME,
} from '@opentelemetry/semantic-conventions';

export const otelSdk = new NodeSDK({
  resource: resourceFromAttributes({
    [ATTR_SERVICE_NAME]: process.env.SERVICE_NAME || 'nestjs-app',
    [ATTR_SERVICE_VERSION]: process.env.npm_package_version || '1.0.0',
    [ATTR_DEPLOYMENT_ENVIRONMENT_NAME]: process.env.NODE_ENV || 'development',
  }),

  // Trace exporter — gửi đến Jaeger/Tempo/Zipkin qua OTLP.
  // No `url`: the exporter reads OTEL_EXPORTER_OTLP_ENDPOINT and appends /v1/traces
  // (default http://localhost:4318/v1/traces). A `url` option is used as-is, without the path.
  traceExporter: new OTLPTraceExporter(),

  // Metric exporter — same rule, appends /v1/metrics
  metricReader: new PeriodicExportingMetricReader({
    exporter: new OTLPMetricExporter(),
    exportIntervalMillis: 15000,
  }),

  // Sampling: no `sampler` here, so the SDK reads OTEL_TRACES_SAMPLER / OTEL_TRACES_SAMPLER_ARG
  // (section 4.4: parentbased_traceidratio, 0.1). Unset = parentbased_always_on (100%).

  // Auto-instrument HTTP, Express, TypeORM, Redis, pg, etc.
  instrumentations: [
    getNodeAutoInstrumentations({
      '@opentelemetry/instrumentation-fs': { enabled: false }, // Quá noisy
      '@opentelemetry/instrumentation-net': { enabled: false },
    }),
  ],
});

otelSdk.start();

// Graceful shutdown: no process.on('SIGTERM') here. main.ts enables Nest shutdown hooks and
// TracingShutdownService flushes the SDK; an extra listener swallows the signal Nest re-sends to exit.
```

```ts
// src/main.ts — import tracing TRƯỚC
import './tracing'; // ← Dòng ĐẦU TIÊN

import { NestFactory } from '@nestjs/core';
import { AppModule } from './app.module';

async function bootstrap() {
  const app = await NestFactory.create(AppModule);
  app.enableShutdownHooks(); // SIGTERM → Nest hooks → TracingShutdownService flushes spans
  await app.listen(3000);
}
bootstrap();
```

```ts
// src/common/tracing/tracing-shutdown.service.ts — register in AppModule providers
import { Injectable, OnApplicationShutdown } from '@nestjs/common';
import { otelSdk } from '../../tracing';

@Injectable()
export class TracingShutdownService implements OnApplicationShutdown {
  // Nest calls this after the HTTP server has closed, so spans of in-flight requests are flushed
  async onApplicationShutdown(): Promise<void> {
    await otelSdk.shutdown();
  }
}
```

**Custom spans trong service:**

```ts
// src/modules/orders/orders.service.ts
import { trace, SpanStatusCode } from '@opentelemetry/api';

const tracer = trace.getTracer('orders-service');

@Injectable()
export class OrdersService {
  async create(dto: CreateOrderDto): Promise<Order> {
    return tracer.startActiveSpan('orders.create', async (span) => {
      try {
        span.setAttribute('order.items_count', dto.items.length);
        span.setAttribute('order.customer_id', dto.customerId);

        // Nested span cho sub-operation
        const order = await tracer.startActiveSpan('orders.validate-stock', async (childSpan) => {
          const result = await this.validateStock(dto.items);
          childSpan.end();
          return result;
        });

        const saved = await this.ordersRepo.save(order);
        span.setAttribute('order.id', saved.id);
        span.setStatus({ code: SpanStatusCode.OK });
        return saved;
      } catch (error) {
        span.recordException(error);
        span.setStatus({ code: SpanStatusCode.ERROR, message: error.message });
        throw error;
      } finally {
        span.end();
      }
    });
  }
}
```

### 3.4. Diagnostics Channel — Database Query Monitoring

```ts
// src/common/diagnostics/db-diagnostics.ts
import diagnostics_channel from 'node:diagnostics_channel';

// Tạo channel cho DB query diagnostics
const queryChannel = diagnostics_channel.channel('app.db.query');

// Trong repository/service — publish query info
export function publishQueryDiagnostics(data: {
  sql: string;
  duration: number;
  table: string;
  rowCount?: number;
}) {
  // Zero overhead khi không có subscriber
  if (queryChannel.hasSubscribers) {
    queryChannel.publish(data);
  }
}
```

```ts
// src/common/diagnostics/db-diagnostics.subscriber.ts
import diagnostics_channel from 'node:diagnostics_channel';
import { Logger } from '@nestjs/common';

const logger = new Logger('DBDiagnostics');
const SLOW_QUERY_THRESHOLD_MS = 100;

// Subscribe — log slow queries
diagnostics_channel.subscribe('app.db.query', (message: any) => {
  if (message.duration > SLOW_QUERY_THRESHOLD_MS) {
    logger.warn({
      message: 'slow_query_detected',
      sql: message.sql.substring(0, 200), // Truncate
      duration: message.duration,
      table: message.table,
    });
  }
});
```

```ts
// Sử dụng TracingChannel (Node.js v19.9+) cho lifecycle events
import diagnostics_channel from 'node:diagnostics_channel';

const channels = diagnostics_channel.tracingChannel('app.payment');

// Wrap function — tự động publish start/end/error events
async function processPayment(orderId: string, amount: number) {
  return channels.tracePromise(
    async () => {
      // Business logic
      const result = await paymentGateway.charge(amount);
      return result;
    },
    { orderId, amount }, // Context data
  );
}

// Subscribe to lifecycle
channels.start.subscribe((message) => {
  console.log('Payment started:', message.orderId);
});
channels.end.subscribe((message) => {
  console.log('Payment completed:', message.orderId);
});
channels.error.subscribe((message) => {
  console.error('Payment failed:', message.error);
});
```

---

## 4. Tooling & Config

### 4.1. Packages cần cài

```bash
# Health checks
pnpm add @nestjs/terminus @nestjs/axios

# Prometheus metrics
pnpm add prom-client

# OpenTelemetry (tracing + metrics)
pnpm add @opentelemetry/sdk-node \
  @opentelemetry/auto-instrumentations-node \
  @opentelemetry/exporter-trace-otlp-http \
  @opentelemetry/exporter-metrics-otlp-http \
  @opentelemetry/sdk-metrics \
  @opentelemetry/resources \
  @opentelemetry/semantic-conventions \
  @opentelemetry/api
```

### 4.2. Docker Compose — Local observability stack

```yaml
# docker-compose.observability.yml
services:
  # Jaeger — Tracing UI
  jaeger:
    image: jaegertracing/all-in-one:latest
    ports:
      - '16686:16686'  # Jaeger UI
      - '4318:4318'    # OTLP HTTP receiver
    environment:
      COLLECTOR_OTLP_ENABLED: 'true'

  # Prometheus — Metrics scraping
  prometheus:
    image: prom/prometheus:latest
    ports:
      - '9090:9090'
    volumes:
      - ./prometheus.yml:/etc/prometheus/prometheus.yml

  # Grafana — Dashboards
  grafana:
    image: grafana/grafana:latest
    ports:
      - '3001:3000'
    environment:
      GF_SECURITY_ADMIN_PASSWORD: admin
```

```yaml
# prometheus.yml
global:
  scrape_interval: 15s

scrape_configs:
  - job_name: 'nestjs-app'
    static_configs:
      - targets: ['host.docker.internal:3000']
    metrics_path: '/metrics'
```

### 4.3. Kubernetes probes

```yaml
# k8s deployment — health check probes
spec:
  containers:
    - name: nestjs-app
      livenessProbe:
        httpGet:
          path: /health/liveness
          port: 3000
        initialDelaySeconds: 10
        periodSeconds: 30
        timeoutSeconds: 5
        failureThreshold: 3
      readinessProbe:
        httpGet:
          path: /health/readiness
          port: 3000
        initialDelaySeconds: 5
        periodSeconds: 10
        timeoutSeconds: 5
        failureThreshold: 3
      startupProbe:
        httpGet:
          path: /health/liveness
          port: 3000
        initialDelaySeconds: 5
        periodSeconds: 5
        failureThreshold: 30
```

### 4.4. Environment variables

```bash
# .env.example — Observability config
SERVICE_NAME=my-nestjs-app
NODE_ENV=development

# OpenTelemetry
OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:4318
OTEL_TRACES_SAMPLER=parentbased_traceidratio
OTEL_TRACES_SAMPLER_ARG=0.1

# Prometheus (nếu dùng push gateway)
PROMETHEUS_PUSH_GATEWAY_URL=http://localhost:9091
```

---

## References

- [NestJS Health Checks (Terminus)](https://docs.nestjs.com/recipes/terminus) — Official NestJS docs
- [OpenTelemetry Node.js SDK](https://opentelemetry.io/docs/languages/js/) — Official OTel docs
- [`nestjs-otel`](https://github.com/pragmaticivan/nestjs-otel) — OpenTelemetry module cho NestJS
- [`prom-client`](https://github.com/siimon/prom-client) — Prometheus client cho Node.js
- [Node.js ](https://nodejs.org/api/diagnostics_channel.html)[`diagnostics_channel`](https://nodejs.org/api/diagnostics_channel.html) — Official Node.js docs
- [Google SRE — Monitoring Distributed Systems](https://sre.google/sre-book/monitoring-distributed-systems/) — Golden signals
- [Prometheus Naming Conventions](https://prometheus.io/docs/practices/naming/) — Metric naming best practices

## Changelog

| Date | Version | Change | By |
| :---- | :---- | :---- | :---- |
| 2026-11-18 | v1.0 | Chuyển từ Notion "NestJS Document" (page `33d71a38d3b28147a7e2fa50e31f7a43`, sửa 2026-04-09). Review và sửa nội dung, code trước khi publish. Owner duyệt trong chat ngày 2026-11-18. | Bắc PV |
