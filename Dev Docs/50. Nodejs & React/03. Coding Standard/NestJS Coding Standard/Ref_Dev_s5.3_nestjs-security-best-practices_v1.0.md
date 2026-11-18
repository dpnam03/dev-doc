# NestJS Coding Standard 5.3 — Security Best Practices

| Field | Value |
| :---- | :---- |
| Owner | Bắc PV — NodeJS BE Dev Lead |
| Audience | Dev (NodeJS BE) |
| Last reviewed | 2026-11-12 |
| Review cadence | Quarterly |
| Version | v1.0 |
| Linked from | Ref_Dev_nestjs-coding-standard_v1.0 |
| Status | Live |

Doc này là mục 5.3 của [NestJS Coding Standard](Ref_Dev_nestjs-coding-standard_v1.0.md), nhóm Security. Doc nêu quy tắc về Security Best Practices trong dự án NestJS, kèm lý do, ví dụ và config. Dev NodeJS BE đọc doc này khi viết code, review code và onboarding.

---

## 1. Tóm tắt & Phạm vi

**Chủ đề:** Security Best Practices trong NestJS — bảo vệ ứng dụng khỏi các attack vectors phổ biến: XSS, clickjacking, CSRF, brute-force, injection, và data leaks thông qua HTTP security headers, CORS, rate limiting, input sanitization, và encryption.

**Vấn đề giải quyết:**

- Ứng dụng thiếu security headers → dễ bị XSS, clickjacking, MIME-sniffing.
- CORS cấu hình sai (`origin: '*'` trên production) → cho phép mọi domain gọi API.
- Không rate limit → brute-force login, spam endpoints, DDoS layer 7.
- Input không sanitize → stored XSS khi render HTML/rich text.
- Dữ liệu nhạy cảm lưu plaintext → lộ khi DB bị compromise.
- CSRF không phòng chống → attacker giả mạo request từ browser đã authenticate.

**Phạm vi áp dụng:** Tất cả NestJS REST APIs, đặc biệt ứng dụng có: user auth (JWT/session), public-facing endpoints, form-based workflows, hoặc lưu trữ dữ liệu nhạy cảm.

**Tại sao quan trọng:**

- Security headers là “lớp phòng thủ miễn phí” — thêm vài dòng config nhưng chặn hàng loạt attack vectors.
- CORS đúng ngăn cross-origin abuse mà không ảnh hưởng legitimate clients.
- Rate limiting bảo vệ availability và ngăn credential stuffing.
- Encryption at rest bảo vệ data ngay cả khi DB/backup bị lộ.

---

## 2. Quy tắc & Giải thích

### 2.1. Security Headers với Helmet

**✅ NÊN:** Dùng `helmet` để tự động thêm security headers cho mọi response.

```ts
// main.ts
import helmet from 'helmet';

async function bootstrap() {
  const app = await NestFactory.create(AppModule);

  // Helmet thêm ~15 security headers mặc định
  app.use(helmet({
    contentSecurityPolicy: {
      directives: {
        defaultSrc: ["'self'"],
        scriptSrc: ["'self'"],
        styleSrc: ["'self'", "'unsafe-inline'"],
        imgSrc: ["'self'", 'data:', 'https:'],
        connectSrc: ["'self'"],
        fontSrc: ["'self'"],
        objectSrc: ["'none'"],
        frameSrc: ["'none'"],
      },
    },
    crossOriginEmbedderPolicy: false, // Tắt nếu cần load cross-origin resources
  }));

  await app.listen(3000);
}
```

**❌ KHÔNG NÊN:** Bỏ qua security headers hoặc tắt Helmet hoàn toàn.

```ts
// ❌ Bad — không có security headers
async function bootstrap() {
  const app = await NestFactory.create(AppModule);
  await app.listen(3000); // Thiếu Helmet → XSS, clickjacking, MIME-sniffing
}

// ❌ Bad — tắt tất cả protections
app.use(helmet({ contentSecurityPolicy: false, frameguard: false }));
```

*Tại sao:* Helmet thêm các headers quan trọng:

| **Header** | **Chức năng** | **Chặn attack** |
| --- | --- | --- |
| `X-Content-Type-Options: nosniff` | Ngăn browser đoán MIME type | MIME-sniffing |
| `X-Frame-Options: SAMEORIGIN` | Chặn embed trong iframe | Clickjacking |
| `Strict-Transport-Security` | Bắt buộc HTTPS | SSL stripping |
| `Content-Security-Policy` | Kiểm soát nguồn resource | XSS, injection |
| `X-DNS-Prefetch-Control: off` | Tắt DNS prefetch | Privacy leak |
| `Referrer-Policy` | Kiểm soát referrer header | Information leak |

