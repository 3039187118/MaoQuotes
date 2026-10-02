"""语录数据库与选择策略。

设计上把「数据」与「选谁」分开：

* :class:`QuoteLibrary` 负责读取 ``data/quotes.json``；
* :class:`QuoteSelector` 是选择策略基类，
  已实现顺序 / 随机两种；
* :class:`TimeAwareSelector` 是为「AI 语录推荐」预留的接口示范，
  未来接入模型时只需实现一个新的 Selector 并在
  :func:`create_selector` 中注册即可，无需改动窗口与动画代码。
"""

from __future__ import annotations

import json
import logging
import random
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Iterable, Sequence

import paths

log = logging.getLogger(__name__)

DEFAULT_SOURCE_CN = "《毛泽东选集》"
DEFAULT_SOURCE_EN = "Selected Works of Mao Zedong"

# 兜底语录：当 quotes.json 缺失或损坏时仍能正常展示
FALLBACK_QUOTES = [
    {"id": 1, "cn": "没有调查，没有发言权", "en": "No investigation, no right to speak."},
    {"id": 2, "cn": "实事求是", "en": "Seek truth from facts."},
    {"id": 3, "cn": "从群众中来，到群众中去", "en": "From the masses, to the masses."},
]


@dataclass(frozen=True)
class Quote:
    """一条语录。"""

    id: int
    cn: str
    en: str
    source_cn: str = DEFAULT_SOURCE_CN
    source_en: str = DEFAULT_SOURCE_EN
    tags: tuple[str, ...] = field(default_factory=tuple)

    @classmethod
    def from_dict(cls, raw: dict, index: int) -> "Quote | None":
        cn = str(raw.get("cn", "")).strip()
        en = str(raw.get("en", "")).strip()
        if not cn and not en:
            return None
        tags = raw.get("tags") or ()
        if isinstance(tags, str):
            tags = (tags,)
        return cls(
            id=int(raw.get("id", index + 1)),
            cn=cn,
            en=en,
            source_cn=str(raw.get("source_cn") or DEFAULT_SOURCE_CN),
            source_en=str(raw.get("source_en") or DEFAULT_SOURCE_EN),
            tags=tuple(str(t) for t in tags),
        )


class QuoteLibrary:
    """语录库，支持热重载（用户改完 JSON 不必重启程序）。"""

    def __init__(self, path=None) -> None:
        self._path = path or paths.quotes_path()
        self._quotes: list[Quote] = []
        self._mtime: float | None = None
        self.reload()

    # ------------------------------------------------------------------ 加载
    def reload(self) -> bool:
        """重新读取 JSON；返回内容是否发生变化。"""
        raw_items: Sequence[dict]
        try:
            with open(self._path, "r", encoding="utf-8") as fp:
                data = json.load(fp)
            raw_items = data if isinstance(data, list) else data.get("quotes", [])
            self._mtime = self._path.stat().st_mtime
        except FileNotFoundError:
            log.warning("未找到语录文件 %s，使用内置兜底语录", self._path)
            raw_items = FALLBACK_QUOTES
        except (OSError, json.JSONDecodeError) as exc:
            log.warning("语录文件解析失败（%s），使用内置兜底语录", exc)
            raw_items = FALLBACK_QUOTES

        quotes: list[Quote] = []
        for i, raw in enumerate(raw_items):
            if not isinstance(raw, dict):
                continue
            quote = Quote.from_dict(raw, i)
            if quote is not None:
                quotes.append(quote)

        if not quotes:
            quotes = [Quote.from_dict(q, i) for i, q in enumerate(FALLBACK_QUOTES)]

        changed = quotes != self._quotes
        self._quotes = quotes
        return changed

    def reload_if_modified(self) -> bool:
        """文件被外部修改过才重新加载。"""
        try:
            mtime = self._path.stat().st_mtime
        except OSError:
            return False
        if self._mtime is not None and mtime <= self._mtime:
            return False
        return self.reload()

    # ------------------------------------------------------------------ 访问
    @property
    def path(self):
        return self._path

    @property
    def quotes(self) -> list[Quote]:
        return list(self._quotes)

    def __len__(self) -> int:
        return len(self._quotes)

    def __getitem__(self, index: int) -> Quote:
        return self._quotes[index % len(self._quotes)]


# --------------------------------------------------------------------- 选择器
class QuoteSelector(ABC):
    """选择策略基类。"""

    def __init__(self, library: QuoteLibrary) -> None:
        self.library = library

    @abstractmethod
    def next_index(self, current: int) -> int:
        """给出下一条语录的下标。"""

    def prev_index(self, current: int) -> int:
        """默认按下标回退，随机模式由历史栈接管。"""
        total = max(1, len(self.library))
        return (current - 1) % total


