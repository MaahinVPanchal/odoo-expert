#!/usr/bin/env python3
import sys
import urllib.request
import urllib.error
import subprocess
import os

def check_service(port, path=None):
    """Check if a service is running on the specified port.
    
    Args:
        port (int): The port number to check
        path (str, optional): The path to check. Defaults to None.
    """
    try:
        # For API service (port 8000), check the OpenAPI docs endpoint
        if port == 8000:
            url = f"http://localhost:{port}/docs"
        # For Streamlit (port 8501), check the root path
        elif port == 8501:
            url = f"http://localhost:{port}"
        else:
            url = f"http://localhost:{port}"
            if path:
                url = f"{url}{path}"
                
        urllib.request.urlopen(url, timeout=5)
        return True
    except urllib.error.URLError:
        return False

def check_supervisor():
    """Check if supervisor processes are running."""
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