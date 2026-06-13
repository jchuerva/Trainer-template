#!/usr/bin/env python3
"""
Calculate the next Monday date for weekly training plan generation.

This script calculates the next Monday from today (in UTC timezone)
and outputs the date, year, and month components needed for the workflow.

Output format (3 lines):
  Line 1: YYYY-MM-DD (next Monday date)
  Line 2: YYYY (year)
  Line 3: MM (month)
"""

from datetime import datetime, timedelta, timezone


def get_next_monday():
    """
    Get the date of next Monday in UTC.

    Returns:
        tuple: (next_monday_str, year, month) where:
            - next_monday_str is in YYYY-MM-DD format
            - year is the 4-digit year string
            - month is the 2-digit month string
    """
    # Use UTC timezone for consistency with GitHub Actions runners
    today = datetime.now(timezone.utc)
    
    # Calculate days until next Monday
    # weekday() returns 0 for Monday, 6 for Sunday
    days_until_monday = (7 - today.weekday()) % 7
    
    # If today is Monday, get next Monday (7 days ahead)
    if days_until_monday == 0:
        days_until_monday = 7
    
    next_monday = today + timedelta(days=days_until_monday)
    next_monday_str = next_monday.strftime('%Y-%m-%d')
    year = next_monday.strftime('%Y')
    month = next_monday.strftime('%m')
    
    return next_monday_str, year, month


def main():
    """Main entry point - outputs date, year, and month."""
    next_monday, year, month = get_next_monday()
    print(next_monday)
    print(year)
    print(month)


if __name__ == "__main__":
    main()
