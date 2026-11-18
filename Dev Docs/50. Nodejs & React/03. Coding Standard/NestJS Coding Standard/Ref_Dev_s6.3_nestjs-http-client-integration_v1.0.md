# NestJS Coding Standard 6.3 — HTTP Client & Third-party Integration

| Field | Value |
| :---- | :---- |
| Owner | Bắc PV — NodeJS BE Dev Lead |
| Audience | Dev (NodeJS BE) |
| Last reviewed | 2026-11-12 |
| Review cadence | Quarterly |
| Version | v1.0 |
| Linked from | Ref_Dev_nestjs-coding-standard_v1.0 |
| Status | Live |

Doc này là mục 6.3 của [NestJS Coding Standard](Ref_Dev_nestjs-coding-standard_v1.0.md), nhóm Async & Integration. Doc nêu quy tắc về HTTP Client & Third-party Integration trong dự án NestJS, kèm lý do, ví dụ và config. Dev NodeJS BE đọc doc này khi viết code, review code và onboarding.

---

## 1. Tóm tắt & Phạm vi

> 🎯 **Chủ đề**: HTTP Client & Third-party Integration trong NestJS — gọi external APIs, tích hợp dịch vụ bên ngoài, xử lý webhooks.
>
> **Scope**: Áp dụng cho mọi service cần giao tiếp với hệ thống bên ngoài — REST APIs, payment gateways, notification services, webhooks từ third-party.
>
> **Tại sao quan trọng**: Hầu hết ứng dụng thực tế đều phụ thuộc vào external services. Nếu không xử lý đúng: timeout treo request, retry vô hạn gây duplicate, lỗi không log được, secret bị lộ. Thiết kế tốt giúp hệ thống resilient, dễ debug, dễ test.

**Phạm vi bao gồm**:

- HTTP Client: `@nestjs/axios` (`HttpModule` / `HttpService`), cấu hình Axios instances
- Resilience patterns: Timeout, Retry với backoff, Circuit Breaker
- Webhook handling: Nhận webhook, verify signature, idempotency, async processing
- External API integration: Tách service layer, error mapping, secret management
- Observability: Logging request/response, tracing, metrics

---

## 2. Quy tắc & Giải thích

### 2.1 Chọn HTTP client phù hợp

| Use case | Phương thức đề xuất | Giải thích |
| --- | --- | --- |
| Gọi external API từ NestJS service | **`@nestjs/axios`** (`HttpModule` • `HttpService`) | NestJS-native, injectable, configurable per-module, hỗ trợ interceptors. |
| Cần full control, streaming, HTTP/2 | **`undici`** (Node.js built-in từ v18+) | Hiệu suất cao hơn Axios, connection pooling tốt, nhưng API khác biệt. |
| Simple fetch trong scripts/tests | **`node:fetch`** (global fetch) | Có sẵn từ Node.js 18+, đủ cho use cases đơn giản, không cần thêm dependency. |

> **Đề xuất mặc định**: Dùng **`@nestjs/axios`** cho hầu hết dự án NestJS. Chỉ chuyển sang `undici` khi cần streaming hoặc high-throughput đặc biệt.

### 2.2 Cấu hình HttpModule đúng cách

**✅ Nên làm:**

- **Register `HttpModule` per-module** với config riêng cho từng external service
- *Tại sao*: Mỗi service có `baseURL`, timeout, headers khác nhau. Global HttpModule buộc tất cả dùng chung config → conflict.
- **Luôn đặt `timeout`** cho mọi HTTP call (recommend 5–10s, tùy service)
- *Tại sao*: Không có timeout = request có thể treo vĩnh viễn, chiếm connection pool, cascade failure sang các service khác.
- **Đặt `maxRedirects: 5`** (hoặc thấp hơn) để tránh redirect loop
- *Tại sao*: Redirect vô hạn = request chạy mãi, tốn resource.
- **Dùng `registerAsync`** để inject `ConfigService` cho baseURL, API keys
- *Tại sao*: Hard-code URL/key trong code = khó đổi env, lộ secret khi push repo.

