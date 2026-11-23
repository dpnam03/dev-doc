# kb-check — kiểm tra doc của dev-docs theo rule của Knowledge Base

Công cụ này phục vụ repo `dev-docs`. Nó không đọc, không ghi, không check file hay PR nào của `BS-Knowledge-Base`. Thứ duy nhất mượn từ KB là **bộ rule**: Foundation 0 và các script checker. Mục đích: doc của dev-docs đạt chuẩn KB trước khi được chuyển đi.

## Dùng

Chạy từ thư mục `dev-docs/`.

```bash
# check một hoặc nhiều file, giữ nguyên tên
python3 .kb-check/kb-precheck.py "path/to/file.md" --to "2. Reference Library/Dev"

# check một file dưới tên đích (đổi tên khi chuyển)
python3 .kb-check/kb-precheck.py draft.md --as "2. Reference Library/Dev/Ref_Dev_git-flow_v1.0.md"

# check mọi file .md của PR #1 trong repo dev-docs
python3 .kb-check/kb-precheck.py --dev-pr 1 --to "2. Reference Library/Dev" --summary
```

Script dựng một thư mục tạm có Foundation 0 và đặt file vào đường dẫn đích, chạy check rồi xóa thư mục tạm. Đường dẫn đích quyết định rule nào áp dụng: layer (`Ref`, `OM`, `Foundation`...), folder function (Owner phải có role đúng).

- Exit `0` nghĩa là không có lỗi chặn. Exit `1` nghĩa là còn `FAIL`.
- Dòng `note` là gợi ý readable-shape, không chặn.
- `--summary` in số lỗi theo file và theo rule. Bỏ đi để xem từng dòng lỗi kèm cách sửa.
- `--json` in kết quả dạng JSON. `--no-readable` bỏ qua check readable-shape.

## Check cho PR

Dùng khi một PR của repo `dev-docs` có file `.md` sắp chuyển vào KB. Chỉ check PR **đang mở**: PR đã merge không còn commit nào vượt `origin/master`, script từ chối chạy.

**Bước 1. Xem tổng quan.** Chạy từ thư mục `dev-docs/`, thay `1` bằng số PR:

```bash
python3 .kb-check/kb-precheck.py --dev-pr 1 --to "2. Reference Library/Dev" --summary
```

Script fetch PR về, lấy mọi file `.md` PR thêm, sửa hoặc đổi tên, rồi check từng file. Kết quả mỗi file một dòng, cuối cùng là tổng lỗi theo rule:

```
[FAIL] Dev Docs/.../alpine-js.md  (55 blocking)  B1-sentence:22 B3-bare-url:28 ...
By rule: B3-bare-url:108, B1-sentence:86, ...
13 file(s) · 296 blocking · 201 advisory
```

**Bước 2. Xem chi tiết.** Bỏ `--summary` để có từng dòng lỗi kèm số dòng và cách sửa. Output dài, nên lưu ra file:

```bash
python3 .kb-check/kb-precheck.py --dev-pr 1 --to "2. Reference Library/Dev" > /tmp/pr1-check.txt
```

**Bước 3. Sửa trên nhánh của PR, push, chạy lại Bước 1.** Mỗi lần chạy fetch lại PR nên lấy đúng commit mới nhất.

**Đọc kết quả**
- Exit `0`: không có lỗi chặn, file đạt chuẩn KB. Exit `1`: còn `FAIL`.
- `FAIL` là lỗi chặn. `note` là gợi ý readable-shape, không chặn.
- Dòng đầu cho biết số file `.md` được check và số file khác bị bỏ qua (ảnh, `.docx`, `.pptx`, file bị xóa hoặc chuyển Archive). Các file đó chỉ có thể check tên, không check nội dung.
- Lỗi `C3.1` (tên file) xuất hiện ở mọi file chưa đặt tên theo `Ref_Dev_<section>_<topic>_vX.Y.md`. Đổi tên rồi mới chuyển vào KB, hoặc check riêng từng file bằng `--as`.

