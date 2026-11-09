# Tổng hợp và phân loại về Magento Security

## Phân loại các kiểu Security

- [Authorization](https://developer.adobe.com/commerce/php/development/security/authorization/)—Control access to pages using different authorization strategies.
- [Brute force attacks](https://developer.adobe.com/commerce/php/development/security/brute-force/)—Identify and protect component functionality vulnerable to brute force attacks.
- [Content security policies](https://developer.adobe.com/commerce/php/development/security/content-security-policies/)—Mitigate against cross-site scripting and related attacks with content security policies.
- [Cross-site request forgery](https://developer.adobe.com/commerce/php/development/security/cross-site-request-forgery/)—Leverage built-in cross-site request forgery (CSRF) protection when developing components.
- [Cross-site scripting](https://developer.adobe.com/commerce/php/development/security/cross-site-scripting/)—Implement cross-site-scripting (XSS) prevention strategies when developing components.
- [Denial of service (DoS) attacks](https://developer.adobe.com/commerce/php/development/security/denial-of-service-attacks/)—Identify and protect component functionality vulnerable to denial of service attacks.
- [File uploads](https://developer.adobe.com/commerce/php/development/security/file-uploads/)—Use out-of-the-box abstraction to safely work with user-uploaded files.
- [Mass assignment](https://developer.adobe.com/commerce/php/development/security/mass-assignment/)—Prevent components from allowing bad actors to override user-editable properties with arbitrary values in HTTP requests.
- [Non-secure functions](https://developer.adobe.com/commerce/php/development/security/non-secure-functions/)—Avoid using PHP functions in components that are known to be vulnerable and exploitable.
- [Sensitive information](https://developer.adobe.com/commerce/php/development/security/sensitive-information/)—Prevent components from exposing sensitive information, like customer passwords, addresses, and dates of birth
- [Server-side request forgery](https://developer.adobe.com/commerce/php/development/security/server-side-request-forgery/)—Follow these strategies to prevent server-side request forgery (SSRF) vulnerabilities in components.
- [Subresource integrity](https://developer.adobe.com/commerce/php/development/security/subresource-integrity/)— Security feature that enables browsers to verify the resources that they fetch.
- [URL library](https://developer.adobe.com/commerce/php/development/framework/url-library/)

## Các kiểu tấn công phổ biến

- **Server attacks:** tấn công vào hạ tầng, ví dụ brute-force SSH, khai thác OS hoặc service (MySQL, Redis, Varnish…) chưa vá.
- **Website defacement:** sau khi chiếm được quyền admin hoặc quyền ghi file, attacker thay đổi nội dung site.
- **Credit card hijacking (Magecart / skimming):** chèn JavaScript vào trang checkout để đánh cắp thông tin thẻ khi khách nhập.
- **Botnetting:** biến server thành bot để gửi spam, tham gia DDoS hoặc đào coin.
- **Remote code execution (RCE):** thực thi code trên server qua lỗ hổng, ví dụ TrojanOrders (CVE-2022-24086), CosmicSting (CVE-2024-34102).
- **Cross-site scripting (XSS):** chèn script vào nội dung hiển thị cho người dùng khác (review, tên sản phẩm, form admin…), thường để đánh cắp session admin.

## Steps for Securing a Magento 2 Website

- [The Security Best Practices Guide](https://experienceleague.adobe.com/en/docs/commerce-operations/implementation-playbook/best-practices/launch/security-best-practices)
- [Security, performance, and data handling](https://developer.adobe.com/commerce/php/best-practices/extensions/security/)
- [Security | Commerce PHP Extensions](https://developer.adobe.com/commerce/php/best-practices/security/)

1. Sign up for security alerts and install all Magento security patches.
2. Add Magento security extensions.
3. Monitor Magento Security Scan.
4. Use a WAF.
5. Enable two-factor authentication (module `Magento_TwoFactorAuth`, có sẵn trong core từ 2.4).

## Checklist bảo mật khi code Magento

Các điểm dev phải tự kiểm tra khi viết code, trước khi gửi review.

### 1. Escape output trong template

Mọi dữ liệu không phải hằng số đều phải escape theo đúng ngữ cảnh. Dùng `$escaper` (có sẵn trong template từ 2.4), không dùng `$block->escapeHtml()` (deprecated).

```php
<h2><?= $escaper->escapeHtml($block->getTitle()) ?></h2>
<a href="<?= $escaper->escapeUrl($block->getLink()) ?>"
   title="<?= $escaper->escapeHtmlAttr($block->getLabel()) ?>">...</a>
<script>
    var name = '<?= $escaper->escapeJs($block->getName()) ?>';
</script>
```

### 2. Controller: HTTP method và form key (CSRF)

- Controller implement `HttpGetActionInterface` hoặc `HttpPostActionInterface` để giới hạn HTTP method. Request POST tới controller frontend sẽ được Magento tự kiểm tra form key.
- Mọi form POST đều có form key: `<?= $block->getBlockHtml('formkey') ?>`.
- Không thực hiện thay đổi dữ liệu (save, delete) trong controller nhận GET.

### 3. Phân quyền controller admin và Web API

- Mỗi controller admin khai báo `public const ADMIN_RESOURCE = 'Vendor_Feature::...';`. Chi tiết xem [Admin config/UI - Best practice](<../04. Guides/DB & Config/Admin config_UI - Best practice_.md>).
- Trong `webapi.xml`, chỉ dùng `<resource ref="anonymous"/>` cho dữ liệu công khai. Dữ liệu customer dùng `self`, dữ liệu quản trị dùng ACL của module.

### 4. Truy vấn database

Không nối chuỗi input vào câu SQL. Dùng collection hoặc `Select` với tham số bind:

```php
$select = $connection->select()
    ->from($this->resource->getTableName('bss_example'))
    ->where('email = ?', $email)
    ->where('store_id IN (?)', $storeIds);
```

### 5. Upload file

- Dùng `Magento\MediaStorage\Model\File\Uploader`, giới hạn đuôi file bằng `setAllowedExtensions()` và kiểm tra cả MIME type.
- Không cho upload file có thể thực thi (`.php`, `.phtml`, `.phar`, `.svg` chứa script…).
- Đổi tên file khi lưu (`setAllowRenameFiles(true)`), không dùng nguyên tên file người dùng gửi lên làm path.

### 6. Dữ liệu nhạy cảm

- Không commit `app/etc/env.php`, file `.env`, key hoặc credential lên git.
- Config nhạy cảm trong admin dùng `type="obscure"` với backend model `Magento\Config\Model\Config\Backend\Encrypted`.
- Không ghi password, token, thông tin thẻ ra log.

### 7. Hàm không an toàn

- Không dùng `eval`, `exec`, `shell_exec`, `system`, `passthru` với dữ liệu từ bên ngoài.
- Không dùng `unserialize()` với dữ liệu bên ngoài. Dùng `Magento\Framework\Serialize\Serializer\Json`.
- Danh sách đầy đủ: [Non-secure functions](https://developer.adobe.com/commerce/php/development/security/non-secure-functions/).

## Tài liệu liên quan

- [MGT Security Checklist](<MGT Security Checklist.md>): checklist bảo mật cho site Magento.
- [Review MGT Security checklist Pre-launch](<Review MGT Security checklist Pre-launch.md>): đánh giá checklist theo các tiêu chuẩn OWASP, NIST, PCI DSS, ISO 27001 và checklist pre-launch cập nhật.