**Ngoại lệ — Shopify embedded app:** app chạy trong iframe của Shopify Admin, nên phải tắt `frameguard` (`X-Frame-Options`) và giới hạn trang được nhúng bằng CSP `frame-ancestors https://{shop}.myshopify.com https://admin.shopify.com` theo [hướng dẫn của Shopify](https://shopify.dev/docs/apps/build/security/set-up-iframe-protection). App không nhúng trong iframe giữ `frameguard` bật.

```ts
// main.ts — Shopify embedded app only
const SHOP_DOMAIN = /^[a-z0-9][a-z0-9-]*\.myshopify\.com$/i;

app.use(helmet({
  frameguard: false, // X-Frame-Options would block the Shopify Admin iframe
  contentSecurityPolicy: {
    directives: {
      // Per request: allow only the shop that loads the app, plus Shopify Admin
      frameAncestors: [
        (req) => {
          const shop = new URL(req.url ?? '/', 'http://localhost').searchParams.get('shop');
          return shop && SHOP_DOMAIN.test(shop)
            ? `https://${shop} https://admin.shopify.com`
            : "'none'";
        },
      ],
    },
  },
}));
```

> **Tham khảo:** [Helmet.js](https://helmetjs.github.io/) · [OWASP Secure Headers](https://owasp.org/www-project-secure-headers/)

---

### 2.2. CORS — Cross-Origin Resource Sharing

**✅ NÊN:** Cấu hình CORS theo môi trường, whitelist chính xác domain.

```ts
// main.ts
import { ConfigService } from '@nestjs/config';

async function bootstrap() {
  const app = await NestFactory.create(AppModule);
  const configService = app.get(ConfigService);

  app.enableCors({
    // Whitelist chính xác — không dùng wildcard trên production
    origin: configService.getOrThrow<string>('CORS_ORIGINS').split(','),
    methods: ['GET', 'POST', 'PATCH', 'DELETE', 'OPTIONS'],
    allowedHeaders: ['Content-Type', 'Authorization', 'X-Api-Key'],
    credentials: true,
    maxAge: 86400, // Preflight cache 24h — giảm OPTIONS requests
  });

  await app.listen(3000);
}
```

```bash
# .env (local)
CORS_ORIGINS=http://localhost:3000,http://localhost:5173

# .env.production
CORS_ORIGINS=https://app.example.com,https://admin.example.com
```

**❌ KHÔNG NÊN:** Dùng wildcard hoặc reflect origin trên production.

```ts
// ❌ Bad — cho phép MỌI domain
app.enableCors({ origin: '*' });

// ❌ Bad — reflects any request origin; with credentials, any site reads responses made with the user's cookie
app.enableCors({ origin: true, credentials: true });

// ❌ Bad — credentials + wildcard = browser sẽ block
app.enableCors({ origin: '*', credentials: true });
```

*Tại sao:* CORS quyết định trang web nào được đọc response của API. Với `'*'`, browser không cho đọc response của request có cookie, nên chỉ lộ data public. Rủi ro thật là reflect origin kèm `credentials: true`: trang của attacker đọc được response bằng cookie của user đã login.

**Dynamic CORS cho multi-tenant:**

```ts
// Nếu cần dynamic origin (multi-tenant, partner APIs)
app.enableCors({
  origin: (origin, callback) => {
    const allowedOrigins = configService
      .getOrThrow<string>('CORS_ORIGINS')
      .split(',');

    // Cho phép requests không có origin (mobile apps, curl, server-to-server)
    if (!origin || allowedOrigins.includes(origin)) {
      callback(null, true);
    } else {
      callback(new Error(`Origin ${origin} not allowed by CORS`));
    }
  },
  credentials: true,
});
```

> **Tham khảo:** [NestJS CORS](https://docs.nestjs.com/security/cors) · [MDN CORS](https://developer.mozilla.org/en-US/docs/Web/HTTP/CORS)

---

### 2.3. Rate Limiting với @nestjs/throttler

**✅ NÊN:** Áp dụng rate limiting global + stricter limits cho sensitive endpoints.

```ts
// app.module.ts
import { ThrottlerModule, ThrottlerGuard } from '@nestjs/throttler';
import { APP_GUARD } from '@nestjs/core';

@Module({
  imports: [
    ThrottlerModule.forRoot([{
      name: 'short',
      ttl: 1000,   // 1 giây
      limit: 3,    // Max 3 requests/giây
    }, {
      name: 'medium',
      ttl: 10000,  // 10 giây
      limit: 20,   // Max 20 requests/10 giây
    }, {
      name: 'long',
      ttl: 60000,  // 1 phút
      limit: 100,  // Max 100 requests/phút
    }]),
  ],
  providers: [{
    provide: APP_GUARD,
    useClass: ThrottlerGuard,
  }],
})
export class AppModule {}
```

**Stricter limits cho auth endpoints:**

```ts
import { Throttle, SkipThrottle } from '@nestjs/throttler';

@Controller('auth')
export class AuthController {
  // Login: chỉ 5 lần/phút — chống brute-force
  @Public()
  @Post('login')
  @Throttle({ short: { limit: 1, ttl: 1000 }, long: { limit: 5, ttl: 60000 } })
  async login(@Body() dto: LoginDto, @Res({ passthrough: true }) res: Response) {
    // ...sets the auth cookies, see 5.1 section 3.2
  }

