# NestJS Coding Standard 8.1 — Testing

| Field | Value |
| :---- | :---- |
| Owner | Bắc PV — NodeJS BE Dev Lead |
| Audience | Dev (NodeJS BE) |
| Last reviewed | 2026-11-12 |
| Review cadence | Quarterly |
| Version | v1.0 |
| Linked from | Ref_Dev_nestjs-coding-standard_v1.0 |
| Status | Live |

Doc này là mục 8.1 của [NestJS Coding Standard](Ref_Dev_nestjs-coding-standard_v1.0.md), nhóm Testing. Doc nêu quy tắc về Testing trong dự án NestJS, kèm lý do, ví dụ và config. Dev NodeJS BE đọc doc này khi viết code, review code và onboarding.

---

## 1. Tóm tắt & Phạm vi

> 🎯 **Chủ đề**: Testing trong NestJS — unit test, integration test, e2e test, mocking strategy, và test coverage.
>
> **Scope**: Áp dụng cho mọi module/service/controller/guard/pipe/interceptor trong dự án NestJS.
>
> **Tại sao quan trọng**: Test là lớp bảo vệ chống regression — thiếu test = merge sợ, refactor sợ, deploy sợ. Test tốt giúp team tự tin ship nhanh, phát hiện bug sớm, và onboard member mới an toàn.

**Phạm vi bao gồm**:

- **Unit test**: Service, Guard, Pipe, Interceptor, custom validators
- **Integration test**: Module với dependencies thật (DB, cache, external service)
- **E2E test**: Full HTTP request lifecycle qua `supertest`
- **Mocking**: Manual mocks, auto-mocking, mock factories, DI overrides
- **Test organization**: File naming, folder structure, test grouping
- **Coverage**: Metrics, thresholds, CI enforcement

---

## 2. Quy tắc & Giải thích

### 2.1 Phân loại test & Kim tự tháp testing

> ✅ **Đề xuất**: Tuân theo Testing Pyramid — nhiều unit test (nhanh, rẻ), ít integration test (chậm hơn, cần infra), rất ít e2e test (chậm nhất, brittle nhất).

| Loại test | Scope | Tốc độ | Khi nào viết | Tỷ lệ đề xuất |
| --- | --- | --- | --- | --- |
| **Unit test** | 1 class/function, mock hết dependencies | ⚡ Rất nhanh (ms) | Mọi service, guard, pipe, utility | \~70% |
| **Integration test** | Module + DB/cache thật, mock external APIs | 🐢 Trung bình (giây) | Repository + Service với DB, cache logic | \~20% |
| **E2E test** | Full HTTP request → response | 🐌 Chậm (giây–phút) | Critical flows: auth, checkout, payment | \~10% |

> **Tại sao?** Unit test nhanh → chạy mỗi khi save/commit → feedback loop ngắn. E2E test chậm + brittle → chỉ cover happy path + critical edge cases.

### 2.2 Unit Test — Nguyên tắc & Cách viết

**✅ Nên làm:**

- **Mỗi test chỉ kiểm tra 1 behavior** — không gộp nhiều assertion không liên quan vào 1 test case
- *Tại sao*: Test fail → biết ngay behavior nào hỏng. Gộp nhiều thứ → phải debug mới biết chỗ nào sai.
- **Dùng `Test.createTestingModule()` của NestJS** để tạo module test với DI container
- *Tại sao*: Giữ nguyên DI behavior, mock dependencies qua `.overrideProvider()`, test gần với production code.
- **Mock tất cả dependencies** — unit test không gọi DB, HTTP, file system
- *Tại sao*: Unit test phải nhanh (\< 50ms/test) và deterministic. DB/network gây flaky test.
- **Đặt tên test mô tả behavior**, không mô tả implementation:
- ✅ `'should throw NotFoundException when product does not exist'`
- ❌ `'should call findOne and return null'`
- **Cấu trúc AAA** (Arrange → Act → Assert) cho mọi test case
- *Tại sao*: Dễ đọc, dễ review — mọi member đều biết pattern.
- **Test cả happy path và edge cases**: input rỗng, null, boundary values, error paths
- **Test service method trả đúng kết quả** VÀ **gọi dependencies đúng cách** (verify mock calls khi cần)

```ts
// products.service.spec.ts — Unit test chuẩn
import { Test, TestingModule } from '@nestjs/testing';
import { ProductsService } from './products.service';
import { ProductsRepository } from './products.repository';
import { NotFoundException } from '@nestjs/common';

describe('ProductsService', () => {
  let service: ProductsService;
  let repository: jest.Mocked<ProductsRepository>;

  beforeEach(async () => {
    const module: TestingModule = await Test.createTestingModule({
      providers: [
        ProductsService,
        {
          provide: ProductsRepository,
          useValue: {
            findById: jest.fn(),
            save: jest.fn(),
            delete: jest.fn(),
          },
        },
      ],
    }).compile();

    service = module.get(ProductsService);
    repository = module.get(ProductsRepository);
  });

  describe('findOne', () => {
    it('should return product when found', async () => {
      // Arrange
      const mockProduct = { id: '1', name: 'Áo thun', price: 199000 };
      repository.findById.mockResolvedValue(mockProduct as any);

      // Act
      const result = await service.findOne('1');

      // Assert
      expect(result).toEqual(mockProduct);
      expect(repository.findById).toHaveBeenCalledWith('1');
    });

    it('should throw NotFoundException when product does not exist', async () => {
      // Arrange
      repository.findById.mockResolvedValue(null);

      // Act & Assert
      await expect(service.findOne('999')).rejects.toThrow(NotFoundException);
    });
  });
});
```

