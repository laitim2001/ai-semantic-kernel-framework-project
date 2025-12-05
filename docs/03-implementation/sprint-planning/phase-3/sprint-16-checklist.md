# Sprint 16 Checklist: GroupChatBuilder 重構

**Sprint 目標**: 將 GroupChatManager 遷移至 GroupChatBuilder
**週期**: Week 33-34
**總點數**: 42 點
**狀態**: 待開始

---

## S16-1: GroupChatBuilder 適配器 (8 點)

- [ ] 創建 `builders/groupchat.py`
- [ ] GroupChatBuilderAdapter 類
- [ ] participants() 支持
- [ ] set_manager() 支持

---

## S16-2: GroupChatManager 功能遷移 (8 點)

- [ ] 遷移 SpeakerSelectionMethod
- [ ] 遷移 GroupMessage
- [ ] 遷移 GroupChatState
- [ ] 遷移事件系統

---

## S16-3: Orchestrator (8 點)

- [ ] GroupChatOrchestratorExecutor 整合

---

## S16-4: ManagerSelection (8 點)

- [ ] ManagerSelectionRequest 整合
- [ ] ManagerSelectionResponse 整合

---

## S16-5: API 更新 (5 點)

- [ ] groupchat 端點更新

---

## S16-6: 測試 (5 點)

- [ ] 覆蓋率 >= 80%

---

## 相關連結

- [Sprint 16 Plan](./sprint-16-plan.md)
- [Phase 3 Overview](./README.md)