```ts
// modules/payment/payment.module.ts
@Module({
  imports: [
    HttpModule.registerAsync({
      inject: [ConfigService],
      useFactory: (config: ConfigService) => ({
        baseURL: config.getOrThrow<string>('PAYMENT_API_URL'),
        timeout: 10_000,
        maxRedirects: 3,
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${config.getOrThrow<string>('PAYMENT_API_KEY')}`,
        },
      }),
    }),
  ],
  providers: [PaymentService],
  exports: [PaymentService],
})
export class PaymentModule {}
```

**❌ Không nên làm:**

- **Không register `HttpModule` global** mà không namespace — các service sẽ share config, gây conflict
- **Không hard-code base URL hoặc API key** trong `HttpModule.register({})` — dùng `ConfigService`
- **Không bỏ qua timeout** — default Axios timeout là `0` (vô hạn)

### 2.3 Tách integration service layer

**✅ Nên làm:**

- **Tạo dedicated service cho mỗi external API**: `PaymentGatewayService`, `NotificationService`, `ShippingApiService`
- *Tại sao*: Single Responsibility — mỗi service chỉ biết cách giao tiếp với 1 external system. Dễ mock trong tests, dễ swap provider.
- **Service chỉ expose domain methods**, không expose raw HTTP calls
- *Tại sao*: Controller/business service không cần biết external API dùng POST hay GET, response format ra sao. Chỉ cần gọi `paymentService.charge(amount)` và nhận typed result.
- **Map external errors → domain exceptions**
- *Tại sao*: Upstream trả `{ error: "insufficient_funds" }` → service map thành `InsufficientFundsException`. Business code không cần hiểu HTTP status codes hay error formats của từng provider.
- **Dùng interfaces cho external service** để dễ swap provider
- *Tại sao*: Khi đổi payment provider (Stripe → VNPay), chỉ cần tạo implementation mới, không đổi business logic.

```ts
// interfaces/payment-gateway.interface.ts
// Provider-neutral results: business code never sees Stripe or partner types
export interface ChargeResult {
  id: string;
  status: 'success' | 'pending' | 'failed';
  amount?: number;
}

export interface RefundResult {
  id: string;
  status: 'success' | 'pending' | 'failed';
}

export interface IPaymentGateway {
  charge(amount: number, currency: string, token: string, idempotencyKey: string): Promise<ChargeResult>;
  refund(chargeId: string, idempotencyKey: string, amount?: number): Promise<RefundResult>;
  verifyWebhook(payload: Buffer, signature: string): boolean;
}

// modules/payment/payment-gateway.service.ts — partner with a JSON REST API.
// HttpService comes from PaymentModule in section 2.2 (baseURL, API key, JSON body).
// Stripe takes form-urlencoded bodies: call it through its SDK instead (section 3.2).
@Injectable()
export class PaymentGatewayService implements IPaymentGateway {
  constructor(
    private readonly httpService: HttpService,
    private readonly configService: ConfigService,
  ) {}

  async charge(amount: number, currency: string, token: string, idempotencyKey: string): Promise<ChargeResult> {
    try {
      const { data } = await firstValueFrom(
        this.httpService.post(
          '/charges',
          { amount, currency, source: token },
          { headers: { 'Idempotency-Key': idempotencyKey } },
        ),
      );
      return { id: data.id, status: data.status };
    } catch (error) {
      throw this.mapError(error as AxiosError);
    }
  }

  async refund(chargeId: string, idempotencyKey: string, amount?: number): Promise<RefundResult> {
    try {
      const { data } = await firstValueFrom(
        this.httpService.post(
          '/refunds',
          { chargeId, amount }, // amount omitted = full refund
          { headers: { 'Idempotency-Key': idempotencyKey } },
        ),
      );
      return { id: data.id, status: data.status };
    } catch (error) {
      throw this.mapError(error as AxiosError);
    }
  }

  // Partner signs the raw body with HMAC-SHA256 and sends the hex digest in a header.
  // createHmac and timingSafeEqual come from node:crypto.
  verifyWebhook(payload: Buffer, signature: string): boolean {
    const secret = this.configService.getOrThrow<string>('PAYMENT_WEBHOOK_SECRET');
    const expected = Buffer.from(createHmac('sha256', secret).update(payload).digest('hex'));
    const received = Buffer.from(signature ?? '');
    // timingSafeEqual throws on different lengths, so compare lengths first
    return expected.length === received.length && timingSafeEqual(expected, received);
  }

