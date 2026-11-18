# NestJS Coding Standard 9.3 — Build & Deployment

| Field | Value |
| :---- | :---- |
| Owner | Bắc PV — NodeJS BE Dev Lead |
| Audience | Dev (NodeJS BE) |
| Last reviewed | 2026-11-12 |
| Review cadence | Quarterly |
| Version | v1.0 |
| Linked from | Ref_Dev_nestjs-coding-standard_v1.0 |
| Status | Live |

Doc này là mục 9.3 của [NestJS Coding Standard](Ref_Dev_nestjs-coding-standard_v1.0.md), nhóm Performance & Operations. Doc nêu quy tắc về Build & Deployment trong dự án NestJS, kèm lý do, ví dụ và config. Dev NodeJS BE đọc doc này khi viết code, review code và onboarding.

---

## 1. Tóm tắt & Phạm vi

**Chủ đề giải quyết vấn đề gì?**

Build & Deployment định nghĩa cách đóng gói, tối ưu và triển khai ứng dụng NestJS lên production. Nội dung bao gồm production build, Docker multi-stage, CI/CD pipeline, environment parity, health checks, graceful shutdown và zero-downtime deployment.

**Áp dụng cho scope nào?**

- Mọi dự án NestJS cần deploy lên staging/production.
- Từ giai đoạn build → containerize → CI/CD → deploy → monitor.
- Liên quan đến dev, DevOps, và tech lead.

**Tại sao quan trọng?**

- Build không tối ưu dẫn đến Docker image lớn, deploy chậm, tốn bandwidth và storage.
- Thiếu CI/CD khiến deployment manual, dễ lỗi, khó rollback.
- Environment không nhất quán (dev ≠ staging ≠ production) gây “works on my machine” bugs.
- Thiếu health checks và graceful shutdown gây downtime khi deploy hoặc khi service gặp sự cố.

---

## 2. Quy tắc & Giải thích

### 2.1. Production build — tối ưu output

**✅ Nên:**

```bash
# Build production
pnpm run build

# Verify output
ls -la dist/
node dist/main.js
```

```json
// tsconfig.build.json — loại bỏ test files khỏi build
{
  "extends": "./tsconfig.json",
  "exclude": [
    "node_modules",
    "test",
    "dist",
    "**/*spec.ts",
    "**/*e2e-spec.ts"
  ]
}
```

**❌ Không nên:** Chạy `ts-node` hoặc `nest start` trên production — chậm hơn 2–5x so với compiled JS.

**Tại sao:** `nest build` compile TypeScript sang JavaScript tối ưu. Chạy compiled code trực tiếp bằng `node dist/main.js` nhanh hơn và tiêu tốn ít RAM hơn so với `ts-node` (cần parse + compile at runtime).

