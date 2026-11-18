# NestJS Coding Standard 5.2 — Authorization

| Field | Value |
| :---- | :---- |
| Owner | Bắc PV — NodeJS BE Dev Lead |
| Audience | Dev (NodeJS BE) |
| Last reviewed | 2026-11-12 |
| Review cadence | Quarterly |
| Version | v1.0 |
| Linked from | Ref_Dev_nestjs-coding-standard_v1.0 |
| Status | Live |

Doc này là mục 5.2 của [NestJS Coding Standard](Ref_Dev_nestjs-coding-standard_v1.0.md), nhóm Security. Doc nêu quy tắc về Authorization trong dự án NestJS, kèm lý do, ví dụ và config. Dev NodeJS BE đọc doc này khi viết code, review code và onboarding.

---

## 1. Tóm tắt & Phạm vi

> 🎯 **Authorization** (phân quyền) quyết định **user đã xác thực được phép làm gì**. Khác với Authentication (xác thực danh tính), Authorization kiểm tra quyền truy cập vào tài nguyên và hành động cụ thể.

**Phạm vi áp dụng:**

- Mọi API endpoint cần kiểm soát quyền truy cập (admin, staff, customer, …)
- Resource-level access control (user chỉ được sửa/xóa resource của mình)
- Feature flags / permission-based access
- Multi-tenant systems cần isolation giữa các tenants

**Tại sao quan trọng?**

- Thiếu authorization → user thường có thể truy cập data/chức năng của admin hoặc user khác (IDOR, privilege escalation)
- OWASP Top 10 luôn có **Broken Access Control** ở vị trí #1
- Authorization bugs thường khó phát hiện bằng testing thông thường — cần thiết kế có hệ thống

---

## 2. Các mô hình phân quyền

### 2.1 RBAC – Role-Based Access Control

**Khái niệm:** Gán quyền cho **role** (vai trò), user được gán role → thừa hưởng quyền của role đó.

**Khi nào dùng:**

- Hệ thống có số lượng roles cố định, ít thay đổi (admin, staff, customer, viewer)
- Quyền gắn liền với vai trò, không phụ thuộc vào context của resource
- Phần lớn CRUD apps, admin panels, internal tools

**Ưu điểm:**

- Đơn giản, dễ hiểu, dễ implement
- Dễ audit: chỉ cần xem user có role gì
- Phù hợp 80% use cases thực tế

**Nhược điểm:**

- Role explosion khi business phức tạp (role per feature per action)
- Không xử lý được “user chỉ được sửa resource của mình” — cần kết hợp thêm logic

**Triển khai trong NestJS:**

```ts
// 1. Định nghĩa roles enum
export enum Role {
  ADMIN = 'admin',
  STAFF = 'staff',
  CUSTOMER = 'customer',
}
```

```ts
// 2. Custom decorator gắn metadata
import { SetMetadata } from '@nestjs/common';

export const ROLES_KEY = 'roles';
export const Roles = (...roles: Role[]) => SetMetadata(ROLES_KEY, roles);
```

```ts
// 3. RolesGuard — đọc metadata, so sánh với user.roles từ JWT
@Injectable()
export class RolesGuard implements CanActivate {
  constructor(private reflector: Reflector) {}

  canActivate(context: ExecutionContext): boolean {
    const requiredRoles = this.reflector.getAllAndOverride<Role[]>(ROLES_KEY, [
      context.getHandler(),
      context.getClass(),
    ]);
    if (!requiredRoles) return true; // Không gắn @Roles → cho qua

    const { user } = context.switchToHttp().getRequest();
    return requiredRoles.some((role) => user.roles?.includes(role));
  }
}
```

```ts
// 4. Sử dụng trong controller
// No @UseGuards: JwtAuthGuard and RolesGuard run globally (section 5.1)
@Controller('users')
export class UsersController {
  @Get()
  @Roles(Role.ADMIN)
  @ApiOperation({ summary: 'Danh sách users — chỉ admin' })
  findAll(): Promise<UserResponseDto[]> {
    return this.usersService.findAll();
  }

  @Get(':id')
  @Roles(Role.ADMIN, Role.STAFF)
  @ApiOperation({ summary: 'Chi tiết user — admin hoặc staff' })
  findOne(@Param('id', ParseIntPipe) id: number): Promise<UserResponseDto> {
    return this.usersService.findOne(id);
  }
}
```

### 2.2 ABAC – Attribute-Based Access Control

