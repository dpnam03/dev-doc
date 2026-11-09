# Declarative Schema trong Magento 2

> Áp dụng cho Magento 2.3+ / Adobe Commerce. Tổng hợp từ tài liệu chính thức của Adobe và một số bài viết cộng đồng (xem mục [Tài liệu tham khảo](#tài-liệu-tham-khảo)).

## 1. Declarative schema là gì?

Trước 2.3, mỗi module tự quản lý database bằng các script PHP: `InstallSchema`, `UpgradeSchema`, `InstallData`, `UpgradeData`, `Recurring`. Mỗi phiên bản mới lại thêm một nhánh `version_compare(...)` trong `UpgradeSchema`. Khi upgrade qua nhiều phiên bản, Magento phải chạy lần lượt mọi script trung gian, nên dev phải đọc hiểu từng script để tránh xung đột.

**Declarative schema** đổi cách tiếp cận: thay vì viết *các bước* thay đổi DB, ta **khai báo trạng thái cuối cùng** của DB trong file `etc/db_schema.xml`. Khi chạy `setup:upgrade`, Magento so sánh trạng thái khai báo với DB thực tế và tự sinh DDL để đồng bộ, bỏ qua các bước trung gian thừa.

**Lợi ích:**

- Không cần viết script cho từng version, chỉ sửa XML.
- Bỏ qua các thao tác trung gian dư thừa khi upgrade nhiều version.
- Có thể xóa dữ liệu khi uninstall module.
- Có dry-run để xem trước SQL sẽ chạy.

**Lưu ý:**

- Ở 2.3, declarative schema chưa bắt buộc, nhưng install/upgrade script đang dần bị loại bỏ. **Đã chuyển module sang declarative schema thì không quay lại upgrade script được.**
- Một module **không nên trộn** `db_schema.xml` với `InstallSchema`/`UpgradeSchema`.

## 2. Các thành phần

| Thành phần | Vị trí | Mục đích |
| --- | --- | --- |
| `db_schema.xml` | `<Vendor>/<Module>/etc/db_schema.xml` | Khai báo cấu trúc bảng: column, constraint, index |
| `db_schema_whitelist.json` | `<Vendor>/<Module>/etc/db_schema_whitelist.json` | Ghi lại các bảng, cột, key do declarative schema quản lý. **Bắt buộc để thực hiện được thao tác drop** |
| Data patch | `<Vendor>/<Module>/Setup/Patch/Data/<PatchName>.php` | Thêm hoặc sửa **dữ liệu** (config, attribute, CMS block…) |
| Schema patch | `<Vendor>/<Module>/Setup/Patch/Schema/<PatchName>.php` | Thay đổi schema phức tạp mà XML không diễn tả được: trigger, stored procedure, partition… |

**Thứ tự chạy khi `setup:upgrade`:** áp dụng `db_schema.xml` trước, sau đó mới chạy schema patch và data patch.

## 3. Cấu trúc `db_schema.xml`

```xml
<?xml version="1.0"?>
<schema xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
        xsi:noNamespaceSchemaLocation="urn:magento:framework:Setup/Declaration/Schema/etc/schema.xsd">
    <table name="bss_example" resource="default" engine="innodb" comment="BSS Example Table">
        <column xsi:type="int" name="entity_id" unsigned="true" nullable="false" identity="true" comment="Entity ID"/>
        <column xsi:type="int" name="customer_id" unsigned="true" nullable="true" comment="Customer ID"/>
        <column xsi:type="varchar" name="title" nullable="false" length="255" comment="Title"/>
        <column xsi:type="text" name="content" nullable="true" comment="Content"/>
        <column xsi:type="decimal" name="amount" scale="4" precision="20" unsigned="false" nullable="false" default="0" comment="Amount"/>
        <column xsi:type="smallint" name="is_active" unsigned="true" nullable="false" default="1" comment="Is Active"/>
        <column xsi:type="timestamp" name="created_at" nullable="false" default="CURRENT_TIMESTAMP" on_update="false" comment="Created At"/>
        <column xsi:type="timestamp" name="updated_at" nullable="false" default="CURRENT_TIMESTAMP" on_update="true" comment="Updated At"/>

        <constraint xsi:type="primary" referenceId="PRIMARY">
            <column name="entity_id"/>
        </constraint>
        <constraint xsi:type="foreign" referenceId="BSS_EXAMPLE_CUSTOMER_ID_CUSTOMER_ENTITY_ENTITY_ID"
                    table="bss_example" column="customer_id"
                    referenceTable="customer_entity" referenceColumn="entity_id"
                    onDelete="CASCADE"/>
        <index referenceId="BSS_EXAMPLE_CUSTOMER_ID" indexType="btree">
            <column name="customer_id"/>
        </index>
        <index referenceId="BSS_EXAMPLE_TITLE_CONTENT" indexType="fulltext">
            <column name="title"/>
            <column name="content"/>
        </index>
    </table>
</schema>
```

### 3.1. Node `table`

| Thuộc tính | Mô tả |
| --- | --- |
| `name` | Tên bảng |
| `engine` | `innodb` hoặc `memory` |
| `resource` | Database shard: `default`, `checkout`, `sales` |
| `comment` | Comment của bảng |
| `onCreate` | Trigger migrate dữ liệu từ bảng khác, chỉ chạy khi bảng được tạo mới |

### 3.2. Node `column`

**Các `xsi:type`:** `blob` (blob, mediumblob, longblob), `boolean`, `date`, `datetime`, `decimal`, `float`, `int` (smallint, bigint, tinyint), `json`, `real` (decimal, float, double, real), `smallint`, `text` (text, mediumtext, longtext), `timestamp`, `varbinary`, `varchar`.

| Thuộc tính | Mô tả |
| --- | --- |
| `name` | Tên cột |
| `default` | Giá trị mặc định |
| `nullable` | Cho phép NULL hay không |
| `identity` | Auto increment |
| `unsigned` | Chỉ nhận số không âm |
| `length` | Độ dài cho `char`, `varchar`, `varbinary` |
| `padding` | Kích thước cột integer |
| `precision` / `scale` | Tổng số chữ số / số chữ số sau dấu phẩy (kiểu real, decimal) |
| `on_update` | Với `timestamp`: tự cập nhật khi row thay đổi |
| `onCreate` | Migrate dữ liệu từ cột khác, chỉ chạy khi cột được tạo |
| `disabled` | Vô hiệu hóa hoặc xóa phần tử đã khai báo (dùng để drop phần tử do module khác khai báo) |
| `comment` | Comment của cột |

### 3.3. Node `constraint`

- `xsi:type`: `primary`, `unique`, `foreign`.
- `referenceId`: key nội bộ để mapping trong `db_schema.xml`. Tên thật trong DB do Magento tự sinh.
- Foreign key có thêm `table`, `column`, `referenceTable`, `referenceColumn`, `onDelete` (`CASCADE`, `SET NULL`, `NO ACTION`).
- **Không hỗ trợ `ON UPDATE`** cho foreign key.
- Chỉ tạo được foreign key khi **cả hai bảng đều được khai báo bằng declarative schema**.

### 3.4. Node `index`

- `indexType`: `btree`, `fulltext`, `hash`.

## 4. Whitelist (`db_schema_whitelist.json`)

Whitelist là "sổ ghi" những gì declarative schema đã tạo. Magento **chỉ drop** bảng, cột hoặc key nào **có trong whitelist**. Nhờ vậy, nó không xóa nhầm các phần tử được tạo bằng cách khác, ví dụ từ script cũ hoặc tạo tay.

Generate whitelist:

```bash
bin/magento setup:db-declaration:generate-whitelist --module-name=Vendor_Module
```

**Khi nào phải generate lại:** sau khi tạo bảng, thêm cột, đổi tên bảng hoặc đổi tên cột. Nên generate lại ở mỗi lần release. Các phần tử đã bị xóa khỏi XML **phải giữ lại trong whitelist** cho đến khi chúng thực sự bị drop khỏi DB.

> Whitelist phải được commit cùng module.

## 5. Các thao tác thường gặp

### Tạo bảng

Thêm node `<table>`, rồi generate whitelist và chạy `setup:upgrade`.

### Xóa bảng

Xóa node `<table>` khỏi XML. Bảng **vẫn phải có trong whitelist** thì mới bị drop.

### Đổi tên bảng

Magento **không dùng `RENAME TABLE`** mà tạo bảng mới rồi drop bảng cũ. Muốn giữ dữ liệu thì dùng `onCreate`:

```xml
<table name="new_declarative_table" onCreate="migrateDataFromAnotherTable(declarative_table)">
    ...
</table>
```

- Generate lại whitelist để có cả tên cũ và tên mới.
- Với bảng lớn, cách này chậm. Nên dump bằng `--safe-mode=1` rồi nạp lại dữ liệu bằng data patch.
- **Không hỗ trợ** đổi tên bảng và đổi tên cột trong cùng một lần migration.

### Thêm cột

```xml
<column xsi:type="timestamp" name="date_closed" comment="Date Closed"/>
```

Sau đó generate lại whitelist.

### Xóa cột

- Cột thuộc module của mình: xóa node `<column>`. Cột phải có trong whitelist.
- Cột do **module khác** khai báo: khai báo lại với `disabled="true"`.

```xml
<column xsi:type="int" name="some_column" disabled="true"/>
```

### Đổi kiểu cột

Sửa `xsi:type` và các thuộc tính liên quan, ví dụ đổi `varchar` thành `text`:

```xml
<column xsi:type="text" name="title" nullable="false" comment="Title"/>
```

### Đổi tên cột

Xóa khai báo cũ, thêm cột mới có `onCreate`:

```xml
<column xsi:type="int" name="new_entity_id" unsigned="true" nullable="false"
        onCreate="migrateDataFrom(entity_id)" comment="Entity ID"/>
```

Sau đó generate lại whitelist.

### Thêm cột vào bảng core hoặc bảng của module khác

Khai báo lại `<table name="...">` trong `db_schema.xml` của module mình, chỉ chứa các cột mới. Magento sẽ merge các khai báo lại với nhau.

```xml
<table name="sales_order">
    <column xsi:type="varchar" name="bss_custom_field" nullable="true" length="255" comment="BSS Custom Field"/>
</table>
```

> Module phải `<sequence>` module sở hữu bảng đó trong `module.xml`, để đảm bảo thứ tự load đúng.

### Thêm index hoặc foreign key

```xml
<index referenceId="INDEX_SEVERITY" indexType="btree">
    <column name="severity"/>
</index>

<constraint xsi:type="foreign" referenceId="FL_ALLOWED_SEVERITIES" table="declarative_table"
            column="severity" referenceTable="severities" referenceColumn="severity_identifier"
            onDelete="CASCADE"/>
```

### Xóa foreign key

Xóa node `<constraint>` (key phải có trong whitelist). Nếu key do module khác khai báo thì dùng `disabled="true"`.

### Tạo lại primary key

```xml
<column xsi:type="int" name="new_id_column" unsigned="true" nullable="false" comment="New Entity Id"/>
<constraint xsi:type="primary" referenceId="PRIMARY" disabled="true"/>
<constraint xsi:type="primary" referenceId="NEW_PRIMARY">
    <column name="new_id_column"/>
</constraint>
```

Trong DB, tên key vẫn là `PRIMARY`.

## 6. Data patch và schema patch

`db_schema.xml` **chỉ mô tả cấu trúc**. Muốn insert hay sửa dữ liệu, hoặc làm thay đổi schema phức tạp, thì dùng patch.

### 6.1. Data patch

> Code mẫu dùng constructor property promotion và `readonly`, yêu cầu PHP 8.1+ (Magento 2.4.4+). Với PHP 7.4, khai báo property và gán trong constructor như cách cũ.

```php
<?php
declare(strict_types=1);

namespace Vendor\Module\Setup\Patch\Data;

use Magento\Framework\Setup\ModuleDataSetupInterface;
use Magento\Framework\Setup\Patch\DataPatchInterface;
use Magento\Framework\Setup\Patch\PatchRevertableInterface;

class AddDefaultExampleRows implements DataPatchInterface, PatchRevertableInterface
{
    public function __construct(
        private readonly ModuleDataSetupInterface $moduleDataSetup
    ) {
    }

    public function apply(): self
    {
        $connection = $this->moduleDataSetup->getConnection();
        $connection->startSetup();
        $connection->insertMultiple(
            $this->moduleDataSetup->getTable('bss_example'),
            [
                ['title' => 'First', 'is_active' => 1],
                ['title' => 'Second', 'is_active' => 0],
            ]
        );
        $connection->endSetup();

        return $this;
    }

    public function revert(): void
    {
        $connection = $this->moduleDataSetup->getConnection();
        $connection->startSetup();
        $connection->delete(
            $this->moduleDataSetup->getTable('bss_example'),
            ['title IN (?)' => ['First', 'Second']]
        );
        $connection->endSetup();
    }

    public static function getDependencies(): array
    {
        return [];
    }

    public function getAliases(): array
    {
        return [];
    }
}
```

### 6.2. Schema patch

Cấu trúc giống data patch, nhưng implement `SchemaPatchInterface` và inject `SchemaSetupInterface`. Dùng cho những thay đổi XML không làm được: trigger, stored procedure, partition, raw DDL đặc thù…

### 6.3. Các method

| Method | Ý nghĩa |
| --- | --- |
| `apply()` | Nội dung thay đổi |
| `getDependencies()` (static) | Danh sách class patch phải chạy trước, có thể nằm ở module khác |
| `getAliases()` | Tên cũ của patch, để đổi tên class mà không bị chạy lại |
| `revert()` | Chỉ có khi implement `PatchRevertableInterface`. Hoàn tác lại `apply()` |
| `getVersion()` | Chỉ có khi implement `PatchVersionInterface`. Dùng khi migrate từ upgrade script cũ (xem mục 7) |

### 6.4. Cơ chế chạy

- Patch đã chạy được ghi vào bảng **`patch_list`**, và **mỗi patch chỉ chạy một lần**.
- Patch chưa chạy sẽ được thực thi khi chạy `bin/magento setup:upgrade`.
- Thứ tự chạy dựa trên `getDependencies()`. Các patch độc lập có thể chạy theo thứ tự bất kỳ.
- Muốn chạy lại một patch (chỉ nên làm ở môi trường dev): xóa dòng tương ứng trong `patch_list` rồi chạy `setup:upgrade`.
- **Không revert được từng patch riêng lẻ.** Revert chỉ xảy ra khi uninstall module:

  ```bash
  bin/magento module:uninstall Vendor_Module
  # module không cài qua composer:
  bin/magento module:uninstall --non-composer Vendor_Module
  ```

- Cẩn thận khi `revert()` xóa dữ liệu được tham chiếu bởi foreign key, vì nó có thể kích hoạt `ON DELETE CASCADE`.
- Có thể tạo nhanh khung patch bằng lệnh:

  ```bash
  bin/magento setup:db-declaration:generate-patch [--revertable[=true|false]] [--type[=data|schema]] Vendor_Module PatchName
  ```

## 7. Migrate module cũ (InstallSchema/UpgradeSchema) sang declarative schema

### Bước 1: Chuyển schema script

Magento có Schema Listener Tool để tự sinh `db_schema.xml` từ script cũ:

```bash
bin/magento setup:install --convert-old-scripts=1
# hoặc
bin/magento setup:upgrade --convert-old-scripts=1
```

- Chỉ chạy ở môi trường **dev**, **không chạy ở production mode**.
- Tool chỉ nhận các thao tác DDL đi qua `\Magento\Framework\DB\Adapter\Pdo\Mysql`. **Raw SQL và DDL tự viết bị bỏ qua.**
- DDL trong `Recurring` không được chuyển.
- Sau khi convert, **phải review kỹ** `db_schema.xml` sinh ra và bổ sung bằng tay phần còn thiếu.

### Bước 2: Chuyển data script

`InstallData` và `UpgradeData` **không convert tự động được**. Cần viết lại thành data patch:

1. Tạo khung patch bằng `setup:db-declaration:generate-patch`.
2. Chuyển logic từ từng nhánh `version_compare` sang một patch riêng.
3. Với module **đã release** (đã cài trên site khách), patch phải implement `PatchVersionInterface::getVersion()`, trả về đúng version trong `version_compare` của script cũ. Nếu version module trong DB lớn hơn hoặc bằng version của patch thì patch bị bỏ qua, tránh chạy lại dữ liệu đã có.
   - Nếu `InstallData` không có version để so sánh thì trả về version đầu tiên của module.

```php
use Magento\Framework\Setup\Patch\PatchVersionInterface;

class AddSomeAttribute implements DataPatchInterface, PatchVersionInterface
{
    public static function getVersion(): string
    {
        return '1.0.3'; // version trong version_compare cũ
    }
    // ...
}
```

### Bước 3: Generate whitelist và test

```bash
bin/magento setup:db-declaration:generate-whitelist --module-name=Vendor_Module
bin/magento setup:upgrade --dry-run=1   # xem trước SQL
bin/magento setup:upgrade
```

### Bước 4: Dọn dẹp

- Xóa `InstallSchema.php`, `UpgradeSchema.php`, `InstallData.php`, `UpgradeData.php` sau khi đã chuyển xong.
- Test cả hai kịch bản: **cài mới hoàn toàn** và **upgrade từ version cũ đang chạy trên site**. So sánh cấu trúc bảng sau khi chạy để chắc chắn không bị lệch.

## 8. Dry-run, safe mode, data restore

| Lệnh | Tác dụng |
| --- | --- |
| `bin/magento setup:upgrade --dry-run=1` | Không thay đổi DB, chỉ ghi các câu DDL sẽ chạy vào `var/log/dry-run-installation.log`. Dùng được cả với `setup:install` |
| `bin/magento setup:upgrade --safe-mode=1` | Backup dữ liệu (dump CSV) của các phần tử sắp bị drop trước khi upgrade |
| `bin/magento setup:upgrade --data-restore=1` | Khôi phục dữ liệu từ bản backup của safe mode |

**Cảnh báo khi disable module:** khi module bị disable trong `app/etc/config.php`, `db_schema.xml` của nó không được đọc nữa nhưng whitelist **vẫn được đọc**. Vì vậy `setup:upgrade` có thể **drop bảng của module đó**. Cách xử lý:

1. Sau khi disable module, chạy `setup:upgrade --safe-mode=1` để backup.
2. Khi enable lại module, chạy `setup:upgrade --data-restore=1`.

## 9. Best practices / checklist

- [ ] Mỗi module mới **chỉ dùng** `db_schema.xml` và patch, không dùng `InstallSchema`/`UpgradeSchema`.
- [ ] Mọi cột đều có `comment`; `nullable`, `default`, `unsigned` được khai báo rõ ràng.
- [ ] Generate và commit `db_schema_whitelist.json` mỗi khi thay đổi `db_schema.xml`.
- [ ] Chạy `--dry-run=1` và đọc `var/log/dry-run-installation.log` trước khi deploy thay đổi schema lên staging hoặc production.
- [ ] Đặt `referenceId` theo convention của Magento: `TABLE_COLUMN` cho index, `TABLE_COLUMN_REFTABLE_REFCOLUMN` cho foreign key.
- [ ] Thêm cột vào bảng core: khai báo lại `<table>` trong module của mình và thêm `<sequence>` trong `module.xml`. **Không sửa trực tiếp file core.**
- [ ] Không dùng declarative schema để drop phần tử của module khác nếu không thực sự cần. Nếu cần thì dùng `disabled="true"`.
- [ ] Data patch phải **idempotent** (chạy lại không lỗi, không nhân đôi dữ liệu), dù `patch_list` đã đảm bảo patch chỉ chạy một lần.
- [ ] Không đổi tên class patch đã release. Nếu bắt buộc đổi thì khai báo tên cũ trong `getAliases()`.
- [ ] Bảng lớn: tránh `onCreate="migrateDataFromAnotherTable(...)"`, hãy dùng safe mode kết hợp data patch.
- [ ] Thay đổi đặc thù như trigger, partition hay stored procedure thì làm bằng schema patch, không cố nhét vào XML.

## Tài liệu tham khảo

- Adobe Commerce Developer: [Declarative schema overview](https://developer.adobe.com/commerce/php/development/components/declarative-schema/)
- Adobe Commerce Developer: [Configure declarative schema](https://developer.adobe.com/commerce/php/development/components/declarative-schema/configuration)
- Adobe Commerce Developer: [Develop data and schema patches](https://developer.adobe.com/commerce/php/development/components/declarative-schema/patches)
- Adobe Commerce Developer: [Migrate install/upgrade scripts to declarative schema](https://developer.adobe.com/commerce/php/development/components/declarative-schema/migration-scripts)
- Mage-OS DevDocs: [db_schema.xml](https://devdocs.mage-os.org/docs/main/db_schema_xml)
- Inchoo: [Declarative Schema feature in Magento 2](https://inchoo.net/magento-2/declarative-schema)
- Onilab: [Declarative Schema in Magento 2.3 and Higher](https://onilab.com/blog/declarative-schema-magento-2-3-and-higher)
- Meetanshi: [How to Create db_schema_whitelist.json in Magento 2](https://meetanshi.com/blog/create-db-schema-whitelist-json-in-magento-2/)
