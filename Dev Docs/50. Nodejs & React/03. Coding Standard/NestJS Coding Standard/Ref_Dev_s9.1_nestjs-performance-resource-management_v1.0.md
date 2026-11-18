# NestJS Coding Standard 9.1 — Performance & Resource Management

| Field | Value |
| :---- | :---- |
| Owner | Bắc PV — NodeJS BE Dev Lead |
| Audience | Dev (NodeJS BE) |
| Last reviewed | 2026-11-12 |
| Review cadence | Quarterly |
| Version | v1.0 |
| Linked from | Ref_Dev_nestjs-coding-standard_v1.0 |
| Status | Live |

Doc này là mục 9.1 của [NestJS Coding Standard](Ref_Dev_nestjs-coding-standard_v1.0.md), nhóm Performance & Operations. Doc nêu quy tắc về Performance & Resource Management trong dự án NestJS, kèm lý do, ví dụ và config. Dev NodeJS BE đọc doc này khi viết code, review code và onboarding.

---

## 1. Tóm tắt & Phạm vi

> 📌 **Chủ đề này giải quyết vấn đề gì?**
>
> Performance & Resource Management bao gồm các kỹ thuật tối ưu hiệu năng và quản lý tài nguyên trong ứng dụng NestJS/Node.js: tận dụng multi-core CPU (Cluster, Worker Threads), giám sát và tối ưu memory, xử lý graceful shutdown để đảm bảo zero-downtime deployment, và profiling để phát hiện bottlenecks.
>
> **Áp dụng cho scope nào?**
> - Production deployment (scaling, availability)
> - CPU-intensive tasks (image processing, crypto, data transformation)
> - Memory-sensitive applications (large datasets, caching layers)
> - CI/CD & container orchestration (Docker, Kubernetes)
>
> **Tại sao quan trọng?**
>
> Node.js chạy single-threaded — nếu không scale đúng cách, ứng dụng sẽ chỉ dùng 1 CPU core, dễ bị block bởi CPU-intensive tasks, và crash không graceful khi deploy/restart gây mất request.

---

## 2. Quy tắc & Giải thích

### 2.1 Node.js Cluster — Scale theo CPU cores

**Nên làm:**

