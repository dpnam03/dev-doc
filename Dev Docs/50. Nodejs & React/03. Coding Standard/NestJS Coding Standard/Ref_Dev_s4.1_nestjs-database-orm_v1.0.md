# NestJS Coding Standard 4.1 — Database & ORM

| Field | Value |
| :---- | :---- |
| Owner | Bắc PV — NodeJS BE Dev Lead |
| Audience | Dev (NodeJS BE) |
| Last reviewed | 2026-11-12 |
| Review cadence | Quarterly |
| Version | v1.0 |
| Linked from | Ref_Dev_nestjs-coding-standard_v1.0 |
| Status | Live |

Doc này là mục 4.1 của [NestJS Coding Standard](Ref_Dev_nestjs-coding-standard_v1.0.md), nhóm Database. Doc nêu quy tắc về Database & ORM trong dự án NestJS, kèm lý do, ví dụ và config. Dev NodeJS BE đọc doc này khi viết code, review code và onboarding.

---

## 1. Tóm tắt & Phạm vi

> 📌 **Chủ đề**: Database & ORM trong NestJS — cách tổ chức code truy vấn DB, quản lý schema, tối ưu hiệu năng, và đảm bảo data integrity trong dự án thực tế.

- **Vấn đề giải quyết**: Thống nhất cách team tương tác với database — từ chọn ORM, tổ chức repository/service, quản lý migration, transaction, đến tối ưu query và connection pool.
- **Scope áp dụng**: Tất cả các module/service có tương tác với database (PostgreSQL, MySQL). Áp dụng cho cả TypeORM và Prisma.
- **Tại sao quan trọng**:
- Database là “single source of truth” — sai ở đây ảnh hưởng toàn bộ hệ thống.
- Code DB không chuẩn dẫn đến N+1 query, lock lâu, data inconsistency — khó debug, tốn chi phí sửa.
- Team cần chung convention để review code DB hiệu quả và onboard member mới nhanh.

---

## 2. Quy tắc & Giải thích

### 2.1. Chọn cách làm việc với DB

> ✅ **Đề xuất**: Dùng ORM (Prisma hoặc TypeORM) làm mặc định cho 80–90% use cases. Dùng raw SQL/query builder cho 10–20% trường hợp phức tạp.

**So sánh ORM vs Raw SQL:**

| Tiêu chí | ORM (Prisma/TypeORM) | Raw SQL / Query Builder |
| --- | --- | --- |
| Type safety | ✅ Auto-generated types từ schema | ❌ Phải tự define types |
| Migration | ✅ Built-in, có lịch sử. Revert: TypeORM có, Prisma không (mục 4.3) | ⚠️ Phải dùng tool riêng (Flyway, Liquibase) |
| Complex query | ⚠️ Hạn chế với multi-join, aggregate | ✅ Linh hoạt, tối ưu được |
| Performance tuning | ⚠️ Khó kiểm soát generated SQL | ✅ Full control |
| Reviewer-friendly | ✅ Schema ở code, dễ review PR | ⚠️ SQL strings khó review |

**Tại sao mix approach?**

- ORM handle tốt CRUD, relations, migrations — chiếm phần lớn code.
- Nhưng reporting/dashboard queries với nhiều JOIN/aggregate — ORM sinh SQL kém tối ưu, raw SQL cho phép control execution plan.

**Lưu ý khi dùng ORM:**

- Tránh lạm dụng **lazy loading** — gây N+1 query mà không biết.
- Tắt **cascade delete/update** mặc định — chỉ bật khi business yêu cầu rõ ràng.
- Luôn **log generated SQL** trong development để kiểm tra query ORM sinh ra.

