import unittest
from unittest.mock import AsyncMock, patch

from fiberhome.scrapli_client import (
    PROMPT_PATTERN,
    FiberhomeClient,
)


class FiberhomeClientTests(unittest.IsolatedAsyncioTestCase):
    @patch("fiberhome.scrapli_client.AsyncGenericDriver")
    async def test_connect_builds_telnet_driver(self, driver_cls: AsyncMock) -> None:
        driver = AsyncMock()
        driver.get_prompt = AsyncMock(return_value="User>")
        driver_cls.return_value = driver
        client = FiberhomeClient("10.0.0.1", "user", "pass", port=2323, timeout=17)

        await client.connect()

        driver_cls.assert_called_once_with(
            host="10.0.0.1",
            port=2323,
            auth_username="user",
            auth_password="pass",
            auth_strict_key=False,
            auth_telnet_login_pattern=r"ogin:",
            auth_password_pattern=r"assword:",
            timeout_socket=17,
            timeout_transport=17,
            timeout_ops=17,
            comms_prompt_pattern=PROMPT_PATTERN,
            comms_return_char="\n",
            comms_roughly_match_inputs=False,
            transport="asynctelnet",
            transport_options={"ptyprocess": False},
        )
        driver.open.assert_awaited_once()
        driver.send_interactive.assert_awaited()

    @patch("fiberhome.scrapli_client.AsyncGenericDriver")
    async def test_send_command_returns_text_result(self, driver_cls: AsyncMock) -> None:
        driver = AsyncMock()
        driver.get_prompt = AsyncMock(return_value="User>")
        driver.send_command.return_value.result = "output"
        driver_cls.return_value = driver
        client = FiberhomeClient("10.0.0.1", "user", "pass")

        await client.connect()
        output = await client.send_command("show version")

        self.assertEqual(output, "output")
        driver.send_command.assert_awaited_with("show version", timeout_ops=None)

    @patch("fiberhome.scrapli_client.AsyncGenericDriver")
    async def test_disconnect_closes_driver(self, driver_cls: AsyncMock) -> None:
        driver = AsyncMock()
        driver.get_prompt = AsyncMock(return_value="User>")
        driver_cls.return_value = driver
        client = FiberhomeClient("10.0.0.1", "user", "pass")

        await client.connect()
        await client.disconnect()

        driver.close.assert_awaited_once()
