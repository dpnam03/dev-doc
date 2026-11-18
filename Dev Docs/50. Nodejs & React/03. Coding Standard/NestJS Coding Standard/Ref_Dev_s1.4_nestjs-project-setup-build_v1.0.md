# NestJS Coding Standard 1.4 — Project Setup & Build

| Field | Value |
| :---- | :---- |
| Owner | Bắc PV — NodeJS BE Dev Lead |
| Audience | Dev (NodeJS BE) |
| Last reviewed | 2026-11-12 |
| Review cadence | Quarterly |
| Version | v1.0 |
| Linked from | Ref_Dev_nestjs-coding-standard_v1.0 |
| Status | Live |

Doc này là mục 1.4 của [NestJS Coding Standard](Ref_Dev_nestjs-coding-standard_v1.0.md), nhóm Nền tảng NestJS. Doc nêu quy tắc về Project Setup & Build trong dự án NestJS, kèm lý do, ví dụ và config. Dev NodeJS BE đọc doc này khi viết code, review code và onboarding.

---

## 1. Tóm tắt & Phạm vi

**Chủ đề giải quyết vấn đề gì?**

Project Setup & Build định nghĩa cách khởi tạo, cấu hình và build một dự án NestJS từ đầu. Nội dung bao gồm cấu trúc project, TypeScript configuration, package manager, linting/formatting, Docker environment, pre-commit validation, và build process.

**Áp dụng cho scope nào?**

- Mọi dự án NestJS mới hoặc đang tái cấu trúc.
- Áp dụng từ giai đoạn khởi tạo project đến khi build production.
- Liên quan đến tất cả member trong team (dev, lead, DevOps).
- Version mục tiêu: NestJS 11, Node ≥22.12 ([NestJS Coding Standard](Ref_Dev_nestjs-coding-standard_v1.0.md) mục 3).

**Tại sao quan trọng?**

- Setup không thống nhất dẫn đến khó onboarding, merge conflicts, và inconsistency trong codebase.
- Thiếu automation (lint, format, validate) khiến code quality phụ thuộc vào review thủ công.
- Build process không rõ ràng gây deployment failures và khó debug.

---

## 2. Quy tắc & Giải thích

### 2.1. Sử dụng pnpm làm package manager duy nhất

**✅ Nên:**

```bash
# Cài đặt dependencies
pnpm install

# Thêm package mới
pnpm add @nestjs/config

# Thêm dev dependency
pnpm add -D @types/node
```

**❌ Không nên:** Trộn lẫn npm, yarn và pnpm trong cùng một project — hoặc commit cả `package-lock.json` lẫn `pnpm-lock.yaml`.

**Tại sao:** pnpm sử dụng content-addressable storage, tiết kiệm đáng kể disk space và tốc độ install nhanh hơn npm/yarn. Quan trọng hơn, việc thống nhất một package manager đảm bảo lockfile nhất quán giữa tất cả member — tránh “works on my machine”.

