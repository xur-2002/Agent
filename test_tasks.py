import json
from agent.models import Task

with open('tasks.json') as f:
    tasks_data = json.load(f)

print(f'✓ Loaded {len(tasks_data)} tasks from JSON')
for task_data in tasks_data:
    task = Task.from_dict(task_data)
    print(f'  ✓ Task "{task.id}" (enabled={task.enabled}, frequency={task.frequency})')

print("\n✓ All tasks instantiated successfully")
