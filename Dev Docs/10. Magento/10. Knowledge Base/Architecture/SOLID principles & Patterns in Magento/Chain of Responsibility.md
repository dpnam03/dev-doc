---
title: Chain of Responsibility Pattern
platform: magento
scope: backend
status: current
author: magento-team@
owner: magento-team@
updated: 2026-10-20
tags: [design-pattern, chain-of-responsibility, behavioral]
---

# Chain of Responsibility Pattern

> **Techstack:** Magento 2.4.x (Adobe Commerce / Magento Open Source)

## 1. Tổng quan

Chain of Responsibility là một behavioral design pattern

![Request đi qua một khối kiểm tra phức tạp gồm Authentication, Authorization, Validation, Caching trước khi tới Ordering System](images/chain-of-responsibility/image-01.png)

*Hình 1: Bài toán – mọi bước kiểm tra (authentication, authorization, validation, caching…) dồn vào một khối logic rối trước khi request tới Ordering System*

![Request đi qua chuỗi các Handler nối tiếp nhau; mỗi handler có thể dừng chuỗi hoặc chuyển tiếp tới Ordering System](images/chain-of-responsibility/image-02.png)

*Hình 2: Giải pháp Chain of Responsibility – mỗi Handler xử lý một bước, có thể dừng request hoặc chuyển cho handler kế tiếp*

Chain of Responsibility

Mẫu này khá phổ biến trong Magento, magento thường sử dụng handler như một processor

**Ví dụ – Sử dụng trong việc xử lý các phụ thuộc:**

```php
foreach ($this->relationProcessors as $processor) {
    /**@var $processor RelationInterface*/
    $processor->processRelation($object);
}
```

tương tự

## 2. Cách thức hoạt động

Mục đích của nó là tạo ra một chuỗi các đối tượng xử lý (handler) mà mỗi đối tượng có cơ hội xử lý một yêu cầu. Nếu một đối tượng không thể xử lý yêu cầu, nó sẽ chuyển tiếp yêu cầu cho đối tượng tiếp theo trong chuỗi.

Cách thức hoạt động của Chain of Responsibility Pattern:

1. Client gửi một yêu cầu đến đối tượng xử lý đầu tiên trong chuỗi.
2. Mỗi Handler sẽ kiểm tra xem nó có thể xử lý yêu cầu hay không.
   - Nếu có, handler sẽ xử lý yêu cầu và có thể dừng chuỗi.
   - Nếu không, handler sẽ chuyển tiếp yêu cầu cho handler tiếp theo trong chuỗi.
3. Quá trình này tiếp tục cho đến khi có một handler xử lý được yêu cầu hoặc đến cuối chuỗi.

## 3. Đặc điểm quan trọng

- **Tính linh hoạt:** Các handler có thể được thêm hoặc bớt một cách linh hoạt mà không ảnh hưởng đến các handler khác trong chuỗi.
- **Giảm sự phụ thuộc:** Client không cần biết handler nào sẽ xử lý yêu cầu, giúp giảm sự phụ thuộc giữa client và các handler cụ thể.
- **Trách nhiệm phân tán:** Mỗi handler chỉ tập trung vào một phần cụ thể của yêu cầu, giúp code dễ hiểu và bảo trì hơn.

## 4. Ứng dụng của Chain of Responsibility Pattern trong Magento

Mẫu thiết kế này khá phổ biến trong Magento, Magento thường sử dụng handler như một processor.

- **Xử lý các phụ thuộc:** Magento sử dụng Chain of Responsibility để xử lý các phụ thuộc giữa các module. Ví dụ, khi lưu một order, có thể có nhiều handler khác nhau cần thực thi (ví dụ: xử lý thông tin thanh toán, cập nhật kho, gửi email thông báo...).
- **Validation:** Chain of Responsibility có thể được sử dụng để thực hiện một loạt các validation cho một đối tượng. Mỗi handler sẽ chịu trách nhiệm cho một loại validation cụ thể. Ví dụ trong `Magento\Quote\Model\ValidationRules\QuoteValidationComposite`, mỗi validationRule sẽ validate trên quote và trả về kết quả, nếu có bất kỳ validationRule nào không đúng, sẽ trả về kết quả lỗi.
- **Các Relation Processor:** Magento sử dụng Chain of Responsibility trong việc xử lý các relation giữa các đối tượng. Ví dụ:
  - Mỗi `RelationInterface` là một handler, chịu trách nhiệm xử lý một loại relation cụ thể.
- **Authentication, Authorization, Validation và Caching:** Mô hình này có thể được sử dụng để xử lý một chuỗi các tác vụ như xác thực, ủy quyền, kiểm tra dữ liệu và lưu cache.
- **Plugin Interceptors:** Mặc dù không phải là Chain of Responsibility thuần túy, plugin interceptor trong Magento cũng hoạt động theo một cách tương tự. Các plugin có thể can thiệp vào trước, sau hoặc xung quanh một method, tạo thành một chuỗi các hành động

```mermaid
sequenceDiagram
    participant RM as Sales ResourceModel Order
    participant RC as OrderRelationsComposite (RelationComposite)
    participant H1 as Sales Order Relation
    participant H2 as Tax Sales Order Relation
    participant EM as Event Manager
    RM->>RC: processRelations($order)
    RC->>H1: processRelation($order)
    H1-->>RC: lưu item, payment, status history…
    RC->>H2: processRelation($order)
    H2-->>RC: xử lý order tax (applied taxes)
    RC->>EM: dispatch('sales_order_process_relation')
```

*Hình 3: Khi save order, `VersionControl\AbstractDb` gọi `RelationComposite::processRelations()`; virtualType `OrderRelationsComposite` (di.xml của Magento_Sales và Magento_Tax) lần lượt chuyển `$order` qua từng `RelationInterface::processRelation()`*

## Tham khảo

**Tài liệu chính thức**
- [Plugins (Interceptors)](https://developer.adobe.com/commerce/php/development/components/plugins)
- [The di.xml file](https://developer.adobe.com/commerce/php/development/build/dependency-injection-file) – khai báo mảng handler qua `<argument xsi:type="array">`

**Source code**
- [`Magento\Framework\Model\ResourceModel\Db\VersionControl\RelationComposite`](https://github.com/magento/magento2/blob/2.4-develop/lib/internal/Magento/Framework/Model/ResourceModel/Db/VersionControl/RelationComposite.php)
- [`Magento\Framework\Model\ResourceModel\Db\VersionControl\RelationInterface`](https://github.com/magento/magento2/blob/2.4-develop/lib/internal/Magento/Framework/Model/ResourceModel/Db/VersionControl/RelationInterface.php)
- [`Magento\Sales\Model\ResourceModel\Order\Relation`](https://github.com/magento/magento2/blob/2.4-develop/app/code/Magento/Sales/Model/ResourceModel/Order/Relation.php)
- [`Magento\Quote\Model\ValidationRules\QuoteValidationComposite`](https://github.com/magento/magento2/blob/2.4-develop/app/code/Magento/Quote/Model/ValidationRules/QuoteValidationComposite.php)

**Bài viết khác**
- [Refactoring.Guru – Chain of Responsibility](https://refactoring.guru/design-patterns/chain-of-responsibility)

**Bài liên quan trong Knowledge Base**
- [Composite Pattern](Composite%20Pattern.md)
- [VersionControl](../DB%20%26%20Data%20Object/VersionControl.md)
- [So sánh overview về Event, Plugin & DI](../DI%20%26%20Interceptors/So%20s%C3%A1nh%20overview%20v%E1%BB%81%20Event%2C%20Plugin%20%26%20DI.md)