**Khái niệm:** Quyết định dựa trên **attributes** (thuộc tính) của subject (user), resource, action, và environment.

**Khi nào dùng:**

- Quyền phụ thuộc vào context: “user chỉ được sửa order của mình”, “manager chỉ xem nhân viên trong department mình”
- Multi-tenant: tenant A không được truy cập data tenant B
- Quy tắc phức tạp cần linh hoạt hơn role đơn thuần

**Ưu điểm:**

- Linh hoạt cao, mô tả được hầu hết business rules
- Không bị role explosion

**Nhược điểm:**

- Phức tạp hơn RBAC, khó debug/audit
- Cần thiết kế policy engine cẩn thận

**Triển khai trong NestJS (Policy-based pattern):**

```ts
// 1. Định nghĩa Policy interface
export interface Policy {
  /** Tên policy — dùng cho logging/debugging */
  name: string;
  /** Kiểm tra user có quyền thực hiện action trên resource không */
  validate(user: UserPayload, resource: any, action?: string): boolean;
}
```

```ts
// 2. Concrete policy — user chỉ sửa resource của mình
export class OwnerPolicy implements Policy {
  name = 'OwnerPolicy';

  validate(user: UserPayload, resource: { userId: number }): boolean {
    return user.sub === resource.userId;
  }
}
```

```ts
// 3. Concrete policy — admin hoặc owner
export class AdminOrOwnerPolicy implements Policy {
  name = 'AdminOrOwnerPolicy';

  validate(user: UserPayload, resource: { userId: number }): boolean {
    return user.roles.includes(Role.ADMIN) || user.sub === resource.userId;
  }
}
```

```ts
// 4. Apply the policy in the service, after loading the resource.
//    Guards only read the JWT (section 3.2), so the DB lookup stays out of them.
@Injectable()
export class OrdersService {
  private readonly updatePolicy: Policy = new AdminOrOwnerPolicy();

  constructor(
    @InjectRepository(Order)
    private readonly ordersRepository: Repository<Order>,
  ) {}

  async update(id: number, dto: UpdateOrderDto, user: UserPayload): Promise<Order> {
    const order = await this.ordersRepository.findOneBy({ id });
    if (!order) throw new NotFoundException(`Order ${id} not found`);

    if (!this.updatePolicy.validate(user, order)) {
      throw new ForbiddenException(`${this.updatePolicy.name}: no access to order ${id}`);
    }
    return this.ordersRepository.save({ ...order, ...dto });
  }
}
```

Policy chỉ đọc `user` và resource truyền vào. Service load resource rồi gọi `validate()`, vì guard không query DB (mục 3.2).

### 2.3 Kết hợp RBAC + ABAC (Recommended)

> 💡 Trong thực tế, hầu hết dự án **kết hợp cả hai**: RBAC cho coarse-grained access (admin vs user), ABAC cho fine-grained access (owner check, department scope, …).

```ts
// Compose decorator — role check + Swagger; the global guards (section 5.1) do the rest
export function AdminOnly() {
  return applyDecorators(
    Roles(Role.ADMIN),
    ApiCookieAuth(),
  );
}

// ABAC (owner check) has no decorator: the service applies AdminOrOwnerPolicy after loading the order (section 2.2)
```

---

## 3. Quy tắc & Giải thích

### 3.1 Guard execution order

NestJS thực thi guards theo thứ tự:

1. **Global guards** (đăng ký qua `app.useGlobalGuards()` hoặc `APP_GUARD`)
2. **Controller-level guards** (`@UseGuards()` trên class)
3. **Method-level guards** (`@UseGuards()` trên method)

Tất cả guards phải trả `true` → request mới được xử lý. Nếu bất kỳ guard nào trả `false` hoặc throw → request bị reject.

**Best practice:** Đặt AuthGuard ở global/controller level, RolesGuard ở method level.

### 3.2 Nên làm

- **Deny by default:** Mọi route mặc định phải require auth. Chỉ mở public bằng `@Public()` decorator + `@SetMetadata('isPublic', true)`

```ts
// Global guard — deny by default
@Injectable()
export class JwtAuthGuard extends AuthGuard('jwt') {
  constructor(private reflector: Reflector) {
    super();
  }

  canActivate(context: ExecutionContext) {
    const isPublic = this.reflector.getAllAndOverride<boolean>('isPublic', [
      context.getHandler(),
      context.getClass(),
    ]);
    if (isPublic) return true;
    return super.canActivate(context);
  }
}

// Registered once as APP_GUARD in AppModule, together with RolesGuard (section 5.1)
```

