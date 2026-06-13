# Progressive Overload Skill

This skill provides specialized knowledge for safely increasing training volume and intensity over time.

## Core Competencies

### The 10% Rule

**Basic principle:**
```
New Weekly Volume ≤ Previous Week Volume × 1.10
```

**Implementation:**
```python
def calculate_safe_volume_increase(current_volume_km, weeks_at_current=1):
    """
    Calculate safe volume increase based on current training.
    
    Args:
        current_volume_km: Current weekly volume in km
        weeks_at_current: Number of weeks at this volume
    
    Returns:
        Recommended volume range for next week
    """
    # Standard 10% increase
    max_increase = current_volume_km * 1.10
    
    # Conservative increase if new to this volume
    if weeks_at_current < 2:
        conservative_increase = current_volume_km * 1.05
    else:
        conservative_increase = current_volume_km * 1.08
    
    # Ceiling: Never increase by more than 10%
    safe_increase = min(conservative_increase, max_increase)
    
    return {
        'min_volume': current_volume_km,  # Maintain
        'recommended': round(safe_increase, 1),
        'max_volume': round(max_increase, 1)
    }
```

### Progressive Overload Factors

**Priority order:**
1. First: Build consistency (3-4 runs/week)
2. Second: Increase volume gradually
3. Third: Add intensity (quality sessions)

**Never increase simultaneously:**
- ❌ Don't increase both volume AND intensity in the same week
- ✅ Increase volume while maintaining intensity
- ✅ OR maintain volume while increasing intensity

### Week-to-Week Patterns

**3:1 Pattern (recommended):**
```
Week 1: 20 km (build)
Week 2: 22 km (build)
Week 3: 24 km (build)
Week 4: 18 km (recovery/deload)
Week 5: 26 km (build from week 3)
```

**2:1 Pattern (aggressive):**
```
Week 1: 20 km (build)
Week 2: 22 km (build)
Week 3: 17 km (recovery)
Week 4: 24 km (build)
```

### Recovery Weeks

**When to deload:**
- Every 3-4 weeks (3:1 or 4:1 pattern)
- After volume increased >15% over 2-3 weeks
- When showing signs of fatigue

**How to deload:**
- Reduce volume by 20-30%
- Maintain intensity (keep quality short)
- Keep frequency (same number of runs)

### Usage Guidelines

**When planning volume increases:**
- Check current 4-week trend
- Never increase >10% per week
- Build in regular deload weeks
- Monitor for overtraining signs

**Red flags to reduce volume:**
- Elevated resting HR
- Persistent muscle soreness
- Performance decline
- Mood/motivation changes
- Sleep disturbances

## References

- "The 10% Rule: Fact or Fiction?" (Buist et al., 2008)
- Training for the New Alpinism (House & Johnston)