**❌ Không nên làm:**

- **Không test implementation details** — test behavior (kết quả, side effects), không test “gọi hàm nào trước”
- *Tại sao*: Refactor internal code → test vẫn pass nếu behavior đúng. Test implementation → mỗi lần refactor đều phải sửa test.
- **Không dùng `any` cho mock** — tạo typed mock hoặc dùng `jest.Mocked<T>`
- **Không share mutable state giữa test cases** — mỗi test có setup riêng trong `beforeEach`
- **Không test private methods trực tiếp** — test qua public API. Nếu private method phức tạp → tách ra utility/service riêng.

### 2.3 Integration Test — Module + DB thật

> ✅ **Đề xuất**: Dùng integration test để verify ORM queries, transaction logic, và repository methods với database thật (test DB container).

**✅ Nên làm:**

- **Dùng test database riêng** — Docker container hoặc in-memory DB (SQLite cho đơn giản, PostgreSQL container cho production parity)
- *Tại sao*: Test trên DB thật bắt được lỗi ORM, migration, constraint mà unit test mock bỏ qua.
- **Reset DB state trước mỗi test** — truncate tables hoặc transaction rollback
- *Tại sao*: Test order-independent — chạy riêng hay chạy cả suite đều pass.
- **Seed data cần thiết trong `beforeEach`** — mỗi test tự tạo data, không rely vào test khác
- **Mock external services** (HTTP APIs, email, payment) — chỉ test DB interaction
- **Đặt tên `*.integration.spec.ts`, chạy bằng `pnpm test:integration`** (config riêng, mục 4.1–4.2)
- *Tại sao*: Unit config bỏ qua các file này, nên `pnpm test` không cần DB. `--runInBand` vì các test dùng chung một DB.

```ts
// orders.integration.spec.ts
import { Test, TestingModule } from '@nestjs/testing';
import { TypeOrmModule } from '@nestjs/typeorm';
import { DataSource } from 'typeorm';
import { OrdersService } from './orders.service';
import { OrdersRepository } from './orders.repository';
import { Order } from './entities/order.entity';
import { OrderItem } from './entities/order-item.entity';
import { cleanDatabase } from '../../../test/helpers/test-db-setup'; // section 4.5

describe('OrdersService (Integration)', () => {
  let module: TestingModule;
  let service: OrdersService;
  let dataSource: DataSource;

  beforeAll(async () => {
    module = await Test.createTestingModule({
      imports: [
        TypeOrmModule.forRoot({
          type: 'postgres', // MySQL: 'mysql' (driver mysql2)
          host: 'localhost',
          port: 5433, // Test DB port
          username: 'test', // Same as the postgres service in CI (section 4.4)
          password: 'test',
          database: 'test_db',
          entities: [Order, OrderItem],
          synchronize: true, // OK cho test DB
        }),
        TypeOrmModule.forFeature([Order, OrderItem]),
      ],
      providers: [
        OrdersService,
        OrdersRepository,
        {
          provide: InventoryService,
          useValue: { checkStock: jest.fn().mockResolvedValue({ available: true }) },
        },
      ],
    }).compile();

    service = module.get(OrdersService);
    dataSource = module.get(DataSource);
  });

  afterEach(async () => {
    // Reset DB state sau mỗi test
    await cleanDatabase(dataSource);
  });

  afterAll(async () => {
    await dataSource.destroy();
    await module.close();
  });

  it('should create order with items in a single transaction', async () => {
    const dto = {
      customerId: 'cust-1',
      items: [{ productId: 'prod-1', quantity: 2 }],
    };

    const order = await service.create(dto);

    expect(order.id).toBeDefined();
    expect(order.status).toBe('pending');

    // Verify data persisted correctly
    const saved = await dataSource.getRepository(Order).findOne({
      where: { id: order.id },
      relations: ['items'],
    });
    expect(saved.items).toHaveLength(1);
    expect(saved.items[0].quantity).toBe(2);
  });

  it('should rollback transaction when inventory check fails', async () => {
    // Arrange — mock inventory failure
    const inventoryService = module.get(InventoryService);
    jest.spyOn(inventoryService, 'checkStock').mockResolvedValueOnce({
      available: false,
      unavailableItems: ['prod-1'],
    });

    // Act & Assert
    await expect(service.create({ customerId: 'cust-1', items: [{ productId: 'prod-1', quantity: 100 }] }))
      .rejects.toThrow(BadRequestException);

    // Verify no order was created
    const count = await dataSource.getRepository(Order).count();
    expect(count).toBe(0);
  });
});
```

Project dùng Prisma giữ nguyên các test case, chỉ khác setup, cleanup và chỗ đọc lại DB. Prisma không có `synchronize`, nên chạy `prisma migrate deploy` lên test DB trước suite.

