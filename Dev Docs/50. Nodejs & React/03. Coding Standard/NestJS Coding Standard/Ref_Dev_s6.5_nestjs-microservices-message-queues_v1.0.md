# NestJS Coding Standard 6.5 — Microservices & Message Queues

| Field | Value |
| :---- | :---- |
| Owner | Bắc PV — NodeJS BE Dev Lead |
| Audience | Dev (NodeJS BE) |
| Last reviewed | 2026-11-12 |
| Review cadence | Quarterly |
| Version | v1.0 |
| Linked from | Ref_Dev_nestjs-coding-standard_v1.0 |
| Status | Live |

Doc này là mục 6.5 của [NestJS Coding Standard](Ref_Dev_nestjs-coding-standard_v1.0.md), nhóm Async & Integration. Doc nêu quy tắc về Microservices & Message Queues trong dự án NestJS, kèm lý do, ví dụ và config. Dev NodeJS BE đọc doc này khi viết code, review code và onboarding.

---

## 1 Tóm tắt & Phạm vi

> 📘 Chủ đề này bao quát kiến trúc **Microservices** trong NestJS — cách tách hệ thống monolith thành các service nhỏ giao tiếp qua **message brokers** (RabbitMQ, Kafka, Redis) hoặc **transport layers** (TCP, gRPC, NATS, MQTT). Áp dụng cho mọi dự án cần **scale horizontal**, **decouple domains**, hoặc **xử lý async workload** lớn.

### 1.1 Khi nào cần Microservices?

- **Scale độc lập**: Một module cần scale riêng (ví dụ: notification service xử lý hàng triệu email/ngày, nhưng order service chỉ vài nghìn request)
- **Team autonomy**: Nhiều team phát triển song song, mỗi team own 1 domain
- **Fault isolation**: Lỗi ở payment service không làm sập product catalog
- **Technology diversity**: Một service dùng Python ML, service khác dùng NestJS

### 1.2 Khi nào KHÔNG nên?

- Dự án nhỏ, 1–3 developers — overhead vận hành lớn hơn lợi ích
- Team chưa có kinh nghiệm distributed systems — bắt đầu bằng **modular monolith** trước
- Chưa xác định rõ domain boundaries — tách sai còn khó hơn monolith

---

## 2 Quy tắc & Giải thích

### 1. Message Patterns: Request-Response vs Event-based

NestJS Microservices hỗ trợ 2 patterns chính:

| Pattern | Decorator | Khi nào dùng | Return |
| --- | --- | --- | --- |
| **Request-Response** | `@MessagePattern()` | Cần response từ service (query data, validate) | `Observable` hoặc `Promise` |
| **Event-based** | `@EventPattern()` | Fire-and-forget (send email, log audit, update cache) | Không return |

**Nên làm:**

- Dùng `@MessagePattern('get_user')` khi caller cần đợi kết quả
- Dùng `@EventPattern('order_created')` khi caller không cần đợi — giảm latency, tăng throughput
- Đặt tên pattern rõ ràng, theo convention: `<domain>.<action>` hoặc `<action>_<entity>` — ví dụ `user.created`, `get_order_details`

**Không nên:**

- Dùng `@MessagePattern()` cho side effects không cần response (gửi email, push notification) — block caller vô ích
- Tên pattern mơ hồ: `handle`, `process`, `data` — không biết service nào handle cái gì

```ts
// ✅ Request-Response — caller cần kết quả
@MessagePattern('get_user_by_id')
async getUser(@Payload() data: { userId: string }): Promise<UserResponseDto> {
  return this.usersService.findById(data.userId);
}

// ✅ Event-based — fire-and-forget
@EventPattern('order_created')
async handleOrderCreated(@Payload() data: OrderCreatedEvent): Promise<void> {
  await this.notificationService.sendOrderConfirmation(data);
}
```

### 2. Transport Layers — Chọn đúng broker

NestJS abstract transport qua `ClientProxy` — code business logic không đổi khi switch broker.

