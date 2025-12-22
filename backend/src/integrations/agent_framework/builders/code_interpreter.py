"""
CodeInterpreterAdapter - Code Interpreter 適配器

將 Azure OpenAI Code Interpreter 功能封裝為 IPA Platform 標準接口。
支援兩種 API 模式:
1. Responses API (推薦, api-version >= 2025-03-01-preview)
2. Assistants API (舊版, 但功能完整)

遵循 Adapter Pattern，與其他 Builder Adapters 保持一致的使用方式。
"""

from typing import Optional, Dict, Any, List, Literal, Union
from dataclasses import dataclass, field
from enum import Enum
import logging
import time

from ..assistant import (
    AssistantManagerService,
    AssistantConfig,
    CodeExecutionResult,
    ExecutionStatus,
    AssistantInfo,
    ConfigurationError,
)

logger = logging.getLogger(__name__)


class APIMode(str, Enum):
    """API 模式選擇。"""
    RESPONSES = "responses"      # 新版 Responses API (推薦)
    ASSISTANTS = "assistants"    # 舊版 Assistants API
    AUTO = "auto"                # 自動選擇 (優先 Responses)


@dataclass
class CodeInterpreterConfig:
    """Code Interpreter 配置。

    Attributes:
        assistant_name: Assistant 名稱 (用於 Assistants API)
        instructions: 系統指令
        timeout: 執行超時時間 (秒)
        max_retries: 最大重試次數
        auto_cleanup: 是否在結束時自動清理 Assistant
        api_mode: API 模式 (responses/assistants/auto)
        api_version: Azure OpenAI API 版本
        azure_endpoint: Azure OpenAI 端點 (可選，用於 Responses API)
        api_key: API 密鑰 (可選，用於 Responses API)
        deployment: 模型部署名稱
    """
    assistant_name: str = "IPA-CodeInterpreter"
    instructions: str = (
        "You are a Python code execution assistant. "
        "Execute code accurately and return results. "
        "When given code, execute it and provide the output. "
        "When given a task, write appropriate Python code to solve it."
    )
    timeout: int = 60
    max_retries: int = 3
    auto_cleanup: bool = True
    api_mode: APIMode = APIMode.AUTO
    api_version: str = "2025-03-01-preview"
    azure_endpoint: Optional[str] = None
    api_key: Optional[str] = None
    deployment: Optional[str] = None


@dataclass
class ExecutionResult:
    """統一執行結果格式。

    與其他 Adapter 的結果格式保持一致。

    Attributes:
        success: 是否成功
        output: 輸出內容
        execution_time: 執行耗時 (秒)
        files: 生成的文件列表
        error: 錯誤信息 (如果有)
        metadata: 額外的元數據
    """
    success: bool
    output: str
    execution_time: float
    files: List[Dict[str, Any]] = field(default_factory=list)
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_code_result(cls, result: CodeExecutionResult) -> "ExecutionResult":
        """從 CodeExecutionResult 創建 ExecutionResult。"""
        return cls(
            success=result.is_success,
            output=result.output,
            execution_time=result.execution_time,
            files=result.files,
            error=result.output if not result.is_success else None,
            metadata={
                "status": result.status.value,
                "code_outputs": result.code_outputs,
                "api_mode": "assistants",
            },
        )

    @classmethod
    def from_responses_api(
        cls,
        response: Any,
        execution_time: float,
    ) -> "ExecutionResult":
        """從 Responses API 結果創建 ExecutionResult。

        Args:
            response: OpenAI Responses API 回應
            execution_time: 執行耗時

        Returns:
            ExecutionResult 實例
        """
        output_text = ""
        code_outputs = []
        files = []
        error = None

        try:
            # 解析 Responses API 輸出
            if hasattr(response, 'output'):
                for item in response.output:
                    if hasattr(item, 'type'):
                        if item.type == 'message':
                            # 提取文字內容
                            for content in getattr(item, 'content', []):
                                if hasattr(content, 'text'):
                                    output_text += content.text + "\n"
                        elif item.type == 'code_interpreter_call':
                            # 提取代碼執行結果
                            code_info = {
                                "id": getattr(item, 'id', ''),
                                "code": getattr(item, 'code', ''),
                            }
                            code_outputs.append(code_info)
                            if hasattr(item, 'outputs'):
                                for out in item.outputs:
                                    if hasattr(out, 'type'):
                                        if out.type == 'logs':
                                            output_text += getattr(out, 'logs', '') + "\n"
                                        elif out.type == 'image':
                                            files.append({
                                                "type": "image",
                                                "file_id": getattr(out, 'file_id', ''),
                                            })

            # 備用: 嘗試 output_text 屬性
            if not output_text and hasattr(response, 'output_text'):
                output_text = response.output_text

            success = True

        except Exception as e:
            error = str(e)
            success = False
            logger.error(f"Failed to parse Responses API output: {e}")

        return cls(
            success=success,
            output=output_text.strip(),
            execution_time=execution_time,
            files=files,
            error=error,
            metadata={
                "status": "completed" if success else "failed",
                "code_outputs": code_outputs,
                "api_mode": "responses",
                "response_id": getattr(response, 'id', ''),
            },
        )

    def to_dict(self) -> Dict[str, Any]:
        """轉換為字典。"""
        return {
            "success": self.success,
            "output": self.output,
            "execution_time": self.execution_time,
            "files": self.files,
            "error": self.error,
            "metadata": self.metadata,
        }


