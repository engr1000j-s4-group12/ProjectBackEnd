# Project Agent Notes

## Project context

- This repository is the cloud-deployable backend and no-development-board
  simulator for a VLM-based Longbin Building navigation terminal.
- The intended runtime chain is ESP32-S3/Xiaozhi -> museum MCP tools -> FastAPI
  backend -> VLM localization, deterministic route planning, and curated exhibit
  data.
- The active delivery branch is `CYH` in `/home/Hylia/workspace/ProjectBackEnd`.
  `/home/Hylia/workspace/BackEnd` is the preserved source of the pre-cloud
  integrated implementation, not the delivery worktree.
- The user will provide additional source material for MCP refinement, testing,
  and database improvement. Preserve provenance and do not turn unverified
  material into asserted exhibit facts.
- Keep route selection deterministic; VLM output supplies evidence rather than
  deciding routes.
- The local admin console is `/admin`. It always displays the four floor maps
  from `server/app/static/admin/maps/` and stores drawn normalized polygons in
  `data/guide.sqlite3` through `server/app/knowledge.py`.
- Console uploads are processed by VLM once at ingest and persisted. Live
  device localization may call VLM for a new camera frame; ordinary knowledge
  queries must use persisted data.
- Xiaozhi devices use `/api/device/v1`, send `Device-Id`, and receive compact
  `announcement` responses. Device sessions persist in SQLite. Cloud deployment
  uses Docker Compose, a persistent runtime volume, optional Caddy HTTPS,
  Basic Auth for admin, and Bearer tokens for device/MCP APIs.
- The read-only Guide integration is available through JSON-RPC at `/mcp` and
  the parallel `/api/v1/knowledge`, `/api/v1/events`, and `/api/v1/guide`
  endpoints. Management writes remain under `/api/admin`.
- All four floor maps and their currently legible room/open/facility nodes are
  stored in `data/guide.sqlite3`. Runtime navigation uses
  `SqliteGuideRepository`; `data/building_map.json` is now a seed/import source
  for the existing 4F graph.
- Console knowledge records are synchronized into `map_nodes`, including VLM
  visual tags. The user's green route markings in
  `output/longbin-1f-4f-node-route.pdf` are stored reproducibly through
  `data/user_marked_routes_2026-07-16.json`; they provide partial 1F–3F route
  graphs with `user_marked` calibration status. Most room-door and inter-floor
  links still need confirmation. The 4F graph also remains estimated until
  on-site measurements and landmark photos are supplied.
- Guest-elevator corrections live in `data/elevator_navigation_2026-07-16.json`.
  The northwest 1F elevator is restricted/no-entry and must never be routed to
  guests; all guest-elevator exits face north. Keep detailed route `steps`
  internal and speak only the concise route `announcement`.

## VLM configuration

- VLM credentials and configuration are provided through `VLM_API_KEY`,
  `VLM_BASE_URL`, and `VLM_MODEL` in the user's `.zshrc`.
- When VLM access is needed, read these variables from a login-style zsh
  environment. Never print, persist, commit, or otherwise expose their values.
- Treat `VLM_API_KEY` as a secret. It may be used for authorized VLM requests,
  but must be redacted from command output, logs, errors, and final responses.
