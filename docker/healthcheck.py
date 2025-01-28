#!/usr/bin/env python3
import sys
import urllib.request
import urllib.error
import subprocess
import os
import asyncio
from src.core.services.db_service import DatabaseService
from src.utils.logging import logger

def check_database():
    """Check database connectivity."""
    try:
        db = DatabaseService()
        return asyncio.run(db.check_health())
    except Exception as e:
        logger.error(f"Database healthcheck failed: {e}")
        return False

def check_service(port: int, path: str = None) -> bool:
    """Check if a service is running on the specified port."""
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
                url = f"{url}/{path.lstrip('/')}"

        with urllib.request.urlopen(url, timeout=5) as response:
            return response.getcode() == 200
    except Exception as e:
        logger.error(f"Service healthcheck failed for port {port}: {e}")
        return False

def check_supervisor():
    """Check if supervisor processes are running."""
    try:
        result = subprocess.run(
            ["supervisorctl", "status"], 
            capture_output=True, 
            text=True,
            check=True
        )
        return all("RUNNING" in line for line in result.stdout.splitlines())
    except Exception as e:
        logger.error(f"Supervisor healthcheck failed: {e}")
        return False

def main():
    """Run all health checks."""
    try:
        # Check all services
        checks = {
            "UI": check_service(8501),
            "API": check_service(8000),
            "Database": check_database(),
            "Supervisor": check_supervisor()
        }
        
        # Log results
        for service, status in checks.items():
            logger.info(f"{service} health check: {'PASSED' if status else 'FAILED'}")
        
        # Exit with appropriate status
        if all(checks.values()):
            sys.exit(0)
        else:
            failed_services = [svc for svc, status in checks.items() if not status]
            logger.error(f"Health check failed for services: {', '.join(failed_services)}")
            sys.exit(1)
            
    except Exception as e:
        logger.error(f"Health check failed with error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()