```ts
// orders.integration.spec.ts — Prisma: replaces the TypeORM setup above
// PrismaService: 4.1 section 2.7. cleanDatabase: section 4.5.
let prisma: PrismaService;

beforeAll(async () => {
  module = await Test.createTestingModule({
    providers: [
      OrdersService,
      OrdersRepository,
      PrismaService,
      {
        provide: ConfigService, // PrismaService reads DATABASE_URL from ConfigService
        useValue: new ConfigService({ DATABASE_URL: 'postgresql://test:test@localhost:5433/test_db' }),
      },
      {
        provide: InventoryService,
        useValue: { checkStock: jest.fn().mockResolvedValue({ available: true }) },
      },
    ],
  }).compile();
  await module.init(); // Runs PrismaService.onModuleInit -> $connect()

  service = module.get(OrdersService);
  prisma = module.get(PrismaService);
});

afterEach(async () => {
  await cleanDatabase(prisma);
});

afterAll(async () => {
  await prisma.$disconnect(); // module.close() does not disconnect Prisma
  await module.close();
});

// Reading back inside the it() blocks
const saved = await prisma.order.findUnique({
  where: { id: order.id },
  include: { items: true },
});
expect(saved?.items).toHaveLength(1);
expect(await prisma.order.count()).toBe(0);
```

Prisma 7 client nạp query compiler bằng dynamic `import()`. Khi `tsconfig` dùng `module: nodenext`, integration test và e2e test phải chạy Jest với `NODE_OPTIONS=--experimental-vm-modules`. Thiếu flag này, `$connect()` báo lỗi `A dynamic import callback was invoked without --experimental-vm-modules`.

**❌ Không nên làm:**

- **Không dùng production DB cho integration test** — luôn dùng DB riêng biệt
- **Không để test depend vào order chạy** — mỗi test phải self-contained
- **Không skip cleanup** — data từ test trước gây flaky test

### 2.4 E2E Test — Full HTTP Lifecycle

> ✅ **Đề xuất**: E2E test dùng `supertest` gọi HTTP thật qua NestJS app. Chỉ viết cho critical user flows — không cover mọi endpoint.

**✅ Nên làm:**

- **Test full request → response**: HTTP method, status code, response body, headers
- **Test authentication flow**: Login → access protected route → refresh token → logout
- **Test validation**: Gửi invalid input → expect 400 + error format chuẩn
- **Test authorization**: User A không access được resource của User B
- **Đặt e2e test trong folder `test/`** ở root, file naming: `.e2e-spec.ts`
- **Tạo `.env.test` cho e2e** — Jest tự set `NODE_ENV=test`, nên `AppModule` load `.env.test` (`envFilePath` ở [NestJS Coding Standard 2.1 — Configuration & Environment Management](Ref_Dev_s2.1_nestjs-configuration-environment_v1.0.md)) và schema `NODE_ENV` phải chấp nhận `test`. File này trỏ tới test DB; trên CI, tạo file này hoặc set các biến tương ứng.

```ts
// test/products.e2e-spec.ts
import { Test, TestingModule } from '@nestjs/testing';
import { INestApplication, ValidationPipe } from '@nestjs/common';
import cookieParser from 'cookie-parser';
import request from 'supertest';
import { AppModule } from '../src/app.module';
import { GlobalExceptionFilter } from '../src/common/filters/global-exception.filter';
import { GlobalResponseInterceptor } from '../src/common/interceptors/global-response.interceptor';
import { validationExceptionFactory } from '../src/common/validation/validation-exception.factory';

describe('ProductsController (E2E)', () => {
  let app: INestApplication;
  let authCookies: string[];

  beforeAll(async () => {
    const module: TestingModule = await Test.createTestingModule({
      imports: [AppModule],
    }).compile();

    app = module.createNestApplication();
    // Same globals as main.ts: the data/error body asserted below comes from them
    app.use(cookieParser()); // JwtStrategy reads the accessToken cookie
    app.useGlobalPipes(new ValidationPipe({
      whitelist: true,
      forbidNonWhitelisted: true,
      transform: true,
      exceptionFactory: validationExceptionFactory,
    }));
    app.useGlobalFilters(new GlobalExceptionFilter());
    app.useGlobalInterceptors(new GlobalResponseInterceptor());
    await app.init();

    // Login: the tokens come back as HttpOnly cookies (5.1 section 3.2), not in the body
    const loginRes = await request(app.getHttpServer())
      .post('/auth/login')
      .send({ email: 'admin@test.com', password: 'Test@123' })
      .expect(204);
    authCookies = loginRes.get('Set-Cookie') ?? [];
  });

  afterAll(async () => {
    await app.close();
  });

  describe('POST /products', () => {
    it('should create product with valid data', () => {
      return request(app.getHttpServer())
        .post('/products')
        .set('Cookie', authCookies)
        .send({ name: 'Áo thun nam', price: 199000 })
        .expect(201)
        .expect((res) => {
          expect(res.body.data.name).toBe('Áo thun nam');
          expect(res.body.data.price).toBe(199000);
        });
    });

    it('should return 400 for invalid input', () => {
      return request(app.getHttpServer())
        .post('/products')
        .set('Cookie', authCookies)
        .send({ name: '', price: -1 }) // Invalid
        .expect(400)
        .expect((res) => {
          expect(res.body.error.type).toBe('VALIDATION_ERROR');
          expect(res.body.error.details).toEqual(
            expect.arrayContaining([expect.objectContaining({ field: 'price' })]),
          );
        });
    });

    it('should return 401 without the auth cookie', () => {
      return request(app.getHttpServer())
        .post('/products')
        .send({ name: 'Test', price: 100 })
        .expect(401);
    });
  });

  describe('GET /products', () => {
    it('should return paginated products', () => {
      return request(app.getHttpServer())
        .get('/products?page=1&limit=10')
        .set('Cookie', authCookies)
        .expect(200)
        .expect((res) => {
          expect(Array.isArray(res.body.data)).toBe(true);
          expect(res.body.meta).toHaveProperty('total');
          expect(res.body.meta).toHaveProperty('totalPages');
        });
    });
  });
});
```

