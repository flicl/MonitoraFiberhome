"""
Async Telnet client for Fiberhome OLT using Scrapli.
"""

import logging
from time import perf_counter

from scrapli.driver.generic.async_driver import AsyncGenericDriver

try:
    from .constants import (
        CMD_CD_CARD,
        CMD_CD_ONU,
        CMD_CD_SERVICE,
        CMD_CD_UP,
        CMD_SHOW_AUTH_ALL,
        CMD_SHOW_SIGNAL,
        CMD_TERMINAL_LENGTH_0,
        TELNET_TIMEOUT,
    )
except ImportError:
    from constants import (
        CMD_CD_CARD,
        CMD_CD_ONU,
        CMD_CD_SERVICE,
        CMD_CD_UP,
        CMD_SHOW_AUTH_ALL,
        CMD_SHOW_SIGNAL,
        CMD_TERMINAL_LENGTH_0,
        TELNET_TIMEOUT,
    )

logger = logging.getLogger(__name__)

PROMPT_PATTERN = r"(?:User>|Admin#|Admin\\service#|Admin\\onu#|Admin\\card#)\s*$"


class FiberhomeClient:
    """Async client for Fiberhome OLT via Telnet using Scrapli."""

    def __init__(
        self,
        host: str,
        username: str,
        password: str,
        port: int = 23,
        timeout: int = TELNET_TIMEOUT,
    ) -> None:
        self.host = host
        self.username = username
        self.password = password
        self.port = port
        self.timeout = timeout
        self._driver: AsyncGenericDriver | None = None

    async def __aenter__(self) -> "FiberhomeClient":
        await self.connect()
        return self

    async def __aexit__(self, exc_type: object, exc_val: object, exc_tb: object) -> None:
        await self.disconnect()

    def _build_driver(self) -> AsyncGenericDriver:
        return AsyncGenericDriver(
            host=self.host,
            port=self.port,
            auth_username=self.username,
            auth_password=self.password,
            auth_strict_key=False,
            auth_telnet_login_pattern=r"ogin:",
            auth_password_pattern=r"assword:",
            timeout_socket=self.timeout,
            timeout_transport=self.timeout,
            timeout_ops=self.timeout,
            comms_prompt_pattern=PROMPT_PATTERN,
            comms_return_char="\n",
            comms_roughly_match_inputs=False,
            transport="asynctelnet",
            transport_options={"ptyprocess": False},
        )

    async def connect(self) -> None:
        """Open the Telnet session, elevate to admin, and disable paging."""
        if self._driver is not None:
            return

        started_at = perf_counter()
        logger.info("Connecting to host=%s port=%s", self.host, self.port)
        driver = self._build_driver()
        await driver.open()

        prompt = await driver.get_prompt()
        if "Admin#" not in prompt:
            await driver.send_interactive(
                [
                    ("EN", "assword:", False),
                    (self.password, "Admin#", True),
                ],
                interaction_complete_patterns=[PROMPT_PATTERN],
            )

        self._driver = driver
        await self._setup_terminal()
        elapsed_ms = round((perf_counter() - started_at) * 1000)
        logger.info(
            "Connected to host=%s result=success duration_ms=%s",
            self.host,
            elapsed_ms,
        )

    async def _setup_terminal(self) -> None:
        await self.send_command(CMD_CD_SERVICE)
        await self.send_command(CMD_TERMINAL_LENGTH_0)
        await self.send_command(CMD_CD_UP)

    async def send_command(self, command: str, timeout: float | None = None) -> str:
        """Send a command and return the parsed text result."""
        if self._driver is None:
            raise RuntimeError("Not connected")

        started_at = perf_counter()
        response = await self._driver.send_command(command, timeout_ops=timeout)
        elapsed_ms = round((perf_counter() - started_at) * 1000)
        logger.debug(
            "Command complete host=%s action=%s result=success duration_ms=%s",
            self.host,
            command,
            elapsed_ms,
        )
        return response.result

    async def collect_onu_authorization(self) -> str:
        await self.send_command(CMD_CD_ONU)
        output = await self.send_command(CMD_SHOW_AUTH_ALL, timeout=self.timeout + 25)
        await self.send_command(CMD_CD_UP)
        return output

    async def collect_pon_signals(self, slot: str, pon: str) -> str:
        await self.send_command(CMD_CD_CARD)
        output = await self.send_command(
            CMD_SHOW_SIGNAL.format(slot=slot, pon=pon),
            timeout=15,
        )
        await self.send_command(CMD_CD_UP)
        return output

    async def disconnect(self) -> None:
        """Close the underlying Scrapli driver."""
        if self._driver is None:
            return

        started_at = perf_counter()
        driver = self._driver
        self._driver = None
        try:
            await driver.close()
        finally:
            elapsed_ms = round((perf_counter() - started_at) * 1000)
            logger.info(
                "Disconnected from host=%s result=success duration_ms=%s",
                self.host,
                elapsed_ms,
            )
