# KineticOS
Autonomous computer-vision platform that turns one smartphone camera into a biomechanics lab:
auto set clipping, "True-Time" isometric timer, bilateral symmetry analysis, post-set telemetry report,
and longitudinal fatigue/asymmetry trends.

## Team
| Role | Owner | Scope |
|---|---|---|
| A - Perception & Real-Time Engine | Teammate 1 | camera -> keypoints/bar tracks -> set/rep events -> clips |
| B - Biomechanics, Analytics & Product | Teammate 2 | metrics -> reports -> database -> app/UI |

## Read in this order
1. docs/00_PROJECT_ANALYSIS.md  - what we are building, risks, what to cut
2. docs/01_ROLES_AND_WORKLOAD.md - who does what (balanced)
3. docs/02_TECH_STACK.md - stack and why
4. docs/03_ARCHITECTURE_AND_CONTRACTS.md - the interface between A and B
5. docs/04_ROADMAP.md - 10-week plan

## Quick start
```
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
pytest
uvicorn api.main:app --reload
```
## Git rules
main = always runnable. Branches: feat/a-*, feat/b-*. PRs reviewed by the other teammate.
Only change `contracts/` after both agree.
