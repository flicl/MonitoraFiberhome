"""
Async Telnet client for Fiberhome OLT.

Provides reusable Telnet connection handling with proper login flow:
1. Banner → Login: → user
2. Password: → password → User>
3. EN → Password: → password → Admin#

Uses asyncio streams for non-blocking I/O.
"""

import asyncio
import logging
import re
from typing import Any

try:
    from .constants import (
        TELNET_TIMEOUT,
        CMD_WAIT_SHORT,
        CMD_WAIT_LONG,
        CMD_CD_SERVICE,
        CMD_CD_ONU,
        CMD_CD_CARD,
        CMD_CD_UP,
        CMD_TERMINAL_LENGTH_0,
    )
except ImportError:
    from constants import (
        TELNET_TIMEOUT,
        CMD_WAIT_SHORT,
        CMD_WAIT_LONG,
        CMD_CD_SERVICE,
        CMD_CD_ONU,
        CMD_CD_CARD,
        CMD_CD_UP,
        CMD_TERMINAL_LENGTH_0,
    )

logger = logging.getLogger(__name__)


class FiberhomeClient:
    """
    Async client for Fiberhome OLT via Telnet.

    Handles the two-level login flow and provides methods for
    executing commands in different CLI modes.
    """

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
        self._reader: asyncio.StreamReader | None = None
        self._writer: asyncio.StreamWriter | None = None
        self._buffer = ""

    async def __aenter__(self) -> "FiberhomeClient":
        """Establish connection and perform login sequence."""
        await self.connect()
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Close connection gracefully."""
        await self.disconnect()

    async def connect(self) -> None:
        """
        Establish Telnet connection and perform two-level login.

        Login flow:
        1. User level: username + password → User>
        2. Admin level: EN + password → Admin#
        """
        logger.info(f"Connecting to {self.host}:{self.port}")

        # Open Telnet connection
        self._reader, self._writer = await asyncio.wait_for(
            asyncio.open_connection(self.host, self.port),
            timeout=self.timeout,
        )

        # Wait for initial banner and login prompt
        await asyncio.sleep(1)
        initial_data = await self._read_until_blocking()

        # Check if we got Login and Password prompts together
        if "assword:" in initial_data.lower():
            # Login and Password already shown, send username first
            await self._send(self.username)
            await asyncio.sleep(CMD_WAIT_SHORT)
            await self._wait_for("assword:", clear_buffer=False)
            await self._send(self.password)
        elif "ogin:" in initial_data.lower():
            # Only Login shown, normal flow
            await self._send(self.username)
            await asyncio.sleep(CMD_WAIT_SHORT)
            await self._wait_for("assword:")
            await self._send(self.password)

        await asyncio.sleep(CMD_WAIT_SHORT)

        # Wait for User> prompt
        await self._wait_for("ser>")

        # Escalate to admin mode
        await self._send("EN")
        await asyncio.sleep(CMD_WAIT_SHORT)

        # Wait for Password: prompt (admin)
        await self._wait_for("assword:")
        await self._send(self.password)
        await asyncio.sleep(CMD_WAIT_SHORT)

        # Wait for Admin# prompt
        await self._wait_for("dmin#")

        # Disable pagination
        await self._setup_terminal()

        logger.info(f"Successfully logged in to {self.host}")

    async def _read_until_blocking(self, timeout: float = 3.0) -> str:
        """Read all available data without waiting for specific pattern."""
        if not self._reader:
            raise RuntimeError("Not connected")

        try:
            while True:
                chunk = await asyncio.wait_for(
                    self._reader.read(4096),
                    timeout=timeout,
                )
                if not chunk:
                    break
                self._buffer += chunk.decode("utf-8", errors="ignore")
        except asyncio.TimeoutError:
            pass  # Expected - no more data

        result = self._buffer
        logger.debug(f"Read until blocking: {repr(result[:500])}")
        return result

    async def _send(self, data: str) -> None:
        """Send data to the connection."""
        if not self._writer:
            raise RuntimeError("Not connected")
        self._writer.write((data + "\n").encode("utf-8"))
        await self._writer.drain()

    async def _wait_for(self, pattern: str, timeout: float | None = None, clear_buffer: bool = True) -> str:
        """
        Wait for a pattern in the output.

        Args:
            pattern: String or regex pattern to wait for
            timeout: Timeout in seconds
            clear_buffer: Whether to clear buffer after match

        Returns:
            Data received before pattern match
        """
        if not self._reader:
            raise RuntimeError("Not connected")

        timeout = timeout or self.timeout
        regex = re.compile(re.escape(pattern), re.IGNORECASE)

        try:
            while True:
                # Check existing buffer first
                if regex.search(self._buffer):
                    result = self._buffer
                    if clear_buffer:
                        self._buffer = ""
                    return result

                # Read available data
                chunk = await asyncio.wait_for(
                    self._reader.read(4096),
                    timeout=timeout,
                )
                if not chunk:
                    raise ConnectionError("Connection closed")

                self._buffer += chunk.decode("utf-8", errors="ignore")

                # Debug: show what we received
                logger.debug(f"Received: {repr(self._buffer[-200:])}")

        except asyncio.TimeoutError:
            logger.error(f"Timeout waiting for pattern: {pattern}")
            logger.debug(f"Buffer content: {self._buffer[:500]}")
            raise

    async def _read_until_prompt(self, prompt_pattern: str, timeout: float | None = None) -> str:
        """
        Read until a specific prompt pattern is found.

        Args:
            prompt_pattern: Regex pattern for the prompt
            timeout: Timeout in seconds

        Returns:
            All data received including the prompt
        """
        if not self._reader:
            raise RuntimeError("Not connected")

        timeout = timeout or self.timeout
        regex = re.compile(prompt_pattern)

        try:
            while True:
                chunk = await asyncio.wait_for(
                    self._reader.read(4096),
                    timeout=timeout,
                )
                if not chunk:
                    raise ConnectionError("Connection closed")

                self._buffer += chunk.decode("utf-8", errors="ignore")

                if regex.search(self._buffer):
                    result = self._buffer
                    self._buffer = ""
                    return result
        except asyncio.TimeoutError:
            logger.error(f"Timeout waiting for prompt: {prompt_pattern}")
            raise

    async def _setup_terminal(self) -> None:
        """Disable pagination in service mode."""
        await self.send_command(CMD_CD_SERVICE, r"Admin\\service#")
        await self.send_command(CMD_TERMINAL_LENGTH_0, r"Admin\\service#")
        await self.send_command(CMD_CD_UP, r"Admin#")

    async def send_command(
        self,
        command: str,
        prompt_pattern: str = r"Admin#",
        timeout: float | None = None,
    ) -> str:
        """
        Send a command and return the output.

        Args:
            command: CLI command to execute
            prompt_pattern: Regex pattern for expected prompt
            timeout: Optional timeout override

        Returns:
            Command output as string
        """
        if not self._writer:
            raise RuntimeError("Not connected")

        logger.debug(f"Sending command: {command}")

        self._buffer = ""
        self._writer.write((command + "\n").encode("utf-8"))
        await self._writer.drain()

        output = await self._read_until_prompt(prompt_pattern, timeout)
        return output

    async def collect_onu_authorization(self) -> str:
        """
        Collect ONU authorization data from all slots/PONs.

        Returns:
            Raw CLI output from 'show authorization slot all pon all'
        """
        # Enter ONU mode
        await self.send_command(CMD_CD_ONU, r"Admin\\onu#")

        # Collect data with extended timeout for large ONU counts
        output = await self.send_command(
            "show authorization slot all pon all",
            r"Admin\\onu#",
            timeout=CMD_WAIT_LONG + 10,
        )

        # Return to admin mode
        await self.send_command(CMD_CD_UP, r"Admin#")

        return output

    async def collect_pon_signals(self, slot: str, pon: str) -> str:
        """
        Collect optical signal data for a specific PON.

        Args:
            slot: Slot number
            pon: PON port number

        Returns:
            Raw CLI output from 'show optic_module_para slot X pon Y'
        """
        # Enter card mode
        await self.send_command(CMD_CD_CARD, r"Admin\\card#")

        # Collect signal data
        output = await self.send_command(
            f"show optic_module_para slot {slot} pon {pon}",
            r"Admin\\card#",
            timeout=15,
        )

        # Return to admin mode
        await self.send_command(CMD_CD_UP, r"Admin#")

        return output

    async def disconnect(self) -> None:
        """Close connection gracefully."""
        if self._writer:
            try:
                await self.send_command("cd ..", r"Admin#|User>", timeout=3)
                await self.send_command("quit", r"User>|Login:", timeout=3)
                await self.send_command("quit", r"Login:", timeout=3)
            except Exception:
                pass
            finally:
                self._writer.close()
                await self._writer.wait_closed()
                self._writer = None
                self._reader = None
                logger.info(f"Disconnected from {self.host}")