**Tham khảo:** [pnpm — Motivation](https://pnpm.io/motivation)

---

### 2.2. Bật TypeScript strict mode

**✅ Nên:** Cấu hình `tsconfig.json` với strict mode đầy đủ:

```json
{
  "compilerOptions": {
    "strict": true,
    "strictNullChecks": true,
    "strictFunctionTypes": true,
    "strictPropertyInitialization": false,
    "noImplicitAny": true,
    "noImplicitThis": true,
    "alwaysStrict": true
  }
}
```

`strictPropertyInitialization: false` vì property của DTO và entity không có initializer, giá trị do class-transformer hoặc ORM gán lúc runtime. Bật option này thì mọi DTO lỗi TS2564.

**❌ Không nên:** Tắt strict mode hoặc dùng `any` thay vì định nghĩa type cụ thể.

```ts
// ❌ Bad — mất type safety, runtime error tiềm ẩn
function processData(data: any) {
  return data.value.toString();
}

// ✅ Good — compiler bắt lỗi ngay khi build
interface DataInput {
  value: string | number;
}

function processData(data: DataInput): string {
  return data.value.toString();
}
```

**Tại sao:** Strict mode buộc developer xử lý null/undefined, implicit any, và type mismatch ngay trong IDE — phát hiện lỗi sớm hơn so với runtime. Theo TypeScript team, bật strict giảm khoảng 15% bugs liên quan đến type.

**Tham khảo:** [TypeScript — tsconfig strict](https://www.typescriptlang.org/tsconfig#strict)

---

### 2.3. Cấu hình ESLint cho NestJS + TypeScript

**✅ Nên:** Dùng file `eslint.config.mjs` (flat config) mà `nest new` tạo sẵn, gồm `typescript-eslint` và Prettier plugin. Team chỉ đổi `no-explicit-any` thành `error`:

```javascript
// eslint.config.mjs — the file `nest new` (NestJS 11) generates, with the team's rule levels
// @ts-check
import eslint from '@eslint/js';
import eslintPluginPrettierRecommended from 'eslint-plugin-prettier/recommended';
import globals from 'globals';
import tseslint from 'typescript-eslint';

export default tseslint.config(
  {
    ignores: ['eslint.config.mjs'],
  },
  eslint.configs.recommended,
  ...tseslint.configs.recommendedTypeChecked,
  eslintPluginPrettierRecommended,
  {
    languageOptions: {
      globals: {
        ...globals.node,
        ...globals.jest,
      },
      sourceType: 'commonjs',
      parserOptions: {
        projectService: true,
        tsconfigRootDir: import.meta.dirname,
      },
    },
  },
  {
    rules: {
      '@typescript-eslint/no-explicit-any': 'error', // nest new sets 'off'
      '@typescript-eslint/no-floating-promises': 'warn',
      '@typescript-eslint/no-unsafe-argument': 'warn',
      'prettier/prettier': ['error', { endOfLine: 'auto' }],
    },
  },
);
```

**❌ Không nên:** Disable hàng loạt rules bằng `eslint-disable` mà không có justification cụ thể.

**Tại sao:** ESLint 9 dùng flat config mặc định, ESLint 10 không còn đọc `.eslintrc.js`. ESLint tự động phát hiện code smells (unused vars, implicit any, unsafe assignments) mà code review thủ công dễ bỏ sót. Kết hợp Prettier plugin tránh conflict giữa format rules và lint rules.

**Tham khảo:** [ESLint — Getting Started](https://eslint.org/docs/latest/use/getting-started) · [typescript-eslint](https://typescript-eslint.io/)

---

### 2.4. Cấu hình Prettier thống nhất

**✅ Nên:** Tạo file `.prettierrc` ở root project:

```json
{
  "singleQuote": true,
  "trailingComma": "all",
  "printWidth": 100,
  "tabWidth": 2,
  "semi": true
}
```

**❌ Không nên:** Mỗi member tự format theo style riêng, hoặc không bật `formatOnSave`.

**Tại sao:** Prettier loại bỏ hoàn toàn tranh cãi về formatting — mọi người dùng chung config, code diff chỉ chứa logic changes, không lẫn whitespace/formatting noise. Giảm merge conflicts đáng kể.

**Tham khảo:** [Prettier — Options](https://prettier.io/docs/en/options.html)

---

### 2.5. Định nghĩa scripts chuẩn trong package.json

**✅ Nên:** Mọi project phải có tập scripts tối thiểu sau:

```json
{
  "scripts": {
    "build": "nest build",
    "start": "nest start",
    "start:dev": "nest start --watch",
    "start:debug": "nest start --debug --watch",
    "start:prod": "node dist/main",
    "lint": "eslint \"{src,apps,libs,test}/**/*.ts\" --fix",
    "format": "prettier --write \"src/**/*.ts\" \"test/**/*.ts\"",
    "test": "jest",
    "test:watch": "jest --watch",
    "test:cov": "jest --coverage",
    "test:e2e": "jest --config ./test/jest-e2e.json"
  }
}
```

**❌ Không nên:** Mỗi member tự chạy lệnh khác nhau (vd: `npx ts-node src/main.ts` thay vì `pnpm start:dev`).

**Tại sao:** Scripts thống nhất = communication bằng code. Member mới chỉ cần đọc `package.json` để biết cách dev, build, test, lint — không cần hỏi ai.

---

### 2.6. Setup Docker environment với Denv

**✅ Nên:** Sử dụng Denv để đồng nhất môi trường development trong team.

**Yêu cầu:**

- Docker & Docker Compose v2
- WSL2 (Windows) hoặc OrbStack (Mac — khuyến nghị thay Docker Desktop)
- Project đã có Git (`git init`)

```bash
# Cài đặt & xác thực
denv auth
denv version

# Tại root folder của project
denv svc init    # Tải template Docker mới nhất
denv env init    # Tạo file .denv.env
```

Cấu hình `.denv.env` cho NestJS:

```bash
DENV_PLATFORM=nodejs
PORT=3000
NODE_COMMAND=pnpm run start:dev
```

```bash
# Khởi chạy và truy cập
denv env up      # Khởi chạy containers
denv shell node  # Truy cập container
```

**❌ Không nên:** Mỗi member tự cài Node.js version khác nhau trên máy local mà không dùng container.

**Tại sao:** Denv đảm bảo mọi member dùng cùng Node version, cùng OS dependencies, cùng service configs. Chia sẻ qua Git nên không cần setup manual.

**Commands thường dùng:**

| Command | Mô tả |
| --- | --- |
| `denv svc init` | Tải template Docker mới nhất |
| `denv svc up` | Khởi chạy core services |
| `denv env init` | Tạo file `.denv.env` |
| `denv env up` | Khởi chạy containers |
| `denv shell` | Truy cập container |
| `denv update` | Update Denv |

---

### 2.7. Pre-commit validation với bss-cli

**✅ Nên:** Chạy `bss-cli` ở pre-commit hook, giống project v535: mỗi commit tự kiểm tra file size và ESLint trên file đã `git add`.

**Yêu cầu:**

- Denv đã setup (mục 2.6). `bss-cli` có sẵn trong container node, máy host không có, nên commit trong container.
- `eslint.config.mjs` theo mục 2.3.

```yaml
# .bss-cli.yaml — commit vào repo; same keys as v535
file_size:
  name: File Size
  limit: 10485760 # 10 MB

eslint:
  name: ESLint
  # The project's ESLint 9: v535 notes the global bss-cli ESLint (8.57.1) breaks on flat config rules
  bin: node_modules/.bin/eslint
  format: stylish
  standard: eslint.config.mjs
```

```bash
# .git/hooks/pre-commit — chmod +x; same hook as v535
#!/bin/bash
bss-cli validate:run
```

**❌ Không nên:** Bypass validator bằng `git commit --no-verify` trừ khi có lý do chính đáng và được lead approve.

**Tại sao:** Pre-commit validation là lớp bảo vệ cuối trước khi code vào repository. Nó bắt lỗi format, lint, và coding standard mà developer có thể quên chạy manual — đảm bảo không có bad code lọt vào main branch.

**Commands chính:**

| Command | Mô tả |
| --- | --- |
| `bss-cli validate:run` | Hook pre-commit gọi lệnh này, kiểm tra các file đã `git add` |
| `bss-cli validate:path` | Chạy tay trước khi commit; v535 dùng để chạy File Size, ESLint, Detect Secrets |
| `bss-cli version` | Kiểm tra version trong container |

---

### 2.8. Kiểm tra build trước khi deploy

**✅ Nên:** Luôn chạy build locally và verify output trước khi push:

```bash
# Build
pnpm run build

# Verify output
ls -la dist/
node dist/main.js
```

**❌ Không nên:** Push code chưa build thành công, rely hoàn toàn vào CI để phát hiện build errors.

**Tại sao:** Build errors phát hiện trên CI tốn thời gian pipeline + block cả team. Chạy build local mất 10–30s nhưng tránh được deployment failures.

---

## 3. Ví dụ minh họa thực tế

### 3.1. Walkthrough: Setup project NestJS mới từ đầu

Dưới đây là quy trình đầy đủ từ `nest new` đến commit đầu tiên với validator:

**Bước 1 — Khởi tạo project:**

```bash
pnpm dlx @nestjs/cli new my-project
cd my-project
```

Nest CLI tạo sẵn cấu trúc project, nhưng cần tuỳ chỉnh thêm cho team standard.

**Bước 2 — Cài đặt dependencies bổ sung:**

```bash
pnpm add @nestjs/config class-validator class-transformer  # ESLint 9, typescript-eslint, Prettier: already added by nest new
```

**Bước 3 — Cấu hình TypeScript strict mode:**

Mở `tsconfig.json`, thêm/sửa trong `compilerOptions`:

```json
{
  "compilerOptions": {
    "strict": true,
    "strictNullChecks": true,
    "strictPropertyInitialization": false,
    "noImplicitAny": true
  }
}
```

*Sau bước này, chạy `pnpm build` — fix tất cả type errors phát sinh từ strict mode trước khi tiếp tục.*

**Bước 4 — Sửa `eslint.config.mjs` và tạo `.prettierrc`:**

`nest new` đã tạo `eslint.config.mjs`, sửa theo mục 2.3. Tạo `.prettierrc` theo mục 2.4.

**Bước 5 — Setup Docker environment:**

```bash
denv svc init
denv env init
# Chỉnh sửa .denv.env: DENV_PLATFORM=nodejs, PORT=3000
denv env up
```

**Bước 6 — Setup pre-commit validator:**

Tạo `.bss-cli.yaml` và `.git/hooks/pre-commit` theo mục 2.7, rồi kiểm tra trong container:

```bash
denv shell node
bss-cli version
```

**Bước 7 — Verify toàn bộ setup:**

```bash
pnpm run lint      # Không có errors
pnpm run format    # Format tất cả files
pnpm run build     # Build thành công
pnpm run test      # Tests pass
```

**Bước 8 — Commit đầu tiên (test validator), chạy trong container:**

```bash
git add .
git commit -m "chore: initial project setup with team standards"
```

Nếu validator báo lỗi → sửa theo output của `bss-cli` → commit lại.

---

### 3.2. Before/After: Từ project thiếu chuẩn đến project đạt chuẩn

**Before** — Project không có standards:

- ❌ Không có `eslint.config.mjs` → code style mỗi người một kiểu
- ❌ `tsconfig.json` không bật strict → `any` tràn lan
- ❌ Không có pre-commit hook → code lỗi format lọt vào repo
- ❌ Member A dùng npm, member B dùng yarn → lockfile conflict

**After** — Áp dụng standards:

- ✅ ESLint + Prettier enforce style tự động
- ✅ Strict mode bắt type errors ngay IDE
- ✅ bss-cli validator reject commit có lỗi
- ✅ Toàn team dùng pnpm + Denv → identical environment

---

## 4. Tooling & Config

### 4.1. Checklist setup cho project mới

- [ ] Cài đặt NestJS CLI: `pnpm add -g @nestjs/cli`
- [ ] Khởi tạo project: `pnpm dlx @nestjs/cli new <project-name>`
- [ ] Chọn pnpm làm package manager
- [ ] Bật TypeScript strict mode trong `tsconfig.json`
- [ ] Sửa `eslint.config.mjs` theo mục 2.3 (`typescript-eslint` + Prettier)
- [ ] Tạo `.prettierrc` với config team chuẩn
- [ ] Thêm scripts chuẩn vào `package.json`
- [ ] Setup Docker environment: `denv svc init` → `denv env init` → `denv env up`
- [ ] Setup pre-commit validator: `.bss-cli.yaml` + `.git/hooks/pre-commit` gọi `bss-cli validate:run` (mục 2.7)
- [ ] Verify: `pnpm lint` → `pnpm build` → `pnpm test` → `git commit`
- [ ] Setup CI/CD pipeline (GitHub Actions, GitLab CI, etc.)

### 4.2. VS Code extensions khuyến nghị

| Extension | Mục đích |
| --- | --- |
| ESLint (`dbaeumer.vscode-eslint`) | Hiện lint errors real-time trong editor |
| Prettier (`esbenp.prettier-vscode`) | Auto-format on save |
| EditorConfig (`editorconfig.editorconfig`) | Đồng nhất indent, encoding giữa editors |
| Docker (`ms-azuretools.vscode-docker`) | Quản lý containers từ VS Code |

### 4.3. VS Code settings.json khuyến nghị

```json
{
  "editor.formatOnSave": true,
  "editor.defaultFormatter": "esbenp.prettier-vscode",
  "editor.codeActionsOnSave": {
    "source.fixAll.eslint": "explicit"
  },
  "typescript.tsdk": "node_modules/typescript/lib"
}
```

---

## References

- [NestJS CLI Documentation](https://docs.nestjs.com/cli/overview)
- [TypeScript — tsconfig Reference](https://www.typescriptlang.org/tsconfig)
- [TypeScript Handbook](https://www.typescriptlang.org/docs/handbook/intro.html)
- [ESLint — Getting Started](https://eslint.org/docs/latest/use/getting-started)
- [ESLint — Configuration](https://eslint.org/docs/latest/use/configure/)
- [Prettier — Options](https://prettier.io/docs/en/options.html)
- [pnpm — Motivation](https://pnpm.io/motivation)
- Denv Documentation: Hướng dẫn cài đặt tại [password.bssgroup.vn](http://password.bssgroup.vn/)
- bss-cli Validator: Chi tiết commands xem mục 2.7

## Changelog

| Date | Version | Change | By |
| :---- | :---- | :---- | :---- |
| 2026-11-18 | v1.0 | Chuyển từ Notion "NestJS Document" (page `33d71a38d3b28107ab01ce8844758499`, sửa 2026-04-09). Review và sửa nội dung, code trước khi publish. Owner duyệt trong chat ngày 2026-11-18. | Bắc PV |