| Transport | Use case | Đặc điểm |
| --- | --- | --- |
| **TCP** | Dev/test, internal service đơn giản | Không cần broker, point-to-point |
| **Redis** | Pub/Sub nhẹ, cache invalidation | Đơn giản, không persistence mặc định |
| **RabbitMQ** | Task queues, routing phức tạp, retry/DLQ | Mature, flexible routing, message acknowledgment |
| **Kafka** | Event streaming, high throughput, event sourcing | Persistence, replay, partitioning, consumer groups |
| **gRPC** | Low latency, strongly typed, polyglot | Binary protocol (Protobuf), streaming support |
| **NATS** | Lightweight messaging, request-reply | Rất nhanh, cloud-native |

**Nên làm:**

- **Bắt đầu với RabbitMQ** nếu chưa có yêu cầu đặc biệt — cân bằng tốt giữa tính năng và độ phức tạp
- Dùng **Kafka** khi cần event replay, audit trail, hoặc throughput > 100K msg/s
- Dùng **gRPC** cho service-to-service sync calls cần low latency và type safety
- Dùng **Redis transport** chỉ cho Pub/Sub đơn giản hoặc cache invalidation cross-service

**Không nên:**

- Dùng TCP transport trong production — không có retry, persistence, monitoring
- Dùng Kafka cho simple task queue — overkill, vận hành phức tạp
- Mix quá nhiều transports trong 1 hệ thống nhỏ — tăng operational overhead

### 3. Client Registration — Inject đúng cách

**Nên làm:**

- Register `ClientsModule` trong feature module cần gọi service khác
- Dùng `@Inject('SERVICE_NAME')` với token rõ ràng
- Config broker connection từ `ConfigService` — không hardcode host/port
- Gọi `client.connect()` trong `onModuleInit()` hoặc để NestJS tự manage

```ts
// ✅ Register client trong module
@Module({
  imports: [
    ClientsModule.registerAsync([
      {
        name: 'ORDERS_SERVICE',
        useFactory: (config: ConfigService) => ({
          transport: Transport.RMQ,
          options: {
            urls: [config.getOrThrow<string>('RMQ_URL')],
            queue: config.getOrThrow<string>('ORDERS_QUEUE'),
            queueOptions: { durable: true },
            persistent: true, // Default is false: messages are lost when the broker restarts
          },
        }),
        inject: [ConfigService],
      },
    ]),
  ],
})
export class PaymentsModule {}
```

```ts
// ✅ Inject và sử dụng trong service
@Injectable()
export class PaymentsService implements OnModuleInit {
  constructor(
    @Inject('ORDERS_SERVICE') private readonly ordersClient: ClientProxy,
  ) {}

  async onModuleInit() {
    await this.ordersClient.connect();
  }

  async getOrderDetails(orderId: string): Promise<OrderDto> {
    return firstValueFrom(
      this.ordersClient.send<OrderDto>('get_order_details', { orderId }),
    );
  }

  async notifyOrderPaid(orderId: string): Promise<void> {
    this.ordersClient.emit('order_paid', { orderId, paidAt: new Date() });
  }
}
```

**Không nên:**

- Tạo `ClientProxy` thủ công bằng `ClientProxyFactory` rải rác — khó manage lifecycle
- Hardcode connection string — dùng `registerAsync` + `ConfigService`
- Quên handle connection errors — broker down sẽ crash app

### 4. Payload Validation & Serialization

**Nên làm:**

- Validate payload bằng `ValidationPipe` + DTO — giống REST controller
- Dùng `@Payload()` decorator thay vì `@Body()` trong microservice handler
- Dùng `@Ctx()` để access transport-specific context (RmqContext, KafkaContext, etc.)
- Serialize/deserialize payload bằng JSON — tránh gửi class instances

```ts
// ✅ Validate payload trong microservice handler
@MessagePattern('create_order')
@UsePipes(new ValidationPipe({ whitelist: true, transform: true }))
async createOrder(@Payload() dto: CreateOrderDto): Promise<OrderResponseDto> {
  return this.ordersService.create(dto);
}
```

```ts
// ✅ Access transport context
// <string> picks the untyped overload; NestJS 12 otherwise rejects a typed @Ctx() param (TS1241)
@EventPattern<string>('order_shipped')
async handleShipped(
  @Payload() data: OrderShippedEvent,
  @Ctx() context: RmqContext,
): Promise<void> {
  const channel = context.getChannelRef();
  const originalMsg = context.getMessage();

  try {
    await this.shippingService.processShipment(data);
    channel.ack(originalMsg); // Manual acknowledgment
  } catch (error) {
    // requeue=false: the message goes to the queue's DLX (see 7.1; dropped if the queue has none).
    // requeue=true would redeliver a poison message forever.
    channel.nack(originalMsg, false, false);
  }
}
```

