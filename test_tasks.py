import json
from agent.models import Task

# Explicitly open tasks.json as UTF-8 (use utf-8-sig to accept BOM) to avoid
# Windows default encoding (GBK) causing UnicodeDecodeError during test collection.
with open('tasks.json', encoding='utf-8-sig') as f:
    tasks_data = json.load(f)

print(f'✓ Loaded {len(tasks_data)} tasks from JSON')
for task_data in tasks_data:
    task = Task.from_dict(task_data)
    print(f'  ✓ Task "{task.id}" (enabled={task.enabled}, frequency={task.frequency})')

print("\n✓ All tasks instantiated successfully")