  // Forgot password: 3 lần/phút — chống email spam
  @Post('forgot-password')
  @Throttle({ long: { limit: 3, ttl: 60000 } })
  async forgotPassword(@Body() dto: ForgotPasswordDto) {
    return this.authService.forgotPassword(dto);
  }

  // Health check: không cần rate limit
  @Get('health')
  @SkipThrottle({ short: true, medium: true, long: true }) // Bare @SkipThrottle() skips only 'default'
  health() {
    return { status: 'ok' };
  }
}
```

**Redis storage cho multi-instance** — dùng `@nest-lab/throttler-storage-redis`, không tự viết storage:

```ts
// app.module.ts — pnpm add @nest-lab/throttler-storage-redis ioredis
import { Module } from '@nestjs/common';
import { APP_GUARD } from '@nestjs/core';
import { ConfigService } from '@nestjs/config';
import { ThrottlerGuard, ThrottlerModule } from '@nestjs/throttler';
import { ThrottlerStorageRedisService } from '@nest-lab/throttler-storage-redis';

@Module({
  imports: [
    ThrottlerModule.forRootAsync({
      inject: [ConfigService],
      useFactory: (configService: ConfigService) => ({
        throttlers: [
          { name: 'short', ttl: 1000, limit: 3 },
          { name: 'medium', ttl: 10000, limit: 20 },
          { name: 'long', ttl: 60000, limit: 100 },
        ],
        // Shared counters across instances; the in-memory default counts per instance
        storage: new ThrottlerStorageRedisService({
          host: configService.getOrThrow<string>('REDIS_HOST'),
          port: configService.getOrThrow<number>('REDIS_PORT'),
          password: configService.get<string>('REDIS_PASSWORD'),
        }),
      }),
    }),
  ],
  providers: [{ provide: APP_GUARD, useClass: ThrottlerGuard }],
})
export class AppModule {}
```

**❌ KHÔNG NÊN:** Không rate limit hoặc dùng cùng limit cho tất cả endpoints.

```ts
// ❌ Bad — không rate limit → brute-force thoải mái
@Post('login')
async login(@Body() dto: LoginDto) { ... }

// ❌ Bad — skip rate limit cho auth endpoint
@Post('login')
@SkipThrottle()
async login(@Body() dto: LoginDto) { ... }
```

*Tại sao:* Rate limiting là tuyến phòng thủ đầu tiên chống:

- **Brute-force**: Thử hàng triệu password combinations.
- **Credential stuffing**: Dùng leaked email/password lists.
- **DDoS layer 7**: Flood requests hợp lệ.
- **Email/SMS spam**: Abuse forgot-password hoặc OTP endpoints.

> **Tham khảo:** [NestJS Rate Limiting](https://docs.nestjs.com/security/rate-limiting) · [@nestjs/throttler](https://github.com/nestjs/throttler)

---

### 2.4. CSRF Protection

**✅ NÊN:** Cookie auth đặt `SameSite=Strict` (mục 2.7) và whitelist CORS origin (mục 2.2), giống doc Chuẩn thiết kế REST API và project v535. Như vậy là đủ chống CSRF, không cần thêm token. Frontend khác subdomain nhưng cùng domain gốc vẫn tính là same-site.

Chỉ thêm `csrf-csrf` (`doubleCsrf`) khi cookie auth buộc phải đặt `SameSite=None`, ví dụ frontend ở domain khác hẳn. Không dùng `csurf` — package đã archived và deprecated.

```ts
// main.ts — only when the auth cookie must be SameSite=None
import { ForbiddenException } from '@nestjs/common';
import cookieParser from 'cookie-parser';
import { doubleCsrf } from 'csrf-csrf';
import type { NextFunction, Request, Response } from 'express';

