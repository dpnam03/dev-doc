# NestJS Coding Standard 2.1 — Configuration & Environment Management

| Field | Value |
| :---- | :---- |
| Owner | Bắc PV — NodeJS BE Dev Lead |
| Audience | Dev (NodeJS BE) |
| Last reviewed | 2026-11-12 |
| Review cadence | Quarterly |
| Version | v1.0 |
| Linked from | Ref_Dev_nestjs-coding-standard_v1.0 |
| Status | Live |

Doc này là mục 2.1 của [NestJS Coding Standard](Ref_Dev_nestjs-coding-standard_v1.0.md), nhóm Configuration & Environment. Doc nêu quy tắc về Configuration & Environment Management trong dự án NestJS, kèm lý do, ví dụ và config. Dev NodeJS BE đọc doc này khi viết code, review code và onboarding.

---

## 1. Tóm tắt & Phạm vi

**Chủ đề:** Quản lý configuration và environment variables trong NestJS.

**Vấn đề giải quyết:**

- Hardcode configuration values trực tiếp trong code → khó thay đổi giữa các môi trường (dev, staging, production).
- Sử dụng `process.env` trực tiếp mà không validate → runtime errors khi thiếu hoặc sai định dạng config.
- Credentials và sensitive data bị commit lên repository → rủi ro bảo mật.
- Thiếu type safety cho config values → khó debug khi có lỗi liên quan đến configuration.

**Phạm vi áp dụng:** Tất cả NestJS applications, từ service nhỏ đến monorepo lớn. Áp dụng cho mọi môi trường: local development, staging, production.

**Tại sao quan trọng:**

- Tách biệt configuration khỏi code, dễ dàng thay đổi theo môi trường mà không cần rebuild.
- Type-safe configuration với TypeScript, phát hiện lỗi ngay trong development.
- Validate config khi application khởi động, fail-fast nếu thiếu hoặc sai config.
- Bảo mật sensitive data thông qua `.env` files và environment variables.
- Dễ dàng mock config trong testing.

---

## 2. Quy tắc & Giải thích

### 2.1. Sử dụng `@nestjs/config` Module

**✅ NÊN:** Luôn sử dụng `@nestjs/config` để quản lý configuration.

```ts
// app.module.ts
import { Module } from '@nestjs/common';
import { ConfigModule } from '@nestjs/config';

@Module({
  imports: [
    ConfigModule.forRoot({
      isGlobal: true,   // ConfigService available toàn bộ app, không cần import lại
      envFilePath: '.env',
      cache: true,       // Cache config values để improve performance
    }),
  ],
})
export class AppModule {}
```

*Tại sao:* `@nestjs/config` cung cấp type-safe configuration service, tích hợp tốt với NestJS DI system, hỗ trợ validation schema, và cho phép tổ chức config theo namespace.

**❌ KHÔNG NÊN:** Truy cập `process.env` trực tiếp trong business code.

```ts
// ❌ Bad — Không type-safe, không validate, không thể mock trong test
@Injectable()
class UserService {
  private readonly apiUrl = process.env.API_URL;
}

// ✅ Good — Type-safe, injectable, testable
import { Injectable } from '@nestjs/common';
import { ConfigService } from '@nestjs/config';

@Injectable()
class UserService {
  private readonly apiUrl: string;

  // Assign in the constructor: a field initializer cannot read a parameter property (TS2729)
  constructor(private readonly configService: ConfigService) {
    this.apiUrl = this.configService.getOrThrow<string>('API_URL');
  }
}
```

*Tại sao:* `process.env` trả về `string | undefined`, không có type safety. Khi dùng `ConfigService`, bạn có thể mock trong unit test và validate khi khởi động.

