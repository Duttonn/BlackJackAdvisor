"""
Pytest Configuration and Test Logging System.

This module configures pytest to automatically capture and log the details
of every test run into timestamped files in the test_results/ directory.

Features:
- Session-level logging with start/end timestamps
- Per-test logging with outcome, duration, and tracebacks
- Captured stdout/stderr for debugging
"""

import pytest
import os
from datetime import datetime

# Create test_results directory if it doesn't exist
RESULTS_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "test_results")
os.makedirs(RESULTS_DIR, exist_ok=True)

# Generate a single log file name for this session
SESSION_TIMESTAMP = datetime.now().strftime("%Y%m%d_%H%M%S")
LOG_FILE = os.path.join(RESULTS_DIR, f"test_run_{SESSION_TIMESTAMP}.log")


@pytest.hookimpl(tryfirst=True, hookwrapper=True)
def pytest_runtest_makereport(item, call):
    """
    Hook to capture test execution details and log them to a file.
    
    This hook intercepts test reports and writes detailed log entries
    for each test, including name, status, duration, and captured output.
    """
    # Execute all other hooks to obtain the report object
    outcome = yield
    report = outcome.get_result()

    # We only care about the 'call' phase (when the test actually runs)
    # or setup/teardown if they fail.
    if report.when == "call" or (report.when in ("setup", "teardown") and report.failed):
        
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            header = f"TEST: {item.nodeid}"
            f.write("=" * 80 + "\n")
            f.write(f"{header}\n")
            f.write(f"TIMESTAMP: {datetime.now().strftime('%H:%M:%S')}\n")
            f.write(f"OUTCOME: {'FAILED' if report.failed else 'PASSED'}\n")
            f.write(f"DURATION: {report.duration:.4f}s\n")
            
            # Capture stdout/stderr if available
            if hasattr(report, "sections"):
                for section_name, content in report.sections:
                    f.write(f"\n--- {section_name} ---\n")
                    f.write(content)
            
            # If there was an exception info (traceback)
            if report.longrepr:
                f.write("\n--- TRACEBACK ---\n")
                f.write(str(report.longrepr))
            
            f.write("\n" + ("-" * 80) + "\n\n")


@pytest.fixture(scope="session", autouse=True)
def log_session_start_end():
    """Log the start and end of the test session."""
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write("#" * 80 + "\n")
        f.write(f"TEST SESSION STARTED: {datetime.now()}\n")
        f.write("#" * 80 + "\n\n")
    
    yield
    
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write("\n" + "#" * 80 + "\n")
        f.write(f"TEST SESSION FINISHED: {datetime.now()}\n")
        f.write("#" * 80 + "\n")


def pytest_collection_modifyitems(config, items):
    """
    Log collected test count at the start of collection.
    """
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(f"COLLECTED: {len(items)} tests\n\n")
