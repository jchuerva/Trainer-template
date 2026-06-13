# Pace Analysis Skill

This skill provides specialized knowledge for analyzing running pace patterns, consistency, and efficiency.

## Core Competencies

### Pace Metrics

**Key pace metrics to analyze:**

1. **Average pace**: Total time / Total distance
2. **Pace variability**: Standard deviation of km splits
3. **Positive/Negative split**: Compare first half vs second half
4. **Pace drift**: Trend of pace deterioration over distance

### Implementation

```python
def analyze_pacing(splits):
    """
    Analyze pacing consistency and patterns.
    splits: list of split times in seconds
    """
    import statistics
    
    if not splits:
        return {}
    
    # Need at least 2 splits for variability calculation
    if len(splits) < 2:
        return {
            'average_pace': splits[0],
            'variability': 0,
            'fastest_split': splits[0],
            'slowest_split': splits[0],
        }
    
    analysis = {
        'average_pace': statistics.mean(splits),
        'variability': statistics.stdev(splits),
        'fastest_split': min(splits),
        'slowest_split': max(splits),
    }
    
    # Calculate split pattern (negative/positive/even)
    first_half = statistics.mean(splits[:len(splits)//2])
    second_half = statistics.mean(splits[len(splits)//2:])
    diff = second_half - first_half
    
    # Use percentage-based thresholds for better accuracy
    # Percentage-based thresholds automatically scale with pace (faster paces
    # naturally have smaller absolute differences for equivalent effort changes)
    # Positive split = second half >2% slower
    # Negative split = second half >2% faster
    if first_half > 0:  # Avoid division by zero
        threshold_percent = 0.02
        threshold = first_half * threshold_percent
        
        if diff < -threshold:
            analysis['split_pattern'] = 'negative split (strong finish)'
        elif diff > threshold:
            analysis['split_pattern'] = 'positive split (fade)'
        else:
            analysis['split_pattern'] = 'even split'
    else:
        # Fallback for edge case
        analysis['split_pattern'] = 'even split'
    
    return analysis
```

### Cadence Analysis

**Optimal cadence ranges:**
- General guideline: 160-180 steps per minute (spm)
- Slower runners (>6:00/km): 160-170 spm acceptable
- Faster runners (<5:00/km): 170-180 spm typical

**Cadence considerations:**
- Low cadence (<160) with slow pace: May indicate overstriding
- High cadence (>185): May be inefficient unless very fast pace
- Cadence drops >10 spm late in run: Sign of fatigue
- Device reporting: Some report half-cadence (multiply by 2)

### Pacing Discipline

**Evaluating pacing consistency:**

1. **Even splits** (< 2% variation): Excellent pacing discipline
2. **Moderate variation** (2-5%): Acceptable, may be terrain-related
3. **High variation** (>5%): Poor pacing control or challenging conditions

**Factors affecting pace:**
- Terrain (hills, surface type)
- Weather conditions (wind, temperature, humidity)
- Fatigue state
- Intentional workout structure (intervals, progressive runs)

### Usage Guidelines

**When analyzing pace:**
- Always consider context (terrain, weather, workout intent)
- Use percentage-based comparisons rather than absolute seconds
- Look for patterns over multiple runs, not single workouts
- Distinguish between controlled variation (workout structure) and poor pacing

**Pacing recommendations:**
- Easy runs: Accept pace variation, focus on HR/effort
- Tempo runs: Aim for consistent pace (±5-10 sec/km)
- Intervals: Consistent pace per rep, not necessarily across workout
- Long runs: Slight positive split acceptable, avoid big surges

## References

- Daniels' Running Formula (Jack Daniels)
- "Pacing Strategy and Athletic Performance" (Foster et al., 1994)
