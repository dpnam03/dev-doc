# NestJS Coding Standard 6.2 — Event System

| Field | Value |
| :---- | :---- |
| Owner | Bắc PV — NodeJS BE Dev Lead |
| Audience | Dev (NodeJS BE) |
| Last reviewed | 2026-11-12 |
| Review cadence | Quarterly |
| Version | v1.0 |
| Linked from | Ref_Dev_nestjs-coding-standard_v1.0 |
| Status | Live |

Doc này là mục 6.2 của [NestJS Coding Standard](Ref_Dev_nestjs-coding-standard_v1.0.md), nhóm Async & Integration. Doc nêu quy tắc về Event System trong dự án NestJS, kèm lý do, ví dụ và config. Dev NodeJS BE đọc doc này khi viết code, review code và onboarding.

---

## 1. Tóm tắt & Phạm vi

> 📌 **Chủ đề**: Event System trong NestJS — cơ chế giao tiếp bất đồng bộ giữa các module thông qua events, giúp **tách coupling** và tăng khả năng mở rộng.
>
> **Phạm vi**: `@nestjs/event-emitter`, Node.js `EventEmitter`, CQRS events.
>
> **Tại sao quan trọng**: Trong các hệ thống phức tạp, nếu module A gọi trực tiếp module B, C, D — code trở nên chặt chẽ, khó test, khó mở rộng. Event system cho phép module A chỉ cần **phát sự kiện**, các module khác tự lắng nghe và xử lý.

### 1.1. Khi nào dùng Event System?

| **Tình huống** | **Giải pháp** | **Ví dụ** |
| --- | --- | --- |
| Side effects sau action chính (gửi email, log audit, clear cache) | `@nestjs/event-emitter` | Sau khi tạo order → gửi email xác nhận + clear cache |
| Decouple modules trong cùng process | `@nestjs/event-emitter` | Module Orders phát event, module Inventory lắng nghe giảm stock |
| Low-level I/O events, stream processing | Node.js `EventEmitter` | Custom transport, file watcher, TCP socket events |
| Complex domain logic, event sourcing, audit trail | CQRS (`@nestjs/cqrs`) | Domain events cho aggregate changes, replay events |

---

## 2. Quy tắc & Giải thích

### 2.1. `@nestjs/event-emitter` — Giải pháp chính cho hầu hết dự án

> 💡 `@nestjs/event-emitter` wrap thư viện `eventemitter2` — hỗ trợ wildcard events, async listeners, và tích hợp sẵn với NestJS DI. Đây là **lựa chọn mặc định** cho event-driven communication trong NestJS.

### 2.2. Nên làm

- **Dùng typed event classes** thay vì string payload — compiler bắt lỗi, IDE autocomplete, refactor an toàn
- *Tại sao*: String events như `'order.created'` với payload `any` — không biết shape cho đến runtime. Typed class cho phép validate tại compile time.
- **Emit events SAU khi action chính hoàn tất** (đặc biệt sau transaction commit) — đảm bảo data consistency
- *Tại sao*: Nếu emit trước khi commit, listener có thể query DB và thấy data chưa tồn tại → bug khó debug.
- **Event không được mất thì ghi vào outbox trong cùng transaction**, job ở process worker đọc outbox rồi mới emit (mục 3.2). Event best-effort như xoá cache, gửi notification vẫn emit sau commit
- *Tại sao*: Process crash giữa lúc commit và lúc `emit()` thì event mất. Outbox giữ event trong DB tới khi listener chạy xong.
- **Listener chỉ làm 1 việc** — mỗi `@OnEvent` handler xử lý 1 side effect duy nhất
- *Tại sao*: Nếu gộp send email + clear cache + log audit vào 1 listener — khi email service lỗi, cache cũng không clear.
- **Fire-and-forget cho non-critical side effects** — dùng `@OnEvent('...', { async: true })` + error handling riêng
- *Tại sao*: Gửi notification thất bại không nên block hay rollback order creation.
- **Đặt event classes trong `events/` folder** của feature module — co-locate với domain
- **Đặt listeners trong file riêng** `<feature>.listeners.ts` hoặc folder `listeners/` — tách biệt khỏi service logic chính