**Không nên:**

- Gửi raw objects không validate — garbage in, garbage out
- Auto-ack messages trước khi xử lý xong — mất message khi crash
- Gửi quá nhiều data trong payload — chỉ gửi IDs/references, service tự query nếu cần full data

### 5. Error Handling trong Microservices

**Nên làm:**

- Dùng `RpcException` thay vì `HttpException` trong microservice handlers — `HttpException` không serialize đúng qua transport
- Tạo custom `RpcExceptionFilter` để format error response chuẩn
- Implement **retry logic** với exponential backoff cho transient errors
- Cấu hình **Dead Letter Queue (DLQ)** cho messages fail sau N retries
- Log đầy đủ context: message pattern, payload (redacted), error stack

```ts
// ✅ RpcException trong microservice
@MessagePattern('get_user_by_id')
async getUser(@Payload() data: { userId: string }): Promise<UserResponseDto> {
  const user = await this.usersService.findById(data.userId);
  if (!user) {
    throw new RpcException({
      status: HttpStatus.NOT_FOUND,
      message: `User ${data.userId} not found`,
      code: 'USER_NOT_FOUND',
    });
  }
  return user;
}
```

```ts
// ✅ Custom RPC Exception Filter
@Catch(RpcException)
export class RpcExceptionFilter implements ExceptionFilter {
  catch(exception: RpcException, host: ArgumentsHost) {
    const error = exception.getError();
    const ctx = host.switchToRpc();
    // Log với context
    Logger.error(
      `RPC Error: ${JSON.stringify(error)}`,
      RpcExceptionFilter.name,
    );
    return throwError(() => error);
  }
}
```

**Không nên:**

- Throw `HttpException` trong microservice handler — client nhận object lỗi không parse được
- Silent catch errors — message biến mất, không ai biết
- Retry vô hạn không có backoff — DDoS chính mình

### 6. Hybrid Application — HTTP + Microservice

Khi 1 app vừa serve REST API vừa listen messages:

```ts
// ✅ Hybrid application — main.ts
async function bootstrap() {
  const app = await NestFactory.create(AppModule);

  // Connect microservice transport
  app.connectMicroservice<MicroserviceOptions>({
    transport: Transport.RMQ,
    options: {
      urls: [process.env.RMQ_URL],
      queue: 'orders_queue',
      queueOptions: { durable: true },
      noAck: false, // Manual acknowledgment
    },
  });

  await app.startAllMicroservices();
  await app.listen(3000);
}
```

**Nên làm:**

- Dùng hybrid khi service vừa cần REST endpoint (health check, admin API) vừa consume messages
- Tách handlers HTTP (controllers) và message (microservice controllers) vào modules riêng
- Health check endpoint kiểm tra cả HTTP server lẫn broker connection

**Không nên:**

- Mix HTTP decorators (`@Get`, `@Post`) và microservice decorators (`@MessagePattern`) trong cùng 1 controller
- Quên `startAllMicroservices()` — microservice handlers sẽ không nhận messages

### 7. Message Queue Patterns nâng cao

### 7.1 RabbitMQ — Exchanges, Routing, DLQ

```ts
// ✅ RabbitMQ với exchange routing
app.connectMicroservice<MicroserviceOptions>({
  transport: Transport.RMQ,
  options: {
    urls: [configService.getOrThrow('RMQ_URL')],
    queue: 'notifications_queue',
    queueOptions: {
      durable: true,
      deadLetterExchange: 'dlx.notifications',
      deadLetterRoutingKey: 'dlq.notifications',
      messageTtl: 30000, // 30s TTL
    },
    prefetchCount: 10, // Xử lý 10 messages song song
    noAck: false,
  },
});
```

### 7.2 Kafka — Consumer Groups, Partitions

```ts
// ✅ Kafka consumer setup
app.connectMicroservice<MicroserviceOptions>({
  transport: Transport.KAFKA,
  options: {
    client: {
      clientId: 'orders-service',
      brokers: configService.getOrThrow<string>('KAFKA_BROKERS').split(','),
    },
    consumer: {
      groupId: 'orders-consumer-group',
      sessionTimeout: 30000,
      heartbeatInterval: 3000,
    },
    run: {
      autoCommit: false, // Manual commit sau khi xử lý xong
    },
  },
});
```

