# DCE Feature List Analysis Report

**Analysis Time**: 2025-12-22 05:11:58

**Source File**: DCE_feature_list_update_20251214_v1.xlsx

---

以下為 **DCE_feature_list_update_20251214_v1.xlsx** 的分析結果（以檔內實際資料為準）：

---

## 1) 這個檔案有哪些工作表 (Sheets)？
- **Sheet1**（唯一工作表）

---

## 2) 主要欄位（Columns）有哪些？
Sheet1 共 **10 欄**：

1. `Sr. No.`
2. `Feature`
3. `Requirement Details`
4. `Applies to`
5. `Included in Rel 4`
6. `Status`
7. `Dependency`
8. `Dependency.1`（內容看起來是 *Due Date*）
9. `Remarks`
10. `T Shirt Sizing`

---

## 3) 有多少 features / rows？
- Sheet1 總列數（含空白/分隔列）：**43 rows**
- 以 `Feature` 欄位「有值」視為一筆 feature：**33 個 features（33 rows）**

> 檔案中存在一些「Feature 為空」的列，較像是說明/分隔用列，因此我用 `Feature != NaN` 作為 feature 計數基準。

---

## 4) Top 10 最重要的 Features
檔案沒有明確的「重要度分數」欄位；因此我以 `Sr. No.` 由小到大視為優先序/重要度（前 10 筆）：

| Sr. No. | Feature | Status | Applies to | T Shirt Sizing |
|---:|---|---|---|---|
| 1 | ACL (Access Control List) Permissions (Roles) | QA- In Progress | All OpCos | L |
| 2 | Closed Order Enhancements | QA- In Progress | RAP, RPH | S |
| 3 | Toner Order Enhancements | On Hold | All OpCos | L |
| 4 | Self Registration | On Hold | RNZ, RPH | S |
| 5 | Catalog Creation | On Hold | All OpCos | L |
| 6 | Catalog mapping automation -Public or Customer... | On Hold | All OpCos | XL |
| 7 | Customer Live Inquiry | TBD | All OpCos | TBD |
| 8 | Reporting | On Hold | RNZ, RPH | S |
| 9 | Relocation Enhancement- | To be started | All OpCos | L |
| 10 | Relocation Enhancement- | To be started | All OpCos | M |

---

## 5) Summary chart（摘要圖表）
我做了兩張摘要分佈圖（以 `Feature` 有值的 33 筆為母體）：

- **Status 分佈**（Unknown=12、On Hold=9、To be started=9、QA- In Progress=2、TBD=1）  
[下載 Status 分佈圖](sandbox:/mnt/data/summary_status.png)

- **T-Shirt Sizing 分佈**（Unknown=13、L=7、S=4、M=4、XL=2、XS=2、TBD=1）  
[下載 T-Shirt Sizing 分佈圖](sandbox:/mnt/data/summary_tshirt.png)

> 註：圖上中文若顯示為方塊為字型缺失造成，不影響統計結果；我也可改成全英文標題重新輸出。

---