async function bootstrap() {
  const app = await NestFactory.create(AppModule);
  const configService = app.get(ConfigService);

  const { doubleCsrfProtection, invalidCsrfTokenError } = doubleCsrf({
    getSecret: () => configService.getOrThrow<string>('CSRF_SECRET'),
    // Bind the CSRF token to the auth cookie so another session cannot reuse it.
    // The frontend re-fetches the CSRF token after the access token is refreshed.
    getSessionIdentifier: (req) => req.cookies['accessToken'] ?? '',
    cookieOptions: { sameSite: 'strict', secure: true, httpOnly: true },
  });

  app.use(cookieParser()); // Must run before doubleCsrfProtection, which reads req.cookies
  // Checks the x-csrf-token header on POST/PUT/PATCH/DELETE; GET/HEAD/OPTIONS are skipped.
  // Cross-origin frontend: add 'X-CSRF-Token' to CORS allowedHeaders.
  // Rethrown as ForbiddenException, otherwise a global @Catch() filter (see 1.2) answers 500.
  app.use((req: Request, res: Response, next: NextFunction) =>
    doubleCsrfProtection(req, res, (err?: unknown) =>
      next(err === invalidCsrfTokenError ? new ForbiddenException('Invalid CSRF token') : err),
    ),
  );

  await app.listen(3000);
}
```

```ts
// Endpoint trả CSRF token cho frontend
@Controller('csrf')
export class CsrfController {
  @Get('token')
  getCsrfToken(@Req() req: Request) {
    // req.csrfToken is attached by doubleCsrfProtection; it also sets the CSRF cookie
    return { csrfToken: req.csrfToken!() };
  }
}
```

**Khi nào CẦN CSRF token:**

- Cookie auth đặt `SameSite=None` hoặc `Lax` (session cookie, JWT trong cookie).

**Khi nào KHÔNG cần CSRF token:**

- Cookie auth đặt `SameSite=Strict` và CORS chỉ whitelist origin của team — cách mặc định ở [NestJS Coding Standard 5.1 — Authentication](Ref_Dev_s5.1_nestjs-authentication_v1.0.md) mục 2.3.
- JWT gửi qua `Authorization: Bearer` header — browser không tự động gửi header.

```ts
// Nếu dùng SameSite cookie (hiện đại, đủ cho hầu hết cases)
// SameSite=Strict/Lax là CSRF protection ở browser level
response.cookie('accessToken', token, {
  httpOnly: true,
  secure: true,
  sameSite: 'strict', // Browser không gửi cookie cho cross-origin requests
  maxAge: 15 * 60 * 1000, // 15 phút
});
```

*Tại sao:* CSRF exploit browser tự động gửi cookies. Nếu user đã login (cookie tồn tại), attacker có thể tạo trang giả submit form tới API → thực hiện action dưới danh nghĩa user. CSRF token hoặc `SameSite` cookie ngăn điều này.

> **Tham khảo:** [OWASP CSRF Prevention](https://cheatsheetseries.owasp.org/cheatsheets/Cross-Site_Request_Forgery_Prevention_Cheat_Sheet.html)

---

### 2.5. Input Sanitization — Chống XSS

**✅ NÊN:** Sanitize HTML input trước khi lưu và khi render.

```ts
// common/pipes/sanitize-html.pipe.ts
import { PipeTransform, Injectable, ArgumentMetadata } from '@nestjs/common';
import * as sanitizeHtml from 'sanitize-html';

@Injectable()
export class SanitizeHtmlPipe implements PipeTransform {
  transform(value: any, metadata: ArgumentMetadata) {
    if (typeof value === 'string') {
      return sanitizeHtml(value, {
        allowedTags: ['b', 'i', 'em', 'strong', 'a', 'p', 'br', 'ul', 'ol', 'li'],
        allowedAttributes: {
          'a': ['href', 'target', 'rel'],
        },
        allowedSchemes: ['http', 'https', 'mailto'],
      });
    }
    if (typeof value === 'object' && value !== null) {
      return this.sanitizeObject(value);
    }
    return value;
  }

  private sanitizeObject(obj: Record<string, any>): Record<string, any> {
    const sanitized: Record<string, any> = {};
    for (const [key, val] of Object.entries(obj)) {
      sanitized[key] = typeof val === 'string'
        ? sanitizeHtml(val, { allowedTags: [], allowedAttributes: {} })
        : val;
    }
    return sanitized;
  }
}
```

```ts
// Áp dụng cho endpoint nhận rich text
@Post('comments')
async createComment(
  @Body(new SanitizeHtmlPipe()) dto: CreateCommentDto,
) {
  return this.commentsService.create(dto);
}
```

**Custom validator để chặn XSS patterns:**

```ts
// common/validators/no-html.validator.ts
import { registerDecorator, ValidationOptions } from 'class-validator';

export function NoHtml(validationOptions?: ValidationOptions) {
  return function (object: Object, propertyName: string) {
    registerDecorator({
      name: 'noHtml',
      target: object.constructor,
      propertyName: propertyName,
      options: {
        message: `${propertyName} must not contain HTML tags`,
        ...validationOptions,
      },
      validator: {
        validate(value: any) {
          if (typeof value !== 'string') return true;
          return !/<[^>]*>/g.test(value);
        },
      },
    });
  };
}

// Sử dụng trong DTO
export class CreateProductDto {
  @IsString()
  @NoHtml() // Chặn HTML injection
  name: string;
}
```

*Tại sao:* Stored XSS là khi attacker inject `<script>` vào DB thông qua input → khi user khác view data, script chạy trong browser của họ → steal cookies, redirect, keylogging.

> **Tham khảo:** [OWASP XSS Prevention](https://cheatsheetseries.owasp.org/cheatsheets/Cross_Site_Scripting_Prevention_Cheat_Sheet.html) · [sanitize-html](https://www.npmjs.com/package/sanitize-html)

---

### 2.6. Encryption & Hashing

**✅ NÊN:** Dùng argon2id cho passwords, Node.js `crypto` cho data encryption. Project đã lưu bcrypt hash thì giữ bcrypt với cost ≥ 12, giống doc Build a Secure Node js REST API của team.

**Password hashing:**

```ts
// Password hashing: argon2id for new projects; a project that already stores bcrypt hashes keeps bcrypt, cost ≥ 12
import * as argon2 from 'argon2';

