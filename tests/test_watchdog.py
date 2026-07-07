"""Tests for the psutil RSS watchdog — the only working memory bound on macOS."""

import asyncio
import signal
import sys

from empiricist.executor.watchdog import RssWatchdog


async def spawn_py(code: str):
    return await asyncio.create_subprocess_exec(
        sys.executable, "-I", "-S", "-c", code,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        start_new_session=True,
    )


def test_breach_kills_process_group():
    async def scenario():
        # Allocate ~300 MB then idle; watchdog capped at 64 MB must kill it.
        proc = await spawn_py(
            "x = bytearray(300 * 1024 * 1024)\n"
            "import time; time.sleep(60)"
        )
        dog = RssWatchdog(proc.pid, rss_mb=64.0)
        task = asyncio.create_task(dog.run())
        rc = await asyncio.wait_for(proc.wait(), timeout=30)
        dog.stop()
        await task
        return rc, dog

    rc, dog = asyncio.run(scenario())
    assert rc == -signal.SIGKILL
    assert dog.killed is True
    assert dog.peak_mb > 64.0


def test_normal_process_untouched_and_peak_recorded():
    async def scenario():
        proc = await spawn_py(
            "x = bytearray(32 * 1024 * 1024)\nprint('ok')"
        )
        dog = RssWatchdog(proc.pid, rss_mb=512.0)
        task = asyncio.create_task(dog.run())
        rc = await asyncio.wait_for(proc.wait(), timeout=30)
        dog.stop()
        await task
        return rc, dog

    rc, dog = asyncio.run(scenario())
    assert rc == 0
    assert dog.killed is False
    assert dog.peak_mb > 0.0


def test_no_limit_only_observes():
    async def scenario():
        proc = await spawn_py("x = bytearray(64 * 1024 * 1024)\nprint('ok')")
        dog = RssWatchdog(proc.pid, rss_mb=None)
        task = asyncio.create_task(dog.run())
        rc = await asyncio.wait_for(proc.wait(), timeout=30)
        dog.stop()
        await task
        return rc, dog

    rc, dog = asyncio.run(scenario())
    assert rc == 0 and dog.killed is False and dog.peak_mb > 0.0


def test_already_dead_process_is_a_noop():
    async def scenario():
        proc = await spawn_py("pass")
        await proc.wait()
        dog = RssWatchdog(proc.pid, rss_mb=1.0)
        await dog.run()  # must return promptly, not raise
        return dog

    dog = asyncio.run(scenario())
    assert dog.killed is False
