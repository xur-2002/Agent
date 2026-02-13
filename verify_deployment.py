#!/usr/bin/env python3
"""
Pre-deployment verification script for Agent MVP.
Validates JSON, Task instantiation, Feishu connectivity (mock), and workflow readiness.

Usage:
  python verify_deployment.py
"""

import json
import sys
import os
from pathlib import Path
from typing import Tuple, List, Dict


def check_tasks_json() -> Tuple[bool, str]:
    """Verify tasks.json is valid and has correct schema."""
    try:
        tasks_path = Path("tasks.json")
        if not tasks_path.exists():
            return False, "❌ tasks.json not found"
        
        with open(tasks_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        # Check if it's a list
        if not isinstance(data, list):
            return False, "❌ tasks.json must be a top-level JSON array"
        
        if len(data) == 0:
            return False, "❌ tasks.json is empty (need at least 1 task)"
        
        # Validate each task has required fields
        for i, task in enumerate(data):
            if not isinstance(task, dict):
                return False, f"❌ Task {i} is not a dict"
            
            if "id" not in task or "title" not in task:
                return False, f"❌ Task {i} missing 'id' or 'title' field"
        
        return True, f"✅ tasks.json valid: {len(data)} tasks found"
    
    except json.JSONDecodeError as e:
        return False, f"❌ JSON parse error: {e}"
    except Exception as e:
        return False, f"❌ Unexpected error: {e}"


def check_task_instantiation() -> Tuple[bool, str]:
    """Verify Task dataclass can be instantiated from JSON."""
    try:
        from agent.models import Task
        
        tasks_path = Path("tasks.json")
        with open(tasks_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        loaded_count = 0
        for task_dict in data:
            task = Task.from_dict(task_dict)
            if not (task.id and task.title):
                return False, f"❌ Task instantiation failed: missing id or title"
            loaded_count += 1
        
        return True, f"✅ Task instantiation successful: {loaded_count} tasks loaded"
    
    except Exception as e:
        return False, f"❌ Task instantiation error: {e}"


def check_storage_backend() -> Tuple[bool, str]:
    """Verify storage backend can load tasks."""
    try:
        from agent.storage import JsonFileStorage
        
        storage = JsonFileStorage()
        tasks = storage.load_tasks()
        
        if not tasks:
            return False, "❌ Storage backend returned no tasks"
        
        return True, f"✅ Storage backend working: {len(tasks)} tasks loaded"
    
    except Exception as e:
        return False, f"❌ Storage backend error: {e}"


def check_requirements() -> Tuple[bool, str]:
    """Verify all required Python packages are installed."""
    required_packages = ["requests", "pytz"]
    missing = []
    
    for package in required_packages:
        try:
            __import__(package)
        except ImportError:
            missing.append(package)
    
    if missing:
        return False, f"❌ Missing packages: {', '.join(missing)}. Run: pip install -r requirements.txt"
    
    return True, f"✅ All required packages installed"


def check_workflow_file() -> Tuple[bool, str]:
    """Verify GitHub Actions workflow is using v4 of upload-artifact."""
    try:
        workflow_path = Path(".github/workflows/agent.yml")
        if not workflow_path.exists():
            return False, "❌ .github/workflows/agent.yml not found"
        
        content = workflow_path.read_text()
        
        # Check for v3 (old, should not exist)
        if "actions/upload-artifact@v3" in content:
            return False, "❌ Workflow still using upload-artifact@v3 (should be @v4)"
        
        # Check for v4 (new, should exist)
        if "actions/upload-artifact@v4" not in content:
            return False, "❌ Workflow not using upload-artifact@v4"
        
        # Check for log capture
        if "tee run-log.txt" not in content:
            return False, "❌ Workflow not capturing logs with 'tee run-log.txt'"
        
        return True, "✅ GitHub Actions workflow ready (v4, log capture enabled)"
    
    except Exception as e:
        return False, f"❌ Workflow check error: {e}"


def check_feishu_env() -> Tuple[bool, str]:
    """Verify Feishu webhook URL is accessible via environment."""
    webhook_url = os.getenv("FEISHU_WEBHOOK_URL")
    
    if webhook_url:
        return True, f"✅ FEISHU_WEBHOOK_URL is set ({len(webhook_url)} chars)"
    else:
        return True, "⚠️  FEISHU_WEBHOOK_URL not set (will be set by GitHub Actions Secret)"


def check_module_imports() -> Tuple[bool, str]:
    """Verify all agent modules can be imported."""
    modules = [
        "agent.models",
        "agent.storage",
        "agent.scheduler",
        "agent.task_runner",
        "agent.feishu",
        "agent.main",
    ]
    
    failed = []
    for module_name in modules:
        try:
            __import__(module_name)
        except ImportError as e:
            failed.append(f"{module_name}: {e}")
    
    if failed:
        return False, f"❌ Module import errors: {', '.join(failed)}"
    
    return True, f"✅ All agent modules importable"


def main():
    """Run all verification checks."""
    print("=" * 70)
    print(" 🚀 AGENT MVP PRE-DEPLOYMENT VERIFICATION")
    print("=" * 70)
    print()
    
    checks = [
        ("JSON Schema", check_tasks_json),
        ("Task Instantiation", check_task_instantiation),
        ("Storage Backend", check_storage_backend),
        ("Python Dependencies", check_requirements),
        ("GitHub Actions Workflow", check_workflow_file),
        ("Feishu Environment", check_feishu_env),
        ("Module Imports", check_module_imports),
    ]
    
    results: List[Tuple[str, bool, str]] = []
    
    for check_name, check_func in checks:
        print(f"Checking {check_name}...", end=" ")
        try:
            success, message = check_func()
            results.append((check_name, success, message))
            print(message)
        except Exception as e:
            error_msg = f"❌ Exception in {check_name}: {e}"
            results.append((check_name, False, error_msg))
            print(error_msg)
        
        print()
    
    # Summary
    print("=" * 70)
    print(" VERIFICATION SUMMARY")
    print("=" * 70)
    
    passed = sum(1 for _, success, _ in results if success)
    total = len(results)
    
    print(f"Passed: {passed}/{total}")
    print()
    
    if passed == total:
        print("✅ ALL CHECKS PASSED - Ready for GitHub Actions deployment!")
        print()
        print("Next steps:")
        print("  1. git add .")
        print("  2. git commit -m 'fix: upgrade workflow and fix tasks.json'")
        print("  3. git push origin main")
        print("  4. Go to GitHub Actions and run workflow manually")
        print("  5. Check Feishu for message within 30 seconds")
        return 0
    else:
        print("❌ SOME CHECKS FAILED - Fix issues before deployment")
        print()
        print("Failed checks:")
        for name, success, message in results:
            if not success:
                print(f"  • {message}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
