# Training Load Skill

This skill provides specialized knowledge for assessing training load, recovery needs, and aerobic efficiency from workout data.

## Core Competencies

### Training Load Assessment

**Key factors for training load:**

1. **Duration**: Time spent in each HR zone
2. **Intensity**: Average HR and distribution across zones
3. **Volume**: Total distance covered
4. **Elevation**: Total ascent adds significant load
5. **Frequency**: Training density over recent days

**Training Stress Score (TSS) approximation:**
```
TSS = (duration_seconds × intensity_factor × 100) / 3600

Where intensity_factor is based on average HR relative to threshold HR:
- Easy (Z2): IF ≈ 0.65
- Steady (Z3): IF ≈ 0.75
- Tempo (Z4): IF ≈ 0.85
- Threshold: IF ≈ 0.95
- VO2max (Z5): IF ≈ 1.05
```

### Aerobic Efficiency Metrics

**Efficiency comparison metrics:**

1. **Pace at HR**: Track pace at a constant HR (e.g., 140 bpm) over time
2. **HR at pace**: Track HR at a constant pace (e.g., 7:00/km) over time
3. **Aerobic Decoupling**: Compare first half vs second half
   - Calculate: (HR/Pace ratio in 2nd half - HR/Pace ratio in 1st half) / HR/Pace ratio in 1st half
   - < 5%: Good coupling (efficient)
   - 5-10%: Moderate decoupling
   - > 10%: Poor coupling (need more aerobic base)

### Recovery Recommendations

**Signs of insufficient recovery:**
- Elevated resting HR (>5 bpm above baseline)
- Higher than normal HR for given pace/effort
- Inability to hit target paces despite RPE increase
- Excessive fatigue or heavy legs
- Declining performance over consecutive sessions

**Recovery guidelines:**
- Easy runs: Next day can be quality session
- Tempo/steady: 24-48h easy before next quality
- Long runs: 48-72h easy recovery
- Hard intervals: 48-72h before next quality session

**Recovery week recommendations:**
- Reduce volume by 20-30%
- Maintain intensity (keep quality sessions short)
- Schedule every 3-4 weeks

### Usage Guidelines

**When assessing training load:**
- Consider accumulated fatigue from previous days
- Look at weekly volume trends
- Account for non-running stress (work, sleep, life)
- Use multiple indicators (HR, pace, RPE, subjective feel)

**Recovery decision framework:**
1. Check recent volume trend (>10% increase = higher risk)
2. Assess HR response (elevated = needs recovery)
3. Evaluate performance (declining = needs recovery)
4. Consider external stressors

**Actionable feedback:**
- Specific: "HR was 8 bpm higher than last week at same pace"
- Contextual: "This is expected after 3 progressive weeks"
- Prescriptive: "Reduce next week volume by 20%"

## References

- Training and Racing with a Power Meter (Allen & Coggan)
- The Endurance Training Manual (Philip Maffetone)
- Heart Rate Training (Roy Benson & Declan Connolly)