**❌ Không nên làm:**

- **Không viết e2e test cho mọi endpoint** — chỉ critical flows (auth, payment, core business)
- *Tại sao*: E2E chậm, brittle, tốn CI time. Unit + integration test cover phần còn lại.
- **Không quên setup GlobalPipes/GlobalFilters** trong e2e — phải mirror production setup
- *Tại sao*: Thiếu ValidationPipe → e2e test pass nhưng app thật validate đúng → false confidence.
- **Không hardcode test data** — dùng factory/seeder tạo data, cleanup sau test

### 2.5 Mocking Strategy

> ✅ **Đề xuất**: Mock đúng cấp độ — unit test mock hết, integration test mock external, e2e test mock ít nhất có thể.

**Các cách mock trong NestJS:**

| Cách mock | Khi nào dùng | Ưu/Nhược điểm |
| --- | --- | --- |
| **Manual mock object** | Unit test — mock đơn giản, ít methods | ✅ Dễ hiểu, nhanh. ❌ Phải update khi interface đổi |
| **`jest.Mocked<T>`** | Unit test — cần type-safe mock cho class lớn | ✅ Type-safe, auto-complete. ❌ Cần setup `jest.fn()` cho mỗi method |
| **`.overrideProvider()`** | Integration/E2E — thay thế provider trong DI container | ✅ NestJS-native, works với DI. ❌ Chậm hơn manual mock |
| **Mock Factory** | Shared mock dùng ở nhiều test files | ✅ DRY, consistent. ❌ Cần maintain factory |

**Pattern: Mock Factory cho reuse**

```ts
// test/mocks/mock-products-repository.ts
import { ProductsRepository } from '../../src/modules/products/products.repository';

export type MockProductsRepository = jest.Mocked<Pick<
  ProductsRepository,
  'findById' | 'findAll' | 'save' | 'delete'
>>;

export const createMockProductsRepository = (): MockProductsRepository => ({
  findById: jest.fn(),
  findAll: jest.fn(),
  save: jest.fn(),
  delete: jest.fn(),
});
```

```ts
// Sử dụng trong test
import { createMockProductsRepository } from '../mocks/mock-products-repository';

beforeEach(async () => {
  const module = await Test.createTestingModule({
    providers: [
      ProductsService,
      { provide: ProductsRepository, useValue: createMockProductsRepository() },
    ],
  }).compile();
});
```

**Pattern: Mock external HTTP calls**

```ts
// Mock HttpService cho external API calls
const mockHttpService = {
  axiosRef: {
    get: jest.fn(),
    post: jest.fn(),
  },
};

// Hoặc dùng nock/msw cho HTTP mocking ở integration level
import nock from 'nock';

beforeEach(() => {
  nock('https://api.payment.com')
    .post('/charges')
    .reply(200, { id: 'ch_123', status: 'succeeded' });
});

afterEach(() => {
  nock.cleanAll();
});
```

**❌ Không nên làm:**

- **Không mock quá sâu** — mock interface/contract, không mock internal implementation
- **Không quên `jest.clearAllMocks()` hoặc `jest.restoreAllMocks()`** trong `afterEach` — mock leak giữa tests gây flaky
- **Không dùng `jest.mock()` ở top level** cho NestJS providers — dùng DI overrides thay thế
- *Tại sao*: `jest.mock()` hoạt động ở module level, bypass DI container → không test đúng cách NestJS resolve dependencies.

### 2.6 Test Guards, Pipes, Interceptors

**Test Guard:**

```ts
// roles.guard.spec.ts
describe('RolesGuard', () => {
  let guard: RolesGuard;
  let reflector: Reflector;

  beforeEach(async () => {
    const module = await Test.createTestingModule({
      providers: [RolesGuard, Reflector],
    }).compile();

    guard = module.get(RolesGuard);
    reflector = module.get(Reflector);
  });

  it('should allow access when no roles required', () => {
    jest.spyOn(reflector, 'getAllAndOverride').mockReturnValue(undefined);
    const context = createMockExecutionContext({ user: { roles: ['customer'] } });

    expect(guard.canActivate(context)).toBe(true);
  });

  it('should deny access when user lacks required role', () => {
    jest.spyOn(reflector, 'getAllAndOverride').mockReturnValue(['admin']);
    const context = createMockExecutionContext({ user: { roles: ['customer'] } });

    expect(guard.canActivate(context)).toBe(false);
  });

  it('should allow access when user has required role', () => {
    jest.spyOn(reflector, 'getAllAndOverride').mockReturnValue(['admin']);
    const context = createMockExecutionContext({ user: { roles: ['admin'] } });

    expect(guard.canActivate(context)).toBe(true);
  });
});
```

**Test Custom Pipe:**

```ts
// parse-positive-int.pipe.spec.ts
describe('ParsePositiveIntPipe', () => {
  let pipe: ParsePositiveIntPipe;

  beforeEach(() => {
    pipe = new ParsePositiveIntPipe();
  });

  it('should return number for valid positive integer string', () => {
    expect(pipe.transform('42', {} as any)).toBe(42);
  });

  it('should throw BadRequestException for negative number', () => {
    expect(() => pipe.transform('-1', {} as any)).toThrow(BadRequestException);
  });

  it('should throw BadRequestException for non-numeric string', () => {
    expect(() => pipe.transform('abc', {} as any)).toThrow(BadRequestException);
  });
});
```

