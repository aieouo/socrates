```powershell
docker compose up -d
```
```powershell
docker compose up -d --build bot
```

<hr>

```powershell
docker logs -f bot
```

<hr>

```powershell
docker compose down
```

<hr>

```powershell
uv run alembic upgrade head
```
```powershell
uv run alembic revision --autogenerate
```
```powershell
uv run alembic downgrade -1
```