### 2.3. Không nên làm

- ❌ **Dùng string literals rải rác** — `this.emitter.emit('order.created', order)` — typo không bị catch
- ✅ Dùng constant hoặc class name: `this.emitter.emit(OrderCreatedEvent.name, new OrderCreatedEvent(order.id, order.customerId, order.totalAmount, dto.items))`
- ❌ **Business logic trong listener** — listener chỉ nên delegate cho service
- *Tại sao*: Listener khó unit test nếu chứa logic phức tạp. Service có DI, dễ mock.
- ❌ **Emit event bên trong transaction** — listener có thể query data chưa commit
- ❌ **Listener throw exception không catch** — exception trong async listener bị nuốt hoặc crash unexpected
- ❌ **Circular event chains** — Event A trigger Event B trigger Event A → infinite loop
- ❌ **Dùng events thay thế direct calls cho synchronous flows** — nếu caller CẦN kết quả từ callee, gọi trực tiếp service

### 2.2. Node.js `EventEmitter` — Khi nào dùng?

> ⚠️ Node.js built-in `EventEmitter` phù hợp cho **low-level, infrastructure code** — KHÔNG dùng cho application-level business events.

- **Dùng khi**: Custom transports, stream processing, file watchers, TCP/UDP sockets, hoặc wrapping native libraries
- **Không dùng khi**: Business domain events — thiếu DI integration, không có lifecycle management, khó test

**So sánh**:

| **Tiêu chí** | **Node.js EventEmitter** | **@nestjs/event-emitter** |
| --- | --- | --- |
| DI Integration | ❌ Không | ✅ Có — inject services trong listener |
| Wildcard events | ❌ Không | ✅ `order.*` match tất cả order events |
| Async listeners | ⚠️ Manual (Promise handling) | ✅ Built-in async support |
| Type safety | ❌ Weak | ✅ Typed event classes |
| Memory leak detection | ✅ `maxListeners` warning | ✅ Inherited từ eventemitter2 |
| Use case | Infrastructure, streams, I/O | Business domain events |

### 2.3. CQRS Events — Khi domain phức tạp

> 🏗️ `@nestjs/cqrs` triển khai pattern Command Query Responsibility Segregation — tách read và write models. Dùng khi hệ thống có **domain logic phức tạp**, cần **event sourcing**, hoặc cần **audit trail đầy đủ**.

- **Dùng khi**: Domain-driven design, event sourcing, complex aggregates, cần replay events
- **Không dùng khi**: CRUD đơn giản — overhead quá lớn so với benefit

**Các thành phần chính**:

| **Thành phần** | **Vai trò** | **Ví dụ** |
| --- | --- | --- |
| `Command` | Intent thay đổi state | `CreateOrderCommand` |
| `CommandHandler` | Xử lý command, apply domain logic | `CreateOrderHandler` |
| `Event` | Fact đã xảy ra (past tense) | `OrderCreatedEvent` |
| `EventHandler` | React to event (side effects) | `OrderCreatedHandler` → send email |
| `Query` | Read request | `GetOrderQuery` |
| `Saga` | Orchestrate multiple events → commands | Order saga: payment → shipping |

**Quyết định khi nào dùng CQRS vs event-emitter:**

- Dự án CRUD thông thường → `@nestjs/event-emitter` (đơn giản, ít boilerplate)
- Domain phức tạp, nhiều aggregate, cần event replay → `@nestjs/cqrs`
- Có thể **kết hợp cả hai**: CQRS cho core domain, event-emitter cho infrastructure side effects

---

## 3. Ví dụ minh họa thực tế

### 3.1. Setup `@nestjs/event-emitter`

```ts
// app.module.ts
import { EventEmitterModule } from '@nestjs/event-emitter';

@Module({
  imports: [
    EventEmitterModule.forRoot({
      wildcard: true,           // Hỗ trợ 'order.*' patterns
      delimiter: '.',            // Separator cho wildcard
      maxListeners: 20,          // Cảnh báo memory leak nếu > 20
      ignoreErrors: false,       // Không nuốt errors
    }),
  ],
})
export class AppModule {}
```

### 3.2. Typed Event Class + Emit sau transaction

