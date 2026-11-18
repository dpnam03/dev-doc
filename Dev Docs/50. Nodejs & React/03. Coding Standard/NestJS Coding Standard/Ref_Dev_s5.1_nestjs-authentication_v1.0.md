# NestJS Coding Standard 5.1 — Authentication

| Field | Value |
| :---- | :---- |
| Owner | Bắc PV — NodeJS BE Dev Lead |
| Audience | Dev (NodeJS BE) |
| Last reviewed | 2026-11-12 |
| Review cadence | Quarterly |
| Version | v1.0 |
| Linked from | Ref_Dev_nestjs-coding-standard_v1.0<br>Ref_Dev_s5.2_nestjs-authorization_v1.0 |
| Status | Live |

Doc này là mục 5.1 của [NestJS Coding Standard](Ref_Dev_nestjs-coding-standard_v1.0.md), nhóm Security. Doc nêu quy tắc về Authentication trong dự án NestJS, kèm lý do, ví dụ và config. Dev NodeJS BE đọc doc này khi viết code, review code và onboarding.

---

## 1. Tóm tắt & Phạm vi

> 🎯 **Chủ đề**: Authentication & Authorization trong NestJS — bảo vệ API, xác thực người dùng, phân quyền truy cập.
>
> **Scope**: Áp dụng cho mọi API endpoint cần kiểm soát truy cập — từ internal service-to-service, đến user-facing (web/mobile), đến public API.
>
> **Tại sao quan trọng**: Auth sai = lộ dữ liệu, mất kiểm soát truy cập, bị tấn công brute-force/XSS. Đây là lớp bảo vệ đầu tiên và quan trọng nhất của hệ thống.

**Phạm vi bao gồm**:

- Authentication: API Key (service-to-service), JWT trong HttpOnly cookie (user sessions), OAuth2/SSO
- Authorization: Guards, RBAC (Role-Based Access Control), ABAC (Attribute-Based)
- Security headers, CORS, Rate Limiting, CSRF protection
- Validation & sanitization để chống injection/XSS

---

## 2. Quy tắc & Giải thích

### 2.1 Chọn phương thức Auth phù hợp theo use case

| Use case | Phương thức đề xuất | Giải thích |
| --- | --- | --- |
| Service-to-service / Internal API | **API Key** (header `x-api-key`) | Đơn giản, không cần identity user. Phù hợp microservice nội bộ, cron, webhook. |
| User-facing (web/mobile) | **JWT trong HttpOnly cookie** (access + refresh token) | Gắn identity user, phân quyền, stateless verify, revoke được qua refresh token. |
| Third-party / SSO | **OAuth2 / OpenID Connect** | Delegate auth cho provider tin cậy (Google, GitHub, SSO nội bộ). |
| Public API có giới hạn | **Rate limit + CAPTCHA** (không bắt buộc auth) | Chống abuse mà không cần login. Kết hợp API key nếu cần tracking. |

> **Đề xuất mặc định**: Với hầu hết dự án NestJS, dùng **JWT cho user-facing** + **API Key cho internal**. Chỉ thêm OAuth2 khi có yêu cầu SSO cụ thể.

### 2.2 API Key cho service-to-service

**✅ Nên làm:**

- **Lưu SHA-256 hash của API key trong env** (`API_KEYS`, đọc qua `ConfigService`), không lưu key gốc, không hard-code trong source code
- *Tại sao*: Hard-code key = lộ key khi push code lên repo. Env cho phép rotate key mà không deploy lại code. Env chỉ chứa hash nên lộ env không lộ key dùng được.
- **So sánh bằng `timingSafeEqual` trên hai SHA-256 digest cùng độ dài**, không dùng `includes()` hay `===`
- *Tại sao*: So sánh string dừng ở ký tự sai đầu tiên, thời gian phản hồi giúp attacker đoán dần từng ký tự.
- **Cần scope, expiry hoặc revoke theo từng client** thì lưu hash trong DB kèm các field đó, thay cho env
- **Support nhiều API key** cho các hệ thống khác nhau
- *Tại sao*: Khi cần revoke access của 1 service, chỉ xóa key của service đó — không ảnh hưởng service khác.
- **Guard đọc header `x-api-key`**, ném custom exception kèm error code rõ ràng (`MISSING_API_KEY`, `INVALID_API_KEY`)
- *Tại sao*: Client biết chính xác lỗi gì để fix, thay vì nhận generic 401.
- **Đưa `ApiKeyGuard` vào `AuthModule` dạng `@Global()`** để các module khác chỉ cần `@UseGuards(ApiKeyGuard)`. Controller dùng API key đánh dấu thêm `@Public()`, nếu không `JwtAuthGuard` global (mục 2.4) trả 401
- *Tại sao*: DRY — tránh duplicate guard logic ở mỗi module.

