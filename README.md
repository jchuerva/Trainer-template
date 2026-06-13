# 🏃 Running Trainer Template

A GitHub-based personal running coach powered by GitHub Copilot / Claude AI.

Upload your workout FIT files and get automatic AI analysis, weekly training plans, progress charts, and accountability through a "run or pay" penalty system.

## Features

- 📊 **Automatic workout analysis** — upload a FIT file, get an AI-generated analysis
- 📅 **Weekly training plans** — AI generates personalized plans based on your goal and history
- 🔥 **Workout heatmap** — visual overview of your training consistency
- 📈 **Yearly health report** — charts for HRV, sleep, resting HR, and workout volume
- 💸 **Run or Pay** — optional penalty system to keep you accountable

## Quick Start

### 1. Use this template

Click **"Use this template"** → **"Create a new repository"**

### 2. Configure your profile

Edit `config/config.yaml` with your personal data:
- Date of birth, weight, height (used for heart rate zone estimates)
- Your preferred run days
- Your goal (create a file in `config/goals/` using `templates/goal-template.md`)

### 3. Set up GitHub secrets

Go to **Settings → Secrets and variables → Actions** and add:

| Secret | Description |
|--------|-------------|
| `COPILOT_TOKEN` | GitHub personal access token with Copilot access |
| `TELEGRAM_CHAT_ID` | Your Telegram chat ID (for notifications) |
| `TELEGRAM_BOT_TOKEN` | Your Telegram bot token (for notifications) |

> Telegram notifications are optional — workflows will still run without them.

### 4. Upload your first workout

Use the provided iOS Shortcut (see `docs/SETUP.md`) or manually upload a FIT file to `workouts/inbox/`.

The workflow will automatically:
1. Move the FIT file to the correct `workouts/YYYY/MM/fit/` folder
2. Generate an AI workout analysis
3. Update charts and indexes

## Repository Structure

```
├── config/
│   ├── config.yaml          ← your personal profile (edit this)
│   ├── config.schema.json   ← validation schema
│   ├── goals/               ← your training goals
│   └── data/
│       └── penalties.yaml   ← run-or-pay tracking
├── workouts/
│   ├── inbox/               ← drop FIT files here
│   ├── YYYY/MM/
│   │   ├── fit/             ← migrated FIT files
│   │   └── analysis/        ← AI-generated analysis (.md)
│   ├── charts/              ← heatmap and charts
│   └── index.md             ← workout index
├── health/
│   └── daily/               ← daily health JSON exports
├── plans/
│   └── YYYY/MM/             ← weekly training plans
├── scripts/                 ← Python scripts
├── templates/               ← markdown templates
├── tests/                   ← test suite
└── docs/                    ← documentation
```

## Documentation

- [Setup Guide](docs/SETUP.md) — detailed setup instructions including iOS Shortcut
- [Usage Guide](docs/USAGE.md) — how to use all features
- [Architecture](docs/ARCHITECTURE.md) — technical overview

## Requirements

- GitHub account with **GitHub Copilot** access
- Python 3.x (for local development/testing)
- Optional: iOS device with Shortcuts app (for easy FIT uploads)
- Optional: Telegram bot (for notifications)

## Workflows

| Workflow | Trigger | Description |
|----------|---------|-------------|
| `migrate-inbox-fit` | Push FIT to `workouts/inbox/` | Moves FIT to `YYYY/MM/fit/` and triggers analysis |
| `generate-analyses-from-fit` | After migrate / manual | AI workout analysis |
| `generate-weekly-plan` | Manual / scheduled | AI weekly training plan |
| `update-workout-charts` | Push to `workouts/` | Regenerates heatmap and charts |
| `update-yearly-report-monthly` | 1st of month / manual | Full-year health report |
| `run-or-pay` | Weekly (Monday) | Checks missed runs and applies penalties |
| `sync-config` | Push to `config/` | Syncs config to templates |
| `tests` | Push / PR | Runs test suite |
