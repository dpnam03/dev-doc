> Các ví dụ dùng module mẫu `Vendor_Feature` với entity `faq`. Khi áp dụng, thay bằng vendor/module/entity thực tế của project.

## Configuration Section

Với mỗi project, cần có 1 section config trong

Stores > Settings > Configuration > {VENDOR NAME}

Các config liên quan đến logic custom của site do BS làm sẽ được đưa vào section này.

- `<tab>` của vendor chỉ khai báo **1 lần** (thường ở module base/core của vendor). Các module khác chỉ tham chiếu tới tab đó qua `<tab>vendor_name</tab>`.
- Mỗi module có 1 `<section>` riêng, gắn ACL `Vendor_Feature::config` qua thẻ `<resource>` (xem phần [ACL](#acl)).
- Khai báo đúng scope cho từng field (`showInDefault`, `showInWebsite`, `showInStore`). Không bật scope store cho những config không thể khác nhau theo store view.
- Field chứa thông tin nhạy cảm (API key, secret, password) dùng `type="obscure"` và backend model `Encrypted`.

Cú pháp `etc/adminhtml/system.xml`

```xml
<?xml version="1.0"?>
<config xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:noNamespaceSchemaLocation="urn:magento:module:Magento_Config:etc/system_file.xsd">
    <system>
        <tab id="vendor_name" translate="label" sortOrder="10">
            <label>Vendor Name</label>
        </tab>
        <section id="vendor_feature" translate="label" sortOrder="10" showInDefault="1" showInWebsite="1" showInStore="1">
            <label>Feature</label>
            <tab>vendor_name</tab>
            <resource>Vendor_Feature::config</resource>
            <group id="general" translate="label" sortOrder="10" showInDefault="1" showInWebsite="1" showInStore="1">
                <label>General</label>
                <field id="enabled" translate="label" type="select" sortOrder="10" showInDefault="1" showInWebsite="1" showInStore="1">
                    <label>Enable</label>
                    <source_model>Magento\Config\Model\Config\Source\Yesno</source_model>
                </field>
                <field id="api_key" translate="label" type="obscure" sortOrder="20" showInDefault="1" showInWebsite="1" showInStore="0">
                    <label>API Key</label>
                    <backend_model>Magento\Config\Model\Config\Backend\Encrypted</backend_model>
                    <depends>
                        <field id="enabled">1</field>
                    </depends>
                </field>
            </group>
        </section>
    </system>
</config>
```

Giá trị mặc định khai báo trong `etc/config.xml`, không để code tự xử lý trường hợp config rỗng:

```xml
<?xml version="1.0"?>
<config xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:noNamespaceSchemaLocation="urn:magento:module:Magento_Store:etc/config.xsd">
    <default>
        <vendor_feature>
            <general>
                <enabled>0</enabled>
            </general>
        </vendor_feature>
    </default>
</config>
```

Đọc config: tập trung vào **1 class** `Model/Config.php` của module, không gọi `ScopeConfigInterface` rải rác ở nhiều nơi. Path config có dạng `section/group/field`.

```php
<?php
declare(strict_types=1);

namespace Vendor\Feature\Model;

use Magento\Framework\App\Config\ScopeConfigInterface;
use Magento\Framework\Encryption\EncryptorInterface;
use Magento\Store\Model\ScopeInterface;

class Config
{
    private const XML_PATH_ENABLED = 'vendor_feature/general/enabled';
    private const XML_PATH_API_KEY = 'vendor_feature/general/api_key';

    public function __construct(
        private readonly ScopeConfigInterface $scopeConfig,
        private readonly EncryptorInterface $encryptor
    ) {
    }

    public function isEnabled(?int $storeId = null): bool
    {
        return $this->scopeConfig->isSetFlag(self::XML_PATH_ENABLED, ScopeInterface::SCOPE_STORE, $storeId);
    }

    public function getApiKey(?int $websiteId = null): string
    {
        // Field dùng backend Encrypted nên giá trị lưu trong DB đã mã hóa, cần decrypt khi đọc
        $value = (string)$this->scopeConfig->getValue(self::XML_PATH_API_KEY, ScopeInterface::SCOPE_WEBSITE, $websiteId);

        return $this->encryptor->decrypt($value);
    }
}
```

> Code mẫu dùng constructor property promotion và `readonly` (PHP 8.1+). Với PHP 7.4, khai báo property và gán trong constructor như cách cũ.

## Menu Section

Tương tự với config, các entity được BS phát triển sẽ được tạo ra các section menu riêng để quản lý.

- Menu item trỏ tới trang danh sách/xem entity dùng ACL **view** của entity đó (`Vendor_Feature::faq_view`), không dùng ACL save/delete.
- `action` có dạng `{frontName}/{controller}/{action}`, với `frontName` khai báo trong `etc/adminhtml/routes.xml`.

Cú pháp `etc/adminhtml/menu.xml`

```xml
<?xml version="1.0"?>
<config xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:noNamespaceSchemaLocation="urn:magento:module:Magento_Backend:etc/menu.xsd">
    <menu>
        <add id="Vendor_Feature::menu" title="Feature" translate="title" module="Vendor_Feature"
             sortOrder="30" resource="Vendor_Feature::faq"/>
        <add id="Vendor_Feature::faq_listing" title="Manage FAQ" translate="title"
             module="Vendor_Feature" sortOrder="10" parent="Vendor_Feature::menu"
             action="vendor_feature/faq/index" resource="Vendor_Feature::faq_view"/>
    </menu>
</config>
```

## ACL

Với mỗi một module config sẽ cần tạo một ACL `{Vendor_Feature}::config` dùng trong section `system.xml`. ACL này đặt dưới nhánh **Stores > Settings > Configuration** (`Magento_Config::config`) để hiển thị đúng vị trí trong cây phân quyền của User Role.

Với mỗi một entity sẽ cần tạo tối thiểu 1 bộ ACL gồm `{entity_name}` (product, faq, v.v..), view, save & delete. ID của các ACL con có tiền tố tên entity (`faq_view`, `faq_save`…) để không bị trùng khi module có nhiều entity.

| ACL | Dùng ở đâu |
| --- | --- |
| `Vendor_Feature::config` | `<resource>` của section trong `system.xml` |
| `Vendor_Feature::faq` | Menu cha, nhóm các quyền của entity |
| `Vendor_Feature::faq_view` | `menu.xml`, controller dạng view page (index, edit) |
| `Vendor_Feature::faq_save` | Controller save, mass enable/disable, button Save trên form |
| `Vendor_Feature::faq_delete` | Controller delete, mass delete, button Delete trên form |

Cú pháp `etc/acl.xml`

```xml
<?xml version="1.0"?>
<config xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:noNamespaceSchemaLocation="urn:magento:framework:Acl/etc/acl.xsd">
    <acl>
        <resources>
            <resource id="Magento_Backend::admin">
                <resource id="Vendor_Feature::faq" title="FAQ" translate="title" sortOrder="50">
                    <resource id="Vendor_Feature::faq_view" title="View" translate="title" sortOrder="10"/>
                    <resource id="Vendor_Feature::faq_save" title="Save" translate="title" sortOrder="20"/>
                    <resource id="Vendor_Feature::faq_delete" title="Delete" translate="title" sortOrder="30"/>
                </resource>
                <resource id="Magento_Backend::stores">
                    <resource id="Magento_Backend::stores_settings">
                        <resource id="Magento_Config::config">
                            <resource id="Vendor_Feature::config" title="Feature Section" translate="title" sortOrder="50"/>
                        </resource>
                    </resource>
                </resource>
            </resource>
        </resources>
    </acl>
</config>
```

Mỗi controller admin **bắt buộc** khai báo `ADMIN_RESOURCE` tương ứng. Nếu không khai báo, controller dùng ACL mặc định `Magento_Backend::admin`, tức là mọi user đăng nhập admin đều gọi được.

```php
<?php
declare(strict_types=1);

namespace Vendor\Feature\Controller\Adminhtml\Faq;

use Magento\Backend\App\Action;
use Magento\Framework\App\Action\HttpPostActionInterface;

class Save extends Action implements HttpPostActionInterface
{
    public const ADMIN_RESOURCE = 'Vendor_Feature::faq_save';

    public function execute()
    {
        // ...
    }
}
```

## UI form/listing

Code bằng UI component của magento <https://developer.adobe.com/commerce/frontend-core/ui-components/>

Nếu cần phải custom lại các form/listing kiểu cũ (như catalog price rule, cart rule v.v…) thì cần viết lại các form/listing đó về dạng UI component rồi sau đó mới bắt đầu thêm các customize vào sau.

Cấu trúc file tối thiểu cho 1 entity (tham khảo module core `Magento_Cms`: `cms_block_listing.xml`, `cms_block_form.xml`):

| Mục đích | File |
| --- | --- |
| Trang listing | `view/adminhtml/layout/vendor_feature_faq_index.xml` gọi `<uiComponent name="vendor_feature_faq_listing"/>` |
| Định nghĩa grid | `view/adminhtml/ui_component/vendor_feature_faq_listing.xml` (columns, filters, mass actions, paging) |
| Data source của grid | `etc/di.xml`: khai báo virtual type `Magento\Framework\View\Element\UiComponent\DataProvider\SearchResult` cho bảng, và thêm vào argument `collections` của `Magento\Framework\View\Element\UiComponent\DataProvider\CollectionFactory` |
| Trang form | `view/adminhtml/layout/vendor_feature_faq_edit.xml` gọi `<uiComponent name="vendor_feature_faq_form"/>` |
| Định nghĩa form | `view/adminhtml/ui_component/vendor_feature_faq_form.xml` (fieldset, field, buttons) |
| Data provider của form | `Ui/DataProvider/FaqDataProvider.php` extends `Magento\Ui\DataProvider\AbstractDataProvider` |
| Button Save/Delete/Back | `Block/Adminhtml/Faq/Edit/*Button.php` implements `ButtonProviderInterface` |

Lưu ý phân quyền trong UI component:

- Mass action và button cũng phải gắn ACL (`aclResource` trong listing, kiểm tra `isAllowed()` trong button provider), không chỉ dựa vào `ADMIN_RESOURCE` của controller.
- Mass action dùng `Magento\Ui\Component\MassAction\Filter` để lấy collection theo các dòng được chọn.
