# NestJS Coding Standard 7.2 — Debugging

| Field | Value |
| :---- | :---- |
| Owner | Bắc PV — NodeJS BE Dev Lead |
| Audience | Dev (NodeJS BE) |
| Last reviewed | 2026-11-12 |
| Review cadence | Quarterly |
| Version | v1.0 |
| Linked from | Ref_Dev_nestjs-coding-standard_v1.0 |
| Status | Live |

Doc này là mục 7.2 của [NestJS Coding Standard](Ref_Dev_nestjs-coding-standard_v1.0.md), nhóm Observability. Doc nêu quy tắc về Debugging trong dự án NestJS, kèm lý do, ví dụ và config. Dev NodeJS BE đọc doc này khi viết code, review code và onboarding.

---

## 1. Tóm tắt & Phạm vi

> 🎯 **Debugging** là kỹ năng quan trọng giúp developer nhanh chóng xác định và sửa lỗi trong quá trình phát triển NestJS. Tài liệu này bao gồm:
> - Sử dụng **Node.js Inspector** và flag `--inspect` để debug runtime
> - Cấu hình **source maps** để debug trực tiếp trên TypeScript
> - Đặt **breakpoints** hiệu quả trong VSCode và Chrome DevTools
> - Debug trong các môi trường khác nhau: local, Docker, test
> - Kỹ thuật debug nâng cao: conditional breakpoints, logpoints, memory profiling

---

## 2. Quy tắc & Giải thích

### 2.1. Ưu tiên Debugger thay vì console.log

**Nên làm:**

- Dùng **Node.js built-in debugger** (`--inspect`) kết hợp VSCode hoặc Chrome DevTools để inspect variables, call stack, và step through code.
- Đặt breakpoints tại các điểm nghi ngờ thay vì rải `console.log` khắp nơi.

**Không nên:**

- Debug bằng cách thêm hàng chục `console.log` rồi quên xóa — gây rác code và có thể lọt vào production.
- Dùng `console.log(JSON.stringify(bigObject))` cho object lớn — debugger cho phép explore object interactively.

**Tại sao?** Debugger cho phép:

- Inspect mọi variable tại bất kỳ thời điểm nào mà không cần sửa code.
- Step into/over/out để theo dõi execution flow chính xác.
- Evaluate expressions trực tiếp trong Debug Console.
- Không để lại “rác” trong codebase.

---

### 2.2. Luôn bật Source Maps cho TypeScript

**Nên làm:**

- Bật `"sourceMap": true` trong `tsconfig.json` — cho phép debugger map từ compiled JS về TypeScript gốc.
- Giữ `"inlineSourceMap": false` trong production build để giảm bundle size.
- Xóa `*.map` khỏi `dist/` ở builder stage trước khi copy vào production image (mục 4.3).

**Không nên:**

- Debug trên compiled JavaScript (`dist/`) khi có thể debug trên TypeScript gốc.
- Deploy source maps lên production (lộ source code, tăng size).

**Tại sao?** NestJS projects viết bằng TypeScript, nhưng Node.js chạy JavaScript. Không có source maps, breakpoints sẽ hit vào file `.js` trong `dist/`, rất khó đọc và khó map về logic gốc.

---

### 2.3. Cấu hình VSCode Launch Configuration đúng cách

**Nên làm:**

- Tạo file `.vscode/launch.json` với các profiles: **Debug NestJS**, **Debug Current Test**, **Attach to Process**.
- Dùng `"request": "launch"` cho local dev, `"request": "attach"` cho Docker/remote.
- Set `"skipFiles"` để bỏ qua `node_modules` và internal Node.js files khi step through.

**Không nên:**

- Chạy `start:debug:brk` (`--inspect-brk`) rồi không attach debugger — app dừng ở dòng đầu chờ debugger, tưởng bị treo. `start:debug` (`--inspect`) không chờ.
- Debug mà không set `skipFiles` — bị lạc vào internal code của NestJS/Express/TypeORM.

