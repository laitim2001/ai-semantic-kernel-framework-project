"""
Template Service

Service for managing session templates.
"""

from typing import Optional, Dict, Any, List
from datetime import datetime
from dataclasses import dataclass, field
from enum import Enum
import uuid
import json
import logging

logger = logging.getLogger(__name__)


class TemplateCategory(str, Enum):
    """模板分類"""
    GENERAL = "general"
    CODING = "coding"
    WRITING = "writing"
    ANALYSIS = "analysis"
    BRAINSTORM = "brainstorm"
    LEARNING = "learning"
    CUSTOM = "custom"


@dataclass
class SessionTemplate:
    """Session 模板"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    description: Optional[str] = None
    category: TemplateCategory = TemplateCategory.GENERAL
    # 模板內容
    system_prompt: Optional[str] = None
    initial_messages: List[Dict[str, str]] = field(default_factory=list)
    suggested_prompts: List[str] = field(default_factory=list)
    # 配置
    config: Dict[str, Any] = field(default_factory=dict)
    # 元數據
    user_id: Optional[str] = None  # None 表示系統模板
    is_public: bool = False
    usage_count: int = 0
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: Optional[datetime] = None


class TemplateService:
    """模板服務

    管理 Session 模板。

    功能:
    - 創建/更新/刪除模板
    - 從 Session 創建模板
    - 應用模板到新 Session
    - 模板分享
    - 系統預設模板
    """

    # 系統預設模板
    SYSTEM_TEMPLATES = [
        {
            "id": "system_coding_assistant",
            "name": "程式開發助手",
            "description": "幫助編寫、審查和調試代碼",
            "category": TemplateCategory.CODING,
            "system_prompt": "你是一位專業的程式開發助手。請幫助用戶編寫高質量的代碼，提供最佳實踐建議，並協助調試問題。",
            "suggested_prompts": [
                "幫我寫一個函數來...",
                "請審查這段代碼並提供改進建議",
                "這段代碼有什麼問題？",
                "如何優化這個演算法？"
            ]
        },
        {
            "id": "system_writing_assistant",
            "name": "寫作助手",
            "description": "協助撰寫、編輯和潤色文章",
            "category": TemplateCategory.WRITING,
            "system_prompt": "你是一位專業的寫作助手。請幫助用戶改進文章的結構、語法和表達方式。",
            "suggested_prompts": [
                "請幫我改寫這段文字",
                "這篇文章需要怎麼改進？",
                "幫我寫一份關於...的報告",
                "請為這篇文章寫一個摘要"
            ]
        },
        {
            "id": "system_data_analyst",
            "name": "資料分析師",
            "description": "幫助分析數據和生成報告",
            "category": TemplateCategory.ANALYSIS,
            "system_prompt": "你是一位資料分析專家。請幫助用戶分析數據、發現洞察並生成清晰的報告。",
            "suggested_prompts": [
                "請分析這份數據",
                "這些數據有什麼趨勢？",
                "幫我生成一份分析報告",
                "如何視覺化這些數據？"
            ]
        },
        {
            "id": "system_brainstorm",
            "name": "創意腦力激盪",
            "description": "協助發想和探索創意",
            "category": TemplateCategory.BRAINSTORM,
            "system_prompt": "你是一位創意顧問。請幫助用戶進行腦力激盪，探索各種可能性和創新想法。",
            "suggested_prompts": [
                "幫我想一些關於...的點子",
                "這個問題還有什麼解決方案？",
                "如何讓這個產品更有創意？",
                "請從不同角度分析這個想法"
            ]
        },
        {
            "id": "system_learning",
            "name": "學習導師",
            "description": "幫助學習新概念和技能",
            "category": TemplateCategory.LEARNING,
            "system_prompt": "你是一位耐心的學習導師。請用清晰易懂的方式解釋概念，並提供實用的學習建議。",
            "suggested_prompts": [
                "請解釋什麼是...",
                "我該如何學習...？",
                "這個概念的實際應用是什麼？",
                "請用簡單的例子說明"
            ]
        }
    ]

    def __init__(
        self,
        repository: Optional[Any] = None,
        cache: Optional[Any] = None
    ):
        """
        初始化模板服務

        Args:
            repository: 資料庫存儲實例
            cache: 快取服務實例
        """
        self._repository = repository
        self._cache = cache

    async def create_template(
        self,
        user_id: str,
        name: str,
        description: Optional[str] = None,
        category: TemplateCategory = TemplateCategory.CUSTOM,
        system_prompt: Optional[str] = None,
        initial_messages: Optional[List[Dict[str, str]]] = None,
        suggested_prompts: Optional[List[str]] = None,
        config: Optional[Dict[str, Any]] = None,
        is_public: bool = False
    ) -> SessionTemplate:
        """
        創建模板

        Args:
            user_id: 用戶 ID
            name: 模板名稱
            description: 描述
            category: 分類
            system_prompt: 系統提示詞
            initial_messages: 初始訊息
            suggested_prompts: 建議提示
            config: 配置
            is_public: 是否公開

        Returns:
            SessionTemplate: 創建的模板
        """
        try:
            template = SessionTemplate(
                name=name,
                description=description,
                category=category,
                system_prompt=system_prompt,
                initial_messages=initial_messages or [],
                suggested_prompts=suggested_prompts or [],
                config=config or {},
                user_id=user_id,
                is_public=is_public
            )

            if self._repository:
                await self._repository.create_template(template)

            await self._invalidate_cache(user_id)
            logger.info(f"Created template: {template.name}")
            return template

        except Exception as e:
            logger.error(f"Failed to create template: {e}")
            raise

    async def create_from_session(
        self,
        session_id: str,
        user_id: str,
        name: str,
        description: Optional[str] = None,
        include_messages: bool = False,
        message_count: int = 5
    ) -> SessionTemplate:
        """
        從現有 Session 創建模板

        Args:
            session_id: 來源 Session ID
            user_id: 用戶 ID
            name: 模板名稱
            description: 描述
            include_messages: 是否包含初始訊息
            message_count: 包含的訊息數量

        Returns:
            SessionTemplate: 創建的模板
        """
        try:
            if not self._repository:
                raise RuntimeError("Repository not available")

            # 獲取 Session
            session = await self._repository.get_session(session_id)
            if not session:
                raise ValueError(f"Session not found: {session_id}")

            # 獲取系統提示
            system_prompt = None
            if hasattr(session, 'system_prompt'):
                system_prompt = session.system_prompt

            # 獲取初始訊息
            initial_messages = []
            if include_messages:
                messages = await self._repository.get_messages(
                    session_id=session_id,
                    limit=message_count,
                    order="asc"
                )
                initial_messages = [
                    {"role": m.role.value, "content": m.content}
                    for m in messages[0] if messages
                ]

            return await self.create_template(
                user_id=user_id,
                name=name,
                description=description or f"從 Session 創建的模板",
                category=TemplateCategory.CUSTOM,
                system_prompt=system_prompt,
                initial_messages=initial_messages
            )

        except Exception as e:
            logger.error(f"Failed to create template from session: {e}")
            raise

    async def get_template(self, template_id: str) -> Optional[SessionTemplate]:
        """獲取模板"""
        try:
            # 檢查是否為系統模板
            for st in self.SYSTEM_TEMPLATES:
                if st["id"] == template_id:
                    return self._parse_system_template(st)

            if self._repository:
                return await self._repository.get_template(template_id)

            return None

        except Exception as e:
            logger.error(f"Failed to get template: {e}")
            return None

    async def get_user_templates(
        self,
        user_id: str,
        category: Optional[TemplateCategory] = None,
        include_system: bool = True,
        include_public: bool = True
    ) -> List[SessionTemplate]:
        """
        獲取用戶可用的模板

        Args:
            user_id: 用戶 ID
            category: 過濾分類
            include_system: 包含系統模板
            include_public: 包含公開模板

        Returns:
            List[SessionTemplate]: 模板列表
        """
        try:
            templates = []

            # 添加系統模板
            if include_system:
                for st in self.SYSTEM_TEMPLATES:
                    template = self._parse_system_template(st)
                    if category is None or template.category == category:
                        templates.append(template)

            # 獲取用戶模板
            if self._repository:
                user_templates = await self._repository.get_user_templates(
                    user_id=user_id,
                    category=category
                )
                templates.extend(user_templates)

                # 獲取公開模板
                if include_public:
                    public_templates = await self._repository.get_public_templates(
                        category=category,
                        exclude_user=user_id
                    )
                    templates.extend(public_templates)

            return templates

        except Exception as e:
            logger.error(f"Failed to get user templates: {e}")
            return []

    async def update_template(
        self,
        template_id: str,
        user_id: str,
        **updates
    ) -> Optional[SessionTemplate]:
        """更新模板"""
        try:
            template = await self.get_template(template_id)
            if not template or template.user_id != user_id:
                return None

            # 更新欄位
            for key, value in updates.items():
                if hasattr(template, key) and value is not None:
                    setattr(template, key, value)

            template.updated_at = datetime.now()

            if self._repository:
                await self._repository.update_template(template)

            await self._invalidate_cache(user_id)
            return template

        except Exception as e:
            logger.error(f"Failed to update template: {e}")
            return None

    async def delete_template(
        self,
        template_id: str,
        user_id: str
    ) -> bool:
        """刪除模板"""
        try:
            template = await self.get_template(template_id)
            if not template or template.user_id != user_id:
                return False

            if self._repository:
                await self._repository.delete_template(template_id)

            await self._invalidate_cache(user_id)
            return True

        except Exception as e:
            logger.error(f"Failed to delete template: {e}")
            return False

    async def apply_template(
        self,
        template_id: str,
        session_id: str
    ) -> bool:
        """
        將模板應用到 Session

        Args:
            template_id: 模板 ID
            session_id: 目標 Session ID

        Returns:
            bool: 是否應用成功
        """
        try:
            template = await self.get_template(template_id)
            if not template:
                return False

            if not self._repository:
                return False

            # 更新 Session 的系統提示
            if template.system_prompt:
                await self._repository.update_session_prompt(
                    session_id=session_id,
                    system_prompt=template.system_prompt
                )

            # 添加初始訊息
            for msg in template.initial_messages:
                await self._repository.add_message(
                    session_id=session_id,
                    role=msg.get("role", "system"),
                    content=msg.get("content", "")
                )

            # 更新使用次數
            template.usage_count += 1
            await self._repository.update_template(template)

            logger.info(f"Applied template {template_id} to session {session_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to apply template: {e}")
            return False

    async def get_popular_templates(
        self,
        category: Optional[TemplateCategory] = None,
        limit: int = 10
    ) -> List[SessionTemplate]:
        """獲取最常用的模板"""
        try:
            all_templates = await self.get_user_templates(
                user_id="",
                category=category,
                include_system=True,
                include_public=True
            )

            # 按使用次數排序
            sorted_templates = sorted(
                all_templates,
                key=lambda t: t.usage_count,
                reverse=True
            )

            return sorted_templates[:limit]

        except Exception as e:
            logger.error(f"Failed to get popular templates: {e}")
            return []

    async def export_template(
        self,
        template_id: str
    ) -> Optional[Dict[str, Any]]:
        """匯出模板"""
        template = await self.get_template(template_id)
        if not template:
            return None

        return {
            "name": template.name,
            "description": template.description,
            "category": template.category.value,
            "system_prompt": template.system_prompt,
            "initial_messages": template.initial_messages,
            "suggested_prompts": template.suggested_prompts,
            "config": template.config,
            "exported_at": datetime.now().isoformat()
        }

    async def import_template(
        self,
        user_id: str,
        data: Dict[str, Any]
    ) -> SessionTemplate:
        """匯入模板"""
        category = TemplateCategory(data.get("category", "custom"))

        return await self.create_template(
            user_id=user_id,
            name=data.get("name", "Imported Template"),
            description=data.get("description"),
            category=category,
            system_prompt=data.get("system_prompt"),
            initial_messages=data.get("initial_messages", []),
            suggested_prompts=data.get("suggested_prompts", []),
            config=data.get("config", {})
        )

    def _parse_system_template(self, data: Dict[str, Any]) -> SessionTemplate:
        """解析系統模板"""
        return SessionTemplate(
            id=data["id"],
            name=data["name"],
            description=data.get("description"),
            category=data.get("category", TemplateCategory.GENERAL),
            system_prompt=data.get("system_prompt"),
            initial_messages=data.get("initial_messages", []),
            suggested_prompts=data.get("suggested_prompts", []),
            config=data.get("config", {}),
            user_id=None  # 系統模板
        )

    async def _invalidate_cache(self, user_id: str) -> None:
        """清除快取"""
        if self._cache:
            await self._cache.delete_pattern(f"templates:{user_id}:*")
