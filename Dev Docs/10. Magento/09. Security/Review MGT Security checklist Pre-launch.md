# Review MGT Security checklist Pre-launch

## List DomainAspect

**MỤC TIÊU**

Giúp nhận diện tất cả layer quan trọng: server, ứng dụng, admin, API, payment, backup, monitoring, secrets, governance, incident response, business logic.

**Đảm bảo dev checklist không bỏ sót domain nào quan trọng.**

**TIÊU CHUẨN QUỐC TẾ ĐƯỢC SỬ DỤNG**

| Tiêu chuẩn | Giải thích | Lý do chọn |
| --- | --- | --- |
| OWASP ASVS (Application Security Verification Standard) | Bộ tiêu chuẩn chi tiết cho bảo mật ứng dụng web, bao gồm authentication, access control, input validation, session management, logging, API security… | Bao phủ gần như toàn bộ các khía cạnh bảo mật ứng dụng web, đặc biệt phù hợp với Magento/eCommerce. |
| OWASP Top 10 | Liệt kê 10 rủi ro bảo mật phổ biến nhất trên web (XSS, SQLi, misconfiguration, etc.) | Giúp ưu tiên các rủi ro quan trọng, dễ giải thích với non-technical stakeholders. |
| NIST SP 800-x (800-53, 800-34, 800-61, 800-115) | Bộ hướng dẫn bảo mật hệ thống, server, incident response, monitoring, testing, contingency planning | Cung cấp khung chuẩn quốc tế cho server security, monitoring, incident response; bù đắp những khía cạnh mà OWASP không chi tiết. |
| PCI DSS (Payment Card Industry Data Security Standard) | Chuẩn bảo mật dành cho thông tin thẻ thanh toán | Quan trọng cho Magento/eCommerce xử lý payment; đảm bảo compliance nếu site dùng payment gateway. |
| ISO 27001 (Information Security Management) | Quy trình quản lý bảo mật, governance, change management | Hỗ trợ phần policy, governance, audit pre-launch; giúp stakeholder hiểu về compliance / procedure. |

Lưu ý: Không chỉ dùng một bộ tiêu chuẩn vì Magento/eCommerce là hệ thống phức tạp, việc kết hợp nhiều bộ tiêu chuẩn giúp bao phủ toàn diện và tránh bỏ sót rủi ro.

**TỔNG HỢP CÁC DOMAIN / ASPECT**

| Section | Domain / Aspect | Weight | Mapping tiêu chuẩn | Giải thích |
| --- | --- | --- | --- | --- |
| Server Security |  |  | OWASP ASVS 2.2–2.3, Top10 A05, NIST SP 800-53, 800-137 | - Bảo vệ server từ truy cập trái phép, port mở không cần thiết, brute-force SSH.<br>- Đảm bảo HTTPS / HSTS / TLS config để bảo vệ dữ liệu truyền tải.<br>- Patching hệ điều hành / component để phòng lỗ hổng đã biết.<br>- Monitoring/logging giúp phát hiện sớm hành vi bất thường. |
|  | Server Security - Hardening server | High |  |  |
|  | Server Security - Kiểm soát truy cập SSH | High |  |  |
|  | Server Security - Firewall | High |  |  |
|  | Server Security - Ports | Medium |  |  |
|  | Server Security - HTTPS / HSTS | High |  |  |
|  | Server Security - Patching | High |  |  |
|  | Server Security - Monitoring / Logging | Medium |  |  |
| Application Security |  |  | OWASP ASVS 5.x, Top10 A01/A03/A05 | - Magento phụ thuộc nhiều module; lỗ hổng trong extension có thể dẫn đến backdoor hoặc data leak.<br>- Input validation/sanitization tránh XSS, SQLi, CSRF.<br>- Security headers / CSP giúp chống clickjacking, MIME sniffing, XSS. |
|  | Application Security - Kiểm soát module / 3rd-party extension | High |  |  |
|  | Application Security - Security headers | Medium |  |  |
|  | Application Security - CSP | Medium |  |  |
|  | Application Security - Input validation | High |  |  |
| Authentication & Access Control |  |  | OWASP ASVS 2.1–2.2, Top10 A07 | - Admin panel là mục tiêu tấn công chính.<br>- Kiểm soát mật khẩu, 2FA, session timeout, cookie security, role-based access. |
|  | Authentication & Access Control - Password | High |  |  |
|  | Authentication & Access Control - 2FA | High |  |  |
|  | Authentication & Access Control - Session management | High |  |  |
|  | Authentication & Access Control - Role & permission | High |  |  |
| Input Validation & Data Security |  |  | OWASP ASVS 5.1–5.3, Top10 A01/A03, PCI DSS 3.5–3.7 | - Ngăn SQLi, XSS, CSRF, file upload abuse.<br>- Bảo vệ thông tin nhạy cảm (PII, payment info) cả at-rest và in-transit. |
|  | Input Validation & Data Security - Data validation / sanitization | High |  |  |
|  | Input Validation & Data Security - File upload security | High |  |  |
|  | Input Validation & Data Security - Sensitive data encryption | High |  |  |
| Dependency & Patch Management |  |  | OWASP ASVS 1.1, Top10 A06, NIST SP 800-115 | - Lỗ hổng trong core Magento hoặc module cũ là rủi ro lớn.<br>- Dev checklist đã bao gồm update Magento / extensions / Varnish / PHP / Redis, nhưng cần CVE scan thường xuyên. |
|  | Dependency & Patch Management - Magento / module versioning | High |  |  |
|  | Dependency & Patch Management - CVE scan | High |  |  |
|  | Dependency & Patch Management - Package scanning | Medium |  |  |
| Backup & Recovery |  |  | OWASP ASVS 14.5, NIST SP 800-34 | - Dữ liệu eCommerce quan trọng, cần backup incremental & full.<br>- Thử restore để đảm bảo backup hoạt động thực tế. |
|  | Backup & Recovery - Database / file backup | High |  |  |
|  | Backup & Recovery - Restore verification | High |  |  |
| Monitoring & Logging |  |  | OWASP ASVS 14.6, NIST SP 800-137 | - Giám sát hành vi admin, module; phát hiện sớm hành vi bất thường.<br>- Dev checklist có log review, nhưng chưa có alert automation → Partially. |
|  | Monitoring & Logging - Admin action log | Medium |  |  |
|  | Monitoring & Logging - Anomaly detection | High |  |  |
|  | Monitoring & Logging - Automated alerting | Medium |  |  |
| API & Payment Security |  |  | OWASP ASVS 9.x, Top10 A07, PCI DSS 4.0 | - API và thanh toán là nguồn dữ liệu nhạy cảm.<br>- Dev checklist đã có hướng dẫn auth API, redirect payment, nhưng cần review rate limiting & abuse prevention. |
|  | API & Payment Security - API authentication | High |  |  |
|  | API & Payment Security - Payment redirect | High |  |  |
|  | API & Payment Security - Rate limiting | High |  |  |
| Secrets Management |  |  | OWASP ASVS 5.1, PCI DSS 3.5–3.7, NIST SP 800-57 | - API keys, DB passwords, config secrets → cần mã hóa & quản lý tập trung. |
|  | Secrets Management - Store secrets securely | High |  |  |
|  | Secrets Management - Key rotation | High |  |  |
| Security Governance / Policy |  |  | OWASP ASVS 1.2–1.4, ISO 27001 A.5/A.6 | - Pre-launch dev checklist phải có quy trình, audit, approval để giảm rủi ro con người. |
|  | Security Governance / Policy - Policy | Medium |  |  |
|  | Security Governance / Policy - Change management | Medium |  |  |
|  | Security Governance / Policy - Audit | Medium |  |  |
|  | Security Governance / Policy - Compliance | Medium |  |  |
| Incident Response / Recovery |  |  | OWASP ASVS 14.3–14.4, NIST SP 800-61, PCI DSS 12.10 | - Site có thể bị hack ngay cả khi đã patch → cần kế hoạch ứng phó. |
|  | Incident Response / Recovery - Incident response plan | High |  |  |
|  | Incident Response / Recovery - Roles | High |  |  |
|  | Incident Response / Recovery - Timeline | High |  |  |
| Business Logic / Functional Security |  |  | OWASP ASVS 4.2 / 5.1, Top10 A01/A05 | - Ecommerce system có coupon, order, API custom → cần kiểm soát hành vi bất thường. |
|  | Business Logic / Functional Security - Logic abuse prevention | High |  |  |
|  | Business Logic / Functional Security - API misuse | High |  |  |
|  | Business Logic / Functional Security - Coupon / order abuse | Medium |  |  |
| Security Testing beyond scanning |  |  | OWASP ASVS 1.1–1.2, NIST SP 800-115 | - Auto scan (MageReport, Sansec) không phát hiện hết → cần test bổ sung. |
|  | Security Testing beyond scanning - Pentest | High |  |  |
|  | Security Testing beyond scanning - Fuzzing | Medium |  |  |
|  | Security Testing beyond scanning - Stress / load testing | Medium |  |  |