**Tùy chọn**
- Đích khác: đổi `--to`, ví dụ `"1. Function Operating Manuals/Dev"` để áp dụng rule của OM.
- Chạy ngoài `dev-docs/`: thêm `--dev-repo /đường/dẫn/dev-docs`.
- `--json` in kết quả dạng JSON, `--no-readable` bỏ qua check readable-shape.

## Chuẩn mà file phải đạt

- Tên file: `[Layer]_[Function]_[Section]_[Topic]_v[Version].[ext]`, ví dụ `Ref_Dev_git-flow_v1.0.md`. Topic viết kebab-case. Đuôi: `md`, `docx`, `xlsx`, `pdf`, `html`.
- Đầu file: tiêu đề một dòng, bảng header 7 field (Owner, Audience, Last reviewed, Review cadence, Version, Linked from, Status), rồi `## Purpose` 2–4 câu.
- Thân bài: heading đánh số 1, 2, 3 và 1.1, 1.2. Câu tối đa 28 từ, đoạn tối đa 5 câu, URL phải bọc thành link, không dùng từ hedging (`may`, `usually`...) hay từ sáo rỗng (`leverage`, `robust`...).
- Cuối file: bảng `# Changelog`.
- Ngôn ngữ (B5): rule gốc của KB là mặc định tiếng Anh, không trộn Anh và Việt trong một doc. Công cụ dev-docs đang **tắt** rule này qua `local-config.json`, nên doc tiếng Việt không bị báo lỗi B5.
- Template: `Ref_Shared_doc-template_v1.1.md` (trong thư mục này).

File `.docx`, `.xlsx`, `.pdf` chỉ bị check tên file. Rule nội dung chỉ chạy trên `.md`.

## Giới hạn

- `Linked from` trỏ tới doc khác của KB. Không có KB để đối chiếu, nên lỗi này chỉ là cảnh báo.
- Không có check bump version (C2.2), changelog của file binary, hay CODEOWNERS. Các check đó cần lịch sử git của KB.

## Tắt hoặc đổi mức độ một rule (override local)

File `local-config.json` chứa các override riêng của dev-docs. Nó được gộp lên trên `config.json` mỗi lần chạy. `config.json` là bản copy của KB và bị `sync.sh` ghi đè, còn `local-config.json` thì không.

Hiện tại file này tắt rule `B5-mixed` (không còn báo lỗi khi doc có tiếng Việt):

```json
{ "severity": { "B5-mixed": "off" } }
```

Mức độ hợp lệ: `blocking` (chặn), `advisory` (chỉ gợi ý), `off` (tắt). Muốn bật lại B5, xóa dòng `B5-mixed` hoặc đổi thành `blocking`. Cùng cách này tắt được rule khác, ví dụ `"B3-bare-url": "advisory"`. Từ cho phép viết hoa (`readable_allow_caps`) cũng đặt được ở đây: thêm khóa `"readable_allow_caps": [...]`, danh sách này **thay thế** hoàn toàn danh sách của KB nên cần liệt kê đủ.

Override này chỉ có tác dụng với công cụ trong dev-docs. PR check thật của KB vẫn áp dụng B5 theo Foundation 0.

## Cập nhật rule

Khi KB đổi rule, kéo bản mới về. Đây là lúc duy nhất công cụ này đọc KB, và nó chỉ copy file rule.

```bash
.kb-check/sync.sh                      # mặc định ../../BS-Knowledge-Base
.kb-check/sync.sh /path/to/BS-Knowledge-Base
```

## Files

| File | Vai trò |
| :-- | :-- |
| `kb-precheck.py` | Entry point. |
| `kb-check.py` | Checker Foundation 0 (copy nguyên từ KB). |
| `pr-check.py`, `readable-check.py`, `readable-banned.txt` | Readable-shape (copy nguyên từ KB). Chỉ dùng hàm readable của `pr-check.py`. |
| `config.json` | Cấu hình severity, cap, allow-list (copy nguyên từ KB). |
| `foundation/` | Foundation 0, nguồn rule. |
| `sync.sh` | Kéo rule mới từ KB. |
