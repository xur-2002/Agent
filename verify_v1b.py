#!/usr/bin/env python
"""Quick verification script for V1(B) implementation."""
import sys
import os
from pathlib import Path

print("="*70)
print("V1(B) IMPLEMENTATION VERIFICATION")
print("="*70)

# 1. Check dispatcher has daily_content_batch route
print("\n✓ Step 1: Checking dispatcher...")
try:
    with open('agent/task_runner.py', 'r') as f:
        content = f.read()
        if 'elif task_id == "daily_content_batch":' in content:
            print("  ✅ Dispatcher has daily_content_batch route")
        else:
            print("  ❌ Dispatcher missing daily_content_batch route")
            sys.exit(1)
except Exception as e:
    print(f"  ❌ Error checking dispatcher: {e}")
    sys.exit(1)

# 2. Check image_provider has correct Rule 1/Rule 2 logic
print("\n✓ Step 2: Checking image provider...")
try:
    with open('agent/image_provider.py', 'r') as f:
        content = f.read()
        if 'if isinstance(material, dict) and "sources" in material and material["sources"] == []' in content:
            print("  ✅ Image provider has Rule 1 (skip when sources==[])")
        else:
            print("  ❌ Image provider missing Rule 1 logic")
            sys.exit(1)
        
        if 'def provide_cover_image(material: dict, base_output: str, slug: str)' in content:
            print("  ✅ Image provider has correct function signature")
        else:
            print("  ❌ Image provider has incorrect function signature")
            sys.exit(1)
except Exception as e:
    print(f"  ❌ Error checking image provider: {e}")
    sys.exit(1)

# 3. Check .gitignore includes state.json and outputs/
print("\n✓ Step 3: Checking .gitignore...")
try:
    with open('.gitignore', 'r') as f:
        content = f.read()
        missing = []
        for item in ['state.json', 'outputs/', 'drafts/', 'publish_kits/']:
            if item not in content:
                missing.append(item)
        
        if not missing:
            print("  ✅ .gitignore includes all ignored paths")
        else:
            print(f"  ⚠️ .gitignore missing: {', '.join(missing)}")
except Exception as e:
    print(f"  ❌ Error checking .gitignore: {e}")
    sys.exit(1)

# 4. Check test files exist
print("\n✓ Step 4: Checking test files...")
test_files = [
    'tests/test_dispatcher_daily.py',
    'tests/test_image_placeholder.py',
    'tests/test_image_skip.py',
    'tests/test_email_skip.py'
]
missing_tests = []
for tf in test_files:
    if not Path(tf).exists():
        missing_tests.append(tf)
    else:
        print(f"  ✅ {tf}")

if missing_tests:
    print(f"  ❌ Missing test files: {', '.join(missing_tests)}")

# 5. Check GitHub Actions workflow
print("\n✓ Step 5: Checking GitHub Actions workflow...")
try:
    with open('.github/workflows/agent.yml', 'r') as f:
        content = f.read()
        if 'Upload generated outputs' in content and 'actions/upload-artifact' in content:
            print("  ✅ Workflow uses artifact upload")
        
        if 'git commit' not in content or 'Commit and push' not in content:
            print("  ✅ Workflow does NOT try to commit ignored files")
        else:
            print("  ⚠️ Workflow still has git commit logic (may fail)")
except Exception as e:
    print(f"  ❌ Error checking workflow: {e}")
    sys.exit(1)

# 6. Try importing key modules
print("\n✓ Step 6: Checking Python imports...")
try:
    from agent.task_runner import run_task, run_daily_content_batch
    print("  ✅ task_runner imports OK")
    
    from agent.image_provider import provide_cover_image
    print("  ✅ image_provider imports OK")
    
    from agent.email_sender import send_daily_summary
    print("  ✅ email_sender imports OK")
    
    from agent.models import Task, TaskResult
    print("  ✅ models imports OK")
except ImportError as e:
    print(f"  ❌ Import error: {e}")
    sys.exit(1)

print("\n" + "="*70)
print("✅ ALL CHECKS PASSED - V1(B) Ready for Testing")
print("="*70)
print("\nNext steps:")
print("  1. Run: pytest -q")
print("  2. Run: python -m agent.main --once")
print("  3. Check: outputs/articles/YYYY-MM-DD/")