- **Tách biệt Authentication và Authorization guards:** AuthGuard validate token → RolesGuard check role → service check resource ownership (policy, mục 2.2). Không gộp tất cả vào 1 guard.
- **Guard chỉ check quyền, không chứa business logic:**

```ts
// ✅ Good — guard chỉ check
@Injectable()
export class RolesGuard implements CanActivate {
  canActivate(context: ExecutionContext): boolean {
    // Chỉ so sánh roles, không query DB, không gọi external service
    return requiredRoles.some((role) => user.roles?.includes(role));
  }
}

// ❌ Bad — guard chứa business logic
@Injectable()
export class OrderGuard implements CanActivate {
  async canActivate(context: ExecutionContext): Promise<boolean> {
    const order = await this.ordersRepo.findOne(orderId);
    if (order.status === 'cancelled') throw new BadRequestException(); // Business logic!
    return order.userId === user.sub;
  }
}
```

- **Resource ownership check nên ở service layer** khi logic phức tạp (query DB, check relations). Guard chỉ phù hợp cho check đơn giản (role, permission từ token).

```ts
// Service — ownership check phức tạp
async update(userId: number, orderId: number, dto: UpdateOrderDto): Promise<Order> {
  const order = await this.ordersRepository.findOneOrFail(orderId);

  if (order.userId !== userId) {
    throw new ForbiddenException(`You do not own order ${orderId}`);
  }

  if (order.status !== OrderStatus.PENDING) {
    throw new BadRequestException(
      `Order ${orderId} status '${order.status}', expected '${OrderStatus.PENDING}'`,
    );
  }

  return this.ordersRepository.save({ ...order, ...dto });
}
```

- **Dùng `ForbiddenException` (403) cho authorization failure**, không dùng `UnauthorizedException` (401):
- 401 = chưa xác thực (thiếu/sai token)
- 403 = đã xác thực nhưng không đủ quyền
- **Store roles/permissions trong JWT claims** để guard không cần query DB mỗi request:

```ts
// JWT payload nên chứa
interface JwtPayload {
  sub: number;         // userId
  roles: Role[];       // ['admin', 'staff']
  permissions?: string[]; // ['orders:read', 'orders:write'] — optional, cho ABAC
  iat: number;
  exp: number;
}
```

### 3.3 Không nên làm

- ❌ **Check quyền bằng `if` rải rác trong controller/service** — khó maintain, dễ bỏ sót
- ❌ **Hardcode role names dưới dạng string** — dùng enum để compiler bắt lỗi typo
- ❌ **Dùng chung 1 guard xử lý cả authn + authz** — vi phạm Single Responsibility
- ❌ **Trust client-side role** (gửi role qua body/header) — role phải từ token đã verify
- ❌ **Quên check authorization ở cả list endpoints** — user A list được data của user B (IDOR)
- ❌ **Return 404 thay vì 403** khi user không có quyền — che giấu sự tồn tại của resource có thể là design choice, nhưng cần nhất quán và có chủ đích

---

## 4. Ví dụ minh họa thực tế

### 4.1 Walkthrough: Module Orders với RBAC + Owner check

**Yêu cầu business:**

- Admin: CRUD tất cả orders
- Staff: xem tất cả orders, update status
- Customer: chỉ xem/tạo/huỷ orders của mình

**Bước 1: Định nghĩa roles và decorators**

```ts
// src/common/guards/roles.enum.ts
export enum Role {
  ADMIN = 'admin',
  STAFF = 'staff',
  CUSTOMER = 'customer',
}

// src/common/decorators/roles.decorator.ts
export const ROLES_KEY = 'roles';
export const Roles = (...roles: Role[]) => SetMetadata(ROLES_KEY, roles);

// src/common/decorators/current-user.decorator.ts
export const CurrentUser = createParamDecorator(
  (data: keyof UserPayload | undefined, ctx: ExecutionContext) => {
    const user = ctx.switchToHttp().getRequest().user;
    return data ? user?.[data] : user;
  },
);
```

**Bước 2: Controller với phân quyền rõ ràng**

