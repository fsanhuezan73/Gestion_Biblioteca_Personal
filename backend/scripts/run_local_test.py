"""Backend local contra el esquema de pruebas BIBLIOTECA_TEST.

Carga, en este orden, backend/.env.test, backend/.env.googlebooks y backend/.env.ai
(los que existan) como variables de entorno, que tienen prioridad sobre
backend/.env (producción). Nunca imprime valores de claves.

Uso (desde backend/, con el venv activo):  python scripts/run_local_test.py [--port 8001]
"""

import argparse
import os
import sys
from pathlib import Path

from dotenv import dotenv_values

BACKEND_DIR = Path(__file__).resolve().parent.parent
EXPECTED_SCHEMA = "BIBLIOTECA_TEST"
ENV_FILES = (".env.test", ".env.googlebooks", ".env.ai")


def load_env() -> list[str]:
    loaded = []
    for name in ENV_FILES:
        path = BACKEND_DIR / name
        if not path.exists():
            if name == ".env.test":
                sys.exit("Falta backend/.env.test: es obligatorio para no usar producción.")
            continue
        for key, value in dotenv_values(path).items():
            if value is not None:
                os.environ[key] = value
        loaded.append(name)
    return loaded


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=8001)
    args = parser.parse_args()

    loaded = load_env()
    user = os.environ.get("ORACLE_USER", "")
    if user.upper() != EXPECTED_SCHEMA:
        sys.exit(f"ORACLE_USER de .env.test no es {EXPECTED_SCHEMA}: se cancela para no tocar producción.")

    keys = {name: bool(os.environ.get(name)) for name in ("GEMINI_API_KEY", "GROQ_API_KEY", "GOOGLE_BOOKS_API_KEY")}
    print(f"Archivos cargados: {', '.join(loaded)}")
    print(f"Base de datos: {EXPECTED_SCHEMA}")
    print("Claves presentes (sin mostrar valores): "
          + ", ".join(f"{k}={'sí' if v else 'no'}" for k, v in keys.items()))
    if not (keys["GEMINI_API_KEY"] or keys["GROQ_API_KEY"]):
        print("Aviso: sin claves de IA, «Recomiéndame qué leer» responderá que no está configurado.")

    os.chdir(BACKEND_DIR)
    sys.path.insert(0, str(BACKEND_DIR))
    import uvicorn

    uvicorn.run("app.main:app", host="127.0.0.1", port=args.port, reload=False)


if __name__ == "__main__":
    main()