```ts
// auth/guards/api-key.guard.ts
import { createHash, timingSafeEqual } from 'node:crypto';

const sha256 = (value: string): Buffer => createHash('sha256').update(value).digest();

@Injectable()
export class ApiKeyGuard implements CanActivate {
  // API_KEYS holds SHA-256 hex digests, never the keys (format validated in section 4.4)
  private readonly keyHashes: Buffer[];

  constructor(configService: ConfigService) {
    this.keyHashes = configService
      .getOrThrow<string>('API_KEYS')
      .split(',')
      .map((hex) => Buffer.from(hex.trim(), 'hex'));
  }

  canActivate(context: ExecutionContext): boolean {
    const request = context.switchToHttp().getRequest<Request>();
    const apiKey = request.headers['x-api-key'] as string;

    if (!apiKey) {
      throw new UnauthorizedException({
        code: 'MISSING_API_KEY',
        message: 'API key is required in x-api-key header',
      });
    }

    // Both sides are 32-byte digests, so timingSafeEqual never throws on a length mismatch
    const presented = sha256(apiKey);
    if (!this.keyHashes.some((hash) => timingSafeEqual(hash, presented))) {
      throw new UnauthorizedException({
        code: 'INVALID_API_KEY',
        message: 'Invalid API key',
      });
    }

    return true;
  }
}
```

**❌ Không nên làm:**

- **Không hard-code key trong code** — dùng env hoặc secret manager
- **Không log key thật** khi sai/thiếu — chỉ log prefix hoặc key ID để debug
- **Không dùng API key cho user-facing** — API key không gắn identity user, không revoke per-session

### 2.3 JWT cho user (web/mobile)

**✅ Nên làm:**

- **Access token ngắn hạn (5–15 phút)**, refresh token dài hơn (7–30 ngày)
- *Tại sao*: Access token ngắn giảm window tấn công nếu bị lộ. Refresh token cho phép renew session mà không bắt login lại.
- **Token payload chứa**: `sub` (userId), `roles`/`permissions`, `iat`, `exp`
- *Tại sao*: Đủ thông tin để authorize mà không cần query DB mỗi request.
- **Gửi access token và refresh token trong HttpOnly cookie**, không trả token trong response body, không lưu localStorage
- *Tại sao*: HTTP-only cookie không bị XSS đọc được. localStorage accessible bởi mọi JS script trên page.
- **Cookie đặt `httpOnly`, `secure` ở production, `sameSite: 'strict'`**, giống project v535. Refresh cookie chỉ gửi tới `/v1/auth`, access cookie gửi tới mọi route.
- *Tại sao*: `sameSite: 'strict'` làm browser không gửi cookie trong request từ site khác. Phần CSRF xem [NestJS Coding Standard 5.3 — Security Best Practices](Ref_Dev_s5.3_nestjs-security-best-practices_v1.0.md) mục 2.4.
- **Refresh token lưu trong DB/Redis dạng SHA-256 hash**, có cơ chế revoke khi logout hoặc bị lộ
- *Tại sao*: Stateless JWT không revoke được — cần server-side tracking cho refresh token. Không hash refresh token bằng bcrypt: bcrypt chỉ đọc 72 byte đầu, với JWT là header và phần đầu payload, nên token cũ vẫn khớp và rotation mất tác dụng.
- **`request.user` là `{ sub, roles }`**, cùng shape với payload JWT mà 5.2 đọc (`user.sub`). Custom decorator `@CurrentUser()` để lấy user payload đã validate
- *Tại sao*: Clean code — controller không cần biết cách extract user từ request.