```ts
// ✅ Kafka handler với manual commit
// <string> picks the untyped overload; NestJS 12 otherwise rejects a typed @Ctx() param (TS1241)
@EventPattern<string>('order.events')
async handleOrderEvent(
  @Payload() data: OrderEvent,
  @Ctx() context: KafkaContext,
) {
  const { offset } = context.getMessage();
  const partition = context.getPartition();
  const topic = context.getTopic();

  try {
    await this.ordersService.processEvent(data);
    // Commit offset sau khi xử lý thành công
    await context.getConsumer().commitOffsets([
      { topic, partition, offset: (Number(offset) + 1).toString() },
    ]);
  } catch (error) {
    this.logger.error(
      `Failed to process event at ${topic}:${partition}:${offset}`,
      error instanceof Error ? error.stack : String(error),
    );
    // Not committing alone does not retry: the next message that succeeds commits
    // a higher offset and this one is never read again. Rethrow so kafkajs
    // redelivers it; a message that can never succeed belongs on a DLQ topic.
    throw error;
  }
}
```

### 7.3 Redis Transport — Pub/Sub

```ts
// ✅ Redis transport cho cache invalidation
app.connectMicroservice<MicroserviceOptions>({
  transport: Transport.REDIS,
  options: {
    host: configService.getOrThrow('REDIS_HOST'),
    port: configService.getOrThrow<number>('REDIS_PORT'),
    retryAttempts: 5,
    retryDelay: 3000,
  },
});
```

### 8. Idempotency & Message Deduplication

Message brokers đảm bảo **at-least-once delivery** — message có thể được gửi lại. Handler phải **idempotent**.

**Nên làm:**

- Gắn `messageId` (UUID) vào mỗi message
- Check `messageId` trước khi xử lý — skip nếu đã xử lý (dùng Redis SET hoặc DB table)
- Design handler idempotent: `SET status = 'paid'` thay vì `balance = balance - amount`

```ts
// ✅ Idempotent handler với deduplication
@EventPattern('payment_completed')
async handlePayment(@Payload() data: PaymentCompletedEvent): Promise<void> {
  const isDuplicate = await this.deduplicationService.isDuplicate(
    'payment_completed',
    data.messageId,
  );
  if (isDuplicate) {
    this.logger.warn(`Duplicate message: ${data.messageId}`);
    return;
  }

  await this.ordersService.markAsPaid(data.orderId);
  await this.deduplicationService.markProcessed(
    'payment_completed',
    data.messageId,
    { ttl: 24 * 60 * 60 }, // TTL 24h
  );
}
```

### 9. Testing Microservices

```ts
// ✅ Unit test cho microservice handler
describe('OrdersController (Microservice)', () => {
  let controller: OrdersMicroserviceController;
  let ordersService: jest.Mocked<OrdersService>;

  beforeEach(async () => {
    const module = await Test.createTestingModule({
      controllers: [OrdersMicroserviceController],
      providers: [
        {
          provide: OrdersService,
          useValue: { findById: jest.fn(), create: jest.fn() },
        },
      ],
    }).compile();

    controller = module.get(OrdersMicroserviceController);
    ordersService = module.get(OrdersService);
  });

  it('should return order by id', async () => {
    const mockOrder = { id: '1', status: 'pending' };
    ordersService.findById.mockResolvedValue(mockOrder as any);

    const result = await controller.getOrder({ orderId: '1' });

    expect(result).toEqual(mockOrder);
    expect(ordersService.findById).toHaveBeenCalledWith('1');
  });

  it('should throw RpcException when order not found', async () => {
    ordersService.findById.mockResolvedValue(null);

    await expect(controller.getOrder({ orderId: '999' })).rejects.toThrow(
      RpcException,
    );
  });
});
```

```ts
// ✅ E2E test với ClientProxy mock
describe('Payments → Orders (Integration)', () => {
  let app: INestMicroservice;

  beforeAll(async () => {
    const module = await Test.createTestingModule({
      imports: [OrdersModule],
    }).compile();

    app = module.createNestMicroservice({
      transport: Transport.TCP,
      options: { port: 0 }, // Random port cho test
    });
    await app.listen();
  });

  afterAll(() => app.close());
});
```

