# NestJS Coding Standard 6.1 — Task Scheduling & Queues

| Field | Value |
| :---- | :---- |
| Owner | Bắc PV — NodeJS BE Dev Lead |
| Audience | Dev (NodeJS BE) |
| Last reviewed | 2026-11-12 |
| Review cadence | Quarterly |
| Version | v1.0 |
| Linked from | Ref_Dev_nestjs-coding-standard_v1.0 |
| Status | Live |

Doc này là mục 6.1 của [NestJS Coding Standard](Ref_Dev_nestjs-coding-standard_v1.0.md), nhóm Async & Integration. Doc nêu quy tắc về Task Scheduling & Queues trong dự án NestJS, kèm lý do, ví dụ và config. Dev NodeJS BE đọc doc này khi viết code, review code và onboarding.

---

## 1. Tóm tắt & Phạm vi

Task Scheduling & Queues giải quyết bài toán **thực thi tác vụ không đồng bộ**. Đó là những công việc không cần (hoặc không nên) chạy trong request lifecycle của HTTP:

- **Task Scheduling** (`@nestjs/schedule`): Chạy tác vụ theo lịch cố định (cron), theo interval, hoặc sau một khoảng delay. Phù hợp cho: cleanup data cũ, gửi báo cáo định kỳ, sync dữ liệu, health check.
- **Queues** (`@nestjs/bullmq` + Redis): Đưa tác vụ vào hàng đợi để xử lý bất đồng bộ bởi worker riêng biệt. Phù hợp cho: gửi email/notification, xử lý file/ảnh, gọi third-party API nặng, batch processing.

**Tại sao quan trọng?**

- Giữ response time thấp — không block user request bởi tác vụ nặng
- Đảm bảo reliability — job thất bại có thể retry tự động
- Scalability — worker có thể scale độc lập với API server
- Observability — theo dõi trạng thái job, detect bottleneck

**Scope áp dụng:** Mọi dự án NestJS cần xử lý background tasks, scheduled jobs, hoặc async processing.

---

## 2. Quy tắc & Giải thích

### 2.1 Task Scheduling (`@nestjs/schedule`)

