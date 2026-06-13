# Building app planning

1. Remove lots of files (including scripts and part of the README an how -to)
2. Create a new github agent to analyse the workous in .fit files

Example of prompt for creating the new agent:
"I want to add a new github agent. It will be in charge of analyse a workout in .fit format an create a analysis of the workout. Create the agent and also a template for the workout analysis.

  - Ritmos de carrera
  - Frecuencia cardiaca
  - Carga y recuperacion

  Copy example from chatGPT


1. Create a new github action which will be triggered when a new .fit file is added to the repository or manually. The action will check all the .fit files in the repository and will use the new github agent to create a analysis for each workout that doesn't have an analysis markdown file. The analysis will be added to a new markdown file with the same name as the .fit file but with .md extension. The .fit files lives in the /workouts/fit and the analysis are in /workouts/analysis.
The action should also update the workouts index file (/workouts/index.md) to include the new analysis files.
The action should also update the progress tracking dashboard (/docs/app-planning.md) to include the new analysis data.

1. Test the new action

2. Update the already existin generate weekly report action to:
  - check the analysis files for the last 2 weeks workouts
  - include the goal objective
  - creat workouts for the next week based on the analysis and the goal objective

3. Update the README and the HOW-TO with the new functionality

