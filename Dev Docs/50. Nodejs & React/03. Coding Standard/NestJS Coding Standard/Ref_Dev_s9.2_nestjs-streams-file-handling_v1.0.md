# NestJS Coding Standard 9.2 — Streams & File Handling

| Field | Value |
| :---- | :---- |
| Owner | Bắc PV — NodeJS BE Dev Lead |
| Audience | Dev (NodeJS BE) |
| Last reviewed | 2026-11-12 |
| Review cadence | Quarterly |
| Version | v1.0 |
| Linked from | Ref_Dev_nestjs-coding-standard_v1.0 |
| Status | Live |

Doc này là mục 9.2 của [NestJS Coding Standard](Ref_Dev_nestjs-coding-standard_v1.0.md), nhóm Performance & Operations. Doc nêu quy tắc về Streams & File Handling trong dự án NestJS, kèm lý do, ví dụ và config. Dev NodeJS BE đọc doc này khi viết code, review code và onboarding.

---

## 1 Tóm tắt & Phạm vi

Chủ đề này bao quát **Node.js Streams**, **file upload** (`@nestjs/platform-express` + Multer), và **streaming response** trong NestJS. Đây là nhóm kỹ thuật quan trọng khi ứng dụng cần:

- Upload/download file lớn (ảnh, video, CSV, Excel, backup) mà không chiếm hết RAM
- Xử lý data pipeline theo từng chunk (ETL, log processing, report generation)
- Trả response dạng stream cho client (file download, SSE, chunked JSON)

**Tại sao quan trọng?**

- Không dùng stream → đọc toàn bộ file vào memory → OOM crash khi file lớn
- Upload không validate/limit → server bị abuse (DDoS qua file upload)
- Không cleanup temp files → disk full theo thời gian

---

## 2 Quy tắc & Giải thích

### 1. Node.js Streams — Nền tảng

Node.js cung cấp 4 loại stream chính:

| Loại Stream | Mô tả | Ví dụ thực tế |
| --- | --- | --- |
| Readable | Nguồn dữ liệu — đọc từng chunk | `fs.createReadStream()`, HTTP request body |
| Writable | Đích dữ liệu — ghi từng chunk | `fs.createWriteStream()`, HTTP response |
| Duplex | Vừa đọc vừa ghi (2 kênh độc lập) | TCP socket, WebSocket |
| Transform | Đọc → biến đổi → ghi (pipeline) | `zlib.createGzip()`, CSV parser |

**Nên làm:**

- Ưu tiên `pipeline()` (từ `stream/promises`) thay vì `.pipe()` — tự động handle error propagation và cleanup
- Dùng `highWaterMark` để control buffer size theo use case (default 16KB cho stream, 64KB cho fs)
- Luôn handle event `'error'` trên mọi stream — stream không có error handler sẽ crash process

**Không nên làm:**

- Đọc toàn bộ file bằng `fs.readFileSync()` hoặc `fs.readFile()` cho file > 10MB — dùng `createReadStream()`
- Dùng `.pipe()` mà không handle error — nếu stream giữa pipeline lỗi, các stream khác không tự cleanup
- Quên `destroy()` stream khi request bị abort — gây memory leak

**Tại sao `pipeline()` tốt hơn `.pipe()`?**

`.pipe()` chỉ forward data, **không** propagate errors giữa các stream. Nếu stream ở giữa lỗi, stream trước và sau vẫn mở → memory leak. `pipeline()` tự động destroy tất cả stream khi bất kỳ stream nào lỗi hoặc kết thúc.

```ts
import { pipeline } from 'stream/promises';
import { createReadStream, createWriteStream } from 'fs';
import { createGzip } from 'zlib';

// ✅ Good — pipeline tự cleanup khi error
async function compressFile(input: string, output: string): Promise<void> {
  await pipeline(
    createReadStream(input),
    createGzip(),
    createWriteStream(output),
  );
}
```

```ts
import { createReadStream, createWriteStream } from 'fs';

// ❌ Bad — .pipe() không propagate error
const src = createReadStream('large.csv');
const dest = createWriteStream('output.csv');
src.pipe(dest); // Nếu dest lỗi (disk full), src vẫn đọc → memory leak
```

