#!/usr/bin/env python3
import sys
import urllib.request
import urllib.error
import subprocess
import os

def check_service(port):
    try:
        url = f"http://localhost:{port}"
        urllib.request.urlopen(url, timeout=5)
        return True
    except urllib.error.URLError:
        return False

def check_supervisor():
    try:
        result = subprocess.run(
            ["supervisorctl", "status"], 
            capture_output=True, 
            text=True
        )
        return all(
            "RUNNING" in line 
            for line in result.stdout.splitlines()
        )
    except Exception:
        return False

if __name__ == "__main__":
    # Check both UI and API ports
    ui_healthy = check_service(8501)
    api_healthy = check_service(8000)
    supervisor_healthy = check_supervisor()
    
    if ui_healthy and api_healthy and supervisor_healthy:
        sys.exit(0)
    else:
        sys.exit(1)