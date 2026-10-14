"""Synthetic file-backed performance checks available in the bundled runtime."""

import json
import os
import statistics
from pathlib import Path
from time import perf_counter


def process_memory() -> dict:
    """Windows high-water working set; includes earlier work in this process."""
    import ctypes
    from ctypes import wintypes

    class Counters(ctypes.Structure):
        _fields_ = [("cb", wintypes.DWORD), ("PageFaultCount", wintypes.DWORD)] + [
            (name, ctypes.c_size_t)
            for name in (
                "PeakWorkingSetSize",
                "WorkingSetSize",
                "QuotaPeakPagedPoolUsage",
                "QuotaPagedPoolUsage",
                "QuotaPeakNonPagedPoolUsage",
                "QuotaNonPagedPoolUsage",
                "PagefileUsage",
                "PeakPagefileUsage",
            )
        ]

    if os.name != "nt":
        return {"memory_measurement": "Windows process counters unavailable"}
    counters = Counters()
    counters.cb = ctypes.sizeof(counters)
    get_process = ctypes.windll.kernel32.GetCurrentProcess
    get_process.restype = wintypes.HANDLE
    get_memory = ctypes.windll.psapi.GetProcessMemoryInfo
    get_memory.argtypes = [wintypes.HANDLE, ctypes.POINTER(Counters), wintypes.DWORD]
    get_memory.restype = wintypes.BOOL
    if not get_memory(get_process(), ctypes.byref(counters), counters.cb):
        raise OSError("Windows process-memory measurement failed.")
    return {
        "process_peak_working_set_bytes": counters.PeakWorkingSetSize,
        "process_working_set_bytes": counters.WorkingSetSize,
        "memory_measurement": "Process cumulative working-set high-water; includes setup and earlier checks.",
    }


def benchmark(work: Path) -> dict:
    from sqlalchemy import create_engine, event
    from sqlalchemy.orm import Session

    from app.api.fsdp import analytics, paged_scholars
    from app.fsdp_reporting import fsdp_report_data
    from app.upgrade import upgrade_database

    work.mkdir(parents=True, exist_ok=False)
    results = []
    for count in (1000, 5000, 10000):
        path = work / f"synthetic-{count}.db"
        engine = create_engine(f"sqlite:///{path.as_posix()}")
        upgrade_database(engine, path)
        with engine.begin() as connection:
            connection.exec_driver_sql(
                "INSERT INTO programs (id,name,revision) VALUES (1,'Synthetic annual program',0)"
            )
            connection.exec_driver_sql(
                "INSERT INTO scholars (id,name,department,revision,missing_requirements,data_source,created_at,updated_at) VALUES (?,?,?,0,0,'Synthetic',CURRENT_TIMESTAMP,CURRENT_TIMESTAMP)",
                [
                    (index, f"Synthetic scholar {index:05}", f"Department {index % 10}")
                    for index in range(1, count + 1)
                ],
            )
            connection.exec_driver_sql(
                "INSERT INTO fsdp_participations (scholar_id,program_id,status,start_academic_year,start_term,grant_type,contract_completed_on) VALUES (?,1,?,?,?,'Full Scholarship','2020-01-01')",
                [
                    (
                        index,
                        "Graduated" if index % 4 == 0 and year == 2025 else "On Going",
                        f"{year}-{year + 1}",
                        "1st",
                    )
                    for index in range(1, count + 1)
                    for year in (2023, 2024, 2025)
                ],
            )
        with Session(engine) as database:
            checks = {
                "directory": lambda: paged_scholars(
                    search="", status_filter="", missing="", page=1, page_size=50, db=database
                ),
                "dashboard": lambda: analytics(department="", start_academic_year="", db=database),
                "report_page": lambda: fsdp_report_data(database, page=1, page_size=50),
            }
            timings = {}
            query_counter = [0]

            def count_query(*args, counter=query_counter):
                counter[0] += 1

            event.listen(engine, "before_cursor_execute", count_query)
            for name, operation in checks.items():
                query_counter[0] = 0
                cold = perf_counter()
                result = operation()
                query_count = query_counter[0]
                cold_ms = (perf_counter() - cold) * 1000
                samples = []
                for _ in range(5):
                    database.expire_all()
                    started = perf_counter()
                    operation()
                    samples.append((perf_counter() - started) * 1000)
                timings[name] = {
                    "cold_ms": round(cold_ms, 2),
                    "warm_median_ms": round(statistics.median(samples), 2),
                    "warm_max_ms": round(max(samples), 2),
                    "samples": len(samples),
                    "query_count_cold": query_count,
                    "response_bytes": len(
                        json.dumps(
                            result,
                            default=lambda value: (
                                value.model_dump(mode="json")
                                if hasattr(value, "model_dump")
                                else str(value)
                            ),
                        ).encode()
                    ),
                }
                timings[name].update(process_memory())
            results.append({"scholars": count, "grants": count * 3, "timings": timings})
        engine.dispose()
    return {
        "synthetic_only": True,
        "file_backed_sqlite": True,
        "hardware": os.environ.get("PROCESSOR_ARCHITECTURE", "unrecorded"),
        "processor": os.environ.get("PROCESSOR_IDENTIFIER", "unrecorded"),
        "results": results,
        "sampling_note": "Five warm samples; maximum is reported rather than claiming a statistically established p95.",
    }
