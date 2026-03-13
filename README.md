# 🏃 Garmin Health Dashboard

Dashboard personal de salud auto-actualizado desde Garmin Connect.  
Se regenera cada noche automáticamente vía GitHub Actions.

---

## 🚀 Setup en 5 pasos (15 minutos)

### Paso 1 — Sube este proyecto a GitHub

```bash
# En tu terminal, dentro de la carpeta garmin-health:
git init
git add .
git commit -m "Initial commit"

# Ve a github.com → New repository → nombre: garmin-health → Create
# Luego copia la URL y ejecuta:
git remote add origin https://github.com/TU_USUARIO/garmin-health.git
git branch -M main
git push -u origin main
```

---

### Paso 2 — Guarda tus credenciales de Garmin como Secrets

1. Ve a tu repo en GitHub → **Settings** → **Secrets and variables** → **Actions**
2. Clic en **New repository secret** y crea estos dos:

| Nombre | Valor |
|--------|-------|
| `GARMIN_EMAIL` | tu email de Garmin Connect |
| `GARMIN_PASSWORD` | tu contraseña de Garmin Connect |

> ⚠️ Los secrets nunca son visibles, ni para ti después de guardarlos. GitHub los encripta.

---

### Paso 3 — Activa GitHub Pages

1. Ve a tu repo → **Settings** → **Pages**
2. En **Source** selecciona: `Deploy from a branch`
3. Branch: `main` / Folder: `/docs`
4. Clic **Save**

En ~2 minutos tu URL estará lista:  
**`https://TU_USUARIO.github.io/garmin-health`**

---

### Paso 4 — Corre el primer update manual

1. Ve a tu repo → pestaña **Actions**
2. Clic en **Update Health Dashboard**
3. Clic en **Run workflow** → **Run workflow**
4. Espera ~2 minutos a que termine (verás un ✅ verde)

¡Listo! Tu dashboard ya tiene datos reales.

---

### Paso 5 — Úsalo

- **Desde el celular:** Abre `https://TU_USUARIO.github.io/garmin-health` y añádelo a la pantalla de inicio (Safari/Chrome → Compartir → "Añadir a pantalla de inicio")
- **Desde PC:** Misma URL, siempre actualizada
- **Actualización automática:** Cada noche a las 2:00 AM hora Colombia

---

## 🖥️ Correr localmente (opcional)

```bash
# Instalar dependencias
pip install garminconnect

# Configurar credenciales (solo la primera vez)
# Windows:
set GARMIN_EMAIL=tu@email.com
set GARMIN_PASSWORD=tu_contraseña

# Mac/Linux:
export GARMIN_EMAIL=tu@email.com
export GARMIN_PASSWORD=tu_contraseña

# Descargar datos y generar dashboard
python src/fetch_garmin.py
python src/build_dashboard.py

# Abrir el resultado
# Abre docs/index.html en tu navegador
```

---

## 📁 Estructura del proyecto

```
garmin-health/
├── .github/
│   └── workflows/
│       └── update_dashboard.yml   ← automatización nightly
├── src/
│   ├── fetch_garmin.py            ← descarga datos de Garmin Connect
│   └── build_dashboard.py         ← genera el HTML
├── data/
│   └── garmin_data.json           ← datos cacheados (generado automáticamente)
├── docs/
│   └── index.html                 ← dashboard final (GitHub Pages lo sirve aquí)
├── requirements.txt
└── README.md
```

---

## ❓ Problemas comunes

**"Authentication failed"**  
→ Verifica email/contraseña en los Secrets. Si tienes 2FA en Garmin, desactívalo temporalmente o genera una app password.

**El workflow falla con error de red**  
→ Garmin a veces bloquea temporalmente. Espera 1h y vuelve a correr manualmente.

**La página no carga en GitHub Pages**  
→ Asegúrate de haber seleccionado `/docs` como carpeta en la configuración de Pages.

**Quiero cambiar el horario de actualización**  
→ Edita la línea `cron` en `.github/workflows/update_dashboard.yml`. Usa [crontab.guru](https://crontab.guru) para construir tu horario.