  private mapError(error: AxiosError): HttpException {
    const status = error.response?.status;
    const body = error.response?.data as Record<string, any>;

    if (status === 402) {
      return new BadRequestException({
        type: 'DOMAIN_ERROR', // A 400 alone would be typed VALIDATION_ERROR (3.3 section 2.3)
        code: 'PAYMENT_DECLINED',
        message: body?.error?.message ?? 'Payment was declined',
      });
    }
    if (status === 429) {
      return new ServiceUnavailableException('Payment provider rate limited');
    }
    return new InternalServerErrorException('Payment service unavailable');
  }
}
```

**❌ Không nên làm:**

- **Không gọi `httpService.get/post()` trực tiếp từ controller** — luôn qua dedicated service
- **Không trả raw AxiosResponse cho business layer** — map sang typed domain object
- **Không để AxiosError bubble up** đến client — luôn catch và map thành HttpException với context rõ ràng

### 2.4 Xử lý Observable vs Promise

**✅ Nên làm:**

- **Dùng `firstValueFrom()` để convert Observable → Promise**
- *Tại sao*: `HttpService` trả về `Observable<AxiosResponse>`. Trong NestJS service, hầu hết logic là async/await — `firstValueFrom` bridge 2 paradigms sạch sẽ.
- **Dùng `lastValueFrom()` chỉ khi cần giá trị cuối cùng** trong stream có nhiều emissions
- *Tại sao*: Hầu hết HTTP requests chỉ emit 1 lần → `firstValueFrom` đủ và rõ ý hơn.

```ts
import { firstValueFrom } from 'rxjs';

// ✅ Good — clean async/await
async getUser(id: string): Promise<UserDto> {
  const { data } = await firstValueFrom(
    this.httpService.get<ExternalUserResponse>(`/users/${id}`),
  );
  return this.mapToUserDto(data);
}
```

**❌ Không nên làm:**

- **Không `.toPromise()`** — deprecated từ RxJS 7
- **Không `.subscribe()` trong service rồi resolve promise manually** — phức tạp, dễ leak subscription

### 2.5 Retry, Timeout & Circuit Breaker

**✅ Nên làm:**

- **Retry với exponential backoff** cho transient errors (5xx, network errors, timeout)
- *Tại sao*: External service có thể tạm unavailable. Retry tự động giúp tăng reliability mà user không cần action gì.
- **Chỉ retry idempotent operations** (GET, PUT) — không retry POST tạo resource (trừ khi có idempotency key)
- *Tại sao*: Retry POST mà không có idempotency key = tạo duplicate orders, double charge.
- **Giới hạn số lần retry** (2–3 lần) và tổng thời gian chờ
- *Tại sao*: Retry quá nhiều = user chờ lâu, tốn resource. Nếu service down, retry không giúp được.
- **Circuit breaker** cho external services critical: mở circuit khi error rate cao, tránh cascade failure
- *Tại sao*: Khi downstream service chết, tiếp tục gọi = tốn timeout × requests, chậm toàn hệ thống. Circuit breaker fail-fast → trả lỗi ngay.

```ts
import { catchError, retry, timer } from 'rxjs';

// Retry với exponential backoff
async callWithRetry<T>(request$: Observable<AxiosResponse<T>>): Promise<T> {
  const { data } = await firstValueFrom(
    request$.pipe(
      retry({
        count: 3,
        delay: (error, retryCount) => {
          // Chỉ retry transient errors
          const status = error?.response?.status;
          if (status && status < 500 && status !== 429) {
            throw error; // 4xx (trừ 429) = client error, không retry
          }
          const delayMs = Math.pow(2, retryCount) * 1000; // 2s, 4s, 8s
          return timer(delayMs);
        },
      }),
      catchError((error) => {
        this.logger.error(
          `External API failed after retries: ${error.message}`,
          error.stack,
        );
        throw this.mapError(error);
      }),
    ),
  );
  return data;
}
```

```ts
// Simple circuit breaker state machine.
// Plain class, not a provider: Nest DI cannot resolve the `number` constructor params.
// One instance per external service: `private readonly breaker = new CircuitBreaker(5, 30_000);`
export class CircuitBreaker {
  private failures = 0;
  private lastFailure: number | null = null;
  private state: 'closed' | 'open' | 'half-open' = 'closed';

