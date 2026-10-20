---
title: Overview Event, Plugin & DI
platform: magento
scope: backend
status: current
author: magento-team@
owner: magento-team@
updated: 2026-10-20
tags: [di, plugin, event, observer, extensibility]
---

# Overview Event, Plugin & DI

> **Techstack:** Magento 2.4.x (Adobe Commerce / Magento Open Source)

Trước đây khi được hỏi làm thế nào thay thế một function của magento thì câu trả lời sẽ thường là:

Ưu tiên sử dụng event > plugin > override

Nhưng trong thực tế, câu trả lời này không chính xác, vì nó cần phải phụ thuộc vào tính chất của đối tượng cần phải thay đổi, và mong muốn thay đổi những gì của đối tượng, function gốc.

## 1. Event – Được xây dựng dựa trên Event observer pattern

![Observer pattern: một Subject gửi thông báo (notifies) tới nhiều Observer](images/so-sanh-overview-ve-event-plugin-di/image-01.png)

*Hình 1: Observer pattern – Subject thông báo tới các Observer*

Mỗi event sẽ thực dispatch để thực hiện thông báo việc đã thực hiện xong hành động và truyền data tới các observer.

Các observer chỉ thực hiện hành động dựa trên thông báo từ Subject, ko thể thực hiện sửa đổi or thay thế hành động của tượng gốc ban đầu. Event-Observer chỉ thay đổi được về data của object được truyền vào bằng các hàm `setData()`.

```mermaid
sequenceDiagram
    participant S as Subject (controller, model...)
    participant EM as Event Manager
    participant Cfg as Event config (events.xml)
    participant Inv as InvokerDefault
    participant O as Observer
    S->>EM: dispatch(eventName, data)
    EM->>Cfg: getObservers(eventName)
    loop Mỗi observer đã đăng ký
        EM->>Inv: dispatch(observerConfig, observer)
        Inv->>O: execute(observer), bỏ qua nếu disabled
        O->>O: đổi data của object qua setData()
    end
    EM-->>S: không có giá trị trả về
```

*Hình 2: `Magento\Framework\Event\Manager::dispatch()` gọi lần lượt các observer đã đăng ký cho event*

Event thường được dispatch trong controller, model, resource model sau, và trước khi các hành động đc thực hiện.

Thi thoảng có thể thấy trong view của layout

## 2. DI – Inject object

DI (dependency injection) sẽ thực hiện thay thế object thông qua ObjectManager. Đối tượng được thay thế sẽ và đối tượng gốc sẽ cũng đc implement một interface.

DI ko hoàn toàn giống như Mage class trong M1 replace object

M2 đưa show cho developer về DI pattern được thực hiện trong M2:

> “Dependency injection is a design pattern that allows an object A to declare its dependencies to an external object B that supplies those dependencies. The dependencies declared by A are usually class interfaces and the dependencies B provides are concrete implementations for those interfaces.
>
> This allows for loose coupling of code because object A no longer needs to be concerned with initializing its own dependencies. Object B decides which implementations to provide to object A based on a configuration or desired behavior.”

DI sẽ phụ thuộc vào ObjectManager nên chúng sẽ chỉ có thể DI được với các object gọi sau khi ObjectManager khởi tạo.

DI sẽ không thể tác động vào các object khởi tạo bằng toán tử `new Object();` mà chỉ tác động vào các object instance sử dụng `ObjectManger::get()`

DI config của object được chia theo từng Environment Area sẽ được lưu trữ trong `generated/metadata/{area_config}.php`, được load khi `ObjectManagerFactory` khởi tạo `ObjectManager` cho từng môi trường.

![Trích đoạn file generated/metadata: argument đã compile cho class Magento\TwoFactorAuth\Block\Provider\Authy\Auth (context, data, jsonHelper, directoryHelper)](images/so-sanh-overview-ve-event-plugin-di/image-02.png)

*Hình 3: DI config đã compile trong `generated/metadata` cho một class*

Ưu điểm của DI so với plugin có lẽ là performance, và khả năng thay thế các đối tượng phụ thuộc khi khởi tạo object.

DI config được load ngay khi khởi tạo đối tượng dựa trên ObjectManager cũng là một ưu điểm giúp sử dụng DI sẽ có hiệu suất nhanh hơn đáng kể so với Plugin.

Sau khi DI thì vì đối tượng gốc được thay thế bằng đối tượng mới nên hành động của đối tượng mới sẽ dễ kiểm soát, không giống như interceptor là thêm các điểm chặn vào trước và sau của method, và một method có thể bị tác động bởi nhiều interceptor.

DI phù hợp với việc customize các service contract, và sửa các hệ thống cần tối ưu hóa hiệu năng và or hành động xử lý dành riêng cho project, các đối tượng đc implement bởi interface.