```ts
// auth/auth.constants.ts
export const ACCESS_COOKIE = 'accessToken';
export const REFRESH_COOKIE = 'refreshToken';
// The refresh cookie is sent only to /v1/auth/refresh and /v1/auth/logout
export const REFRESH_COOKIE_PATH = '/v1/auth';

// auth/interfaces/user-payload.interface.ts — request.user, read by 5.2 as user.sub / user.roles
export interface UserPayload {
  sub: number;
  roles: Role[]; // enum Role, 5.2 section 2.1
}

// auth/strategies/jwt.strategy.ts
@Injectable()
export class JwtStrategy extends PassportStrategy(Strategy) {
  constructor(configService: ConfigService) {
    super({
      // Access token comes from the HttpOnly cookie set at login (needs cookie-parser, 5.3 section 3.1)
      jwtFromRequest: ExtractJwt.fromExtractors([
        (req: Request): string | null => req.cookies?.[ACCESS_COOKIE] ?? null,
      ]),
      ignoreExpiration: false,
      secretOrKey: configService.getOrThrow<string>('JWT_SECRET'),
    });
  }

  validate(payload: JwtPayload): UserPayload {
    return { sub: payload.sub, roles: payload.roles };
  }
}
```

```ts
// auth/decorators/current-user.decorator.ts
export const CurrentUser = createParamDecorator(
  (data: keyof UserPayload | undefined, ctx: ExecutionContext) => {
    const user = ctx.switchToHttp().getRequest().user;
    return data ? user?.[data] : user;
  },
);
```

**❌ Không nên làm:**

- **Không lưu JWT trong localStorage** trên browser — XSS attack sẽ đánh cắp token
- **Không đặt access token quá dài** (> 1 giờ) — tăng risk khi bị lộ
- **Không lưu sensitive data trong JWT payload** (password, PII) — JWT chỉ encode, không encrypt
- **Không bỏ qua refresh token rotation** — nếu refresh token bị lộ mà không revoke, attacker có permanent access

### 2.4 Authorization — Guard & Deny-by-default

**✅ Nên làm:**

- **Deny-by-default**: đăng ký `JwtAuthGuard` một lần bằng `APP_GUARD` trong `AppModule`. Route public đánh dấu `@Public()`
- *Tại sao*: Quên gắn guard = endpoint public. Deny-by-default an toàn hơn — quên gắn `@Public()` chỉ gây 401, không lộ data.
- **RBAC qua `RolesGuard`** đọc metadata `@Roles(Role.ADMIN, Role.STAFF)` từ handler. Enum `Role` và `RolesGuard` ở [NestJS Coding Standard 5.2 — Authorization](Ref_Dev_s5.2_nestjs-authorization_v1.0.md) mục 2.1
- *Tại sao*: Declarative — dễ audit, dễ review quyền trên từng endpoint.
- **Compose decorator**: `@AdminOnly()` = `@Roles(Role.ADMIN)` + Swagger decorators
- *Tại sao*: DRY — tránh lặp 3-4 decorators trên mỗi method.

```ts
// auth/decorators/public.decorator.ts
export const IS_PUBLIC_KEY = 'isPublic';
export const Public = () => SetMetadata(IS_PUBLIC_KEY, true);

// auth/guards/jwt-auth.guard.ts — global, so every route needs a valid access cookie unless @Public()
@Injectable()
export class JwtAuthGuard extends AuthGuard('jwt') {
  constructor(private readonly reflector: Reflector) {
    super();
  }

  canActivate(context: ExecutionContext) {
    const isPublic = this.reflector.getAllAndOverride<boolean>(IS_PUBLIC_KEY, [
      context.getHandler(),
      context.getClass(),
    ]);
    return isPublic ? true : super.canActivate(context);
  }
}
```

```ts
// app.module.ts — register each guard once; order: authentication, then roles
@Module({
  providers: [
    { provide: APP_GUARD, useClass: JwtAuthGuard },
    { provide: APP_GUARD, useClass: RolesGuard }, // RolesGuard, Roles: 5.2 section 2.1
  ],
})
export class AppModule {}
```

