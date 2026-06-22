"""
预算控制(provider 无关)
==========================
对应文档第 1.3 / 9 节:预算必须在代码里强制,不能只写在 prompt 里。
跟踪 step 数、token 数、累计成本,任一超限即停止循环。
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class Budget:
    max_steps: int = 50
    max_tokens: int = 500_000
    max_cost_usd: float = 5.0

    # 运行时累计
    steps: int = 0
    input_tokens: int = 0
    output_tokens: int = 0
    cost_usd: float = 0.0

    def add_usage(self, input_tokens: int, output_tokens: int,
                  in_price_per_mtok: float, out_price_per_mtok: float) -> None:
        self.input_tokens += input_tokens
        self.output_tokens += output_tokens
        self.cost_usd += (
            input_tokens / 1_000_000 * in_price_per_mtok
            + output_tokens / 1_000_000 * out_price_per_mtok
        )

    def tick(self) -> None:
        self.steps += 1

    def exceeded(self) -> str | None:
        """返回超限原因,未超限返回 None。"""
        if self.steps >= self.max_steps:
            return f"达到步数上限 {self.max_steps}"
        if self.input_tokens + self.output_tokens >= self.max_tokens:
            return f"达到 token 上限 {self.max_tokens}"
        if self.cost_usd >= self.max_cost_usd:
            return f"达到成本上限 ${self.max_cost_usd}"
        return None

    def summary(self) -> str:
        return (
            f"steps={self.steps} "
            f"tokens={self.input_tokens}+{self.output_tokens} "
            f"cost=${self.cost_usd:.4f}"
        )