  constructor(
    private readonly threshold: number = 5,
    private readonly resetTimeMs: number = 30_000,
  ) {}

  async execute<T>(fn: () => Promise<T>): Promise<T> {
    if (this.state === 'open') {
      if (Date.now() - (this.lastFailure ?? 0) > this.resetTimeMs) {
        this.state = 'half-open';
      } else {
        throw new ServiceUnavailableException('Circuit breaker is open');
      }
    }

    try {
      const result = await fn();
      this.onSuccess();
      return result;
    } catch (error) {
      this.onFailure();
      throw error;
    }
  }

  private onSuccess(): void {
    this.failures = 0;
    this.state = 'closed';
  }

  private onFailure(): void {
    this.failures++;
    this.lastFailure = Date.now();
    if (this.failures >= this.threshold) {
      this.state = 'open';
    }
  }
}
```

**❌ Không nên làm:**

- **Không retry mọi error** — 400 Bad Request, 401 Unauthorized, 404 Not Found không cần retry
- **Không retry POST/PATCH** tạo/thay đổi resource mà không có idempotency key
- **Không retry vô hạn** — giới hạn 2–3 lần + tổng timeout
- **Không bỏ qua backoff** — retry liên tục gây thêm áp lực cho service đang overload

### 2.6 Webhook handling

**✅ Nên làm:**

- **Verify webhook signature** trước khi xử lý payload
- *Tại sao*: Không verify = attacker có thể gửi fake webhook, trigger business logic sai (fake payment success, fake order).
- **Trả 200/202 ngay** trước khi xử lý heavy logic — đẩy vào queue xử lý async
- *Tại sao*: Webhook sender thường có timeout ngắn (5–15s). Xử lý lâu = sender retry → duplicate processing.
- **Idempotency**: Lưu webhook event ID, skip nếu đã xử lý
- *Tại sao*: Sender có thể gửi lại cùng event (retry, at-least-once delivery). Không check = duplicate side effects.
- **Dùng raw body** để verify signature — parsed body có thể khác raw bytes
- *Tại sao*: HMAC signature tính trên raw bytes. JSON parse → stringify có thể thay đổi whitespace, key order.
- **Log mọi webhook event** (event type, ID, timestamp) để debug và audit

```ts
// webhooks/stripe-webhook.controller.ts
@Controller('webhooks/stripe')
export class StripeWebhookController {
  private readonly logger = new Logger(StripeWebhookController.name);

  constructor(
    private readonly webhookService: StripeWebhookService,
    @InjectQueue('payment-webhooks') private readonly webhookQueue: Queue,
  ) {}

