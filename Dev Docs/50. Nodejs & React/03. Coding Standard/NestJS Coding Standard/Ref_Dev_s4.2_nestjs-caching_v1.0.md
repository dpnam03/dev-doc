# NestJS Coding Standard 4.2 — Caching

| Field | Value |
| :---- | :---- |
| Owner | Bắc PV — NodeJS BE Dev Lead |
| Audience | Dev (NodeJS BE) |
| Last reviewed | 2026-11-12 |
| Review cadence | Quarterly |
| Version | v1.0 |
| Linked from | Ref_Dev_nestjs-coding-standard_v1.0 |
| Status | Live |

Doc này là mục 4.2 của [NestJS Coding Standard](Ref_Dev_nestjs-coding-standard_v1.0.md), nhóm Database. Doc nêu quy tắc về Caching trong dự án NestJS, kèm lý do, ví dụ và config. Dev NodeJS BE đọc doc này khi viết code, review code và onboarding.

---

## 1. Tóm tắt & Phạm vi

Caching (Bộ nhớ đệm) là kỹ thuật lưu trữ dữ liệu tạm thời để **tăng tốc độ phản hồi** và **giảm tải cho Database/External Services**. Đây là một trong những kỹ thuật tối ưu hiệu năng quan trọng nhất trong backend development.

**Phạm vi áp dụng:**

- API responses thường xuyên được truy vấn (danh sách sản phẩm, cấu hình hệ thống, dữ liệu ít thay đổi)
- Kết quả tính toán phức tạp (aggregation, reports)
- Session data, token blacklists
- Rate limiting counters

**Tại sao quan trọng?**

- Giảm latency từ hàng trăm ms (DB query) xuống \< 2ms (cache hit)
- Giảm tải cho Database — tránh bottleneck khi traffic cao
- Tăng khả năng chịu tải (throughput) của hệ thống
- Giảm chi phí infrastructure (ít DB connections, ít compute)

---

## 2. Quy tắc & Giải thích

### 2.1. Chọn Cache Storage phù hợp

| **Storage** | **Latency** | **Persistence** | **Shared** | **Khi nào dùng** |
| --- | --- | --- | --- | --- |
| In-Memory | 0ms | ❌ Mất khi restart | ❌ | Single server, dev/test, cache nhỏ |
| Redis | 1-2ms | ✅ Có thể persist | ✅ | Production, multi-server, cần data structures phong phú |
| Memcached | 1-2ms | ❌ Mất khi restart | ✅ | Cache đơn giản string/HTML, multi-threaded |
| Multi-tier (L1+L2) | 0ms (L1) / 1-2ms (L2) | ✅ (L2) | ✅ (L2) | Traffic cực lớn, cần tối ưu network latency |

**Khuyến nghị:** Dùng **Redis** làm cache storage mặc định cho production. Chỉ dùng In-Memory cho development/testing hoặc khi chắc chắn chỉ có 1 server.

### 2.2. Nên làm

- **Luôn đặt TTL (Time-To-Live) cho mọi cache entry** — cache không TTL sẽ chiếm RAM vô hạn và trả dữ liệu cũ (stale data). Chọn TTL phù hợp: config/static data (5-30 phút), API responses (30s-5 phút), session (15-60 phút).
- **Dùng `@nestjs/cache-manager` khi chỉ cần key-value đơn giản** (.get/.set/.del) — tận dụng được `CacheInterceptor` cho auto-caching, dễ swap storage (Redis ↔︎ Memcached) mà không đổi code.
- **Dùng `ioredis` khi cần sức mạnh đầy đủ của Redis** (Pub/Sub, Streams, Hash, Sorted Sets, Redlock distributed locking) — không bị giới hạn bởi abstraction layer.
- **Đặt `isGlobal: true` cho `CacheModule`** — tránh import lặp lại trong từng module, giữ code DRY.
- **Cache key phải unique và có namespace** — tránh collision giữa các features. Format: `<module>:<entity>:<id>` (ví dụ: `products:detail:123`, `orders:list:page1`).
- **Invalidate cache khi data thay đổi** — luôn xóa/cập nhật cache trong các mutation operations (create, update, delete). Nếu không, user sẽ thấy dữ liệu cũ.
- **Dùng cache-aside (lazy loading) pattern làm mặc định** — chỉ cache khi data được request, tránh cache data không ai dùng.
- **Quản lý cache thủ công cho các operation phức tạp** — `CacheInterceptor` chỉ phù hợp cho GET đơn giản. Với business logic phức tạp, inject `CACHE_MANAGER` và kiểm soát get/set/del trực tiếp.
- **Đặt `max` (số lượng item tối đa) cho in-memory cache** — tránh memory leak khi cache quá nhiều items.