> 📖 Tham khảo: [Node.js Stream API](https://nodejs.org/docs/latest/api/stream.html) · [stream.pipeline()](https://nodejs.org/docs/latest/api/stream.html#streampipelinesource-transforms-destination-callback)

---

### 2. File Upload với Multer

NestJS dùng `multer` (qua `@nestjs/platform-express`) để handle multipart/form-data upload.

**Nên làm:**

- Luôn giới hạn `fileSize` trong `MulterOptions` — tránh upload file quá lớn crash server
- Validate MIME type bằng `fileFilter` — không tin `mimetype` từ client, kiểm tra magic bytes nếu cần bảo mật cao
- Dùng `diskStorage` cho file lớn (> 10MB) — tránh giữ toàn bộ buffer trong RAM
- Dùng `memoryStorage` chỉ cho file nhỏ cần xử lý ngay (resize ảnh, parse CSV nhỏ)
- Cleanup temp files sau khi xử lý xong — dùng `finally` block hoặc cleanup middleware
- Đặt `dest` hoặc `storage` vào thư mục temp riêng (ví dụ `uploads/tmp/`) — dễ quản lý và cleanup

**Không nên làm:**

- Upload không giới hạn size — 1 request upload 10GB có thể crash server
- Trust `file.mimetype` từ client để quyết định logic bảo mật — client có thể giả mạo
- Lưu file upload trực tiếp vào thư mục public/static — nguy cơ path traversal, executable upload
- Dùng `memoryStorage` cho file lớn — mỗi request giữ toàn bộ file trong RAM
- Dùng `FileTypeValidator` với `diskStorage` — validator đọc magic bytes trong `file.buffer`, `diskStorage` không có buffer nên mọi upload bị 400. Validate bằng `FileTypeValidator` thì dùng `memoryStorage` (file nhỏ, như ví dụ dưới)

**Cấu trúc code upload chuẩn:**

```ts
import { BadRequestException, Controller, Post, UploadedFile, UseInterceptors, ParseFilePipe, MaxFileSizeValidator, FileTypeValidator } from '@nestjs/common';
import { FileInterceptor } from '@nestjs/platform-express';
import { memoryStorage } from 'multer';
import { extname } from 'path';
import { FilesService } from './files.service';

const MAX_FILE_SIZE = 10 * 1024 * 1024; // 10MB

@Controller('files')
export class FilesController {
  constructor(private readonly filesService: FilesService) {}

  @Post('upload')
  @UseInterceptors(FileInterceptor('file', {
    // FileTypeValidator checks magic bytes in file.buffer; diskStorage leaves it undefined
    storage: memoryStorage(),
    limits: { fileSize: MAX_FILE_SIZE },
    fileFilter: (_req, file, cb) => {
      const allowed = /\.(jpg|jpeg|png|webp|pdf)$/i;
      if (!allowed.test(extname(file.originalname))) {
        // HttpException keeps its 4xx status; a plain Error here becomes a 500
        return cb(new BadRequestException('File type not allowed'), false);
      }
      cb(null, true);
    },
  }))
  async uploadFile(
    @UploadedFile(new ParseFilePipe({
      validators: [
        new MaxFileSizeValidator({ maxSize: MAX_FILE_SIZE }),
        new FileTypeValidator({ fileType: /(jpg|jpeg|png|webp|pdf)/ }),
      ],
    }))
    file: Express.Multer.File,
  ) {
    return this.filesService.processUpload(file);
  }
}
```

**Multiple file upload:**

```ts
import { FilesInterceptor, FileFieldsInterceptor } from '@nestjs/platform-express';

// Nhiều file cùng field name
@Post('gallery')
@UseInterceptors(FilesInterceptor('photos', 10, multerOptions))
async uploadGallery(@UploadedFiles() files: Express.Multer.File[]) { ... }

// Nhiều field khác nhau
@Post('profile')
@UseInterceptors(FileFieldsInterceptor([
  { name: 'avatar', maxCount: 1 },
  { name: 'documents', maxCount: 5 },
], multerOptions))
async uploadProfile(
  @UploadedFiles() files: {
    avatar?: Express.Multer.File[];
    documents?: Express.Multer.File[];
  },
) { ... }
```

> 📖 Tham khảo: [NestJS File Upload](https://docs.nestjs.com/techniques/file-upload) · [Multer docs](https://github.com/expressjs/multer)

---

### 3. Streaming Response

Khi trả file hoặc data lớn cho client, dùng stream thay vì load toàn bộ vào memory.

**Nên làm:**

- Dùng `StreamableFile` (từ `@nestjs/common`) — NestJS wrapper chuẩn, tự set headers và handle pipe
- Set `Content-Type`, `Content-Disposition`, và `Content-Length` (nếu biết) trong response headers
- Dùng `@Header()` decorator hoặc `@Res({ passthrough: true })` để set headers mà vẫn giữ interceptors
- Compress response với `compression` middleware cho text-based streams (JSON, CSV, logs)

**Không nên làm:**

- Dùng `@Res()` trực tiếp (không `passthrough`) — mất interceptors, exception filters, và serialization
- Load toàn bộ file vào Buffer rồi `res.send(buffer)` — tốn RAM tỷ lệ với file size
- Quên set `Content-Disposition: attachment` cho file download — browser sẽ cố render thay vì tải
- Ghép tên file lấy từ request (`@Param`, query) vào đường dẫn — path traversal: `..%2F` đọc được file ngoài thư mục upload. Tra file theo ID trong DB; nếu buộc phải nhận tên file thì `path.resolve()` rồi chặn mọi path không nằm trong thư mục upload

**Download file dạng stream:**

```ts
import { Controller, Get, Param, ParseUUIDPipe, Res, StreamableFile } from '@nestjs/common';
import { Response } from 'express';
import { createReadStream } from 'fs';
import { join } from 'path';
import { FilesService } from './files.service';

@Controller('files')
export class FilesController {
  constructor(private readonly filesService: FilesService) {}

  @Get(':id/download')
  async download(
    @Param('id', ParseUUIDPipe) id: string,
    @Res({ passthrough: true }) res: Response,
  ): Promise<StreamableFile> {
    // Look the file up by ID; never build a path from client input ("..%2F" = path traversal)
    const meta = await this.filesService.findById(id); // throws NotFoundException if missing
    const file = createReadStream(join(process.cwd(), 'uploads', meta.storedName)); // name generated at upload

    res.attachment(meta.originalName); // Content-Disposition: attachment, filename escaped
    res.set('Content-Type', 'application/octet-stream');

    return new StreamableFile(file);
  }
}
```

**Stream CSV export (generate on-the-fly):**

```ts
import { Transform } from 'stream';
import { pipeline } from 'stream/promises';

// Quote every field and double inner quotes (RFC 4180): commas, quotes, newlines stay inside one cell
const csvField = (value: unknown): string => `"${String(value ?? '').replace(/"/g, '""')}"`;