  @Post()
  @HttpCode(HttpStatus.OK)
  async handleWebhook(
    @Headers('stripe-signature') signature: string,
    @Req() req: RawBodyRequest<Request>,
  ): Promise<{ received: true }> {
    // 1. Verify signature với raw body
    const event = this.webhookService.verifySignature(
      req.rawBody,
      signature,
    );

    this.logger.log(`Webhook received: ${event.type} (${event.id})`);

    // 2. Idempotency check
    if (await this.webhookService.isProcessed(event.id)) {
      this.logger.warn(`Duplicate webhook skipped: ${event.id}`);
      return { received: true };
    }

    // 3. Enqueue for async processing — trả response ngay
    await this.webhookQueue.add(
      'stripe-event',
      {
        eventId: event.id,
        eventType: event.type,
        payload: event.data,
      },
      // Same jobId → BullMQ keeps one job, so two concurrent deliveries
      // that both pass isProcessed() still enqueue the event once
      { jobId: event.id },
    );

    return { received: true };
  }
}
```

```ts
// Verify the Stripe signature with the SDK (this.stripe: Stripe client from the `stripe` package).
// constructEvent parses `Stripe-Signature: t=…,v1=…`, checks the HMAC of `${t}.${rawBody}`
// in constant time and rejects events older than 300s (default tolerance).
verifySignature(rawBody: Buffer | undefined, signature: string): Stripe.Event {
  if (!rawBody) {
    // req.rawBody is only set with NestFactory.create(AppModule, { rawBody: true })
    throw new BadRequestException('Missing raw body');
  }
  const secret = this.configService.getOrThrow<string>('STRIPE_WEBHOOK_SECRET');

  try {
    return this.stripe.webhooks.constructEvent(rawBody, signature, secret);
  } catch {
    throw new UnauthorizedException('Invalid webhook signature');
  }
}
```

**❌ Không nên làm:**

- **Không xử lý webhook mà không verify signature** — fake webhook = security vulnerability
- **Không xử lý synchronous heavy logic** trong webhook handler — trả response chậm → sender retry → duplicate
- **Không bỏ qua idempotency check** — webhook sender gửi lại = double processing
- **Không dùng `JSON.parse(body)` để verify signature** — dùng raw body (Buffer)
- **Không dùng `===` để so sánh signature** — dùng `crypto.timingSafeEqual` để chống timing attacks

### 2.7 Logging & Observability cho external calls

**✅ Nên làm:**

- **Log request/response** cho mọi external call: method, URL, status, duration
- *Tại sao*: External call fail là nguồn bug phổ biến nhất. Không log = debug mù.
- **Axios interceptors** cho logging, tracing, error transform
- *Tại sao*: Centralize cross-cutting logic — không cần lặp log ở mỗi method call.
- **Không log sensitive data**: Authorization headers, API keys, request bodies chứa PII
- *Tại sao*: Log file có thể truy cập bởi nhiều người/hệ thống. Lộ key = security incident.
- **Track latency metrics** cho mỗi external service
- *Tại sao*: Phát hiện external service chậm dần trước khi thành incident.

```ts
// Axios interceptor cho logging
this.httpService.axiosRef.interceptors.request.use((config) => {
  config['metadata'] = { startTime: Date.now() };
  this.logger.debug(
    `→ ${config.method?.toUpperCase()} ${config.baseURL}${config.url}`,
  );
  return config;
});

this.httpService.axiosRef.interceptors.response.use(
  (response) => {
    const duration = Date.now() - response.config['metadata'].startTime;
    this.logger.log(
      `← ${response.status} ${response.config.method?.toUpperCase()} ` +
      `${response.config.baseURL}${response.config.url} (${duration}ms)`,
    );
    return response;
  },
  (error: AxiosError) => {
    const duration = Date.now() - error.config?.['metadata']?.startTime;
    this.logger.error(
      `← ${error.response?.status ?? 'NETWORK_ERROR'} ` +
      `${error.config?.method?.toUpperCase()} ` +
      `${error.config?.baseURL}${error.config?.url} (${duration}ms)`,
    );
    throw error;
  },
);
```

**❌ Không nên làm:**

- **Không log full request/response body** mặc định — chỉ log khi debug, redact sensitive fields
- **Không log Authorization header, API key, access token**
- **Không bỏ qua error logging** — external call fail mà không log = invisible failures

### 2.8 Secret & credential management

**✅ Nên làm:**

- **Mọi API key, secret, token đều qua `ConfigService`** — không hard-code, không `process.env` trực tiếp
- **Validate tất cả required secrets khi app start** (Joi schema) — fail-fast nếu thiếu
- **Rotate keys định kỳ** — support multiple keys đồng thời (old + new) trong transition period
- **Dùng `getOrThrow()`** cho required config — không dùng `get()` rồi bỏ qua `undefined`

**❌ Không nên làm:**

- **Không commit `.env` files** với credentials thật — chỉ commit `.env.example`
- **Không log credentials** kể cả khi init/debug
- **Không share API key** giữa nhiều external services — mỗi service 1 key riêng

---

## 3. Ví dụ minh họa thực tế

### 3.1 Walkthrough: Tích hợp Payment Gateway + Webhook

**Cấu trúc thư mục:**

```txt
src/modules/payment/
├── payment.module.ts              # HttpModule.registerAsync + providers
├── payment.controller.ts          # User-facing endpoints: create charge, refund
├── payment.service.ts             # Business logic: orchestrate charge flow
├── gateways/
│   ├── payment-gateway.interface.ts  # IPaymentGateway — swap provider dễ dàng
│   └── stripe-gateway.service.ts     # Stripe implementation
├── webhooks/
│   ├── stripe-webhook.controller.ts  # Receive + verify + enqueue
│   └── stripe-webhook.processor.ts   # BullMQ processor — async handling
├── dto/
│   ├── create-charge.dto.ts
│   ├── charge-response.dto.ts
│   └── refund.dto.ts
├── exceptions/
│   ├── payment-declined.exception.ts
│   └── payment-gateway-error.exception.ts
└── interfaces/
    ├── charge-result.interface.ts
    └── stripe-event.interface.ts