### 10. Graceful Shutdown

```ts
// ✅ Graceful shutdown — drain messages trước khi tắt
async function bootstrap() {
  const app = await NestFactory.create(AppModule);
  app.enableShutdownHooks();

  app.connectMicroservice<MicroserviceOptions>({
    transport: Transport.RMQ,
    options: {
      urls: [process.env.RMQ_URL],
      queue: 'orders_queue',
      queueOptions: { durable: true },
      noAck: false,
    },
  });

  await app.startAllMicroservices();
  await app.listen(3000);
}
```

```ts
// ✅ Lifecycle hook — cleanup connections
@Injectable()
export class AppLifecycle implements OnApplicationShutdown {
  private readonly logger = new Logger(AppLifecycle.name);

  async onApplicationShutdown(signal?: string) {
    this.logger.log(`Shutting down... Signal: ${signal}`);
    // Đợi messages đang xử lý hoàn tất
    // Close connections
  }
}
```

---

## 3. Ví dụ minh họa thực tế

### 3.1. Scenario: E-Commerce Order Flow

Một hệ thống e-commerce với 4 services giao tiếp qua RabbitMQ:

```mermaid
graph LR
    A["API Gateway (HTTP)"] -->|REST| B["Orders Service"]
    B -->|order.created| C["Payments Service"]
    C -->|payment.completed| B
    B -->|order.confirmed| D["Inventory Service"]
    B -->|order.confirmed| E["Notification Service"]
    D -->|stock.reserved| B
    E -->|email.sent| F[("Audit Log")]
```

### 3.2. Step 1: Orders Service — Tạo order và emit event

```ts
// orders/orders.service.ts
@Injectable()
export class OrdersService {
  constructor(
    @Inject('PAYMENTS_SERVICE') private readonly paymentsClient: ClientProxy,
    @Inject('INVENTORY_SERVICE') private readonly inventoryClient: ClientProxy,
    @Inject('NOTIFICATION_SERVICE') private readonly notificationClient: ClientProxy,
    private readonly ordersRepository: OrdersRepository,
  ) {}

  async createOrder(dto: CreateOrderDto, userId: string): Promise<Order> {
    // 1. Validate stock (sync — cần kết quả)
    const stockAvailable = await firstValueFrom(
      this.inventoryClient.send<boolean>('check_stock', {
        items: dto.items,
      }),
    );

    if (!stockAvailable) {
      throw new BadRequestException('Insufficient stock');
    }

    // 2. Create order trong DB
    const order = await this.ordersRepository.create({
      ...dto,
      userId,
      status: OrderStatus.PENDING,
    });

    // 3. Emit event (async — không đợi)
    this.paymentsClient.emit('order_created', {
      messageId: randomUUID(),
      orderId: order.id,
      totalAmount: order.totalAmount,
      userId,
      createdAt: new Date(),
    });

    return order;
  }
}
```

### 3.3. Step 2: Payments Service — Listen và process

```ts
// payments/payments.microservice.controller.ts
@Controller()
export class PaymentsMicroserviceController {
  constructor(private readonly paymentsService: PaymentsService) {}

  // <string> picks the untyped overload; NestJS 12 otherwise rejects a typed @Ctx() param (TS1241)
  @EventPattern<string>('order_created')
  @UsePipes(new ValidationPipe({ whitelist: true, transform: true }))
  async handleOrderCreated(
    @Payload() data: OrderCreatedEvent,
    @Ctx() context: RmqContext,
  ): Promise<void> {
    const channel = context.getChannelRef();
    const originalMsg = context.getMessage();

    try {
      await this.paymentsService.processPayment(data);
      channel.ack(originalMsg);
    } catch (error) {
      // No requeue: send to the DLX configured on the queue (7.1) instead of looping
      channel.nack(originalMsg, false, false);
    }
  }
}
```

### 3.4. Step 3: Event DTOs — Typed contracts

```ts
// shared/events/order-created.event.ts
export class OrderCreatedEvent {
  @IsUUID()
  messageId: string;

  @IsUUID()
  orderId: string;

  @IsNumber()
  @Min(0)
  totalAmount: number;

  @IsUUID()
  userId: string;

  @IsDateString()
  createdAt: string;
}
```

---

## 4. Tooling & Config