### 2.7 Test Organization & Naming

**Quy tắc:**

- ✅ **Unit test**: Đặt cạnh file source — `products.service.ts` → `products.service.spec.ts`
- ✅ **Integration test**: Đặt cạnh file source — `orders.service.ts` → `orders.integration.spec.ts`
- ✅ **E2E test**: Đặt trong `test/` ở root — `test/products.e2e-spec.ts`
- ✅ **Mock factories**: Đặt trong `test/mocks/` — dùng chung cho cả unit và integration
- ✅ **Test helpers/utilities**: Đặt trong `test/helpers/` — factory functions, custom matchers
- ✅ **Describe block** theo class → method → scenario:

```ts
describe('OrdersService', () => {
  describe('create', () => {
    it('should create order with valid items', () => { ... });
    it('should throw when stock insufficient', () => { ... });
    it('should rollback when DB error occurs', () => { ... });
  });

  describe('cancel', () => {
    it('should cancel pending order', () => { ... });
    it('should throw when order already shipped', () => { ... });
  });
});
```

**Cấu trúc folder:**

```txt
project-root/
├── src/
│   └── modules/
│       └── products/
│           ├── products.service.ts
│           ├── products.service.spec.ts        # Unit test
│           ├── products.repository.ts
│           ├── products.repository.spec.ts     # Unit test
│           ├── products.controller.ts
│           └── products.controller.spec.ts     # Unit test
├── test/
│   ├── mocks/
│   │   ├── mock-products-repository.ts
│   │   └── mock-config-service.ts
│   ├── helpers/
│   │   ├── create-mock-context.ts
│   │   └── test-db-setup.ts
│   ├── products.e2e-spec.ts                    # E2E test
│   ├── auth.e2e-spec.ts                        # E2E test
│   ├── jest-e2e.json
│   └── jest-integration.json
├── jest.config.ts
└── package.json
```

### 2.8 Coverage — Metrics & Thresholds

> ⚠️ **Nguyên tắc**: Coverage là metric hữu ích nhưng không phải mục tiêu. 100% coverage không có nghĩa là code không có bug. Focus vào test quality (test đúng behavior) hơn là số %.

**Quy tắc:**

- ✅ **NÊN**: Đặt coverage threshold tối thiểu trong CI: **80% lines, 80% branches** cho business logic
- ✅ **NÊN**: Focus coverage vào **service layer** (business logic) và **guards/pipes** (security/validation)
- ✅ **NÊN**: Review uncovered lines — nếu là error handling/edge case → cần test. Nếu là boilerplate → có thể bỏ qua.
- ✅ **NÊN**: Track coverage trend — nếu giảm dần qua các PR → cần review process
- ❌ **KHÔNG NÊN**: Chase 100% coverage — tốn thời gian test getter/setter, DTO, entity mà không có value
- ❌ **KHÔNG NÊN**: Exclude files khỏi coverage chỉ để đạt threshold — chỉ exclude generated files, migrations

---

## 3. Ví dụ minh họa thực tế

### 3.1 Walkthrough: Test cho feature “Quản lý sản phẩm”

**Bước 1: Unit test Service — business logic**

```ts
// products.service.spec.ts
describe('ProductsService', () => {
  let service: ProductsService;
  let repository: jest.Mocked<ProductsRepository>;
  let cacheManager: jest.Mocked<Cache>;

  beforeEach(async () => {
    const module = await Test.createTestingModule({
      providers: [
        ProductsService,
        {
          provide: ProductsRepository,
          useValue: {
            findById: jest.fn(),
            findBySku: jest.fn(),
            findAll: jest.fn(),
            save: jest.fn(),
            delete: jest.fn(),
          },
        },
        {
          provide: CACHE_MANAGER,
          useValue: {
            get: jest.fn(),
            set: jest.fn(),
            del: jest.fn(),
          },
        },
      ],
    }).compile();

    service = module.get(ProductsService);
    repository = module.get(ProductsRepository);
    cacheManager = module.get(CACHE_MANAGER);
  });

  afterEach(() => {
    jest.clearAllMocks();
  });

  describe('create', () => {
    it('should create product and invalidate cache', async () => {
      // Arrange
      const dto: CreateProductDto = { name: 'Áo thun', price: 199000 };
      const saved = { id: '1', ...dto, createdAt: new Date() };
      repository.save.mockResolvedValue(saved as any);

      // Act
      const result = await service.create(dto);

      // Assert
      expect(result).toEqual(saved);
      expect(repository.save).toHaveBeenCalledWith(expect.objectContaining(dto));
      expect(cacheManager.del).toHaveBeenCalledWith('products:list');
    });

    it('should throw ConflictException when SKU already exists', async () => {
      const dto: CreateProductDto = { name: 'Áo thun', price: 199000, sku: 'AT-001' };
      repository.findBySku.mockResolvedValue({ id: '2', sku: 'AT-001' } as any);

      await expect(service.create(dto)).rejects.toThrow(ConflictException);
      expect(repository.save).not.toHaveBeenCalled();
    });
  });

  describe('findOne', () => {
    it('should return cached product when available', async () => {
      const cached = { id: '1', name: 'Áo thun', price: 199000 };
      cacheManager.get.mockResolvedValue(cached);

      const result = await service.findOne('1');

      expect(result).toEqual(cached);
      expect(repository.findById).not.toHaveBeenCalled(); // Không query DB
    });

    it('should query DB and cache result on cache miss', async () => {
      const product = { id: '1', name: 'Áo thun', price: 199000 };
      cacheManager.get.mockResolvedValue(null);
      repository.findById.mockResolvedValue(product as any);

      const result = await service.findOne('1');

      expect(result).toEqual(product);
      expect(repository.findById).toHaveBeenCalledWith('1');
      expect(cacheManager.set).toHaveBeenCalledWith(
        'products:detail:1',
        product,
        5 * 60 * 1000,
      );
    });
  });
});
```