```ts
@ApiTags('orders')
@Controller('orders')
@ApiCookieAuth()
export class OrdersController {
  constructor(private readonly ordersService: OrdersService) {}

  // Admin + Staff: xem tất cả
  @Get()
  @Roles(Role.ADMIN, Role.STAFF)
  @ApiOperation({ summary: 'Danh sách tất cả orders' })
  findAll(@Query() query: ListOrderDto): Promise<PaginatedResult<OrderResponseDto>> {
    return this.ordersService.findAll(query);
  }

  // Customer: chỉ xem orders của mình
  @Get('my-orders')
  @Roles(Role.CUSTOMER)
  @ApiOperation({ summary: 'Danh sách orders của tôi' })
  findMyOrders(
    @CurrentUser('sub') userId: number,
    @Query() query: ListOrderDto,
  ): Promise<PaginatedResult<OrderResponseDto>> {
    return this.ordersService.findByUser(userId, query);
  }

  // Tất cả roles: xem chi tiết, nhưng service check ownership
  @Get(':id')
  @Roles(Role.ADMIN, Role.STAFF, Role.CUSTOMER)
  @ApiOperation({ summary: 'Chi tiết order' })
  findOne(
    @Param('id', ParseIntPipe) id: number,
    @CurrentUser() user: UserPayload,
  ): Promise<OrderResponseDto> {
    return this.ordersService.findOneWithAuth(id, user);
  }

  // Customer: tạo order
  @Post()
  @Roles(Role.CUSTOMER)
  @ApiOperation({ summary: 'Tạo order mới' })
  create(
    @Body() dto: CreateOrderDto,
    @CurrentUser('sub') userId: number,
  ): Promise<OrderResponseDto> {
    return this.ordersService.create(userId, dto);
  }

  // Admin: xoá order
  @Delete(':id')
  @Roles(Role.ADMIN)
  @HttpCode(HttpStatus.NO_CONTENT)
  @ApiOperation({ summary: 'Xoá order — chỉ admin' })
  remove(@Param('id', ParseIntPipe) id: number): Promise<void> {
    return this.ordersService.remove(id);
  }
}
```

**Bước 3: Service với ownership check**

```ts
@Injectable()
export class OrdersService {
  constructor(
    @InjectRepository(Order)
    private readonly ordersRepository: Repository<Order>,
  ) {}

  async findOneWithAuth(id: number, user: UserPayload): Promise<Order> {
    const order = await this.ordersRepository.findOne({ where: { id } });
    if (!order) {
      throw new NotFoundException(`Order ${id} not found`);
    }

    // Admin/Staff xem được tất cả, Customer chỉ xem của mình
    if (
      !user.roles.includes(Role.ADMIN) &&
      !user.roles.includes(Role.STAFF) &&
      order.userId !== user.sub
    ) {
      throw new ForbiddenException(
        `You do not have permission to access order ${id}`,
      );
    }

    return order;
  }

  async cancel(orderId: number, user: UserPayload): Promise<Order> {
    const order = await this.findOneWithAuth(orderId, user);

    if (order.status !== OrderStatus.PENDING) {
      throw new BadRequestException(
        `Order ${orderId} status '${order.status}', expected '${OrderStatus.PENDING}'`,
      );
    }

    order.status = OrderStatus.CANCELLED;
    return this.ordersRepository.save(order);
  }
}
```

### 4.2 Before / After: Từ ad-hoc check đến systematic authorization

**❌ Before — ad-hoc, rải rác, dễ bỏ sót:**

```ts
@Controller('orders')
export class OrdersController {
  @Get(':id')
  async findOne(@Param('id') id: number, @Req() req: Request) {
    const order = await this.ordersRepo.findOne({ where: { id } });
    // Check rải rác, không nhất quán
    if (req.user.role !== 'admin' && order.userId !== req.user.id) {
      throw new HttpException('Forbidden', 403);
    }
    return order; // Trả raw entity!
  }

  @Patch(':id')
  async update(@Param('id') id: number, @Body() body: any, @Req() req: Request) {
    // Copy-paste check — dễ quên khi thêm endpoint mới
    const order = await this.ordersRepo.findOne({ where: { id } });
    if (req.user.role !== 'admin' && order.userId !== req.user.id) {
      throw new HttpException('Forbidden', 403);
    }
    return this.ordersRepo.save({ ...order, ...body });
  }
}
```

**✅ After — systematic, reusable, auditable:**

