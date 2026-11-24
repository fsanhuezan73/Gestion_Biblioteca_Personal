"""Backend local contra un esquema Oracle elegido explícitamente.

- Por defecto, el esquema de pruebas BIBLIOTECA_TEST (backend/.env.test).
- Con --schema personal, el esquema de PRODUCCIÓN BIBLIOTECA_PERSONAL
  (backend/.env); exige además --confirm-production.

Carga como variables de entorno (que tienen prioridad sobre backend/.env) el
archivo del esquema y, si existen, backend/.env.googlebooks y backend/.env.ai.
Se cancela si ORACLE_USER no coincide con el esquema pedido. Nunca imprime
valores de claves.

Uso (desde backend/, con el venv activo):
    python scripts/run_local_test.py [--port 8001]
    python scripts/run_local_test.py --schema personal --confirm-production --port 8002
"""

import argparse
import os
import sys
from pathlib import Path

from dotenv import dotenv_values

BACKEND_DIR = Path(__file__).resolve().parent.parent
SCHEMAS = {
    "test": ("BIBLIOTECA_TEST", ".env.test"),
    "personal": ("BIBLIOTECA_PERSONAL", ".env"),
}
OPTIONAL_ENV_FILES = (".env.googlebooks", ".env.ai")


def load_env(schema_file: str) -> list[str]:
    loaded = []
    for name in (schema_file, *OPTIONAL_ENV_FILES):
        path = BACKEND_DIR / name
        if not path.exists():
            if name == schema_file:
                sys.exit(f"Falta backend/{name}: es obligatorio para elegir el esquema.")
            continue
        for key, value in dotenv_values(path).items():
            if value is not None:
                os.environ[key] = value
        loaded.append(name)
    return loaded


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=8001)
    parser.add_argument("--schema", choices=sorted(SCHEMAS), default="test")
    parser.add_argument("--confirm-production", action="store_true")
    args = parser.parse_args()

    expected, schema_file = SCHEMAS[args.schema]
    if args.schema == "personal" and not args.confirm_production:
        sys.exit("BIBLIOTECA_PERSONAL es producción: agrega --confirm-production (o usa ./start-personal.sh).")

    loaded = load_env(schema_file)
    user = os.environ.get("ORACLE_USER", "")
    if user.upper() != expected:
        sys.exit(f"ORACLE_USER de backend/{schema_file} no es {expected}: se cancela.")

    keys = {name: bool(os.environ.get(name)) for name in ("GEMINI_API_KEY", "GROQ_API_KEY", "GOOGLE_BOOKS_API_KEY")}
    print(f"Archivos cargados: {', '.join(loaded)}")
    if args.schema == "personal":
        print("*** Base de datos: BIBLIOTECA_PERSONAL (PRODUCCIÓN): los cambios afectan tus datos reales ***")
    else:
        print(f"Base de datos: {expected}")
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