```ts
// Compose decorator — role check + Swagger; authentication already runs globally
export function AdminOnly() {
  return applyDecorators(
    Roles(Role.ADMIN),
    ApiCookieAuth(),
    ApiForbiddenResponse({ description: 'Admin role required' }),
  );
}
```

```ts
// Controller — no @UseGuards: the global JwtAuthGuard already protects every route
@ApiTags('orders')
@Controller('orders')
export class OrdersController {
  @Get()
  @ApiOperation({ summary: 'Danh sách đơn hàng của user hiện tại' })
  findMyOrders(@CurrentUser('sub') userId: number) { ... }

  @Delete(':id')
  @AdminOnly() // Chỉ admin mới được xóa
  remove(@Param('id', ParseIntPipe) id: number) { ... }
}
```

**❌ Không nên làm:**

- **Không để endpoint production mà không có guard** — trừ khi explicitly public (search, health check)
- **Không check role trong service/controller logic** (`if (user.role === 'admin')`) — dùng guard + decorator
- *Tại sao*: Scattered role checks khó audit, dễ bỏ sót. Guard centralize logic tại 1 điểm.
- **Không dùng global guard mà không có cơ chế `@Public()`** — sẽ block health check, Swagger, login endpoint
- **Không gắn thêm `@UseGuards(JwtAuthGuard)` hay đăng ký `APP_GUARD` lần nữa** — guard chạy nhiều lần cho một request

### 2.5 Security Best Practices

**✅ Nên làm:**

- **CORS**: Production chỉ whitelist domain frontend thật sự dùng
- *Tại sao*: Với `origin: '*'`, browser không cho đọc response của request có cookie, nên chỉ lộ data public. Rủi ro thật là reflect origin của request (`origin: true`) kèm `credentials: true`: mọi site đọc được response bằng cookie của user.

```ts
// main.ts
app.enableCors({
  origin: configService.getOrThrow<string>('CORS_ORIGINS').split(','),
  credentials: true, // Cho phép cookie cross-origin
  methods: ['GET', 'POST', 'PATCH', 'DELETE'],
});
```

- **Rate Limiting**: Bảo vệ khỏi brute-force login, spam endpoint
- *Tại sao*: Không có rate limit = attacker thử hàng triệu password combinations.
- Config throttler (giới hạn chung và giới hạn riêng cho login) ở [NestJS Coding Standard 5.3 — Security Best Practices](Ref_Dev_s5.3_nestjs-security-best-practices_v1.0.md) mục 2.3.