**Tại sao?** Launch configuration chuẩn giúp cả team dùng chung setup, onboard nhanh, và tránh mất thời gian config lại mỗi lần.

---

### 2.4. Sử dụng Breakpoints thông minh

**Nên làm:**

- **Conditional breakpoints**: chỉ dừng khi điều kiện đúng — ví dụ `orderId === 'abc-123'`.
- **Logpoints**: log message tại breakpoint mà không dừng execution — thay thế `console.log` tạm thời.
- **Exception breakpoints**: bật “Uncaught Exceptions” trong VSCode để tự động dừng khi có unhandled error.

**Không nên:**

- Đặt breakpoint ở đầu mọi function — quá nhiều, mất thời gian step through.
- Quên tắt breakpoints cũ — debugger dừng ở chỗ không liên quan.

**Tại sao?** Conditional breakpoints và logpoints giúp debug chính xác mà không cần restart app hay sửa code. Đặc biệt hữu ích khi debug loop lớn hoặc request cụ thể trong hệ thống nhiều traffic.

---

### 2.5. Debug trong Docker

**Nên làm:**

- Expose debug port trong `docker-compose.yml` chỉ trên localhost của host: `ports: ["127.0.0.1:9229:9229"]`.
- Chạy app với `node --inspect=0.0.0.0:9229` trong container.
- Dùng VSCode attach configuration với `"remoteRoot"` mapping đúng path trong container.

**Không nên:**

- Expose debug port `9229` trên production hoặc public network — ai kết nối được port này đều chạy được code trong process.
- Dùng `--inspect` không có `=0.0.0.0` trong Docker — mặc định chỉ bind `127.0.0.1`, không thể attach từ host.

**Tại sao?** Nhiều team chạy NestJS trong Docker. Nếu không cấu hình debug port đúng, không thể attach debugger từ host machine, buộc phải fallback về `console.log`.

---

### 2.6. Debug Unit Tests và E2E Tests

**Nên làm:**

- Dùng VSCode launch config “Debug Current Test” để chạy Jest với `--inspect-brk` trên file đang mở.
- Dùng `test.only()` hoặc `.only` để focus vào test case cần debug.
- Đặt breakpoint trong cả test file và source file để trace execution.

**Không nên:**

- Debug test bằng cách thêm `console.log` vào source code rồi chạy `pnpm test`.
- Chạy toàn bộ test suite khi chỉ cần debug 1 test case — chậm và nhiều noise.

---

### 2.7. Debug NestJS-specific: Middleware, Guards, Interceptors, Pipes

**Nên làm:**

- Đặt breakpoint ở `canActivate()` (Guards), `intercept()` (Interceptors), `transform()` (Pipes) để trace request lifecycle.
- Dùng `Logger.debug()` có context (`new Logger(GuardName.name)`) để phân biệt log từ các layer.
- Khi request không vào handler: kiểm tra theo thứ tự Middleware → Guard → Interceptor → Pipe.

**Không nên:**

- Chỉ debug ở handler (controller method) khi lỗi có thể xảy ra ở middleware hoặc guard.
- Quên rằng exception filters catch errors trước khi chúng đến client — đặt breakpoint ở filter để xem error gốc.

**Tại sao?** NestJS có request lifecycle phức tạp: Middleware → Guards → Interceptors → Pipes → Handler → Interceptors (response) → Filters (exceptions). Bug có thể xảy ra ở bất kỳ layer nào.

---

## 3. Ví dụ minh họa thực tế

### 3.1. Debug một API endpoint bị trả wrong data

**Tình huống**: `GET /orders/:id` trả về `totalAmount: 0` dù order có items.

**Bước 1**: Đặt breakpoint ở controller handler

```ts
// orders.controller.ts
@Get(':id')
async findOne(@Param('id', ParseIntPipe) id: number): Promise<OrderResponseDto> {
  const order = await this.ordersService.findOne(id); // ← Breakpoint here
  return plainToInstance(OrderResponseDto, order, { excludeExtraneousValues: true });
}
```