```ts
@Controller('orders')
@ApiCookieAuth()
export class OrdersController {
  @Get(':id')
  @Roles(Role.ADMIN, Role.STAFF, Role.CUSTOMER)
  @ApiOperation({ summary: 'Chi tiết order' })
  async findOne(
    @Param('id', ParseIntPipe) id: number,
    @CurrentUser() user: UserPayload,
  ): Promise<OrderResponseDto> {
    // Ownership check tập trung trong service
    return this.ordersService.findOneWithAuth(id, user);
  }

  @Patch(':id')
  @Roles(Role.ADMIN, Role.STAFF, Role.CUSTOMER)
  @ApiOperation({ summary: 'Cập nhật order' })
  async update(
    @Param('id', ParseIntPipe) id: number,
    @Body() dto: UpdateOrderDto,
    @CurrentUser() user: UserPayload,
  ): Promise<OrderResponseDto> {
    return this.ordersService.updateWithAuth(id, dto, user);
  }
}
```

---

## 5. Tooling & Config

### 5.1 Setup guard registration

```ts
// src/common/guards/index.ts — barrel export
export { RolesGuard } from './roles.guard';
export { ROLES_KEY, Roles } from '../decorators/roles.decorator';
export { Role } from './roles.enum';
```

```ts
// app.module.ts — global guard registration
import { APP_GUARD } from '@nestjs/core';

@Module({
  providers: [
    // The only place guards are registered. Order: AuthGuard → RolesGuard
    { provide: APP_GUARD, useClass: JwtAuthGuard },
    { provide: APP_GUARD, useClass: RolesGuard },
  ],
})
export class AppModule {}
```

### 5.2 Testing guards

```ts
// roles.guard.spec.ts
describe('RolesGuard', () => {
  let guard: RolesGuard;
  let reflector: Reflector;

  beforeEach(async () => {
    const module = await Test.createTestingModule({
      providers: [RolesGuard, Reflector],
    }).compile();
    guard = module.get(RolesGuard);
    reflector = module.get(Reflector);
  });

  it('should allow when no roles required', () => {
    jest.spyOn(reflector, 'getAllAndOverride').mockReturnValue(undefined);
    expect(guard.canActivate(mockContext)).toBe(true);
  });

  it('should allow admin when admin role required', () => {
    jest.spyOn(reflector, 'getAllAndOverride').mockReturnValue([Role.ADMIN]);
    mockContext.switchToHttp().getRequest.mockReturnValue({
      user: { sub: 1, roles: [Role.ADMIN] },
    });
    expect(guard.canActivate(mockContext)).toBe(true);
  });

  it('should deny customer when admin role required', () => {
    jest.spyOn(reflector, 'getAllAndOverride').mockReturnValue([Role.ADMIN]);
    mockContext.switchToHttp().getRequest.mockReturnValue({
      user: { sub: 2, roles: [Role.CUSTOMER] },
    });
    expect(guard.canActivate(mockContext)).toBe(false);
  });
});
```

### 5.3 Permission matrix documentation

Tạo bảng permission matrix cho team review:

| Endpoint | Admin | Staff | Customer | Note |
| --- | --- | --- | --- | --- |
| `GET /orders` | ✅ | ✅ | ❌ | Xem tất cả orders |
| `GET /orders/my-orders` | ❌ | ❌ | ✅ | Chỉ orders của mình |
| `GET /orders/:id` | ✅ | ✅ | ✅ (owner) | Service check ownership |
| `POST /orders` | ❌ | ❌ | ✅ | Tạo order |
| `PATCH /orders/:id` | ✅ | ✅ (status) | ✅ (owner, pending) | Business rules trong service |
| `DELETE /orders/:id` | ✅ | ❌ | ❌ | Chỉ admin |

---

## References

- [NestJS Authorization docs](https://docs.nestjs.com/security/authorization)
- [NestJS Guards docs](https://docs.nestjs.com/guards)
- [OWASP Broken Access Control](https://owasp.org/Top10/A01_2021-Broken_Access_Control/)
- [NIST RBAC model](https://csrc.nist.gov/projects/role-based-access-control)
- [NIST ABAC guide](https://csrc.nist.gov/publications/detail/sp/800-162/final)
- [NestJS Coding Standard 5.1 — Authentication](Ref_Dev_s5.1_nestjs-authentication_v1.0.md) — Xác thực, JWT, API Key (prerequisite cho Authorization)

## Changelog

| Date | Version | Change | By |
| :---- | :---- | :---- | :---- |
| 2026-11-18 | v1.0 | Chuyển từ Notion "NestJS Document" (page `33d71a38d3b2819cae35c75c571545f0`, sửa 2026-04-09). Review và sửa nội dung, code trước khi publish. Owner duyệt trong chat ngày 2026-11-18. | Bắc PV |
