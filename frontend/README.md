# PhotoMate Flow Frontend

This is the maintainable source project for the new `/flow/` frontend used by the FastAPI backend.

It was restored from the local `webnew3` React/Vite project because the repository previously only kept the built static files under `webs/flow/`.

## Commands

```powershell
cd frontend
npm install
npm run dev
npm run build
```

`npm run build` writes the production frontend to `../webs/flow`, which is what `app/main.py` serves at `/` and `/flow/`.

## Backend APIs Used

- `GET /api/map`
- `GET /api/waypoints`
- `GET /api/status`
- `POST /api/navigation/go`
- `POST /api/navigation/stop`
- `WS /ws/pose`

## Notes

This source matches the current new-flow frontend structure closely, but it should be treated as a restored source baseline rather than a guaranteed original authoring copy. Future frontend work, such as voice WebSocket logs, should happen here and then be rebuilt into `webs/flow/`.