- **Dùng Cluster module hoặc PM2 cluster mode để chạy nhiều worker processes**, mỗi worker là 1 Node.js process riêng biệt, tận dụng tất cả CPU cores.
- *Tại sao:* Node.js event loop chạy trên 1 thread duy nhất. Trên server 8-core mà chạy 1 process = lãng phí 87.5% CPU capacity.
- Tham khảo: [Node.js Cluster documentation](https://nodejs.org/docs/latest/api/cluster.html)
- **Để container orchestrator (Docker/K8s) quản lý scaling thay vì tự cluster trong code** khi chạy trên container environment.
- *Tại sao:* K8s Horizontal Pod Autoscaler (HPA) scale linh hoạt hơn, có health checks, rolling updates tích hợp. Tự cluster trong container = mỗi pod chạy N process, phức tạp hóa resource limits và monitoring.
- **Set số workers = số CPU cores có sẵn**, không hardcode.
- Dùng `os.availableParallelism()` (Node.js ≥ 19.4) hoặc `os.cpus().length` để detect.
- Trong container, set `UV_THREADPOOL_SIZE` và workers dựa trên allocated CPU, không phải host CPU.

**Không nên làm:**

- ❌ Hardcode số workers (`cluster.fork()` x 8) — mỗi môi trường có CPU khác nhau.
- ❌ Dùng cluster cho CPU-intensive task processing — dùng Worker Threads thay thế (xem mục 2.2).
- ❌ Share in-memory state giữa workers (mỗi worker có heap riêng) — dùng Redis/DB cho shared state.

### 2.2 Worker Threads — Offload CPU-intensive tasks

**Nên làm:**

- **Dùng `worker_threads` cho CPU-intensive operations** (image processing, hashing lớn, PDF generation, data parsing) để không block event loop.
- *Tại sao:* Event loop bị block = tất cả concurrent requests đều bị chờ. Worker thread chạy trên thread riêng với V8 isolate riêng, không ảnh hưởng main thread.
- Tham khảo: [Node.js Worker Threads documentation](https://nodejs.org/docs/latest/api/worker_threads.html)
- **Dùng worker pool pattern** (ví dụ: `piscina`, `workerpool`) thay vì tạo worker mới cho mỗi task.
- *Tại sao:* Tạo worker mới tốn \~30-50ms + memory overhead. Pool reuse workers, queue tasks, và limit concurrency.
- **Truyền data qua `SharedArrayBuffer` hoặc transferable objects** cho large datasets.
- *Tại sao:* `postMessage()` mặc định clone data (structured clone), tốn CPU + memory. `SharedArrayBuffer` cho zero-copy sharing, transferable objects cho ownership transfer không clone.

**Không nên làm:**

- ❌ Dùng worker threads cho I/O tasks (DB queries, HTTP calls) — Node.js đã async I/O, thêm thread không nhanh hơn mà tốn overhead.
- ❌ Tạo worker mỗi request — overhead tạo thread + V8 isolate quá lớn.
- ❌ Share complex objects qua `SharedArrayBuffer` mà không có synchronization (Atomics) — race condition.

### 2.3 Memory Profiling & Optimization

**Nên làm:**

- **Monitor memory usage trong production** bằng `process.memoryUsage()` và expose qua metrics endpoint.
- `heapUsed`: memory thực tế đang dùng
- `heapTotal`: memory đã allocate
- `rss`: total physical memory (bao gồm C++ objects, stack, code)
- `external`: memory cho C++ objects bound to JS (Buffers)
- **Set `--max-old-space-size` phù hợp với container memory limit.**
- Rule of thumb: `max-old-space-size` = 75% container memory limit (để dành cho stack, native code, OS).
- Ví dụ: container 512MB → `--max-old-space-size=384`
- **Dùng heap snapshots và `--inspect` để debug memory leaks trong development.**
- Chrome DevTools: `node --inspect dist/main.js` → chrome://inspect
- Tham khảo: [Node.js Diagnostics Guide](https://nodejs.org/docs/latest/api/diagnostics_channel.html)
- **Tránh memory leaks phổ biến:**
- Global arrays/maps chỉ grow không bao giờ shrink → dùng LRU cache có max size
- Event listeners không remove → luôn cleanup trong `OnModuleDestroy`
- Closures giữ reference đến large objects → nullify references khi không cần

**Không nên làm:**

- ❌ Gọi `global.gc()` manually trong production — V8 GC tự optimize tốt hơn. Chỉ dùng `--expose-gc` khi profiling.
- ❌ Ignore `process.on('warning')` events — Node.js emit warning khi detect potential memory leak (too many listeners, buffer size).
- ❌ Load toàn bộ large dataset vào memory — dùng Streams (xem nhóm “Streams & File Handling”).

### 2.4 Graceful Shutdown

**Nên làm:**

- **Implement graceful shutdown handler trong NestJS:**

1. Bật `enableShutdownHooks()` trong `main.ts`
2. Implement `OnModuleDestroy` / `OnApplicationShutdown` trong services cần cleanup
3. Close DB connections, flush logs, finish in-progress jobs, deregister from service discovery

- *Tại sao:* `SIGTERM` (từ K8s, Docker, PM2) yêu cầu app tắt. Nếu không handle → connections bị cut đột ngột → requests fail, data inconsistent.
- Tham khảo: [NestJS Application Shutdown](https://docs.nestjs.com/fundamentals/lifecycle-events#application-shutdown)
- **Set timeout cho shutdown process** — nếu cleanup quá lâu, force exit.
- K8s `terminationGracePeriodSeconds` mặc định 30s. App nên shutdown trong 25s, để 5s buffer.
- **Stop accepting new requests trước khi bắt đầu cleanup.**
- `server.close()` ngừng nhận connection mới nhưng vẫn finish requests đang xử lý.
- **Health check endpoint trả unhealthy ngay khi nhận SIGTERM** — load balancer ngừng route traffic.

**Không nên làm:**

- ❌ `process.exit(0)` ngay khi nhận SIGTERM — skip tất cả cleanup, pending requests mất.
- ❌ Shutdown không có timeout — stuck cleanup = container bị SIGKILL (mất data).
- ❌ Thêm `process.on('SIGTERM')` cạnh `enableShutdownHooks()` — Nest gửi lại signal để thoát, listener thừa bắt signal đó: handler chạy hai lần, process có thể không thoát.
- ❌ Quên close background jobs (BullMQ workers, cron jobs) — job chạy dở bị kill, retry lại từ đầu.

### 2.5 Event Loop & Performance Best Practices

**Nên làm:**

- **Monitor event loop lag** bằng `monitorEventLoopDelay()` (Node.js perf\_hooks) và expose metric.
- Event loop delay > 100ms = có CPU-intensive code blocking event loop.
- **Dùng `setImmediate()` để break up long-running synchronous loops.**
- *Tại sao:* Cho event loop cơ hội xử lý I/O callbacks và incoming requests giữa các iterations.
- **Optimize JSON serialization cho large responses:**
- Dùng `fast-json-stringify` cho known schemas (2-5x nhanh hơn `JSON.stringify`).
- Stream large JSON arrays thay vì serialize toàn bộ vào memory.

**Không nên làm:**

- ❌ Synchronous file I/O (`fs.readFileSync`) trong request handler — block event loop cho tất cả concurrent requests.
- ❌ `JSON.parse()` / `JSON.stringify()` cho payloads > 1MB trong hot paths — tốn CPU, có thể gây event loop lag.
- ❌ Regex phức tạp trên user input không giới hạn length — ReDoS vulnerability + CPU spike.

---

### 2.6 Response Compression

**Nên làm:**

- **Bật `compression()` middleware trong production** — gzip/brotli giảm 70-90% response size, cải thiện đáng kể page load và bandwidth.
- *Tại sao:* API responses (JSON) thường có tỉ lệ compression rất cao. Response 100KB có thể giảm xuống 10-30KB sau compression.
- Tham khảo: [NestJS Compression](https://docs.nestjs.com/techniques/compression)

```ts
import * as compression from 'compression';

async function bootstrap() {
  const app = await NestFactory.create(AppModule);
  app.use(compression());  // Gzip/brotli tự động ✅
  await app.listen(3000);
}
```

**Không nên làm:**

- ❌ Bỏ qua compression cho API responses — tốn bandwidth, chậm page load.
- ❌ Compress responses nhỏ (\< 1KB) — overhead compression lớn hơn lợi ích.

---

### 2.7 Lazy Loading Modules

**Nên làm:**

- **Lazy load modules ít dùng** (admin panels, analytics dashboards, report generators) — giảm startup time và memory usage.
- *Tại sao:* Tất cả modules load khi startup, lãng phí memory cho features ít dùng. Lazy loading defer initialization đến khi cần.
- **Giữ eager load cho critical modules**: Authentication, core API routes, public endpoints.

**Không nên làm:**

- ❌ Lazy load authentication/authorization modules — cần sẵn sàng ngay từ đầu.
- ❌ Lazy load modules được truy cập thường xuyên — first-request latency spike.

**Đo lường trước khi optimize:** Profile startup time và memory usage trước, chỉ lazy load modules thực sự ảnh hưởng.

> **Tham khảo:** [NestJS Lazy Loading Modules](https://docs.nestjs.com/fundamentals/lazy-loading-modules)

---

## 3. Ví dụ minh họa thực tế

### 3.1 Cluster Mode với NestJS

```ts
// cluster.service.ts — Cluster wrapper cho NestJS
import * as cluster from 'node:cluster';
import * as os from 'node:os';
import { Injectable, Logger } from '@nestjs/common';

@Injectable()
export class ClusterService {
  private static readonly logger = new Logger(ClusterService.name);

  static clusterize(callback: () => Promise<void>): void {
    const numCPUs = os.availableParallelism?.() ?? os.cpus().length;

    if (cluster.isPrimary) {
      this.logger.log(`Primary process ${process.pid} — forking ${numCPUs} workers`);

      for (let i = 0; i < numCPUs; i++) {
        cluster.fork();
      }

      cluster.on('exit', (worker, code, signal) => {
        this.logger.warn(
          `Worker ${worker.process.pid} exited (code=${code}, signal=${signal}). Restarting...`,
        );
        cluster.fork(); // Auto-restart crashed workers
      });
    } else {
      callback();
    }
  }
}
```

```ts
// main.ts — sử dụng cluster
import { ClusterService } from './cluster.service';
import { NestFactory } from '@nestjs/core';
import { AppModule } from './app.module';

// Option A: Cluster mode (bare metal / VM)
ClusterService.clusterize(async () => {
  const app = await NestFactory.create(AppModule);
  app.enableShutdownHooks();
  await app.listen(3000);
});

// Option B: Single process (Docker/K8s — let orchestrator scale)
// async function bootstrap() {
//   const app = await NestFactory.create(AppModule);
//   app.enableShutdownHooks();
//   await app.listen(3000);
// }
// bootstrap();
```

### 3.2 Worker Thread Pool cho CPU-intensive task

```ts
// image-processing.worker.ts — Piscina worker: export a handler, Piscina calls it once per task
import sharp from 'sharp';

export interface ResizeTask {
  input: Uint8Array; // a Buffer arrives here as a plain Uint8Array (structured clone)
  width: number;
  height: number;
  format: 'webp' | 'jpeg' | 'png';
}

export default async function resize({ input, width, height, format }: ResizeTask): Promise<Buffer> {
  // Copied back to the main thread (sharp's output buffer is not transferable), arrives as a Uint8Array
  return sharp(input).resize(width, height).toFormat(format).toBuffer();
}
```

```ts
// image-processing.service.ts — Service dùng Piscina pool
import { Injectable, OnModuleDestroy } from '@nestjs/common';
import Piscina from 'piscina';
import { join } from 'node:path';
import type { ResizeTask } from './image-processing.worker';

@Injectable()
export class ImageProcessingService implements OnModuleDestroy {
  private readonly pool: Piscina<ResizeTask, Uint8Array>;

  constructor() {
    this.pool = new Piscina({
      filename: join(__dirname, 'image-processing.worker.js'),
      maxThreads: 4,    // Limit threads — không quá số CPU cores
      idleTimeout: 30_000, // Cleanup idle workers sau 30s
    });
  }

  async resizeImage(
    buffer: Buffer,
    width: number,
    height: number,
    format: ResizeTask['format'] = 'webp',
  ): Promise<Buffer> {
    const output = await this.pool.run({ input: buffer, width, height, format });
    return Buffer.from(output.buffer, output.byteOffset, output.byteLength); // Wrap without copying
  }

  // Cleanup pool khi app shutdown
  async onModuleDestroy() {
    await this.pool.destroy();
  }
}
```

### 3.3 Graceful Shutdown — Full Implementation

```ts
// main.ts
import { NestFactory } from '@nestjs/core';
import { AppModule } from './app.module';

async function bootstrap() {
  const app = await NestFactory.create(AppModule);

  // Single shutdown mechanism: on SIGTERM (K8s, Docker) or SIGINT (PM2), Nest runs
  // onModuleDestroy → beforeApplicationShutdown → closes HTTP server → onApplicationShutdown.
  // Do not add process.on('SIGTERM'): Nest re-sends the signal to exit, an extra listener swallows it.
  // SIGUSR2 is left out so --heapsnapshot-signal=SIGUSR2 (section 4.1) does not stop the app.
  app.enableShutdownHooks(['SIGTERM', 'SIGINT']);

  await app.listen(3000);
}
bootstrap();
```

```ts
// shutdown-timeout.service.ts — force exit if cleanup hangs
import { Injectable, Logger, OnApplicationShutdown, OnModuleDestroy } from '@nestjs/common';

// Force exit after 25s (K8s default terminationGracePeriodSeconds = 30s)
const SHUTDOWN_TIMEOUT = 25_000;

@Injectable()
export class ShutdownTimeoutService implements OnModuleDestroy, OnApplicationShutdown {
  private readonly logger = new Logger(ShutdownTimeoutService.name);
  private timer?: NodeJS.Timeout;

  // Registered in AppModule: Nest calls its hooks before those of imported modules
  onModuleDestroy() {
    this.timer = setTimeout(() => {
      this.logger.error('Graceful shutdown timed out, forcing exit');
      process.exit(1);
    }, SHUTDOWN_TIMEOUT).unref();
  }

  // app.close() without a signal (e.g. e2e tests): the process keeps running, so cancel the timer
  onApplicationShutdown(signal?: string) {
    if (!signal) clearTimeout(this.timer);
  }
}
```

```ts
// health.controller.ts — Health check aware of shutdown
import { Controller, Get, OnModuleDestroy, VERSION_NEUTRAL } from '@nestjs/common';
import {
  HealthCheck,
  HealthCheckService,
  TypeOrmHealthIndicator,
} from '@nestjs/terminus';

@Controller({ path: 'health', version: VERSION_NEUTRAL }) // Probes call /health, outside /v1
export class HealthController implements OnModuleDestroy {
  private isShuttingDown = false;

  constructor(
    private health: HealthCheckService,
    private db: TypeOrmHealthIndicator, // Prisma: PrismaHealthIndicator, see 7.3 section 3.1
  ) {}

  // First shutdown hook, while the HTTP server still accepts requests.
  // Registered in AppModule so it runs before imported modules start their cleanup.
  onModuleDestroy() {
    this.isShuttingDown = true;
  }

  // Liveness: answers while the process runs; no dependency checks, so a DB outage never restarts the pod
  @Get('liveness')
  @HealthCheck()
  liveness() {
    return this.health.check([
      () => ({ app: { status: 'up' } }),
    ]);
  }

  // Readiness fails during shutdown so the load balancer stops sending traffic; liveness stays up
  @Get('readiness')
  @HealthCheck()
  readiness() {
    if (this.isShuttingDown) {
      throw new Error('Service is shutting down');
    }
    return this.health.check([
      () => this.db.pingCheck('database', { timeout: 3000 }),
    ]);
  }
}
```

```ts
// app.module.ts — register both in AppModule: Nest runs AppModule hooks first on shutdown
import { Module } from '@nestjs/common';
import { TerminusModule } from '@nestjs/terminus';
import { HealthController } from './health.controller';
import { ShutdownTimeoutService } from './shutdown-timeout.service';

@Module({
  imports: [TerminusModule /* , TypeOrmModule.forRoot(...), feature modules */],
  controllers: [HealthController],
  providers: [ShutdownTimeoutService],
})
export class AppModule {}
```

```ts
// queue-processor.service.ts — Cleanup background jobs
import { Injectable, OnModuleDestroy, Logger } from '@nestjs/common';
import { Queue, Worker } from 'bullmq';

@Injectable()
export class QueueProcessorService implements OnModuleDestroy {
  private readonly logger = new Logger(QueueProcessorService.name);
  private worker: Worker;

  // Graceful: close worker — finish current job, stop picking new ones
  async onModuleDestroy() {
    this.logger.log('Closing queue worker...');
    await this.worker.close(); // Waits for current job to finish
    this.logger.log('Queue worker closed');
  }
}
```

### 3.4 Memory Monitoring Service

```ts
// memory-monitor.service.ts
import { Injectable, Logger } from '@nestjs/common';
import { Cron, CronExpression } from '@nestjs/schedule';
import { getHeapStatistics } from 'node:v8';

@Injectable()
export class MemoryMonitorService {
  private readonly logger = new Logger(MemoryMonitorService.name);
  private readonly HEAP_THRESHOLD = 0.85; // Warn khi heap usage > 85%

  @Cron(CronExpression.EVERY_30_SECONDS)
  checkMemory() {
    const usage = process.memoryUsage();
    // Compare with the V8 heap limit (--max-old-space-size), not heapTotal:
    // heapTotal grows on demand, so heapUsed / heapTotal passes 85% long before the limit
    const heapLimit = getHeapStatistics().heap_size_limit;
    const heapRatio = usage.heapUsed / heapLimit;

    // Structured log cho monitoring system parse
    this.logger.log({
      message: 'Memory usage',
      heapUsedMB: Math.round(usage.heapUsed / 1024 / 1024),
      heapTotalMB: Math.round(usage.heapTotal / 1024 / 1024),
      heapLimitMB: Math.round(heapLimit / 1024 / 1024),
      rssMB: Math.round(usage.rss / 1024 / 1024),
      externalMB: Math.round(usage.external / 1024 / 1024),
      heapRatio: heapRatio.toFixed(2),
    });

    if (heapRatio > this.HEAP_THRESHOLD) {
      this.logger.warn(
        `Heap usage ${(heapRatio * 100).toFixed(0)}% exceeds threshold ${this.HEAP_THRESHOLD * 100}%`,
      );
    }
  }
}
```

### 3.5 Event Loop Monitoring

```ts
// event-loop-monitor.service.ts
import { Injectable, Logger, OnModuleInit, OnModuleDestroy } from '@nestjs/common';
import { monitorEventLoopDelay, IntervalHistogram } from 'node:perf_hooks';

@Injectable()
export class EventLoopMonitorService implements OnModuleInit, OnModuleDestroy {
  private readonly logger = new Logger(EventLoopMonitorService.name);
  private histogram: IntervalHistogram;
  private interval: NodeJS.Timeout;

  onModuleInit() {
    this.histogram = monitorEventLoopDelay({ resolution: 20 });
    this.histogram.enable();

    this.interval = setInterval(() => {
      const p99 = this.histogram.percentile(99) / 1e6; // ns → ms
      const max = this.histogram.max / 1e6;
      const mean = this.histogram.mean / 1e6;

      this.logger.log({
        message: 'Event loop delay',
        meanMs: mean.toFixed(2),
        p99Ms: p99.toFixed(2),
        maxMs: max.toFixed(2),
      });

      if (p99 > 100) {
        this.logger.warn(`Event loop p99 delay ${p99.toFixed(0)}ms > 100ms threshold`);
      }

      this.histogram.reset();
    }, 10_000);
  }

  onModuleDestroy() {
    clearInterval(this.interval);
    this.histogram.disable();
  }
}
```

---

## 4. Tooling & Config

### 4.1 Node.js Flags cho Performance

```bash
# Production — optimize V8, set memory limit phù hợp container
node --max-old-space-size=384 --optimize-for-size dist/main.js

# Development — profiling
node --inspect --max-old-space-size=512 dist/main.js

# Heap snapshot near OOM (memory leak debugging): written when the heap nears the limit, at most 1
node --heapsnapshot-near-heap-limit=1 --max-old-space-size=384 dist/main.js

# Heap snapshot on demand (does not fire on OOM). Needs enableShutdownHooks(['SIGTERM', 'SIGINT']):
# the no-arg form also handles SIGUSR2 and shuts the app down (section 3.3)
node --heapsnapshot-signal=SIGUSR2 --max-old-space-size=384 dist/main.js
# Gửi SIGUSR2 → Node.js tạo .heapsnapshot file → mở trong Chrome DevTools
```

### 4.2 Dockerfile — Resource-Aware

```docker
FROM node:22-alpine AS production

WORKDIR /app
COPY --from=builder /app/dist ./dist
COPY --from=builder /app/node_modules ./node_modules
COPY --from=builder /app/package.json ./

# Set memory limit = 75% container limit
# Container 512MB → max-old-space-size=384
ENV NODE_OPTIONS="--max-old-space-size=384"

# Non-root user; LoggerModule writes to /app/logs (Logging 7.1, section 3.2)
RUN mkdir logs && chown node:node logs
USER node

# Health check
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD wget -qO- http://localhost:3000/health/liveness || exit 1

CMD ["node", "dist/main.js"]
```

### 4.3 PM2 — Cluster Management (non-container)

```js
// ecosystem.config.js
module.exports = {
  "apps": [{
    "name": "nestjs-app",
    "script": "dist/main.js",
    "instances": "max",
    "exec_mode": "cluster",
    "max_memory_restart": "400M",
    "node_args": "--max-old-space-size=384",
    "env_production": {
      "NODE_ENV": "production"
    },
    // PM2 sends SIGINT (Nest shutdown hooks run), then SIGKILL after kill_timeout.
    // No "shutdown_with_message": it replaces SIGINT with a 'shutdown' message, so Nest hooks never run.
    "kill_timeout": 25000,
    "listen_timeout": 10000
  }]
};
```

### 4.4 Kubernetes Deployment — Resource Limits

```yaml
# deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: nestjs-app
spec:
  selector:
    matchLabels:
      app: nestjs-app # Required by apps/v1, must match the template labels
  template:
    metadata:
      labels:
        app: nestjs-app
    spec:
      terminationGracePeriodSeconds: 30
      containers:
        - name: nestjs-app
          image: ghcr.io/org/app:a1b2c3d
          resources:
            requests:
              memory: "256Mi"
              cpu: "250m"
            limits:
              memory: "512Mi"
              cpu: "1000m"
          livenessProbe:
            httpGet:
              path: /health/liveness
              port: 3000
            initialDelaySeconds: 10
            periodSeconds: 15
          readinessProbe:
            httpGet:
              path: /health/readiness
              port: 3000
            initialDelaySeconds: 5
            periodSeconds: 5
          lifecycle:
            preStop:
              exec:
                command: ["sh", "-c", "sleep 5"] # Wait for LB to deregister
```

### 4.5 Packages khuyến nghị

| Package | Mục đích | Ghi chú |
| --- | --- | --- |
| `piscina` | Worker thread pool | Maintained by Node.js team, zero dependencies |
| `@nestjs/terminus` | Health checks | Tích hợp DB, Redis, disk, memory health indicators |
| `@nestjs/schedule` | Cron jobs / intervals | Dùng cho memory monitoring scheduled tasks |
| `clinic.js` | Performance profiling suite | Doctor (event loop), Bubbleprof (async), Flame (CPU) |
| `0x` | Flamegraph generation | Lightweight alternative to clinic flame |
| `fast-json-stringify` | Fast JSON serialization | 2-5x faster khi schema known |

---

## References

- [Node.js Cluster documentation](https://nodejs.org/docs/latest/api/cluster.html)
- [Node.js Worker Threads documentation](https://nodejs.org/docs/latest/api/worker_threads.html)
- [Node.js Performance Hooks (perf\_hooks)](https://nodejs.org/docs/latest/api/perf_hooks.html)
- [Node.js Process documentation](https://nodejs.org/docs/latest/api/process.html)
- [Node.js OS module](https://nodejs.org/docs/latest/api/os.html)
- [NestJS Lifecycle Events & Shutdown Hooks](https://docs.nestjs.com/fundamentals/lifecycle-events)
- [NestJS Health Checks (Terminus)](https://docs.nestjs.com/recipes/terminus)
- [Piscina — Worker Thread Pool](https://github.com/piscinajs/piscina)
- [Clinic.js — Node.js Performance Profiling](https://clinicjs.org/)
- [V8 Memory Management & GC](https://v8.dev/blog/trash-talk)

## Changelog

| Date | Version | Change | By |
| :---- | :---- | :---- | :---- |
| 2026-11-18 | v1.0 | Chuyển từ Notion "NestJS Document" (page `33d71a38d3b2816593bbce944fb85313`, sửa 2026-04-09). Review và sửa nội dung, code trước khi publish. Owner duyệt trong chat ngày 2026-11-18. | Bắc PV |