### 2.3. Không nên làm

- **Không cache mọi thứ** — chỉ cache data đọc nhiều, ít thay đổi. Cache data thay đổi liên tục (real-time counters, chat messages) gây phức tạp không cần thiết.
- **Không dùng `CacheInterceptor` cho non-GET endpoints** — interceptor chỉ cache GET requests. POST/PATCH/DELETE sẽ không hoạt động và có thể gây confusing behavior.
- **Không dùng `CacheInterceptor` với `@Res()` decorator** — khi inject response object trực tiếp, interceptor không thể kiểm soát response.
- **Không dùng In-Memory cache trong môi trường multi-server** — mỗi server có cache riêng, dẫn đến data không đồng bộ giữa các instances.
- **Không cache sensitive data (passwords, tokens) mà không mã hóa** — cache thường không có access control chặt như database.
- **Không set TTL = 0 (vô hạn) trong production** — data sẽ stale và chiếm RAM mãi mãi.
- **Không bỏ qua error handling khi cache unavailable** — Redis down không nên làm sập app. Fallback về DB query khi cache miss/error.

### 2.4. Cache Strategies

**Cache-Aside (Lazy Loading) — Khuyến nghị mặc định:**

1. App kiểm tra cache trước
2. Cache hit → trả về ngay
3. Cache miss → query DB → lưu vào cache → trả về

- *Ưu điểm:* Chỉ cache data được request, tiết kiệm bộ nhớ
- *Nhược điểm:* Request đầu tiên luôn chậm (cold start)

**Write-Through:**

1. Khi write data → ghi đồng thời vào cache và DB

- *Ưu điểm:* Cache luôn đồng bộ với DB
- *Nhược điểm:* Write chậm hơn (2x writes), cache data có thể không bao giờ được đọc

**Write-Behind (Write-Back):**

1. Write vào cache trước → async ghi vào DB sau

- *Ưu điểm:* Write cực nhanh
- *Nhược điểm:* Rủi ro mất data nếu cache crash trước khi flush xuống DB

**Cache-Aside + TTL** là combo phù hợp nhất cho phần lớn use cases trong NestJS applications.

### 2.5. Multi-tier Caching (L1 + L2)

Khi traffic cực lớn, mỗi request gọi Redis vẫn tốn network latency. Giải pháp: kết hợp **L1 (Local Memory)** và **L2 (Redis)**.

- **L1 (Local Memory):** Trả kết quả ngay (0ms), nhưng mỗi server có bản sao riêng
- **L2 (Redis):** Nguồn sự thật chung (source of truth) cho mọi servers
- **Cơ chế (cache-manager 7):** `get()` tìm L1 rồi L2, trả bản đầu tiên tìm thấy và không copy vào L1. Chỉ `wrap()` copy bản tìm thấy ở L2 vào L1. `set()` và `del()` ghi vào cả hai tầng.
- **Invalidate:** `del()` chỉ xóa L1 của instance đang chạy và Redis. L1 của instance khác vẫn trả bản cũ tới hết TTL của entry.

Chỉ dùng multi-tier khi đã đo lường và xác nhận Redis latency là bottleneck thực sự. Đừng over-engineer.

---

## 3. Ví dụ minh họa thực tế

### 3.1. Setup cơ bản với In-Memory Cache

**Cài đặt:**

```bash
# keyv@5: cache-manager 7 reads stores through the Keyv 5 API; with keyv 6, wrap() never hits the cache
pnpm add @nestjs/cache-manager cache-manager keyv@5 cacheable
```

