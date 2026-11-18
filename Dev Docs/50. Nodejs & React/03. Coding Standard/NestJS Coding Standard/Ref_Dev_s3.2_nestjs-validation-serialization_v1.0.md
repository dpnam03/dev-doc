# NestJS Coding Standard 3.2 — Validation & Serialization

| Field | Value |
| :---- | :---- |
| Owner | Bắc PV — NodeJS BE Dev Lead |
| Audience | Dev (NodeJS BE) |
| Last reviewed | 2026-11-12 |
| Review cadence | Quarterly |
| Version | v1.0 |
| Linked from | Ref_Dev_nestjs-coding-standard_v1.0 |
| Status | Live |

Doc này là mục 3.2 của [NestJS Coding Standard](Ref_Dev_nestjs-coding-standard_v1.0.md), nhóm API & Data handling. Doc nêu quy tắc về Validation & Serialization trong dự án NestJS, kèm lý do, ví dụ và config. Dev NodeJS BE đọc doc này khi viết code, review code và onboarding.

---

## 1. Tóm tắt & Phạm vi

**Chủ đề:** Validation input và serialization output trong NestJS — đảm bảo dữ liệu vào hợp lệ và dữ liệu ra an toàn, nhất quán.

**Vấn đề giải quyết:**

- Client gửi dữ liệu sai format, thiếu field, hoặc chứa field không mong muốn → gây runtime errors hoặc lỗ hổng bảo mật (mass assignment).
- Response trả thẳng entity từ database → lộ field nhạy cảm (password, internal metadata, cost price).
- Validation logic rải rác trong service layer → khó maintain, dễ bỏ sót.
- Response format không nhất quán giữa các endpoints → frontend phải handle nhiều shape khác nhau.

**Phạm vi áp dụng:** Tất cả DTOs (input/output), ValidationPipe config, serialization strategy trong NestJS applications.

**Tại sao quan trọng:**

- Fail-fast: phát hiện lỗi input ngay tại controller layer, trả `400 Bad Request` rõ ràng.
- Bảo mật: `@Exclude()` và Response DTO ngăn lộ field nhạy cảm.
- DRY: `PartialType`, `PickType`, `OmitType` tránh duplicate DTO definitions.
- Type safety: DTO + `class-validator` + `class-transformer` đảm bảo data flow type-safe từ request đến response.

---

## 2. Quy tắc & Giải thích

### 2.1. Global ValidationPipe với whitelist + transform

**✅ NÊN:** Setup `ValidationPipe` global trong `main.ts` với config đầy đủ.

```ts
// main.ts
import { ValidationPipe } from '@nestjs/common';
import { validationExceptionFactory } from './common/validation/validation-exception.factory';

async function bootstrap() {
  const app = await NestFactory.create(AppModule);

  app.useGlobalPipes(
    new ValidationPipe({
      whitelist: true,              // Loại bỏ field không có decorator
      forbidNonWhitelisted: true,   // Reject nếu có field thừa
      transform: true,              // Auto-transform string → number, etc.
      transformOptions: {
        enableImplicitConversion: true, // Turns 'false' into true for booleans — see section 2.10
      },
      exceptionFactory: validationExceptionFactory, // Error body with details, see section 2.6
    }),
  );

  await app.listen(3000);
}
```

*Tại sao:*

- `whitelist: true` — loại bỏ field không khai báo trong DTO, ngăn mass assignment attack (client gửi `isAdmin: true`).
- `forbidNonWhitelisted: true` — reject request nếu có field lạ, giúp frontend phát hiện sai payload sớm.
- `transform: true` — tự động convert query/path params từ string sang đúng type (number). Boolean trong query cần `@Transform` riêng, xem mục 2.10.

**❌ KHÔNG NÊN:** Không bật validation global, mỗi endpoint tự validate thủ công.