```

### 3.2 Before/After: Từ code thiếu resilience → code production-ready

**❌ Before — Không resilient, không separation:**

```ts
// Mọi thứ trong controller, không timeout, không retry, không error mapping
@Controller('payments')
export class PaymentsController {
  constructor(private readonly httpService: HttpService) {}

  @Post('charge')
  async charge(@Body() body: any) {
    // Hard-code URL + API key
    const result = await this.httpService.post(
      'https://api.stripe.com/v1/charges',
      body,
      { headers: { Authorization: 'Bearer sk_live_xxx' } },
    ).toPromise(); // deprecated!

    return result.data; // Raw response — lộ internal data
  }

  @Post('webhook')
  async webhook(@Body() body: any) {
    // Không verify signature!
    // Xử lý sync — chậm → sender retry → duplicate
    if (body.type === 'charge.succeeded') {
      await this.processChargeSuccess(body.data); // Có thể mất 30s
    }
    return { ok: true };
  }
}
```

**Vấn đề:**

1. Hard-code API key trong source code
2. Không timeout — external call có thể treo vĩnh viễn
3. `.toPromise()` deprecated từ RxJS 7
4. Không verify webhook signature — attacker gửi fake webhook được
5. Sync processing trong webhook handler — timeout → sender retry → duplicate
6. `body: any` — không validate
7. Trả raw external response — lộ internal structure
8. Không error mapping — AxiosError leak ra client

**✅ After — Production-ready:**

```ts
// payment.module.ts — config từ env, có timeout
@Module({
  imports: [
    BullModule.registerQueue({ name: 'payment-webhooks' }),
  ],
  controllers: [PaymentController, StripeWebhookController],
  providers: [
    {
      // Stripe SDK client: form-urlencoded body, typed errors, webhook verification
      provide: Stripe,
      inject: [ConfigService],
      useFactory: (config: ConfigService) =>
        new Stripe(config.getOrThrow<string>('STRIPE_SECRET_KEY'), {
          timeout: 10_000,
          maxNetworkRetries: 2, // Retries network errors, 409 and 5xx with backoff
        }),
    },
    PaymentService,
    { provide: 'IPaymentGateway', useClass: StripeGatewayService },
    StripeWebhookService,
    StripeWebhookProcessor,
  ],
  exports: [PaymentService],
})
export class PaymentModule {}
```

```ts
// gateways/stripe-gateway.service.ts — dedicated service, retry, error mapping
@Injectable()
export class StripeGatewayService implements IPaymentGateway {
  private readonly logger = new Logger(StripeGatewayService.name);

  constructor(
    private readonly stripe: Stripe,
    private readonly configService: ConfigService,
  ) {
    this.setupLogging();
  }

  async charge(amount: number, currency: string, token: string, idempotencyKey: string): Promise<ChargeResult> {
    try {
      const charge = await this.stripe.charges.create(
        { amount, currency, source: token },
        // One key per payment attempt: PaymentService creates it and stores it on the
        // order before the first call, then reuses it on every retry (job retry,
        // resubmit after a timeout). Stripe returns the first result instead of charging twice.
        { idempotencyKey },
      );

      return {
        id: charge.id,
        status: charge.status === 'succeeded' ? 'success' : 'pending',
        amount: charge.amount,
      };
    } catch (error) {
      throw this.mapError(error);
    }
  }