**Cấu hình CacheModule (AppModule):**

```ts
import { Module } from '@nestjs/common';
import { CacheModule } from '@nestjs/cache-manager';
import { Keyv } from 'keyv';
import { CacheableMemory } from 'cacheable';

@Module({
  imports: [
    CacheModule.register({
      ttl: 60 * 1000,  // TTL mặc định: 60 giây (milliseconds)
      // cache-manager v6+ ignores a top-level `max`: cap the item count on the store
      stores: [new Keyv({ store: new CacheableMemory({ lruSize: 100 }) })],
      isGlobal: true,   // Dùng được ở mọi module, không cần import lại
    }),
  ],
})
export class AppModule {}
```

### 3.2. Quản lý Cache thủ công (Khuyến nghị cho business logic)

Inject `CACHE_MANAGER` token để kiểm soát cache trực tiếp:

```ts
import { randomUUID } from 'node:crypto';
import { Inject, Injectable } from '@nestjs/common';
import { CACHE_MANAGER } from '@nestjs/cache-manager';
import type { Cache } from 'cache-manager'; // `import type`: Cache is only a type (TS1272 under isolatedModules)

const LIST_VERSION_KEY = 'products:list:version';
const LIST_VERSION_TTL = 24 * 60 * 60 * 1000; // Longer than any list TTL

@Injectable()
export class ProductsService {
  constructor(
    @Inject(CACHE_MANAGER) private readonly cacheManager: Cache,
    private readonly productsRepository: ProductsRepository,
  ) {}

  // Cache-Aside pattern: check cache → fallback DB → store cache
  // wrap() does get → on miss call the function → set; concurrent calls for one key share one call
  async findOne(id: number): Promise<Product> {
    return this.cacheManager.wrap(
      `products:detail:${id}`,
      () => this.productsRepository.findOneOrFail(id),
      5 * 60 * 1000, // TTL 5 minutes
    );
  }

  // Invalidate cache khi update
  async update(id: number, dto: UpdateProductDto): Promise<Product> {
    const product = await this.productsRepository.update(id, dto);

    // Xóa cache cũ — request tiếp theo sẽ load fresh data
    await this.cacheManager.del(`products:detail:${id}`);
    // List keys embed a version: a new version makes every cached page unreachable (they expire by TTL)
    await this.cacheManager.set(LIST_VERSION_KEY, randomUUID(), LIST_VERSION_TTL);

    return product;
  }

  // Cache list với pagination key
  async findAll(page: number, limit: number): Promise<Product[]> {
    const version = await this.cacheManager.wrap(LIST_VERSION_KEY, () => randomUUID(), LIST_VERSION_TTL);
    return this.cacheManager.wrap(
      `products:list:${version}:page${page}:limit${limit}`,
      () => this.productsRepository.findAll(page, limit),
      2 * 60 * 1000, // TTL 2 phút
    );
  }
}
```

Key list có nhiều biến thể (page, limit, filter), nên `del()` một key cố định không xóa được các key này. Đưa version vào key list và đổi version mỗi khi ghi.

### 3.3. Auto-Caching với CacheInterceptor (cho GET đơn giản)

`CacheInterceptor` tự động cache response cho GET endpoints:

```ts
import { Controller, Get, UseInterceptors } from '@nestjs/common';
import { CacheInterceptor, CacheTTL, CacheKey } from '@nestjs/cache-manager';

@Controller('categories')
@UseInterceptors(CacheInterceptor) // Auto-cache tất cả GET trong controller
export class CategoriesController {
  constructor(private readonly categoriesService: CategoriesService) {}

  @Get()
  @CacheTTL(30 * 1000) // Override TTL: 30 giây
  @CacheKey('categories:all') // Custom cache key thay vì dùng URL
  findAll(): Promise<Category[]> {
    return this.categoriesService.findAll();
  }
}
```