// argon2id with the library defaults; the hash string stores salt and parameters
export async function hashPassword(plaintext: string): Promise<string> {
  return argon2.hash(plaintext, { type: argon2.argon2id });
}

export async function verifyPassword(plaintext: string, hashed: string): Promise<boolean> {
  return argon2.verify(hashed, plaintext);
}
```

**Symmetric encryption cho sensitive data (PII, tokens):**

```ts
import { Injectable } from '@nestjs/common';
import { ConfigService } from '@nestjs/config';
import { createCipheriv, createDecipheriv, randomBytes, scryptSync } from 'crypto';

const ALGORITHM = 'aes-256-gcm';
const IV_LENGTH = 16;
const TAG_LENGTH = 16;
const KEY_LENGTH = 32;
// Fixed salt: the key is derived once; a per-message salt would need one scrypt (~30 ms) per call
const KEY_SALT = 'encryption-service:v1';

@Injectable()
export class EncryptionService {
  private readonly key: Buffer;

  constructor(configService: ConfigService) {
    // scryptSync blocks the event loop: run it once at startup, never per request
    this.key = scryptSync(configService.getOrThrow<string>('ENCRYPTION_SECRET'), KEY_SALT, KEY_LENGTH);
  }

  encrypt(plaintext: string): string {
    const iv = randomBytes(IV_LENGTH);

    const cipher = createCipheriv(ALGORITHM, this.key, iv);
    const encrypted = Buffer.concat([
      cipher.update(plaintext, 'utf8'),
      cipher.final(),
    ]);
    const tag = cipher.getAuthTag();

    // Format: iv:tag:encrypted (all base64)
    return [
      iv.toString('base64'),
      tag.toString('base64'),
      encrypted.toString('base64'),
    ].join(':');
  }

  decrypt(encryptedData: string): string {
    const [ivB64, tagB64, dataB64] = encryptedData.split(':');

    const iv = Buffer.from(ivB64, 'base64');
    const tag = Buffer.from(tagB64, 'base64');
    const encrypted = Buffer.from(dataB64, 'base64');

    const decipher = createDecipheriv(ALGORITHM, this.key, iv);
    decipher.setAuthTag(tag);

    return Buffer.concat([
      decipher.update(encrypted),
      decipher.final(),
    ]).toString('utf8');
  }
}
```

**❌ KHÔNG NÊN:**

```ts
// ❌ Bad — MD5/SHA cho password (không có salt, quá nhanh → brute-force dễ)
import { createHash } from 'crypto';
const hashed = createHash('md5').update(password).digest('hex');

// ❌ Bad — encryption key hardcoded
const KEY = 'my-super-secret-key-12345678901';

// ❌ Bad — ECB mode (không có IV, patterns lộ)
const cipher = createCipheriv('aes-256-ecb', key, null);

// ❌ Bad — lưu plaintext sensitive data
await this.usersRepository.save({
  ...dto,
  ssn: dto.ssn,           // Plaintext SSN!
  taxCode: dto.taxCode,   // Plaintext tax code!
});
```

```ts
// ✅ Good — encrypt trước khi lưu
await this.usersRepository.save({
  ...dto,
  ssn: this.encryptionService.encrypt(dto.ssn),
  taxCode: this.encryptionService.encrypt(dto.taxCode),
});
```

❌ **KHÔNG NÊN:** Lưu số thẻ (PAN) hoặc CVV, kể cả đã mã hoá (PCI DSS). Dùng tokenization của payment provider, chỉ lưu token.

*Tại sao:*

- **argon2id** tự động thêm salt, tốn cả CPU lẫn memory (mặc định 64 MiB mỗi lần hash) → brute-force bằng GPU rất tốn.
- **AES-256-GCM** cung cấp cả encryption + authentication (phát hiện tampering).
- **MD5/SHA** quá nhanh cho password hashing → GPU có thể thử hàng tỷ hashes/giây.

> **Tham khảo:** [Node.js Crypto](https://nodejs.org/docs/latest/api/crypto.html) · [OWASP Password Storage](https://cheatsheetseries.owasp.org/cheatsheets/Password_Storage_Cheat_Sheet.html)

---

### 2.7. Cookie Security

**✅ NÊN:** Set đầy đủ security flags cho cookies.

```ts
// Secure cookie configuration
response.cookie('accessToken', token, {
  httpOnly: true,    // JavaScript không đọc được → chống XSS steal
  secure: true,      // Chỉ gửi qua HTTPS
  sameSite: 'strict', // Không gửi cross-origin → chống CSRF
  maxAge: 15 * 60 * 1000, // 15 phút
  path: '/',
  domain: '.example.com', // Scope chính xác
});

// Refresh token — stricter path
response.cookie('refreshToken', refreshToken, {
  httpOnly: true,
  secure: true,
  sameSite: 'strict',
  maxAge: 7 * 24 * 60 * 60 * 1000, // 7 ngày
  path: '/v1/auth', // Chỉ gửi tới /v1/auth/refresh và /v1/auth/logout
});
```

**❌ KHÔNG NÊN:**

```ts
// ❌ Bad — thiếu security flags
response.cookie('token', token); // Mặc định: httpOnly=false, secure=false, sameSite=lax

