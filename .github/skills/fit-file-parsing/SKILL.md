# FIT File Parsing Skill

This skill provides specialized knowledge for parsing and extracting data from FIT (Flexible and Interoperable Data Transfer) files commonly used by fitness devices.

## Core Competencies

### Python FIT Parsing

**Required library:**
```bash
pip install fitparse
```

**Basic parsing approach:**
```python
import fitparse
from datetime import datetime, timedelta

def parse_fit_file(fit_path):
    """
    Parse FIT file and extract key workout metrics.
    Returns a dictionary with workout summary.
    """
    fitfile = fitparse.FitFile(fit_path)
    
    # Initialize metrics
    metrics = {
        'start_time': None,
        'total_distance': 0,
        'total_time': 0,
        'average_hr': None,
        'max_hr': None,
        'average_cadence': None,
        'total_ascent': 0,
        'total_descent': 0,
        'laps': [],
        'records': []
    }
    
    # Parse session records for summary data
    for record in fitfile.get_messages('session'):
        for field in record:
            if field.name == 'start_time':
                metrics['start_time'] = field.value
            elif field.name == 'total_distance':
                metrics['total_distance'] = field.value / 1000  # Convert to km
            elif field.name == 'total_timer_time':
                metrics['total_time'] = field.value
            elif field.name == 'avg_heart_rate':
                metrics['average_hr'] = field.value
            elif field.name == 'max_heart_rate':
                metrics['max_hr'] = field.value
            elif field.name == 'avg_cadence':
                metrics['average_cadence'] = field.value
            elif field.name == 'total_ascent':
                metrics['total_ascent'] = field.value
            elif field.name == 'total_descent':
                metrics['total_descent'] = field.value
    
    # Parse lap data for segment analysis
    for record in fitfile.get_messages('lap'):
        lap = {}
        for field in record:
            if field.name in ['total_distance', 'total_timer_time', 'avg_heart_rate', 
                             'max_heart_rate', 'avg_cadence', 'avg_speed']:
                lap[field.name] = field.value
        if lap:
            metrics['laps'].append(lap)
    
    return metrics
```

### Key Metrics to Extract

**Session-level data:**
- `start_time`: Workout start timestamp
- `total_distance`: Total distance in meters (convert to km)
- `total_timer_time`: Total time in seconds
- `average_heart_rate`: Average heart rate in bpm
- `max_heart_rate`: Maximum heart rate in bpm
- `average_cadence`: Average cadence in steps per minute
- `total_ascent`: Total elevation gain in meters
- `total_descent`: Total elevation loss in meters

**Lap/Split data:**
- Per-lap distance, time, pace
- Per-lap HR metrics (average, max)
- Per-lap cadence

**Record-level data (detailed):**
- GPS coordinates
- Speed at each timestamp
- Heart rate at each timestamp
- Elevation at each timestamp

### Usage Guidelines

**When parsing FIT files:**
- Always handle missing data gracefully (use None or defaults)
- Convert units appropriately (meters to km, seconds to time format)
- Check for device-specific quirks (e.g., half-cadence reporting)
- Parse laps/splits for detailed segment analysis

**Common issues:**
- Some devices report cadence as half-cadence (multiply by 2)
- GPS data may have gaps or inaccuracies
- Temperature data may be missing
- Power data only available on certain devices

## References

- FIT SDK documentation: https://developer.garmin.com/fit/protocol/
- fitparse library: https://github.com/dtcooper/python-fitparse
