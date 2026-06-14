#!/usr/bin/env python3
"""Quick server test script."""
import subprocess
import time
import sys

# Start the server
proc = subprocess.Popen(
    [sys.executable, "-m", "solara", "run", "portfolio_manager.solara_app", "--port", "8773", "--no-open"],
    cwd="/home/trooteye/Work/hermes_agent/hermes_data/portfolio-manager",
    stdout=subprocess.PIPE,
    stderr=subprocess.STDOUT,
)

# Wait for it to start
time.sleep(6)

# Check if port is listening
result = subprocess.run(["ss", "-tlnp"], capture_output=True, text=True)
listening = "8773" in result.stdout
print(f"Port 8773 listening: {listening}")

# Try to connect
result2 = subprocess.run(
    ["curl", "-s", "-o", "/dev/null", "-w", "%{http_code}", "http://localhost:8773/"],
    capture_output=True,
    text=True,
)
print(f"HTTP status: {result2.stdout.strip()}")

# Show server log
if proc.stdout:
    proc.stdout.seek(0)
    log = proc.stdout.read()
    print(f"Server log (last 500 chars):\n{log[-500:]}")

# Kill the server
proc.terminate()
proc.wait(timeout=5)
print("Server stopped")