**Tham khảo:** [NestJS — Deployment](https://docs.nestjs.com/deployment)

---

### 2.2. Docker multi-stage build

**✅ Nên:** Sử dụng multi-stage build để tạo image production nhỏ gọn:

```docker
# ===== Stage 1: Build =====
FROM node:22-alpine AS builder

WORKDIR /app

# Cài pnpm
# Corepack runs the exact version in "packageManager" of package.json (block below), same as CI
RUN corepack enable

# Copy lockfile trước — tận dụng Docker layer cache
COPY pnpm-lock.yaml package.json ./
RUN pnpm install --frozen-lockfile

# Copy source và build
COPY . .
RUN pnpm run build

# Prune dev dependencies
RUN pnpm prune --prod

# ===== Stage 2: Production =====
FROM node:22-alpine AS production

# Security: non-root user
RUN addgroup -g 1001 -S nodejs && \
    adduser -S nestjs -u 1001 -G nodejs

WORKDIR /app

# Copy chỉ artifacts cần thiết
COPY --from=builder --chown=nestjs:nodejs /app/dist ./dist
COPY --from=builder --chown=nestjs:nodejs /app/node_modules ./node_modules
COPY --from=builder --chown=nestjs:nodejs /app/package.json ./

RUN mkdir logs && chown nestjs:nodejs logs  # LoggerModule writes here (Logging 7.1, section 3.2)

USER nestjs

EXPOSE 3000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD wget -qO- http://localhost:3000/health/liveness || exit 1

CMD ["node", "dist/main.js"]
```

```json
// package.json — one pinned pnpm version for local (corepack), Docker and CI (pnpm/action-setup)
{
  "packageManager": "pnpm@9.15.9",
  "engines": { "node": ">=22.12" }
}
```

**❌ Không nên:**

- Single-stage build copy toàn bộ `node_modules` (bao gồm devDependencies) — image lớn gấp 2–3x.
- Chạy container bằng `root` user — vi phạm principle of least privilege.
- Dùng `npm install` thay vì `pnpm install --frozen-lockfile` — không đảm bảo reproducible builds.

**Tại sao:**

- **Multi-stage** tách build environment (có devDependencies, TypeScript, source code) khỏi runtime environment (chỉ có compiled JS + production deps). Image production thường nhỏ hơn 60–70%.
- **Alpine base** nhỏ (\~5MB) so với Debian-based (\~100MB+), giảm attack surface.
- **`--frozen-lockfile`** đảm bảo CI/CD install đúng versions trong lockfile — không auto-update.
- **Non-root user** hạn chế thiệt hại nếu container bị compromise.

**Tham khảo:** [Docker — Multi-stage builds](https://docs.docker.com/build/building/multi-stage/) · [Node.js Docker Best Practices](https://github.com/nodejs/docker-node/blob/main/docs/BestPractices.md)

---

### 2.3. `.dockerignore` — giảm build context

**✅ Nên:** Tạo `.dockerignore` để loại bỏ files không cần thiết khỏi Docker build context:

```txt
node_modules
dist
.git
.github
.vscode
*.md
*.log
.env*
!.env.example
coverage
test
.nyc_output
.DS_Store
Dockerfile*
docker-compose*
```

**Tại sao:** Docker gửi toàn bộ build context lên daemon trước khi build. Nếu có `node_modules` (hàng trăm MB), build context rất lớn, COPY rất chậm. `.dockerignore` giống `.gitignore` — loại bỏ files không cần cho build.

---

### 2.4. Environment parity — dev ≈ staging ≈ production

**✅ Nên:**

- Dùng **cùng Node.js version** ở local (Denv), CI, và production (đều từ `node:22-alpine`).
- Dùng **cùng package manager** (pnpm) và **cùng lockfile** ở mọi môi trường.
- Dùng **Docker Compose** cho local development với services giống production (PostgreSQL, Redis, etc.).
- Tách `.env` theo môi trường: `.env` (local), `.env.test`, `.env.staging`, `.env.production`, load theo [NestJS Coding Standard 2.1 — Configuration & Environment Management](Ref_Dev_s2.1_nestjs-configuration-environment_v1.0.md) mục 2.2.
- Dùng `ConfigService` + validation schema (Joi/Zod) để fail-fast khi thiếu config.

```yaml
# docker-compose.yml — local dev giống production topology
services:
  app:
    build:
      context: .
      target: builder
    ports:
      - "3000:3000"
    env_file: .env
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy
    volumes:
      - .:/app
      - /app/node_modules

  postgres:
    image: postgres:16-alpine # MySQL: mysql:8.4 with MYSQL_* env and a mysqladmin ping healthcheck
    environment:
      POSTGRES_DB: app_dev
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: postgres
    ports:
      - "5432:5432"
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U postgres"]
      interval: 10s
      timeout: 5s
      retries: 5

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 5s
      retries: 5
```

**❌ Không nên:**

- Dev dùng Node 20, production dùng Node 22 — behavior khác nhau.
- Dev dùng SQLite, production dùng PostgreSQL — query behavior khác nhau.
- Hardcode config trong code thay vì dùng env variables.

**Tại sao:** “The twelve-factor app” principle #10 — Dev/prod parity giảm thiểu gaps giữa environments. Bugs phát hiện ở staging gần như chắc chắn reproduce được ở production nếu environments giống nhau.

**Tham khảo:** [The Twelve-Factor App — Dev/prod parity](https://12factor.net/dev-prod-parity)

---

### 2.5. Health checks & Graceful shutdown

**✅ Nên:**

```ts
// health.controller.ts — health check endpoint
import { Controller, Get, VERSION_NEUTRAL } from '@nestjs/common';
import {
  HealthCheck, HealthCheckService, TypeOrmHealthIndicator,
} from '@nestjs/terminus';

@Controller({ path: 'health', version: VERSION_NEUTRAL }) // Probes call /health, outside /v1
export class HealthController {
  constructor(
    private health: HealthCheckService,
    private db: TypeOrmHealthIndicator, // Prisma: PrismaHealthIndicator, see 7.3 section 3.1
  ) {}

  // Liveness: answers while the process runs; no dependency checks, so a DB outage never restarts the pod
  @Get('liveness')
  @HealthCheck()
  liveness() {
    return this.health.check([
      () => ({ app: { status: 'up' } }),
    ]);
  }

  // Readiness: dependencies the app needs to serve traffic (full version in 7.3 section 3.1)
  @Get('readiness')
  @HealthCheck()
  readiness() {
    return this.health.check([
      () => this.db.pingCheck('database', { timeout: 3000 }),
    ]);
  }
}
```

```ts
// main.ts — graceful shutdown
import { NestFactory } from '@nestjs/core';
import { Logger } from '@nestjs/common';

async function bootstrap() {
  const app = await NestFactory.create(AppModule);
  const logger = new Logger('Bootstrap');

  // Enable shutdown hooks
  app.enableShutdownHooks();

  const port = process.env.PORT || 3000;
  await app.listen(port);
  logger.log(`Application running on port ${port}`);
}
bootstrap();
```

```ts
// app.service.ts — cleanup on shutdown
import { Injectable, OnApplicationShutdown } from '@nestjs/common';
import { Logger } from '@nestjs/common';

@Injectable()
export class AppService implements OnApplicationShutdown {
  private readonly logger = new Logger(AppService.name);

  async onApplicationShutdown(signal?: string) {
    this.logger.log(`Shutting down... Signal: ${signal}`);
    // Close DB connections, flush logs, finish processing queues
    await this.cleanup();
  }

  private async cleanup(): Promise<void> {
    // Flush pending writes, close connections, etc.
  }
}
```

**❌ Không nên:**

- Deploy không có health check endpoint — orchestrator không biết app có healthy không.
- `process.exit(0)` ngay khi nhận SIGTERM — requests đang xử lý bị drop.
- Health check gọi external services nặng — health endpoint phải nhanh (\< 500ms).

**Tại sao:**

- **Health checks** cho phép orchestrator (Kubernetes, Docker Swarm, ECS) biết khi nào app ready nhận traffic (readiness) và khi nào cần restart (liveness).
- **Graceful shutdown** đảm bảo requests đang xử lý hoàn thành trước khi app tắt — tránh 502/503 errors cho users.
- **`@nestjs/terminus`** cung cấp health indicators cho DB, Redis, memory, disk — integrate sẵn với NestJS.

**Tham khảo:** [NestJS — Health checks](https://docs.nestjs.com/recipes/terminus) · [Kubernetes — Configure Liveness and Readiness Probes](https://kubernetes.io/docs/tasks/configure-pod-container/configure-liveness-readiness-startup-probes/)

---

### 2.6. CI/CD pipeline

**✅ Nên:** Thiết kế pipeline gồm các stages tuần tự:

1. **Install** — `pnpm install --frozen-lockfile`
2. **Lint** — `pnpm run lint`
3. **Test** — `pnpm run test --coverage`
4. **Build** — `pnpm run build`
5. **Docker build & push** — Build image, tag theo commit SHA + branch
6. **Deploy** — Deploy lên staging (auto) → production (manual approve)

```yaml
# .github/workflows/ci-cd.yml
name: CI/CD Pipeline

on:
  push:
    branches: [main, develop]
    tags: ['v*'] # release tags: type=semver below only produces a tag on these
  pull_request:
    branches: [main]

env:
  REGISTRY: ghcr.io
  IMAGE_NAME: ${{ github.repository }}

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - uses: pnpm/action-setup@v4 # version from "packageManager" in package.json (section 2.2)

      - uses: actions/setup-node@v4
        with:
          node-version: 22
          cache: pnpm

      - run: pnpm install --frozen-lockfile
      - run: pnpm run lint
      - run: pnpm run test --coverage --ci
      - run: pnpm run build

  docker:
    needs: test
    if: github.ref == 'refs/heads/main' || github.ref == 'refs/heads/develop' || startsWith(github.ref, 'refs/tags/v')
    runs-on: ubuntu-latest
    permissions:
      contents: read
      packages: write
    steps:
      - uses: actions/checkout@v4

      - uses: docker/login-action@v3
        with:
          registry: ${{ env.REGISTRY }}
          username: ${{ github.actor }}
          password: ${{ secrets.GITHUB_TOKEN }}

      - uses: docker/metadata-action@v5
        id: meta
        with:
          images: ${{ env.REGISTRY }}/${{ env.IMAGE_NAME }}
          tags: |
            type=sha,prefix=
            type=ref,event=branch
            type=semver,pattern={{version}}

      - uses: docker/build-push-action@v5
        with:
          context: .
          push: true
          tags: ${{ steps.meta.outputs.tags }}
          cache-from: type=gha
          cache-to: type=gha,mode=max

  deploy-staging:
    needs: docker
    if: github.ref == 'refs/heads/develop'
    runs-on: ubuntu-latest
    environment: staging
    steps:
      - name: Deploy to staging
        run: |
          # Deploy bằng SSH, kubectl, AWS ECS, hoặc platform cụ thể
          echo "Deploying to staging..."

  deploy-production:
    needs: docker
    if: github.ref == 'refs/heads/main'
    runs-on: ubuntu-latest
    environment:
      name: production
      # Require manual approval
    steps:
      - name: Deploy to production
        run: |
          echo "Deploying to production..."
```

**❌ Không nên:**

- Deploy production tự động không qua approval — rollback khó khăn nếu có lỗi.
- Skip lint/test trong CI — bugs lọt vào production.
- Build Docker image mà không tag theo commit SHA — không trace được version nào đang chạy.
- Cache không đúng cách — mỗi build install lại toàn bộ dependencies.

**Tại sao:**

- **Pipeline stages** đảm bảo code quality gates: lint → test → build phải pass tất cả trước khi deploy.
- **Docker layer cache** (GitHub Actions cache) giảm build time từ 5–10 phút xuống 1–2 phút.
- **Commit SHA tags** cho phép trace chính xác version nào đang chạy ở environment nào, hỗ trợ rollback nhanh.
- **Environment protection rules** (manual approval cho production) ngăn deploy nhầm.

**Tham khảo:** [GitHub Actions — Docker build-push-action](https://github.com/docker/build-push-action) · [NestJS — CI/CD Integration](https://docs.nestjs.com/devtools/ci-cd-integration)

---

### 2.7. Docker image tagging strategy

**✅ Nên:** Sử dụng multiple tags cho mỗi image:

```bash
# Tag theo commit SHA — immutable, dùng cho tracing
ghcr.io/org/app:a1b2c3d

# Tag theo branch — mutable, dùng cho latest build
ghcr.io/org/app:develop
ghcr.io/org/app:main

# Tag theo semver — cho releases
ghcr.io/org/app:1.2.3
ghcr.io/org/app:1.2
ghcr.io/org/app:1
```

**❌ Không nên:** Chỉ dùng tag `latest` — không biết version nào đang chạy, không rollback được.

**Tại sao:** Commit SHA tag là immutable — mỗi tag trỏ đến đúng 1 image. Khi production gặp lỗi, chỉ cần deploy lại image với SHA tag của commit trước đó.

---

### 2.8. Zero-downtime deployment

**✅ Nên:**

- Sử dụng **rolling update** (Kubernetes) hoặc **blue-green deployment** — không bao giờ tắt toàn bộ instances cùng lúc.
- Chạy migration theo **expand/contract** ([NestJS Coding Standard 4.1 — Database & ORM](Ref_Dev_s4.1_nestjs-database-orm_v1.0.md) mục 2.4). Migration chỉ thêm (cột nullable, bảng, index) chạy trước khi deploy code mới. v535 cũng chạy `prisma migrate deploy` trước khi start app. Migration xoá hoặc đổi tên chạy ở release sau, khi không còn instance chạy code cũ.
- Health check ready trước khi nhận traffic.
- Graceful shutdown để drain connections đang xử lý.

```yaml
# Kubernetes deployment snippet
apiVersion: apps/v1
kind: Deployment
metadata:
  name: app
spec:
  replicas: 3
  selector:
    matchLabels:
      app: app # Required by apps/v1, must match the template labels
  strategy:
    type: RollingUpdate
    rollingUpdate:
      maxUnavailable: 1
      maxSurge: 1
  template:
    metadata:
      labels:
        app: app
    spec:
      terminationGracePeriodSeconds: 30
      containers:
        - name: app
          image: ghcr.io/org/app:a1b2c3d
          ports:
            - containerPort: 3000
          readinessProbe:
            httpGet:
              path: /health/readiness
              port: 3000
            initialDelaySeconds: 5
            periodSeconds: 10
          livenessProbe:
            httpGet:
              path: /health/liveness
              port: 3000
            initialDelaySeconds: 15
            periodSeconds: 20
          resources:
            requests:
              memory: "256Mi"
              cpu: "250m"
            limits:
              memory: "512Mi"
              cpu: "500m"
```

**❌ Không nên:**

- Stop tất cả instances → deploy → start lại — downtime toàn bộ.
- Xoá hoặc đổi tên cột trong cùng release với code mới — instance code cũ còn chạy trong rolling update sẽ lỗi, và rollback code không còn cột cũ để đọc.
- Không set resource limits — 1 pod OOM có thể ảnh hưởng node.

**Tại sao:** Rolling update thay thế pods từng cái một, đảm bảo luôn có instances sẵn sàng phục vụ requests. Kết hợp readiness probe, traffic chỉ được route đến pods đã ready.

**Tham khảo:** [Kubernetes — Rolling Update](https://kubernetes.io/docs/tutorials/kubernetes-basics/update/update-intro/)

---

### 2.9. Security trong build & deploy

**✅ Nên:**

- **Scan vulnerabilities** trong Docker image trước khi push:

```yaml
# Trong CI pipeline
- name: Short SHA (the 7-char tag that docker/metadata-action type=sha builds)
  run: echo "SHORT_SHA=${GITHUB_SHA::7}" >> "$GITHUB_ENV"
- name: Run Trivy vulnerability scanner
  uses: aquasecurity/trivy-action@v0.36.0
  with:
    image-ref: ${{ env.REGISTRY }}/${{ env.IMAGE_NAME }}:${{ env.SHORT_SHA }}
    format: table
    exit-code: 1
    severity: CRITICAL,HIGH
```

- **Không bake secrets vào image** — dùng runtime env variables hoặc secrets manager.
- **Audit dependencies** định kỳ: `pnpm audit`.
- **Pin base image version**: `node:22.22.3-alpine` thay vì `node:latest`.

**❌ Không nên:**

- `COPY .env .` trong Dockerfile — secrets nằm trong image layer, ai có image đều đọc được.
- Dùng `node:latest` — version thay đổi bất kỳ lúc nào, build không reproducible.
- Bỏ qua vulnerability scan — known CVEs trong dependencies có thể bị exploit.

**Tại sao:** Docker image là artifact được distribute rộng rãi (registry, CI cache, developer machines). Secrets baked vào image = secrets bị lộ. Pin version đảm bảo reproducible builds.

---

## 3. Ví dụ minh họa thực tế

### 3.1. Walkthrough: Từ code đến production deployment

**Bước 1 — Developer push code:**

```bash
# Developer làm việc trên feature branch
git checkout -b feat/add-payment-api

# Code, test locally
pnpm run test
pnpm run build

# Commit (pre-commit validator chạy tự động)
git add .
git commit -m "feat(payments): add payment processing API"
git push origin feat/add-payment-api
```

**Bước 2 — Pull Request → CI chạy tự động:**

- Lint ✅ → Test ✅ → Build ✅
- Code review bởi team member
- Merge vào `develop`

**Bước 3 — CI/CD deploy staging:**

```txt
[CI] Install dependencies (pnpm install --frozen-lockfile)  ... 15s
[CI] Lint (pnpm run lint)                                   ... 8s
[CI] Test (pnpm run test --coverage)                        ... 25s
[CI] Build (pnpm run build)                                 ... 12s
[CI] Docker build (multi-stage)                             ... 45s (cached: 15s)
[CI] Push image: ghcr.io/org/app:a1b2c3d                   ... 10s
[CI] Deploy to staging                                      ... 30s
[CI] Health check passed ✅
```

**Bước 4 — QA test staging → Merge vào main → Deploy production (manual approve):**

```txt
[CI] Same pipeline → Docker build → Push
[CD] ⏳ Waiting for approval...
[CD] ✅ Approved by tech lead
[CD] Rolling update: 3 replicas, 1 at a time
[CD] Pod 1: ready ✅ (health check passed)
[CD] Pod 2: ready ✅
[CD] Pod 3: ready ✅
[CD] Deployment complete — zero downtime
```

---

### 3.2. Before/After: Từ manual deploy đến CI/CD

**Before** — Manual deployment:

- ❌ SSH vào server → `git pull` → `npm install` → `npm run build` → `pm2 restart`
- ❌ Downtime 2–5 phút mỗi lần deploy
- ❌ “Works on my machine” — Node version khác nhau giữa dev và server
- ❌ Rollback = `git revert` + deploy lại (10–15 phút)
- ❌ Không ai biết version nào đang chạy trên production

**After** — CI/CD pipeline:

- ✅ Push code → CI tự động test + build + deploy
- ✅ Zero-downtime với rolling update
- ✅ Docker đảm bảo environment consistency
- ✅ Rollback = deploy image tag trước đó (\< 1 phút)
- ✅ Commit SHA tag → trace chính xác version đang chạy

---

## 4. Tooling & Config

### 4.1. Checklist deployment cho project

- [ ] Tạo `Dockerfile` với multi-stage build (builder + production)
- [ ] Tạo `.dockerignore` loại bỏ `node_modules`, `.git`, test files
- [ ] Setup `docker-compose.yml` cho local development
- [ ] Tạo `/health/liveness` và `/health/readiness` với `@nestjs/terminus` ([NestJS Coding Standard 7.3 — Monitoring & Observability](Ref_Dev_s7.3_nestjs-monitoring-observability_v1.0.md) mục 2.1)
- [ ] Implement `enableShutdownHooks()` trong `main.ts`
- [ ] Implement `OnApplicationShutdown` cho cleanup logic
- [ ] Setup CI/CD pipeline (GitHub Actions / GitLab CI)
- [ ] Cấu hình Docker layer caching trong CI
- [ ] Image tagging: commit SHA + branch + semver
- [ ] Vulnerability scanning (Trivy / Snyk) trong pipeline
- [ ] Environment-specific `.env` files + validation schema
- [ ] Deployment strategy: rolling update hoặc blue-green
- [ ] Resource limits (memory, CPU) cho containers
- [ ] Monitoring & alerting cho health check failures

### 4.2. Dependencies cần cài đặt

```bash
# Health checks
pnpm add @nestjs/terminus

# (Optional) Nếu dùng TypeORM health indicator
pnpm add @nestjs/typeorm
```

### 4.3. File structure liên quan

```txt
project-root/
├── Dockerfile                  # Multi-stage build
├── .dockerignore               # Exclude files from build context
├── docker-compose.yml          # Local dev environment
├── docker-compose.prod.yml     # Production overrides (optional)
├── .github/
│   └── workflows/
│       ├── ci.yml              # Lint + test + build
│       └── cd.yml              # Docker build + deploy
├── src/
│   ├── health/
│   │   ├── health.module.ts
│   │   └── health.controller.ts
│   └── main.ts                 # enableShutdownHooks()
├── .env.example                # Template (committed)
├── .env                        # Local dev (gitignored)
├── .env.staging                # Staging (gitignored)
└── .env.production             # Production (gitignored)
```

### 4.4. So sánh deployment platforms

| Platform | Ưu điểm | Nhược điểm | Phù hợp |
| --- | --- | --- | --- |
| **Kubernetes (K8s)** | Full control, auto-scaling, self-healing | Complex setup, cần DevOps expertise | Large-scale, microservices |
| **Docker Compose + VPS** | Simple, cheap, full control | Manual scaling, no auto-healing | Small–medium projects |
| **AWS ECS / Fargate** | Managed containers, auto-scaling | AWS lock-in, pricing complexity | AWS-centric teams |
| **Render / Railway** | Zero-config deploy, free tier | Limited control, cold starts | MVPs, side projects |

---

## References

- [NestJS — Deployment](https://docs.nestjs.com/deployment)
- [NestJS — Health checks (Terminus)](https://docs.nestjs.com/recipes/terminus)
- [NestJS — CI/CD Integration](https://docs.nestjs.com/devtools/ci-cd-integration)
- [Docker — Multi-stage builds](https://docs.docker.com/build/building/multi-stage/)
- [Docker — Dockerfile best practices](https://docs.docker.com/develop/develop-images/dockerfile_best-practices/)
- [Node.js Docker Best Practices](https://github.com/nodejs/docker-node/blob/main/docs/BestPractices.md)
- [The Twelve-Factor App](https://12factor.net/)
- [Kubernetes — Rolling Update](https://kubernetes.io/docs/tutorials/kubernetes-basics/update/update-intro/)
- [GitHub Actions — Docker build-push-action](https://github.com/docker/build-push-action)
- [Trivy — Container Image Scanning](https://aquasecurity.github.io/trivy/)

## Changelog

| Date | Version | Change | By |
| :---- | :---- | :---- | :---- |
| 2026-11-18 | v1.0 | Chuyển từ Notion "NestJS Document" (page `33d71a38d3b28149b394ff9e34848f89`, sửa 2026-04-09). Review và sửa nội dung, code trước khi publish. Owner duyệt trong chat ngày 2026-11-18. | Bắc PV |