- **Security headers**: Dùng `helmet` cho production
- *Tại sao*: Bật X-Frame-Options (chống clickjacking), HSTS (force HTTPS), X-Content-Type-Options (chống MIME sniffing).
- Tham khảo: [Helmet docs](https://helmetjs.github.io/)

```ts
// main.ts
import helmet from 'helmet';
app.use(helmet());
```

- **Validation & Sanitization**: Bắt buộc DTO + `ValidationPipe` global
- *Tại sao*: Input không validate = SQL injection, XSS, NoSQL injection.
- Với data text (HTML, comment) render ra view → sanitize bằng thư viện như `sanitize-html` hoặc `DOMPurify`.
- **Auth error messages phải generic**: `'Invalid credentials'` — cùng message cho wrong email và wrong password
- *Tại sao*: Message khác nhau cho “email không tồn tại” vs “password sai” giúp attacker enumerate valid emails.

**❌ Không nên làm:**

- **Không dùng `origin: '*'` trong production** — chỉ dùng khi dev
- **Không bỏ qua rate limiting** cho login/register/forgot-password endpoints
- **Không trả error message khác nhau** cho “user not found” vs “wrong password”
- **Không lưu password dạng plain text** — hash bằng argon2id; project đã dùng bcrypt thì giữ bcrypt với cost ≥ 12 ([NestJS Coding Standard 5.3 — Security Best Practices](Ref_Dev_s5.3_nestjs-security-best-practices_v1.0.md) mục 2.6)

---

## 3. Ví dụ minh họa thực tế

### 3.1 Walkthrough: Triển khai Auth module hoàn chỉnh

**Cấu trúc thư mục:**

```txt
src/api/user/auth.controller.ts  # Login, register, refresh, logout endpoints (1.1 section 2.2)
src/modules/auth/
├── auth.module.ts              # Module declaration, imports, providers
├── auth.service.ts             # Business logic: validate, sign, refresh, revoke
├── guards/
│   ├── jwt-auth.guard.ts       # Global guard, reads the access token cookie
│   ├── api-key.guard.ts        # x-api-key header validation
│   └── roles.guard.ts          # RBAC based on metadata
├── strategies/
│   └── jwt.strategy.ts         # Passport JWT strategy
├── decorators/
│   ├── current-user.decorator.ts  # Extract user from request
│   ├── roles.decorator.ts         # SetMetadata('roles', [...])
│   └── public.decorator.ts        # Mark route as public (skip auth)
├── auth.constants.ts           # Cookie names and refresh cookie path
├── dto/
│   ├── login.dto.ts
│   └── register.dto.ts
└── interfaces/
    ├── jwt-payload.interface.ts
    └── user-payload.interface.ts
```

### 3.2 Before/After: Từ code không an toàn → code chuẩn

**❌ Before — Không an toàn:**

```ts
// Không guard, không validate, lộ thông tin
@Controller('users')
export class UsersController {
  @Post('login')
  async login(@Body() body: any) {
    const user = await this.usersRepo.findOne({ where: { email: body.email } });
    if (!user) throw new NotFoundException('Email not found'); // Reveals which emails exist
    if (body.password !== user.password) throw new BadRequestException('Wrong password'); // Plain text!
    const token = jwt.sign({ userId: user.id }, 'my-secret-key'); // Hard-code secret
    return { token };
  }

  @Get('profile') // Không guard — ai cũng truy cập được!
  async getProfile(@Req() req) {
    return this.usersRepo.findOne({ where: { id: req.user?.id } });
  }
}
```

**Vấn đề:**

1. `body: any` — không validate input
2. Plain text password comparison — không hash
3. Error message lộ email exists (“Email không tồn tại” vs “Sai mật khẩu”)
4. Hard-code JWT secret
5. `getProfile` không có guard — public access
6. Trả raw entity — có thể lộ password hash, tokens

**✅ After — Chuẩn security:**

```ts
// auth.controller.ts — tokens travel only in HttpOnly cookies, never in the response body
import type { Request, Response } from 'express';
import ms, { type StringValue } from 'ms';

@ApiTags('auth')
@Controller('auth')
export class AuthController {
  constructor(
    private readonly authService: AuthService,
    private readonly configService: ConfigService,
  ) {}

  @Public()
  @Post('login')
  @HttpCode(HttpStatus.NO_CONTENT)
  @ApiOperation({ summary: 'User login' })
  async login(@Body() dto: LoginDto, @Res({ passthrough: true }) res: Response): Promise<void> {
    this.setAuthCookies(res, await this.authService.login(dto));
  }

  @Public() // The access token may already be expired; the refresh cookie is checked instead
  @Post('refresh')
  @HttpCode(HttpStatus.NO_CONTENT)
  async refresh(@Req() req: Request, @Res({ passthrough: true }) res: Response): Promise<void> {
    const refreshToken: unknown = req.cookies?.[REFRESH_COOKIE];
    if (typeof refreshToken !== 'string') {
      throw new UnauthorizedException('Invalid refresh token');
    }
    this.setAuthCookies(res, await this.authService.refreshToken(refreshToken));
  }

  @Post('logout')
  @HttpCode(HttpStatus.NO_CONTENT)
  async logout(
    @CurrentUser('sub') userId: number,
    @Res({ passthrough: true }) res: Response,
  ): Promise<void> {
    await this.authService.revokeRefreshToken(userId);
    res.clearCookie(ACCESS_COOKIE, { path: '/' });
    res.clearCookie(REFRESH_COOKIE, { path: REFRESH_COOKIE_PATH });
  }

  // Same flags as v535: HttpOnly, Secure in production, SameSite=Strict
  private setAuthCookies(res: Response, tokens: AuthTokens): void {
    const base = {
      httpOnly: true,
      secure: this.configService.get<string>('NODE_ENV') === 'production',
      sameSite: 'strict' as const,
    };
    res.cookie(ACCESS_COOKIE, tokens.accessToken, {
      ...base,
      path: '/',
      maxAge: ms(this.configService.getOrThrow<StringValue>('JWT_ACCESS_EXPIRES')),
    });
    res.cookie(REFRESH_COOKIE, tokens.refreshToken, {
      ...base,
      path: REFRESH_COOKIE_PATH,
      maxAge: ms(this.configService.getOrThrow<StringValue>('JWT_REFRESH_EXPIRES')),
    });
  }
}
```

```ts
// auth.service.ts — business logic
import { createHash, randomUUID, timingSafeEqual } from 'node:crypto';
import * as argon2 from 'argon2';
import type { StringValue } from 'ms'; // '15m', '7d': expiresIn rejects a plain string (TS2769)

// Returned to AuthController, which writes both tokens to HttpOnly cookies
export interface AuthTokens {
  accessToken: string;
  refreshToken: string;
}

@Injectable()
export class AuthService {
  constructor(
    private readonly usersService: UsersService,
    private readonly jwtService: JwtService,
    private readonly configService: ConfigService,
  ) {}

  async login(dto: LoginDto): Promise<AuthTokens> {
    const user = await this.usersService.findByEmail(dto.email);

    // Generic error — không phân biệt email sai hay password sai
    if (!user || !(await argon2.verify(user.passwordHash, dto.password))) {
      throw new UnauthorizedException('Invalid credentials');
    }

    return this.generateTokens(user);
  }

  async refreshToken(refreshToken: string): Promise<AuthTokens> {
    let payload: JwtPayload;
    try {
      payload = await this.jwtService.verifyAsync<JwtPayload>(refreshToken, {
        secret: this.configService.getOrThrow<string>('JWT_REFRESH_SECRET'),
      });
    } catch {
      throw new UnauthorizedException('Invalid refresh token');
    }

    const user = await this.usersService.findById(payload.sub);
    const presentedHash = Buffer.from(this.hashToken(refreshToken), 'hex');

    // Only the latest issued token matches; an old (rotated) or revoked token fails here
    if (
      !user?.refreshTokenHash ||
      !timingSafeEqual(Buffer.from(user.refreshTokenHash, 'hex'), presentedHash)
    ) {
      throw new UnauthorizedException('Invalid refresh token');
    }

    return this.generateTokens(user); // Rotation: overwrites the stored hash
  }

  private async generateTokens(user: User): Promise<AuthTokens> {
    const payload: JwtPayload = { sub: user.id, roles: user.roles };

    const [accessToken, refreshToken] = await Promise.all([
      this.jwtService.signAsync(payload, {
        expiresIn: this.configService.getOrThrow<StringValue>('JWT_ACCESS_EXPIRES'),
      }),
      this.jwtService.signAsync(payload, {
        secret: this.configService.getOrThrow<string>('JWT_REFRESH_SECRET'),
        expiresIn: this.configService.getOrThrow<StringValue>('JWT_REFRESH_EXPIRES'),
        jwtid: randomUUID(), // Unique per token, so every refresh yields a new hash
      }),
    ]);

    // Lưu refresh token hash vào DB để có thể revoke
    await this.usersService.updateRefreshToken(user.id, this.hashToken(refreshToken));

    return { accessToken, refreshToken };
  }

  async revokeRefreshToken(userId: number): Promise<void> {
    await this.usersService.updateRefreshToken(userId, null); // Logout: no refresh token matches any more
  }

  // SHA-256, not bcrypt: bcrypt reads only the first 72 bytes, which a JWT fills with
  // its header and the start of the payload, so an old token would still match
  private hashToken(token: string): string {
    return createHash('sha256').update(token).digest('hex');
  }
}
```

**Cải thiện:**

1. DTO với `class-validator` — validate email format, password length
2. `argon2.verify` — so sánh hash, không plain text
3. Generic error message — attacker không biết email tồn tại hay không
4. JWT secret từ `ConfigService` — không hard-code
5. `JwtAuthGuard` chạy global, route public đánh dấu `@Public()`
6. Token nằm trong HttpOnly cookie, response body không chứa token nên JS trên page không đọc được
7. Refresh token lưu dạng SHA-256 hash, so sánh bằng `timingSafeEqual` — revoke được khi logout, token cũ hết hiệu lực sau mỗi lần refresh. Mỗi user chỉ lưu 1 hash, nên login trên thiết bị thứ hai sẽ logout thiết bị đầu.

---

## 4. Tooling & Config

### 4.1 Packages cần cài

```bash
# Auth core
pnpm add @nestjs/passport passport passport-jwt @nestjs/jwt cookie-parser ms
pnpm add -D @types/passport-jwt @types/cookie-parser @types/ms   # ms: cookie maxAge from JWT_*_EXPIRES

# Password hashing
pnpm add argon2

# Security headers & rate limiting
pnpm add helmet
pnpm add @nestjs/throttler

# Validation (nếu chưa có)
pnpm add class-validator class-transformer
```

### 4.2 Environment variables

```txt
# .env.example
JWT_SECRET=your-secret-key-at-least-32-chars-long
JWT_ACCESS_EXPIRES=15m
JWT_REFRESH_SECRET=different-secret-for-refresh-tokens
JWT_REFRESH_EXPIRES=7d

# API Keys (comma-separated cho multi-service)
# SHA-256 hex of each key, not the key itself. Generate: printf '%s' "$KEY" | sha256sum
API_KEYS=<sha256-hex-of-service-a-key>,<sha256-hex-of-service-b-key>

# CORS
CORS_ORIGINS=https://app.example.com,https://admin.example.com

```

### 4.3 Auth module setup

```ts
// auth/auth.module.ts
import type { StringValue } from 'ms';

@Global()
@Module({
  imports: [
    PassportModule.register({ defaultStrategy: 'jwt' }),
    JwtModule.registerAsync({
      inject: [ConfigService],
      useFactory: (config: ConfigService) => ({
        secret: config.getOrThrow<string>('JWT_SECRET'),
        signOptions: {
          expiresIn: config.getOrThrow<StringValue>('JWT_ACCESS_EXPIRES'),
        },
      }),
    }),
  ],
  controllers: [AuthController],
  providers: [
    AuthService,
    JwtStrategy,
    ApiKeyGuard,
    RolesGuard,
  ],
  exports: [AuthService, JwtModule],
})
export class AuthModule {}
```

### 4.4 Config validation (Joi)

```ts
// config/validation.schema.ts — thêm auth config
export const validationSchema = Joi.object({
  // ... other configs
  JWT_SECRET: Joi.string().required().min(32),
  JWT_ACCESS_EXPIRES: Joi.string().default('15m'),
  JWT_REFRESH_SECRET: Joi.string().required().min(32),
  JWT_REFRESH_EXPIRES: Joi.string().default('7d'),
  API_KEYS: Joi.string().required().pattern(/^[0-9a-f]{64}(,[0-9a-f]{64})*$/), // SHA-256 hex list
  CORS_ORIGINS: Joi.string().required(),
});
```

---

## References

- [NestJS Authentication docs](https://docs.nestjs.com/security/authentication)
- [NestJS Authorization docs](https://docs.nestjs.com/security/authorization)
- [NestJS Rate Limiting (Throttler)](https://docs.nestjs.com/security/rate-limiting)
- [NestJS CORS](https://docs.nestjs.com/security/cors)
- [NestJS Helmet](https://docs.nestjs.com/security/helmet)
- [Passport.js docs](http://www.passportjs.org/docs/)
- [JWT RFC 7519](https://datatracker.ietf.org/doc/html/rfc7519)
- [OWASP Authentication Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Authentication_Cheat_Sheet.html)
- [OWASP Authorization Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Authorization_Cheat_Sheet.html)
- [OWASP Password Storage Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Password_Storage_Cheat_Sheet.html)

## Changelog

| Date | Version | Change | By |
| :---- | :---- | :---- | :---- |
| 2026-11-18 | v1.0 | Chuyển từ Notion "NestJS Document" (page `33d71a38d3b2817cbd39c498cdc959db`, sửa 2026-04-09). Review và sửa nội dung, code trước khi publish. Owner duyệt trong chat ngày 2026-11-18. | Bắc PV |
