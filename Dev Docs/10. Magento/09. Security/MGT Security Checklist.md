# MGT Security Checklist

## Hiện trạng & Plan QC

Hiện trạng

Đây là nháp để suy nghĩ thôi, các a điền thoải mái vào mấy cột này nhé

**Checklist security làm khi audit**

**Trong quá trình development k có gì control**

**Plan QC**

1. Scan code: Dùng 1 tool quét tất các commit xem có ai push env lên ko (a Hiếu sẽ setup trong chiều nay và quét hết các commit trong lịch sử)

2. Scan Request: Cấp tool tester để review hết các request cho tất cả các dự án có connect vs bên t3:

2.1 Connect vs server (từ server của mình gọi đến bên t3 sẽ bảo mật)

**Long-term solution (expect hoàn thiện trước ngày 31/3)**

a Hiếu tạo tool để tự động log các request ở 2.2 ra file -> tester test, a hiếu review và optimize tool liên tục

Tool scan security code đc tích hợp vào CI/CD, chạy mỗi khi có commit mới

**Update security checklist**

**Expected Output**

Xác định quy trình check security cho dự án (tạm thời làm MGT và SPF theme trước), chia làm đủ các trường hợp:
- Site build mới hoàn toàn
- Site khách có sẵn, maintain or phát triển tính năng mới

Đảm bảo tất cả dự án (mới + đang develop) đều có quy trình kiểm soát security chuẩn trong giai đoạn phát triển.
Phát hiện & ngăn chặn sớm các lỗ hổng bảo mật trước khi đi vào production.
Giảm phụ thuộc vào reactive check khi có issue báo lên.

**Dùng tool nào?**

**Tích hợp vào CI/CD ntn?**

**Brainstorming**

e tham khảo 1 số nguồn (chưa biết legit k :)) ) thì thấy có 1 số practice có thể làm trong gđ development

Secret detection: chắc là hoàn thiện cái plan làm cùng đội QC trên kia là ok nhỉ?

những cái này nếu làm thì chắc có thể tích hợp vào CI CD. 
trong doc của gitlab kia e còn thấy nhiều thứ lắm, k biết có thể áp dụng dc nhưgx gì và gitea thì có áp dụng dc hem

Static code analysis (SAST) https://docs.gitlab.com/user/application_security/sast/

**Dependency Scanning (thấy gitlab có)**

Pull request (PR) review checklist: bắt buộc có security reviewer cho các phần nhạy cảm (auth, payment, external API)

Sau khi xác định dc các action cần làm + tool thì cần có security policy hoặc guideline để xem cái gì là bắt buộc, làm vào thời điểm nào, báo cáo cho ai, ai là người phụ trách

## Checklist Pre-launch | MGT

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

| Safe | No need more action |
| --- | --- |
| ToDo | Need more action |
| Pending | No conclusion yet, need detailed reason |