// ❌ Bad — token trong localStorage (XSS có thể đọc)
localStorage.setItem('token', token);
```

---

### 2.8. Logging & Error Disclosure

**✅ NÊN:** Log security events nhưng không log sensitive data.

```ts
// ✅ Good — log security event, không log credentials
this.logger.warn(
  `Failed login attempt for email ${email} from IP ${request.ip}`,
);

// ✅ Good — log API key prefix, không log full key
this.logger.warn(
  `Invalid API key (prefix: ${apiKey.substring(0, 8)}...) from IP ${request.ip}`,
);

// ✅ Good — không expose internal details trong error response
if (status >= 500 && process.env.NODE_ENV === 'production') {
  errorResponse.error.message = 'Internal server error';
  // Không trả stack trace, DB query, file paths
}
```

**❌ KHÔNG NÊN:**

```ts
// ❌ Bad — log password/token
this.logger.log(`User login: email=${email}, password=${password}`);
this.logger.log(`JWT token: ${token}`);

// ❌ Bad — expose stack trace trên production
response.status(500).json({
  error: exception.message,
  stack: exception.stack, // Lộ internal file paths, library versions
});
```

---

### 2.9. Dependency Security Audits

**✅ NÊN:** Chạy dependency audit định kỳ trong CI/CD để phát hiện known CVEs.

```bash
# CI pipeline — chạy mỗi build
pnpm audit --audit-level high

# Bun runtime
bun pm audit

# Snyk — deep vulnerability scanning
snyk test --severity-threshold=high
```

**Automated alerts:**

- **Dependabot** (GitHub): Tự động tạo PR update dependencies có CVE.
- **Snyk**: Monitor liên tục, alert qua Slack/email khi có vulnerability mới.
- **Renovate Bot**: Auto-update minor/patch versions, tạo PR cho major updates.

**Quy tắc:**

- ✅ **NÊN**: Chạy `pnpm audit` trong CI pipeline — fail build nếu có CVE severity high/critical.
- ✅ **NÊN**: Pin major versions, auto-patch minor/patch updates.
- ✅ **NÊN**: Review và update dependencies ít nhất mỗi tháng.
- ✅ **NÊN**: `helmet` đặt TRƯỚC mọi route và middleware khác trong `main.ts` — middleware order matters, routes định nghĩa trước helmet sẽ không có security headers.
- ❌ **KHÔNG NÊN**: Deploy mà không chạy dependency audit — known CVEs có thể bị exploit.
- ❌ **KHÔNG NÊN**: Giữ dependencies outdated vĩnh viễn — càng cũ càng nhiều CVEs tích lũy.

*Tại sao:* Outdated dependencies chứa known vulnerabilities mà attacker có thể exploit. Automated scanning phát hiện sớm, trước khi deploy lên production.

> **Tham khảo:** [npm audit](https://docs.npmjs.com/cli/audit) · [Snyk](https://snyk.io/) · [GitHub Dependabot](https://docs.github.com/en/code-security/dependabot)

---

### 2.10. Trust proxy và giới hạn body size

**✅ NÊN:** Đặt `trust proxy` bằng số proxy đứng trước app, và giới hạn body 2 MB, giống project v535.

```ts
// main.ts
const app = await NestFactory.create<NestExpressApplication>(AppModule);
// 1 behind one Nginx or load balancer; 0 when clients reach the app directly
app.set('trust proxy', configService.get<number>('TRUST_PROXY_HOPS', 0));
app.useBodyParser('json', { limit: '2mb' }); // Larger bodies get 413
app.useBodyParser('urlencoded', { extended: true, limit: '2mb' });
```

*Tại sao:* Thiếu `trust proxy` sau Nginx thì `req.ip` luôn là IP của proxy, nên throttler đếm chung mọi client. Bật khi không có proxy thì client tự gửi `X-Forwarded-For` giả để đổi IP.

### 2.11. SSRF — không gọi URL do client gửi mà không kiểm tra

**✅ NÊN:** Khi server tải URL do client gửi (ảnh, webhook, import từ link), chỉ chấp nhận `https` và host nằm trong allowlist.

```ts
// Only https, and only hosts on the list: an exact match or a subdomain of an entry
export function assertAllowedUrl(raw: string, allowedHosts: string[]): URL {
  const url = new URL(raw); // Throws on a malformed URL
  const host = url.hostname.toLowerCase();
  const allowed = allowedHosts.some((entry) => host === entry || host.endsWith(`.${entry}`));
  if (url.protocol !== 'https:' || !allowed) {
    throw new BadRequestException({ code: 'URL_NOT_ALLOWED', message: `URL host ${host} is not allowed` });
  }
  return url;
}
```

- Tắt follow redirect khi tải (axios `maxRedirects: 0`, [NestJS Coding Standard 6.3 — HTTP Client & Third-party Integration](Ref_Dev_s6.3_nestjs-http-client-integration_v1.0.md)), hoặc kiểm tra lại URL sau mỗi redirect.

*Tại sao:* Không kiểm tra thì attacker cho server gọi `http://169.254.169.254` (metadata của cloud) hoặc service nội bộ.