## 3. Plugin – interceptors

Plugin sẽ thực hiện một interceptor lên object gốc, yếu điểm sẽ là performance và đối tượng gốc sẽ bị thay đổi. Vì interceptor sẽ thực hiện bọc ngoài func gốc bằng một function mới.

![Mô hình interceptor chung: request từ client đi qua PreHandle, PostHandle, AfterCompletion trước khi tới server và trả response](images/so-sanh-overview-ve-event-plugin-di/image-03.png)

*Hình 4: Interceptor chặn trước và sau khi request được xử lý*

```mermaid
sequenceDiagram
    participant Caller
    participant I as Subject Interceptor
    participant B as beforeX plugins
    participant A as aroundX plugin
    participant O as Method gốc
    participant Af as afterX plugins
    Caller->>I: x(args)
    I->>B: beforeX(subject, ...args) theo sortOrder
    B-->>I: args mới (nếu trả về khác null)
    alt Có around plugin
        I->>A: aroundX(subject, proceed, ...args)
        A->>O: proceed(...args) – chạy tiếp các plugin còn lại rồi method gốc
        O-->>A: result
        A-->>I: result
    else Không có around plugin
        I->>O: ___callParent(x, args)
        O-->>I: result
    end
    I->>Af: afterX(subject, result, ...args) theo sortOrder
    Af-->>I: result mới
    I-->>Caller: result
```

*Hình 5: Thứ tự chạy before → around → method gốc → after trong `Magento\Framework\Interception\Interceptor::___callPlugins()`*

Ưu điểm:

- Linh động dễ dàng tùy chỉnh đối tượng.
- Có thể tác động đến hầu hết các method, object
- Có thể thực hiện nhiều interceptor vào trong cùng một method của object

Yếu điểm:

- Performance
- Plugin sẽ là tạo thêm một đối tượng mới trong DI config, để ObjectManager có thể khởi tạo đối tượng này. `Magento\Framework\Interception\PluginList\PluginList`
- Nhiều Interceptor cùng tác động vào một hành động => dữ liệu bị thay đổi khi chạy qua interceptor => Khó kiểm soát dữ liệu.

Plugin phù hợp với việc customize, sửa đổi lại function cũ, thường là khi build extension vì có thể nhiều interceptor tác động lên 1 func.

> [!TIP]
> Một interceptor nên hạn chế thay đổi dữ liệu đầu vào ra ra của đối tượng gốc. Trong một vài trường hợp nên thay thế bằng DI. Nên ưu tiên plugin tới interface thay vì plugin tới trực tiếp class.

=> Tùy vào mục đích và mong muốn chúng ta sẽ lựa chọn giải pháp phù hợp.

```mermaid
flowchart TD
    A["Cần thay đổi hành vi của Magento"] --> B{"Chỉ cần nhận thông báo và<br/>đổi data object qua setData()?"}
    B -- "Có, và có event được dispatch" --> E["Event – Observer"]
    B -- Không --> C{"Thay thế hẳn implementation<br/>(service contract, tối ưu hiệu năng,<br/>logic riêng cho project)?"}
    C -- Có --> D["DI – preference cho interface"]
    C -- Không --> P{"Sửa đổi function cũ,<br/>nhiều extension cùng tác động?"}
    P -- Có --> F["Plugin – ưu tiên plugin tới interface"]
```

*Hình 6: Tóm tắt cách lựa chọn giữa Event, DI và Plugin theo nội dung bài*

## Tham khảo

**Tài liệu chính thức**

- [Events and observers](https://developer.adobe.com/commerce/php/development/components/events-and-observers/)
- [Plugins (Interceptors)](https://developer.adobe.com/commerce/php/development/components/plugins)
- [Dependency injection](https://developer.adobe.com/commerce/php/development/components/dependency-injection)
- [The di.xml file](https://developer.adobe.com/commerce/php/development/build/dependency-injection-file)

**Source code**

- [`Magento\Framework\Event\Manager`](https://github.com/magento/magento2/blob/2.4-develop/lib/internal/Magento/Framework/Event/Manager.php)
- [`Magento\Framework\Interception\Interceptor`](https://github.com/magento/magento2/blob/2.4-develop/lib/internal/Magento/Framework/Interception/Interceptor.php)

**Bài viết khác**

- [Refactoring.Guru – Observer](https://refactoring.guru/design-patterns/observer)

**Bài liên quan trong Knowledge Base**

- [Dependency injection configuration](Dependency%20injection%20configuration.md)
- [Object Manager](../Object%20Manager.md)
- [Observer](../SOLID%20principles%20%26%20Patterns%20in%20Magento/Observer.md)
- [Decorator Pattern](../SOLID%20principles%20%26%20Patterns%20in%20Magento/Decorator%20Pattern.md)
