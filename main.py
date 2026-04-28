"""
Ponto de entrada da aplicação.
Execute com: uv run python main.py
Ou com reload: uv run uvicorn app.main:app --reload
"""

import uvicorn


def main():
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=False,
    )


if __name__ == "__main__":
    main()