  async refund(chargeId: string, idempotencyKey: string, amount?: number): Promise<RefundResult> {
    try {
      // amount omitted = full refund; the key follows the same rule as charge()
      const refund = await this.stripe.refunds.create({ charge: chargeId, amount }, { idempotencyKey });
      return { id: refund.id, status: this.mapRefundStatus(refund.status) };
    } catch (error) {
      throw this.mapError(error);
    }
  }

  verifyWebhook(payload: Buffer, signature: string): boolean {
    try {
      // Same check as StripeWebhookService.verifySignature in section 2.6
      this.stripe.webhooks.constructEvent(
        payload,
        signature,
        this.configService.getOrThrow<string>('STRIPE_WEBHOOK_SECRET'),
      );
      return true;
    } catch {
      return false;
    }
  }

  // Stripe refund status: pending | requires_action | succeeded | failed | canceled
  private mapRefundStatus(status: string | null): RefundResult['status'] {
    if (status === 'succeeded') return 'success';
    if (status === 'failed' || status === 'canceled') return 'failed';
    return 'pending';
  }

  private mapError(error: unknown): HttpException {
    if (error instanceof Stripe.errors.StripeCardError) {
      return new PaymentDeclinedException(error.decline_code ?? 'unknown');
    }
    if (error instanceof Stripe.errors.StripeRateLimitError) {
      return new ServiceUnavailableException('Payment provider rate limited');
    }
    this.logger.error('Stripe API error', error instanceof Error ? error.stack : String(error));
    return new PaymentGatewayErrorException('Payment service unavailable');
  }

  private setupLogging(): void {
    this.stripe.on('response', (event: Stripe.ResponseEvent) => {
      this.logger.log(`← ${event.status} ${event.method} ${event.path} (${event.elapsed}ms)`);
    });
  }
}
```

```ts
// webhooks/stripe-webhook.controller.ts — verify + idempotent + async
@Controller('webhooks/stripe')
export class StripeWebhookController {
  private readonly logger = new Logger(StripeWebhookController.name);

  constructor(
    private readonly webhookService: StripeWebhookService,
    @InjectQueue('payment-webhooks') private readonly queue: Queue,
  ) {}

  @Post()
  @HttpCode(HttpStatus.OK)
  async handle(
    @Headers('stripe-signature') signature: string,
    @Req() req: RawBodyRequest<Request>,
  ): Promise<{ received: true }> {
    const event = this.webhookService.verifyAndParse(req.rawBody, signature);
    this.logger.log(`Webhook: ${event.type} (${event.id})`);

    if (await this.webhookService.isDuplicate(event.id)) {
      this.logger.warn(`Duplicate skipped: ${event.id}`);
      return { received: true };
    }

    await this.queue.add(
      event.type,
      {
        eventId: event.id,
        type: event.type,
        data: event.data,
      },
      { jobId: event.id }, // Concurrent duplicates enqueue one job
    );

    return { received: true };
  }
}
```

**Cải thiện:**

1. Config từ env qua `ConfigService` — không hard-code
2. Timeout 10s — không bao giờ treo vĩnh viễn
3. SDK `stripe` thay HTTP call tự viết; `idempotencyKey` cho mỗi charge — retry không charge hai lần
4. Verify webhook signature bằng `stripe.webhooks.constructEvent()`
5. Async processing qua BullMQ queue — trả response ngay
6. Idempotency check + `jobId: event.id` — skip duplicate events
7. Typed DTOs — validate input
8. Error mapping — domain exceptions thay vì raw Stripe error
9. Log latency qua `stripe.on('response')` — debug failures

---

## 4. Tooling & Config

### 4.1 Packages cần cài

```bash
# HTTP Client (NestJS native)
pnpm add @nestjs/axios axios

# Stripe SDK (charge + webhook verification)
pnpm add stripe

# Queue cho async webhook processing
pnpm add @nestjs/bullmq bullmq

# Retry/resilience (optional — nếu cần advanced patterns)
pnpm add nestjs-resilience  # Circuit breaker, retry, timeout decorators

