from __future__ import annotations

import os
import threading
import time
from typing import Optional

import psutil
from fastapi import FastAPI
from prometheus_client import Gauge
from prometheus_fastapi_instrumentator import Instrumentator


_PROCESS: Optional[psutil.Process] = None
_SAMPLER_THREAD: Optional[threading.Thread] = None
_STOP_EVENT: Optional[threading.Event] = None


# Gauges for system-level metrics
GAUGE_CPU_PERCENT = Gauge(
    "system_cpu_percent",
    "System-wide CPU utilization percent (psutil.getloadavg on Windows returns NotImplemented, using cpu_percent)",
)
GAUGE_MEM_USED_BYTES = Gauge(
    "system_memory_used_bytes",
    "System memory used in bytes",
)
GAUGE_MEM_AVAILABLE_BYTES = Gauge(
    "system_memory_available_bytes",
    "System memory available in bytes",
)

# Gauges for current process metrics
GAUGE_PROC_CPU_PERCENT = Gauge(
    "process_cpu_percent",
    "Current process CPU utilization percent",
)
GAUGE_PROC_RSS_BYTES = Gauge(
    "process_memory_rss_bytes",
    "Current process Resident Set Size in bytes",
)
GAUGE_PROC_VMS_BYTES = Gauge(
    "process_memory_vms_bytes",
    "Current process Virtual Memory Size in bytes",
)
GAUGE_OPEN_FDS = Gauge(
    "process_open_fds",
    "Number of open file descriptors/handles for the process (Windows counts handles)",
)


def _sample_metrics_loop(poll_seconds: float = 2.0) -> None:
    global _PROCESS
    assert _PROCESS is not None
    # Prime cpu_percent to avoid first-call 0.0
    _ = psutil.cpu_percent(interval=None)
    _ = _PROCESS.cpu_percent(interval=None)
    while _STOP_EVENT is not None and not _STOP_EVENT.is_set():
        try:
            # System
            cpu_percent = psutil.cpu_percent(interval=None)
            virt = psutil.virtual_memory()
            GAUGE_CPU_PERCENT.set(cpu_percent)
            GAUGE_MEM_USED_BYTES.set(virt.used)
            GAUGE_MEM_AVAILABLE_BYTES.set(virt.available)

            # Process
            proc_cpu = _PROCESS.cpu_percent(interval=None)
            mem_info = _PROCESS.memory_info()
            GAUGE_PROC_CPU_PERCENT.set(proc_cpu)
            GAUGE_PROC_RSS_BYTES.set(mem_info.rss)
            GAUGE_PROC_VMS_BYTES.set(mem_info.vms)

            # Open fds/handles
            try:
                if hasattr(_PROCESS, "num_handles"):
                    GAUGE_OPEN_FDS.set(_PROCESS.num_handles())  # Windows
                else:
                    GAUGE_OPEN_FDS.set(_PROCESS.num_fds())  # POSIX
            except Exception:
                # Some platforms may not support it; keep metric but skip update
                pass
        except Exception:
            # Avoid crashing the thread; next loop will retry
            pass
        time.sleep(poll_seconds)


def setup_metrics(app: FastAPI) -> None:
    """Attach Prometheus instrumentation and background sampler.

    - Exposes /metrics with default FastAPI request metrics
    - Samples system and process metrics via psutil periodically
    """

    # Standard HTTP metrics
    instrumentator = Instrumentator().instrument(app)
    instrumentator.expose(app, include_in_schema=False)

    # Background sampler for psutil metrics
    global _PROCESS, _STOP_EVENT, _SAMPLER_THREAD
    _PROCESS = psutil.Process(os.getpid())
    _STOP_EVENT = threading.Event()
    _SAMPLER_THREAD = threading.Thread(
        target=_sample_metrics_loop, name="metrics-sampler", args=(2.0,), daemon=True
    )

    @app.on_event("startup")
    async def _start_sampler() -> None:
        if _SAMPLER_THREAD is not None and not _SAMPLER_THREAD.is_alive():
            _SAMPLER_THREAD.start()

    @app.on_event("shutdown")
    async def _stop_sampler() -> None:
        if _STOP_EVENT is not None:
            _STOP_EVENT.set()
        if _SAMPLER_THREAD is not None and _SAMPLER_THREAD.is_alive():
            _SAMPLER_THREAD.join(timeout=2.0)