**Bước 2: Unit test Controller — HTTP layer**

```ts
// products.controller.spec.ts
describe('ProductsController', () => {
  let controller: ProductsController;
  let service: jest.Mocked<ProductsService>;

  beforeEach(async () => {
    const module = await Test.createTestingModule({
      controllers: [ProductsController],
      providers: [{
        provide: ProductsService,
        useValue: {
          create: jest.fn(),
          findOne: jest.fn(),
          findAll: jest.fn(),
          update: jest.fn(),
          remove: jest.fn(),
        },
      }],
    }).compile();

    controller = module.get(ProductsController);
    service = module.get(ProductsService);
  });

  describe('create', () => {
    it('should call service.create and return result', async () => {
      const dto = { name: 'Áo thun', price: 199000 };
      const expected = { id: '1', ...dto };
      service.create.mockResolvedValue(expected as any);

      const result = await controller.create(dto as any);

      expect(service.create).toHaveBeenCalledWith(dto);
      expect(result).toBeDefined();
    });
  });
});
```

**Bước 3: E2E test — full HTTP flow**

```ts
// test/products.e2e-spec.ts
describe('Products (E2E)', () => {
  let app: INestApplication;
  let authCookies: string[];

  beforeAll(async () => {
    const module = await Test.createTestingModule({
      imports: [AppModule],
    }).compile();

    app = module.createNestApplication();
    // Mirror production setup
    app.use(cookieParser());
    app.useGlobalPipes(new ValidationPipe({ whitelist: true, transform: true, exceptionFactory: validationExceptionFactory }));
    app.useGlobalFilters(new GlobalExceptionFilter());
    app.useGlobalInterceptors(new GlobalResponseInterceptor());
    await app.init();

    // Seed + login; returns the Set-Cookie headers of POST /auth/login
    authCookies = await loginAsAdmin(app);
  });

  afterAll(async () => {
    await app.close();
  });

  it('POST /products → 201 → GET /products/:id → 200', async () => {
    // Create
    const createRes = await request(app.getHttpServer())
      .post('/products')
      .set('Cookie', authCookies)
      .send({ name: 'Áo thun E2E', price: 199000 })
      .expect(201);

    const productId = createRes.body.data.id;

    // Verify — GET by id
    const getRes = await request(app.getHttpServer())
      .get(`/products/${productId}`)
      .set('Cookie', authCookies)
      .expect(200);

    expect(getRes.body.data.name).toBe('Áo thun E2E');
    expect(getRes.body.data.price).toBe(199000);
  });
});
```

### 3.2 Before/After: Từ test kém → test chuẩn

**❌ Before — Test không đáng tin cậy:**

```ts
// ❌ Bad — mock quá sâu, test implementation, no cleanup
describe('OrdersService', () => {
  let service: OrdersService;

  beforeAll(() => {
    // ❌ Share state giữa tests
    service = new OrdersService(mockRepo as any, mockInventory as any);
  });

  it('test create order', async () => {
    // ❌ Tên test mơ hồ
    // ❌ Dùng any, không type-safe
    const result = await service.create({ items: [{ productId: '1', quantity: 1 }] } as any);

    // ❌ Test implementation detail
    expect(mockRepo.createQueryBuilder).toHaveBeenCalled();
    expect(mockRepo.createQueryBuilder().where).toHaveBeenCalledWith('id = :id', { id: '1' });

    // ❌ Không assert kết quả business
    expect(result).toBeTruthy();
  });

  // ❌ Không test error cases
});
```

**✅ After — Test đáng tin cậy:**

```ts
// ✅ Good — clear name, proper mock, test behavior
describe('OrdersService', () => {
  let service: OrdersService;
  let ordersRepo: jest.Mocked<OrdersRepository>;
  let inventoryService: jest.Mocked<InventoryService>;

  beforeEach(async () => {
    // ✅ Fresh setup mỗi test — không share state
    const module = await Test.createTestingModule({
      providers: [
        OrdersService,
        { provide: OrdersRepository, useValue: createMockOrdersRepository() },
        { provide: InventoryService, useValue: createMockInventoryService() },
      ],
    }).compile();

    service = module.get(OrdersService);
    ordersRepo = module.get(OrdersRepository);
    inventoryService = module.get(InventoryService);
  });

  afterEach(() => {
    jest.clearAllMocks(); // ✅ Cleanup mock state
  });

  describe('create', () => {
    const validDto: CreateOrderDto = {
      customerId: 'cust-1',
      items: [{ productId: 'prod-1', quantity: 2 }],
    };

    it('should create order when stock is available', async () => {
      // ✅ Arrange — clear setup
      inventoryService.checkStock.mockResolvedValue({ available: true });
      ordersRepo.createWithItems.mockResolvedValue({ id: 'ord-1', status: 'pending' } as any);

      // ✅ Act
      const result = await service.create(validDto);

      // ✅ Assert behavior, không assert internal calls
      expect(result.id).toBe('ord-1');
      expect(result.status).toBe('pending');
    });

    it('should throw BadRequestException when stock insufficient', async () => {
      // ✅ Test error path
      inventoryService.checkStock.mockResolvedValue({
        available: false,
        unavailableItems: ['prod-1'],
      });

      await expect(service.create(validDto)).rejects.toThrow(BadRequestException);
      expect(ordersRepo.createWithItems).not.toHaveBeenCalled(); // ✅ Verify side effect
    });
  });
});
```