# Validation (nếu chưa có)
pnpm add class-validator class-transformer
```

### 4.2 Environment variables

```txt
# .env.example

# Payment Gateway (Stripe)
STRIPE_SECRET_KEY=sk_test_xxx
STRIPE_WEBHOOK_SECRET=whsec_xxx

# Notification Service
NOTIFICATION_API_URL=https://api.notification.internal
NOTIFICATION_API_KEY=notif-key-xxx

# Shipping Provider
SHIPPING_API_URL=https://api.ghn.vn/home/api/v2
SHIPPING_API_TOKEN=token-xxx

# HTTP Client defaults
HTTP_TIMEOUT=10000
HTTP_MAX_REDIRECTS=5

# Redis queue for the BullMQ webhook queue: kept apart from the cache Redis (6.1 section 4.2)
REDIS_QUEUE_HOST=localhost
REDIS_QUEUE_PORT=6380
REDIS_QUEUE_PASSWORD=
```

### 4.3 Enable raw body cho webhook endpoints

```ts
// main.ts — cần raw body để verify HMAC signature
const app = await NestFactory.create(AppModule, {
  rawBody: true, // Enable raw body globally
});
```

### 4.4 Config validation (Joi)

```ts
// config/validation.schema.ts — thêm external service configs
export const validationSchema = Joi.object({
  // ... other configs
  STRIPE_SECRET_KEY: Joi.string().required(),
  STRIPE_WEBHOOK_SECRET: Joi.string().required(),
  HTTP_TIMEOUT: Joi.number().default(10000),
  HTTP_MAX_REDIRECTS: Joi.number().default(5),
});
```

### 4.5 Testing external services

```ts
// Dùng dependency injection để mock external service trong tests
describe('PaymentService', () => {
  let service: PaymentService;
  let mockGateway: jest.Mocked<IPaymentGateway>;

  beforeEach(async () => {
    mockGateway = {
      charge: jest.fn(),
      refund: jest.fn(),
      verifyWebhook: jest.fn(),
    };

    const module = await Test.createTestingModule({
      providers: [
        PaymentService,
        { provide: 'IPaymentGateway', useValue: mockGateway },
      ],
    }).compile();

    service = module.get(PaymentService);
  });

  it('should charge successfully', async () => {
    mockGateway.charge.mockResolvedValue({
      id: 'ch_123', status: 'success', amount: 50000,
    });

    const result = await service.createCharge({
      amount: 50000, currency: 'vnd', token: 'tok_xxx',
    });

    expect(result.status).toBe('success');
    expect(mockGateway.charge).toHaveBeenCalledTimes(1);
  });
});
```

---

## References

- [NestJS HTTP Module docs](https://docs.nestjs.com/techniques/http-module)
- [Axios documentation](https://axios-http.com/docs/intro)
- [NestJS Events (Event Emitter)](https://docs.nestjs.com/techniques/events)
- [BullMQ — Queue for Node.js](https://docs.bullmq.io/)
- [nestjs-resilience — Circuit breaker, retry patterns](https://github.com/SocketSomeone/nestjs-resilience)
- [RxJS ](https://rxjs.dev/api/index/function/firstValueFrom)[`firstValueFrom`](https://rxjs.dev/api/index/function/firstValueFrom)
- [OWASP Webhook Security](https://cheatsheetseries.owasp.org/cheatsheets/Webhook_Security_Cheat_Sheet.html)
- [Stripe Webhook Signature Verification](https://stripe.com/docs/webhooks/signatures)
- [Node.js undici — HTTP/1.1 client](https://undici.nodejs.org/)
- [Circuit Breaker Pattern (Martin Fowler)](https://martinfowler.com/bliki/CircuitBreaker.html)

## Changelog

| Date | Version | Change | By |
| :---- | :---- | :---- | :---- |
| 2026-11-18 | v1.0 | Chuyển từ Notion "NestJS Document" (page `33d71a38d3b2816eb172cc3b0f2d1c47`, sửa 2026-04-09). Review và sửa nội dung, code trước khi publish. Owner duyệt trong chat ngày 2026-11-18. | Bắc PV |