**Bước 2**: Inspect `order` object trong debugger → thấy `order.totalAmount = 150000` ✅

**Bước 3**: Step over `plainToInstance` → kết quả `totalAmount: undefined` ❌

**Bước 4**: Kiểm tra `OrderResponseDto` → thiếu `@Expose()` trên `totalAmount`

```ts
// Before (bug)
export class OrderResponseDto {
  @Expose() id: string;
  @Expose() status: string;
  totalAmount: number; // ← Thiếu @Expose() → bị strip bởi excludeExtraneousValues
}

// After (fix)
export class OrderResponseDto {
  @Expose() id: string;
  @Expose() status: string;
  @Expose() totalAmount: number; // ✅ Thêm @Expose()
}
```

**Bài học**: Debugger giúp tìm ra bug trong 2 phút thay vì thêm 10 dòng `console.log`.

---

### 3.2. Debug Guard không cho phép request hợp lệ

**Tình huống**: User có role `staff` nhưng endpoint `@Roles(Role.STAFF)` trả 403.

**Bước 1**: Bật “Exception breakpoints” → Caught: `ForbiddenException`

**Bước 2**: Đặt breakpoint ở `RolesGuard.canActivate()`

```ts
// roles.guard.ts
canActivate(context: ExecutionContext): boolean {
  const requiredRoles = this.reflector.getAllAndOverride<Role[]>(ROLES_KEY, [
    context.getHandler(),
    context.getClass(),
  ]);
  if (!requiredRoles) return true;
  const { user } = context.switchToHttp().getRequest();
  // ← Breakpoint: inspect user.roles → ['Staff'] (PascalCase!)
  return requiredRoles.some((role) => user.roles?.includes(role));
  // requiredRoles = ['staff'] (lowercase enum) → includes() = false
}
```

**Root cause**: JWT payload chứa `roles: ['Staff']` (PascalCase) nhưng enum `Role.STAFF = 'staff'` (lowercase).

**Fix**: Normalize roles khi decode JWT hoặc thống nhất format.

---

### 3.3. Debug Memory Leak với Chrome DevTools

**Bước 1**: Chạy app với `--inspect`

```bash
node --inspect dist/main.js
```

**Bước 2**: Mở Chrome → `chrome://inspect` → chọn target

**Bước 3**: Tab **Memory** → Take Heap Snapshot trước và sau khi gửi 1000 requests

**Bước 4**: Compare snapshots → tìm objects tăng bất thường

**Bước 5**: Thường gặp trong NestJS:

- Event listeners không remove khi module destroy
- Cache không có TTL/max size
- Streams không close properly

---

## 4. Tooling & Config

### 4.1. VSCode Launch Configuration

```json
// .vscode/launch.json
{
  "version": "0.2.0",
  "configurations": [
    {
      "name": "Debug NestJS",
      "type": "node",
      "request": "launch",
      "runtimeExecutable": "pnpm",
      "runtimeArgs": ["run", "start:debug"],
      "sourceMaps": true,
      "cwd": "${workspaceFolder}",
      "console": "integratedTerminal",
      "skipFiles": [
        "<node_internals>/**",
        "**/node_modules/**"
      ]
    },
    {
      "name": "Debug Current Test",
      "type": "node",
      "request": "launch",
      "runtimeExecutable": "pnpm",
      "runtimeArgs": [
        "run", "test", "--",
        "--testPathPattern", "${fileBasename}",
        "--no-coverage"
      ],
      "sourceMaps": true,
      "console": "integratedTerminal",
      "skipFiles": ["<node_internals>/**"]
    },
    {
      "name": "Attach to Docker",
      "type": "node",
      "request": "attach",
      "port": 9229,
      "address": "localhost",
      "localRoot": "${workspaceFolder}",
      "remoteRoot": "/app",
      "sourceMaps": true,
      "skipFiles": ["<node_internals>/**"]
    }
  ]
}
```