```ts
// modules/orders/events/order-created.event.ts
export class OrderCreatedEvent {
  constructor(
    public readonly orderId: string,
    public readonly customerId: string,
    public readonly totalAmount: number,
    public readonly items: Array<{ productId: string; quantity: number }>,
    public readonly createdAt: Date = new Date(),
  ) {}
}
```

```ts
// modules/orders/orders.service.ts
import { EventEmitter2 } from '@nestjs/event-emitter';
import { OrderCreatedEvent } from './events/order-created.event';

@Injectable()
export class OrdersService {
  constructor(
    private readonly ordersRepo: OrdersRepository,
    private readonly dataSource: DataSource,
    private readonly eventEmitter: EventEmitter2,
  ) {}

  async create(dto: CreateOrderDto): Promise<Order> {
    // 1. Validate TRƯỚC transaction
    await this.validateStock(dto.items);

    // 2. Transaction — chỉ chứa DB writes
    const order = await this.dataSource.transaction(async (manager) => {
      const order = await this.ordersRepo.createWithItems(manager, dto);
      await this.inventoryRepo.decreaseStock(manager, dto.items);
      return order;
    });

    // 3. Emit event SAU transaction commit ✅
    this.eventEmitter.emit(
      OrderCreatedEvent.name,
      new OrderCreatedEvent(
        order.id,
        order.customerId,
        order.totalAmount,
        dto.items,
      ),
    );

    return order;
  }
}
```

**Event không được mất — outbox:** service ghi order và một dòng `outbox_events` trong cùng transaction. `OutboxPublisher` chạy ở process worker ([NestJS Coding Standard 1.1 — Cấu trúc dự án](Ref_Dev_s1.1_nestjs-project-structure_v1.0.md) mục 2.1), emit từng event rồi đánh dấu `publishedAt`.

```ts
// common/outbox/outbox-event.entity.ts
@Entity('outbox_events')
export class OutboxEvent {
  @PrimaryGeneratedColumn()
  id: number;

  @Column()
  name: string;

  @Column({ type: 'json' })
  payload: Record<string, unknown>;

  @Column({ type: 'timestamp', nullable: true })
  publishedAt: Date | null;

  @CreateDateColumn()
  createdAt: Date;
}
```

```ts
// modules/orders/orders.service.ts, create() — the order and its event commit together, or neither does
async create(dto: CreateOrderDto): Promise<Order> {
  await this.validateStock(dto.items);

  return this.dataSource.transaction(async (manager) => {
    const order = await this.ordersRepo.createWithItems(manager, dto);
    await this.inventoryRepo.decreaseStock(manager, dto.items);
    await manager.insert(OutboxEvent, {
      name: OrderCreatedEvent.name,
      payload: { ...new OrderCreatedEvent(order.id, order.customerId, order.totalAmount, dto.items) },
    });
    return order;
  });
}
```

```ts
// common/outbox/outbox-publisher.service.ts — runs in the worker process (1.1 section 2.1)
@Injectable()
export class OutboxPublisher {
  constructor(
    @InjectRepository(OutboxEvent) private readonly outbox: Repository<OutboxEvent>,
    private readonly eventEmitter: EventEmitter2,
  ) {}

  @Interval(5000)
  async publishPending(): Promise<void> {
    const events = await this.outbox.find({
      where: { publishedAt: IsNull() },
      order: { id: 'ASC' },
      take: 100,
    });
    for (const event of events) {
      // Rejects when a listener throws (listener options in the notes below): the event stays for the next run
      await this.eventEmitter.emitAsync(event.name, event.payload);
      await this.outbox.update(event.id, { publishedAt: new Date() });
    }
  }
}
```

- Listener của event đi qua outbox khai báo `@OnEvent(OrderCreatedEvent.name, { suppressErrors: false })`, không thêm `async: true`. Khi đó listener lỗi thì `emitAsync` reject và event được thử lại ở lần chạy sau.
- Mặc định `@nestjs/event-emitter` nuốt lỗi của listener, nên publisher vẫn đánh dấu event đã publish. Thêm `async: true` cùng `suppressErrors: false` thì lỗi làm crash process.
- Publisher có thể crash sau khi emit và trước khi update, nên một event có thể được giao hai lần. Listener phải idempotent.
- Chỉ chạy publisher ở một instance worker. Chạy nhiều instance thì khoá dòng bằng `FOR UPDATE SKIP LOCKED`.
- Payload đi qua JSON, nên listener nhận plain object và `createdAt` là string.

