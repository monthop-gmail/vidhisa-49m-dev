## Summary

Apply Python code style standards to the API codebase using ruff, including docstrings, type hints, and consistent formatting. All 65 tests continue to pass.

## Type

- [ ] Bug fix
- [ ] Feature ใหม่
- [x] Refactor / ปรับปรุง
- [ ] Docs / เอกสาร
- [ ] Test
- [ ] Infra / CI

## Service ที่แก้

- [x] API (`services/api/`)
- [ ] Dashboard (`services/dashboard/`)
- [ ] DB (`services/db/`)
- [ ] Infra / CI

## Changes

### Configuration
- Add `services/api/pyproject.toml` with ruff configuration (line-length: 120, target: Python 3.12)
- Add ruff and mypy to `requirements-test.txt`

### Code Quality Improvements
- **All modules**: Add Google-style docstrings for classes and public functions
- **All functions**: Add type hints for parameters and return types
- **Imports**: Reorganize to standard library → third-party → local
- **Formatting**: Apply ruff format to all Python files

### Files Refactored (22 files, +817/-320 lines)

| File | Changes |
|------|---------|
| `app/main.py` | Docstrings, type hints |
| `app/config.py` | Docstrings, type hints |
| `app/database.py` | Docstrings, type hints |
| `app/models.py` | Docstrings, Column() wrappers |
| `app/schemas.py` | Modern Pydantic v2 syntax (`str \| None`) |
| `app/anti_fraud.py` | Docstrings, restructured for readability |
| `app/events.py` | Docstrings, modern type hints |
| `app/routers/records.py` | Docstrings |
| `app/routers/stats.py` | Docstrings |
| `app/routers/branches.py` | Docstrings |
| `app/routers/organizations.py` | Docstrings |
| `app/routers/branch.py` | Docstrings |
| `app/routers/feed.py` | Docstrings |
| `app/routers/leaderboard.py` | Docstrings |
| `app/routers/markers.py` | Docstrings |
| `app/routers/projection.py` | Docstrings |
| `app/routers/sse.py` | Docstrings |

### Documentation
- Update `CLAUDE.md` with Code Style (Python) section

## Testing

```bash
docker compose exec vidhisa-api python3 -m pytest tests/ -v
# 65 passed
```

## Checklist

- [x] ทดสอบในเครื่องแล้ว (`docker compose up -d`)
- [x] Test ผ่าน (`python3 -m pytest tests/ -v`)
- [x] อัพเดท spec/docs (ถ้าเกี่ยวข้อง)

## Screenshots (ถ้ามี)

## Issue ที่เกี่ยวข้อง (จำเป็น)

<!-- ⚠️ PR จะไม่ผ่าน CI ถ้าไม่ link กับ Issue — ใส่เลข issue ต่อท้าย # -->

Closes #