### 4.2. package.json scripts

```json
{
  "scripts": {
    "start:debug": "nest start --debug --watch",
    "start:debug:brk": "nest start --watch --exec \"node --inspect-brk\"",
    "test:debug": "node --inspect-brk -r tsconfig-paths/register -r ts-node/register node_modules/jest/bin/jest.js --runInBand"
  }
}
```

> `nest start --debug` truyền `--inspect` (không phải `--inspect-brk`), nên app chạy ngay và inspector bind `127.0.0.1:9229`. `start:debug:brk` dùng `--exec` để chạy `--inspect-brk`, app chờ debugger attach. Trên máy dev không bind `0.0.0.0`.

### 4.3. tsconfig.json — Source Maps

```json
{
  "compilerOptions": {
    "sourceMap": true,
    "inlineSources": true,
    "declaration": true,
    "removeComments": false
  }
}
```

> `inlineSources: true` nhúng TypeScript source vào source map file, giúp debugger hiển thị code gốc ngay cả khi file `.ts` không có trên disk (hữu ích trong Docker).

`nest build` và `nest start` cùng đọc `tsconfig.build.json`. Tắt `sourceMap` ở đó thì `start:debug` cũng mất source map, nên xóa `*.map` ở builder stage:

```docker
# Dockerfile, builder stage — keep source maps (with inlined TS source) out of the production image
RUN pnpm run build && find dist -name '*.map' -delete
```

### 4.4. Docker Compose — Debug Mode

```yaml
# docker-compose.debug.yml
services:
  api:
    build:
      context: .
      dockerfile: Dockerfile.dev
    command: pnpm exec nest start --debug=0.0.0.0:9229 --watch --no-shell
    ports:
      - "3000:3000"
      - "127.0.0.1:9229:9229"  # Debug port, host localhost only
    volumes:
      - ./src:/app/src  # Hot reload source
    environment:
      - NODE_ENV=development
```

> Trong container inspector bind `0.0.0.0` để Docker forward được, còn host chỉ publish ra `127.0.0.1`. `--no-shell` để `--watch` kill được process cũ khi image không có `ps` (như `node:*-slim`), tránh lỗi `EADDRINUSE`.

### 4.5. ndb — Enhanced Debugging Experience

```bash
# Cài đặt
pnpm add -g ndb

# Chạy với ndb — tự mở Chrome DevTools riêng
ndb pnpm run start:debug
```

`ndb` cung cấp UI tốt hơn `chrome://inspect`: tự detect child processes, blackbox scripts, và persistent breakpoints.

---

## References

- [Node.js Debugging Guide](https://nodejs.org/en/learn/getting-started/debugging) — Official Node.js debugging documentation
- [Node.js Inspector API](https://nodejs.org/docs/latest/api/inspector.html) — `node:inspector` module reference
- [NestJS Recipes: Hot Reload](https://docs.nestjs.com/recipes/hot-reload) — HMR setup liên quan đến debug workflow
- [VSCode Debugging](https://code.visualstudio.com/docs/editor/debugging) — Launch configurations, breakpoints, logpoints
- [Chrome DevTools — Memory](https://developer.chrome.com/docs/devtools/memory) — Heap snapshots, allocation profiling
- [Jest Troubleshooting](https://jestjs.io/docs/troubleshooting) — Debug Jest tests với `--inspect-brk`
- [V8 Inspector Protocol](https://v8.dev/docs/inspector) — Underlying protocol cho Node.js debugging

## Changelog

| Date | Version | Change | By |
| :---- | :---- | :---- | :---- |
| 2026-11-18 | v1.0 | Chuyển từ Notion "NestJS Document" (page `33d71a38d3b281078a01fefb52b955c2`, sửa 2026-04-09). Review và sửa nội dung, code trước khi publish. Owner duyệt trong chat ngày 2026-11-18. | Bắc PV |