## Mapping Checklist & Tổng hợp

| Configuration | Checkpoints | Domain/Aspect | Note |
| --- | --- | --- | --- |
| SERVER | Whitelist IP for SSH access | Server Security - Kiểm soát truy cập SSH |  |
|  | Use key for SSH and disable login SSH via password | Server Security - Kiểm soát truy cập SSH |  |
|  | Review SSH log to find and block IPs that try to access, and set up fail2ban to automatically block them | Server Security - Kiểm soát truy cập SSH |  |
|  |  | Server Security - Monitoring / Logging |  |
|  | Avoid opening multiple ports on server (80, 443 and 22 ports are sufficient for SSH), whitelist IP is required when opening other ports | Server Security - Ports |  |
|  | Header response needs to include:<br>- x-frame-options:SAMEORIGIN to block clickjacking exploits<br>- x-content-type-options: nosniff to prevent MIME type sniffing vulnerabilities<br>- x-xss-protection1; mode=block defend against Cross-Site Scripting (XSS) attacks<br>https://i.imgur.com/OYxBy4Q.png | Application Security - Security headers |  |
|  |  | Application Security - CSP | gián tiếp liên quan đến clickjacking/XSS |
|  | - Enable HTTP Strict Transport Security to avoid MITM | Server Security - HTTPS / HSTS |  |
|  | Launching the entire site over HTTPs | Server Security - HTTPS / HSTS | Server Security - HTTPS / HSTS |
|  | Use only secure communications protocol (SSH/SFTP/HTTPS) to manage files, and disable FTP. | Server Security - Kiểm soát truy cập SSH |  |
|  |  | Server Security - HTTPS / HSTS |  |
|  | Magento includes .htaccess files to protect system files when using the Apache web server. | Application Security - Security headers |  |
|  | Keep the system up to date, and immediately install patches when new security issues are discovered. | Server Security - Patching |  |
|  | Closely monitor any issues that are reported for software components used by your Magento installation, including the operating system, MySQL database, PHP, Redis (if used), Apache or Nginx, Memcached, Solr, and any other components in your specific configuration. | Dependency & Patch Management - CVE scan |  |
|  |  | Dependency & Patch Management - Package scanning |  |
|  | Check if DMARC record is enabled | API & Payment Security - Payment redirect | gián tiếp qua email spoofing protection |
|  |  | Security Governance / Policy - Compliance |  |
| SERVER APPLICATIONS | Make sure that all applications running on the server are secure. | Server Security - Hardening server |  |
|  | Hide information about server version in response https://i.imgur.com/AxAg9nq.png | Server Security - Hardening server |  |
|  | Hide information about PHP version in response https://imgur.com/PKES05H | Server Security - Hardening server |  |
|  | Update the running service to the latest version compatible with the site's code version. | Server Security - Patching |  |
|  |  | Dependency & Patch Management - Package scanning |  |
|  | Avoid running other software on the same server as Magento, especially if it is accessible from the Internet. Vulnerabilities in blog applications such as Wordpress can expose private information from Magento. Install such software on a separate server or virtual machine. | Server Security - Hardening server |  |
|  |  | Business Logic / Functional Security - Logic abuse prevention | Tách môi trường giảm rủi ro lây nhiễm chéo |
|  | Check Varnish cache version. If Varnish is in this list of risky versions, need to upgrade to a secured one<br>Details: https://varnish-cache.org/security/VSV00016.html#vsv00016 <br>CVE rating: https://www.cve.org/CVERecord?id=CVE-2025-47905 | Dependency & Patch Management - Package scanning |  |
|  |  | Dependency & Patch Management - CVE scan |  |
| ADVANCED TECHNIQUES | Automate the deployment process, if possible, and use private keys for data transfer. | Secrets Management - Store secrets securely |  |
|  |  | Security Governance / Policy - Change management | CI/CD, release control |
|  | Limit access to the Magento Admin by updating the whitelist with the IP address of each computer that is authorized to use the Admin and Magento Connect downloader. | Application Security - Security headers | Chỉ trong trường hợp rule áp dụng ở layer application |
|  |  | Server Security - Firewall | Trường hợp hạn chế truy cập từ network |
|  |  | Authentication & Access Control - Role & permission | Giới hạn quyền truy cập admin |
|  | Do not install extensions directly on a production server. | Security Governance / Policy - Change management |  |
|  | Use two-factor authorization for Admin logins. There are several extensions available that provide additional security by requiring an additional passcode that is generated on your phone, or a token from a special device. | Authentication & Access Control - 2FA |  |
|  | Review your server for “development leftovers.” Make sure there are no accessible log files, publicly visible .git directories, tunnels to execute SQL, database dumps, phpinfo files, or any other unprotected files that are not required, and that might be used in an attack. | Server Security - Hardening server |  |
|  |  | Application Security - Kiểm soát module / 3rd-party extension | Khi để lộ file chứa thông tin nhạy cảm |
|  | Limit outgoing connections to only those that are required, such as for a payment integration. | Server Security - Firewall |  |
|  |  | API & Payment Security - Payment redirect | Liên quan traffic thanh toán ra ngoài |
|  | Use a Web Application Firewall to analyze traffic and discover suspicious patterns, such as credit card information being sent to an attacker. | Monitoring & Logging - Anomaly detection |  |
|  |  | Monitoring & Logging - Automated alerting |  |
|  |  | Server Security - Firewall |  |
|  | Avoid directing SQL queries in the code with passing parameters received from the user. If necessary, reformat the parameters before passing them into the query | Input Validation & Data Security - Data validation / sanitization |  |
|  |  | Business Logic / Functional Security - Logic abuse prevention |  |
|  | Avoid using modules with encrypted code because their logic cannot be checked (Modules with reputation in market can be take into consideration) | Application Security - Kiểm soát module / 3rd-party extension |  |
|  | Setup authenticate resource for API to return sensitive data (pay attention when checking) | API & Payment Security - API authentication |  |
|  |  | Input Validation & Data Security - Sensitive data encryption | Khi API trả dữ liệu nhạy cảm |
|  | Declare ACL for custom controllers in admin (pay attention when checking) | Authentication & Access Control - Role & permission |  |
|  | Sensitive configuration information should be stored with 'obscure' type (pay attention when checking) | Secrets Management - Store secrets securely |  |
|  |  | Input Validation & Data Security - Sensitive data encryption |  |
| MAGENTO INSTALLATION | Use the latest version of Magento to ensure that your installation includes the most recent security enhancements. | Dependency & Patch Management - Magento / module versioning |  |
|  |  | Dependency & Patch Management - Package scanning |  |
|  | Applying new security patch on a regular basis | Server Security - Patching |  |
|  |  | Dependency & Patch Management - Magento / module versioning |  |
|  | Use a unique, custom Admin URL instead of the default “admin” or the often-used “backend,” Although it will not directly protect your site from a determined attacker, it can reduce exposure to scripts that try to break into every Magento site. (Never leave your valuables in plain sight.) | Authentication & Access Control - Session management | Giảm tấn công brute-force/scan URL |
|  |  | Business Logic / Functional Security - Logic abuse prevention |  |
|  | Block access to any development, staging, or testing systems. Use IP whitelisting and .htaccess password protection. When compromised, such systems can produce a data leak or be used to attack the production system. | Server Security - Firewall |  |
|  |  | Server Security - Hardening server |  |
|  |  | Authentication & Access Control - Role & permission |  |
|  | Use the correct file permissions. Core Magento and directory files should be set to ready only, including app/etc/local.xml files. | Server Security - Hardening server |  |
|  | Install extensions only from trusted sources. Never use paid extensions that are published on torrent or other sites. If possible, review extensions for security issues before installing them. | Application Security - Kiểm soát module / 3rd-party extension |  |
|  |  | Dependency & Patch Management - Package scanning |  |
|  | Ensure that your server and database are automatically backed up to external location. A typical setup requires daily incremental backups, with a full backup on a weekly basis. Make sure to test the backup regularly to verify that it can be restored. | Backup & Recovery - Database / file backup |  |
|  |  | Backup & Recovery - Restore verification |  |
|  | For a large site, simple text file dumps of the database take an unacceptable amount of time to restore. Work with your hosting provider to deploy a professional database backup solution. | Backup & Recovery - Database / file backup |  |
|  | Scan your store monthly on MageReport.com to detect malware and to identify any security patches you may not have deployed. MageReport.com is a highly-regarded service that is available at no charge. | Monitoring & Logging - Anomaly detection |  |
|  |  | Dependency & Patch Management - CVE scan |  |
|  | Scan the site with Sansec.io to make sure there is no vulnerability found | Monitoring & Logging - Anomaly detection |  |
|  |  | Dependency & Patch Management - CVE scan |  |
|  | Unsecure Magmi Data Import Tool , adminer | Application Security - Kiểm soát module / 3rd-party extension |  |
|  |  | Server Security - Hardening server |  |
|  | Set up module action log to track actions in admin | Monitoring & Logging - Admin action log |  |
|  | Take advantage of Magento‘s security-related configuration settings for Admin Security, Password Options, and CAPTCHA. | Authentication & Access Control - Password |  |
|  | Disable "Admin Account Sharing" to prevent an admin account from being logged in by 2 different computers simultaneously<br>https://i.imgur.com/IMFZPNA.png | Authentication & Access Control - Session management | Ngăn login cùng tài khoản từ nhiều máy |
|  | Set up "Admin Session Lifetime" to force admin account logging out after an inactive period of time (Magento default is 900s, which is a reasonable period of time https://i.imgur.com/7mbJeNF.png ) | Authentication & Access Control - Session management |  |
|  | Enable "Add Secret Key to URLs" to avoid CSRF attacks <br>https://i.imgur.com/8mQG8BU.png | Authentication & Access Control - Session management | CSRF mitigation |
|  | Configure "Maximum Login Failures to Lockout Account" and "Lockout Time" to avoid password brute-forcing<br>https://i.imgur.com/Tc3Zo53.png | Authentication & Access Control - Password | Ngăn brute-force |
|  | Enable "Login is Case Sensitive" to force inputting the right uppercase and lowercase letter format<br>https://i.imgur.com/mE8XiFz.png | Authentication & Access Control - Password |  |
|  | Disable dangerous PHP functions (by checking disable_functions in phpinfo): pcntl_alarm,pcntl_fork,pcntl_waitpid,pcntl_wait,pcntl_wifexited,pcntl_wifstopped,pcntl_wifsignaled,pcntl_wifcontinued,pcntl_wexitstatus,pcntl_wtermsig,pcntl_wstopsig,pcntl_signal,pcntl_signal_get_handler,pcntl_signal_dispatch,pcntl_get_last_error,pcntl_strerror,pcntl_sigprocmask,pcntl_sigwaitinfo,pcntl_sigtimedwait,pcntl_exec,pcntl_getpriority,pcntl_setpriority,pcntl_async_signals,pcntl_unshare,proc_open,show_source,system,shell_exec,passthru,exec,popen | Server Security - Hardening server |  |
|  | Scan code by Sucuri or other similar security scanners | Security Testing beyond scanning - Pentest |  |
|  | Setup WAF | Server Security - Firewall |  |
|  | Block malicious requests (setup ModSecurity https://github.com/SpiderLabs/ModSecurity + coreruleset https://github.com/coreruleset/coreruleset) | Server Security - Firewall |  |
|  | Apply CSP to authorize 3rd-party scripts that can load on site | Application Security - CSP |  |
|  | Use form_key and validate form_key for forms that import data to database (pay attention when checking) | Input Validation & Data Security - Data validation / sanitization |  |
|  | Config Cookie Domain matches the site domain to avoid subdomains being able to read cookies from other sites. | Authentication & Access Control - Session management |  |
|  | Data before being saved to the database needs to be validated and reformatted to remove all dangerous elements. | Input Validation & Data Security - Data validation / sanitization |  |
|  | Online payment should redirect to payment site to make payment | API & Payment Security - Payment redirect |  |
|  | API needs to have auth mechanism for sensitive information (customer, order,...) | API & Payment Security - API authentication |  |
|  | Review access log to see if there is anything unusual | Monitoring & Logging - Anomaly detection |  |
|  | When displaying html content, data needs to be validated and reformatted to avoid XSS. | Input Validation & Data Security - Data validation / sanitization |  |
|  | Check file type against the type that is allowed to be uploaded in code when uploading new files (pay attention when checking) | Input Validation & Data Security - File upload security |  |
|  | Check CosmicSting (CVE-2024-34102) vulnerability:<br>https://sansec.io/research/cosmicsting <br>https://www.vicarius.io/vsociety/posts/cosmicsting-critical-unauthenticated-xxe-vulnerability-in-adobe-commerce-and-magento-cve-2024-34102 <br>If site is exposed to this vulnerability, need to follow this recovery plan here | Dependency & Patch Management - CVE scan | Follow recovery plan if site exposed |
| SECURITY REVIEW | Check periodically for unauthorized Admin users. | Authentication & Access Control - Role & permission |  |
| 3RD-PARTY MODULES REVIEW | Ref: https://sansec.io/research/license-backdoor <br><br>Check the following 3rd-party modules to detect backdoor script:<br>Tigren        Ajaxsuite<br>Tigren        Ajaxcart<br>Tigren        Ajaxlogin<br>Tigren        Ajaxcompare<br>Tigren        Ajaxwishlist<br>Tigren        MultiCOD<br>Meetanshi        ImageClean<br>Meetanshi        CookieNotice<br>Meetanshi        Flatshipping<br>Meetanshi        FacebookChat<br>Meetanshi        CurrencySwitcher<br>Meetanshi        DeferJS<br>MGS        Lookbook<br>MGS        StoreLocator<br>MGS        Brand<br>MGS        GDPR<br>MGS        Portfolio<br>MGS        Popup<br>MGS        DeliveryTime<br>MGS        ProductTabs<br>MGS        Blog | Application Security - Kiểm soát module / 3rd-party extension | Phát hiện backdoor hoặc module nguy hiểm |
| SECRET DETECTION | Scan all requests sent from the website and run record file through Scan-har | Monitoring & Logging - Anomaly detection | Kiểm tra hành vi bất thường từ request |
| DEPENDENCY SCANNING | Scan the packages currently used by the site and report any security issues found.<br>Using these commands to scan commits and main branches<br>scan:commit<br>scan:branch<br>(tag @CI/CD bot in Mattermost channel of project - Project must set up CI/CD already) | Dependency & Patch Management - Package scanning | CI/CD scan, đảm bảo module/version an toàn |

| Tiêu chí | Weight | Count checkpoints |
| --- | --- | --- |
| API & Payment Security - API authentication | High | 2 |
| API & Payment Security - Payment redirect | High | 3 |
| API & Payment Security - Rate limiting | High | 0 |
| Application Security - CSP | High | 2 |
| Application Security - Input validation | Medium | 0 |
| Application Security - Kiểm soát module / 3rd-party extension | Medium | 5 |
| Application Security - Security headers | High | 3 |
| Authentication & Access Control - 2FA | High | 1 |
| Authentication & Access Control - Password | High | 3 |
| Authentication & Access Control - Role & permission | High | 4 |
| Authentication & Access Control - Session management | High | 5 |
| Backup & Recovery - Database / file backup | High | 2 |
| Backup & Recovery - Restore verification | High | 1 |
| Business Logic / Functional Security - API misuse | High | 0 |
| Business Logic / Functional Security - Coupon / order abuse | High | 0 |
| Business Logic / Functional Security - Logic abuse prevention | Medium | 3 |
| Dependency & Patch Management - CVE scan | High | 5 |
| Dependency & Patch Management - Magento / module versioning | High | 2 |
| Dependency & Patch Management - Package scanning | Medium | 6 |
| Incident Response / Recovery - Incident response plan | High | 0 |
| Incident Response / Recovery - Roles | High | 0 |
| Incident Response / Recovery - Timeline | High | 0 |
| Input Validation & Data Security - Data validation / sanitization | High | 4 |
| Input Validation & Data Security - File upload security | High | 1 |
| Input Validation & Data Security - Sensitive data encryption | High | 2 |
| Monitoring & Logging - Admin action log | Medium | 1 |
| Monitoring & Logging - Anomaly detection | High | 5 |
| Monitoring & Logging - Automated alerting | Medium | 1 |
| Secrets Management - Key rotation | High | 0 |
| Secrets Management - Store secrets securely | High | 2 |
| Security Governance / Policy - Audit | Medium | 0 |
| Security Governance / Policy - Change management | Medium | 2 |
| Security Governance / Policy - Compliance | Medium | 1 |
| Security Governance / Policy - Policy | Medium | 0 |
| Security Testing beyond scanning - Fuzzing | High | 0 |
| Security Testing beyond scanning - Pentest | Medium | 1 |
| Security Testing beyond scanning - Stress / load testing | Medium | 0 |
| Server Security - Firewall | High | 6 |
| Server Security - Hardening server | High | 9 |
| Server Security - HTTPS / HSTS | High | 3 |
| Server Security - Kiểm soát truy cập SSH | Medium | 4 |
| Server Security - Monitoring / Logging | High | 1 |
| Server Security - Patching | High | 3 |
| Server Security - Ports | Medium | 1 |

| Section | Số lượng checkpoint |
| --- | --- |
| Server Security | 27 |
| Authentication & Access Control | 13 |
| Dependency & Patch Management | 13 |
| Application Security | 10 |
| Monitoring & Logging | 7 |
| Input Validation & Data Security | 7 |
| API & Payment Security | 5 |
| Backup & Recovery | 3 |
| Security Governance / Policy | 3 |
| Business Logic / Functional Security | 3 |
| Secrets Management | 2 |
| Security Testing beyond scanning | 1 |

## Đánh giá & Recommended

**ĐÁNH GIÁ VỀ SECTIONS**

-  Các section như Server Security, Authentication & Access Control, Dependency & Patch Management, Application Security được cover bởi nhiều checkpoint, thể hiện coverage tốt.
- Các section còn lại có số lượng checkpoint ít hơn, đặc biệt Secrets Management, Security Testing beyond scanning, Backup & Recovery, Incident Response, cần xem xét bổ sung checkpoint để tăng coverage

ĐÁNH GIÁ THEO  CÁC TIÊU CHÍ BẢO MẬT ĐƯỢC COVER BỞI CÁC CHECKPOINT

| Các tiêu chí chưa được cover hoặc cover rất hạn chế | Có 8 tiêu chí trọng số High nhưng chưa có checkpoint nào cover ==> suggest ưu tiên cao nhất bổ sung actions để cover | (1) | Recommended actions |
| --- | --- | --- | --- |
|  | Có 13 tiêu chí chỉ được cover bởi 1 checkpoint hoặc weighted Medium nhưng chưa có checkpoint nào cover ==> cân nhắc bổ sung thêm | (2) | Recommended actions |
|  | Nhóm này là ưu tiên xem xét bổ sung checkpoint để tăng coverage cho checklist. Các đánh giá chi tiết và các recommended actions được trình bày trong sheet kèm theo. |  |  |
| Các tiêu chí còn lại | Đều được cover bởi ít nhất 2 checkpoint. |  |  |
|  | Cho thấy checklist đã bao phủ đa phần các domain, tuy nhiên cần xác định xem các checkpoint có đủ depth và scope chưa (không nằm trong phạm vi đánh giá hiện tại). |  |  |

**LƯU Ý**

Phần đánh giá này chỉ dựa trên số lượng checkpoint cover tiêu chí và weighted, không đánh giá độ sâu, hiệu quả hay mức độ technical của từng checkpoint.

Recommended actions cho các tiêu chí chưa cover hoặc cover ít đã được tổng hợp trong 2 bảng bên, bao gồm gợi ý checkpoint bổ sung và hành động cụ thể, nhằm tăng coverage checklist và đảm bảo rủi ro được quản lý đầy đủ.

**SUGGEST ACTIONS VỚI CÁC TIÊU CHÍ (1)**

| Tiêu chí (High, chưa có checkpoint) | Weight | Checkpoint gợi ý | Note / Giải thích |
| --- | --- | --- | --- |
| API & Payment Security - Rate limiting | High | 1. Thêm giới hạn request API per IP hoặc per user (e.g., max 100 requests / 1 phút) | Ngăn brute-force, DDoS, scraping dữ liệu khách hàng |
|  | High | 2. Rate limit các endpoint nhạy cảm: login, checkout, password reset | Giảm rủi ro abuse, bảo vệ server |
|  | High | 3. Throttle admin API access, chỉ cho IP whitelist | Giảm rủi ro API bị tấn công từ ngoài |
| Business Logic / Functional Security - API misuse | High | 1. Validate các request API về user role & permissions | Ngăn user truy cập endpoint không được phép |
|  | High | 2. Kiểm tra giá trị input trên API (discount, points, loyalty) | Ngăn tấn công logic exploit |
|  | High | 3. Audit API calls để phát hiện pattern bất thường | Logging + anomaly detection |
| Business Logic / Functional Security - Coupon / order abuse | High | 1. Giới hạn số lượng coupon / discount code có thể áp dụng 1 user | Ngăn duplicate / exploit coupon |
|  | High | 2. Validate order tổng giá trị trước khi approve | Ngăn tăng giá trị hoặc giảm giá bất hợp pháp |
|  | High | 3. Thêm threshold / rate limiting cho đặt hàng / checkout | Ngăn spam hoặc abuse hệ thống order |
| Incident Response / Recovery - Incident response plan | High | 1. Xây dựng IR plan gồm bước detect, contain, eradicate, recover | Cấu trúc chuẩn ISO 27035 / NIST |
|  | High | 2. Định nghĩa kênh thông báo sự cố (email, Slack, pager) | Giúp team phản ứng nhanh |
|  | High | 3. Lập checklist bước restore backup, kiểm tra integrity | Giảm downtime và rủi ro mất dữ liệu |
| Incident Response / Recovery - Roles | High | 1. Gán rõ trách nhiệm cho admin, dev, security analyst | Ai làm gì khi có sự cố? |
|  | High | 2. Tạo bảng phân quyền / escalation matrix | Ai được approve restore, ai được xử lý bug / incident |
| Incident Response / Recovery - Timeline | High | 1. Đặt SLA cho các bước IR: detect, contain, recover | Ví dụ: detect &lt;1h, contain &lt;2h, recover &lt;4h |
|  | High | 2. Ghi lại timestamp tất cả sự kiện trong IR | Giúp audit và cải thiện quy trình |
| Secrets Management - Key rotation | High | 1. Thiết lập chính sách rotate API keys, encryption keys định kỳ (ví dụ 90 ngày) | Giảm rủi ro key leak |
|  | High | 2. Sử dụng vault / secure storage (Hashicorp Vault, AWS KMS, Magento env config) | Không lưu key plain text |
|  | High | 3. Audit lịch sử key sử dụng / access | Phát hiện key bị abuse |
| Security Testing beyond scanning - Fuzzing | High | 1. Fuzz input API, form, upload để tìm crash / unexpected behavior | Test edge case / input anomaly |
|  | High | 2. Tạo automated fuzz script tích hợp CI/CD | Giúp phát hiện sớm vấn đề bảo mật |
|  | High | 3. Thử nghiệm với payload XSS / SQLi / XML injection | Khám phá lỗ hổng chưa được phát hiện bằng scan |

**RECOMMENDED ACTIONS VỚI CÁC TIÊU CHÍ (2)**

| Tiêu chí | Weight | Checkpoint đã có | Recommended Actions | Giải thích |
| --- | --- | --- | --- | --- |
| Application Security - Input validation | Medium | - | 1. Kiểm tra tất cả input từ user (forms, API, file upload) server-side<br>2. Áp dụng whitelist validation, escape output khi render HTML | Một tiêu chí “Input validation” nhưng chưa có checkpoint → hiện site có thể bị XSS/SQLi/logic abuse. Medium weight nên bổ sung để tăng defense-in-depth |
| Authentication & Access Control - 2FA | High | Use two-factor authorization for Admin logins. |  |  |
| Backup & Recovery - Restore verification | High | Ensure server and database backup to external location, test restore |  |  |
| Input Validation & Data Security - File upload security | High | Check file type against allowed type when uploading new files | 1. Thêm size check, content scan (e.g., virus/malware)<br>2. Validate file extension server-side + MIME type | Chỉ check type trong code không đủ. Hacker có thể bypass extension/type, nên cần thêm defense-in-depth |
| Monitoring & Logging - Admin action log | Medium | Set up module action log to track actions in admin | 1. Kết hợp với alerting khi có hành vi bất thường<br>2. Định kỳ review log, archive log | Chỉ có action log chưa đủ nếu không review/alert<br>Recommended bổ sung để giám sát thực sự hữu hiệu |
| Monitoring & Logging - Automated alerting | Medium | Use a Web Application Firewall to analyze traffic and detect suspicious patterns |  |  |
| Security Governance / Policy - Audit | Medium | - | 1. Thiết lập audit trail cho các thay đổi cấu hình, module, user roles<br>2. Định kỳ review audit log (monthly/quarterly) | Audit thiếu → không có cách chứng minh thay đổi hoặc sự kiện admin, dễ bỏ sót rủi ro. Bổ sung để Medium weight tiêu chí được cover |
| Security Governance / Policy - Compliance | Medium | Check if DMARC record is enabled |  |  |
| Security Governance / Policy - Policy | Medium | - | 1. Document chính sách bảo mật: password, access control, patching, backup<br>2. Phổ biến policy cho dev, admin, ops team<br>3. Thiết lập review & update định kỳ (6-12 tháng) | Chỉ có policy chưa đủ; nếu không document và enforce → staff không follow → rủi ro vẫn tồn tại |
| Security Testing beyond scanning - Pentest | Medium | Scan code by Sucuri hoặc security scanners |  |  |
| Security Testing beyond scanning - Stress / load testing | Medium | - | 1. Thiết lập stress/load test cho checkout, API, database<br>2. Sử dụng tool như JMeter, Gatling hoặc Magento Cloud Performance Testing | Chỉ dựa vào scan tự động không đủ, site có thể gặp DoS hoặc performance degradation |
| Server Security - Monitoring / Logging | High | Review SSH log, set up fail2ban | 1. Kết hợp alert khi có brute-force attack<br>2. Định kỳ review log, rotate log, archive | Một checkpoint fail2ban là tốt, nhưng chưa đủ giám sát toàn diện. Alert + log rotation giúp phòng ngừa rủi ro lâu dài |
| Server Security - Ports | Medium | Avoid opening multiple ports (80,443,22) | 1. Thường xuyên audit port mở trên server<br>2. Cấu hình firewall để hạn chế traffic không cần thiết | Checkpoint hiện tại nói về “ports cần hạn chế”, nhưng chưa có audit định kỳ, nên bổ sung |

## OOS Pre-launch

| Tiêu chí | Checkpoint gợi ý | Action (QC đề xuất – đã chuẩn hoá) | Owner / Chuyển giao |
| --- | --- | --- | --- |
| Incident Response / Recovery (Incident response plan) | 1. Xây dựng IR plan gồm các bước: detect, contain, eradicate, recover<br>2. Định nghĩa rõ kênh thông báo sự cố (email, Slack, pager)<br>3. Lập checklist các bước restore backup và kiểm tra tính toàn vẹn (integrity). | Đề xuất xây dựng Incident Response framework ở cấp tổ chức (bao gồm IR plan, communication channel, recovery checklist). | Technical Manager |
| Incident Response / Recovery (Roles) | 1. Gán rõ trách nhiệm cụ thể cho Admin, Dev, Security Analyst<br>2. Tạo bảng phân quyền và ma trận leo thang (escalation matrix). | Đề xuất định nghĩa rõ vai trò, trách nhiệm và escalation matrix như một phần của Incident Response framework. | Technical Manager / Delivery Manager |
| Incident Response / Recovery (Timeline) | 1. Thiết lập SLA cụ thể cho từng giai đoạn IR: detect, contain, recover<br>2. Quy định việc ghi lại timestamp cho tất cả các sự kiện diễn ra trong quá trình IR. | Đề xuất thiết lập SLA và timeline chuẩn cho Incident Response ở level tổ chức | Technical Manager |
| Secrets Management (Key rotation) | 1. Sử dụng vault hoặc các giải pháp lưu trữ bảo mật (Hashicorp Vault, AWS KMS, Magento env config)<br>2. Thực hiện Audit định kỳ lịch sử sử dụng và truy cập key (Access logs). | Đề xuất đưa Secrets Management (storage, rotation, audit) vào Security baseline của platform | Technical Manager / Infra |
| Security Testing beyond scanning (Fuzzing) | 1. Thực hiện Fuzz input đối với API, form, upload để tìm crash hoặc các hành vi bất thường<br>2. Xây dựng kịch bản (automated fuzz script) tích hợp vào quy trình CI/CD<br>3. Thử nghiệm chuyên sâu với các payload XSS, SQLi và XML injection | Chia theo roadmap:<br>- Ngắn hạn: QC/API team thực hiện manual / guided fuzzing ở mức cơ bản<br>- Trung–dài hạn: Đề xuất tích hợp automated fuzzing vào CI/CD khi QC Automation/SDET đủ năng lực | Tech Manager phê duyệt |
| Monitoring & Logging – Admin action log | 1. Kết hợp với alerting khi có hành vi bất thường<br>2. Định kỳ review log, archive log | Đề xuất bổ sung application-level monitoring & alerting (admin actions) như một phần của monitoring strategy tổng thể | Ops / Technical Manager / Security |
| Security Governance / Policy – Audit | 1. Thiết lập audit trail cho các thay đổi cấu hình, module, user roles<br>2. Định kỳ review audit log (monthly/quarterly) | Đề xuất thiết lập Security Governance controls (audit trail, audit process, review cycle) ở cấp tổ chức. | Security Lead / Technical Manager |
| Security Governance / Policy – Policy | 1. Document chính sách bảo mật: password, access control, patching, backup<br>2. Phổ biến policy cho dev, admin, ops team<br>3. Thiết lập review & update định kỳ (6–12 tháng) | Đề xuất ban hành và duy trì Security Policy chính thức cho toàn bộ delivery & operations | Management / Security / Technical Manager |
| Security Testing beyond scanning – Stress / Load testing | 1. Thiết lập stress/load test cho checkout, API, database<br>2. Sử dụng tool như JMeter, Gatling hoặc Magento Cloud Performance Testing | Áp dụng theo giai đoạn:<br>- Pre-launch: optional, risk-based<br>- Post-launch / scale: đưa vào performance & reliability roadmap | Technical Manager / Performance / QC Automation (future) |
| Server Security – Monitoring / Logging | 1. Kết hợp alert khi có brute-force attack<br>2. Định kỳ review log, rotate log, archive | Đề xuất bổ sung server-level monitoring & alerting (brute-force, infra security) như một phần của monitoring strategy tổng thể. | Ops / Infra / Security |
| Server Security – Ports | 1. Thường xuyên audit port mở trên server<br>2. Cấu hình firewall để hạn chế traffic không cần thiết | Đề xuất đưa port audit & firewall hardening vào server security checklist định kỳ | Ops / Infra / Technical Manager |

## Updated Checklist

| Configuration | Checkpoints | Status check | Note |
| --- | --- | --- | --- |
| SERVER | Whitelist IP for SSH access |  |  |
|  | Use key for SSH and disable login SSH via password |  |  |
|  | Review SSH log to find and block IPs that try to access, and set up fail2ban to automatically block them |  |  |
|  | Avoid opening multiple ports on server (80, 443 and 22 ports are sufficient for SSH), whitelist IP is required when opening other ports |  |  |
|  | Header response needs to include:<br>- x-frame-options:SAMEORIGIN to block clickjacking exploits<br>- x-content-type-options: nosniff to prevent MIME type sniffing vulnerabilities<br>- x-xss-protection1; mode=block defend against Cross-Site Scripting (XSS) attacks<br>https://i.imgur.com/OYxBy4Q.png<br>- Enable HTTP Strict Transport Security to avoid MITM |  |  |
|  | Launching the entire site over HTTPs |  |  |
|  | Use only secure communications protocol (SSH/SFTP/HTTPS) to manage files, and disable FTP. |  |  |
|  | Magento includes .htaccess files to protect system files when using the Apache web server. |  |  |
|  | Keep the system up to date, and immediately install patches when new security issues are discovered. |  |  |
|  | Closely monitor any issues that are reported for software components used by your Magento installation, including the operating system, MySQL database, PHP, Redis (if used), Apache or Nginx, Memcached, Solr, and any other components in your specific configuration. |  |  |
|  | Check if DMARC record is enabled |  |  |
| SERVER APPLICATIONS | Make sure that all applications running on the server are secure. |  |  |
|  | Hide information about server version in response https://i.imgur.com/AxAg9nq.png |  |  |
|  | Hide information about PHP version in response https://imgur.com/PKES05H |  |  |
|  | Update the running service to the latest version compatible with the site's code version. |  |  |
|  | Avoid running other software on the same server as Magento, especially if it is accessible from the Internet. Vulnerabilities in blog applications such as Wordpress can expose private information from Magento. Install such software on a separate server or virtual machine. |  |  |
|  | Check Varnish cache version. If Varnish is in this list of risky versions, need to upgrade to a secured one<br>Details: https://varnish-cache.org/security/VSV00016.html#vsv00016 <br>CVE rating: https://www.cve.org/CVERecord?id=CVE-2025-47905 |  |  |
| ADVANCED TECHNIQUES | Automate the deployment process, if possible, and use private keys for data transfer. |  |  |
|  | Limit access to the Magento Admin by updating the whitelist with the IP address of each computer that is authorized to use the Admin and Magento Connect downloader. |  |  |
|  | Do not install extensions directly on a production server. |  |  |
|  | Use two-factor authorization for Admin logins. There are several extensions available that provide additional security by requiring an additional passcode that is generated on your phone, or a token from a special device. |  |  |
|  | Review your server for “development leftovers.” Make sure there are no accessible log files, publicly visible .git directories, tunnels to execute SQL, database dumps, phpinfo files, or any other unprotected files that are not required, and that might be used in an attack. |  |  |
|  | Limit outgoing connections to only those that are required, such as for a payment integration. |  |  |
|  | Use a Web Application Firewall to analyze traffic and discover suspicious patterns, such as credit card information being sent to an attacker. |  |  |
|  | Avoid directing SQL queries in the code with passing parameters received from the user. If necessary, reformat the parameters before passing them into the query |  |  |
|  | Avoid using modules with encrypted code because their logic cannot be checked (Modules with reputation in market can be take into consideration) |  |  |
|  | Setup authenticate resource for API to return sensitive data (pay attention when checking) |  |  |
|  | Declare ACL for custom controllers in admin (pay attention when checking) |  |  |
|  | Sensitive configuration information should be stored with 'obscure' type (pay attention when checking) |  |  |
| MAGENTO INSTALLATION | Use the latest version of Magento to ensure that your installation includes the most recent security enhancements.<br>Applying new security patch on a regular basis |  |  |
|  | Use a unique, custom Admin URL instead of the default “admin” or the often-used “backend,” Although it will not directly protect your site from a determined attacker, it can reduce exposure to scripts that try to break into every Magento site. (Never leave your valuables in plain sight.) |  |  |
|  | Block access to any development, staging, or testing systems. Use IP whitelisting and .htaccess password protection. When compromised, such systems can produce a data leak or be used to attack the production system. |  |  |
|  | Use the correct file permissions. Core Magento and directory files should be set to ready only, including app/etc/local.xml files. |  |  |
|  | Install extensions only from trusted sources. Never use paid extensions that are published on torrent or other sites. If possible, review extensions for security issues before installing them. |  |  |
|  | Ensure that your server and database are automatically backed up to external location. A typical setup requires daily incremental backups, with a full backup on a weekly basis. Make sure to test the backup regularly to verify that it can be restored. |  |  |
|  | For a large site, simple text file dumps of the database take an unacceptable amount of time to restore. Work with your hosting provider to deploy a professional database backup solution. |  |  |
|  | Scan your store monthly on MageReport.com to detect malware and to identify any security patches you may not have deployed. MageReport.com is a highly-regarded service that is available at no charge. |  |  |
|  | Scan the site with Sansec.io to make sure there is no vulnerability found |  |  |
|  | Unsecure Magmi Data Import Tool , adminer |  |  |
|  | Set up module action log to track actions in admin |  |  |
|  | Take advantage of Magento‘s security-related configuration settings for Admin Security, Password Options, and CAPTCHA. |  |  |
|  | Disable "Admin Account Sharing" to prevent an admin account from being logged in by 2 different computers simultaneously<br>https://i.imgur.com/IMFZPNA.png |  |  |
|  | Set up "Admin Session Lifetime" to force admin account logging out after an inactive period of time (Magento default is 900s, which is a reasonable period of time https://i.imgur.com/7mbJeNF.png ) |  |  |
|  | Enable "Add Secret Key to URLs" to avoid CSRF attacks <br>https://i.imgur.com/8mQG8BU.png |  |  |
|  | Configure "Maximum Login Failures to Lockout Account" and "Lockout Time" to avoid password brute-forcing<br>https://i.imgur.com/Tc3Zo53.png |  |  |
|  | Enable "Login is Case Sensitive" to force inputting the right uppercase and lowercase letter format<br>https://i.imgur.com/mE8XiFz.png |  |  |
|  | Disable dangerous PHP functions (by checking disable_functions in phpinfo): pcntl_alarm,pcntl_fork,pcntl_waitpid,pcntl_wait,pcntl_wifexited,pcntl_wifstopped,pcntl_wifsignaled,pcntl_wifcontinued,pcntl_wexitstatus,pcntl_wtermsig,pcntl_wstopsig,pcntl_signal,pcntl_signal_get_handler,pcntl_signal_dispatch,pcntl_get_last_error,pcntl_strerror,pcntl_sigprocmask,pcntl_sigwaitinfo,pcntl_sigtimedwait,pcntl_exec,pcntl_getpriority,pcntl_setpriority,pcntl_async_signals,pcntl_unshare,proc_open,show_source,system,shell_exec,passthru,exec,popen |  |  |
|  | Scan code by Sucuri or other similar security scanners |  |  |
|  | Setup WAF |  |  |
|  | Block malicious requests (setup ModSecurity https://github.com/SpiderLabs/ModSecurity + coreruleset https://github.com/coreruleset/coreruleset) |  |  |
|  | Apply CSP to authorize 3rd-party scripts that can load on site |  |  |
|  | Use form_key and validate form_key for forms that import data to database (pay attention when checking) |  |  |
|  | Config Cookie Domain matches the site domain to avoid subdomains being able to read cookies from other sites. |  |  |
|  | Data before being saved to the database needs to be validated and reformatted to remove all dangerous elements. |  |  |
|  | Online payment should redirect to payment site to make payment |  |  |
|  | API needs to have auth mechanism for sensitive information (customer, order,...) |  |  |
|  | Review access log to see if there is anything unusual |  |  |
|  | When displaying html content, data needs to be validated and reformatted to avoid XSS. |  |  |
|  | Check file type against the type that is allowed to be uploaded in code when uploading new files (pay attention when checking) |  |  |
|  | Check CosmicSting (CVE-2024-34102) vulnerability:<br>https://sansec.io/research/cosmicsting <br>https://www.vicarius.io/vsociety/posts/cosmicsting-critical-unauthenticated-xxe-vulnerability-in-adobe-commerce-and-magento-cve-2024-34102 <br>If site is exposed to this vulnerability, need to follow this recovery plan here |  |  |
| SECURITY REVIEW | Check periodically for unauthorized Admin users. |  |  |
| 3RD-PARTY MODULES REVIEW | Ref: https://sansec.io/research/license-backdoor <br><br>Check the following 3rd-party modules to detect backdoor script:<br>Tigren        Ajaxsuite<br>Tigren        Ajaxcart<br>Tigren        Ajaxlogin<br>Tigren        Ajaxcompare<br>Tigren        Ajaxwishlist<br>Tigren        MultiCOD<br>Meetanshi        ImageClean<br>Meetanshi        CookieNotice<br>Meetanshi        Flatshipping<br>Meetanshi        FacebookChat<br>Meetanshi        CurrencySwitcher<br>Meetanshi        DeferJS<br>MGS        Lookbook<br>MGS        StoreLocator<br>MGS        Brand<br>MGS        GDPR<br>MGS        Portfolio<br>MGS        Popup<br>MGS        DeliveryTime<br>MGS        ProductTabs<br>MGS        Blog |  |  |
| SECRET DETECTION | Scan all requests sent from the website and run record file through Scan-har |  |  |
| DEPENDENCY SCANNING | Scan the packages currently used by the site and report any security issues found.<br>Using these commands to scan commits and main branches<br>scan:commit<br>scan:branch<br>(tag @CI/CD bot in Mattermost channel of project - Project must set up CI/CD already) |  |  |
| MAGENTO INSTALLATION | Should enable rate limit https://developer.adobe.com/commerce/webapi/get-started/rate-limiting/ |  |  |
|  | Should enable input limit https://developer.adobe.com/commerce/webapi/get-started/api-security/ |  |  |
| MAGENTO INSTALLATION | Should disable introspection querying graphql https://developer.adobe.com/commerce/webapi/graphql/usage/introspection-queries/ |  |  |
| MAGENTO INSTALLATION | Review integration permission and unused  https://experienceleague.adobe.com/en/docs/commerce-admin/systems/integrations# |  |  |

| Trạng thái | Ý nghĩa |
| --- | --- |
| Safe | No need more action |
| ToDo | Need more action |
| Pending | No conclusion yet, need detailed reason |
