# Workout Prescriptions Skill

This skill provides specialized knowledge for prescribing specific workout types with appropriate paces, durations, and structures.

## Core Competencies

### Workout Types

**Easy Runs (Zone 1-2):**
- Purpose: Build aerobic base, active recovery
- Pace: Conversational (can speak in full sentences)
- HR: 60-70% HRmax
- Duration: 30-60 minutes
- Frequency: 2-4x per week

**Long Runs (Zone 1-2, mostly):**
- Purpose: Build endurance, mental toughness
- Pace: Easy, maybe finish with tempo
- HR: 60-75% HRmax
- Duration: 90-180 minutes (or 20-30% of weekly volume)
- Frequency: 1x per week (typically Saturday/Sunday)

**Tempo/Steady State (Zone 3-4):**
- Purpose: Improve lactate threshold
- Pace: "Comfortably hard" (can speak short phrases)
- HR: 75-85% HRmax
- Duration: 20-40 minutes continuous, or intervals (e.g., 3×10 min)
- Frequency: 1x per week

**Intervals (Zone 4-5):**
- Purpose: Improve VO2max, race pace
- Pace: Hard effort (difficult to speak)
- HR: 85-95% HRmax
- Duration: Varies by type:
  - VO2max: 3-5 min reps, 2-3 min recovery
  - Race pace: 800m-2km reps, equal recovery
  - Hill repeats: 60-90 sec uphill, jog down recovery
- Frequency: 1x per week (alternating with tempo)

**Strides/Pickups:**
- Purpose: Neuromuscular development, running economy
- Pace: 5K-10K race pace, controlled fast
- Duration: 15-30 seconds each
- Recovery: 60-90 seconds easy
- Reps: 4-8 strides
- Frequency: 2-3x per week (after easy runs)

### Pace Calculation

**Note:** This skill works in conjunction with the **heart-rate-zones** skill for HR calculations.

```python
# Use calculate_hr_zones from heart-rate-zones skill for HR calculations
# See heart-rate-zones/SKILL.md for implementation details

def calculate_training_paces(age, recent_easy_pace, recent_hr_data=None):
    """
    Calculate training pace zones based on age and recent performance.
    References heart-rate-zones skill for HR calculations.
    
    Args:
        age: Runner's age in years
        recent_easy_pace: Recent easy run pace in min/km (string like "7:30")
        recent_hr_data: Optional dict with observed HR ranges
    
    Returns:
        Dictionary with pace and HR zones
    """
    # Validate pace input
    if recent_easy_pace is None or not str(recent_easy_pace).strip():
        raise ValueError("recent_easy_pace cannot be empty. Expected 'M:SS' or 'MM:SS'")
    
    # Calculate HR max using Tanaka formula from heart-rate-zones skill
    # (For documentation purposes, formula is shown here; in actual implementation,
    # this would reference the heart-rate-zones skill's calculate_hr_zones function)
    hr_max = 208 - (0.7 * age)
    
    # If recent max HR observed, use it
    if recent_hr_data and 'observed_max' in recent_hr_data:
        hr_max = recent_hr_data['observed_max']
    
    # Parse easy pace (handles both "M:SS" and "MM:SS" formats)
    pace_parts = str(recent_easy_pace).strip().split(':')
    if len(pace_parts) != 2:
        raise ValueError(f"Invalid pace format: {recent_easy_pace}. Expected 'M:SS' or 'MM:SS'")
    
    try:
        easy_mins = int(pace_parts[0])
        easy_secs = int(pace_parts[1])
    except ValueError:
        raise ValueError(f"Invalid pace format: {recent_easy_pace}. Minutes and seconds must be numeric.")
    
    if easy_secs >= 60:
        raise ValueError(f"Invalid pace format: {recent_easy_pace}. Seconds must be less than 60.")
    
    easy_pace_seconds = easy_mins * 60 + easy_secs
    
    # Estimate other paces based on easy pace
    # These are rough estimates; adjust based on fitness tests
    steady_pace = easy_pace_seconds * 0.92  # ~8% faster
    tempo_pace = easy_pace_seconds * 0.85   # ~15% faster
    threshold_pace = easy_pace_seconds * 0.80  # ~20% faster
    
    def format_pace(seconds):
        mins = int(seconds // 60)
        secs = int(seconds % 60)
        return f"{mins}:{secs:02d}"
    
    zones = {
        'Easy': {
            'pace_range': f"{format_pace(easy_pace_seconds)} - {format_pace(easy_pace_seconds * 1.10)}",
            'hr_range': f"{int(hr_max * 0.60)}-{int(hr_max * 0.70)} bpm",
            'hr_zone': 'Z1-Z2',
            'effort': 'Conversational, relaxed'
        },
        'Steady': {
            'pace_range': f"{format_pace(steady_pace)} - {format_pace(easy_pace_seconds * 0.95)}",
            'hr_range': f"{int(hr_max * 0.70)}-{int(hr_max * 0.80)} bpm",
            'hr_zone': 'Z3',
            'effort': 'Comfortably hard'
        },
        'Tempo': {
            'pace_range': f"{format_pace(tempo_pace)} - {format_pace(steady_pace)}",
            'hr_range': f"{int(hr_max * 0.80)}-{int(hr_max * 0.88)} bpm",
            'hr_zone': 'Z4',
            'effort': 'Hard but sustainable'
        },
        'Threshold': {
            'pace_range': f"{format_pace(threshold_pace)} - {format_pace(tempo_pace)}",
            'hr_range': f"{int(hr_max * 0.88)}-{int(hr_max * 0.95)} bpm",
            'hr_zone': 'Z4-Z5',
            'effort': 'Very hard'
        }
    }
    
    return zones
```

### Half Marathon Specific Workouts

**Goal pace runs:**
- 3-5 miles at goal half marathon pace
- Start at 8-10 weeks before race
- Gradually increase to 8-10 miles at pace

**Long runs with tempo finish:**
- 10-15 km easy + 3-5 km at tempo/goal pace
- Simulates racing on tired legs

**Threshold intervals:**
- 3-4 × 2 km at threshold pace (2-3 min recovery)
- Improves lactate clearance

**Progressive long runs:**
- Start easy, gradually increase pace
- Last 5-8 km at steady/tempo effort
- Teaches pacing discipline

### Usage Guidelines

**When prescribing workouts:**
- Match workout to training phase
- Consider recent training load
- Account for recovery status
- Be specific with paces and durations
- Provide alternative if conditions poor

**Workout modification rules:**
- Reduce reps/duration if fatigued (never increase pace)
- Skip quality if sick or injured
- Adjust for extreme weather
- Maintain easy day after quality

## References

- Daniels' Running Formula (Jack Daniels)
- Advanced Marathoning (Pfitzinger & Douglas)
- 80/20 Running (Matt Fitzgerald)