class SequentialSelector(QuoteSelector):
    """顺序播放。"""

    def next_index(self, current: int) -> int:
        total = max(1, len(self.library))
        return (current + 1) % total


class RandomSelector(QuoteSelector):
    """随机播放（洗牌袋算法：一轮之内不重复，轮末重新洗牌）。"""

    def __init__(self, library: QuoteLibrary) -> None:
        super().__init__(library)
        self._bag: list[int] = []

    def _refill(self, exclude: int | None) -> None:
        total = len(self.library)
        self._bag = list(range(total))
        random.shuffle(self._bag)
        # 避免与上一条重复
        if total > 1 and exclude is not None and self._bag and self._bag[-1] == exclude:
            self._bag[0], self._bag[-1] = self._bag[-1], self._bag[0]

    def next_index(self, current: int) -> int:
        if not self._bag:
            self._refill(current)
        if not self._bag:
            return 0
        return self._bag.pop()


class TimeAwareSelector(RandomSelector):
    """按时段挑选语录 —— 预留给「AI 语录推荐」的扩展示范。

    当前实现是纯本地规则：根据当前时间匹配语录的 ``tags``
    （morning / afternoon / evening / night），匹配不到时退化为随机。
    未来接入模型时，可在此基础上把 :meth:`candidates` 换成模型输出。
    """

    SLOTS = (
        (5, 11, "morning"),
        (11, 17, "afternoon"),
        (17, 22, "evening"),
        (22, 29, "night"),  # 22:00 - 次日 5:00
    )

    @classmethod
    def current_slot(cls, now: datetime | None = None) -> str:
        hour = (now or datetime.now()).hour
        for start, end, name in cls.SLOTS:
            if start <= hour < end or start <= hour + 24 < end:
                return name
        return "night"

    def candidates(self) -> list[int]:
        slot = self.current_slot()
        return [i for i, q in enumerate(self.library.quotes) if slot in q.tags]

    def next_index(self, current: int) -> int:
        pool = self.candidates()
        if len(pool) <= 1:
            return super().next_index(current)
        pool = [i for i in pool if i != current] or pool
        return random.choice(pool)


_SELECTORS = {
    "sequential": SequentialSelector,
    "random": RandomSelector,
    "time_aware": TimeAwareSelector,  # 预留，暂不在设置界面暴露
}


def create_selector(mode: str, library: QuoteLibrary) -> QuoteSelector:
    return _SELECTORS.get(mode, RandomSelector)(library)


class QuoteRotator:
    """对外统一的「当前语录 / 下一条 / 上一条」控制器。"""

    HISTORY_LIMIT = 64

    def __init__(self, library: QuoteLibrary, mode: str = "random") -> None:
        self.library = library
        self._mode = mode
        self._selector = create_selector(mode, library)
        self._index = 0
        self._history: list[int] = [0]
        self._history_pos = 0

    # ------------------------------------------------------------------ 属性
    @property
    def mode(self) -> str:
        return self._mode

    def set_mode(self, mode: str) -> None:
        if mode == self._mode:
            return
        self._mode = mode
        self._selector = create_selector(mode, self.library)

    @property
    def index(self) -> int:
        return self._index

    def current(self) -> Quote:
        if not len(self.library):
            self.library.reload()
        return self.library[self._index]

    # ------------------------------------------------------------------ 切换
    def next(self) -> Quote:
        # 若之前后退过，则先沿历史前进
        if self._history_pos < len(self._history) - 1:
            self._history_pos += 1
            self._index = self._history[self._history_pos]
            return self.current()

        self._index = self._selector.next_index(self._index)
        self._push_history(self._index)
        return self.current()

    def prev(self) -> Quote:
        if self._history_pos > 0:
            self._history_pos -= 1
            self._index = self._history[self._history_pos]
        else:
            self._index = self._selector.prev_index(self._index)
            self._history.insert(0, self._index)
            self._history = self._history[: self.HISTORY_LIMIT]
        return self.current()

    def jump_to(self, index: int) -> Quote:
        total = max(1, len(self.library))
        self._index = index % total
        self._push_history(self._index)
        return self.current()

    def clamp(self) -> None:
        """语录数量变化后修正下标。"""
        total = max(1, len(self.library))
        if self._index >= total:
            self._index = 0
            self._history = [0]
            self._history_pos = 0

    # ------------------------------------------------------------------ 内部
    def _push_history(self, index: int) -> None:
        self._history = self._history[: self._history_pos + 1]
        self._history.append(index)
        if len(self._history) > self.HISTORY_LIMIT:
            self._history = self._history[-self.HISTORY_LIMIT:]
        self._history_pos = len(self._history) - 1


def iter_quote_texts(quotes: Iterable[Quote]) -> Iterable[str]:
    """调试辅助。"""
    for q in quotes:
        yield f"{q.id}. {q.cn} / {q.en}"