### 2.12. `execFile` thay `exec`

**✅ NÊN:** Chạy chương trình ngoài bằng `execFile` với mảng tham số. Không ghép input vào chuỗi lệnh của `exec`.

```ts
import { execFile } from 'node:child_process';
import { promisify } from 'node:util';

const execFileAsync = promisify(execFile);

// ❌ Bad — exec runs the string in a shell: a file named "a.pdf; rm -rf ~" runs the second command
// exec(`pdftotext ${filename} out.txt`);

// ✅ Good — arguments go to the program as they are, no shell in between
await execFileAsync('pdftotext', [filename, 'out.txt']);
```

---

## 3. Ví dụ minh họa thực tế

### 3.1. Walkthrough: Secure NestJS Bootstrap — Áp dụng đầy đủ Security Best Practices

**Bước 1 — Install dependencies**

```bash
pnpm add helmet @nestjs/throttler argon2 cookie-parser sanitize-html
pnpm add -D @types/cookie-parser @types/sanitize-html
```

**Bước 2 — main.ts hoàn chỉnh**

```ts
import { NestFactory } from '@nestjs/core';
import { ValidationPipe, Logger, VersioningType } from '@nestjs/common';
import { ConfigService } from '@nestjs/config';
import helmet from 'helmet';
import cookieParser from 'cookie-parser';
import { AppModule } from './app.module';
import { validationExceptionFactory } from './common/validation/validation-exception.factory';

async function bootstrap() {
  const app = await NestFactory.create(AppModule);
  const configService = app.get(ConfigService);
  const logger = new Logger('Bootstrap');

  // 1. Security headers
  app.use(helmet({
    contentSecurityPolicy: {
      directives: {
        defaultSrc: ["'self'"],
        scriptSrc: ["'self'"],
        styleSrc: ["'self'", "'unsafe-inline'"],
        imgSrc: ["'self'", 'data:', 'https:'],
        connectSrc: ["'self'"],
        objectSrc: ["'none'"],
        frameSrc: ["'none'"],
      },
    },
  }));

  // 2. CORS
  const corsOrigins = configService
    .getOrThrow<string>('CORS_ORIGINS')
    .split(',');
  app.enableCors({
    origin: corsOrigins,
    methods: ['GET', 'POST', 'PATCH', 'DELETE', 'OPTIONS'],
    allowedHeaders: ['Content-Type', 'Authorization', 'X-Api-Key'],
    credentials: true,
    maxAge: 86400,
  });

  // 3. Cookie parser
  app.use(cookieParser());

  // 4. Global validation
  app.useGlobalPipes(new ValidationPipe({
    whitelist: true,
    forbidNonWhitelisted: true,
    transform: true,
    exceptionFactory: validationExceptionFactory, // Error body with details, see 3.2 section 2.6
  }));

  // 5. URI versioning, no global prefix → /v1/... (see 3.1)
  app.enableVersioning({ type: VersioningType.URI, defaultVersion: '1' });

  const port = configService.get<number>('PORT', 3000);
  await app.listen(port);
  logger.log(`Application running on port ${port}`);
}
bootstrap();
```

**Bước 3 — app.module.ts với ThrottlerModule**

```ts
import { Module } from '@nestjs/common';
import { ConfigModule } from '@nestjs/config';
import { ThrottlerModule, ThrottlerGuard } from '@nestjs/throttler';
import { APP_GUARD } from '@nestjs/core';
import * as Joi from 'joi';

@Module({
  imports: [
    ConfigModule.forRoot({
      isGlobal: true,
      cache: true,
      validationSchema: Joi.object({
        NODE_ENV: Joi.string()
          .valid('development', 'staging', 'production', 'test')
          .required(),
        PORT: Joi.number().default(3000),
        CORS_ORIGINS: Joi.string().required(),
        JWT_SECRET: Joi.string().required().min(32),
        ENCRYPTION_SECRET: Joi.string().required().min(32),
        CSRF_SECRET: Joi.string().min(32), // Optional: only when the auth cookie is SameSite=None (section 2.4)
      }),
    }),
    ThrottlerModule.forRoot([{
      name: 'short',
      ttl: 1000,
      limit: 3,
    }, {
      name: 'medium',
      ttl: 10000,
      limit: 20,
    }, {
      name: 'long',
      ttl: 60000,
      limit: 100,
    }]),
  ],
  providers: [{
    provide: APP_GUARD,
    useClass: ThrottlerGuard,
  }],
})
export class AppModule {}
```

**Bước 4 — Security Checklist cho mỗi endpoint**