### 3.3. Event Listeners — mỗi listener 1 việc

```ts
// modules/orders/listeners/order-notification.listener.ts
import { OnEvent } from '@nestjs/event-emitter';
import { OrderCreatedEvent } from '../events/order-created.event';

@Injectable()
export class OrderNotificationListener {
  private readonly logger = new Logger(OrderNotificationListener.name);

  constructor(private readonly mailService: MailService) {}

  @OnEvent(OrderCreatedEvent.name, { async: true })
  async handleOrderCreated(event: OrderCreatedEvent): Promise<void> {
    try {
      await this.mailService.sendOrderConfirmation({
        customerId: event.customerId,
        orderId: event.orderId,
        totalAmount: event.totalAmount,
      });
    } catch (error) {
      // Fire-and-forget: log error, KHÔNG re-throw
      this.logger.warn(
        `Failed to send order confirmation for ${event.orderId}: ${error.message}`,
      );
    }
  }
}
```

```ts
// modules/orders/listeners/order-cache.listener.ts
@Injectable()
export class OrderCacheListener {
  private readonly logger = new Logger(OrderCacheListener.name);

  constructor(
    @Inject(CACHE_MANAGER) private readonly cacheManager: Cache,
  ) {}

  @OnEvent(OrderCreatedEvent.name, { async: true })
  async handleCacheInvalidation(event: OrderCreatedEvent): Promise<void> {
    try {
      await this.cacheManager.del(`orders:list:customer:${event.customerId}`);
      await this.cacheManager.del('orders:stats:dashboard');
    } catch (error) {
      this.logger.warn(`Cache invalidation failed: ${error.message}`);
    }
  }
}
```

```ts
// modules/audit/listeners/order-audit.listener.ts
@Injectable()
export class OrderAuditListener {
  constructor(private readonly auditService: AuditService) {}

  @OnEvent(OrderCreatedEvent.name, { async: true })
  async handleAuditLog(event: OrderCreatedEvent): Promise<void> {
    await this.auditService.log({
      action: 'order.created',
      entityId: event.orderId,
      entityType: 'Order',
      metadata: { customerId: event.customerId, totalAmount: event.totalAmount },
      timestamp: event.createdAt,
    });
  }
}
```

### 3.4. Register listeners trong module

```ts
// modules/orders/orders.module.ts
@Module({
  providers: [
    OrdersService,
    OrdersRepository,
    OrderNotificationListener,   // Đăng ký listener như provider
    OrderCacheListener,
  ],
})
export class OrdersModule {}

// modules/audit/audit.module.ts — listener ở module khác
@Module({
  providers: [
    AuditService,
    OrderAuditListener,  // Cross-module listener
  ],
})
export class AuditModule {}
```

### 3.5. Wildcard Events

Wildcard chỉ match nguyên một segment tách bằng `delimiter`. Event đặt tên theo class (`OrderCreatedEvent.name`) chỉ có một segment, nên pattern như `'OrderCreated*'` không bao giờ match. Cần wildcard thì emit và `@OnEvent` cùng dùng constant dạng `'order.created'`.

```ts
// modules/orders/events/order-events.ts — dotted names, one segment per level
export const OrderEvents = {
  CREATED: 'order.created',
  UPDATED: 'order.updated',
} as const;

// Emit with the constant instead of the class name
this.eventEmitter.emit(
  OrderEvents.CREATED,
  new OrderCreatedEvent(order.id, order.customerId, order.totalAmount, dto.items),
);

// Matches 'order.created', 'order.updated'
@OnEvent('order.*', { async: true })
async handleOrderEvents(event: unknown): Promise<void> {
  // ...
}
```

### 3.6. Before/After — Refactor từ tight coupling sang event-driven

**❌ Before — Tight coupling, OrdersService phụ thuộc 4 modules:**

