# NestJS Coding Standard 6.4 — WebSockets & Real-time

| Field | Value |
| :---- | :---- |
| Owner | Bắc PV — NodeJS BE Dev Lead |
| Audience | Dev (NodeJS BE) |
| Last reviewed | 2026-11-12 |
| Review cadence | Quarterly |
| Version | v1.0 |
| Linked from | Ref_Dev_nestjs-coding-standard_v1.0 |
| Status | Live |

Doc này là mục 6.4 của [NestJS Coding Standard](Ref_Dev_nestjs-coding-standard_v1.0.md), nhóm Async & Integration. Doc nêu quy tắc về WebSockets & Real-time trong dự án NestJS, kèm lý do, ví dụ và config. Dev NodeJS BE đọc doc này khi viết code, review code và onboarding.

---

## 1. Tóm tắt & Phạm vi

> 📌 **Chủ đề**: WebSockets & Real-time trong NestJS — cách xây dựng giao tiếp hai chiều (bidirectional) giữa client và server sử dụng `@nestjs/websockets`, Gateways, và [Socket.io](http://socket.io/).

- **Vấn đề giải quyết**: Thống nhất cách team triển khai real-time features — từ thiết kế Gateway, quản lý rooms/namespaces, xử lý authentication, đến error handling và scaling trong môi trường production.
- **Scope áp dụng**: Tất cả các module/feature cần giao tiếp real-time: chat, notifications, live updates, collaborative editing, dashboards, tracking.
- **Tại sao quan trọng**:
- WebSocket khác hoàn toàn REST — stateful connection, persistent, bidirectional — cần conventions riêng để tránh memory leak, connection leak, và security holes.
- Thiếu chuẩn hóa dẫn đến mỗi người implement một kiểu — khó maintain, debug, và scale.
- Real-time features thường là phần phức tạp nhất của hệ thống — cần patterns rõ ràng để onboard member mới nhanh.

---

## 2. Quy tắc & Giải thích

### 2.1. Kiến trúc Gateway trong NestJS

> ✅ **Đề xuất**: Dùng `@nestjs/websockets` + `@nestjs/platform-socket.io` làm mặc định. Mỗi domain/feature có 1 Gateway riêng.

**WebSocket Gateway là gì?**

Gateway là class được decorate bằng `@WebSocketGateway()` — tương đương Controller trong REST nhưng cho WebSocket connections. Gateway handle incoming messages, broadcast events, và quản lý client connections.

**So sánh WebSocket vs REST:**

| Tiêu chí | REST (HTTP) | WebSocket |
| --- | --- | --- |
| Kết nối | Stateless — mỗi request tạo connection mới | Stateful — persistent connection |
| Hướng giao tiếp | Client → Server (request/response) | Bidirectional (cả 2 chiều) |
| Server push | ❌ Không hỗ trợ (cần polling) | ✅ Server push events bất kỳ lúc nào |
| Overhead | HTTP headers mỗi request | Lightweight frames sau handshake |
| Use case | CRUD, APIs, file upload | Chat, notifications, live data, gaming |

**Khi nào dùng WebSocket?**

- ✅ Cần server push data đến client ngay lập tức (notifications, chat messages).
- ✅ Cần bidirectional communication liên tục (collaborative editing, live cursors).
- ✅ Cần low-latency updates (live dashboards, stock tickers, gaming).
- ❌ **KHÔNG dùng** cho CRUD operations đơn giản — REST vẫn phù hợp hơn.
- ❌ **KHÔNG dùng** khi client chỉ cần nhận updates hiếm khi — Server-Sent Events (SSE) nhẹ hơn.

> Tham khảo: [NestJS Gateways](https://docs.nestjs.com/websockets/gateways), [Socket.io](http://socket.io/) [Docs](https://socket.io/docs/v4/)

### 2.2. Tổ chức code: Gateway, Service & Module

> ✅ **Đề xuất**: Tách Gateway (handle connections/messages) và Service (business logic) — giống pattern Controller/Service trong REST.

**Tại sao tách?**

- **Testability**: Mock gateway trong unit test — test business logic độc lập.
- **Reusability**: Service có thể được inject bởi cả REST controller và WebSocket gateway.
- **Readability**: Reviewer biết rõ “chỗ này handle WebSocket” vs “chỗ này là business logic”.

**Quy tắc:**

- ✅ **NÊN**: Mỗi feature/domain có 1 gateway riêng: `chat.gateway.ts`, `notifications.gateway.ts`.
- ✅ **NÊN**: Gateway chỉ handle message routing, connection lifecycle. Business logic ở service.
- ✅ **NÊN**: Đặt gateway trong feature module: `src/modules/<feature>/<feature>.gateway.ts`.
- ✅ **NÊN**: Register gateway trong module’s `providers` — NestJS DI tự quản lý lifecycle.
- ❌ **KHÔNG NÊN**: 1 gateway xử lý tất cả events của toàn app — khó maintain, vi phạm SRP.
- ❌ **KHÔNG NÊN**: Business logic trong gateway — gateway chỉ delegate cho service.

```ts
// Cấu trúc feature module với Gateway
src/modules/chat/
├── chat.module.ts          // Module declaration
├── chat.gateway.ts         // WebSocket event handling
├── chat.service.ts         // Business logic
├── dto/
│   ├── send-message.dto.ts
│   └── join-room.dto.ts
└── entities/
    └── message.entity.ts
```

### 2.3. Gateway Configuration & Namespaces

> ✅ **Đề xuất**: Dùng namespace để tách biệt các domain WebSocket. Cấu hình CORS, transports, và ping trong `@WebSocketGateway()` decorator.

**Quy tắc:**

- ✅ **NÊN**: Dùng namespace cho mỗi feature: `/chat`, `/notifications`, `/live-updates`.
- ✅ **NÊN**: Cấu hình CORS khớp với REST API — dùng `ConfigService`, không hardcode.
- ✅ **NÊN**: Bật `pingInterval` và `pingTimeout` để detect dead connections sớm.
- ✅ **NÊN**: Dùng `transports: ['websocket']` cho production — tránh HTTP long-polling fallback nếu không cần.
- ❌ **KHÔNG NÊN**: `cors: { origin: '*' }` trong production — chỉ whitelist domains cần thiết.
- ❌ **KHÔNG NÊN**: Để `pingTimeout` quá cao — dead connections chiếm resources.

```ts
// chat.gateway.ts — cấu hình chuẩn
@WebSocketGateway({
  namespace: '/chat',
  cors: {
    origin: process.env.CORS_ORIGINS?.split(',') || ['http://localhost:3000'],
    credentials: true,
  },
  transports: ['websocket', 'polling'], // Fallback cho network kém
  pingInterval: 25000,  // Ping mỗi 25s
  pingTimeout: 20000,   // Timeout sau 20s không pong
})
export class ChatGateway implements OnGatewayInit, OnGatewayConnection, OnGatewayDisconnect {
  @WebSocketServer()
  server: Server;

  private readonly logger = new Logger(ChatGateway.name);

  afterInit(server: Server) {
    this.logger.log('Chat Gateway initialized');
  }

  handleConnection(client: Socket) {
    this.logger.log(`Client connected: ${client.id}`);
  }

  handleDisconnect(client: Socket) {
    this.logger.log(`Client disconnected: ${client.id}`);
  }
}
```

> Tham khảo: [Socket.io](http://socket.io/) [Server Options](https://socket.io/docs/v4/server-options/), [NestJS Gateway Decorator](https://docs.nestjs.com/websockets/gateways#gateway-decorator)

### 2.4. Message Handling & Event Naming

> ✅ **Đề xuất**: Dùng `@SubscribeMessage('event-name')` cho incoming events. Event names theo convention `domain:action` (kebab-case hoặc camelCase, thống nhất trong team).

**Quy tắc:**

- ✅ **NÊN**: Event naming rõ ràng, có prefix domain: `chat:sendMessage`, `chat:joinRoom`, `notification:markRead`.
- ✅ **NÊN**: Validate payload bằng `ValidationPipe` — giống REST DTOs.
- ✅ **NÊN**: Return value từ `@SubscribeMessage` handler = acknowledgment cho client.
- ✅ **NÊN**: Dùng DTO cho mọi incoming message payload — type-safe, validate được.
- ❌ **KHÔNG NÊN**: Event names mơ hồ: `message`, `data`, `update` — không biết thuộc feature nào.
- ❌ **KHÔNG NÊN**: `@MessageBody() body: any` — mất type-safety và validation.

```ts
// DTOs cho WebSocket events
export class SendMessageDto {
  @IsString() @IsNotEmpty()
  roomId: string;

  @IsString() @IsNotEmpty() @MaxLength(5000)
  content: string;

  @IsOptional() @IsEnum(MessageType)
  type?: MessageType;
}

export class JoinRoomDto {
  @IsString() @IsNotEmpty()
  roomId: string;
}
```

```ts
// Gateway — message handling với validation
@WebSocketGateway({ namespace: '/chat' })
export class ChatGateway {
  constructor(private readonly chatService: ChatService) {}

  @WebSocketServer()
  server: Server;

  @SubscribeMessage('chat:sendMessage')
  @UsePipes(new ValidationPipe({ whitelist: true, transform: true }))
  async handleSendMessage(
    @ConnectedSocket() client: Socket,
    @MessageBody() dto: SendMessageDto,
  ): Promise<MessageResponseDto> {
    const userId = client.data.userId; // Set trong auth middleware
    const message = await this.chatService.sendMessage(userId, dto);

    // Broadcast cho cả room (trừ sender)
    client.to(dto.roomId).emit('chat:newMessage', message);

    // Return = acknowledgment cho sender
    // Plain data goes to the client's ack callback; returning { event, data }
    // would emit that event instead and never call the ack.
    return message;
  }

  @SubscribeMessage('chat:joinRoom')
  @UsePipes(new ValidationPipe({ whitelist: true, transform: true }))
  async handleJoinRoom(
    @ConnectedSocket() client: Socket,
    @MessageBody() dto: JoinRoomDto,
  ): Promise<{ roomId: string }> {
    const userId = client.data.userId;
    await this.chatService.validateRoomAccess(userId, dto.roomId);

    await client.join(dto.roomId);
    client.to(dto.roomId).emit('chat:userJoined', { userId, roomId: dto.roomId });

    return { roomId: dto.roomId }; // Ack payload
  }
}
```

### 2.5. Rooms & Broadcasting

> ✅ **Đề xuất**: Dùng [Socket.io](http://socket.io/) rooms để group clients. Broadcast qua rooms thay vì loop qua từng client.

**Quy tắc:**

- ✅ **NÊN**: Dùng `client.join(roomId)` để add client vào room, `client.leave(roomId)` để rời.
- ✅ **NÊN**: Room naming convention: `<entity>:<id>` — ví dụ `order:123`, `chat:room-456`, `user:789`.
- ✅ **NÊN**: Cleanup rooms khi client disconnect — tránh ghost rooms.
- ✅ **NÊN**: Dùng `server.to(room).emit()` để broadcast — [Socket.io](http://socket.io/) optimize routing.
- ❌ **KHÔNG NÊN**: Loop qua `server.sockets` để emit cho từng client — không scale, chậm.
- ❌ **KHÔNG NÊN**: Lưu client list trong memory (Map/Set) khi [Socket.io](http://socket.io/) rooms đã handle.

**Broadcasting patterns:**

```ts
// Broadcast cho tất cả trong room (trừ sender)
client.to('chat:room-123').emit('chat:newMessage', message);

// Broadcast cho tất cả trong room (bao gồm sender)
this.server.to('chat:room-123').emit('chat:newMessage', message);

// Broadcast cho tất cả connected clients
this.server.emit('system:maintenance', { message: 'Server restart in 5 min' });

// Emit cho 1 client cụ thể
this.server.to(clientSocketId).emit('notification:new', notification);

// Broadcast cho nhiều rooms
this.server.to('room-1').to('room-2').emit('event', data);
```

### 2.6. Authentication & Authorization

> ⚠️ **Nguyên tắc cốt lõi**: WebSocket connections PHẢI được authenticate. Dùng middleware hoặc Guard — không tin client payload.

**Quy tắc:**

- ✅ **NÊN**: Authenticate trong `handleConnection` hoặc dùng [Socket.io](http://socket.io/) middleware — reject sớm trước khi handle bất kỳ event nào.
- ✅ **NÊN**: Đọc access token từ cookie `accessToken` trong handshake, cùng cookie HTTP API dùng ([NestJS Coding Standard 5.1 — Authentication](Ref_Dev_s5.1_nestjs-authentication_v1.0.md) mục 2.3). Client khác origin bật `withCredentials: true`.
- ✅ **NÊN**: Lưu user info vào `client.data` sau khi authenticate — tránh decode JWT mỗi event.
- ✅ **NÊN**: Dùng Guards (`@UseGuards()`) cho event-level authorization khi cần.
- ✅ **NÊN**: Disconnect client khi token expired — dùng `client.disconnect(true)`.
- ❌ **KHÔNG NÊN**: Tin `userId` từ client payload — luôn lấy từ `client.data` (đã verify).
- ❌ **KHÔNG NÊN**: Cho phép anonymous connections trừ khi business yêu cầu rõ ràng (public chat room).

```ts
// Cách 1: Socket.io middleware (recommended)
import { parse } from 'cookie';

@WebSocketGateway({ namespace: '/chat' })
export class ChatGateway implements OnGatewayInit {
  constructor(
    private readonly jwtService: JwtService,
    private readonly configService: ConfigService,
  ) {}

  afterInit(server: Server) {
    server.use(async (socket, next) => {
      try {
        // The browser sends the HttpOnly accessToken cookie with the handshake request
        const token = parse(socket.handshake.headers.cookie ?? '').accessToken;

        if (!token) {
          return next(new WsException('Missing authentication token'));
        }

        const payload = await this.jwtService.verifyAsync<JwtPayload>(token, {
          secret: this.configService.getOrThrow<string>('JWT_SECRET'),
        });

        // Lưu user info vào socket.data — dùng ở mọi handler
        socket.data.userId = payload.sub;
        socket.data.roles = payload.roles;
        next();
      } catch (error) {
        next(new WsException('Invalid or expired token'));
      }
    });
  }
}
```

```ts
// Cách 2: NestJS Guard cho event-level authorization
@Injectable()
export class WsRolesGuard implements CanActivate {
  constructor(private reflector: Reflector) {}

  canActivate(context: ExecutionContext): boolean {
    const requiredRoles = this.reflector.getAllAndOverride<Role[]>(ROLES_KEY, [
      context.getHandler(),
      context.getClass(),
    ]);
    if (!requiredRoles) return true;

    const client = context.switchToWs().getClient<Socket>();
    return requiredRoles.some((role) => client.data.roles?.includes(role));
  }
}

// Sử dụng trong gateway
@SubscribeMessage('chat:deleteMessage')
@UseGuards(WsRolesGuard)
@Roles(Role.ADMIN, Role.STAFF) // enum Role, 5.2 section 2.1
async handleDeleteMessage(
  @ConnectedSocket() client: Socket,
  @MessageBody() dto: DeleteMessageDto,
) {
  // Chỉ admin/staff mới vào được
}
```

> Tham khảo: [Socket.io](http://socket.io/) [Middlewares](https://socket.io/docs/v4/middlewares/), [NestJS Guards](https://docs.nestjs.com/websockets/guards)

### 2.7. Exception Handling

> ✅ **Đề xuất**: Dùng `WsException` thay vì `HttpException` trong Gateway context. Implement `WsExceptionFilter` global cho gateway.

**Quy tắc:**

- ✅ **NÊN**: Throw `WsException` (từ `@nestjs/websockets`) cho WebSocket errors — client nhận đúng format.
- ✅ **NÊN**: Implement custom `WsExceptionFilter` — format error response chuẩn.
- ✅ **NÊN**: Log errors với context (client ID, room, event name).
- ✅ **NÊN**: Emit error event cho client thay vì disconnect khi lỗi recoverable.
- ❌ **KHÔNG NÊN**: Throw `HttpException` trong gateway — client nhận message sai format.
- ❌ **KHÔNG NÊN**: Silent catch errors — client không biết request fail.

```ts
// Custom WsException filter
// Also catches HttpException: ValidationPipe throws BadRequestException, not WsException
@Catch(WsException, HttpException)
export class WsExceptionFilter implements ExceptionFilter {
  private readonly logger = new Logger(WsExceptionFilter.name);

  catch(exception: WsException | HttpException, host: ArgumentsHost) {
    const client = host.switchToWs().getClient<Socket>();
    const error =
      exception instanceof WsException ? exception.getError() : exception.getResponse();

    // Same { error } wrapper as the REST error body (3.1 section 2.4)
    const errorResponse = {
      error: {
        ...(typeof error === 'string' ? { message: error } : error),
        timestamp: new Date().toISOString(),
      },
    };

    this.logger.warn(
      `WS Error [${client.id}]: ${JSON.stringify(error)}`,
    );

    client.emit('error', errorResponse);
  }
}

// Apply filter trên gateway
@WebSocketGateway({ namespace: '/chat' })
@UseFilters(new WsExceptionFilter())
export class ChatGateway { ... }
```

### 2.8. Connection State Management

> ⚠️ **Nguyên tắc**: Quản lý connection state cẩn thận — cleanup khi disconnect, tránh memory leak.

**Quy tắc:**

- ✅ **NÊN**: Track online users qua Redis (production) hoặc Map (dev) — cần cho “user online status”.
- ✅ **NÊN**: Cleanup tất cả rooms và user state trong `handleDisconnect`.
- ✅ **NÊN**: Handle reconnection gracefully — rejoin rooms, sync missed events.
- ✅ **NÊN**: Dùng `client.data` để lưu per-connection state (userId, joinedRooms) — tự cleanup khi disconnect.
- ❌ **KHÔNG NÊN**: Lưu state trong gateway instance variables (Map/Set) mà không cleanup — memory leak.
- ❌ **KHÔNG NÊN**: Assume connection luôn ổn định — handle network interruptions.

```ts
// Connection state management
@WebSocketGateway({ namespace: '/chat' })
export class ChatGateway implements OnGatewayConnection, OnGatewayDisconnect {
  private readonly logger = new Logger(ChatGateway.name);

  constructor(
    private readonly chatService: ChatService,
    private readonly presenceService: PresenceService, // Redis-based
  ) {}

  @WebSocketServer()
  server: Server;

  async handleConnection(client: Socket) {
    const userId = client.data.userId;
    if (!userId) {
      client.disconnect(true);
      return;
    }

    // Notify rooms. client.rooms is already empty in handleDisconnect,
    // so read it on 'disconnecting', which fires before socket.io leaves the rooms
    client.on('disconnecting', () => {
      const rooms = Array.from(client.rooms).filter((r) => r !== client.id);
      for (const room of rooms) {
        client.to(room).emit('chat:userLeft', { userId });
      }
    });

    // Track user online status trong Redis
    await this.presenceService.setOnline(userId, client.id);

    // Rejoin rooms (reconnection support)
    const userRooms = await this.chatService.getUserRooms(userId);
    for (const roomId of userRooms) {
      await client.join(`chat:${roomId}`);
    }

    this.logger.log(`User ${userId} connected (socket: ${client.id})`);
  }

  async handleDisconnect(client: Socket) {
    const userId = client.data.userId;
    if (!userId) return;

    // Cleanup presence
    await this.presenceService.setOffline(userId, client.id);

    this.logger.log(`User ${userId} disconnected (socket: ${client.id})`);
  }
}
```

### 2.9. Scaling với Redis Adapter

> ⚠️ **Nguyên tắc**: [Socket.io](http://socket.io/) mặc định chỉ broadcast trong 1 process. Multi-server/container PHẢI dùng Redis Adapter để sync events cross-instance.

**Quy tắc:**

- ✅ **NÊN**: Dùng `@socket.io/redis-adapter` cho production multi-instance.
- ✅ **NÊN**: Sticky sessions (hoặc WebSocket-only transport) khi dùng load balancer.
- ✅ **NÊN**: Monitor Redis adapter connection — reconnect tự động.
- ❌ **KHÔNG NÊN**: Lưu state trong memory (Map/Set) khi multi-instance — data không đồng bộ.
- ❌ **KHÔNG NÊN**: Assume tất cả clients kết nối cùng 1 server instance.

```ts
// Redis adapter setup
import { IoAdapter } from '@nestjs/platform-socket.io';
import { createAdapter } from '@socket.io/redis-adapter';
import { createClient, type RedisClientOptions } from 'redis';
import { ServerOptions } from 'socket.io';
import { INestApplication, Logger } from '@nestjs/common';

export class RedisIoAdapter extends IoAdapter {
  private adapterConstructor: ReturnType<typeof createAdapter>;
  private readonly logger = new Logger(RedisIoAdapter.name);

  constructor(private app: INestApplication) {
    super(app);
  }

  async connectToRedis(options: RedisClientOptions): Promise<void> {
    const pubClient = createClient(options);
    const subClient = pubClient.duplicate();

    pubClient.on('error', (err: Error) => this.logger.error('Redis Pub error', err.stack));
    subClient.on('error', (err: Error) => this.logger.error('Redis Sub error', err.stack));

    await Promise.all([pubClient.connect(), subClient.connect()]);

    this.adapterConstructor = createAdapter(pubClient, subClient);
    this.logger.log('Redis adapter connected');
  }

  createIOServer(port: number, options?: ServerOptions) {
    const server = super.createIOServer(port, options);
    server.adapter(this.adapterConstructor);
    return server;
  }
}
```

```ts
// main.ts — apply Redis adapter
async function bootstrap() {
  const app = await NestFactory.create(AppModule);
  const configService = app.get(ConfigService);

  // Setup Redis adapter cho production
  if (configService.get('NODE_ENV') === 'production') {
    const redisIoAdapter = new RedisIoAdapter(app);
    // Same REDIS_HOST/PORT/PASSWORD as the cache (2.1 section 2.3)
    await redisIoAdapter.connectToRedis({
      socket: {
        host: configService.getOrThrow<string>('REDIS_HOST'),
        port: configService.getOrThrow<number>('REDIS_PORT'),
      },
      password: configService.get<string>('REDIS_PASSWORD'),
    });
    app.useWebSocketAdapter(redisIoAdapter);
  }

  await app.listen(configService.get('PORT', 3000));
}
```

> Tham khảo: [Socket.io](http://socket.io/) [Redis Adapter](https://socket.io/docs/v4/redis-adapter/), [NestJS Adapters](https://docs.nestjs.com/websockets/adapter)

### 2.10. Performance & Best Practices

**Quy tắc:**

- ✅ **NÊN**: Compress payload lớn — bật `perMessageDeflate` hoặc nén data trước khi emit.
- ✅ **NÊN**: Throttle/debounce events ở client-side — tránh flood server (typing indicators, mouse movement).
- ✅ **NÊN**: Dùng `volatile.emit()` cho non-critical events (typing indicator) — drop nếu client chưa sẵn sàng.
- ✅ **NÊN**: Paginate historical data qua REST API — WebSocket chỉ cho real-time events.
- ✅ **NÊN**: Giới hạn payload size — reject messages quá lớn (`maxHttpBufferSize`).
- ❌ **KHÔNG NÊN**: Gửi toàn bộ entity qua WebSocket — chỉ gửi changed fields hoặc delta.
- ❌ **KHÔNG NÊN**: Dùng WebSocket cho file upload — dùng REST + presigned URL.
- ❌ **KHÔNG NÊN**: Broadcast tất cả events cho tất cả clients — dùng rooms để scope.

---

## 3. Ví dụ minh họa thực tế

### 3.1. Walkthrough: Feature “Chat Room” — từ Module đến Production

Giả sử team cần implement feature chat room với yêu cầu:

- User join/leave rooms
- Gửi/nhận messages real-time
- Online status tracking
- Authentication bằng JWT

**Bước 1: Module setup**

```ts
// chat.module.ts
@Module({
  imports: [JwtModule, UsersModule],
  providers: [ChatGateway, ChatService, PresenceService],
})
export class ChatModule {}
```

**Bước 2: DTOs — validate incoming messages**

```ts
// dto/send-message.dto.ts
export class SendMessageDto {
  @IsString() @IsNotEmpty()
  roomId: string;

  @IsString() @IsNotEmpty() @MaxLength(5000)
  content: string;

  @IsOptional() @IsEnum(MessageType)
  type?: MessageType = MessageType.TEXT;
}

// dto/join-room.dto.ts
export class JoinRoomDto {
  @IsString() @IsNotEmpty()
  roomId: string;
}

// dto/message-response.dto.ts
export class MessageResponseDto {
  id: string;
  roomId: string;
  senderId: string;
  senderName: string;
  content: string;
  type: MessageType;
  createdAt: Date;
}
```

**Bước 3: Service — business logic**

```ts
// chat.service.ts
@Injectable()
export class ChatService {
  constructor(
    private readonly messagesRepo: MessagesRepository,
    private readonly roomsRepo: RoomsRepository,
  ) {}

  async sendMessage(
    userId: string,
    dto: SendMessageDto,
  ): Promise<MessageResponseDto> {
    // Validate room membership
    const isMember = await this.roomsRepo.isMember(dto.roomId, userId);
    if (!isMember) {
      throw new WsException('Not a member of this room');
    }

    // Persist message
    const message = await this.messagesRepo.create({
      roomId: dto.roomId,
      senderId: userId,
      content: dto.content,
      type: dto.type ?? MessageType.TEXT,
    });

    return this.toResponseDto(message);
  }

  async validateRoomAccess(userId: string, roomId: string): Promise<void> {
    const room = await this.roomsRepo.findById(roomId);
    if (!room) throw new WsException(`Room ${roomId} not found`);

    const isMember = await this.roomsRepo.isMember(roomId, userId);
    if (!isMember) throw new WsException('Access denied');
  }

  async getUserRooms(userId: string): Promise<string[]> {
    return this.roomsRepo.findRoomIdsByUserId(userId);
  }
}
```

**Bước 4: Gateway — handle WebSocket events**

```ts
// chat.gateway.ts
import { parse } from 'cookie'; // Reads the HttpOnly accessToken cookie from the handshake

@WebSocketGateway({
  namespace: '/chat',
  cors: {
    origin: process.env.CORS_ORIGINS?.split(','),
    credentials: true,
  },
  pingInterval: 25000,
  pingTimeout: 20000,
})
@UseFilters(new WsExceptionFilter())
export class ChatGateway
  implements OnGatewayInit, OnGatewayConnection, OnGatewayDisconnect
{
  @WebSocketServer()
  server: Server;

  private readonly logger = new Logger(ChatGateway.name);

  constructor(
    private readonly chatService: ChatService,
    private readonly presenceService: PresenceService,
    private readonly jwtService: JwtService,
    private readonly configService: ConfigService,
  ) {}

  // Auth middleware
  afterInit(server: Server) {
    server.use(async (socket, next) => {
      try {
        const token = parse(socket.handshake.headers.cookie ?? '').accessToken;
        if (!token) return next(new WsException('Missing token'));

        const payload = await this.jwtService.verifyAsync<JwtPayload>(token, {
          secret: this.configService.getOrThrow<string>('JWT_SECRET'),
        });
        socket.data.userId = payload.sub;
        socket.data.roles = payload.roles;
        next();
      } catch {
        next(new WsException('Invalid token'));
      }
    });
  }

  // Connection lifecycle
  async handleConnection(client: Socket) {
    const userId = client.data.userId;
    if (!userId) return client.disconnect(true);

    // client.rooms is empty by the time handleDisconnect runs; read it here
    client.on('disconnecting', () => {
      const rooms = Array.from(client.rooms).filter((r) => r !== client.id);
      for (const room of rooms) {
        client.to(room).emit('chat:userOffline', { userId });
      }
    });

    await this.presenceService.setOnline(userId, client.id);

    // Auto-rejoin rooms
    const rooms = await this.chatService.getUserRooms(userId);
    await Promise.all(rooms.map((r) => client.join(`chat:${r}`)));

    this.logger.log(`User ${userId} connected`);
  }

  async handleDisconnect(client: Socket) {
    const userId = client.data.userId;
    if (!userId) return;

    await this.presenceService.setOffline(userId, client.id);

    this.logger.log(`User ${userId} disconnected`);
  }

  // Event handlers
  @SubscribeMessage('chat:sendMessage')
  @UsePipes(new ValidationPipe({ whitelist: true, transform: true }))
  async handleSendMessage(
    @ConnectedSocket() client: Socket,
    @MessageBody() dto: SendMessageDto,
  ) {
    const message = await this.chatService.sendMessage(
      client.data.userId,
      dto,
    );
    client.to(`chat:${dto.roomId}`).emit('chat:newMessage', message);
    return message; // Plain data → sender's ack callback
  }

  @SubscribeMessage('chat:joinRoom')
  @UsePipes(new ValidationPipe({ whitelist: true, transform: true }))
  async handleJoinRoom(
    @ConnectedSocket() client: Socket,
    @MessageBody() dto: JoinRoomDto,
  ) {
    await this.chatService.validateRoomAccess(client.data.userId, dto.roomId);
    await client.join(`chat:${dto.roomId}`);
    client.to(`chat:${dto.roomId}`).emit('chat:userJoined', {
      userId: client.data.userId,
    });
    return { roomId: dto.roomId };
  }

  @SubscribeMessage('chat:leaveRoom')
  @UsePipes(new ValidationPipe({ whitelist: true, transform: true }))
  async handleLeaveRoom(
    @ConnectedSocket() client: Socket,
    @MessageBody() dto: JoinRoomDto,
  ) {
    await client.leave(`chat:${dto.roomId}`);
    client.to(`chat:${dto.roomId}`).emit('chat:userLeft', {
      userId: client.data.userId,
    });
    return { roomId: dto.roomId };
  }

  @SubscribeMessage('chat:typing')
  async handleTyping(
    @ConnectedSocket() client: Socket,
    @MessageBody() dto: JoinRoomDto,
  ) {
    // Volatile — drop nếu client chưa sẵn sàng
    client.to(`chat:${dto.roomId}`).volatile.emit('chat:userTyping', {
      userId: client.data.userId,
    });
  }
}
```

**Bước 5: Client-side integration (reference)**

```ts
// Client-side (React/Angular/Vue) — chỉ để reference
import { io, Socket } from 'socket.io-client';

const socket: Socket = io('http://localhost:3000/chat', {
  auth: { token: 'jwt-access-token' },
  transports: ['websocket', 'polling'],
  reconnection: true,
  reconnectionAttempts: 5,
  reconnectionDelay: 1000,
});

// Listen events
socket.on('chat:newMessage', (message) => { /* render message */ });
socket.on('chat:userJoined', ({ userId }) => { /* update user list */ });
socket.on('error', (error) => { /* show error */ });

// Send events with acknowledgment
socket.emit('chat:sendMessage', { roomId: 'room-1', content: 'Hello!' }, (response: unknown) => {
  console.log('Ack:', response); // MessageResponseDto as JSON (createdAt arrives as a string)
});
```

### 3.2. Before / After: Từ implementation sai đến chuẩn

**Before — không auth, không validate, business logic trong gateway:**

```ts
// ❌ Bad — mọi thứ gộp chung, không auth, không validate
@WebSocketGateway()
export class AppGateway {
  @WebSocketServer() server: Server;

  @SubscribeMessage('sendMessage')
  async handleMessage(@MessageBody() body: any) {
    // Business logic trực tiếp trong gateway
    const message = await this.messageRepo.save({
      userId: body.userId,  // Trust client! XSS/spoof risk
      content: body.content, // Không validate!
      room: body.room,
    });
    this.server.emit('newMessage', message); // Broadcast cho TẤT CẢ clients!
    return message;
  }
}
```

**After — auth, validate, tách service, scoped broadcast:**

```ts
// ✅ Good — auth middleware, validate DTO, delegate service, room-scoped broadcast
@WebSocketGateway({ namespace: '/chat' })
@UseFilters(new WsExceptionFilter())
export class ChatGateway implements OnGatewayInit {
  constructor(private readonly chatService: ChatService) {}

  @WebSocketServer() server: Server;

  afterInit(server: Server) {
    server.use(authMiddleware); // JWT verify
  }

  @SubscribeMessage('chat:sendMessage')
  @UsePipes(new ValidationPipe({ whitelist: true, transform: true }))
  async handleMessage(
    @ConnectedSocket() client: Socket,
    @MessageBody() dto: SendMessageDto,
  ) {
    const userId = client.data.userId; // Từ verified JWT
    const message = await this.chatService.sendMessage(userId, dto);
    client.to(`chat:${dto.roomId}`).emit('chat:newMessage', message); // Room-scoped
    return message; // Ack for the sender
  }
}
```

---

## 4. Tooling & Config

### 4.1. Installation

```bash
# Core packages
pnpm add @nestjs/websockets @nestjs/platform-socket.io
pnpm add socket.io

# Redis adapter (production)
pnpm add @socket.io/redis-adapter redis

# Client (nếu cần test)
pnpm add -D socket.io-client
```

### 4.2. Module Registration

```ts
// app.module.ts
@Module({
  imports: [
    ConfigModule.forRoot({ isGlobal: true }),
    ChatModule,
    NotificationsModule, // Mỗi feature module chứa gateway riêng
  ],
})
export class AppModule {}
```

### 4.3. Load Balancer Configuration (Nginx)

```txt
# nginx.conf — WebSocket proxy
upstream backend {
  ip_hash; # Sticky sessions cho Socket.io
  server app1:3000;
  server app2:3000;
}

server {
  location /socket.io/ {
    proxy_pass http://backend;
    proxy_http_version 1.1;
    proxy_set_header Upgrade $http_upgrade;
    proxy_set_header Connection "upgrade";
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_read_timeout 86400; # 24h — keep connection alive
  }
}
```

### 4.4. Testing WebSocket Gateway

```ts
// chat.gateway.spec.ts
import { Test, TestingModule } from '@nestjs/testing';
import { INestApplication } from '@nestjs/common';
import { io, Socket } from 'socket.io-client';

describe('ChatGateway (e2e)', () => {
  let app: INestApplication;
  let clientSocket: Socket;

  beforeAll(async () => {
    const module: TestingModule = await Test.createTestingModule({
      imports: [ChatModule],
    }).compile();

    app = module.createNestApplication();
    await app.listen(0); // Random port
    const port = app.getHttpServer().address().port;

    clientSocket = io(`http://localhost:${port}/chat`, {
      auth: { token: 'valid-jwt-token' },
      transports: ['websocket'],
    });

    await new Promise<void>((resolve) => clientSocket.on('connect', resolve));
  });

  afterAll(async () => {
    clientSocket.disconnect();
    await app.close();
  });

  it('should send and receive messages', (done) => {
    // The handler's return value arrives as the ack argument
    clientSocket.emit(
      'chat:sendMessage',
      { roomId: 'room-1', content: 'Hello!' },
      (data: MessageResponseDto) => {
        expect(data).toHaveProperty('id');
        expect(data.content).toBe('Hello!');
        done();
      },
    );
  });
});
```

### 4.5. Monitoring Checklist

- [ ] Track số lượng active connections (per namespace, per server)
- [ ] Monitor memory usage — connection leak gây tăng RAM liên tục
- [ ] Alert khi connection count vượt threshold
- [ ] Log connection/disconnection events (không log message content)
- [ ] Monitor Redis adapter latency (nếu dùng)
- [ ] Health check endpoint cho WebSocket server

---

## References

- [NestJS WebSockets](https://docs.nestjs.com/websockets/gateways) — Tài liệu chính thức về Gateways, Adapters, Exception Filters
- [Socket.io](http://socket.io/) [Documentation](https://socket.io/docs/v4/) — Server/Client API, Rooms, Namespaces, Adapters
- [Socket.io](http://socket.io/) [Redis Adapter](https://socket.io/docs/v4/redis-adapter/) — Multi-server scaling
- [Socket.io](http://socket.io/) [Admin UI](https://socket.io/docs/v4/admin-ui/) — Monitoring tool cho development
- [WebSocket Protocol (RFC 6455)](https://www.rfc-editor.org/rfc/rfc6455) — Protocol specification
- [NestJS Guards for WebSockets](https://docs.nestjs.com/websockets/guards) — Authorization trong WebSocket context
- [NestJS Exception Filters for WebSockets](https://docs.nestjs.com/websockets/exception-filters) — Error handling

## Changelog

| Date | Version | Change | By |
| :---- | :---- | :---- | :---- |
| 2026-11-18 | v1.0 | Chuyển từ Notion "NestJS Document" (page `33d71a38d3b28193ac88d9e8c1b9a18e`, sửa 2026-04-09). Review và sửa nội dung, code trước khi publish. Owner duyệt trong chat ngày 2026-11-18. | Bắc PV |