@Get('export/orders')
async exportOrders(
  @Res({ passthrough: true }) res: Response,
): Promise<StreamableFile> {
  res.set({
    'Content-Type': 'text/csv; charset=utf-8',
    'Content-Disposition': 'attachment; filename="orders.csv"',
  });

  const csvTransform = new Transform({
    objectMode: true,
    transform(row, _encoding, callback) {
      const line = [row.id, row.customer, row.total].map(csvField).join(',') + '\n';
      callback(null, line);
    },
  });

  // Header row
  csvTransform.push('id,customer,total\n');

  // Stream từ DB cursor (ví dụ TypeORM QueryBuilder stream)
  const queryStream = await this.ordersRepo
    .createQueryBuilder('order')
    // stream() yields raw rows keyed "order_id", "order_customer"...: alias the columns the transform reads
    .select('order.id', 'id')
    .addSelect('order.customer', 'customer')
    .addSelect('order.total', 'total')
    .stream();

  // Not awaited: StreamableFile reads csvTransform. pipeline() destroys queryStream
  // (and frees the DB connection) if the query fails or the client disconnects.
  pipeline(queryStream, csvTransform).catch((err) =>
    this.logger.warn(`Order export aborted: ${err.message}`),
  );

  return new StreamableFile(csvTransform);
}
```

> 📖 Tham khảo: [NestJS Streaming Files](https://docs.nestjs.com/techniques/streaming-files) · [StreamableFile API](https://docs.nestjs.com/techniques/streaming-files#streamable-file-class)

---

### 4. Server-Sent Events (SSE)

SSE cho phép server push events tới client qua HTTP — đơn giản hơn WebSocket cho one-way streaming.

```ts
import { Controller, Sse, MessageEvent } from '@nestjs/common';
import { Observable, interval, map } from 'rxjs';