---

## 4. Tooling & Config

### 4.1 Jest Configuration

```ts
// jest.config.ts — Unit test config
import type { Config } from 'jest';

const config: Config = {
  moduleFileExtensions: ['js', 'json', 'ts'],
  rootDir: '.',
  testRegex: '.*\\.spec\\.ts$',
  // Integration specs need a real DB: run them with test:integration, not `pnpm test`
  testPathIgnorePatterns: ['/node_modules/', '\\.integration\\.spec\\.ts$'],
  transform: {
    '^.+\\.ts$': 'ts-jest',
  },
  collectCoverageFrom: [
    'src/**/*.ts',
    '!src/**/*.module.ts',       // Module declarations
    '!src/**/*.entity.ts',       // Entities (no logic)
    '!src/**/*.dto.ts',          // DTOs (validated elsewhere)
    '!src/**/*.integration.spec.ts', // Ignored above, otherwise counted as uncovered source
    '!src/main.ts',              // Bootstrap
    '!src/**/index.ts',          // Barrel exports
  ],
  coverageDirectory: './coverage',
  // Defaults plus json-summary: the CI coverage gate reads coverage/coverage-summary.json (section 4.4)
  coverageReporters: ['json', 'text', 'lcov', 'clover', 'json-summary'],
  coverageThreshold: {
    global: {
      branches: 80,
      functions: 80,
      lines: 80,
      statements: 80,
    },
  },
  testEnvironment: 'node',
  moduleNameMapper: {
    '^(\\.{1,2}/.*)\\.js$': '$1', // Prisma 7 generated client imports './x.js' from .ts files
    '^@common/(.*)$': '<rootDir>/src/common/$1',
    '^@modules/(.*)$': '<rootDir>/src/modules/$1',
    '^@config/(.*)$': '<rootDir>/src/config/$1',
  },
};

export default config;
```

```json
// test/jest-e2e.json — E2E test config
{
  "moduleFileExtensions": ["js", "json", "ts"],
  "rootDir": "..",
  "testEnvironment": "node",
  "testRegex": ".e2e-spec.ts$",
  "transform": {
    "^.+\\.ts$": "ts-jest"
  },
  "moduleNameMapper": {
    "^(\\.{1,2}/.*)\\.js$": "$1",
    "^@common/(.*)$": "<rootDir>/src/common/$1",
    "^@modules/(.*)$": "<rootDir>/src/modules/$1"
  }
}
```

```json
// test/jest-integration.json — Integration test config (needs the test DB)
{
  "moduleFileExtensions": ["js", "json", "ts"],
  "rootDir": "..",
  "testEnvironment": "node",
  "testRegex": ".*\\.integration\\.spec\\.ts$",
  "transform": {
    "^.+\\.ts$": "ts-jest"
  },
  "moduleNameMapper": {
    "^(\\.{1,2}/.*)\\.js$": "$1",
    "^@common/(.*)$": "<rootDir>/src/common/$1",
    "^@modules/(.*)$": "<rootDir>/src/modules/$1",
    "^@config/(.*)$": "<rootDir>/src/config/$1"
  }
}
```

### 4.2 Package.json scripts

```json
{
  "scripts": {
    "test": "jest",
    "test:watch": "jest --watch",
    "test:cov": "jest --coverage",
    "test:debug": "node --inspect-brk -r tsconfig-paths/register -r ts-node/register node_modules/jest/bin/jest.js --runInBand",
    "test:integration": "jest --config ./test/jest-integration.json --runInBand",
    "test:e2e": "jest --config ./test/jest-e2e.json --runInBand",
    "test:e2e:cov": "jest --config ./test/jest-e2e.json --runInBand --coverage"
  }
}
```

### 4.3 Packages cần cài

```bash
# Testing core (thường đã có sẵn với Nest CLI)
pnpm add -D jest ts-jest @types/jest

# NestJS testing utilities
pnpm add -D @nestjs/testing

# E2E testing
pnpm add -D supertest @types/supertest

# HTTP mocking (optional — cho integration test)
pnpm add -D nock
# hoặc
pnpm add -D msw

# Coverage badge (optional)
pnpm add -D jest-badge-generator
```

### 4.4 CI Integration