> ⚠️ **Lưu ý về CacheInterceptor:**
> - Chỉ hoạt động với **GET** requests
> - **Không dùng** với `@Res()` decorator (inject response object trực tiếp)
> - **Không phù hợp** cho GraphQL (interceptors chạy riêng cho mỗi field resolver)
> - Với logic phức tạp (invalidation, conditional caching), dùng cache thủ công

### 3.4. Tích hợp Redis (Production)

**Cách 1: Qua `cache-manager` (Abstraction — khuyến nghị khi chỉ cần get/set/del):**

```bash
# Major 5 of both: @keyv/redis 6 needs keyv 6, which breaks wrap() in cache-manager 7 (section 3.1)
pnpm add @keyv/redis@5 keyv@5
```

```ts
import { Logger, Module } from '@nestjs/common';
import { CacheModule } from '@nestjs/cache-manager';
import { ConfigService } from '@nestjs/config';
import { createKeyv } from '@keyv/redis';

@Module({
  imports: [
    CacheModule.registerAsync({
      isGlobal: true,
      inject: [ConfigService],
      useFactory: (config: ConfigService) => {
        const redisStore = createKeyv(
          {
            socket: {
              host: config.getOrThrow<string>('cache.host'), // config/cache.config.ts (section 4.3)
              port: config.getOrThrow<number>('cache.port'),
            },
            password: config.get<string>('cache.password'),
            disableOfflineQueue: true, // Redis down: fail at once instead of queueing (section 3.6)
          },
          { connectionTimeout: 1000 }, // Give up on a connect attempt after 1 s
        );
        const logger = new Logger('Cache');
        // Store errors never reach get/set/wrap; this listener is the only place they show up
        redisStore.on('error', (err: Error) => logger.warn(`Redis cache error: ${err.message}`));
        return {
          // @nestjs/cache-manager 3+ only reads `stores`; a `store` key is silently ignored
          stores: [redisStore],
          ttl: config.getOrThrow<number>('cache.ttl'), // milliseconds
        };
      },
    }),
  ],
})
export class AppModule {}
```

*Ưu điểm:* Code business logic không đổi — chỉ swap config. `CacheInterceptor` vẫn hoạt động. Dễ chuyển sang Memcached nếu cần.

**Cách 2: Qua `ioredis` (Redis Driver — khi cần full Redis features):**

```bash
pnpm add @nestjs-modules/ioredis ioredis
```

```ts
import { Module } from '@nestjs/common';
import { RedisModule } from '@nestjs-modules/ioredis';

@Module({
  imports: [
    RedisModule.forRoot({
      type: 'single',
      url: `redis://${process.env.REDIS_HOST}:${process.env.REDIS_PORT}`,
      options: {
        password: process.env.REDIS_PASSWORD,
      },
    }),
  ],
})
export class AppModule {}
```

```ts
// Sử dụng với full Redis features
import { InjectRedis } from '@nestjs-modules/ioredis';
import Redis from 'ioredis';

@Injectable()
export class SessionService {
  constructor(@InjectRedis() private readonly redis: Redis) {}

  // Hash — lưu session data có cấu trúc
  async setSession(sessionId: string, data: Record<string, string>): Promise<void> {
    await this.redis.hset(`session:${sessionId}`, data);
    await this.redis.expire(`session:${sessionId}`, 3600); // 1 giờ
  }

  // Sorted Set — leaderboard
  async updateScore(userId: string, score: number): Promise<void> {
    await this.redis.zadd('leaderboard', score, userId);
  }

  // Pub/Sub — real-time notifications
  async publishEvent(channel: string, message: string): Promise<void> {
    await this.redis.publish(channel, message);
  }
}
```

### 3.5. Multi-tier Caching (L1 Local + L2 Redis)

```bash
pnpm add @keyv/redis@5 keyv@5 cacheable
```

```ts
import { Module } from '@nestjs/common';
import { CacheModule } from '@nestjs/cache-manager';
import KeyvRedis from '@keyv/redis';
import { Keyv } from 'keyv';
import { CacheableMemory } from 'cacheable';