```ts
// ✅ Endpoint đầy đủ security layers
@Controller('orders')
@ApiTags('orders')
// Layer 1: Authentication — global JwtAuthGuard reads the accessToken cookie (5.1 section 2.4)
export class OrdersController {
  @Post()
  @Roles(Role.ADMIN, Role.STAFF)      // Layer 2: Authorization — global RolesGuard
  @Throttle({ long: { limit: 30, ttl: 60000 } }) // Layer 3: Rate limit
  @ApiOperation({ summary: 'Create order' })
  async create(
    @Body() dto: CreateOrderDto,      // Layer 4: Validation (ValidationPipe)
    @CurrentUser() user: UserPayload, // Layer 5: User context
  ): Promise<OrderResponseDto> {      // Layer 6: Serialization (Response DTO)
    return this.ordersService.create(dto, user);
  }
}
```

---

## 4. Tooling & Config

### 4.1. Checklist setup Security Best Practices

- [ ] Install `helmet` → cấu hình trong `main.ts`
- [ ] CORS whitelist theo env: `.env` local mở rộng, `.env.production` strict
- [ ] `@nestjs/throttler` global + stricter cho auth endpoints
- [ ] `argon2id` cho password hashing (project có sẵn bcrypt: cost ≥ 12)
- [ ] `EncryptionService` (AES-256-GCM) cho PII/sensitive data
- [ ] `SameSite=Strict` + `HttpOnly` + `Secure` cho cookies
- [ ] Input sanitization pipe cho endpoints nhận HTML/rich text
- [ ] `@NoHtml()` validator cho plain text fields
- [ ] Không log passwords, tokens, full API keys
- [ ] Không expose stack traces trên production
- [ ] Cookie auth `SameSite=Strict` + CORS whitelist; `csrf-csrf` chỉ khi cookie phải dùng `SameSite=None`
- [ ] Validation schema cho env vars bao gồm `JWT_SECRET`, `ENCRYPTION_SECRET`
- [ ] `trust proxy` theo `TRUST_PROXY_HOPS`, body limit 2 MB (mục 2.10)
- [ ] URL do client gửi đi qua allowlist (mục 2.11); chạy lệnh ngoài bằng `execFile` (mục 2.12)

### 4.2. Environment variables cần thiết

```bash
# .env.example
NODE_ENV=development
PORT=3000

# Security
CORS_ORIGINS=http://localhost:3000
JWT_SECRET=your-jwt-secret-at-least-32-characters-long
ENCRYPTION_SECRET=your-encryption-secret-at-least-32-chars
TRUST_PROXY_HOPS=0  # Proxies in front of the app: 1 behind one Nginx (section 2.10)
# Only when the auth cookie is SameSite=None (section 2.4)
CSRF_SECRET=your-csrf-secret-at-least-32-characters

```

### 4.3. ESLint rules bổ sung

```javascript
// eslint.config.mjs — add to the config of 1.4 section 2.3
export default tseslint.config(
  // ...config from 1.4 section 2.3
  {
    rules: {
      // Read env through ConfigService, not process.env (no-process-env is deprecated)
      'no-restricted-properties': ['warn', {
        object: 'process',
        property: 'env',
        message: 'Use ConfigService instead of process.env',
      }],
      // Use Logger, not console.log
      'no-console': ['error', { allow: ['warn', 'error'] }],
    },
  },
);
```

---

## References

- [NestJS Security](https://docs.nestjs.com/security/helmet) — Helmet, CORS, CSRF, Rate Limiting
- [NestJS Rate Limiting](https://docs.nestjs.com/security/rate-limiting) — @nestjs/throttler
- [Helmet.js](https://helmetjs.github.io/) — Security headers middleware
- [Node.js Crypto](https://nodejs.org/docs/latest/api/crypto.html) — Built-in crypto module
- [OWASP Cheat Sheet Series](https://cheatsheetseries.owasp.org/) — Security best practices
- [Password Storage](https://cheatsheetseries.owasp.org/cheatsheets/Password_Storage_Cheat_Sheet.html)
- [XSS Prevention](https://cheatsheetseries.owasp.org/cheatsheets/Cross_Site_Scripting_Prevention_Cheat_Sheet.html)
- [CSRF Prevention](https://cheatsheetseries.owasp.org/cheatsheets/Cross-Site_Request_Forgery_Prevention_Cheat_Sheet.html)
- [HTTP Headers](https://cheatsheetseries.owasp.org/cheatsheets/HTTP_Headers_Cheat_Sheet.html)
- [MDN CORS](https://developer.mozilla.org/en-US/docs/Web/HTTP/CORS) — Cross-Origin Resource Sharing
- [argon2](https://www.npmjs.com/package/argon2) — Password hashing
- [sanitize-html](https://www.npmjs.com/package/sanitize-html) — HTML sanitization

## Changelog

| Date | Version | Change | By |
| :---- | :---- | :---- | :---- |
| 2026-11-18 | v1.0 | Chuyển từ Notion "NestJS Document" (page `33d71a38d3b281429616d511ed1700ed`, sửa 2026-04-09). Review và sửa nội dung, code trước khi publish. Owner duyệt trong chat ngày 2026-11-18. | Bắc PV |