@Controller('events')
export class EventsController {
  @Sse('stream')
  stream(): Observable<MessageEvent> {
    return interval(1000).pipe(
      map((num) => ({
        data: { timestamp: new Date().toISOString(), count: num },
      })),
    );
  }
}
```

**Nên làm:**

- Return `Observable<MessageEvent>` từ `@Sse()` handler — NestJS tự set `Content-Type: text/event-stream`
- Dùng SSE cho: notifications, progress updates, live logs, dashboard metrics
- Implement reconnection logic ở client (EventSource tự reconnect, nhưng cần handle `lastEventId`)

**Không nên làm:**

- Dùng SSE cho bi-directional communication — dùng WebSocket thay thế
- Giữ connection SSE mở vô thời hạn không có heartbeat — proxy/load balancer có thể kill

---

### 5. Streaming với External Storage (S3, GCS)

Trong production, file thường lưu trên cloud storage thay vì local disk.

**Pattern: Upload stream trực tiếp lên S3 (không lưu temp file):**

```ts
import { S3Client, PutObjectCommand } from '@aws-sdk/client-s3';
import { Upload } from '@aws-sdk/lib-storage';

@Injectable()
export class StorageService {
  private readonly s3: S3Client;

  async uploadStream(
    key: string,
    stream: Readable,
    contentType: string,
  ): Promise<string> {
    const upload = new Upload({
      client: this.s3,
      params: {
        Bucket: this.configService.getOrThrow('S3_BUCKET'),
        Key: key,
        Body: stream,
        ContentType: contentType,
      },
      // Multipart upload cho file lớn
      partSize: 5 * 1024 * 1024, // 5MB per part
      queueSize: 4, // 4 concurrent uploads
    });

    await upload.done();
    return key;
  }
}
```

**Pattern: Download stream từ S3:**

```ts
import { GetObjectCommand } from '@aws-sdk/client-s3';
import { Readable } from 'stream';

async downloadStream(key: string): Promise<Readable> {
  const { Body } = await this.s3.send(
    new GetObjectCommand({
      Bucket: this.bucket,
      Key: key,
    }),
  );
  return Body as Readable;
}
```

---

### 6. Backpressure — Khái niệm quan trọng

Backpressure xảy ra khi producer (Readable) tạo data nhanh hơn consumer (Writable) xử lý. Node.js stream tự động handle backpressure qua `highWaterMark` — khi buffer đầy, Readable tạm dừng đọc cho đến khi Writable xử lý xong.

**Nên làm:**

- Dùng `pipeline()` — tự quản lý backpressure giữa các stream
- Kiểm tra giá trị return của `writable.write()` — nếu `false`, đợi event `'drain'` trước khi ghi tiếp
- Set `highWaterMark` phù hợp: nhỏ hơn cho memory-constrained, lớn hơn cho throughput

**Không nên làm:**

- Dùng vòng lặp `for await...of` trên Readable rồi `write()` liên tục không check backpressure
- Ignore return value của `writable.write()` — gây buffer bloat, OOM

```ts
// ✅ Good — respect backpressure
async function copyWithBackpressure(
  readable: Readable,
  writable: Writable,
): Promise<void> {
  for await (const chunk of readable) {
    const canContinue = writable.write(chunk);
    if (!canContinue) {
      await new Promise<void>((resolve) => writable.once('drain', resolve));
    }
  }
  writable.end();
}
```

---

## 3. Ví dụ minh họa thực tế

### 3.1. Walkthrough: Import CSV lớn vào database

**Yêu cầu:** Import file CSV 500MB chứa 2 triệu dòng orders vào PostgreSQL.

**Before (❌ sai — load toàn bộ vào memory):**

```ts
async importOrders(filePath: string): Promise<void> {
  // ❌ Đọc toàn bộ 500MB vào RAM
  const content = fs.readFileSync(filePath, 'utf-8');
  const rows = content.split('\n').map(parseCsvRow);

  // ❌ Insert 2M rows trong 1 transaction
  await this.ordersRepo.save(rows);
}
```

**After (✅ đúng — stream + batch insert):**

```ts
import { pipeline } from 'stream/promises';
import { createReadStream } from 'fs';
import { Transform } from 'stream';
import csvParser from 'csv-parser';

