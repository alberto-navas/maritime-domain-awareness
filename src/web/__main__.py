"""Permite arrancar el panel web con `python -m src.web` (127.0.0.1:8000)."""

import uvicorn

if __name__ == "__main__":  # pragma: no cover — punto de entrada trivial, arranca un servidor real
    uvicorn.run("src.web.app:app", host="127.0.0.1", port=8000, reload=False)