```ts
// ❌ OrdersService import trực tiếp mọi thứ
@Injectable()
export class OrdersService {
  constructor(
    private readonly ordersRepo: OrdersRepository,
    private readonly mailService: MailService,         // ❌ Coupling
    private readonly cacheManager: Cache,               // ❌ Coupling
    private readonly auditService: AuditService,        // ❌ Coupling
    private readonly analyticsService: AnalyticsService, // ❌ Coupling
  ) {}

  async create(dto: CreateOrderDto): Promise<Order> {
    const order = await this.ordersRepo.save(dto);

    // Gọi tuần tự — chậm, 1 lỗi block tất cả
    await this.mailService.sendConfirmation(order);     // Fail → order vẫn tạo?
    await this.cacheManager.del('orders:list');          // Fail → stale cache
    await this.auditService.log('order.created', order); // Fail → mất audit
    await this.analyticsService.track('purchase', order); // Fail → mất data

    return order;
  }
}
```

**✅ After — Decoupled, OrdersService chỉ biết EventEmitter:**

```ts
// ✅ OrdersService chỉ phụ thuộc EventEmitter
@Injectable()
export class OrdersService {
  constructor(
    private readonly ordersRepo: OrdersRepository,
    private readonly dataSource: DataSource,
    private readonly eventEmitter: EventEmitter2,  // Chỉ 1 dependency cho side effects
  ) {}

  async create(dto: CreateOrderDto): Promise<Order> {
    const order = await this.dataSource.transaction(async (manager) => {
      return this.ordersRepo.createWithItems(manager, dto);
    });

    // Emit 1 lần — N listeners xử lý song song, independent
    this.eventEmitter.emit(
      OrderCreatedEvent.name,
      new OrderCreatedEvent(order.id, order.customerId, order.totalAmount, dto.items),
    );

    return order; // Return ngay, không chờ side effects
  }
}
```

### 3.7. CQRS Example — Domain Events

```ts
// modules/orders/commands/create-order.command.ts
export class CreateOrderCommand {
  constructor(
    public readonly customerId: string,
    public readonly items: Array<{ productId: string; quantity: number }>,
  ) {}
}
```

```ts
// modules/orders/commands/handlers/create-order.handler.ts
import { CommandHandler, ICommandHandler, EventBus } from '@nestjs/cqrs';

@CommandHandler(CreateOrderCommand)
export class CreateOrderHandler implements ICommandHandler<CreateOrderCommand> {
  constructor(
    private readonly ordersRepo: OrdersRepository,
    private readonly eventBus: EventBus,
  ) {}

  async execute(command: CreateOrderCommand): Promise<Order> {
    const order = await this.ordersRepo.create(command);

    // Publish domain event qua CQRS EventBus
    this.eventBus.publish(
      new OrderCreatedEvent(order.id, order.customerId, order.totalAmount, command.items),
    );

    return order;
  }
}
```

```ts
// modules/orders/events/handlers/order-created.handler.ts
import { EventsHandler, IEventHandler } from '@nestjs/cqrs';

@EventsHandler(OrderCreatedEvent)
export class OrderCreatedHandler implements IEventHandler<OrderCreatedEvent> {
  async handle(event: OrderCreatedEvent): Promise<void> {
    // Side effect: send notification, update read model, etc.
  }
}
```

```ts
// modules/orders/sagas/order.saga.ts — orchestrate event flows
import { Saga, ofType } from '@nestjs/cqrs';
import { Observable, map } from 'rxjs';

@Injectable()
export class OrderSaga {
  @Saga()
  orderCreated = (events$: Observable<any>): Observable<ICommand> => {
    return events$.pipe(
      ofType(OrderCreatedEvent),
      map((event) => new ProcessPaymentCommand(event.orderId, event.totalAmount)),
    );
  };
}
```

---

## 4. Tooling & Config

### 4.1. Cài đặt

```bash
# Event Emitter — lựa chọn mặc định
pnpm add @nestjs/event-emitter

# CQRS — chỉ khi domain phức tạp
pnpm add @nestjs/cqrs
```

### 4.2. Module Registration

