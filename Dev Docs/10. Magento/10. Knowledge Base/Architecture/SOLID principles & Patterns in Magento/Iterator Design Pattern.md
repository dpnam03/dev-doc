---
title: Iterator Pattern
platform: magento
scope: backend
status: current
author: magento-team@
owner: magento-team@
updated: 2026-10-20
tags: [design-pattern, iterator, behavioral]
---

# Iterator Pattern

> **Techstack:** Magento 2.4.x (Adobe Commerce / Magento Open Source)

## 1. Định nghĩa

Mô hình Iterator là một mẫu thiết kế thuộc nhóm behavioral design pattern. Mục đích chính của nó là cung cấp một cách thức để truy cập tuần tự các phần tử của một tập hợp (collection) mà không cần quan tâm đến cấu trúc bên trong của tập hợp đó. Nói cách khác, Iterator cho phép bạn duyệt qua một danh sách các đối tượng một cách có trật tự, mà không cần biết danh sách đó được lưu trữ như thế nào.

## 2. Cách thức hoạt động

Cách thức hoạt động của Iterator Pattern:

- **Iterator Interface:** Định nghĩa các phương thức để truy cập và duyệt qua các phần tử của một tập hợp. Các phương thức phổ biến bao gồm `hasNext()` (kiểm tra xem còn phần tử tiếp theo hay không), `next()` (lấy phần tử tiếp theo), và đôi khi có `current()` (lấy phần tử hiện tại), `rewind()` (đặt con trỏ về vị trí đầu tiên), ...
- **Concrete Iterator:** Implement interface IteratorInterface và chịu trách nhiệm duyệt qua các phần tử của một collection cụ thể. Nó sẽ theo dõi vị trí hiện tại và đảm bảo rằng việc duyệt qua các phần tử diễn ra một cách tuần tự.
- **Collection Interface:** Định nghĩa phương thức để trả về một iterator tương ứng với collection đó. Trong nhiều trường hợp, nó còn có thể có các phương thức để thêm, xóa, sửa đổi các phần tử của collection.
- **Concrete Collection:** Implement CollectionInterface và chứa danh sách các phần tử. Nó sẽ tạo ra các ConcreteIterator tương ứng khi được yêu cầu.
- **Client:** Sử dụng iterator để truy cập các phần tử của một collection mà không cần biết chi tiết về cách collection đó được tổ chức.

## 3. Lợi ích của Iterator Pattern

- **Đơn giản hóa việc duyệt:** Bạn có thể duyệt qua các phần tử của một collection mà không cần quan tâm đến cấu trúc bên trong của nó.
- **Tách biệt logic duyệt:** Logic duyệt được tách ra khỏi collection, giúp code dễ bảo trì và tái sử dụng.
- **Hỗ trợ nhiều kiểu duyệt:** Một collection có thể có nhiều iterator khác nhau, mỗi iterator sẽ thực hiện việc duyệt theo một cách thức khác nhau.
- **Tính mở rộng:** Bạn có thể dễ dàng thêm các collection và iterator mới mà không cần sửa đổi code cũ.
- **Truy cập tuần tự:** đảm bảo việc truy cập các phần tử trong một tập hợp được thực hiện một cách tuần tự.

## 4. Ứng dụng của Iterator Pattern trong Magento

Mặc dù các nguồn không đề cập trực tiếp đến việc sử dụng Iterator Pattern trong Magento, ta có thể suy luận rằng mô hình này được áp dụng trong một số trường hợp:

- **Duyệt qua các Collection:** Magento sử dụng nhiều collection (ví dụ: collection sản phẩm, collection đơn hàng). Iterator Pattern có thể được sử dụng để cung cấp cách duyệt các collection này một cách nhất quán, không phụ thuộc vào cách collection được lưu trữ trong bộ nhớ.
- **Duyệt qua các Block trong Layout:** Các block trong layout của Magento có thể được xem như một collection, và Iterator Pattern có thể được sử dụng để duyệt qua các block này khi render một trang.
- **Duyệt qua các Module:** Trong quá trình khởi tạo và cấu hình Magento, có thể sử dụng iterator để duyệt qua danh sách các module, plugins, preference.
- **Duyệt qua các phần tử trong Composite Pattern:** Khi các đối tượng được tổ chức theo dạng cấu trúc cây phân cấp, bạn có thể dùng iterator để duyệt các phần tử trong cấu trúc này (như trong ví dụ Composite Pattern đã đề cập).

```mermaid
classDiagram
    direction TB
    class IteratorAggregate {
        <<interface>>
        +getIterator()
    }
    class Countable {
        <<interface>>
        +count()
    }
    class DataCollection {
        #_items
        +getIterator() ArrayIterator
        +count()
        +load()
    }
    class AbstractDb {
        <<abstract>>
        #_fetchAll(select)
    }
    class ProductCollection
    class OrderCollection
    class ArrayIterator {
        +current()
        +key()
        +next()
        +rewind()
        +valid()
    }
    IteratorAggregate <|.. DataCollection
    Countable <|.. DataCollection
    DataCollection <|-- AbstractDb
    AbstractDb <|-- ProductCollection : gián tiếp
    AbstractDb <|-- OrderCollection : gián tiếp
    DataCollection ..> ArrayIterator : getIterator()
```

*Hình 1: Iterator trong collection của Magento – `Magento\Framework\Data\Collection` implement `\IteratorAggregate`; `getIterator()` gọi `load()` rồi trả về `\ArrayIterator($this->_items)`, nên client chỉ cần `foreach ($collection as $item)` với collection sản phẩm hay đơn hàng*

## 5. Ví dụ

Hãy tưởng tượng bạn có một giỏ hàng (collection) chứa các sản phẩm. Bạn muốn duyệt qua từng sản phẩm trong giỏ hàng để hiển thị chúng. Thay vì phải biết cách giỏ hàng được lưu trữ như thế nào (ví dụ, một mảng, một danh sách liên kết), bạn có thể sử dụng một iterator để truy cập tuần tự từng sản phẩm một.

## Tham khảo

**Tài liệu chính thức**
- [Persistence layer](https://developer.adobe.com/commerce/php/architecture/layers/persistence) – model, resource model và collection
- [PHP Manual – IteratorAggregate](https://www.php.net/manual/en/class.iteratoraggregate.php)

**Source code**
- [`Magento\Framework\Data\Collection`](https://github.com/magento/magento2/blob/2.4-develop/lib/internal/Magento/Framework/Data/Collection.php)
- [`Magento\Framework\Data\Collection\AbstractDb`](https://github.com/magento/magento2/blob/2.4-develop/lib/internal/Magento/Framework/Data/Collection/AbstractDb.php)

**Bài viết khác**
- [Refactoring.Guru – Iterator](https://refactoring.guru/design-patterns/iterator)

**Bài liên quan trong Knowledge Base**
- [Iterator – duyệt dữ liệu lớn](../DB%20%26%20Data%20Object/iterator.md)
- [Composite Pattern](Composite%20Pattern.md)
