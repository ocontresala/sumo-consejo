# Sistema de Informes — Sumo Consejo de Estaca

Aplicación web para que los miembros del sumo consejo diligencien sus informes mensuales de asesor de barrio.

---

## Inicio rápido

### Requisitos
- Docker Desktop instalado (Windows/Mac/Linux)
- Puerto 5000 disponible

### Levantar la aplicación

```bash
# 1. Descomprime el archivo y entra a la carpeta
cd sumo-consejo

# 2. Construye e inicia
docker compose up --build

# 3. Abre en el navegador
http://localhost:5000
```

La base de datos se crea automáticamente en la carpeta `data/` la primera vez.

---

## Usuarios de prueba (precargados)

| Rol | Nombre | Correo | Contraseña |
|-----|--------|--------|------------|
| Administrador | Presidente de Estaca | admin@estaca.org | admin123 |
| Asesor | Élder García | garcia@estaca.org | asesor123 |
| Asesor | Élder López | lopez@estaca.org | asesor123 |
| Asesor | Élder Martínez | martinez@estaca.org | asesor123 |
| Asesor | Élder Rodríguez | rodriguez@estaca.org | asesor123 |
| Asesor | Élder Hernández | hernandez@estaca.org | asesor123 |

**Cambia las contraseñas antes de usar en producción.**

---

## Estructura del proyecto

```
sumo-consejo/
├── docker-compose.yml
├── data/                  ← Base de datos SQLite (se crea automáticamente)
│   └── sumo_consejo.db
└── app/
    ├── Dockerfile
    ├── requirements.txt
    ├── app.py             ← Aplicación principal
    └── templates/
        ├── base.html
        ├── login.html
        ├── dashboard.html
        ├── informe.html
        ├── admin.html
        └── admin_informe.html
```

---

## Funcionalidades

### Asesor de barrio
- Iniciar sesión con su correo
- Ver historial de informes enviados
- Crear informe mensual con las 5 hojas:
  1. Cuórum de élderes
  2. Ministración
  3. Obra misional
  4. Templo e historia familiar
  5. Estado general del barrio
- Guardar como borrador y completar después
- Enviar el informe a la presidencia
- Ver observaciones de la presidencia

### Administrador (Presidencia de estaca)
- Ver estado de los 5 barrios
- Ver todos los informes enviados
- Leer el detalle completo de cada informe
- Escribir observaciones y marcar como revisado

---

## Personalizar

### Cambiar nombres de barrios y asesores
Edita la función `seed_db()` en `app.py` antes del primer inicio. O modifica directamente la base de datos con cualquier cliente SQLite.

### Cambiar la clave secreta
En `docker-compose.yml`, cambia el valor de `SECRET_KEY`:
```yaml
environment:
  - SECRET_KEY=tu-clave-muy-segura-aqui
```

### Detener la aplicación
```bash
docker compose down
```

### Actualizar después de cambios en el código
```bash
docker compose up --build
```

---

## Respaldo de datos

Los datos están en `data/sumo_consejo.db`. Para respaldar, simplemente copia ese archivo.

```bash
cp data/sumo_consejo.db data/sumo_consejo_backup_$(date +%Y%m%d).db
```
