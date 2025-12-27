import httpx
import pytest

from retry import async_retry


class TestAsyncRetry:
    @pytest.mark.asyncio
    async def test_succeeds_on_first_attempt(self):
        call_count = 0

        @async_retry(max_attempts=3)
        async def succeed_immediately():
            nonlocal call_count
            call_count += 1
            return "success"

        result = await succeed_immediately()
        assert result == "success"
        assert call_count == 1

    @pytest.mark.asyncio
    async def test_retries_on_timeout(self):
        call_count = 0

        @async_retry(max_attempts=3, backoff_factor=0.1)
        async def fail_then_succeed():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise httpx.TimeoutException("Timeout")
            return "success"

        result = await fail_then_succeed()
        assert result == "success"
        assert call_count == 3

    @pytest.mark.asyncio
    async def test_fails_after_max_attempts(self):
        call_count = 0

        @async_retry(max_attempts=3, backoff_factor=0.1)
        async def always_fails():
            nonlocal call_count
            call_count += 1
            raise httpx.ConnectError("Connection failed")

        with pytest.raises(httpx.ConnectError):
            await always_fails()

        assert call_count == 3

    @pytest.mark.asyncio
    async def test_does_not_retry_on_other_exceptions(self):
        call_count = 0

        @async_retry(max_attempts=3)
        async def raises_value_error():
            nonlocal call_count
            call_count += 1
            raise ValueError("Not a network error")

        with pytest.raises(ValueError):
            await raises_value_error()

        assert call_count == 1

    @pytest.mark.asyncio
    async def test_custom_exceptions(self):
        @async_retry(max_attempts=3, backoff_factor=0.1, exceptions=(ValueError,))
        async def custom_exception():
            raise ValueError("Custom")

        with pytest.raises(ValueError):
            await custom_exception()

    @pytest.mark.asyncio
    async def test_retries_on_connect_error(self):
        call_count = 0

        @async_retry(max_attempts=2, backoff_factor=0.1)
        async def connection_error():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise httpx.ConnectError("Connection failed")
            return "connected"

        result = await connection_error()
        assert result == "connected"
        assert call_count == 2

    @pytest.mark.asyncio
    async def test_retries_on_read_timeout(self):
        call_count = 0

        @async_retry(max_attempts=2, backoff_factor=0.1)
        async def read_timeout():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise httpx.ReadTimeout("Read timeout")
            return "read"

        result = await read_timeout()
        assert result == "read"
        assert call_count == 2