async importOrders(filePath: string): Promise<{ imported: number }> {
  let imported = 0;
  let batch: OrderEntity[] = [];
  const BATCH_SIZE = 1000;

  // Arrow function keeps `this` = service; inside the Transform methods below `this` is the stream
  const insertBatch = async (): Promise<void> => {
    if (batch.length === 0) return;
    const rows = batch;
    batch = [];
    await this.ordersRepo
      .createQueryBuilder()
      .insert()
      .values(rows)
      .execute();
    imported += rows.length;
  };

  const batchInsert = new Transform({
    objectMode: true,
    transform(row, _encoding, callback) {
      batch.push(mapCsvToEntity(row));
      if (batch.length < BATCH_SIZE) return callback();
      // Pass the insert error to callback so pipeline() rejects instead of hanging
      insertBatch().then(() => callback(), callback);
    },
    flush(callback) {
      // Flush remaining rows
      insertBatch().then(() => callback(), callback);
    },
  });

  await pipeline(
    createReadStream(filePath),
    csvParser(),
    batchInsert,
  );

  return { imported };
}
```

**Giải thích từng bước:**

1. `createReadStream` — đọc file theo chunk 64KB, không load toàn bộ
2. `csvParser()` — Transform stream parse CSV headers + rows
3. `batchInsert` — Gom 1000 rows rồi bulk insert, giảm round-trips tới DB. Insert lỗi thì gọi `callback(err)` để `pipeline()` reject; không gọi thì import treo
4. `pipeline()` — Kết nối 3 stream, tự handle backpressure và error cleanup
5. `flush()` — Xử lý batch cuối cùng khi stream kết thúc

---

## 4. Tooling & Config

### 4.1. Packages cần thiết

```bash
# File upload
pnpm add @nestjs/platform-express multer
pnpm add -D @types/multer

# CSV parsing (nếu cần)
pnpm add csv-parser
pnpm add -D @types/csv-parser

# TypeORM QueryBuilder.stream() on PostgreSQL (CSV export)
pnpm add pg-query-stream

# AWS S3 streaming
pnpm add @aws-sdk/client-s3 @aws-sdk/lib-storage
```

### 4.2. Multer config tập trung

Tạo file `src/common/config/multer.config.ts`:

```ts
import { MulterOptions } from '@nestjs/platform-express/multer/interfaces/multer-options.interface';
import { diskStorage } from 'multer';
import { extname } from 'path';
import { v4 as uuid } from 'uuid';

export const UPLOAD_DIR = './uploads/tmp';

export const defaultMulterOptions: MulterOptions = {
  storage: diskStorage({
    destination: UPLOAD_DIR,
    filename: (_req, file, cb) =>
      cb(null, `${uuid()}${extname(file.originalname)}`),
  }),
  limits: {
    fileSize: 10 * 1024 * 1024, // 10MB default
    files: 10, // max 10 files per request
  },
};

export function createMulterOptions(
  overrides?: Partial<MulterOptions>,
): MulterOptions {
  return { ...defaultMulterOptions, ...overrides };
}
```

### 4.3. Cleanup temp files

Dùng cron job hoặc middleware để dọn temp files:

```ts
import { Cron, CronExpression } from '@nestjs/schedule';
import { readdirSync, statSync, unlinkSync } from 'fs';
import { join } from 'path';

@Injectable()
export class FileCleanupService {
  private readonly logger = new Logger(FileCleanupService.name);

  @Cron(CronExpression.EVERY_HOUR)
  cleanupTempFiles(): void {
    const tmpDir = './uploads/tmp';
    const maxAge = 60 * 60 * 1000; // 1 hour
    const now = Date.now();

    const files = readdirSync(tmpDir);
    for (const file of files) {
      const filePath = join(tmpDir, file);
      const { mtimeMs } = statSync(filePath);
      if (now - mtimeMs > maxAge) {
        unlinkSync(filePath);
        this.logger.log(`Cleaned up temp file: ${file}`);
      }
    }
  }
}
```

---

## References

- [Node.js Streams API](https://nodejs.org/docs/latest/api/stream.html)
- [Node.js stream.pipeline()](https://nodejs.org/docs/latest/api/stream.html#streampipelinesource-transforms-destination-callback)
- [Node.js File System (fs)](https://nodejs.org/docs/latest/api/fs.html)
- [NestJS File Upload](https://docs.nestjs.com/techniques/file-upload)
- [NestJS Streaming Files](https://docs.nestjs.com/techniques/streaming-files)
- [NestJS Server-Sent Events](https://docs.nestjs.com/techniques/server-sent-events)
- [Multer — Express file upload](https://github.com/expressjs/multer)
- [AWS SDK v3 — S3 Upload](https://docs.aws.amazon.com/AWSJavaScriptSDK/v3/latest/Package/-aws-sdk-lib-storage/)
- [Node.js Backpressuring in Streams](https://nodejs.org/en/learn/modules/backpressuring-in-streams)

## Changelog

| Date | Version | Change | By |
| :---- | :---- | :---- | :---- |
| 2026-11-18 | v1.0 | Chuyển từ Notion "NestJS Document" (page `33d71a38d3b281ec8092e6d7fcdb9e58`, sửa 2026-04-09). Review và sửa nội dung, code trước khi publish. Owner duyệt trong chat ngày 2026-11-18. | Bắc PV |
