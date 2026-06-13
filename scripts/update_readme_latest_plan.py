#!/usr/bin/env python3
"""
Update README with the latest training plan link.
This script is called by the generate-weekly-plan workflow.
"""

import sys
import re
from datetime import datetime
from pathlib import Path

def get_repo_root():
    """Get repository root directory."""
    return Path(__file__).parent.parent

def find_latest_plan():
    """Find the most recent weekly plan file."""
    repo_root = get_repo_root()
    plans_dir = repo_root / "plans"
    
    # Find all weekly plan files
    plan_files = list(plans_dir.rglob("week-*.md"))
    
    if not plan_files:
        return None, None
    
    # Sort by filename (YYYY-MM-DD format) and get latest
    plan_files.sort(key=lambda p: p.stem)
    latest = plan_files[-1]
    
    # Extract date from filename (week-YYYY-MM-DD.md)
    match = re.search(r'week-(\d{4}-\d{2}-\d{2})', latest.name)
    if match:
        date_str = match.group(1)
        rel_path = str(latest.relative_to(repo_root))
        return rel_path, date_str
    
    return None, None

def update_readme(plan_path, plan_date):
    """Update README with latest plan link in the Quick Links table."""
    repo_root = get_repo_root()
    readme_path = repo_root / "README.md"
    
    if not readme_path.exists():
        print("Error: README.md not found", file=sys.stderr)
        return False
    
    with open(readme_path, 'r') as f:
        content = f.read()
    
    # Pattern to match the Latest Training Plan table row
    # Matches: | **[Latest Training Plan](any/path.md)** | This week's plan |
    table_pattern = r'\| \*\*\[Latest Training Plan\]\([^)]+\)\*\* \| This week\'s plan \|'
    
    # New table row with updated link
    new_table_row = f"| **[Latest Training Plan]({plan_path})** | This week's plan |"
    
    # Update the table row
    if re.search(table_pattern, content):
        content = re.sub(table_pattern, new_table_row, content)
    else:
        print("Warning: Latest Training Plan table row not found in README", file=sys.stderr)
        return False
    
    with open(readme_path, 'w') as f:
        f.write(content)
    
    print(f"✅ README updated with latest plan: {plan_path}")
    return True

def main():
    """Main entry point."""
    plan_path, plan_date = find_latest_plan()
    
    if not plan_path:
        print("Error: No training plans found", file=sys.stderr)
        sys.exit(1)
    
    if not update_readme(plan_path, plan_date):
        sys.exit(1)

if __name__ == "__main__":
    main()