### 4.1. RabbitMQ Local Development

```yaml
# docker-compose.yml
services:
  rabbitmq:
    image: rabbitmq:3-management-alpine
    ports:
      - '5672:5672'   # AMQP
      - '15672:15672' # Management UI
    environment:
      RABBITMQ_DEFAULT_USER: admin
      RABBITMQ_DEFAULT_PASS: admin
    volumes:
      - rabbitmq_data:/var/lib/rabbitmq

  kafka:
    image: confluentinc/cp-kafka:7.5.0
    ports:
      - '9092:9092'
    environment:
      KAFKA_NODE_ID: 1
      KAFKA_PROCESS_ROLES: broker,controller
      KAFKA_LISTENERS: PLAINTEXT://0.0.0.0:9092,CONTROLLER://0.0.0.0:9093
      KAFKA_CONTROLLER_QUORUM_VOTERS: 1@kafka:9093
      CLUSTER_ID: 'local-cluster-id'

volumes:
  rabbitmq_data:
```

### 4.2. Package Dependencies

```json
{
  "dependencies": {
    "@nestjs/microservices": "^11.x",
    "amqplib": "^0.10.x",
    "amqp-connection-manager": "^4.x",
    "kafkajs": "^2.x",
    "ioredis": "^5.x"
  }
}
```

`Transport.KAFKA` của NestJS dùng `kafkajs`, package này không có release nào trên npm từ 2023-02-27 (đo ngày 2026-11-13).

### 4.3. Environment Variables

```txt
# .env.example
RMQ_URL=amqp://admin:admin@localhost:5672
ORDERS_QUEUE=orders_queue
PAYMENTS_QUEUE=payments_queue
NOTIFICATIONS_QUEUE=notifications_queue

KAFKA_BROKERS=localhost:9092
KAFKA_CLIENT_ID=my-service
KAFKA_CONSUMER_GROUP=my-consumer-group

REDIS_HOST=localhost
REDIS_PORT=6379
```

### 4.4. Monitoring

- **RabbitMQ Management UI**: `http://localhost:15672` — xem queue depth, message rates, consumers
- **Kafka UI** (akhq/kafka-ui): xem topics, partitions, consumer lag
- **Health Check** — tích hợp `@nestjs/terminus` kiểm tra broker connection

```ts
// health/microservice-health.indicator.ts
// HealthIndicator and HealthCheckError are gone in @nestjs/terminus 12;
// HealthIndicatorService works on terminus 11 and 12.
@Injectable()
export class RabbitMQHealthIndicator {
  constructor(
    private readonly healthIndicatorService: HealthIndicatorService,
    @Inject('ORDERS_SERVICE') private readonly client: ClientProxy,
  ) {}

  async isHealthy(key: string): Promise<HealthIndicatorResult> {
    const indicator = this.healthIndicatorService.check(key);
    try {
      await firstValueFrom(
        this.client.send('health_check', {}).pipe(timeout(3000)),
      );
      return indicator.up();
    } catch {
      return indicator.down('RabbitMQ check failed');
    }
  }
}
```

---

## References

- [NestJS Microservices Documentation](https://docs.nestjs.com/microservices/basics)
- [NestJS RabbitMQ Transport](https://docs.nestjs.com/microservices/rabbitmq)
- [NestJS Kafka Transport](https://docs.nestjs.com/microservices/kafka)
- [NestJS gRPC Transport](https://docs.nestjs.com/microservices/grpc)
- [NestJS Redis Transport](https://docs.nestjs.com/microservices/redis)
- [RabbitMQ Tutorials](https://www.rabbitmq.com/tutorials)
- [Apache Kafka Documentation](https://kafka.apache.org/documentation/)
- [Enterprise Integration Patterns](https://www.enterpriseintegrationpatterns.com/)
- [Node.js Best Practices — Microservices](https://github.com/goldbergyoni/nodebestpractices#6-microservices)

## Changelog

| Date | Version | Change | By |
| :---- | :---- | :---- | :---- |
| 2026-11-18 | v1.0 | Chuyển từ Notion "NestJS Document" (page `33d71a38d3b281dea450e26dfb574e91`, sửa 2026-04-09). Review và sửa nội dung, code trước khi publish. Owner duyệt trong chat ngày 2026-11-18. | Bắc PV |
