# API Contract

All API responses use:

```json
{
  "success": true,
  "data": {},
  "message": "",
  "timestamp": ""
}
```

Public routes include `/api/health`, `/api/scenic`, `/api/scenic/{id}`, `/api/scenic/search`, `/api/provinces`, `/api/weather`, `/api/comments`, `/api/live`, and `/api/uploads`.

User routes include profile, favorites, trips, routes, and trip export endpoints under `/api/user`.

Admin routes cover dashboard, scenic management, image review, comment review, users, API access configuration, roles, security logs, and system settings under `/api/admin`.
