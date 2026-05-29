"""
ATHU Module - Trading Agent
IMPORTANT: THIS MODULE REQUIRES MANDATORY HUMAN CONFIRMATION BEFORE ANY TRADE.
No order is ever placed without explicit user confirmation (voice or button click).
Dry-run mode is on by default.

RISK DISCLAIMER: Trading involves significant financial risk. ATHU is not a licensed
financial adviser. All trading decisions are solely the responsibility of the user.
Use this module at your own risk.
"""

import logging
from typing import Callable

from modules.base_module import BaseModule
from core.logger import log_trade

logger = logging.getLogger("athu.trading")

RISK_DISCLAIMER = (
    "WARNING: Trading module activated. "
    "ATHU will NEVER execute trades without your explicit confirmation. "
    "Dry-run mode is active by default. "
    "Trading involves significant financial risk. "
    "ATHU is not a financial adviser."
)


class TradingAgent(BaseModule):
    MODULE_NAME = "trading"

    def __init__(self, config: dict):
        super().__init__(config)
        self._killed = False
        self._dry_run = self.module_config.get("dry_run", True)
        logger.warning(RISK_DISCLAIMER)

    def get_tools(self) -> list[tuple[str, dict, Callable]]:
        return [
            (
                "check_trading_conditions",
                {
                    "name": "check_trading_conditions",
                    "description": "Check if trading conditions for a strategy are met.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "strategy": {"type": "string", "description": "Strategy name"},
                            "ticker": {"type": "string", "description": "Stock ticker symbol"},
                        },
                        "required": ["strategy", "ticker"],
                    },
                },
                self.check_trading_conditions,
            ),
            (
                "request_trade_confirmation",
                {
                    "name": "request_trade_confirmation",
                    "description": "Request user confirmation before placing a trade. ALWAYS call before any trade.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "action": {"type": "string", "enum": ["BUY", "SELL"]},
                            "ticker": {"type": "string"},
                            "quantity": {"type": "number"},
                            "price": {"type": "number"},
                            "strategy": {"type": "string"},
                        },
                        "required": ["action", "ticker", "quantity", "price", "strategy"],
                    },
                },
                self.request_trade_confirmation,
            ),
            (
                "abort_all_trading",
                {
                    "name": "abort_all_trading",
                    "description": "Emergency kill switch. Immediately suspends all trading activity.",
                    "parameters": {"type": "object", "properties": {}, "required": []},
                },
                self.abort_all_trading,
            ),
        ]

    async def check_trading_conditions(self, strategy: str, ticker: str) -> str:
        if self._killed:
            return "Trading module has been suspended via kill switch."
        return (
            "[DRY RUN] Checking conditions for strategy '" + strategy + "' on " + ticker + ". "
            "Rule engine not yet implemented. See Phase 4."
        )

    async def request_trade_confirmation(
        self, action: str, ticker: str, quantity: float, price: float, strategy: str
    ) -> str:
        if self._killed:
            return "Trading module has been suspended via kill switch."
        mode = "[DRY RUN] " if self._dry_run else ""
        msg = (
            mode + "Sir, conditions met for '" + strategy + "'. "
            + action + " " + str(quantity) + " shares of " + ticker
            + " at $" + str(round(price, 2)) + ". "
            "Please confirm via voice ('Confirm') or the trading panel button."
        )
        await log_trade(
            strategy=strategy, ticker=ticker, action=action,
            quantity=quantity, price=price, confirmed=False,
            dry_run=self._dry_run, result="awaiting_confirmation"
        )
        return msg

    async def abort_all_trading(self) -> str:
        self._killed = True
        logger.critical("TRADING KILL SWITCH ACTIVATED.")
        return "Trading module suspended. No further trades will be proposed or executed until restart."