@Module({
  imports: [
    CacheModule.registerAsync({
      isGlobal: true,
      useFactory: async () => ({
        stores: [
          // L1: Local Memory — 0ms, mỗi server có bản riêng
          new Keyv({
            store: new CacheableMemory({ ttl: 60000, lruSize: 5000 }),
          }),
          // L2: Redis — 1-2ms, shared giữa tất cả servers
          new KeyvRedis(
            { url: 'redis://localhost:6379', disableOfflineQueue: true }, // Fail fast, section 3.6
            { connectionTimeout: 1000 },
          ),
        ],
      }),
    }),
  ],
})
export class AppModule {}
```

> 💡 **Cơ chế hoạt động:** Đọc qua `wrap()` để bản tìm thấy ở L2 được copy vào L1. `get()` không copy (mục 2.5).

### 3.6. Error Handling — Graceful Degradation

Cache unavailable **không nên** làm sập ứng dụng. Với cache-manager 7 và `@keyv/redis`, lỗi Redis không tới code gọi cache:

- Keyv bắt lỗi của store: `get()` và `wrap()` coi như cache miss, `set()` và `del()` vẫn resolve. try/catch quanh các call này không bao giờ chạy.
- Lỗi chỉ xuất hiện qua event `error` của store. Gắn listener để log, như mục 3.4.
- Mặc định client Redis giữ command trong offline queue và reconnect liên tục. Khi Redis down, mọi call cache treo tới lúc Redis lên lại, request treo theo.
- Bật `disableOfflineQueue: true` và `connectionTimeout` như mục 3.4. Khi đó Redis down thì call cache trả về ngay, service đọc DB.

---

## 4. Tooling & Config

### 4.1. Packages cần thiết

| **Package** | **Mục đích** | **Khi nào dùng** |
| --- | --- | --- |
| `@nestjs/cache-manager` | NestJS cache abstraction | Luôn cần |
| `cache-manager` | Core cache manager | Luôn cần |
| `@keyv/redis` | Redis store cho cache-manager v6+ (`createKeyv`) | Production với Redis (abstraction) |
| `ioredis` • `@nestjs-modules/ioredis` | Redis driver trực tiếp | Cần full Redis features |
| `@keyv/redis` • `keyv` • `cacheable` | Multi-tier caching | Traffic cực cao, cần L1+L2 |

### 4.2. Environment Variables

```bash
# .env.example
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_PASSWORD=
CACHE_TTL_MS=60000
CACHE_MAX_ITEMS=1000
```

### 4.3. Config Module tích hợp

```ts
// config/cache.config.ts
import { registerAs } from '@nestjs/config';

export default registerAs('cache', () => ({
  host: process.env.REDIS_HOST || 'localhost',
  port: parseInt(process.env.REDIS_PORT, 10) || 6379,
  password: process.env.REDIS_PASSWORD || undefined,
  ttl: parseInt(process.env.CACHE_TTL_MS, 10) || 60000,
  max: parseInt(process.env.CACHE_MAX_ITEMS, 10) || 1000,
}));
```

### 4.4. Docker — Redis local

```yaml
# docker-compose.yml
services:
  redis:
    image: redis:7-alpine
    ports:
      - '6379:6379'
    command: redis-server --requirepass ${REDIS_PASSWORD:-}
    volumes:
      - redis-data:/data
    restart: unless-stopped

volumes:
  redis-data:
```

---

## References

- [NestJS Caching Documentation](https://docs.nestjs.com/techniques/caching) — tài liệu chính thống
- [cache-manager npm](https://www.npmjs.com/package/cache-manager) — core library
- [ioredis GitHub](https://github.com/redis/ioredis) — Redis driver cho Node.js
- [@keyv/redis](https://www.npmjs.com/package/@keyv/redis) — Redis store cho cache-manager v6+, multi-tier caching
- [Redis Documentation](https://redis.io/docs/) — Redis official docs

## Changelog

| Date | Version | Change | By |
| :---- | :---- | :---- | :---- |
| 2026-11-18 | v1.0 | Chuyển từ Notion "NestJS Document" (page `33d71a38d3b2818a83afc63485294362`, sửa 2026-04-09). Review và sửa nội dung, code trước khi publish. Owner duyệt trong chat ngày 2026-11-18. | Bắc PV |
