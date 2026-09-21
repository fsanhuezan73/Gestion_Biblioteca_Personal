# Deploy en Render + Vercel

## 1) Preparación previa

Asegúrate de tener:
- repo en GitHub
- cuenta en Render
- cuenta en Vercel
- un backend Oracle disponible con las credenciales correctas

## 2) Backend en Render

### Opción A: desplegar desde el repo raíz

Crea un Web Service en Render con:
- Nombre: `biblioteca-personal-api`
- Root directory: `backend`
- Build command: `pip install -r requirements.txt`
- Start command: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`

Añade estas variables de entorno en Render:

```env
APP_ENV=production
ALLOWED_ORIGINS=https://biblioteca-personal.site
ORACLE_USER=tu_usuario
ORACLE_PASSWORD=tu_password
ORACLE_DSN=tu_dsn
ORACLE_WALLET_DIR=
ORACLE_WALLET_PASSWORD=
ORACLE_WALLET_BASE64=zip_del_wallet_en_base64
JWT_SECRET_KEY=tu_secret_largo_y_seguro
JWT_ALGORITHM=HS256
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=30
```

### Importante
- `ALLOWED_ORIGINS` debe incluir exactamente el dominio público del frontend en Vercel.
- El dominio canónico de producción es `https://biblioteca-personal.site`.
- `https://www.biblioteca-personal.site` redirige al dominio canónico.
- Si tu app se sirve desde `https://<proyecto>.vercel.app`, usa ese valor.
- Render no puede leer una ruta de tu Mac. Deja `ORACLE_WALLET_DIR` vacío y define
	`ORACLE_WALLET_BASE64` con el ZIP del wallet codificado en Base64.

En macOS, genera el valor sin imprimirlo en pantalla:

```bash
cd Wallet
zip -r -q ../oracle-wallet.zip wallet
base64 < ../oracle-wallet.zip | tr -d '\n' | pbcopy
rm ../oracle-wallet.zip
```

Después pega el contenido del portapapeles en el valor secreto `ORACLE_WALLET_BASE64` de Render.

## 3) Frontend en Vercel

Importa el repo en Vercel y configura:
- Framework: Vite
- Root directory: `frontend`
- Build command: `npm run build`
- Output directory: `dist`

Añade esta variable de entorno:

```env
VITE_API_URL=https://tu-backend.onrender.com/api/v1
```

## 4) Comprobar que todo funciona

1. Accede al frontend desplegado
2. Intenta registrarte o iniciar sesión
3. Prueba crear un libro
4. Verifica que las peticiones van al backend en Render
5. Comprueba que `/health` del backend responde bien

## 5) CORS y local

Tu entorno local sigue funcionando porque:
- `ALLOWED_ORIGINS` solo se usa en producción
- el frontend local usa `http://localhost:8000/api/v1` por defecto
- el backend local sigue aceptando localhost por defecto

## 6) URL pública esperada

- Frontend: `https://biblioteca-personal.site`
- Backend: `https://biblioteca-personal-api.onrender.com/docs`

## 7) Si falla algo

Revisa:
- que el backend esté escuchando en `$PORT`
- que `ALLOWED_ORIGINS` coincida exactamente con el sitio de Vercel
- que `VITE_API_URL` apunte al backend real
- que Oracle acepte conexiones desde Render
- que `JWT_SECRET_KEY` esté definido
