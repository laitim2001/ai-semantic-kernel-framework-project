# 🔚 情況9: Session 結束 - 結束開發會話

> **使用時機**: 結束當天的開發工作時
> **目標**: 安全地結束會話並記錄狀態
> **適用場景**: 工作日結束、長時間休息、切換項目

---

## 📋 Prompt 模板 (給開發人員)

```markdown
你好！我需要結束今天的開發會話。

**今日完成**:
- [完成項目 1]
- [完成項目 2]

**進行中的工作** (如有):
- [未完成項目]

請幫我：

1. 保存所有變更
   - 確認並提交所有變更
   - 推送到遠端分支

2. 記錄會話狀態
   - 總結今日完成的工作
   - 記錄未完成的工作

3. 整理工作環境
   - 關閉不需要的服務 (可選)
   - 清理臨時文件

4. 準備下次會話
   - 列出明天要做的事項
   - 標記需要注意的事項

請用中文回答。
```

---

## 🤖 AI 助手執行步驟

### Step 1: 檢查和保存變更 (2 分鐘)

```bash
# 1. 檢查未提交的變更
Bash: git status

# 2. 查看變更內容
Bash: git diff --stat

# 3. 如果有未提交的變更，執行提交
Bash: git add .
Bash: git commit -m "$(cat <<'EOF'
chore: Save progress - session end

🤖 Generated with Claude Code
Co-Authored-By: Claude <noreply@anthropic.com>
EOF
)"

# 4. 推送到遠端
Bash: git push origin HEAD
```

### Step 2: 生成會話總結 (2 分鐘)

```markdown
# 📊 會話總結報告

## 日期: YYYY-MM-DD

## ✅ 今日完成
| 項目 | 類型 | 影響範圍 |
|------|------|----------|
| [完成項目 1] | feat/fix/docs | [模組] |
| [完成項目 2] | feat/fix/docs | [模組] |

## 🔄 進行中
| 項目 | 進度 | 下一步 |
|------|------|--------|
| [未完成項目] | X% | [下一步行動] |

## 📝 提交記錄
```
[最近 3-5 個提交的 git log --oneline]
```

## 📂 變更的文件
- `path/to/file1.py` - [變更說明]
- `path/to/file2.py` - [變更說明]

## ⚠️ 注意事項
- [需要注意的問題或風險]
- [需要跟進的事項]

## 📋 明日計劃
1. [ ] [下一個任務 1]
2. [ ] [下一個任務 2]
3. [ ] [下一個任務 3]
```

### Step 3: 環境清理 (可選)

```bash
# 1. 檢查運行中的服務
Bash: docker-compose ps

# 2. 停止服務 (如需要)
Bash: docker-compose down

# 3. 清理臨時文件
Bash: find . -name "*.pyc" -delete
Bash: find . -name "__pycache__" -type d -exec rm -rf {} +
```

### Step 4: 確認最終狀態

```bash
# 1. 確認分支狀態
Bash: git branch -v

# 2. 確認與遠端同步
Bash: git status

# 3. 查看最近的提交
Bash: git log --oneline -5
```

---

## 📋 會話結束檢查清單

### 必做項目
- [ ] 所有變更已提交
- [ ] 變更已推送到遠端
- [ ] 測試通過 (至少相關模組)
- [ ] 無明顯的未處理問題

### 建議項目
- [ ] 更新相關文檔
- [ ] 記錄會話總結
- [ ] 列出明日計劃
- [ ] 標記需要注意的事項

### 可選項目
- [ ] 停止開發服務
- [ ] 清理臨時文件
- [ ] 通知團隊成員

---

## 📝 快速結束命令

如果需要快速結束，可以使用以下組合命令：

```bash
# 快速保存和推送
git add . && git commit -m "chore: WIP - session end" && git push origin HEAD

# 查看狀態確認
git status && git log --oneline -3
```

---

## ✅ 驗收標準

AI 助手完成結束流程後應確認：

1. **變更已保存**
   - 所有代碼變更已提交
   - 變更已推送到遠端

2. **狀態已記錄**
   - 提供會話總結報告
   - 記錄未完成的工作

3. **下次會話準備**
   - 列出明日計劃
   - 標記需要注意的事項

4. **環境整理**
   - 確認分支狀態乾淨
   - 無遺漏的臨時文件

---

## 🔗 相關文檔

### 開發流程指引
- [情況1: 專案入門](./SITUATION-1-PROJECT-ONBOARDING.md) - 下次會話開始時使用
- [情況6: 保存進度](./SITUATION-6-SAVE-PROGRESS.md)

### 工作流程
- `.claude/rules/git-workflow.md` - Git 工作流程規則

---

**維護者**: AI 助手 + 開發團隊
**最後更新**: 2025-12-24
**版本**: 2.0