```ts
// app.module.ts — Event Emitter
import { EventEmitterModule } from '@nestjs/event-emitter';

@Module({
  imports: [
    EventEmitterModule.forRoot({
      wildcard: true,
      delimiter: '.',
      maxListeners: 20,
      ignoreErrors: false,
    }),
  ],
})
export class AppModule {}
```

```ts
// app.module.ts — CQRS (nếu cần)
import { CqrsModule } from '@nestjs/cqrs';

@Module({
  imports: [CqrsModule.forRoot()],
})
export class AppModule {}
```

### 4.3. Cấu trúc folder cho feature module có events

```txt
src/modules/orders/
├── orders.module.ts
├── orders.controller.ts
├── orders.service.ts
├── orders.repository.ts
├── dto/
│   ├── create-order.dto.ts
│   └── update-order.dto.ts
├── entities/
│   └── order.entity.ts
├── events/                         # Event classes
│   ├── order-created.event.ts
│   ├── order-updated.event.ts
│   └── order-cancelled.event.ts
├── listeners/                      # Event listeners
│   ├── order-notification.listener.ts
│   └── order-cache.listener.ts
├── commands/                       # (Chỉ khi dùng CQRS)
│   ├── create-order.command.ts
│   └── handlers/
│       └── create-order.handler.ts
└── sagas/                          # (Chỉ khi dùng CQRS)
    └── order.saga.ts
```

### 4.4. Testing Events

```ts
// orders.service.spec.ts
describe('OrdersService', () => {
  let service: OrdersService;
  let eventEmitter: EventEmitter2;

  beforeEach(async () => {
    const module = await Test.createTestingModule({
      providers: [
        OrdersService,
        { provide: EventEmitter2, useValue: { emit: jest.fn() } },
        { provide: OrdersRepository, useValue: { createWithItems: jest.fn() } },
      ],
    }).compile();

    service = module.get(OrdersService);
    eventEmitter = module.get(EventEmitter2);
  });

  it('should emit OrderCreatedEvent after order creation', async () => {
    const order = await service.create(mockDto);

    expect(eventEmitter.emit).toHaveBeenCalledWith(
      OrderCreatedEvent.name,
      expect.any(OrderCreatedEvent),
    );
  });
});
```

```ts
// Listener test — verify side effect
describe('OrderNotificationListener', () => {
  it('should send email on OrderCreatedEvent', async () => {
    const mailService = { sendOrderConfirmation: jest.fn() };
    const listener = new OrderNotificationListener(mailService as any);

    await listener.handleOrderCreated(new OrderCreatedEvent('ord-1', 'cust-1', 500000, []));

    expect(mailService.sendOrderConfirmation).toHaveBeenCalledWith(
      expect.objectContaining({ orderId: 'ord-1' }),
    );
  });

  it('should not throw on mail failure', async () => {
    const mailService = { sendOrderConfirmation: jest.fn().mockRejectedValue(new Error('SMTP down')) };
    const listener = new OrderNotificationListener(mailService as any);

    // Should not throw
    await expect(
      listener.handleOrderCreated(new OrderCreatedEvent('ord-1', 'cust-1', 500000, [])),
    ).resolves.not.toThrow();
  });
});
```

---

## References

- [NestJS Events — Official Docs](https://docs.nestjs.com/techniques/events)
- [NestJS CQRS — Official Docs](https://docs.nestjs.com/recipes/cqrs)
- [Node.js EventEmitter — API Reference](https://nodejs.org/docs/latest/api/events.html)
- [eventemitter2 — npm](https://www.npmjs.com/package/eventemitter2)
- [Martin Fowler — Event-Driven Architecture](https://martinfowler.com/articles/201701-event-driven.html)
- [Microsoft — CQRS Pattern](https://learn.microsoft.com/en-us/azure/architecture/patterns/cqrs)

## Changelog

| Date | Version | Change | By |
| :---- | :---- | :---- | :---- |
| 2026-11-18 | v1.0 | Chuyển từ Notion "NestJS Document" (page `33d71a38d3b28110b7bed258b9be3ad6`, sửa 2026-04-09). Review và sửa nội dung, code trước khi publish. Owner duyệt trong chat ngày 2026-11-18. | Bắc PV |