> **Tham khảo:** [NestJS Validation](https://docs.nestjs.com/techniques/validation)

---

### 2.2. DTO Input với class-validator decorators

**✅ NÊN:** Mỗi DTO field phải có ít nhất 1 validation decorator.

```ts
import {
  IsString, IsNumber, IsOptional, IsNotEmpty,
  IsEmail, IsEnum, Min, Max, Length, Matches,
} from 'class-validator';
import { Type } from 'class-transformer';

export class CreateProductDto {
  @IsString()
  @IsNotEmpty()
  @Length(3, 100)
  name: string;

  @IsString()
  @IsOptional()
  description?: string;

  @IsNumber()
  @Min(0)
  price: number;

  @IsNumber()
  @Min(0)
  @Type(() => Number)  // Transform string từ query/param thành number
  stock: number;

  @IsString()
  @Matches(/^[A-Z0-9-]+$/)
  sku: string;

  @IsEnum(ProductStatus)
  status: ProductStatus;
}
```

**❌ KHÔNG NÊN:** DTO field không có decorator — `whitelist` sẽ strip field đó.

```ts
// ❌ Bad — field không có decorator sẽ bị whitelist loại bỏ
export class CreateProductDto {
  name: string;   // Bị strip!
  price: number;  // Bị strip!
}

// ❌ Bad — dùng any, mất type-safety và validation
async create(@Body() body: any) { ... }
```

*Tại sao:* `class-validator` decorators vừa validate vừa là signal cho `whitelist` biết field nào hợp lệ. Thiếu decorator = field bị loại bỏ hoặc không validate.

> **Tham khảo:** [class-validator GitHub](https://github.com/typestack/class-validator)

---

### 2.3. Nested Object Validation

**✅ NÊN:** Dùng `@ValidateNested()` + `@Type()` cho nested objects.

```ts
import { ValidateNested } from 'class-validator';
import { Type } from 'class-transformer';

class AddressDto {
  @IsString()
  @IsNotEmpty()
  street: string;

  @IsString()
  @IsNotEmpty()
  city: string;

  @IsString()
  @IsOptional()
  zipCode?: string;
}

export class CreateCustomerDto {
  @IsString()
  @IsNotEmpty()
  name: string;

  @IsEmail()
  email: string;

  @ValidateNested()         // Validate nested object
  @Type(() => AddressDto)   // Transform plain object → AddressDto instance
  address: AddressDto;
}
```

**❌ KHÔNG NÊN:** Nested object không có `@ValidateNested()` — sẽ không validate.

```ts
// ❌ Bad — address không được validate
export class CreateCustomerDto {
  @IsString() name: string;
  address: AddressDto;  // Thiếu @ValidateNested + @Type → không validate!
}
```

*Tại sao:* `class-validator` chỉ validate top-level fields mặc định. `@ValidateNested()` kích hoạt recursive validation, `@Type()` đảm bảo plain object được convert thành class instance trước khi validate.

---

### 2.4. Custom Validator cho domain-specific rules

**✅ NÊN:** Tạo custom validator khi logic validate phức tạp hoặc domain-specific.

```ts
import {
  registerDecorator, ValidationOptions, ValidationArguments,
} from 'class-validator';

export function IsVietnamesePhone(validationOptions?: ValidationOptions) {
  return function (object: Object, propertyName: string) {
    registerDecorator({
      name: 'isVietnamesePhone',
      target: object.constructor,
      propertyName,
      options: validationOptions,
      validator: {
        validate(value: any, args: ValidationArguments) {
          return typeof value === 'string' && /^(0|\+84)[0-9]{9}$/.test(value);
        },
        defaultMessage(args: ValidationArguments) {
          return '$property must be a Vietnamese phone number: 0 or +84 followed by 9 digits';
        },
      },
    });
  };
}

// Sử dụng
export class CreateCustomerDto {
  @IsVietnamesePhone()
  phone: string;
}
```

*Tại sao:* Custom validator tập trung logic domain vào 1 nơi, tái sử dụng được, và error message nhất quán.

---

### 2.5. UpdateDto dùng PartialType — DRY

**✅ NÊN:** Dùng `PartialType` từ `@nestjs/swagger` để tạo UpdateDto.

```ts
import { PartialType } from '@nestjs/swagger';

// Tất cả fields của CreateProductDto nhưng optional
export class UpdateProductDto extends PartialType(CreateProductDto) {}
```

**Các Mapped Types khác:**

```ts
import { PartialType, PickType, OmitType, IntersectionType } from '@nestjs/swagger';

// Chỉ lấy email + password
export class LoginDto extends PickType(CreateUserDto, ['email', 'password']) {}

// Loại bỏ password
export class UserProfileDto extends OmitType(CreateUserDto, ['password']) {}

// Kết hợp 2 DTOs
export class UpdateUserWithMetaDto extends IntersectionType(
  UpdateUserDto,
  MetadataDto,
) {}
```

**❌ KHÔNG NÊN:** Copy-paste fields giữa DTOs.

```ts
// ❌ Bad — duplicate fields, dễ bị out-of-sync
export class UpdateProductDto {
  @IsString() @IsOptional() name?: string;
  @IsNumber() @IsOptional() price?: number;
  @IsString() @IsOptional() sku?: string;
}

// ✅ Good — DRY, tự động sync khi CreateDto thay đổi
export class UpdateProductDto extends PartialType(CreateProductDto) {}
```

*Tại sao:* Mapped Types đảm bảo UpdateDto luôn sync với CreateDto. Khi thêm field mới vào CreateDto, UpdateDto tự động có — không cần nhớ update thủ công.

> **Tham khảo:** [NestJS Mapped Types](https://docs.nestjs.com/openapi/mapped-types)

---

### 2.6. Validation Messages rõ ràng

**✅ NÊN:** `message` viết tiếng Anh, cho log và developer gọi API. Chỉ viết message riêng khi message mặc định không nói rõ rule. Rule nào client cần text riêng cho user thì gắn `context: { code }`.

```ts
export class CreateUserDto {
  @IsEmail() // → "email must be an email"
  email: string;

  @IsString()
  @MinLength(8, { context: { code: 'PASSWORD_TOO_SHORT' } })
  @Matches(/(?=.*[A-Z])(?=.*[0-9])/, {
    message: 'password must contain at least 1 uppercase letter and 1 digit',
    context: { code: 'PASSWORD_TOO_WEAK' },
  })
  password: string;
}
```

**`exceptionFactory` cho ValidationPipe:** lỗi validate trả `details` dạng `[{ field, message, code? }]`, đúng format lỗi ở [NestJS Coding Standard 3.1 — REST API Design](Ref_Dev_s3.1_nestjs-rest-api-design_v1.0.md) mục 2.4. Field của DTO lồng nhau có path dạng `items.0.quantity`. `code` lấy từ `context.code` của rule, như rule `MinLength` ở trên.

```ts
// common/validation/validation-exception.factory.ts
import { BadRequestException } from '@nestjs/common';
import { ValidationError } from 'class-validator';
import { ErrorDetail } from '../filters/global-exception.filter';

// One entry per failed rule. Nested DTOs get a dotted path such as items.0.quantity.
function toDetails(errors: ValidationError[], parent = ''): ErrorDetail[] {
  return errors.flatMap((error) => {
    const field = parent ? `${parent}.${error.property}` : error.property;
    const own = Object.entries(error.constraints ?? {}).map(([rule, message]) => {
      // A DTO can name the rule with { context: { code } }, see the example above
      const code: unknown = error.contexts?.[rule]?.code;
      return { field, message, ...(typeof code === 'string' && { code }) };
    });
    return [...own, ...toDetails(error.children ?? [], field)];
  });
}

export function validationExceptionFactory(errors: ValidationError[]) {
  const details = toDetails(errors);
  return new BadRequestException({
    code: 'VALIDATION_ERROR',
    message: details.map((d) => d.message).join('; '),
    details,
  });
}
```

```ts
// main.ts
new ValidationPipe({
  // ...
  exceptionFactory: validationExceptionFactory,
})
```

**❌ KHÔNG NÊN:** Viết text cho end user vào `message`, hoặc giữ message mặc định không nói rõ rule.

```ts
// ❌ Bad — user-facing text belongs to the client, keyed by code
@MinLength(8, { message: 'Password phải có ít nhất 8 ký tự' })

// ❌ Bad — the default message prints the regex, not the rule
@Matches(/(?=.*[A-Z])(?=.*[0-9])/) // → "password must match /(?=.*[A-Z])(?=.*[0-9])/ regular expression"
```

*Tại sao:* Client map `code` sang text theo ngôn ngữ của user, nên thêm ngôn ngữ hay sửa câu chữ không cần sửa backend. `message` tiếng Anh giữ log thống nhất và đọc được khi debug.

---

### 2.7. Serialization — Tách Response DTO, không trả raw entity

**✅ NÊN:** Tạo Response DTO riêng với `@Expose()` / `@Exclude()`.

```ts
import { Exclude, Expose, Transform } from 'class-transformer';

export class UserResponseDto {
  // IDs go out as strings: integers above 2^53 lose precision in JavaScript
  @Expose()
  @Transform(({ value }) => String(value), { toClassOnly: true })
  id: string;

  @Expose()
  email: string;

  @Expose()
  displayName: string;

  @Exclude()                // Không trả về client
  password: string;

  @Exclude()                // Không trả về client
  refreshToken: string;

  @Expose()
  @Transform(({ value }) => value?.toISOString(), { toClassOnly: true })
  createdAt: Date;
}
```

**Sử dụng trong controller:**

```ts
import { plainToInstance } from 'class-transformer';

@Get(':id')
async findOne(@Param('id', ParseIntPipe) id: number): Promise<UserResponseDto> {
  const user = await this.usersService.findOne(id);
  return plainToInstance(UserResponseDto, user, {
    excludeExtraneousValues: true,  // Chỉ expose fields có @Expose()
  });
}
```

Doc này chỉ dùng một cách serialize: controller gọi `plainToInstance` như trên. Không đăng ký thêm global `ClassSerializerInterceptor` hay `TransformInterceptor` (xem mục 2.11).

**❌ KHÔNG NÊN:** Trả raw entity trực tiếp.

```ts
// ❌ Bad — entity có thể chứa password, tokens, internal data
@Get(':id')
async findOne(@Param('id') id: number) {
  return this.usersRepository.findOne({ where: { id } });
}
```

*Tại sao:* Entity thường chứa fields không nên expose (password hash, refresh tokens, internal metadata, cost prices). Response DTO là tầng kiểm soát cuối cùng trước khi data đến client — đảm bảo chỉ trả những gì cần thiết.

> **Tham khảo:** [NestJS Serialization](https://docs.nestjs.com/techniques/serialization) · [class-transformer GitHub](https://github.com/typestack/class-transformer)

---

### 2.8. Transform custom cho response fields

**✅ NÊN:** Dùng `@Transform` khi cần convert dữ liệu trước khi trả response.

```ts
export class ProductResponseDto {
  @Expose()
  @Transform(({ value }) => String(value), { toClassOnly: true })
  id: string;

  @Expose()
  name: string;

  // toClassOnly: runs once, in plainToInstance — not again if the instance is serialized later
  @Expose()
  @Transform(({ value }) => value / 100, { toClassOnly: true })   // Cents → VND
  price: number;

  @Expose()
  @Transform(({ value }) => value?.toISOString(), { toClassOnly: true })
  createdAt: Date;

  @Expose()
  @Transform(({ obj }) => `${obj.firstName} ${obj.lastName}`, { toClassOnly: true })
  fullName: string;                         // Computed field
}
```

*Tại sao:* Transform giúp convert data format (cents → currency, date → ISO string) tại serialization layer, không cần logic convert rải rác trong service.

---

### 2.9. Validate chỉ input ở controller, business logic ở service

**✅ NÊN:** Phân chia rõ ràng:

- **Controller layer (DTO + Pipe):** Validate format, type, required fields.
- **Service layer:** Validate business logic (product tồn tại, stock đủ, user có quyền).

```ts
// Controller — validate format
@Post()
async create(@Body() dto: CreateOrderDto) {
  // DTO đã validate: items not empty, quantity > 0, etc.
  return this.ordersService.create(dto);
}

// Service — validate business rules
async create(dto: CreateOrderDto): Promise<Order> {
  // Business validation: stock đủ không?
  for (const item of dto.items) {
    const product = await this.productsRepo.findById(item.productId);
    if (!product) {
      throw new NotFoundException(`Product ${item.productId} not found`);
    }
    if (product.stock < item.quantity) {
      throw new BadRequestException(
        `Insufficient stock for ${product.name}: available ${product.stock}, requested ${item.quantity}`,
      );
    }
  }
  // ... create order
}
```

**❌ KHÔNG NÊN:** Validate format trong service hoặc business logic trong controller.

*Tại sao:* Tách validation theo layer giúp: (1) dễ test — mock service khi test controller, (2) dễ reuse — format validation tự động qua Pipe, (3) dễ maintain — biết chính xác validate gì ở đâu.

---

### 2.10. Filter DTOs cho Query Parameters

**✅ NÊN:** Tạo Filter DTO riêng cho query parameters thay vì parse thủ công trong controller.

```ts
import { IsOptional, IsEnum, IsString, IsInt, IsBoolean, Min, Max, MinLength } from 'class-validator';
import { Transform, Type } from 'class-transformer';

export class GetTasksFilterDto {
  @IsOptional()
  @IsEnum(TaskStatus)
  status?: TaskStatus;

  @IsOptional()
  @IsString()
  @MinLength(3)
  search?: string;

  // Read the raw string: implicit conversion has already turned 'false' into true
  @IsOptional()
  @Transform(({ obj, key }) => {
    const raw = obj[key];
    if (raw === 'true' || raw === true) return true;
    if (raw === 'false' || raw === false) return false;
    return raw; // anything else fails @IsBoolean
  })
  @IsBoolean()
  active?: boolean;

  @IsOptional()
  @Type(() => Number)
  @IsInt() @Min(1)
  page?: number = 1;

  @IsOptional()
  @Type(() => Number)
  @IsInt() @Min(1) @Max(100)
  limit?: number = 20;
}
```

**Boolean trong query:** query string luôn là string, và `enableImplicitConversion` gọi `Boolean('false')` nên `?active=false` thành `true`. Field boolean trong query DTO phải có `@Transform` đọc giá trị gốc `obj[key]` như `active` ở trên. Đọc `value` thì sai, vì `value` đã bị convert trước khi `@Transform` chạy.

**❌ KHÔNG NÊN:** Parse thủ công `parseInt()`, `Number()`, `Boolean()` trong controller.

```ts
// ❌ Bad — manual parsing, không validate, không type-safe
@Get()
async findAll(@Query() query: any) {
  const page = parseInt(query.page) || 1;
  const limit = parseInt(query.limit) || 10;
  const active = query.active === 'true';
  return this.service.findAll({ page, limit, active });
}

// ✅ Good — Filter DTO, auto-transform, validated
@Get()
async findAll(@Query() query: GetTasksFilterDto) {
  return this.service.findAll(query);
}
```

*Tại sao:* Filter DTO tập trung validation + transformation vào 1 nơi, auto-transform string → number qua `@Type()`, và cung cấp type-safety cho cả controller lẫn service.

---

### 2.11. Global TransformInterceptor cho Serialization

**❌ KHÔNG NÊN:** Dùng `TransformInterceptor` (hoặc `ClassSerializerInterceptor`) global thay cho `plainToInstance` ở controller.

```ts
// ❌ Bad — does not filter plain objects (Prisma rows, raw query results)
import { Injectable, NestInterceptor, ExecutionContext, CallHandler } from '@nestjs/common';
import { map, Observable } from 'rxjs';
import { instanceToPlain } from 'class-transformer';

@Injectable()
export class TransformInterceptor implements NestInterceptor {
  intercept(context: ExecutionContext, next: CallHandler): Observable<any> {
    return next.handle().pipe(
      map((data) => {
        // Handle paginated responses
        if (data?.data !== undefined && data?.meta !== undefined) {
          return { ...data, data: instanceToPlain(data.data) };
        }
        // Handle arrays
        if (Array.isArray(data)) {
          return data.map((item) => instanceToPlain(item));
        }
        // Handle single objects
        return instanceToPlain(data);
      }),
    );
  }
}
```

*Tại sao:* `instanceToPlain()` chỉ áp `@Exclude()`/`@Expose()` cho class instance. Service trả plain object (Prisma row, raw query) thì field nhạy cảm vẫn ra response. Đặt interceptor sau `plainToInstance` thì serialize hai lần; `ClassSerializerInterceptor` với `strategy: 'excludeAll'` còn biến plain object như `{ data, meta }` thành `{}`.

> **Tham khảo:** [class-transformer instanceToPlain](https://github.com/typestack/class-transformer)

---

## 3. Ví dụ minh họa thực tế

### 3.1. Walkthrough: Product API — Validation & Serialization đầy đủ

**Bước 1 — Setup Global ValidationPipe trong `main.ts`**

```ts
import { ValidationPipe } from '@nestjs/common';
import { validationExceptionFactory } from './common/validation/validation-exception.factory';

async function bootstrap() {
  const app = await NestFactory.create(AppModule);

  // Validation
  app.useGlobalPipes(
    new ValidationPipe({
      whitelist: true,
      forbidNonWhitelisted: true,
      transform: true,
      transformOptions: { enableImplicitConversion: true },
      exceptionFactory: validationExceptionFactory, // Error body with details, see section 2.6
    }),
  );

  // Serialization: no global interceptor — controllers call plainToInstance (Step 4)

  await app.listen(3000);
}
```

**Bước 2 — Input DTOs**

```ts
// dto/create-product.dto.ts
export class CreateProductDto {
  @ApiProperty({ example: 'Áo thun nam', description: 'Tên sản phẩm' })
  @IsString()
  @IsNotEmpty()
  @Length(3, 100)
  name: string;

  @ApiPropertyOptional({ example: 'Áo thun cotton 100%' })
  @IsString()
  @IsOptional()
  description?: string;

  @ApiProperty({ example: 199000, minimum: 0 })
  @IsNumber()
  @Min(0)
  price: number;

  @ApiProperty({ example: 50, minimum: 0 })
  @IsNumber()
  @Min(0)
  stock: number;

  @ApiProperty({ example: 'SKU-001' })
  @IsString()
  @Matches(/^[A-Z0-9-]+$/)
  sku: string;

  @ApiProperty({ enum: ProductStatus, example: ProductStatus.ACTIVE })
  @IsEnum(ProductStatus)
  status: ProductStatus;
}

// dto/update-product.dto.ts — DRY
export class UpdateProductDto extends PartialType(CreateProductDto) {}

// dto/list-product.dto.ts — Query params
export class ListProductDto {
  @ApiPropertyOptional({ enum: ProductStatus })
  @IsOptional()
  @IsEnum(ProductStatus)
  status?: ProductStatus;

  @ApiPropertyOptional({ default: 1, minimum: 1 })
  @IsOptional()
  @Type(() => Number)
  @IsNumber()
  @Min(1)
  page?: number = 1;

  @ApiPropertyOptional({ default: 20, minimum: 1, maximum: 100 })
  @IsOptional()
  @Type(() => Number)
  @IsNumber()
  @Min(1)
  @Max(100)
  limit?: number = 20;
}
```

**Bước 3 — Response DTO**

```ts
// dto/product-response.dto.ts
export class ProductResponseDto {
  @ApiProperty({ example: '1' })
  @Expose()
  @Transform(({ value }) => String(value), { toClassOnly: true })
  id: string;

  @ApiProperty({ example: 'Áo thun nam' })
  @Expose()
  name: string;

  @ApiProperty({ example: 199000 })
  @Expose()
  price: number;

  @ApiProperty({ example: 'SKU-001' })
  @Expose()
  sku: string;

  @ApiProperty({ example: 50 })
  @Expose()
  stock: number;

  @ApiProperty({ enum: ProductStatus })
  @Expose()
  status: ProductStatus;

  @ApiProperty()
  @Expose()
  @Transform(({ value }) => value?.toISOString(), { toClassOnly: true })
  createdAt: Date;

  // Không expose: costPrice, supplierInfo, internalNotes, deletedAt
}
```

**Bước 4 — Controller sử dụng DTOs**

```ts
@ApiTags('products')
@Controller('products')
export class ProductsController {
  constructor(private readonly productsService: ProductsService) {}

  @Post()
  @ApiOperation({ summary: 'Tạo sản phẩm mới' })
  @ApiCreatedResponse({ type: ProductResponseDto })
  async create(@Body() dto: CreateProductDto): Promise<ProductResponseDto> {
    const product = await this.productsService.create(dto);
    return plainToInstance(ProductResponseDto, product, {
      excludeExtraneousValues: true,
    });
  }

  @Get(':id')
  @ApiOperation({ summary: 'Chi tiết sản phẩm' })
  @ApiOkResponse({ type: ProductResponseDto })
  async findOne(@Param('id', ParseIntPipe) id: number): Promise<ProductResponseDto> {
    const product = await this.productsService.findOne(id);
    return plainToInstance(ProductResponseDto, product, {
      excludeExtraneousValues: true,
    });
  }

  @Patch(':id')
  @ApiOperation({ summary: 'Cập nhật sản phẩm' })
  @ApiOkResponse({ type: ProductResponseDto })
  async update(
    @Param('id', ParseIntPipe) id: number,
    @Body() dto: UpdateProductDto,
  ): Promise<ProductResponseDto> {
    const product = await this.productsService.update(id, dto);
    return plainToInstance(ProductResponseDto, product, {
      excludeExtraneousValues: true,
    });
  }
}
```

---

### 3.2. Before/After: Từ validation thiếu chuẩn đến đầy đủ

**Before** — Không validate, trả raw entity:

```ts
// ❌ Không validate input
@Post()
async create(@Body() body: any) {
  return this.productRepository.save(body);
  // Client gửi { isAdmin: true, price: -100 } → lưu thẳng vào DB!
}

// ❌ Trả raw entity
@Get(':id')
async findOne(@Param('id') id: string) {
  return this.productRepository.findOne({ where: { id } });
  // Response chứa: costPrice, supplierInfo, deletedAt...
}
```

**After** — Validate đầy đủ, serialize an toàn:

```ts
// ✅ Validate input qua DTO
@Post()
async create(@Body() dto: CreateProductDto): Promise<ProductResponseDto> {
  // dto đã validate: name required, price >= 0, sku format đúng
  // whitelist đã strip field lạ (isAdmin, etc.)
  const product = await this.productsService.create(dto);
  return plainToInstance(ProductResponseDto, product, {
    excludeExtraneousValues: true,
  });
}

// ✅ Response DTO kiểm soát output
@Get(':id')
async findOne(@Param('id', ParseIntPipe) id: number): Promise<ProductResponseDto> {
  const product = await this.productsService.findOne(id);
  return plainToInstance(ProductResponseDto, product, {
    excludeExtraneousValues: true,
  });
  // Response chỉ chứa: id, name, price, sku, stock, status, createdAt
}
```

---

## 4. Tooling & Config

### 4.1. Checklist setup Validation & Serialization

- [ ] Cài đặt packages: `pnpm add class-validator class-transformer`
- [ ] Setup global `ValidationPipe` trong `main.ts` với `whitelist`, `forbidNonWhitelisted`, `transform`
- [ ] Serialize response bằng `plainToInstance(ResponseDto, data, { excludeExtraneousValues: true })` ở controller, không thêm global serializer interceptor
- [ ] Tạo Input DTOs với `class-validator` decorators cho mọi endpoint
- [ ] Tạo Response DTOs với `@Expose()` / `@Exclude()` cho mọi entity
- [ ] Dùng `PartialType(CreateDto)` cho UpdateDto
- [ ] Thêm `@ApiProperty` cho mọi DTO field (Swagger)
- [ ] Validation `message` viết tiếng Anh; rule cần text riêng ở client có `context: { code }`
- [ ] Test validation: gửi request thiếu field, field sai type, field thừa

### 4.2. Testing validation trong unit tests

```ts
import { validate } from 'class-validator';
import { plainToInstance } from 'class-transformer';

describe('CreateProductDto', () => {
  it('should fail if name is too short', async () => {
    const dto = plainToInstance(CreateProductDto, {
      name: 'AB',       // Quá ngắn (min 3)
      price: 100,
      stock: 10,
      sku: 'SKU-001',
      status: 'active',
    });

    const errors = await validate(dto);
    expect(errors.length).toBeGreaterThan(0);
    expect(errors[0].property).toBe('name');
  });

  it('should fail if price is negative', async () => {
    const dto = plainToInstance(CreateProductDto, {
      name: 'Valid name',
      price: -100,      // Âm
      stock: 10,
      sku: 'SKU-001',
      status: 'active',
    });

    const errors = await validate(dto);
    const priceError = errors.find((e) => e.property === 'price');
    expect(priceError).toBeDefined();
  });

  it('should pass with valid data', async () => {
    const dto = plainToInstance(CreateProductDto, {
      name: 'Áo thun nam',
      price: 199000,
      stock: 50,
      sku: 'SKU-001',
      status: 'active',
    });

    const errors = await validate(dto);
    expect(errors.length).toBe(0);
  });
});
```

### 4.3. Swagger CLI Plugin — giảm boilerplate

```json
// nest-cli.json
{
  "compilerOptions": {
    "plugins": [
      {
        "name": "@nestjs/swagger",
        "options": {
          "classValidatorShim": true,
          "introspectComments": true
        }
      }
    ]
  }
}
```

*Plugin tự động infer `@ApiProperty` từ TypeScript types và `class-validator` decorators. Vẫn nên explicit `@ApiProperty` cho fields quan trọng cần `example` và `description`.*

---

## References

- [NestJS Validation](https://docs.nestjs.com/techniques/validation) — ValidationPipe, auto-validation
- [NestJS Serialization](https://docs.nestjs.com/techniques/serialization) — ClassSerializerInterceptor, Expose/Exclude
- [NestJS Mapped Types](https://docs.nestjs.com/openapi/mapped-types) — PartialType, PickType, OmitType
- [class-validator GitHub](https://github.com/typestack/class-validator) — Decorators reference
- [class-transformer GitHub](https://github.com/typestack/class-transformer) — Transform, Expose, Exclude
- [NestJS OpenAPI (Swagger)](https://docs.nestjs.com/openapi/introduction) — @ApiProperty, Swagger CLI plugin

## Changelog

| Date | Version | Change | By |
| :---- | :---- | :---- | :---- |
| 2026-11-18 | v1.0 | Chuyển từ Notion "NestJS Document" (page `33d71a38d3b281d1831bf9f7f2bb3718`, sửa 2026-04-09). Review và sửa nội dung, code trước khi publish. Owner duyệt trong chat ngày 2026-11-18. | Bắc PV |
