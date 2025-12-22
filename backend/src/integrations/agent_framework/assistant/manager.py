"""
AssistantManagerService - Azure OpenAI Assistants 管理服務

負責創建和管理 Azure OpenAI Assistants，處理 Thread 和 Run 生命週期。
專門設計用於 Code Interpreter 功能。
"""

from typing import List, Optional, Dict, Any
import time
import logging

from openai import AzureOpenAI

from .models import (
    CodeExecutionResult,
    ExecutionStatus,
    AssistantConfig,
    AssistantInfo,
)
from .exceptions import (
    AssistantError,
    ExecutionTimeoutError,
    AssistantNotFoundError,
    AssistantCreationError,
    ThreadCreationError,
    RunError,
    ConfigurationError,
)

logger = logging.getLogger(__name__)


class AssistantManagerService:
    """Azure OpenAI Assistants 管理服務。

    負責創建和管理 Assistants，處理 Thread 和 Run 生命週期。
    專門設計用於 Code Interpreter 功能。

    Example:
        ```python
        from src.integrations.agent_framework.assistant import AssistantManagerService

        # 使用默認配置
        manager = AssistantManagerService()

        # 創建 Assistant
        assistant = manager.create_assistant(
            name="Data Analyst",
            instructions="You are a data analysis assistant.",
        )

        # 執行程式碼
        result = manager.execute_code(
            assistant_id=assistant.id,
            code="print(sum(range(1, 101)))"
        )
        print(result.output)  # 包含 "5050"

        # 清理
        manager.delete_assistant(assistant.id)
        ```
    """

    def __init__(
        self,
        endpoint: Optional[str] = None,
        api_key: Optional[str] = None,
        deployment: Optional[str] = None,
        api_version: str = "2024-12-01-preview",
    ):
        """初始化 Assistant Manager。

        Args:
            endpoint: Azure OpenAI 端點 (可選，默認從環境變量讀取)
            api_key: API 金鑰 (可選，默認從環境變量讀取)
            deployment: 模型部署名稱 (可選，默認從環境變量讀取)
            api_version: API 版本

        Raises:
            ConfigurationError: 當必要配置缺失時
        """
        # 延遲導入以避免循環依賴
        from src.core.config import settings

        self._endpoint = endpoint or getattr(settings, 'AZURE_OPENAI_ENDPOINT', '')
        self._api_key = api_key or getattr(settings, 'AZURE_OPENAI_API_KEY', '')
        self._deployment = deployment or getattr(settings, 'AZURE_OPENAI_DEPLOYMENT_NAME', '')
        self._api_version = api_version

        # 驗證配置
        if not self._endpoint:
            raise ConfigurationError("AZURE_OPENAI_ENDPOINT is required")
        if not self._api_key:
            raise ConfigurationError("AZURE_OPENAI_API_KEY is required")
        if not self._deployment:
            raise ConfigurationError("AZURE_OPENAI_DEPLOYMENT_NAME is required")

        # 創建客戶端
        self._client = AzureOpenAI(
            azure_endpoint=self._endpoint,
            api_key=self._api_key,
            api_version=self._api_version,
        )

        logger.info(
            f"AssistantManagerService initialized: "
            f"endpoint={self._endpoint[:50]}..., deployment={self._deployment}"
        )

    def create_assistant(
        self,
        name: str,
        instructions: str,
        tools: Optional[List[Dict[str, str]]] = None,
        model: Optional[str] = None,
    ) -> AssistantInfo:
        """創建帶 Code Interpreter 的 Assistant。

        Args:
            name: Assistant 名稱
            instructions: 系統指令
            tools: 工具列表，默認包含 code_interpreter
            model: 模型部署名稱 (可選，默認使用初始化時的配置)

        Returns:
            AssistantInfo 包含創建的 Assistant 信息

        Raises:
            AssistantCreationError: 當創建失敗時
        """
        if tools is None:
            tools = [{"type": "code_interpreter"}]

        model_name = model or self._deployment

        try:
            assistant = self._client.beta.assistants.create(
                name=name,
                instructions=instructions,
                model=model_name,
                tools=tools,
            )

            logger.info(f"Created assistant: {assistant.id} ({name})")

            return AssistantInfo.from_api_response(assistant)

        except Exception as e:
            logger.error(f"Failed to create assistant: {e}")
            raise AssistantCreationError(f"Failed to create assistant: {e}")

    def get_assistant(self, assistant_id: str) -> AssistantInfo:
        """獲取 Assistant 信息。

        Args:
            assistant_id: Assistant ID

        Returns:
            AssistantInfo 包含 Assistant 信息

        Raises:
            AssistantNotFoundError: 當 Assistant 不存在時
        """
        try:
            assistant = self._client.beta.assistants.retrieve(assistant_id)
            return AssistantInfo.from_api_response(assistant)
        except Exception as e:
            if "not found" in str(e).lower():
                raise AssistantNotFoundError(assistant_id)
            raise AssistantError(f"Failed to get assistant: {e}")

    def list_assistants(self, limit: int = 20) -> List[AssistantInfo]:
        """列出所有 Assistants。

        Args:
            limit: 返回數量限制

        Returns:
            AssistantInfo 列表
        """
        try:
            assistants = self._client.beta.assistants.list(limit=limit)
            return [AssistantInfo.from_api_response(a) for a in assistants.data]
        except Exception as e:
            logger.error(f"Failed to list assistants: {e}")
            return []

    def delete_assistant(self, assistant_id: str) -> bool:
        """刪除 Assistant。

        Args:
            assistant_id: 要刪除的 Assistant ID

        Returns:
            是否刪除成功
        """
        try:
            self._client.beta.assistants.delete(assistant_id)
            logger.info(f"Deleted assistant: {assistant_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to delete assistant {assistant_id}: {e}")
            return False

    def execute_code(
        self,
        assistant_id: str,
        code: str,
        timeout: int = 60,
    ) -> CodeExecutionResult:
        """執行程式碼並返回結果。

        Args:
            assistant_id: Assistant ID
            code: 要執行的 Python 程式碼
            timeout: 超時時間 (秒)

        Returns:
            CodeExecutionResult 包含執行結果

        Raises:
            ExecutionTimeoutError: 當執行超時時
            AssistantNotFoundError: 當 Assistant 不存在時
        """
        start_time = time.time()

        try:
            # 創建 Thread
            thread = self._client.beta.threads.create()
            logger.debug(f"Created thread: {thread.id}")

            # 發送程式碼執行請求
            prompt = f"""Execute this Python code and return the result:

```python
{code}
```

Please execute the code and show the output."""

            self._client.beta.threads.messages.create(
                thread_id=thread.id,
                role="user",
                content=prompt,
            )

            # 運行 Assistant
            run = self._client.beta.threads.runs.create(
                thread_id=thread.id,
                assistant_id=assistant_id,
            )
            logger.debug(f"Created run: {run.id}")

            # 等待完成
            while run.status in ["queued", "in_progress"]:
                elapsed = time.time() - start_time
                if elapsed > timeout:
                    logger.warning(f"Execution timed out after {elapsed:.1f}s")
                    return CodeExecutionResult(
                        status=ExecutionStatus.TIMEOUT,
                        output=f"Execution timed out after {timeout} seconds",
                        execution_time=elapsed,
                    )

                time.sleep(1)
                run = self._client.beta.threads.runs.retrieve(
                    thread_id=thread.id,
                    run_id=run.id,
                )
                logger.debug(f"Run status: {run.status}")

            execution_time = time.time() - start_time

            if run.status == "completed":
                return self._extract_result(thread.id, execution_time)
            elif run.status == "failed":
                error_msg = "Unknown error"
                if hasattr(run, 'last_error') and run.last_error:
                    error_msg = str(run.last_error)
                logger.error(f"Run failed: {error_msg}")
                return CodeExecutionResult(
                    status=ExecutionStatus.ERROR,
                    output=error_msg,
                    execution_time=execution_time,
                )
            elif run.status == "cancelled":
                return CodeExecutionResult(
                    status=ExecutionStatus.CANCELLED,
                    output="Execution was cancelled",
                    execution_time=execution_time,
                )
            else:
                return CodeExecutionResult(
                    status=ExecutionStatus.ERROR,
                    output=f"Unexpected run status: {run.status}",
                    execution_time=execution_time,
                )

        except Exception as e:
            elapsed = time.time() - start_time
            logger.error(f"Code execution failed: {e}")

            if "not found" in str(e).lower():
                raise AssistantNotFoundError(assistant_id)

            return CodeExecutionResult(
                status=ExecutionStatus.ERROR,
                output=str(e),
                execution_time=elapsed,
            )

    def _extract_result(
        self,
        thread_id: str,
        execution_time: float,
    ) -> CodeExecutionResult:
        """從 Thread 提取執行結果。

        Args:
            thread_id: Thread ID
            execution_time: 執行耗時

        Returns:
            CodeExecutionResult 包含提取的結果
        """
        try:
            messages = self._client.beta.threads.messages.list(thread_id=thread_id)

            output = ""
            files = []
            code_outputs = []

            for msg in messages.data:
                if msg.role == "assistant":
                    for content in msg.content:
                        if content.type == "text":
                            output = content.text.value
                            # 提取代碼輸出標註
                            if hasattr(content.text, 'annotations'):
                                for ann in content.text.annotations:
                                    if hasattr(ann, 'file_path'):
                                        files.append({
                                            "type": "file",
                                            "file_id": ann.file_path.file_id,
                                        })
                        elif content.type == "image_file":
                            files.append({
                                "type": "image",
                                "file_id": content.image_file.file_id,
                            })
                    break  # 只取第一個 assistant 回覆

            return CodeExecutionResult(
                status=ExecutionStatus.SUCCESS,
                output=output,
                execution_time=execution_time,
                files=files,
                code_outputs=code_outputs,
            )

        except Exception as e:
            logger.error(f"Failed to extract result: {e}")
            return CodeExecutionResult(
                status=ExecutionStatus.ERROR,
                output=f"Failed to extract result: {e}",
                execution_time=execution_time,
            )

    def run_task(
        self,
        assistant_id: str,
        task: str,
        context: Optional[Dict[str, Any]] = None,
        timeout: int = 60,
    ) -> CodeExecutionResult:
        """執行任務 (讓 Assistant 決定如何解決)。

        與 execute_code 不同，這個方法傳遞任務描述，
        讓 Assistant 自行決定需要什麼代碼來解決。

        Args:
            assistant_id: Assistant ID
            task: 任務描述
            context: 可選的上下文信息
            timeout: 超時時間 (秒)

        Returns:
            CodeExecutionResult 包含執行結果
        """
        # 構建提示詞
        prompt = f"Task: {task}\n"
        if context:
            prompt += f"\nContext:\n"
            for key, value in context.items():
                prompt += f"- {key}: {value}\n"
        prompt += "\nPlease solve this task using Python code if needed."

        # 使用 execute_code 執行
        return self.execute_code(
            assistant_id=assistant_id,
            code=prompt,  # 這裡 prompt 作為任務描述
            timeout=timeout,
        )

    @property
    def client(self) -> AzureOpenAI:
        """獲取底層 Azure OpenAI 客戶端。"""
        return self._client

    @property
    def deployment(self) -> str:
        """獲取模型部署名稱。"""
        return self._deployment
