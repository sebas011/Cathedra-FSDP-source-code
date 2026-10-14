import asyncio
from types import SimpleNamespace

from app.request_gate import RestoreGateMiddleware, RestoreRequestGate, finish_before_release


def test_repeated_cancellation_keeps_gate_until_worker_finishes():
    import threading

    async def scenario():
        gate = RestoreRequestGate()
        entered = threading.Event()
        release = threading.Event()

        def work():
            entered.set()
            release.wait(timeout=5)

        async def protected():
            async with gate.exclusive():
                await finish_before_release(asyncio.to_thread(work))

        operation = asyncio.create_task(protected())
        await asyncio.to_thread(entered.wait, 1)
        operation.cancel()
        await asyncio.sleep(0)
        operation.cancel()
        await asyncio.sleep(0.02)
        assert gate._restore_active
        assert not operation.done()
        release.set()
        try:
            await operation
        except asyncio.CancelledError:
            pass
        async with gate.shared():
            assert not gate._restore_active

    asyncio.run(scenario())


def test_cancelled_authorization_keeps_shared_lease_until_session_cleanup():
    import threading

    async def scenario():
        gate = RestoreRequestGate()
        entered = threading.Event()
        release = threading.Event()
        closed = threading.Event()

        def work():
            entered.set()
            try:
                release.wait(timeout=5)
            finally:
                closed.set()

        async def protected():
            async with gate.shared():
                await finish_before_release(asyncio.to_thread(work))

        operation = asyncio.create_task(protected())
        await asyncio.to_thread(entered.wait, 1)
        operation.cancel()
        await asyncio.sleep(0.02)
        assert gate._active_requests == 1 and not closed.is_set()
        release.set()
        try:
            await operation
        except asyncio.CancelledError:
            pass
        async with gate.exclusive():
            assert closed.is_set()

    asyncio.run(scenario())


def test_ordinary_requests_can_overlap() -> None:
    async def scenario() -> None:
        gate = RestoreRequestGate()
        first_entered = asyncio.Event()
        release_first = asyncio.Event()
        second_entered = asyncio.Event()

        async def first_request() -> None:
            async with gate.shared():
                first_entered.set()
                await release_first.wait()

        async def second_request() -> None:
            async with gate.shared():
                second_entered.set()

        first = asyncio.create_task(first_request())
        await asyncio.wait_for(first_entered.wait(), timeout=1)
        await asyncio.wait_for(second_request(), timeout=1)
        assert second_entered.is_set()
        release_first.set()
        await asyncio.wait_for(first, timeout=1)

    asyncio.run(scenario())


def test_restore_drains_existing_requests_and_blocks_new_ones() -> None:
    async def scenario() -> None:
        gate = RestoreRequestGate()
        first_entered = asyncio.Event()
        release_first = asyncio.Event()
        restore_entered = asyncio.Event()
        release_restore = asyncio.Event()
        second_entered = asyncio.Event()

        async def first_request() -> None:
            async with gate.shared():
                first_entered.set()
                await release_first.wait()

        async def restore_request() -> None:
            async with gate.exclusive():
                restore_entered.set()
                await release_restore.wait()

        async def second_request() -> None:
            async with gate.shared():
                second_entered.set()

        first = asyncio.create_task(first_request())
        await asyncio.wait_for(first_entered.wait(), timeout=1)
        restore = asyncio.create_task(restore_request())
        await asyncio.sleep(0)
        second = asyncio.create_task(second_request())
        await asyncio.sleep(0)
        assert not restore_entered.is_set()
        assert not second_entered.is_set()
        release_first.set()
        await asyncio.wait_for(restore_entered.wait(), timeout=1)
        assert not second_entered.is_set()
        release_restore.set()
        await asyncio.wait_for(asyncio.gather(first, restore, second), timeout=1)
        assert second_entered.is_set()

    asyncio.run(scenario())


def test_cancelled_restore_does_not_hold_the_gate() -> None:
    async def scenario() -> None:
        gate = RestoreRequestGate()
        async with gate.shared():
            waiting_restore = asyncio.create_task(gate.exclusive().__aenter__())
            await asyncio.sleep(0)
            waiting_restore.cancel()
            try:
                await waiting_restore
            except asyncio.CancelledError:
                pass
            async with gate.shared():
                pass

    asyncio.run(asyncio.wait_for(scenario(), timeout=1))


def test_restore_route_uses_exclusive_gate(monkeypatch) -> None:
    monkeypatch.setattr("app.request_gate.authorize_restore", lambda scope: None)

    async def scenario() -> None:
        gate = RestoreRequestGate()
        restore_entered = asyncio.Event()
        release_restore = asyncio.Event()
        ordinary_entered = asyncio.Event()

        async def downstream(scope, receive, send) -> None:
            if scope["path"] == "/api/v1/maintenance/restore":
                restore_entered.set()
                await release_restore.wait()
            else:
                ordinary_entered.set()

        async def unused(*args):
            return {"type": "http.request", "body": b"{}", "more_body": False}

        middleware = RestoreGateMiddleware(downstream)
        application = SimpleNamespace(state=SimpleNamespace(restore_request_gate=gate))
        restore_scope = {
            "type": "http",
            "method": "POST",
            "path": "/api/v1/maintenance/restore",
            "app": application,
        }
        ordinary_scope = {
            "type": "http",
            "method": "GET",
            "path": "/api/v1/health",
            "app": application,
        }
        restore = asyncio.create_task(middleware(restore_scope, unused, unused))
        await asyncio.wait_for(restore_entered.wait(), timeout=1)
        ordinary = asyncio.create_task(middleware(ordinary_scope, unused, unused))
        await asyncio.sleep(0)
        assert not ordinary_entered.is_set()
        release_restore.set()
        await asyncio.wait_for(asyncio.gather(restore, ordinary), timeout=1)
        assert ordinary_entered.is_set()

    asyncio.run(scenario())