> 📘 Tài liệu chính thống: [NestJS Task Scheduling](https://docs.nestjs.com/techniques/task-scheduling) · [node-cron expressions](https://github.com/kelektiv/node-cron)

### 2.2 Nên làm

- **Đăng ký `ScheduleModule.forRoot()` ở `AppModule`** — bắt buộc để kích hoạt tất cả decorators (`@Cron`, `@Interval`, `@Timeout`)
- *Tại sao:* Module này scan toàn bộ providers để tìm và đăng ký scheduled tasks. Thiếu nó thì decorators bị bỏ qua im lặng.
- **Tách scheduled tasks vào service riêng** (ví dụ `tasks.service.ts`) — không đặt trong controller hoặc trộn với business service
- *Tại sao:* Dễ quản lý, test, và monitor. Controller chỉ xử lý HTTP, service chỉ chứa business logic.
- **Dùng `CronExpression` enum** thay vì hardcode cron string khi có sẵn
- *Tại sao:* Tự document, giảm lỗi typo. `CronExpression.EVERY_DAY_AT_MIDNIGHT` rõ ràng hơn `'0 0 * * *'`.
- **Dùng cron name cho dynamic management** — `@Cron('expression', { name: 'taskName' })` để có thể stop/start/modify runtime
- *Tại sao:* `SchedulerRegistry` cần name để lookup. Không có name thì không thể control dynamically.
- **Wrap logic trong try/catch** — scheduled task throw error sẽ fail silently
- *Tại sao:* Không có global exception filter cho cron jobs (khác với HTTP request). Unhandled error chỉ log ra console, dễ bỏ sót.
- **Log mỗi lần task chạy** — ít nhất log start + duration + result
- *Tại sao:* Scheduled tasks chạy ngầm, không có request log. Thiếu log thì không biết task có chạy đúng không.

### 2.3 Không nên làm

- **Không chạy heavy logic trực tiếp trong cron handler** — delegate sang queue nếu task mất > vài giây
- *Tại sao:* Cron handler chạy trên main event loop. Task nặng block event loop → ảnh hưởng toàn bộ API requests.
- **Không dùng `@Interval` cho production critical tasks** — interval bị reset khi app restart, không persist
- *Tại sao:* `@Interval` chỉ là `setInterval` wrapper, không có persistence hay distributed lock.
- **Không quên distributed lock khi chạy multi-instance** — 3 instances = cron chạy 3 lần
- *Tại sao:* `@nestjs/schedule` không có built-in distributed locking. Cần dùng Redis lock (Redlock) hoặc database-level lock.

### 2.2 Queues (`@nestjs/bullmq`)

> 📘 Tài liệu chính thống: [NestJS Queues](https://docs.nestjs.com/techniques/queues) · [BullMQ Guide](https://docs.bullmq.io/guide/introduction)

### 2.3 Nên làm

- **Tách producer (enqueue) và consumer (process) rõ ràng** — producer ở feature service, consumer ở dedicated processor class
- *Tại sao:* Single Responsibility. Producer chỉ cần biết queue name + job data. Consumer handle logic xử lý + retry + error.
- **Type-safe job data** — define interface cho mỗi job type, dùng generic khi add/process
- *Tại sao:* Tránh runtime error do sai structure. TypeScript bắt lỗi tại compile time.
- **Luôn cấu hình retry strategy** — `attempts` + `backoff` (exponential) cho mọi job
- *Tại sao:* Network flaky, external API timeout — retry tự động giải quyết transient failures mà không cần manual intervention.
- **Set `removeOnComplete` và `removeOnFail`** — tránh Redis memory leak
- *Tại sao:* BullMQ mặc định giữ tất cả completed/failed jobs trong Redis. Production chạy lâu → Redis OOM.
- **Dùng `jobId` cho idempotent jobs** — tránh duplicate khi enqueue lại
- *Tại sao:* Nếu enqueue trong retry logic hoặc webhook handler, cùng một event có thể trigger nhiều lần.
- **Graceful shutdown** — gọi `app.enableShutdownHooks()` để `@nestjs/bullmq` gọi `worker.close()` khi nhận SIGTERM; `worker.close()` đợi job đang `active` chạy xong. Không gọi `queue.drain()`: lệnh này xoá job `waiting` (cả `delayed` nếu truyền `true`)
- *Tại sao:* Job của worker bị kill nằm ở `active` đến khi stalled check (mỗi `stalledInterval`, mặc định 30s) đưa về `wait` và chạy lại từ đầu. Bị kill quá `maxStalledCount` (mặc định 1) lần thì job thành `failed`, dù còn `attempts`.
- **Monitor bằng Bull Board hoặc tương đương** — dashboard real-time cho job status
- *Tại sao:* Queue là black box nếu không có monitoring. Cần biết: bao nhiêu pending, bao nhiêu failed, processing time.

### 2.4 Không nên làm

- **Không đặt business logic nặng trong producer** — producer chỉ validate + enqueue
- *Tại sao:* Producer chạy trong request context. Logic nặng ở đây thì queue mất ý nghĩa.
- **Không dùng `concurrency` quá cao** mà không hiểu bottleneck
- *Tại sao:* `concurrency: 100` nhưng DB connection pool chỉ có 10 → connection exhaustion → crash.
- **Không bỏ qua failed jobs** — implement Dead Letter Queue (DLQ) hoặc alert
- *Tại sao:* Failed job = mất data hoặc user không nhận được email/notification. Cần mechanism để review và re-process.
- **Không gọi external API với concurrency cao** — dùng rate limiter của BullMQ
- *Tại sao:* Third-party API có rate limit. Vượt limit → bị block → tất cả jobs fail.
- **Không share Redis instance giữa cache và queue trong production** — tách riêng
- *Tại sao:* Queue operations (blocking pop, pub/sub) ảnh hưởng cache performance. Redis OOM từ queue data xóa luôn cache.

---

## 3. Ví dụ minh họa thực tế

### 3.1 Scheduled Task: Cleanup expired sessions

**Bài toán:** Mỗi ngày lúc 2:00 AM, xóa sessions đã hết hạn khỏi database.

```ts
// src/modules/tasks/tasks.module.ts
import { Module } from '@nestjs/common';
import { ScheduleModule } from '@nestjs/schedule';
import { SessionCleanupService } from './session-cleanup.service';

@Module({
  imports: [ScheduleModule.forRoot()],
  providers: [SessionCleanupService],
})
export class TasksModule {}
```

```ts
// src/modules/tasks/session-cleanup.service.ts
import { Injectable, Logger } from '@nestjs/common';
import { Cron, CronExpression } from '@nestjs/schedule';
import { SessionsRepository } from '../sessions/sessions.repository';

@Injectable()
export class SessionCleanupService {
  private readonly logger = new Logger(SessionCleanupService.name);

  constructor(private readonly sessionsRepo: SessionsRepository) {}

  @Cron(CronExpression.EVERY_DAY_AT_2AM, { name: 'session-cleanup' })
  async handleSessionCleanup(): Promise<void> {
    const start = Date.now();
    this.logger.log('Starting expired session cleanup...');

    try {
      const deletedCount = await this.sessionsRepo.deleteExpired();
      const duration = Date.now() - start;
      this.logger.log(
        `Session cleanup completed: ${deletedCount} sessions removed in ${duration}ms`,
      );
    } catch (error) {
      this.logger.error('Session cleanup failed', error instanceof Error ? error.stack : error);
      // Có thể emit event hoặc gửi alert
    }
  }
}
```

**Giải thích:**

- `name: 'session-cleanup'` — cho phép quản lý dynamic qua `SchedulerRegistry`
- try/catch bắt mọi error — cron không có exception filter
- Log start + result + duration — cần cho monitoring và debugging

### 3.2 Dynamic Cron: User-defined scheduled reports

```ts
// Tạo/stop cron job động dựa trên user input
import { Injectable } from '@nestjs/common';
import { SchedulerRegistry } from '@nestjs/schedule';
import { CronJob } from 'cron';

@Injectable()
export class ReportSchedulerService {
  constructor(
    private readonly schedulerRegistry: SchedulerRegistry,
    private readonly reportsService: ReportsService,
  ) {}

  scheduleReport(userId: string, cronExpression: string): void {
    const jobName = `report-${userId}`;

    // Xóa job cũ nếu tồn tại
    if (this.schedulerRegistry.doesExist('cron', jobName)) {
      this.schedulerRegistry.deleteCronJob(jobName);
    }

    const job = new CronJob(cronExpression, () => {
      this.reportsService.generateAndSend(userId).catch((err) => {
        this.logger.error(`Report generation failed for user ${userId}`, err.stack);
      });
    });

    this.schedulerRegistry.addCronJob(jobName, job);
    job.start();
  }

  stopReport(userId: string): void {
    const jobName = `report-${userId}`;
    this.schedulerRegistry.deleteCronJob(jobName);
  }
}
```

### 3.3 Queue: Welcome email sau signup

**Bài toán:** User đăng ký → enqueue welcome email → worker gửi email bất đồng bộ.

```ts
// src/modules/mail/interfaces/mail-job.interface.ts
export interface WelcomeEmailJobData {
  userId: string;
  email: string;
  name: string;
}

export interface PasswordResetJobData {
  email: string;
  resetToken: string;
  expiresAt: string;
}

export type MailJobData = WelcomeEmailJobData | PasswordResetJobData;
```

```ts
// src/modules/mail/mail.module.ts
import { Module } from '@nestjs/common';
import { BullModule } from '@nestjs/bullmq';
import { MailService } from './mail.service';
import { MailProcessor } from './mail.processor';
import { MAIL_QUEUE } from './mail.constants';

@Module({
  imports: [
    BullModule.registerQueue({
      name: MAIL_QUEUE,
      defaultJobOptions: {
        attempts: 3,
        backoff: { type: 'exponential', delay: 2000 },
        removeOnComplete: { count: 1000 },  // Giữ 1000 completed jobs gần nhất
        removeOnFail: { age: 7 * 24 * 3600 }, // Giữ failed jobs 7 ngày
      },
    }),
  ],
  providers: [MailService, MailProcessor],
  exports: [MailService],
})
export class MailModule {}
```

```ts
// src/modules/mail/mail.constants.ts
export const MAIL_QUEUE = 'mail';

export enum MailJobName {
  WELCOME_EMAIL = 'welcome-email',
  PASSWORD_RESET = 'password-reset',
}
```

```ts
// src/modules/mail/mail.service.ts — Producer
import { Injectable } from '@nestjs/common';
import { InjectQueue } from '@nestjs/bullmq';
import { Queue } from 'bullmq';
import { MAIL_QUEUE, MailJobName } from './mail.constants';
import { WelcomeEmailJobData } from './interfaces/mail-job.interface';

@Injectable()
export class MailService {
  constructor(
    @InjectQueue(MAIL_QUEUE) private readonly mailQueue: Queue,
  ) {}

  async sendWelcomeEmail(data: WelcomeEmailJobData): Promise<void> {
    await this.mailQueue.add(
      MailJobName.WELCOME_EMAIL,
      data,
      {
        jobId: `welcome-${data.userId}`, // Idempotent — không gửi duplicate
        delay: 5000, // Delay 5s — tránh gửi nếu user delete account ngay
      },
    );
  }
}
```

```ts
// src/modules/mail/mail.processor.ts — Consumer
import { Processor, WorkerHost, OnWorkerEvent } from '@nestjs/bullmq';
import { Logger } from '@nestjs/common';
import { Job } from 'bullmq';
import { MAIL_QUEUE, MailJobName } from './mail.constants';
import { WelcomeEmailJobData } from './interfaces/mail-job.interface';

@Processor(MAIL_QUEUE)
export class MailProcessor extends WorkerHost {
  private readonly logger = new Logger(MailProcessor.name);

  async process(job: Job<WelcomeEmailJobData>): Promise<void> {
    this.logger.log(`Processing ${job.name} [${job.id}]`);

    switch (job.name) {
      case MailJobName.WELCOME_EMAIL:
        await this.handleWelcomeEmail(job.data);
        break;
      default:
        this.logger.warn(`Unknown job name: ${job.name}`);
    }
  }

  private async handleWelcomeEmail(data: WelcomeEmailJobData): Promise<void> {
    // Gọi email provider (SendGrid, SES, etc.)
    await this.emailProvider.send({
      to: data.email,
      subject: `Chào mừng ${data.name}!`,
      template: 'welcome',
      context: { name: data.name },
    });
  }

  @OnWorkerEvent('failed')
  onFailed(job: Job, error: Error): void {
    this.logger.error(
      `Job ${job.name} [${job.id}] failed after ${job.attemptsMade} attempts: ${error.message}`,
      error.stack,
    );
  }

  @OnWorkerEvent('completed')
  onCompleted(job: Job): void {
    this.logger.log(`Job ${job.name} [${job.id}] completed`);
  }
}
```

**Giải thích từng bước:**

1. **Interface typed** — `WelcomeEmailJobData` đảm bảo producer và consumer agree trên data shape
2. **`defaultJobOptions`** — `attempts: 3` là tối đa 3 lần chạy (1 lần đầu + 2 lần retry), exponential backoff 2s → 4s
3. **`removeOnComplete/Fail`** — tự dọn Redis, tránh memory leak
4. **`jobId: welcome-${userId}`** — idempotent, enqueue lại cùng userId không tạo duplicate
5. **`WorkerHost` pattern** — recommended bởi NestJS docs, tích hợp tốt với DI
6. **Event listeners** — `@OnWorkerEvent` cho logging và alerting

### 3.4 Advanced: Distributed cron lock với Redis

```ts
// src/common/decorators/distributed-cron.decorator.ts
import { randomUUID } from 'node:crypto';
import { Cron } from '@nestjs/schedule';
import { Inject } from '@nestjs/common';
import Redis from 'ioredis';

// Compare-and-delete: remove the lock only if it still holds this run's token
const RELEASE_LOCK_SCRIPT = `
  if redis.call('GET', KEYS[1]) == ARGV[1] then
    return redis.call('DEL', KEYS[1])
  end
  return 0
`;

export function DistributedCron(cronExpression: string, options: { name: string; lockTtlMs?: number }) {
  return function (target: any, propertyKey: string, descriptor: PropertyDescriptor) {
    const originalMethod = descriptor.value;
    const lockTtl = options.lockTtlMs ?? 60_000;

    descriptor.value = async function (this: { redis: Redis }, ...args: any[]) {
      const redis: Redis = this.redis; // Inject Redis vào service
      const lockKey = `cron-lock:${options.name}`;
      // Unique per run; process.pid is 1 in every container, so it cannot identify the owner
      const token = randomUUID();

      // SET NX PX — only one instance acquires the lock
      const acquired = await redis.set(lockKey, token, 'PX', lockTtl, 'NX');
      if (!acquired) return; // Instance khác đã chạy

      try {
        await originalMethod.apply(this, args);
      } finally {
        // If the TTL expired and another instance took the lock, leave its lock alone
        await redis.eval(RELEASE_LOCK_SCRIPT, 1, lockKey, token);
      }
    };

    // Vẫn dùng @Cron decorator bên dưới
    Cron(cronExpression, { name: options.name })(target, propertyKey, descriptor);
    return descriptor;
  };
}
```

```ts
// Sử dụng
@Injectable()
export class ReportService {
  constructor(private readonly redis: Redis) {}

  @DistributedCron(CronExpression.EVERY_HOUR, { name: 'hourly-report', lockTtlMs: 300_000 })
  async generateHourlyReport(): Promise<void> {
    // Chỉ 1 instance trong cluster chạy task này
    await this.buildAndSendReport();
  }
}
```

### 3.5 Dead Letter Queue (DLQ) pattern

```ts
// Khi job fail hết attempts → move sang DLQ để review
@Processor(MAIL_QUEUE)
export class MailProcessor extends WorkerHost {
  constructor(
    @InjectQueue('mail-dlq') private readonly dlqQueue: Queue,
  ) {
    super();
  }

  @OnWorkerEvent('failed')
  async onFailed(job: Job, error: Error): Promise<void> {
    // Chỉ move vào DLQ khi hết tất cả attempts
    if (job.attemptsMade >= (job.opts.attempts ?? 1)) {
      await this.dlqQueue.add('failed-mail', {
        originalJob: { name: job.name, data: job.data, id: job.id },
        error: { message: error.message, stack: error.stack },
        failedAt: new Date().toISOString(),
      });
      this.logger.error(`Job ${job.id} moved to DLQ after ${job.attemptsMade} attempts`);
    }
  }
}
```

---

## 4. Tooling & Config

### 4.1 Packages cần cài

```bash
# Task Scheduling
pnpm add @nestjs/schedule
pnpm add -D @types/cron

# Queues (BullMQ)
pnpm add @nestjs/bullmq bullmq
pnpm add ioredis

# Monitoring (optional)
pnpm add @bull-board/api @bull-board/express @bull-board/nestjs express-basic-auth
```

### 4.2 Redis config cho BullMQ

```ts
// app.module.ts
import { BullModule } from '@nestjs/bullmq';

@Module({
  imports: [
    BullModule.forRootAsync({
      useFactory: (configService: ConfigService) => ({
        connection: {
          host: configService.getOrThrow<string>('REDIS_QUEUE_HOST'),
          port: configService.getOrThrow<number>('REDIS_QUEUE_PORT'),
          password: configService.get<string>('REDIS_QUEUE_PASSWORD'),
          maxRetriesPerRequest: null, // Required cho BullMQ
        },
      }),
      inject: [ConfigService],
    }),
  ],
})
export class AppModule {}
```

### 4.3 Bull Board monitoring setup

```ts
// src/modules/bull-board/bull-board.module.ts
import { Module } from '@nestjs/common';
import { ConfigService } from '@nestjs/config';
import { BullBoardModule } from '@bull-board/nestjs';
import { ExpressAdapter } from '@bull-board/express';
import { BullMQAdapter } from '@bull-board/api/bullMQAdapter';
import basicAuth from 'express-basic-auth';
import { MAIL_QUEUE } from '../mail/mail.constants';

@Module({
  imports: [
    BullBoardModule.forRootAsync({
      inject: [ConfigService],
      useFactory: (config: ConfigService) => ({
        route: '/admin/queues',
        adapter: ExpressAdapter,
        // Bull Board is an Express router, not a Nest controller: guards never run on it.
        // This middleware runs before the router on every board path (UI and API).
        middleware: basicAuth({
          challenge: true,
          users: {
            [config.getOrThrow<string>('BULL_BOARD_USER')]:
              config.getOrThrow<string>('BULL_BOARD_PASSWORD'),
          },
        }),
      }),
    }),
    BullBoardModule.forFeature({ name: MAIL_QUEUE, adapter: BullMQAdapter }),
  ],
})
export class BullBoardSetupModule {}
```

> ⚠️ **Lưu ý:** Bull Board là Express router, Nest guard không chạy trên route này. Bảo vệ bằng option `middleware` như trên, vì dashboard expose toàn bộ job data.

### 4.4 Docker Compose cho Redis (dev)

```yaml
# docker-compose.yml
services:
  redis-queue:
    image: redis:7-alpine
    ports:
      - '6380:6379'  # Port khác với redis-cache
    volumes:
      - redis-queue-data:/data
    command: redis-server --appendonly yes --maxmemory 256mb --maxmemory-policy noeviction

volumes:
  redis-queue-data:
```

> 💡 `maxmemory-policy: noeviction` cho queue Redis — không được tự xóa data khi đầy (khác với cache dùng `allkeys-lru`). Khi đầy → BullMQ báo lỗi → alert → xử lý.

---

## References

- [NestJS — Task Scheduling](https://docs.nestjs.com/techniques/task-scheduling)
- [NestJS — Queues](https://docs.nestjs.com/techniques/queues)
- [BullMQ Documentation](https://docs.bullmq.io/)
- [BullMQ — Parallelism and Concurrency](https://docs.bullmq.io/guide/parallelism-and-concurrency)
- [Bull Board — Queue Monitoring](https://github.com/felixmosh/bull-board)
- [Redlock — Distributed Locks](https://github.com/mike-marcacci/node-redlock)
- [Node.js Event Loop — Timers](https://nodejs.org/en/learn/asynchronous-work/event-loop-timers-and-nexttick)

## Changelog

| Date | Version | Change | By |
| :---- | :---- | :---- | :---- |
| 2026-11-18 | v1.0 | Chuyển từ Notion "NestJS Document" (page `33d71a38d3b281398768d973a41a56d0`, sửa 2026-04-09). Review và sửa nội dung, code trước khi publish. Owner duyệt trong chat ngày 2026-11-18. | Bắc PV |