```yaml
# .github/workflows/test.yml — GitHub Actions
name: Test
on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    services:
      postgres:
        image: postgres:16 # MySQL: mysql:8.4 with MYSQL_* env, port 3306, --health-cmd "mysqladmin ping"
        env:
          POSTGRES_USER: test
          POSTGRES_PASSWORD: test
          POSTGRES_DB: test_db
        ports:
          - 5433:5432
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5

    steps:
      - uses: actions/checkout@v4
      - uses: pnpm/action-setup@v4 # version from "packageManager" in package.json (9.3, section 2.2)
      - uses: actions/setup-node@v4
        with:
          node-version: 22
          cache: pnpm

      - run: pnpm install --frozen-lockfile
      - run: pnpm test:cov          # Unit + coverage
      - run: pnpm test:integration  # Integration (postgres service)
      - run: pnpm test:e2e          # E2E

      - name: Check coverage threshold
        run: |
          COVERAGE=$(cat coverage/coverage-summary.json | jq '.total.lines.pct')
          if (( $(echo "$COVERAGE < 80" | bc -l) )); then
            echo "Coverage $COVERAGE% is below 80% threshold"
            exit 1
          fi
```

### 4.5 Test Helper Utilities

```ts
// test/helpers/create-mock-context.ts
import { ExecutionContext } from '@nestjs/common';

export function createMockExecutionContext(
  overrides: { user?: any; params?: any; query?: any; body?: any } = {},
): ExecutionContext {
  const request = {
    user: overrides.user ?? { userId: 'test-user', roles: ['customer'] },
    params: overrides.params ?? {},
    query: overrides.query ?? {},
    body: overrides.body ?? {},
  };

  return {
    switchToHttp: () => ({
      getRequest: () => request,
      getResponse: () => ({ json: jest.fn(), status: jest.fn().mockReturnThis() }),
    }),
    getHandler: () => jest.fn(),
    getClass: () => jest.fn(),
  } as unknown as ExecutionContext;
}
```

```ts
// test/helpers/test-db-setup.ts
import { DataSource } from 'typeorm';

export async function cleanDatabase(dataSource: DataSource): Promise<void> {
  const tables = dataSource.entityMetadatas.map((e) => dataSource.driver.escape(e.tableName));
  if (dataSource.options.type === 'postgres') {
    await dataSource.query(`TRUNCATE TABLE ${tables.join(', ')} CASCADE`);
    return;
  }
  // MySQL has no TRUNCATE ... CASCADE. FOREIGN_KEY_CHECKS is per connection,
  // so every statement runs on the same QueryRunner.
  const runner = dataSource.createQueryRunner();
  try {
    await runner.query('SET FOREIGN_KEY_CHECKS = 0');
    for (const table of tables) await runner.query(`TRUNCATE TABLE ${table}`);
  } finally {
    await runner.query('SET FOREIGN_KEY_CHECKS = 1');
    await runner.release();
  }
}
```

```ts
// test/helpers/test-db-setup.ts — Prisma on PostgreSQL: no entity metadata, read table names from the catalog
export async function cleanDatabase(prisma: PrismaService): Promise<void> {
  const tables = await prisma.$queryRaw<{ tablename: string }[]>`
    SELECT tablename FROM pg_tables
    WHERE schemaname = current_schema() AND tablename <> '_prisma_migrations'`;
  if (tables.length === 0) return;
  // Table names come from the catalog, not from user input
  const names = tables.map(({ tablename }) => `"${tablename}"`).join(', ');
  await prisma.$executeRawUnsafe(`TRUNCATE TABLE ${names} CASCADE`);
}
```

```ts
// test/helpers/test-db-setup.ts — Prisma on MySQL: FOREIGN_KEY_CHECKS is per connection,
// so every statement runs in one interactive transaction (one connection)
export async function cleanDatabase(prisma: PrismaService): Promise<void> {
  await prisma.$transaction(async (tx) => {
    const tables = await tx.$queryRaw<{ name: string }[]>`
      SELECT table_name AS name FROM information_schema.tables
      WHERE table_schema = DATABASE() AND table_type = 'BASE TABLE'
        AND table_name <> '_prisma_migrations'`;
    await tx.$executeRawUnsafe('SET FOREIGN_KEY_CHECKS = 0');
    try {
      // Table names come from the catalog, not from user input
      for (const { name } of tables) await tx.$executeRawUnsafe(`TRUNCATE TABLE \`${name}\``);
    } finally {
      await tx.$executeRawUnsafe('SET FOREIGN_KEY_CHECKS = 1');
    }
  });
}
```

---

## References

- [NestJS Testing docs](https://docs.nestjs.com/fundamentals/testing) — Official guide cho unit, integration, e2e test
- [Jest Documentation](https://jestjs.io/docs/getting-started) — API reference, matchers, mocking
- [NestJS Testing utilities](https://docs.nestjs.com/fundamentals/testing#testing-utilities) — `Test.createTestingModule`, overrides
- [Supertest](https://github.com/ladjs/supertest) — HTTP assertions cho e2e test
- [Testing best practices (Node.js)](https://github.com/goldbergyoni/nodebestpractices#4-testing-and-overall-quality-practices) — Yoni Goldberg’s Node.js best practices
- [Jest Mock Functions](https://jestjs.io/docs/mock-functions) — `jest.fn()`, `jest.spyOn()`, mock implementations
- [Nock](https://github.com/nock/nock) — HTTP server mocking for Node.js
- [MSW (Mock Service Worker)](https://mswjs.io/) — API mocking library

## Changelog

| Date | Version | Change | By |
| :---- | :---- | :---- | :---- |
| 2026-11-18 | v1.0 | Chuyển từ Notion "NestJS Document" (page `33d71a38d3b28102a524e423ad2c3ce9`, sửa 2026-04-09). Review và sửa nội dung, code trước khi publish. Owner duyệt trong chat ngày 2026-11-18. | Bắc PV |
