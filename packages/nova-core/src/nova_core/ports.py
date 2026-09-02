"""NovaAgent Core 的抽象端口。

端口只依赖 Core 的值对象和事件。具体网络客户端、数据库连接、锁与进程均由
上层 adapter 持有，不能经这些方法进入可序列化状态。
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import AsyncIterator
from datetime import datetime

from .events import AgentEvent, ModelEvent
from .types import (
    AgentRequest,
    ControlCommand,
    Correlation,
    Message,
    ModelRequest,
    PolicyDecision,
    Session,
    SessionHistory,
    ToolCall,
    ToolDefinition,
    ToolResult,
    TurnIdentity,
    TurnSnapshot,
)


class Agent(ABC):
    """运行一次 Turn 并以事件流作为唯一实时输出。"""

    @abstractmethod
    def stream(self, request: AgentRequest) -> AsyncIterator[AgentEvent]:
        """开始或恢复一次 Turn，并按产生顺序返回事件。"""

        raise NotImplementedError


class ModelGateway(ABC):
    """把唯一的 ModelRequest 转换为供应商无关事件流。"""

    @abstractmethod
    def stream(self, request: ModelRequest) -> AsyncIterator[ModelEvent]:
        """请求模型；实现不得写历史、snapshot 或 UI。"""

        raise NotImplementedError


class Tool(ABC):
    """声明 schema、安全属性并执行单个已编号工具调用。"""

    @property
    @abstractmethod
    def definition(self) -> ToolDefinition:
        """返回启动期不可变的工具定义。"""

        raise NotImplementedError

    @abstractmethod
    async def execute(self, call: ToolCall, correlation: Correlation) -> ToolResult:
        """执行调用；调用方负责先经过参数与策略检查。"""

        raise NotImplementedError

    async def on_cancel(self, call: ToolCall, correlation: Correlation) -> None:
        """释放该调用持有的外部资源；无状态工具可使用默认实现。"""


class PolicyGateway(ABC):
    """在工具副作用发生前给出唯一策略判定。"""

    @abstractmethod
    async def evaluate(
        self,
        call: ToolCall,
        definition: ToolDefinition,
        correlation: Correlation,
    ) -> PolicyDecision:
        """检查解析后的参数、风险、路径、网络和资源约束。"""

        raise NotImplementedError


class SessionStore(ABC):
    """保存会话身份与原始消息历史的端口。"""

    @abstractmethod
    async def create(self, session: Session) -> None:
        """创建新会话；同 ID 冲突必须显式失败。"""

        raise NotImplementedError

    @abstractmethod
    async def get(self, session_id: str) -> SessionHistory | None:
        """读取完整可重放历史；不存在时返回 ``None``。"""

        raise NotImplementedError

    @abstractmethod
    async def append_messages(
        self,
        session_id: str,
        messages: tuple[Message, ...],
        expected_version: int,
    ) -> int:
        """以乐观锁追加原始消息并返回新版本。"""

        raise NotImplementedError


class TurnStore(ABC):
    """保存当前 Turn snapshot 的端口。"""

    @abstractmethod
    async def load(self, turn_id: str) -> TurnSnapshot | None:
        """读取最近一次确认的 snapshot。"""

        raise NotImplementedError

    @abstractmethod
    async def save(self, snapshot: TurnSnapshot, expected_version: int | None) -> int:
        """创建或 compare-and-swap 更新 snapshot，并返回新版本。"""

        raise NotImplementedError


class EventStore(ABC):
    """为恢复和重放保存 append-only AgentEvent。"""

    @abstractmethod
    async def append(self, event: AgentEvent) -> None:
        """按 ``turn_id + seq`` 追加事件，禁止覆盖已有序号。"""

        raise NotImplementedError

    @abstractmethod
    async def read(self, turn_id: str, after_seq: int = -1) -> tuple[AgentEvent, ...]:
        """按 seq 升序返回游标之后的事件。"""

        raise NotImplementedError


class EventSink(ABC):
    """面向 UI、日志、测试和观测系统的实时事件端口。"""

    @abstractmethod
    async def publish(self, event: AgentEvent) -> None:
        """发布事件；可靠恢复仍以 EventStore 为事实源。"""

        raise NotImplementedError


class ControlPort(ABC):
    """运行时在安全点轮询外部取消、暂停和恢复命令。"""

    @abstractmethod
    async def poll(self, identity: TurnIdentity) -> ControlCommand | None:
        """返回下一条命令；没有待处理控制消息时返回 ``None``。"""

        raise NotImplementedError


class Clock(ABC):
    """为时间戳、超时与测试提供可替换时钟。"""

    @abstractmethod
    def now(self) -> datetime:
        """返回带时区的当前时间。"""

        raise NotImplementedError


class IdGenerator(ABC):
    """为事件、Turn、trace 与审批生成稳定 ID。"""

    @abstractmethod
    def new_id(self, namespace: str) -> str:
        """在给定命名空间内返回非空且不可复用的 ID。"""

        raise NotImplementedError