class CodeInterpreterAdapter:
    """Code Interpreter 適配器。

    將 Azure OpenAI Code Interpreter 功能封裝為 IPA Platform 標準接口。
    支援兩種 API 模式:
    - Responses API (推薦): 新版 API，更簡潔高效
    - Assistants API (舊版): 功能完整，支援多輪對話

    Features:
        - 雙 API 模式支援: Responses API 和 Assistants API
        - Lazy initialization: 首次使用時才創建資源
        - 自動資源管理: 支援 context manager 和 cleanup()
        - 統一結果格式: 與其他 Adapter 保持一致

    Example:
        ```python
        from src.integrations.agent_framework.builders import CodeInterpreterAdapter

        # 使用 Responses API (推薦)
        config = CodeInterpreterConfig(
            api_mode=APIMode.RESPONSES,
            azure_endpoint="https://xxx.openai.azure.com/",
            api_key="your-key",
            deployment="gpt-5.2",
        )
        adapter = CodeInterpreterAdapter(config=config)
        result = adapter.execute("print(2 + 2)")
        print(result.output)  # 包含 "4"

        # 使用 Assistants API (舊版)
        config = CodeInterpreterConfig(api_mode=APIMode.ASSISTANTS)
        adapter = CodeInterpreterAdapter(config=config)
        result = adapter.execute("print(sum(range(1, 101)))")

        # Context manager
        with CodeInterpreterAdapter() as adapter:
            result = adapter.analyze_task("Calculate factorial of 10")
            print(result.output)
        ```

    Note:
        - Responses API 需要 api-version >= 2025-03-01-preview
        - Assistants API 會創建和管理 Assistant 實例
    """

    def __init__(
        self,
        config: Optional[CodeInterpreterConfig] = None,
        manager: Optional[AssistantManagerService] = None,
    ):
        """初始化 Code Interpreter 適配器。

        Args:
            config: 配置選項 (可選)
            manager: AssistantManagerService 實例 (可選，用於測試)
        """
        self._config = config or CodeInterpreterConfig()
        self._manager: Optional[AssistantManagerService] = manager
        self._assistant_id: Optional[str] = None
        self._assistant_info: Optional[AssistantInfo] = None
        self._initialized = False
        self._openai_client = None
        self._active_api_mode: Optional[APIMode] = None

        logger.info(
            f"CodeInterpreterAdapter created: "
            f"name={self._config.assistant_name}, "
            f"timeout={self._config.timeout}s, "
            f"api_mode={self._config.api_mode.value}"
        )

    def _get_openai_client(self):
        """獲取 OpenAI 客戶端 (用於 Responses API)。"""
        if self._openai_client is not None:
            return self._openai_client

        try:
            from openai import AzureOpenAI
            from src.core.config import get_settings

            settings = get_settings()

            # 優先使用配置中的值，否則使用環境變數
            endpoint = self._config.azure_endpoint or settings.AZURE_OPENAI_ENDPOINT
            api_key = self._config.api_key or settings.AZURE_OPENAI_API_KEY

            if not endpoint or not api_key:
                raise ConfigurationError(
                    "Azure OpenAI endpoint and API key are required for Responses API"
                )

            self._openai_client = AzureOpenAI(
                api_version=self._config.api_version,
                azure_endpoint=endpoint,
                api_key=api_key,
            )

            logger.info(f"OpenAI client created for Responses API")
            return self._openai_client

        except ImportError:
            raise ConfigurationError("openai package is required: pip install openai")
        except Exception as e:
            logger.error(f"Failed to create OpenAI client: {e}")
            raise ConfigurationError(f"Failed to create OpenAI client: {e}")

    def _get_deployment(self) -> str:
        """獲取模型部署名稱。"""
        if self._config.deployment:
            return self._config.deployment

        try:
            from src.core.config import get_settings
            settings = get_settings()
            return settings.AZURE_OPENAI_DEPLOYMENT_NAME or "gpt-4"
        except Exception:
            return "gpt-4"

    def _determine_api_mode(self) -> APIMode:
        """決定使用哪個 API 模式。"""
        if self._config.api_mode != APIMode.AUTO:
            return self._config.api_mode

        # 自動模式: 嘗試 Responses API，失敗則回退到 Assistants API
        try:
            client = self._get_openai_client()
            if hasattr(client, 'responses'):
                logger.info("Auto mode: Using Responses API")
                return APIMode.RESPONSES
        except Exception as e:
            logger.info(f"Auto mode: Responses API not available ({e}), using Assistants API")

        return APIMode.ASSISTANTS

    def _ensure_manager(self) -> AssistantManagerService:
        """確保 Manager 已初始化 (用於 Assistants API)。"""
        if self._manager is None:
            try:
                self._manager = AssistantManagerService()
            except ConfigurationError as e:
                logger.error(f"Failed to initialize AssistantManagerService: {e}")
                raise
        return self._manager

    def _ensure_initialized(self) -> None:
        """確保適配器已初始化。"""
        if self._initialized:
            return

        self._active_api_mode = self._determine_api_mode()

        if self._active_api_mode == APIMode.ASSISTANTS:
            # Assistants API: 創建 Assistant
            manager = self._ensure_manager()
            try:
                assistant_info = manager.create_assistant(
                    name=self._config.assistant_name,
                    instructions=self._config.instructions,
                )
                self._assistant_id = assistant_info.id
                self._assistant_info = assistant_info
                logger.info(
                    f"CodeInterpreterAdapter initialized (Assistants API): "
                    f"assistant_id={self._assistant_id}"
                )
            except Exception as e:
                logger.error(f"Failed to initialize Assistants API: {e}")
                raise
        else:
            # Responses API: 確保客戶端可用
            self._get_openai_client()
            logger.info("CodeInterpreterAdapter initialized (Responses API)")

        self._initialized = True

    def execute(
        self,
        code: str,
        timeout: Optional[int] = None,
    ) -> ExecutionResult:
        """執行 Python 程式碼。

        Args:
            code: 要執行的 Python 代碼
            timeout: 可選的超時時間 (秒)，默認使用配置值

        Returns:
            ExecutionResult 包含執行結果

        Example:
            ```python
            result = adapter.execute("print(sum(range(1, 101)))")
            if result.success:
                print(result.output)  # 包含 "5050"
            else:
                print(f"Error: {result.error}")
            ```
        """
        self._ensure_initialized()

        if self._active_api_mode == APIMode.RESPONSES:
            return self._execute_responses_api(code, timeout)
        else:
            return self._execute_assistants_api(code, timeout)

    def _execute_responses_api(
        self,
        code: str,
        timeout: Optional[int] = None,
    ) -> ExecutionResult:
        """使用 Responses API 執行代碼。"""
        start_time = time.time()

        try:
            client = self._get_openai_client()
            deployment = self._get_deployment()

            # 構建請求: 要求執行特定代碼
            input_text = f"Execute the following Python code and show the output:\n\n```python\n{code}\n```"

            response = client.responses.create(
                model=deployment,
                input=input_text,
                tools=[{
                    "type": "code_interpreter",
                    "container": {"type": "auto"}
                }],
            )

            execution_time = time.time() - start_time
            result = ExecutionResult.from_responses_api(response, execution_time)

            logger.info(
                f"Responses API execution completed: "
                f"success={result.success}, time={execution_time:.2f}s"
            )

            return result

        except Exception as e:
            execution_time = time.time() - start_time
            logger.error(f"Responses API execution failed: {e}")

            return ExecutionResult(
                success=False,
                output="",
                execution_time=execution_time,
                error=str(e),
                metadata={"api_mode": "responses", "error_type": type(e).__name__},
            )

    def _execute_assistants_api(
        self,
        code: str,
        timeout: Optional[int] = None,
    ) -> ExecutionResult:
        """使用 Assistants API 執行代碼。"""
        manager = self._ensure_manager()
        result = manager.execute_code(
            assistant_id=self._assistant_id,
            code=code,
            timeout=timeout or self._config.timeout,
        )
        return ExecutionResult.from_code_result(result)

    def analyze_task(
        self,
        task: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> ExecutionResult:
        """執行分析任務。

        讓 AI 生成並執行程式碼來完成分析任務。

        Args:
            task: 任務描述
            context: 可選的上下文信息

        Returns:
            ExecutionResult 包含分析結果

        Example:
            ```python
            result = adapter.analyze_task(
                "Calculate the mean and standard deviation of [1, 2, 3, 4, 5]"
            )
            print(result.output)
            ```
        """
        self._ensure_initialized()

        if self._active_api_mode == APIMode.RESPONSES:
            return self._analyze_task_responses_api(task, context)
        else:
            return self._analyze_task_assistants_api(task, context)

    def _analyze_task_responses_api(
        self,
        task: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> ExecutionResult:
        """使用 Responses API 執行分析任務。"""
        start_time = time.time()

        try:
            client = self._get_openai_client()
            deployment = self._get_deployment()

            # 構建輸入
            input_text = task
            if context:
                import json
                context_str = json.dumps(context, indent=2, ensure_ascii=False)
                input_text = f"{task}\n\nContext:\n{context_str}"

            response = client.responses.create(
                model=deployment,
                input=input_text,
                tools=[{
                    "type": "code_interpreter",
                    "container": {"type": "auto"}
                }],
            )

            execution_time = time.time() - start_time
            result = ExecutionResult.from_responses_api(response, execution_time)

            logger.info(
                f"Responses API analysis completed: "
                f"success={result.success}, time={execution_time:.2f}s"
            )

            return result

        except Exception as e:
            execution_time = time.time() - start_time
            logger.error(f"Responses API analysis failed: {e}")

            return ExecutionResult(
                success=False,
                output="",
                execution_time=execution_time,
                error=str(e),
                metadata={"api_mode": "responses", "error_type": type(e).__name__},
            )

    def _analyze_task_assistants_api(
        self,
        task: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> ExecutionResult:
        """使用 Assistants API 執行分析任務。"""
        manager = self._ensure_manager()
        result = manager.run_task(
            assistant_id=self._assistant_id,
            task=task,
            context=context,
            timeout=self._config.timeout,
        )
        return ExecutionResult.from_code_result(result)

    def execute_simple(self, prompt: str) -> ExecutionResult:
        """執行簡單的 Responses API 請求 (無 code_interpreter)。

        適用於不需要代碼執行的簡單問答。

        Args:
            prompt: 提問內容

        Returns:
            ExecutionResult 包含回應

        Example:
            ```python
            result = adapter.execute_simple("What is 25 * 48?")
            print(result.output)  # "1200"
            ```
        """
        start_time = time.time()

        try:
            client = self._get_openai_client()
            deployment = self._get_deployment()

            response = client.responses.create(
                model=deployment,
                input=prompt,
            )

            execution_time = time.time() - start_time

            # 提取輸出
            output_text = ""
            if hasattr(response, 'output_text'):
                output_text = response.output_text
            elif hasattr(response, 'output'):
                for item in response.output:
                    if hasattr(item, 'content'):
                        for c in item.content:
                            if hasattr(c, 'text'):
                                output_text += c.text

            return ExecutionResult(
                success=True,
                output=output_text.strip(),
                execution_time=execution_time,
                metadata={
                    "api_mode": "responses",
                    "response_id": getattr(response, 'id', ''),
                    "method": "simple",
                },
            )

        except Exception as e:
            execution_time = time.time() - start_time
            logger.error(f"Simple execution failed: {e}")

            return ExecutionResult(
                success=False,
                output="",
                execution_time=execution_time,
                error=str(e),
                metadata={"api_mode": "responses", "method": "simple"},
            )

    def cleanup(self) -> bool:
        """清理資源，刪除 Assistant。

        Returns:
            是否清理成功

        Note:
            - Assistants API: 刪除創建的 Assistant
            - Responses API: 無需清理
        """
        if not self._initialized:
            return True

        if self._active_api_mode == APIMode.ASSISTANTS and self._assistant_id:
            try:
                manager = self._ensure_manager()
                success = manager.delete_assistant(self._assistant_id)

                if success:
                    self._assistant_id = None
                    self._assistant_info = None
                    logger.info("CodeInterpreterAdapter cleaned up (Assistants API)")

                self._initialized = False
                return success
            except Exception as e:
                logger.error(f"Failed to cleanup CodeInterpreterAdapter: {e}")
                return False
        else:
            # Responses API 無需清理
            self._initialized = False
            logger.info("CodeInterpreterAdapter cleaned up (Responses API)")
            return True

    def __enter__(self) -> "CodeInterpreterAdapter":
        """Context manager 進入。"""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Context manager 退出。"""
        if self._config.auto_cleanup:
            self.cleanup()

    @property
    def is_initialized(self) -> bool:
        """檢查是否已初始化。"""
        return self._initialized

    @property
    def active_api_mode(self) -> Optional[APIMode]:
        """獲取當前使用的 API 模式。"""
        return self._active_api_mode

    @property
    def assistant_id(self) -> Optional[str]:
        """獲取當前 Assistant ID (僅 Assistants API)。"""
        return self._assistant_id

    @property
    def assistant_info(self) -> Optional[AssistantInfo]:
        """獲取當前 Assistant 信息 (僅 Assistants API)。"""
        return self._assistant_info

    @property
    def config(self) -> CodeInterpreterConfig:
        """獲取配置。"""
        return self._config