> **Tham khảo:** [NestJS Configuration](https://docs.nestjs.com/techniques/configuration)

---

### 2.2. Tổ chức Environment Files theo môi trường

**✅ NÊN:** Tách `.env` files theo môi trường, chỉ commit file template.

```txt
# Cấu trúc files
.env                 # Local development — KHÔNG commit
.env.example         # Template cho team — commit vào Git
.env.test            # E2E test: Jest đặt NODE_ENV=test — KHÔNG commit
.env.staging         # Staging, khi không set env qua platform — KHÔNG commit
.env.production      # Production, khi không set env qua platform — KHÔNG commit
```

```ts
// .env.<NODE_ENV> first, then .env: a key found in an earlier file wins, a missing file is skipped
ConfigModule.forRoot({
  envFilePath: [`.env.${process.env.NODE_ENV ?? 'development'}`, '.env'],
  isGlobal: true,
})
```

**❌ KHÔNG NÊN:** Commit `.env` files chứa sensitive data lên Git.

```txt
# .gitignore
.env
.env.local
.env.*.local
.env.test
.env.production
.env.staging

# ✅ Chỉ commit file template
!.env.example
```

*Tại sao:* `.env.example` giúp team biết cần set những biến nào mà không lộ giá trị thực. Mỗi developer copy `.env.example` → `.env` rồi điền giá trị local.

---

### 2.3. Validate Configuration với Schema (Joi hoặc Zod)

**Đề xuất:** Sử dụng **Joi** cho hầu hết dự án (tích hợp sẵn với `@nestjs/config`, ecosystem lớn). Dùng **Zod** nếu team đã adopt Zod trong project.

`@nestjs/config` 12 nhận `validationSchema` dạng Standard Schema, nên cần `joi` ≥ 18. Shape của `validationOptions` khác nhau giữa bản 4.x (NestJS 11) và 12, nên option của Joi đặt trên schema bằng `.prefs()`.

**✅ NÊN:** Validate tất cả environment variables khi app khởi động.

```ts
// config/validation.schema.ts
import Joi from 'joi'; // default import: `import * as Joi` breaks on an ESM build

export const validationSchema = Joi.object({
  NODE_ENV: Joi.string()
    .valid('development', 'production', 'staging', 'test')
    .default('development'),
  PORT: Joi.number().default(3000),
  DATABASE_URL: Joi.string().required(),
  JWT_SECRET: Joi.string().required().min(32),
  JWT_ACCESS_EXPIRES: Joi.string().default('15m'),
  REDIS_HOST: Joi.string().required(),
  REDIS_PORT: Joi.number().default(6379),
  REDIS_PASSWORD: Joi.string().allow('').optional(), // Empty in local .env
  LOG_LEVEL: Joi.string()
    .valid('error', 'warn', 'info', 'debug')
    .default('info'),
  LOG_DIR: Joi.string().default('logs'),
  PROCESS_TYPE: Joi.string().valid('api', 'worker').default('api'),
}).prefs({
  abortEarly: false,   // Show tất cả validation errors cùng lúc
  allowUnknown: true,  // Cho phép env vars không define trong schema
});
```

```ts
// app.module.ts
import { validationSchema } from './config/validation.schema';

@Module({
  imports: [
    ConfigModule.forRoot({
      isGlobal: true,
      validationSchema, // Joi options are set on the schema with .prefs()
    }),
  ],
})
export class AppModule {}
```

*Tại sao:* Validation schema đảm bảo tất cả required config có mặt và đúng format **ngay khi app khởi động** (fail-fast), thay vì gặp lỗi runtime muộn khi chạy đến đoạn code sử dụng config.

**❌ KHÔNG NÊN:** Bỏ qua validation, chỉ kiểm tra config khi sử dụng.

```ts
// ❌ Bad — Lỗi xảy ra muộn, khi user gọi API mới phát hiện thiếu config
class DatabaseService {
  connect() {
    const url = this.configService.get('DATABASE_URL');
    if (!url) {
      throw new Error('DATABASE_URL is required');
    }
  }
}

// ✅ Good — Lỗi ngay khi app start, trước khi nhận bất kỳ request nào
// → Sử dụng validation schema như ví dụ trên
```

> **Tham khảo:** [Joi API](https://joi.dev/api/) · [Zod](https://zod.dev/)

---

### 2.4. Type-safe Configuration với Custom Config Files (registerAs)

**✅ NÊN:** Tạo typed configuration files cho từng domain, sử dụng `registerAs`.

```ts
// config/database.config.ts
import { registerAs } from '@nestjs/config';

export default registerAs('database', () => ({
  host: process.env.DATABASE_HOST,
  port: parseInt(process.env.DATABASE_PORT ?? '5432', 10),
  username: process.env.DATABASE_USERNAME,
  password: process.env.DATABASE_PASSWORD,
  name: process.env.DATABASE_NAME, // read as database.name (4.1)
  synchronize: false, // Schema changes go through migrations only (see 4.1)
  logging: process.env.NODE_ENV === 'development',
}));
```

```ts
// config/jwt.config.ts
export default registerAs('jwt', () => ({
  secret: process.env.JWT_SECRET,
  accessExpiresIn: process.env.JWT_ACCESS_EXPIRES || '15m', // Same env names as 5.1
  refreshSecret: process.env.JWT_REFRESH_SECRET,
  refreshExpiresIn: process.env.JWT_REFRESH_EXPIRES || '7d',
}));
```

```ts
// app.module.ts
import databaseConfig from './config/database.config';
import jwtConfig from './config/jwt.config';

@Module({
  imports: [
    ConfigModule.forRoot({
      isGlobal: true,
      load: [databaseConfig, jwtConfig],
    }),
  ],
})
export class AppModule {}
```

*Tại sao:* Tổ chức config theo domain (database, jwt, redis, …) giúp dễ quản lý, tái sử dụng, và có type inference tốt hơn. Mỗi module chỉ cần quan tâm config namespace của mình.

---

### 2.5. Sử dụng `getOrThrow()` cho required config

**✅ NÊN:** Dùng `getOrThrow()` khi config value là bắt buộc.

```ts
// ✅ Fail-fast — ném exception ngay nếu thiếu config
const apiKey = this.configService.getOrThrow<string>('API_KEY');
```

**❌ KHÔNG NÊN:** Dùng `get()` cho required config mà không handle undefined.

```ts
// ❌ Bad — Có thể return undefined, gây lỗi runtime ở nơi khác
const apiKey = this.configService.get<string>('API_KEY');
// apiKey có thể là undefined → lỗi khó debug
```

*Tại sao:* `getOrThrow()` ném exception **ngay tại dòng gọi**, giúp xác định chính xác config nào thiếu. `get()` trả về `undefined` im lặng, lỗi chỉ xuất hiện khi giá trị được sử dụng ở nơi khác.

---

### 2.6. Namespace Configuration để tránh xung đột

**✅ NÊN:** Sử dụng namespace (qua `registerAs`) để nhóm related config.

```ts
// config/app.config.ts
export default registerAs('app', () => ({
  name: process.env.APP_NAME || 'My NestJS App',
  version: process.env.APP_VERSION || '1.0.0',
  environment: process.env.NODE_ENV || 'development',
  port: parseInt(process.env.PORT ?? '3000', 10),
  cors: {
    enabled: process.env.CORS_ENABLED === 'true',
    origin: process.env.CORS_ORIGIN || '*',
  },
}));

// Sử dụng với dot notation
const appName = this.configService.get<string>('app.name');
const corsEnabled = this.configService.get<boolean>('app.cors.enabled');
```

*Tại sao:* Namespace tránh naming conflicts giữa các config group (ví dụ `database.host` vs `redis.host`) và giúp code rõ ràng hơn khi đọc.

---

### 2.7. Xử lý logic theo environment trong config files

**✅ NÊN:** Centralize environment-specific logic trong config files.

```ts
// config/logger.config.ts
export default registerAs('logger', () => {
  const isDevelopment = process.env.NODE_ENV === 'development';
  const isProduction = process.env.NODE_ENV === 'production';

  return {
    level: process.env.LOG_LEVEL || (isDevelopment ? 'debug' : 'info'),
    format: isProduction ? 'json' : 'pretty',
    transports: isProduction ? ['file', 'console'] : ['console'],
    fileOptions: isProduction
      ? { filename: 'logs/app.log', maxFiles: 10, maxSize: '10m' }
      : undefined,
  };
});
```

*Tại sao:* Tập trung logic phân biệt environment tại một nơi (config file) thay vì scatter khắp codebase với các `if (process.env.NODE_ENV === 'production')`. Khi cần thay đổi behavior theo environment, chỉ cần sửa config file.

---

### 2.8. Secrets Management

**✅ NÊN:** Sử dụng environment variables cho sensitive data, **không bao giờ hardcode**.

```bash
# .env.example — Safe to commit, KHÔNG chứa giá trị thật
NODE_ENV=development
PORT=3000
DATABASE_HOST=localhost
JWT_SECRET=your-secret-here-min-32-chars
API_KEY=your-api-key-here
```

**✅ NÊN:** Trong production, set env vars qua platform (Docker, Kubernetes, AWS, etc.).

```yaml
# docker-compose.yml
services:
  app:
    environment:
      - NODE_ENV=production
      - DATABASE_URL=${DATABASE_URL}
      - JWT_SECRET=${JWT_SECRET}
    env_file:
      - .env.production
```

```yaml
# Kubernetes Secret
apiVersion: v1
kind: Secret
metadata:
  name: app-secrets
type: Opaque
data:
  jwt-secret: base64-encoded-secret
  database-url: base64-encoded-url
```

**❌ KHÔNG NÊN:** Hardcode secrets trong code hoặc commit `.env` files với credentials thật.

*Tại sao:* Secrets trong source code = bất kỳ ai có access repo đều thấy. Sử dụng platform-level env vars hoặc secret management tools (AWS Secrets Manager, HashiCorp Vault) để bảo vệ credentials.

---

### 2.9. Mock ConfigService trong Testing

**✅ NÊN:** Mock `ConfigService` trong unit tests để tách biệt khỏi actual environment.

```ts
// auth.service.spec.ts
describe('AuthService', () => {
  let service: AuthService;

  const mockConfigService = {
    get: jest.fn((key: string) => {
      const config: Record<string, string> = {
        'jwt.secret': 'test-secret-at-least-32-characters-long',
        'jwt.accessExpiresIn': '15m',
      };
      return config[key];
    }),
    getOrThrow: jest.fn((key: string): string => { // explicit return type: avoids TS7022 (self-reference)
      const value = mockConfigService.get(key);
      if (!value) throw new Error(`Config ${key} not found`);
      return value;
    }),
  };

  beforeEach(async () => {
    const module: TestingModule = await Test.createTestingModule({
      providers: [
        AuthService,
        { provide: ConfigService, useValue: mockConfigService },
      ],
    }).compile();

    service = module.get<AuthService>(AuthService);
  });

  it('should generate token with correct config', () => {
    expect(mockConfigService.get('jwt.secret'))
      .toBe('test-secret-at-least-32-characters-long');
  });
});
```

*Tại sao:* Mock ConfigService giúp test không phụ thuộc vào file `.env` hay actual environment variables. Test chạy nhanh, deterministic, và portable.

---

## 3. Ví dụ minh họa thực tế

### 3.1. Walkthrough: Setup Configuration hoàn chỉnh cho NestJS Application

**Bước 1 — Cài đặt dependencies**

```bash
pnpm add @nestjs/config joi@^18
```

**Bước 2 — Tạo cấu trúc thư mục config**

```txt
src/
├── config/
│   ├── validation.schema.ts    # Schema validate env vars
│   ├── app.config.ts            # App-level config
│   ├── database.config.ts       # Database config
│   └── jwt.config.ts            # JWT config
├── app.module.ts
└── main.ts
```

**Bước 3 — Tạo Validation Schema**

```ts
// src/config/validation.schema.ts
import Joi from 'joi'; // default import: `import * as Joi` breaks on an ESM build

export const validationSchema = Joi.object({
  // App
  NODE_ENV: Joi.string()
    .valid('development', 'staging', 'production', 'test')
    .required(),
  PORT: Joi.number().default(3000),

  // Database
  DATABASE_HOST: Joi.string().required(),
  DATABASE_PORT: Joi.number().default(5432),
  DATABASE_USERNAME: Joi.string().required(),
  DATABASE_PASSWORD: Joi.string().required(),
  DATABASE_NAME: Joi.string().required(),
  DATABASE_SSL_CA: Joi.string().optional(), // CA bundle (PEM) of the DB server, production

  // JWT
  JWT_SECRET: Joi.string().required().min(32),
  JWT_ACCESS_EXPIRES: Joi.string().default('15m'),
  JWT_REFRESH_SECRET: Joi.string().required().min(32),
  JWT_REFRESH_EXPIRES: Joi.string().default('7d'),

  // Redis
  REDIS_HOST: Joi.string().required(),
  REDIS_PORT: Joi.number().default(6379),
  REDIS_PASSWORD: Joi.string().allow('').optional(), // .env.example leaves it empty

  // Logging
  LOG_LEVEL: Joi.string()
    .valid('error', 'warn', 'info', 'debug')
    .default('info'),
  LOG_DIR: Joi.string().default('logs'),
  PROCESS_TYPE: Joi.string().valid('api', 'worker').default('api'),
}).prefs({
  abortEarly: false,
  allowUnknown: true,
});
```

**Bước 4 — Tạo Config Files theo domain**

```ts
// src/config/app.config.ts
import { registerAs } from '@nestjs/config';

export default registerAs('app', () => ({
  name: process.env.APP_NAME || 'NestJS App',
  environment: process.env.NODE_ENV || 'development',
  port: parseInt(process.env.PORT ?? '3000', 10),
  isDevelopment: process.env.NODE_ENV === 'development',
  isProduction: process.env.NODE_ENV === 'production',
}));
```

```ts
// src/config/database.config.ts
import { registerAs } from '@nestjs/config';

export default registerAs('database', () => ({
  host: process.env.DATABASE_HOST,
  port: parseInt(process.env.DATABASE_PORT ?? '5432', 10),
  username: process.env.DATABASE_USERNAME,
  password: process.env.DATABASE_PASSWORD,
  name: process.env.DATABASE_NAME, // read as database.name (4.1)
  synchronize: false, // Schema changes go through migrations only (see 4.1)
  logging: process.env.NODE_ENV === 'development',
  ssl: process.env.NODE_ENV === 'production'
    ? { rejectUnauthorized: true, ca: process.env.DATABASE_SSL_CA } // DB provider CA bundle (PEM)
    : false,
}));
```

```ts
// src/config/jwt.config.ts
import { registerAs } from '@nestjs/config';

export default registerAs('jwt', () => ({
  secret: process.env.JWT_SECRET,
  accessExpiresIn: process.env.JWT_ACCESS_EXPIRES || '15m',
  refreshSecret: process.env.JWT_REFRESH_SECRET,
  refreshExpiresIn: process.env.JWT_REFRESH_EXPIRES || '7d',
}));
```

**Bước 5 — Kết nối tất cả trong AppModule**

```ts
// src/app.module.ts
import { Module } from '@nestjs/common';
import { ConfigModule } from '@nestjs/config';
import { validationSchema } from './config/validation.schema';
import appConfig from './config/app.config';
import databaseConfig from './config/database.config';
import jwtConfig from './config/jwt.config';

@Module({
  imports: [
    ConfigModule.forRoot({
      isGlobal: true,
      envFilePath: [`.env.${process.env.NODE_ENV ?? 'development'}`, '.env'], // section 2.2
      load: [appConfig, databaseConfig, jwtConfig],
      validationSchema, // Joi options are set on the schema with .prefs()
      cache: true,
    }),
    // Other modules...
  ],
})
export class AppModule {}
```

**Bước 6 — Tạo `.env.example`**

```bash
# .env.example
# Application
NODE_ENV=development
PORT=3000

# Database
DATABASE_HOST=localhost
DATABASE_PORT=5432  # MySQL: 3306
DATABASE_USERNAME=postgres  # MySQL: an app user, not root
DATABASE_PASSWORD=your-password-here
DATABASE_NAME=myapp
# Production only: CA bundle (PEM) of the DB server
# DATABASE_SSL_CA=

# JWT
JWT_SECRET=your-jwt-secret-min-32-characters-long
JWT_ACCESS_EXPIRES=15m
JWT_REFRESH_SECRET=your-refresh-secret-min-32-characters-long
JWT_REFRESH_EXPIRES=7d

# Redis
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_PASSWORD=

# Logging
LOG_LEVEL=debug
```

**Bước 7 — Sử dụng trong service**

```ts
// src/app.service.ts
import { Injectable } from '@nestjs/common';
import { ConfigService } from '@nestjs/config';

@Injectable()
export class AppService {
  constructor(private configService: ConfigService) {}

  getAppInfo() {
    return {
      name: this.configService.get<string>('app.name'),
      environment: this.configService.get<string>('app.environment'),
      version: '1.0.0',
    };
  }

  isDevelopment(): boolean {
    return this.configService.getOrThrow<boolean>('app.isDevelopment');
  }
}
```

---

## 4. Tooling & Config

### 4.1. Checklist setup Configuration

- [ ] Cài đặt `@nestjs/config`: `pnpm add @nestjs/config`
- [ ] Cài đặt validation library: `pnpm add joi@^18` (hoặc `pnpm add zod`)
- [ ] Tạo thư mục `src/config/`
- [ ] Tạo validation schema: `src/config/validation.schema.ts`
- [ ] Tạo config files cho từng domain (`app`, `database`, `jwt`, …)
- [ ] Setup `ConfigModule.forRoot()` trong `AppModule` với validation
- [ ] Tạo `.env.example` file (commit vào Git)
- [ ] Thêm `.env*` vào `.gitignore` (trừ `.env.example`)
- [ ] Test validation: start app với config thiếu/sai → phải fail ngay
- [ ] Document các environment variables cần thiết trong README

### 4.2. VS Code extensions hỗ trợ

- **DotENV** (`mikestead.dotenv`) — Syntax highlighting cho `.env` files

### 4.3. EditorConfig cho `.env` files

```txt
# .editorconfig
[*.env*]
charset = utf-8
indent_style = space
indent_size = 2
end_of_line = lf
insert_final_newline = true
trim_trailing_whitespace = true
```

### 4.4. Scripts tiện ích

```json
// package.json
{
  "scripts": {
    "env:validate": "nest build && node scripts/validate-env.mjs"
  }
}
```

```js
// scripts/validate-env.mjs — usage: pnpm env:validate .env.staging
import { validationSchema } from '../dist/config/validation.schema.js';

process.loadEnvFile(process.argv[2] ?? '.env');
const { error } = validationSchema.validate(process.env, { abortEarly: false, allowUnknown: true });
if (error) {
  console.error(error.message);
  process.exit(1);
}
console.log('Env validation passed');
```

---

## References

- [NestJS Configuration Module](https://docs.nestjs.com/techniques/configuration) — Tài liệu chính thức về `@nestjs/config`
- [Node.js process.env](https://nodejs.org/docs/latest/api/process.html#processenv) — API reference cho environment variables
- [Joi Validation Library](https://joi.dev/api/) — Schema validation library
- [Zod](https://zod.dev/) — TypeScript-first schema validation
- [The Twelve-Factor App — Config](https://12factor.net/config) — Nguyên tắc quản lý config trong ứng dụng hiện đại
- [dotenv Package](https://github.com/motdotla/dotenv) — Load `.env` files vào `process.env`

## Changelog

| Date | Version | Change | By |
| :---- | :---- | :---- | :---- |
| 2026-11-18 | v1.0 | Chuyển từ Notion "NestJS Document" (page `33d71a38d3b281d781b0d4d706ee0be2`, sửa 2026-04-09). Review và sửa nội dung, code trước khi publish. Owner duyệt trong chat ngày 2026-11-18. | Bắc PV |
