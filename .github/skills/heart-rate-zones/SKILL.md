# Heart Rate Zones Skill

This skill provides specialized knowledge for calculating and interpreting heart rate training zones. This is a shared skill used by both workout analysis and training plan generation.

## Core Competencies

### Heart Rate Zone Calculation

**Age-based maximum heart rate estimation:**

```
Traditional formula:
HRmax = 220 - age

Tanaka formula (recommended):
HRmax = 208 - (0.7 × age)
```

**Why Tanaka formula is preferred:**

The Tanaka formula (2001) is more accurate across a wider age range and for both trained and untrained individuals. Research shows:
- The traditional 220-age formula overestimates HRmax in younger adults and underestimates it in older adults
- Tanaka's formula is based on a meta-analysis of 351 studies with 18,712 subjects
- It provides more accurate predictions regardless of training status
- Standard error is lower compared to the traditional formula

For these reasons, we use Tanaka formula as the default for all runners.

**Standard 5-zone model:**
- **Zone 1 (Recovery)**: 50-60% of HRmax - Very light, conversational
- **Zone 2 (Easy/Aerobic)**: 60-70% of HRmax - Comfortable, can hold conversation
- **Zone 3 (Tempo)**: 70-80% of HRmax - Comfortably hard, some breathlessness
- **Zone 4 (Threshold)**: 80-90% of HRmax - Hard, sustainable for 20-40 minutes
- **Zone 5 (VO2max/Anaerobic)**: 90-100% of HRmax - Very hard, short bursts only

### Implementation

```python
def calculate_hr_zones(age):
    """
    Calculate heart rate training zones based on age.
    Uses Tanaka formula: HRmax = 208 - (0.7 × age)
    
    Args:
        age: Runner's age in years
    
    Returns:
        tuple: (zones dict, hr_max int)
    """
    # Use Tanaka formula for trained runners
    hr_max = 208 - (0.7 * age)
    
    zones = {
        'Z1': (int(hr_max * 0.50), int(hr_max * 0.60)),
        'Z2': (int(hr_max * 0.60), int(hr_max * 0.70)),
        'Z3': (int(hr_max * 0.70), int(hr_max * 0.80)),
        'Z4': (int(hr_max * 0.80), int(hr_max * 0.90)),
        'Z5': (int(hr_max * 0.90), int(hr_max * 1.00))
    }
    
    return zones, int(hr_max)

def determine_hr_zone(hr, zones):
    """
    Determine which zone a given heart rate falls into.
    
    Note: Boundary conditions are inclusive. If HR equals the upper bound
    of a zone (e.g., hr == zones['Z2'][1]), it will be classified in that zone.
    HR values above Z5's upper bound return 'Z5+'.
    """
    for zone_name, (lower, upper) in zones.items():
        if lower <= hr <= upper:
            return zone_name
    return 'Z5+' if hr > zones['Z5'][1] else 'Below Z1'
```

### Usage Guidelines

**When calculating zones:**
- Use Tanaka formula (208 - 0.7 × age) for trained runners
- Use observed max HR if available from recent workouts
- Zones are approximate - individual variation exists
- Consider recent HR data to validate calculated zones

**Zone interpretations:**
- Z1-Z2: Easy, aerobic base building (80% of training)
- Z3: Steady, comfortable threshold work
- Z4: Tempo, lactate threshold training
- Z5: VO2max intervals, race pace for shorter distances

## References

- Tanaka, Monahan, & Seals (2001). "Age-predicted maximal heart rate revisited"
- Seiler & Tønnessen (2009). "Intervals, Thresholds, and Long Slow Distance"
