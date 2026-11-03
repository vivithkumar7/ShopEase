# Docker-hosted verification evidence

These files were captured from the running Docker Compose application at
`http://localhost:8003`:

- `swagger-ui.png`: actual full-page Swagger UI screenshot showing the routes.
- `docker-crud-smoke-test.txt`: host-side HTTP smoke test output for create,
  list, read, update, delete, validation, and not-found cases.
- `docker-compose-ps.txt`: Compose status and published port.
- `docker-service-logs.txt`: application access logs from those requests.
- `docker-memory-lifecycle.txt`: proof that a product is gone after container
  restart, as expected for in-memory storage.
- `live-api-output.png`: actual browser screenshot of the health response.
- `docker-verification.png`: screenshot summary rendered from the captured
  Compose status, smoke-test output, and server logs.

The application uses in-memory storage, so this evidence does not imply
database persistence. Product records are lost on process restart.
