# BSS Dev Documentation

Tài liệu kỹ thuật của khối Dev, lưu trên Google Drive và chia thành **2 Shared Drive** theo mức truy cập, cộng một khu **Archive** cho tài liệu cũ.

## 2 Shared Drive + Archive

| Shared Drive | Nội dung | Quyền xem | Quyền sửa |
|---|---|---|---|
| 📁 **Dev Docs** | Tài liệu chung, tài liệu từng team, kể cả DevOps | `all-dev@` (Viewer) | Mỗi team sửa thư mục của mình |
| 📁 **Security** | Audit, sự cố bảo mật | `team-leads@`, `devops@`, `security@` | `security@`, `devops@` |
| 📁 **Archive** | Tài liệu cũ, không còn cập nhật | `team-leads@`, `devops@` | `team-leads@` |

> Quyền luôn cấp qua **Google Groups**, không cấp cho từng email. Khi có người vào hoặc nghỉ, chỉ cần sửa group.

---

## Shared Drive 1: Dev Docs

```
Dev Docs/
├── 00. Onboarding/                  ← bắt đầu từ đây: đọc gì trước, setup máy
├── 01. Common/                      ← dùng chung cho mọi team
│   ├── 01. Git/                     (Git flow, training git flow)
│   ├── 02. Clean Code & Review/     (Clean code BS)
│   ├── 03. Dev Environment & CI-CD/ (Docker BSS, denv, validate code – hướng dẫn SỬ DỤNG)
│   ├── 04. Estimate & Audit/        (Audit List – hoạt động audit & tối ưu site)
│   ├── 05. SEO/
│   ├── 06. AI Code Agent/           (Claude Code, AI Code Review, docker security cho agent)
│   ├── 07. Sharing Sessions/        (ACE Docs – danh sách các buổi sharing)
│   ├── 08. Security/                (security chung: checklist website, chống leak dữ liệu, xử lý khi bị tấn công)
│   └── 09. Debug/                   (Debug JS trên Chrome DevTools)
├── 10. Magento/
├── 20. Shopify/
├── 30. Odoo/
├── 40. Mobile App/
├── 50. Nodejs & React/
├── 60. DevOps/                      ← server, CI/CD, docker – mọi team đều cần biết
│   ├── 01. Server/                  (resize instance, move server, Varnish, server knowledge)
│   ├── 02. CI-CD Infra/             (Jenkins, bot Skype, demo Magento, diagram)
│   ├── 03. Docker Images/           (denv nginx config)
│   ├── 04. Monitoring/
│   └── 05. Roadmap/                 (DevOps Plan)
└── 70. WordPress/
```

> `60. DevOps` không theo khung con của các team platform, vì nội dung là hạ tầng chứ không phải dự án.

### Khung con chung cho mọi team

Thư mục của team nào cũng dùng cùng một khung, để ai cũng biết cần tìm ở đâu:

```
10. Magento/
├── 01. Roadmap & Training/          (roadmap, HYVA, PWA, slide sharing)
├── 02. Setup & Environment/         (setup dev site, file config)
├── 03. Coding Standard/
├── 04. Guides/                      (module, integration, theme, DB/config, git & patches)
├── 05. Testing/                     (unit test, integration test)
├── 06. Debug & Performance/         (debug, speed)
├── 07. CI-CD/                       (pipeline riêng của platform)
├── 08. Checklist & Best Practice/   (pre-launch, best practice)
├── 09. Security/                    (security riêng của platform: checklist, secure coding)
└── 10. Knowledge Base/              (chỉ Magento: Architecture, Framework, Design Pattern…)
```

**Đặt tài liệu security ở đâu:**
- Security của riêng một platform (ví dụ MGT Security Checklist, Secure Node.js API) → `09. Security/` của team đó.
- Security dùng cho nhiều platform → `01. Common/08. Security/`.

### Phân quyền sửa

Mỗi team có quyền **Content manager** trên thư mục của team mình:

| Thư mục | Group được sửa |
|---|---|
| `01. Common/` | `tech-leads@` |
| `10. Magento/` | `magento-team@` |
| `20. Shopify/` | `shopify-team@` |
| `30. Odoo/` | `odoo-team@` |
| `40. Mobile App/` | `mobile-team@` |
| `50. Nodejs & React/` | `nodejs-team@` |
| `60. DevOps/` | `devops@` |
| `70. WordPress/` | `wordpress-team@` |

**Đặt tài liệu CI/CD, docker ở đâu:**
- Hướng dẫn **dev sử dụng** → `01. Common/03. Dev Environment & CI-CD/` hoặc `07. CI-CD/` của team.
- Tài liệu **vận hành hạ tầng** → `60. DevOps/`.

---

## Shared Drive 2: Security

Khu hạn chế: chỉ dành cho những gì **không phải dev nào cũng được xem**. Checklist và hướng dẫn security nằm trong `Dev Docs` (theo từng team và `01. Common/08. Security`).

```
Security/
├── 02. Audit/
└── 03. Incidents/
```

---

## Archive

Tài liệu cũ, không còn cập nhật, chỉ giữ để tra cứu. Worker MCP bỏ qua thư mục này.

```
Archive/
├── Common/      (Standard Estimate time & Audit code, Google Shopping, Redirect 302)
├── Magento/     (Old document: M1, patch cũ, PWA research, payment setup cũ…)
└── DevOps/      (pipeline Bitbucket cũ, Bitbucket Changes, Static, validate tool 2020, docker-multiproject 1.5 / 2.3 / 2.4)
```

> `DevOps/docker-multiproject-1.5` có chứa private key và `.env`, vì vậy Archive chỉ mở cho leads và devops.

---

## Quy ước khi thêm tài liệu

1. **Đặt đúng chỗ:** chọn team, rồi chọn thư mục con theo khung `01`–`09`. Tài liệu dùng cho nhiều team thì đặt vào `01. Common/`.
2. **Tên file:** đặt theo chủ đề, **không ghi tên tác giả** trong tên file. Ví dụ dùng `Tang toc Magento.docx` thay cho `Tăng tốc web magento-Toản.docx`.
3. **Đầu mỗi tài liệu** ghi rõ: tác giả, owner hiện tại, ngày cập nhật gần nhất.
4. **Định dạng:** ưu tiên Google Docs, Sheets và Slides. Video và file nén vẫn để được trên Drive.
5. **Không lưu secret:** không để private key, file `.env`, password hay token trong tài liệu. Chỉ ghi chỗ lấy credential (Vault/1Password, mục X).
6. **Tài liệu hết hạn:** chuyển vào `Archive/<team>/`, không xoá.
7. **Muốn tạo thư mục mới ngoài khung:** trao đổi với tech lead trước để giữ cấu trúc thống nhất.
