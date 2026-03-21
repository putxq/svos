# SVOS — Sovereign Ventures OS

**SVOS** is a sovereign digital business operating system that turns a business idea into an autonomous, governed, multi-agent company.

## What SVOS Is
SVOS is not a chatbot wrapper. It is a full operating layer for digital companies:

- Constitutional governance and policy validation
- Executive multi-agent structure (Board + C-Suite + Departments)
- Production lines (content/sales/support)
- Digital factories (content/data/strategy/product)
- Autonomous loop with scheduler and execution tools
- Innovation APIs (CRM + Digital Factory + Revenue + Company DNA)

## Current Status (v3.2 LIVE)
- Live API on Railway
- Core governance + agents active
- Executive dashboard active
- Real execution endpoints active
- CRM + Factory APIs active
- Revenue Engine + Company DNA APIs added

## Key API Areas

### Core & Governance
- `GET /health`
- `POST /constitution/validate`
- `POST /board/decide`

### Executive & Operations
- `POST /csuite/run_all`
- `POST /assembly/content`
- `POST /assembly/sales`
- `POST /assembly/support`

### Factory & Execution
- `POST /factory/content`
- `POST /factory/strategy`
- `POST /factory/analysis`
- `POST /factory/product`
- `POST /execute/full-package`

### Scheduler & Autonomous
- `POST /scheduler/start`
- `POST /scheduler/stop`
- `POST /scheduler/run-once`
- `GET /scheduler/status`

### CRM
- `POST /crm/leads`
- `GET /crm/pipeline`
- `GET /crm/leads/{id}`
- `POST /crm/leads/{id}/score`
- `POST /crm/leads/{id}/suggest`
- `POST /crm/leads/{id}/outreach`
- `POST /crm/leads/{id}/stage`

### Revenue Engine
- `POST /revenue/discover`
- `POST /revenue/evaluate`
- `POST /revenue/pricing`
- `POST /revenue/forecast`
- `GET /revenue/summary`

### Company DNA
- `POST /dna/initialize`
- `GET /dna/profile`
- `POST /dna/record-decision`
- `POST /dna/record-lesson`
- `POST /dna/evolve`
- `POST /dna/brand-voice`

## Deployment
Production URL:
- `https://web-production-ddd97.up.railway.app`

## Roadmap Priorities
1. Stripe + first paying customer
2. Automated onboarding (48h setup path)
3. Intelligence layer upgrades (market monitoring)
4. MCP integrations
5. White-label + API ecosystem

## Vision
Enable SMEs to run full digital operations with autonomous agents at a cost lower than one employee — with real governance, visibility, and execution.

---
Built by **Omar Alharbi** — 2026
