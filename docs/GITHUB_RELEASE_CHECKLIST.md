# LineLens GitHub Release Checklist

Before marking the repository public and submitting for the challenge, verify all items below.

### Repository
- [ ] Root contains only: README.md, LICENSE, .gitignore, ATTRIBUTIONS.md, frontend/, backend/, docs/, assets/, demo/
- [ ] No development scratch files at root
- [ ] No `.pytest_cache` or build caches committed

### README
- [ ] README renders correctly on GitHub
- [ ] No broken image links
- [ ] No absolute local paths
- [ ] All internal doc links work
- [ ] Hero screenshot added
- [ ] Demo video linked

### Source
- [ ] Frontend TypeScript compiles (`npm run build`)
- [ ] Backend Python compiles (`python -m compileall -q app`)
- [ ] All imports resolve
- [ ] No hardcoded absolute paths in source

### Setup
- [ ] Clean clone: `git clone`, `cd`, install, start — works
- [ ] Backend starts: `cd backend && pip install -r requirements.txt && uvicorn app.main:app --port 8102`
- [ ] Frontend starts: `cd frontend && npm install && npm run dev`
- [ ] Quality model artifact loads from relative path
- [ ] API proxy connects frontend to backend

### Security
- [ ] No API keys or tokens
- [ ] No `.env` files committed
- [ ] No personal file paths
- [ ] No development chat/prompt content
- [ ] No NexusTwin/NebulaCloud references in public-facing files

### Attribution
- [ ] LICENSE file present and correct
- [ ] ATTRIBUTIONS.md lists NexusTwin visual reference and all libraries

### Screenshots (Final Media)
- [ ] `dashboard-overview.png` — captured at 1440x900
- [ ] `sensor-gap.png`
- [ ] `bottleneck-forecast.png`
- [ ] `quality-twin.png`
- [ ] `common-pattern.png`
- [ ] `incident.png`

### Video
- [ ] `demo/LineLens_Prototype_Demo.mp4` recorded (90-120 seconds)
- [ ] Video linked in README

### Submission Documents (Portal Upload — not in repo)
- [ ] `LineLens_README.pdf` generated and uploaded to submission portal
- [ ] `LineLens_Detailed_Business_Proposal.pdf` generated and uploaded
- [ ] `LineLens_Detailed_Business_Proposal.pptx` generated and uploaded

### Testing
- [ ] Backend test suite passes: `python -m pytest backend/tests/ -v` (from repo root)
- [ ] Frontend production build passes: `cd frontend && npm run build`

### Publication
- [ ] Repository set to public
- [ ] GitHub description set (~120 chars)
- [ ] GitHub topics added
- [ ] Final URL copied to submission form