> Tham khảo: [Prisma Docs](https://www.prisma.io/docs), [TypeORM Docs](https://typeorm.io/)

### 2.2. Tổ chức code: Repository & Service Pattern

> ✅ **Đề xuất**: Tách riêng Repository (data access) và Service (business logic). Service KHÔNG chứa SQL/ORM call trực tiếp.

**Tại sao tách?**

- **Testability**: Mock repository trong unit test — không cần DB thật.
- **Swappability**: Đổi ORM/DB engine — chỉ đổi repository implementation, service giữ nguyên API.
- **Readability**: Reviewer biết rõ “chỗ này là data access” vs “chỗ này là business logic”.

**Quy tắc:**

- ✅ **NÊN**: Repository chỉ chứa CRUD operations + custom queries. Mỗi entity có 1 repository.
- ✅ **NÊN**: Service inject repository, orchestrate business logic, gọi repository methods.
- ❌ **KHÔNG NÊN**: Service chứa `this.dataSource.query(...)`, `this.repo.createQueryBuilder(...)` hoặc `this.prisma.order.findMany(...)` trực tiếp.
- ❌ **KHÔNG NÊN**: Repository chứa business logic (validate, calculate, transform).

```ts
// orders.repository.ts — chỉ data access
@Injectable()
export class OrdersRepository {
  constructor(
    @InjectRepository(Order)
    private readonly repo: Repository<Order>,
  ) {}

  async findById(id: string): Promise<Order | null> {
    return this.repo.findOne({
      where: { id },
      relations: ['items', 'customer'],
    });
  }

  async findPendingOrders(customerId: string): Promise<Order[]> {
    return this.repo.find({
      where: { customerId, status: OrderStatus.PENDING },
      order: { createdAt: 'DESC' },
    });
  }

  async save(order: Order): Promise<Order> {
    return this.repo.save(order);
  }
}
```

Project dùng Prisma inject `PrismaService` (mục 2.7) thay cho `Repository<Order>`. Giữ cùng tên method thì service không phải sửa.

```ts
// orders.repository.ts — Prisma
import { Order, OrderStatus, Prisma } from '../generated/prisma/client'; // generator `output` in schema.prisma (section 4.2)

@Injectable()
export class OrdersRepository {
  constructor(private readonly prisma: PrismaService) {}

  async findById(id: string) {
    return this.prisma.order.findUnique({
      where: { id },
      include: { items: true, customer: true },
    });
  }

  async findPendingOrders(customerId: string): Promise<Order[]> {
    return this.prisma.order.findMany({
      where: { customerId, status: OrderStatus.PENDING },
      orderBy: { createdAt: 'desc' },
    });
  }

  async save(data: Prisma.OrderUncheckedCreateInput): Promise<Order> {
    return this.prisma.order.create({ data });
  }
}
```

```ts
// orders.service.ts — business logic, inject repository
@Injectable()
export class OrdersService {
  constructor(
    private readonly ordersRepo: OrdersRepository,
    private readonly inventoryService: InventoryService,
  ) {}

  async create(dto: CreateOrderDto): Promise<Order> {
    // Business logic: validate stock
    await this.inventoryService.validateStock(dto.items);

    // Map DTO -> entity
    const order = this.mapToEntity(dto);

    // Persist via repository
    return this.ordersRepo.save(order);
  }
}
```

### 2.3. Parameterized Queries & Prisma Client Extensions

> ✅ **Đề xuất**: Raw query luôn truyền giá trị qua parameter, không nối chuỗi. Prisma v7 dùng `Prisma.sql` template tag (auto-parameterized). TypeORM dùng placeholder (`$1`, MySQL là `?`) hoặc named parameter của QueryBuilder. Với Prisma, dùng `$extends()` cho reusable custom methods.

**Parameterized queries với `Prisma.sql` template tag:**

```ts
import { Prisma } from '../generated/prisma/client'; // generator `output` in schema.prisma (section 4.2)

// ✅ Good — variables tự động được parameterized
async findByName(name: string) {
  return this.prisma.$queryRaw(Prisma.sql`SELECT * FROM users WHERE name = ${name}`);
}

// ✅ Good — Interactive transaction với async callback
async transfer(fromId: string, toId: string, amount: number) {
  return this.prisma.$transaction(async (tx) => {
    await tx.account.update({
      where: { id: fromId },
      data: { balance: { decrement: amount } },
    });
    await tx.account.update({
      where: { id: toId },
      data: { balance: { increment: amount } },
    });
  });
}
```

**TypeORM — placeholder hoặc named parameter:**

```ts
// ✅ Good — the value goes in a separate array, not into the SQL string
async findByName(name: string) {
  return this.dataSource.query('SELECT * FROM users WHERE name = $1', [name]); // MySQL: ? instead of $1
}

// ✅ Good — QueryBuilder with a named parameter
async findByEmail(email: string) {
  return this.usersRepo
    .createQueryBuilder('user')
    .where('user.email = :email', { email })
    .getOne();
}
```

**❌ KHÔNG NÊN:**

```ts
// ❌ Bad — string concatenation = SQL injection!
async findByName(name: string) {
  return this.prisma.$queryRawUnsafe(`SELECT * FROM users WHERE name = '${name}'`);
}

// ❌ Bad — string interpolation trong $queryRaw
async findByEmail(email: string) {
  return this.prisma.$queryRaw(`SELECT * FROM users WHERE email = '${email}'`);
}

// ❌ Bad — TypeORM: string interpolation in query() and in where()
async findByName(name: string) {
  return this.dataSource.query(`SELECT * FROM users WHERE name = '${name}'`);
}
async findByEmail(email: string) {
  return this.usersRepo.createQueryBuilder('user').where(`user.email = '${email}'`).getOne();
}
```

**Client Extensions (`$extends`)** cho reusable query patterns:

```ts
// Prisma 7: PrismaClient requires a driver adapter
const adapter = new PrismaPg({ connectionString: process.env.DATABASE_URL });
const prisma = new PrismaClient({ adapter }).$extends({
  model: {
    user: {
      async findByEmail(email: string) {
        return prisma.user.findUnique({ where: { email } });
      },
      async findActive() {
        return prisma.user.findMany({ where: { status: 'ACTIVE' } });
      },
    },
  },
});

// Sử dụng
const user = await prisma.user.findByEmail('user@example.com');
```

*Tại sao:* `Prisma.sql` template tag tự động parameterize variables, loại bỏ hoàn toàn risk SQL injection mà không cần escape thủ công. `$extends()` cho phép thêm custom methods vào Prisma Client mà không cần wrapper class.

> **Tham khảo:** [Prisma Raw Queries](https://www.prisma.io/docs/concepts/components/prisma-client/raw-database-access) · [Prisma Client Extensions](https://www.prisma.io/docs/concepts/components/prisma-client/client-extensions)

---

### 2.4. Migration & Version hóa schema

> ⚠️ **Nguyên tắc cốt lõi**: Mọi thay đổi schema DB PHẢI đi qua migration file, được review trong PR, và chạy qua CI/CD. Không chỉnh schema trực tiếp bằng GUI/CLI trên bất kỳ môi trường nào.

**Quy tắc:**

- ✅ **NÊN**: Mỗi thay đổi schema = 1 migration file riêng, có tên mô tả rõ (`add-column-order-discount`, `create-index-user-email`).
- ✅ **NÊN**: Review migration trong PR — đặc biệt chú ý `DROP`, `ALTER` trên bảng lớn.
- ✅ **NÊN**: Test migration trên staging trước khi chạy production.
- ✅ **NÊN**: Tách migration “nặng” thành nhiều bước:

1. Add cột mới (nullable) — migration chạy trước khi deploy code mới
2. Backfill data dần (batch)
3. Switch application code sang cột mới — deploy code
4. Drop cột cũ — migration ở release sau, khi không còn instance chạy code cũ

Thứ tự deploy theo các bước này ở [NestJS Coding Standard 9.3 — Build & Deployment](Ref_Dev_s9.3_nestjs-build-deployment_v1.0.md) mục 2.8.

- ❌ **KHÔNG NÊN**: Chạy migration nặng (full table rewrite, add index on large table) vào giờ cao điểm.
- ❌ **KHÔNG NÊN**: Dùng `synchronize: true` trong production — TypeORM sẽ auto-alter schema, gây mất data.

**Tools:**

- Prisma: `migrate dev` chỉ chạy local; staging và production chạy `migrate deploy`, lệnh này không reset DB.
- Prisma: migration thêm `NOT NULL`, unique, foreign key phải kèm SQL sửa dữ liệu cũ.
- TypeORM: `typeorm migration:generate`, `typeorm migration:run`

> Tham khảo: [Prisma Migrate](https://www.prisma.io/docs/concepts/components/prisma-migrate), [TypeORM Migrations](https://typeorm.io/migrations)

### 2.5. Transaction — khi nào và cách dùng

> ✅ **Đề xuất**: Dùng transaction khi 1 use case gồm nhiều thao tác DB phải atomic (cùng thành công hoặc cùng rollback).

**Khi nào cần transaction?**

- Tạo order + trừ tồn kho.
- Tạo user + tạo profile + tạo audit record.
- Transfer tiền giữa 2 tài khoản.

**Quy tắc:**

- ✅ **NÊN**: Mọi thao tác DB trong 1 use case dùng chung 1 transaction.
- ✅ **NÊN**: Giữ transaction ngắn — chỉ chứa DB operations.
- ❌ **KHÔNG NÊN**: Gọi HTTP/external API **bên trong** transaction — nếu API chậm/fail, transaction giữ lock quá lâu → deadlock risk.
- ❌ **KHÔNG NÊN**: Transaction quá dài (nhiều logic) — dễ gây lock escalation.

**Pattern đúng:**

```ts
// ✅ Good — transaction chỉ chứa DB operations
async createOrder(dto: CreateOrderDto): Promise<Order> {
  // 1. Validate NGOÀI transaction (gọi external nếu cần)
  await this.paymentGateway.validateCard(dto.cardToken);
  const total = await this.pricingService.calculateTotal(dto.items); // Read prices before the transaction

  // 2. Transaction chỉ chứa DB writes
  const order = await this.prisma.$transaction(async (tx) => {
    // status is omitted: the schema default is PENDING (section 4.2)
    const order = await tx.order.create({
      data: { customerId: dto.customerId, total },
    });
    for (const item of dto.items) {
      // Check and decrement in one UPDATE, so concurrent orders cannot oversell
      const { count } = await tx.inventory.updateMany({
        where: { productId: item.productId, stock: { gte: item.quantity } },
        data: { stock: { decrement: item.quantity } },
      });
      if (count === 0) {
        // Throwing inside $transaction rolls back the order as well
        throw new BadRequestException(`Insufficient stock for: ${item.productId}`);
      }
    }
    return order;
  });

  // 3. Side effects SAU transaction (fire-and-forget)
  this.eventEmitter.emit('order.created', order);
  return order;
}
```

**Cùng pattern với TypeORM:**

```ts
// ✅ Good — TypeORM: same flow with dataSource.transaction()
async createOrder(dto: CreateOrderDto): Promise<Order> {
  await this.paymentGateway.validateCard(dto.cardToken);
  const total = await this.pricingService.calculateTotal(dto.items);

  const order = await this.dataSource.transaction(async (manager) => {
    const order = await manager.save(Order, {
      customerId: dto.customerId,
      status: OrderStatus.PENDING,
      total,
    });
    for (const item of dto.items) {
      // Check and decrement in one UPDATE, so concurrent orders cannot oversell
      const result = await manager.decrement(
        Inventory,
        { productId: item.productId, stock: MoreThanOrEqual(item.quantity) },
        'stock',
        item.quantity,
      );
      if (result.affected === 0) {
        // Throwing inside dataSource.transaction() rolls back the order as well
        throw new BadRequestException(`Insufficient stock for: ${item.productId}`);
      }
    }
    return order;
  });

  this.eventEmitter.emit('order.created', order);
  return order;
}
```

**Isolation level, row lock và retry:**

- ✅ **NÊN**: Đọc rồi update theo điều kiện thì khoá dòng bằng `SELECT ... FOR UPDATE` (TypeORM `lock: { mode: 'pessimistic_write' }`).
- ✅ **NÊN**: Rule phụ thuộc nhiều dòng (số dư ≥ 0) thì dùng `Serializable` và retry lỗi `P2034` (PostgreSQL `40001`, MySQL `1213`).

```ts
import { setTimeout } from 'node:timers/promises';

// Serializable for invariants such as balance ≥ 0; the DB aborts one of two conflicting transactions
async function withdraw(id: number, amount: number): Promise<void> {
  for (let attempt = 1; ; attempt++) {
    try {
      await prisma.$transaction(
        async (tx) => {
          const account = await tx.account.findUniqueOrThrow({ where: { id } });
          if (account.balance < amount) {
            throw new BadRequestException({ type: 'DOMAIN_ERROR', code: 'INSUFFICIENT_BALANCE', message: `Account ${id} balance is below ${amount}` });
          }
          await tx.account.update({ where: { id }, data: { balance: account.balance - amount } });
        },
        { isolationLevel: Prisma.TransactionIsolationLevel.Serializable },
      );
      return;
    } catch (error) {
      // P2034: write conflict or deadlock (PostgreSQL 40001, MySQL 1213) — safe to run the transaction again
      const retryable = error instanceof Prisma.PrismaClientKnownRequestError && error.code === 'P2034';
      if (!retryable || attempt === 3) throw error;
      await setTimeout(50 * attempt + Math.random() * 50);
    }
  }
}
```

**Pattern sai:**

```ts
// ❌ Bad — gọi HTTP bên trong transaction
await this.prisma.$transaction(async (tx) => {
  const order = await tx.order.create({ ... });
  // External call giữ transaction lock nếu chậm/timeout!
  await this.paymentGateway.charge(order.total);
  await tx.inventory.decrease({ ... });
});
```

### 2.6. Index & Query Performance

**Quy tắc index:**

- ✅ **NÊN** index: Foreign keys (`user_id`, `order_id`), fields trong `WHERE`, `JOIN`, `ORDER BY`.
- ✅ **NÊN**: Composite index cho queries thường filter nhiều field cùng lúc (column order matters — đặt selectivity cao trước).
- ❌ **KHÔNG NÊN**: Index quá nhiều — mỗi index tốn RAM + làm chậm `INSERT/UPDATE/DELETE`.
- ❌ **KHÔNG NÊN**: Index trên columns hiếm khi query.

**Tránh N+1 Query:**

N+1 là lỗi phổ biến nhất khi dùng ORM:

```ts
// ❌ Bad — N+1: 1 query lấy orders + N queries lấy user cho mỗi order
const orders = await this.ordersRepo.find();
for (const order of orders) {
  order.user = await this.usersRepo.findOne({ where: { id: order.userId } });
}

// ✅ Good — Eager load 1 lần
const orders = await this.ordersRepo.find({
  relations: ['user'],
});

// ✅ Good — Hoặc dùng QueryBuilder cho complex cases
const orders = await this.ordersRepo
  .createQueryBuilder('order')
  .leftJoinAndSelect('order.user', 'user')
  .where('order.status = :status', { status: 'pending' })
  .getMany();
```

Prisma: `include` lấy relation trong cùng lệnh. Prisma chạy 2 query: bảng chính, rồi bảng relation theo `IN`.

```ts
// ✅ Good — Prisma: include loads the relation, 2 queries in total
const orders = await this.prisma.order.findMany({
  include: { customer: true },
});
```

**Pagination — luôn phải có:**

- ✅ **NÊN**: Cursor-based pagination cho data thay đổi thường xuyên (feeds, timelines).
- ✅ **NÊN**: Offset-based (`LIMIT/OFFSET`) cho admin dashboards, reports.
- ✅ **NÊN**: Cursor gồm `(createdAt, id)`, không chỉ `createdAt`: cursor chỉ có `createdAt` bỏ sót các row trùng timestamp. Cột `createdAt` lưu precision millisecond (`@CreateDateColumn({ precision: 3 })`), vì JS `Date` cắt mất microsecond. Trên MySQL thêm `default: () => 'CURRENT_TIMESTAMP(3)'`, nếu không TypeORM sinh `DEFAULT CURRENT_TIMESTAMP(6)` và MySQL báo `Invalid default value`. Prisma `DateTime` mặc định đã là precision 3 (`TIMESTAMP(3)`, MySQL `DATETIME(3)`).
- ❌ **KHÔNG BAO GIỜ**: Trả toàn bộ bảng trong 1 request.

```ts
// Cursor-based pagination — cursor = (createdAt, id) of the last row, base64url-encoded
// Same { data, meta } shape as PaginatedResult (1.5 section 2.6), with cursor meta
interface CursorPage<T> {
  data: T[];
  meta: { hasMore: boolean; nextCursor?: string };
}

const encodeCursor = (o: Order) =>
  Buffer.from(JSON.stringify([o.createdAt.toISOString(), o.id])).toString('base64url');
const decodeCursor = (cursor: string) => {
  const [createdAt, id] = JSON.parse(Buffer.from(cursor, 'base64url').toString()) as [string, string];
  return { createdAt: new Date(createdAt), id };
};

async findAll(cursor?: string, limit = 20): Promise<CursorPage<Order>> {
  const qb = this.ordersRepo
    .createQueryBuilder('order')
    .orderBy('order.createdAt', 'DESC')
    .addOrderBy('order.id', 'DESC') // Tie-breaker: rows sharing a createdAt keep a fixed order
    .take(limit + 1); // Lấy thêm 1 để check hasMore

  if (cursor) {
    const { createdAt, id } = decodeCursor(cursor);
    qb.where(
      '(order.createdAt < :createdAt OR (order.createdAt = :createdAt AND order.id < :id))',
      { createdAt, id },
    );
  }

  const items = await qb.getMany();
  const hasMore = items.length > limit;
  if (hasMore) items.pop();

  const last = items.at(-1);
  return {
    data: items,
    meta: { hasMore, nextCursor: last ? encodeCursor(last) : undefined },
  };
}
```

Prisma, cùng cursor và cùng thứ tự sắp xếp:

```ts
// Prisma — CursorPage, encodeCursor and decodeCursor as above
async findAll(cursor?: string, limit = 20): Promise<CursorPage<Order>> {
  const after = cursor ? decodeCursor(cursor) : undefined;
  const items = await this.prisma.order.findMany({
    where: after
      ? {
          OR: [
            { createdAt: { lt: after.createdAt } },
            { createdAt: after.createdAt, id: { lt: after.id } },
          ],
        }
      : undefined,
    orderBy: [{ createdAt: 'desc' }, { id: 'desc' }], // id breaks ties, as in the TypeORM version
    take: limit + 1, // One extra row tells whether there is a next page
  });

  const hasMore = items.length > limit;
  if (hasMore) items.pop();

  const last = items.at(-1);
  return {
    data: items,
    meta: { hasMore, nextCursor: last ? encodeCursor(last) : undefined },
  };
}
```

### 2.7. Connection Pool

> ⚠️ **Nguyên tắc**: DB (PostgreSQL/MySQL) chỉ chịu được số lượng connection nhất định. Phải cấu hình pool hợp lý và reuse.

**Quy tắc:**

- ✅ **NÊN**: Cấu hình pool size hợp lý (10–30 tùy app/infra).
- ✅ **NÊN**: Dùng **singleton module** cho DB connection (Global module trong NestJS).
- ❌ **KHÔNG NÊN**: Tạo `new PrismaClient()` hoặc `createConnection()` trong mỗi request.
- ❌ **KHÔNG NÊN**: Để pool size mặc định mà không monitor.

```ts
import { PrismaPg } from '@prisma/adapter-pg';
import { PrismaClient } from '../generated/prisma/client'; // generator `output` in schema.prisma (section 4.2)

// ✅ Good — PrismaService singleton, reuse across app
@Global()
@Module({
  providers: [PrismaService],
  exports: [PrismaService],
})
export class DatabaseModule {}

@Injectable()
export class PrismaService extends PrismaClient implements OnModuleInit {
  constructor(config: ConfigService) {
    // Prisma 7 requires a driver adapter
    super({ adapter: new PrismaPg({ connectionString: config.getOrThrow<string>('DATABASE_URL') }) });
    // MySQL: { adapter: new PrismaMariaDb(url) } from '@prisma/adapter-mariadb', DATABASE_URL=mysql://...
  }

  async onModuleInit() {
    await this.$connect();
  }
}
```

TypeORM: `TypeOrmModule.forRootAsync` (mục 4.1) tạo một connection pool dùng chung cho cả app. Pool size đặt ở `poolSize`, TypeORM chuyển thành `max` của pg hoặc `connectionLimit` của mysql2.

### 2.8. Data Integrity & Validation

> ✅ **Đề xuất**: Validate ở 3 lớp: DTO (format), Service (business rule), Database (constraint). DB là “cổng cuối” bảo vệ dữ liệu.

**Quy tắc:**

- ✅ **NÊN**: DTO + `class-validator` validate format ở HTTP layer.
- ✅ **NÊN**: Service validate business rules (trạng thái, giới hạn, quyền).
- ✅ **NÊN**: DB constraints: `NOT NULL`, `UNIQUE`, `FOREIGN KEY`, `CHECK` — phòng trường hợp bypass API.
- ❌ **KHÔNG NÊN**: Tin hoàn toàn vào API validation — data có thể vào DB qua migration, script, direct access.
- ❌ **KHÔNG NÊN**: Lưu tiền bằng `Float`/`FLOAT` — `0.1 + 0.2` ra `0.30000000000000004`. Dùng `DECIMAL(19, 4)` (Prisma `Decimal @db.Decimal(19, 4)`) hoặc số nguyên theo đơn vị nhỏ nhất.

### 2.9. Backup & Restore

**Quy tắc:**

- ✅ **NÊN**: Backup tự động hằng ngày (full) + incremental.
- ✅ **NÊN**: **Test restore định kỳ** — backup không có giá trị nếu không restore được.
- ✅ **NÊN**: Dùng audit table/log để xác định records bị ảnh hưởng khi có bug production.
- ✅ **NÊN**: Viết script sửa data có targeted thay vì rollback cả DB.

---

## 3. Ví dụ minh họa thực tế

### 3.1. Walkthrough: Feature “Tạo đơn hàng” — từ Controller đến DB

Giả sử team cần implement feature tạo đơn hàng với yêu cầu:

- Validate input
- Kiểm tra tồn kho
- Tạo order + order items trong 1 transaction
- Trừ tồn kho

**Bước 1: DTO — validate format**

```ts
// dto/create-order.dto.ts
export class CreateOrderDto {
  @IsString() @IsNotEmpty()
  customerId: string;

  @ValidateNested({ each: true })
  @Type(() => OrderItemDto)
  @ArrayMinSize(1)
  items: OrderItemDto[];
}

export class OrderItemDto {
  @IsString() productId: string;
  @IsInt() @Min(1) quantity: number;
}
```

**Bước 2: Repository — data access**

```ts
// orders.repository.ts
@Injectable()
export class OrdersRepository {
  constructor(
    @InjectRepository(Order)
    private readonly repo: Repository<Order>,
  ) {}

  async createWithItems(
    manager: EntityManager, // Nhận manager từ transaction
    order: Partial<Order>,
    items: Partial<OrderItem>[],
  ): Promise<Order> {
    const savedOrder = await manager.save(Order, order);
    const orderItems = items.map((item) => ({
      ...item,
      orderId: savedOrder.id,
    }));
    await manager.save(OrderItem, orderItems);
    return savedOrder;
  }
}

// inventory.repository.ts
@Injectable()
export class InventoryRepository {
  // Check and decrement in one UPDATE: returns false when stock < quantity
  async decrementStock(
    manager: EntityManager,
    productId: string,
    quantity: number,
  ): Promise<boolean> {
    const result = await manager.decrement(
      Inventory,
      { productId, stock: MoreThanOrEqual(quantity) },
      'stock',
      quantity,
    );
    return result.affected === 1;
  }
}
```

**Bước 3: Service — business logic + transaction**

```ts
// orders.service.ts
@Injectable()
export class OrdersService {
  constructor(
    private readonly ordersRepo: OrdersRepository,
    private readonly inventoryService: InventoryService,
    private readonly dataSource: DataSource,
  ) {}

  async create(dto: CreateOrderDto): Promise<Order> {
    // Transaction — chỉ DB operations
    return this.dataSource.transaction(async (manager) => {
      const order = await this.ordersRepo.createWithItems(
        manager,
        { customerId: dto.customerId, status: OrderStatus.PENDING },
        dto.items,
      );

      // Stock check happens here, inside the transaction, not before it
      await this.inventoryService.decreaseStock(manager, dto.items);

      return order;
    });
  }
}

// inventory.service.ts
@Injectable()
export class InventoryService {
  constructor(private readonly inventoryRepo: InventoryRepository) {}

  async decreaseStock(manager: EntityManager, items: OrderItemDto[]): Promise<void> {
    for (const item of items) {
      const ok = await this.inventoryRepo.decrementStock(manager, item.productId, item.quantity);
      if (!ok) {
        // Throwing inside dataSource.transaction() rolls back the whole order
        throw new BadRequestException(`Insufficient stock for: ${item.productId}`);
      }
    }
  }
}
```

**Bước 2–3 với Prisma:** repository nhận `Prisma.TransactionClient` thay cho `EntityManager`. Service dùng `prisma.$transaction()` thay cho `dataSource.transaction()`. Schema ở mục 4.2 bắt buộc `total`, nên service đọc giá trước transaction như mục 2.5.

```ts
// orders.repository.ts — Prisma
import { Order, Prisma } from '../generated/prisma/client';

@Injectable()
export class OrdersRepository {
  async createWithItems(
    tx: Prisma.TransactionClient, // Received from prisma.$transaction()
    order: Pick<Prisma.OrderUncheckedCreateInput, 'customerId' | 'total'>,
    items: OrderItemDto[],
  ): Promise<Order> {
    // Nested create: the order and its items in one call
    return tx.order.create({
      data: { ...order, items: { create: items } },
    });
  }
}

// inventory.repository.ts — Prisma
@Injectable()
export class InventoryRepository {
  // Check and decrement in one UPDATE: returns false when stock < quantity
  async decrementStock(
    tx: Prisma.TransactionClient,
    productId: string,
    quantity: number,
  ): Promise<boolean> {
    const { count } = await tx.inventory.updateMany({
      where: { productId, stock: { gte: quantity } },
      data: { stock: { decrement: quantity } },
    });
    return count === 1;
  }
}
```

```ts
// orders.service.ts — Prisma
@Injectable()
export class OrdersService {
  constructor(
    private readonly ordersRepo: OrdersRepository,
    private readonly inventoryService: InventoryService,
    private readonly pricingService: PricingService,
    private readonly prisma: PrismaService,
  ) {}

  async create(dto: CreateOrderDto): Promise<Order> {
    // total is required by the Prisma schema (section 4.2); read prices before the transaction
    const total = await this.pricingService.calculateTotal(dto.items);

    return this.prisma.$transaction(async (tx) => {
      const order = await this.ordersRepo.createWithItems(
        tx,
        { customerId: dto.customerId, total },
        dto.items,
      );

      // Stock check happens here, inside the transaction, not before it
      await this.inventoryService.decreaseStock(tx, dto.items);

      return order;
    });
  }
}

// inventory.service.ts — Prisma: same logic, tx instead of manager
@Injectable()
export class InventoryService {
  constructor(private readonly inventoryRepo: InventoryRepository) {}

  async decreaseStock(tx: Prisma.TransactionClient, items: OrderItemDto[]): Promise<void> {
    for (const item of items) {
      const ok = await this.inventoryRepo.decrementStock(tx, item.productId, item.quantity);
      if (!ok) {
        // Throwing inside $transaction() rolls back the whole order
        throw new BadRequestException(`Insufficient stock for: ${item.productId}`);
      }
    }
  }
}
```

**Bước 4: Controller — chỉ delegate**

```ts
// orders.controller.ts
@ApiTags('orders')
@Controller('orders')
export class OrdersController {
  constructor(private readonly ordersService: OrdersService) {}

  @Post()
  @ApiOperation({ summary: 'Tạo đơn hàng mới' })
  @ApiCreatedResponse({ type: OrderResponseDto })
  async create(@Body() dto: CreateOrderDto): Promise<OrderResponseDto> {
    const order = await this.ordersService.create(dto);
    return plainToInstance(OrderResponseDto, order, {
      excludeExtraneousValues: true,
    });
  }
}
```

### 3.2. Before / After: Sửa N+1 Query

**Before — N+1 problem:**

```ts
// ❌ 1 query lấy 100 orders + 100 queries lấy customer
async getOrderReport(): Promise<OrderReport[]> {
  const orders = await this.ordersRepo.find({ where: { status: 'completed' } });

  return Promise.all(
    orders.map(async (order) => {
      const customer = await this.customersRepo.findOne({
        where: { id: order.customerId },
      });
      return { orderId: order.id, customerName: customer.name, total: order.total };
    }),
  );
}
// Kết quả: 101 queries cho 100 orders → chậm, tốn connection pool
```

**After — Single query với JOIN:**

```ts
// ✅ 1 query duy nhất với JOIN
async getOrderReport(): Promise<OrderReport[]> {
  return this.ordersRepo
    .createQueryBuilder('order')
    .leftJoin('order.customer', 'customer')
    .select(['order.id', 'customer.name', 'order.total'])
    .where('order.status = :status', { status: 'completed' })
    .getRawMany();
}
// Kết quả: 1 query cho 100 orders → nhanh, tiết kiệm resources
```

**After với Prisma** — `select` lồng relation, Prisma chạy 2 query thay vì 101:

```ts
// ✅ 2 queries: orders, then customers WHERE id IN (...)
async getOrderReport(): Promise<OrderReport[]> {
  const orders = await this.prisma.order.findMany({
    where: { status: OrderStatus.COMPLETED },
    select: { id: true, total: true, customer: { select: { name: true } } },
  });
  return orders.map((o) => ({
    orderId: o.id,
    customerName: o.customer.name,
    total: o.total.toNumber(), // Decimal -> number
  }));
}
```

---

## 4. Tooling & Config

### 4.1. TypeORM Setup trong NestJS

```ts
// app.module.ts
@Module({
  imports: [
    TypeOrmModule.forRootAsync({
      imports: [ConfigModule],
      inject: [ConfigService],
      useFactory: (config: ConfigService) => ({
        type: 'postgres', // MySQL: 'mysql' (pnpm add mysql2)
        host: config.getOrThrow('database.host'),
        port: config.getOrThrow<number>('database.port'),
        username: config.getOrThrow('database.username'),
        password: config.getOrThrow('database.password'),
        database: config.getOrThrow('database.name'),
        autoLoadEntities: true,
        synchronize: false, // ⚠️ LUÔN false ở production
        logging: config.get('NODE_ENV') === 'development',
        poolSize: 20, // pg "max" / mysql2 "connectionLimit"
        extra: {
          idleTimeoutMillis: 30000, // pg option; mysql2 uses idleTimeout
        },
      }),
    }),
  ],
})
export class AppModule {}
```

### 4.2. Prisma Setup trong NestJS

```ts
// prisma/schema.prisma
generator client {
  provider = "prisma-client"
  output   = "../src/generated/prisma" // import from '<output>/client'
}

datasource db {
  provider = "postgresql" // MySQL: "mysql" + @prisma/adapter-mariadb
}

model Order {
  id         String      @id @default(uuid())
  customerId String      @map("customer_id")
  status     OrderStatus @default(PENDING)
  total      Decimal     @db.Decimal(10, 2)
  createdAt  DateTime    @default(now()) @map("created_at")
  updatedAt  DateTime    @updatedAt @map("updated_at")

  customer Customer  @relation(fields: [customerId], references: [id])
  items    OrderItem[]

  @@index([customerId])
  @@index([status, createdAt])
  @@map("orders")
}
```

Prisma 7 không nhận `url` trong `datasource`: CLI đọc URL từ `prisma.config.ts`, runtime nhận URL qua driver adapter (mục 2.7). Với NestJS 11, thêm `prisma.config.ts` vào `exclude` của `tsconfig.build.json`, nếu không `nest build` ra `dist/src/main.js`.

```ts
// prisma.config.ts (project root)
import 'dotenv/config'; // Prisma 7 CLI does not load .env by itself
import { defineConfig } from 'prisma/config';

export default defineConfig({
  schema: 'prisma/schema.prisma',
  migrations: { path: 'prisma/migrations' },
  datasource: { url: process.env.DATABASE_URL },
});
```

```bash
pnpm add @prisma/client @prisma/adapter-pg   # MySQL: @prisma/adapter-mariadb
pnpm add -D prisma dotenv
```

### 4.3. Migration commands

```bash
# TypeORM
pnpm typeorm migration:generate src/migrations/AddOrderDiscount -d src/data-source.ts
pnpm typeorm migration:run -d src/data-source.ts
pnpm typeorm migration:revert -d src/data-source.ts

# Prisma
pnpm prisma migrate dev --name add-order-discount
pnpm prisma migrate deploy   # Production
pnpm prisma migrate status
```

Prisma Migrate không có down migration. Muốn hoàn tác một migration đã chạy, đưa `schema.prisma` về trạng thái cũ rồi tạo migration mới bằng `migrate dev`. `prisma migrate diff --script` sinh được SQL ngược để review. `prisma migrate resolve --rolled-back` chỉ nhận migration bị fail, migration đã chạy xong bị từ chối (P3012).

### 4.4. Logging queries (development)

```ts
// TypeORM — bật logging
TypeOrmModule.forRoot({
  logging: ['query', 'error', 'warn'],
  logger: 'advanced-console',
});

// Prisma — bật query logging
const prisma = new PrismaClient({
  adapter: new PrismaPg({ connectionString: process.env.DATABASE_URL }), // required in Prisma 7
  log: [
    { emit: 'stdout', level: 'query' },
    { emit: 'stdout', level: 'error' },
  ],
});
```

---

## References

- [Prisma Documentation](https://www.prisma.io/docs) — Official Prisma docs (schema, migrate, client)
- [TypeORM Documentation](https://typeorm.io/) — Official TypeORM docs (entities, migrations, query builder)
- [NestJS Database](https://docs.nestjs.com/techniques/database) — NestJS integration guide
- [PostgreSQL Documentation](https://www.postgresql.org/docs/) — Index types, EXPLAIN, performance tuning
- [Use The Index, Luke](https://use-the-index-luke.com/) — SQL indexing & tuning (database-agnostic)
- [Prisma N+1 Problem](https://www.prisma.io/docs/guides/performance-and-optimization/query-optimization-performance) — Query optimization guide

## Changelog

| Date | Version | Change | By |
| :---- | :---- | :---- | :---- |
| 2026-11-18 | v1.0 | Chuyển từ Notion "NestJS Document" (page `33d71a38d3b281628d19d6466cffcb63`, sửa 2026-04-09). Review và sửa nội dung, code trước khi publish. Owner duyệt trong chat ngày 2026-11-18. | Bắc PV |
