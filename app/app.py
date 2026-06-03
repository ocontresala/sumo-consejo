from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
import sqlite3, os, json as _json
from datetime import datetime

app = Flask(__name__)
app.jinja_env.filters['from_json'] = _json.loads
app.secret_key = os.environ.get('SECRET_KEY', 'sumo-consejo-secret-2025')

@app.context_processor
def inject_globals():
    return {'now': datetime.now(), 'meses': MESES}

DB_PATH = '/data/sumo_consejo.db'

# ── DB ──────────────────────────────────────────────
def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn

def init_db():
    with get_db() as db:
        db.executescript("""
        CREATE TABLE IF NOT EXISTS unidad (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT NOT NULL,
            tipo TEXT DEFAULT 'barrio',
            activo INTEGER DEFAULT 1
        );
        CREATE TABLE IF NOT EXISTS usuario (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            rol TEXT DEFAULT 'asesor',
            activo INTEGER DEFAULT 1,
            created_at TEXT DEFAULT (datetime('now'))
        );
        CREATE TABLE IF NOT EXISTS asignacion_asesor (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            usuario_id INTEGER NOT NULL,
            unidad_id INTEGER NOT NULL,
            fecha_inicio TEXT NOT NULL,
            fecha_fin TEXT,
            FOREIGN KEY(usuario_id) REFERENCES usuario(id),
            FOREIGN KEY(unidad_id) REFERENCES unidad(id)
        );
        CREATE TABLE IF NOT EXISTS informe (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            asignacion_id INTEGER NOT NULL,
            periodo_anio INTEGER NOT NULL,
            periodo_mes INTEGER NOT NULL,
            created_at TEXT DEFAULT (datetime('now')),
            UNIQUE(asignacion_id, periodo_anio, periodo_mes),
            FOREIGN KEY(asignacion_id) REFERENCES asignacion_asesor(id)
        );
        CREATE TABLE IF NOT EXISTS hoja_cuorum (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            informe_id INTEGER UNIQUE NOT NULL,
            estado TEXT DEFAULT 'borrador',
            fecha_envio TEXT,
            reuniones_presidencia INTEGER DEFAULT 0,
            reuniones_correlacion INTEGER DEFAULT 0,
            sesiones_asistidas INTEGER DEFAULT 0,
            elderes_preparacion INTEGER DEFAULT 0,
            est_presidencia_completa TEXT DEFAULT 'proceso',
            est_conoce_responsabilidades TEXT DEFAULT 'proceso',
            est_reuniones_regulares TEXT DEFAULT 'proceso',
            est_transmite_informacion TEXT DEFAULT 'proceso',
            temas_ensenados TEXT DEFAULT '[]',
            necesidades TEXT,
            miembros_atencion TEXT,
            acciones_propuestas TEXT,
            FOREIGN KEY(informe_id) REFERENCES informe(id)
        );
        CREATE TABLE IF NOT EXISTS hoja_ministracion (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            informe_id INTEGER UNIQUE NOT NULL,
            estado TEXT DEFAULT 'borrador',
            fecha_envio TEXT,
            hermanos_activos INTEGER DEFAULT 0,
            entrevistas_realizadas INTEGER DEFAULT 0,
            familias_sin_asignacion INTEGER DEFAULT 0,
            asignaciones_revisadas INTEGER DEFAULT 0,
            est_cobertura_total TEXT DEFAULT 'proceso',
            est_entrevistas TEXT DEFAULT 'proceso',
            est_coord_soc_socorro TEXT DEFAULT 'proceso',
            est_contacto_regular TEXT DEFAULT 'proceso',
            actividades TEXT DEFAULT '[]',
            situaciones TEXT,
            coord_soc_socorro TEXT,
            plan_accion TEXT,
            FOREIGN KEY(informe_id) REFERENCES informe(id)
        );
        CREATE TABLE IF NOT EXISTS hoja_misional (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            informe_id INTEGER UNIQUE NOT NULL,
            estado TEXT DEFAULT 'borrador',
            fecha_envio TEXT,
            bautismos INTEGER DEFAULT 0,
            nuevos_miembros_activos INTEGER DEFAULT 0,
            misioneros_tiempo_completo INTEGER DEFAULT 0,
            misioneros_relevados INTEGER DEFAULT 0,
            est_pdte_conoce_resp TEXT DEFAULT 'proceso',
            est_coord_lider_misional TEXT DEFAULT 'proceso',
            est_nuevos_miembros TEXT DEFAULT 'proceso',
            est_miembros_regresan TEXT DEFAULT 'proceso',
            actividades TEXT DEFAULT '[]',
            situacion_general TEXT,
            miembros_atencion TEXT,
            comentarios TEXT,
            FOREIGN KEY(informe_id) REFERENCES informe(id)
        );
        CREATE TABLE IF NOT EXISTS hoja_templo (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            informe_id INTEGER UNIQUE NOT NULL,
            estado TEXT DEFAULT 'borrador',
            fecha_envio TEXT,
            miembros_recomendacion INTEGER DEFAULT 0,
            jovenes_recomendacion INTEGER DEFAULT 0,
            miembros_preparandose INTEGER DEFAULT 0,
            visitas_coordinadas INTEGER DEFAULT 0,
            est_pdte_conoce_resp TEXT DEFAULT 'proceso',
            est_lider_thf TEXT DEFAULT 'proceso',
            est_siguiente_ordenanza TEXT DEFAULT 'proceso',
            est_activos_hf TEXT DEFAULT 'proceso',
            actividades TEXT DEFAULT '[]',
            estado_obra TEXT,
            miembros_apoyo TEXT,
            necesidades TEXT,
            FOREIGN KEY(informe_id) REFERENCES informe(id)
        );
        CREATE TABLE IF NOT EXISTS hoja_general (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            informe_id INTEGER UNIQUE NOT NULL,
            estado TEXT DEFAULT 'borrador',
            fecha_envio TEXT,
            est_vitalidad TEXT DEFAULT 'proceso',
            est_obispado TEXT DEFAULT 'proceso',
            est_ordenanzas TEXT DEFAULT 'proceso',
            est_misional TEXT DEFAULT 'proceso',
            est_templo TEXT DEFAULT 'proceso',
            est_ministracion TEXT DEFAULT 'proceso',
            actividades_obispado TEXT DEFAULT '[]',
            fortalezas TEXT,
            desafios TEXT,
            plan_accion TEXT,
            solicitudes TEXT,
            FOREIGN KEY(informe_id) REFERENCES informe(id)
        );
        """)
        # Migrate: add columns to hoja tables if missing
        for tabla in ['hoja_cuorum','hoja_ministracion','hoja_misional','hoja_templo','hoja_general']:
            for col, default in [
                ('estado', 'TEXT DEFAULT "borrador"'),
                ('fecha_envio', 'TEXT'),
                ('observacion_presidencia', 'TEXT'),
                ('aprobado_por', 'TEXT'),
                ('fecha_aprobacion', 'TEXT'),
            ]:
                try:
                    db.execute(f'ALTER TABLE {tabla} ADD COLUMN {col} {default}')
                    db.commit()
                except: pass

        row = db.execute("SELECT COUNT(*) as c FROM usuario").fetchone()
        if row['c'] == 0:
            seed_db(db)

def seed_db(db):
    unidades = [
        'Barrio Floridablanca',
        'Barrio La Cumbre',
        'Barrio Diamante',
        'Barrio Piedecuesta',
        'Barrio Villa de San Carlos',
        'Rama San Gil',
    ]
    for u in unidades:
        db.execute("INSERT INTO unidad (nombre) VALUES (?)", (u,))

    # Administradores
    admins = [
        ('Presidente Contreras', 'contreras@estaca.org'),
        ('Presidente Ramirez',   'ramirez@estaca.org'),
        ('Presidente Brito',     'brito@estaca.org'),
    ]
    for nombre, email in admins:
        db.execute("INSERT INTO usuario (nombre, email, password_hash, rol) VALUES (?,?,?,?)",
            (nombre, email, generate_password_hash('admin123'), 'admin'))

    # Asesores
    asesores = [
        ('Gonzalo Lizacano', 'floridablanca@estaca.org', 1),
        ('Camilo Argota',    'lacumbre@estaca.org',      2),
        ('Emilio Rojas',     'diamante@estaca.org',      3),
        ('Edward Torres',    'piedecuesta@estaca.org',   4),
        ('Hernando Basto',   'villasancarlos@estaca.org',5),
        ('Jimmy Rodriguez',  'sangil@estaca.org',        6),
    ]
    for nombre, email, unidad_id in asesores:
        db.execute("INSERT INTO usuario (nombre, email, password_hash, rol) VALUES (?,?,?,?)",
            (nombre, email, generate_password_hash('asesor123'), 'asesor'))
        uid = db.execute("SELECT id FROM usuario WHERE email=?", (email,)).fetchone()['id']
        db.execute("INSERT INTO asignacion_asesor (usuario_id, unidad_id, fecha_inicio) VALUES (?,?,?)",
            (uid, unidad_id, '2025-01-01'))
    db.commit()

# ── AUTH ────────────────────────────────────────────
def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated

def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if session.get('rol') != 'admin':
            flash('Acceso restringido.', 'error')
            return redirect(url_for('dashboard'))
        return f(*args, **kwargs)
    return decorated

# ── HELPERS ─────────────────────────────────────────
MESES = ['','Enero','Febrero','Marzo','Abril','Mayo','Junio',
         'Julio','Agosto','Septiembre','Octubre','Noviembre','Diciembre']

HOJAS_INFO = {
    'cuorum':       ('hoja_cuorum',       '1', 'Cuórum de élderes',         'navy'),
    'ministracion': ('hoja_ministracion', '2', 'Ministración',              'olive'),
    'misional':     ('hoja_misional',     '3', 'Obra misional',             'rust'),
    'templo':       ('hoja_templo',       '4', 'Templo e hª familiar',      'amber'),
    'general':      ('hoja_general',      '5', 'Estado general del barrio', 'purple'),
}

def get_asignacion(usuario_id):
    with get_db() as db:
        return db.execute("""
            SELECT a.*, u.nombre as unidad_nombre
            FROM asignacion_asesor a JOIN unidad u ON u.id=a.unidad_id
            WHERE a.usuario_id=? AND a.fecha_fin IS NULL
        """, (usuario_id,)).fetchone()

def get_or_create_informe(asignacion_id, anio, mes):
    with get_db() as db:
        inf = db.execute("SELECT * FROM informe WHERE asignacion_id=? AND periodo_anio=? AND periodo_mes=?",
            (asignacion_id, anio, mes)).fetchone()
        if not inf:
            db.execute("INSERT INTO informe (asignacion_id, periodo_anio, periodo_mes) VALUES (?,?,?)",
                (asignacion_id, anio, mes))
            db.commit()
            inf = db.execute("SELECT * FROM informe WHERE asignacion_id=? AND periodo_anio=? AND periodo_mes=?",
                (asignacion_id, anio, mes)).fetchone()
        return inf

def get_hoja(tabla, informe_id):
    with get_db() as db:
        return db.execute(f"SELECT * FROM {tabla} WHERE informe_id=?", (informe_id,)).fetchone()

def get_todas_hojas(informe_id):
    return {
        'cuorum':       get_hoja('hoja_cuorum',       informe_id),
        'ministracion': get_hoja('hoja_ministracion',  informe_id),
        'misional':     get_hoja('hoja_misional',      informe_id),
        'templo':       get_hoja('hoja_templo',        informe_id),
        'general':      get_hoja('hoja_general',       informe_id),
    }

# ── ROUTES ──────────────────────────────────────────

@app.route('/')
def home():
    return render_template('home.html')

@app.route('/sumoconsejo')
@app.route('/sumoconsejo/')
def index():
    return redirect(url_for('dashboard') if 'user_id' in session else url_for('login'))

@app.route('/sumoconsejo/login', methods=['GET','POST'])
@app.route('/login', methods=['GET','POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email','').strip().lower()
        pwd   = request.form.get('password','')
        with get_db() as db:
            u = db.execute("SELECT * FROM usuario WHERE email=? AND activo=1", (email,)).fetchone()
        if u and check_password_hash(u['password_hash'], pwd):
            session.update({'user_id': u['id'], 'nombre': u['nombre'], 'rol': u['rol']})
            return redirect(url_for('dashboard'))
        flash('Correo o contraseña incorrectos.', 'error')
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route('/sumoconsejo/dashboard')
@app.route('/dashboard')
@login_required
def dashboard():
    if session['rol'] == 'admin':
        return redirect(url_for('admin_dashboard'))
    asig = get_asignacion(session['user_id'])
    now  = datetime.now()
    with get_db() as db:
        informes = db.execute("""
            SELECT i.* FROM informe i
            JOIN asignacion_asesor a ON a.id=i.asignacion_id
            WHERE a.usuario_id=?
            ORDER BY i.periodo_anio DESC, i.periodo_mes DESC LIMIT 12
        """, (session['user_id'],)).fetchall()
    # Para cada informe calcular estado de hojas
    informes_con_estado = []
    for inf in informes:
        hojas = get_todas_hojas(inf['id'])
        enviadas = sum(1 for h in hojas.values() if h and (dict(h).get('estado') == 'enviado'))
        total    = 5
        informes_con_estado.append({'inf': inf, 'hojas': hojas, 'enviadas': enviadas, 'total': total})
    return render_template('dashboard.html', asig=asig, informes=informes_con_estado,
                           meses=MESES, now=now)

@app.route('/sumoconsejo/admin')
@app.route('/admin')
@login_required
@admin_required
def admin_dashboard():
    with get_db() as db:
        unidades = db.execute("""
            SELECT u.nombre, u.id,
                usr.nombre as asesor,
                (SELECT COUNT(*) FROM hoja_cuorum hc
                 JOIN informe i ON i.id=hc.informe_id
                 JOIN asignacion_asesor a ON a.id=i.asignacion_id
                 WHERE a.unidad_id=u.id AND hc.estado='enviado') as hojas_enviadas
            FROM unidad u
            LEFT JOIN asignacion_asesor aa ON aa.unidad_id=u.id AND aa.fecha_fin IS NULL
            LEFT JOIN usuario usr ON usr.id=aa.usuario_id
            WHERE u.activo=1
        """).fetchall()
        recientes = db.execute("""
            SELECT i.*, u2.nombre as unidad, usr.nombre as asesor
            FROM informe i
            JOIN asignacion_asesor a ON a.id=i.asignacion_id
            JOIN unidad u2 ON u2.id=a.unidad_id
            JOIN usuario usr ON usr.id=a.usuario_id
            ORDER BY i.created_at DESC LIMIT 30
        """).fetchall()
    recientes_con_estado = []
    for inf in recientes:
        hojas = get_todas_hojas(inf['id'])
        enviadas = sum(1 for h in hojas.values() if h and (dict(h).get('estado') == 'enviado'))
        recientes_con_estado.append({'inf': inf, 'hojas': hojas, 'enviadas': enviadas})
    now = datetime.now()
    return render_template('admin.html', unidades=unidades,
                           recientes=recientes_con_estado, meses=MESES, now=now)

@app.route('/informe/<int:anio>/<int:mes>')
@login_required
def ver_informe(anio, mes):
    asig = get_asignacion(session['user_id'])
    if not asig:
        flash('No tienes una unidad asignada.', 'error')
        return redirect(url_for('dashboard'))
    inf   = get_or_create_informe(asig['id'], anio, mes)
    hojas = get_todas_hojas(inf['id'])
    return render_template('informe.html', inf=inf, asig=asig, hojas=hojas,
                           anio=anio, mes=mes, meses=MESES, hojas_info=HOJAS_INFO)

@app.route('/informe/<int:anio>/<int:mes>/guardar/<hoja_key>', methods=['POST'])
@login_required
def guardar_hoja(anio, mes, hoja_key):
    asig = get_asignacion(session['user_id'])
    inf  = get_or_create_informe(asig['id'], anio, mes)
    iid  = inf['id']
    f    = request.form
    # Bloquear si la hoja ya fue enviada o aprobada
    inf_check = get_or_create_informe(asig['id'], anio, mes)
    hoja_actual = get_hoja(HOJAS_INFO[hoja_key][0], inf_check['id'])
    if hoja_actual and dict(hoja_actual).get('estado') in ['enviado', 'aprobado']:
        flash('Esta hoja ya fue enviada y está pendiente de revisión por la presidencia.', 'error')
        return redirect(url_for('ver_informe', anio=anio, mes=mes))
    enviar = f.get('enviar') == '1'
    estado = 'enviado' if enviar else 'borrador'
    fecha_envio = "datetime('now')" if enviar else 'NULL'

    tablas_map = {
        'cuorum': ("INSERT OR REPLACE INTO hoja_cuorum "
            "(informe_id,estado,fecha_envio,reuniones_presidencia,reuniones_correlacion,sesiones_asistidas,"
            "elderes_preparacion,est_presidencia_completa,est_conoce_responsabilidades,"
            "est_reuniones_regulares,est_transmite_informacion,temas_ensenados,"
            "necesidades,miembros_atencion,acciones_propuestas) "
            f"VALUES (?,?,{'datetime('+chr(39)+'now'+chr(39)+')' if enviar else 'NULL'},?,?,?,?,?,?,?,?,?,?,?,?)",
            lambda: (iid, estado,
                f.get('reuniones_presidencia',0), f.get('reuniones_correlacion',0),
                f.get('sesiones_asistidas',0), f.get('elderes_preparacion',0),
                f.get('est_presidencia_completa','proceso'), f.get('est_conoce_responsabilidades','proceso'),
                f.get('est_reuniones_regulares','proceso'), f.get('est_transmite_informacion','proceso'),
                _json.dumps(f.getlist('temas_ensenados')),
                f.get('necesidades',''), f.get('miembros_atencion',''), f.get('acciones_propuestas','')
            )),
        'ministracion': ("INSERT OR REPLACE INTO hoja_ministracion "
            "(informe_id,estado,fecha_envio,hermanos_activos,entrevistas_realizadas,familias_sin_asignacion,"
            "asignaciones_revisadas,est_cobertura_total,est_entrevistas,"
            "est_coord_soc_socorro,est_contacto_regular,actividades,"
            "situaciones,coord_soc_socorro,plan_accion) "
            f"VALUES (?,?,{'datetime('+chr(39)+'now'+chr(39)+')' if enviar else 'NULL'},?,?,?,?,?,?,?,?,?,?,?,?)",
            lambda: (iid, estado,
                f.get('hermanos_activos',0), f.get('entrevistas_realizadas',0),
                f.get('familias_sin_asignacion',0), f.get('asignaciones_revisadas',0),
                f.get('est_cobertura_total','proceso'), f.get('est_entrevistas','proceso'),
                f.get('est_coord_soc_socorro','proceso'), f.get('est_contacto_regular','proceso'),
                _json.dumps(f.getlist('actividades')),
                f.get('situaciones',''), f.get('coord_soc_socorro',''), f.get('plan_accion','')
            )),
        'misional': ("INSERT OR REPLACE INTO hoja_misional "
            "(informe_id,estado,fecha_envio,bautismos,nuevos_miembros_activos,misioneros_tiempo_completo,"
            "misioneros_relevados,est_pdte_conoce_resp,est_coord_lider_misional,"
            "est_nuevos_miembros,est_miembros_regresan,actividades,"
            "situacion_general,miembros_atencion,comentarios) "
            f"VALUES (?,?,{'datetime('+chr(39)+'now'+chr(39)+')' if enviar else 'NULL'},?,?,?,?,?,?,?,?,?,?,?,?)",
            lambda: (iid, estado,
                f.get('bautismos',0), f.get('nuevos_miembros_activos',0),
                f.get('misioneros_tiempo_completo',0), f.get('misioneros_relevados',0),
                f.get('est_pdte_conoce_resp','proceso'), f.get('est_coord_lider_misional','proceso'),
                f.get('est_nuevos_miembros','proceso'), f.get('est_miembros_regresan','proceso'),
                _json.dumps(f.getlist('actividades')),
                f.get('situacion_general',''), f.get('miembros_atencion',''), f.get('comentarios','')
            )),
        'templo': ("INSERT OR REPLACE INTO hoja_templo "
            "(informe_id,estado,fecha_envio,miembros_recomendacion,jovenes_recomendacion,miembros_preparandose,"
            "visitas_coordinadas,est_pdte_conoce_resp,est_lider_thf,"
            "est_siguiente_ordenanza,est_activos_hf,actividades,"
            "estado_obra,miembros_apoyo,necesidades) "
            f"VALUES (?,?,{'datetime('+chr(39)+'now'+chr(39)+')' if enviar else 'NULL'},?,?,?,?,?,?,?,?,?,?,?,?)",
            lambda: (iid, estado,
                f.get('miembros_recomendacion',0), f.get('jovenes_recomendacion',0),
                f.get('miembros_preparandose',0), f.get('visitas_coordinadas',0),
                f.get('est_pdte_conoce_resp','proceso'), f.get('est_lider_thf','proceso'),
                f.get('est_siguiente_ordenanza','proceso'), f.get('est_activos_hf','proceso'),
                _json.dumps(f.getlist('actividades')),
                f.get('estado_obra',''), f.get('miembros_apoyo',''), f.get('necesidades','')
            )),
        'general': ("INSERT OR REPLACE INTO hoja_general "
            "(informe_id,estado,fecha_envio,est_vitalidad,est_obispado,est_ordenanzas,"
            "est_misional,est_templo,est_ministracion,actividades_obispado,"
            "fortalezas,desafios,plan_accion,solicitudes) "
            f"VALUES (?,?,{'datetime('+chr(39)+'now'+chr(39)+')' if enviar else 'NULL'},?,?,?,?,?,?,?,?,?,?,?)",
            lambda: (iid, estado,
                f.get('est_vitalidad','proceso'), f.get('est_obispado','proceso'),
                f.get('est_ordenanzas','proceso'), f.get('est_misional','proceso'),
                f.get('est_templo','proceso'), f.get('est_ministracion','proceso'),
                _json.dumps(f.getlist('actividades_obispado')),
                f.get('fortalezas',''), f.get('desafios',''),
                f.get('plan_accion',''), f.get('solicitudes','')
            )),
    }

    if hoja_key in tablas_map:
        sql, params_fn = tablas_map[hoja_key]
        with get_db() as db:
            db.execute(sql, params_fn())
            db.commit()
        if enviar:
            nombre_hoja = HOJAS_INFO[hoja_key][2]
            flash(f'Hoja "{nombre_hoja}" enviada correctamente a la presidencia.', 'success')
        else:
            flash('Borrador guardado.', 'success')

    return redirect(url_for('ver_informe', anio=anio, mes=mes))

@app.route('/admin/informe/<int:inf_id>')
@login_required
@admin_required
def admin_ver_informe(inf_id):
    with get_db() as db:
        inf = db.execute("""
            SELECT i.*, u.nombre as unidad, usr.nombre as asesor
            FROM informe i
            JOIN asignacion_asesor a ON a.id=i.asignacion_id
            JOIN unidad u ON u.id=a.unidad_id
            JOIN usuario usr ON usr.id=a.usuario_id
            WHERE i.id=?
        """, (inf_id,)).fetchone()
    if not inf:
        flash('Informe no encontrado.', 'error')
        return redirect(url_for('admin_dashboard'))
    hojas = get_todas_hojas(inf_id)
    return render_template('admin_informe.html', inf=inf, hojas=hojas,
                           meses=MESES, hojas_info=HOJAS_INFO)

@app.route('/admin/observacion/<int:inf_id>/<hoja_key>', methods=['POST'])
@login_required
@admin_required
def admin_observacion(inf_id, hoja_key):
    # Guardar observacion en tabla separada o simplemente marcar revisado
    # Por simplicidad agregamos columna observacion a cada hoja
    obs = request.form.get('observacion','')
    tabla = HOJAS_INFO[hoja_key][0]
    with get_db() as db:
        # Agregar columna si no existe
        try:
            db.execute(f"ALTER TABLE {tabla} ADD COLUMN observacion_presidencia TEXT")
            db.commit()
        except:
            pass
        db.execute(f"UPDATE {tabla} SET observacion_presidencia=?, estado='revisado' WHERE informe_id=?",
                   (obs, inf_id))
        db.commit()
    flash('Observación guardada.', 'success')
    return redirect(url_for('admin_ver_informe', inf_id=inf_id))


@app.route('/admin/consolidado')
@login_required
@admin_required
def admin_consolidado():
    import json
    now = datetime.now()
    anio = int(request.args.get('anio', now.year))
    mes  = int(request.args.get('mes',  now.month))

    with get_db() as db:
        unidades = db.execute("""
            SELECT u.id, u.nombre, usr.nombre as asesor
            FROM unidad u
            LEFT JOIN asignacion_asesor aa ON aa.unidad_id=u.id AND aa.fecha_fin IS NULL
            LEFT JOIN usuario usr ON usr.id=aa.usuario_id
            WHERE u.activo=1 ORDER BY u.nombre
        """).fetchall()

    data = {}
    for u in unidades:
        uid = u["id"]
        with get_db() as db:
            asig = db.execute("""
                SELECT a.id FROM asignacion_asesor a
                WHERE a.unidad_id=? AND a.fecha_fin IS NULL
            """, (uid,)).fetchone()
        if not asig:
            data[uid] = {"hojas_enviadas": 0}
            continue

        with get_db() as db:
            inf = db.execute("""
                SELECT * FROM informe
                WHERE asignacion_id=? AND periodo_anio=? AND periodo_mes=?
            """, (asig["id"], anio, mes)).fetchone()

        if not inf:
            data[uid] = {"hojas_enviadas": 0}
            continue

        iid = inf["id"]
        hojas = get_todas_hojas(iid)
        enviadas = sum(1 for h in hojas.values() if h and dict(h).get("estado") in ["enviado","revisado"])

        row = {"hojas_enviadas": enviadas}
        for key, hoja in hojas.items():
            if hoja:
                row[key] = dict(hoja)
            else:
                row[key] = None
        data[uid] = row

    return render_template("admin_consolidado.html",
        unidades=unidades, data=data, anio=anio, mes=mes)


@app.route('/manifest.json')
def manifest():
    from flask import send_from_directory
    return send_from_directory('static', 'manifest.json', mimetype='application/manifest+json')

@app.route('/sw.js')
def service_worker():
    from flask import send_from_directory
    response = send_from_directory('static', 'sw.js', mimetype='application/javascript')
    response.headers['Service-Worker-Allowed'] = '/'
    return response


@app.route('/admin/resetear/<int:inf_id>/<hoja_key>', methods=['POST'])
@login_required
@admin_required
def admin_resetear_hoja(inf_id, hoja_key):
    tabla = HOJAS_INFO.get(hoja_key, [None])[0]
    if not tabla:
        flash('Hoja no válida.', 'error')
        return redirect(url_for('admin_ver_informe', inf_id=inf_id))
    with get_db() as db:
        db.execute(f'DELETE FROM {tabla} WHERE informe_id=?', (inf_id,))
        db.commit()
    nombre = HOJAS_INFO[hoja_key][2]
    flash(f'Hoja "{nombre}" eliminada. El asesor puede volver a diligenciarla.', 'success')
    return redirect(url_for('admin_ver_informe', inf_id=inf_id))

@app.route('/admin/resetear-informe/<int:inf_id>', methods=['POST'])
@login_required
@admin_required
def admin_resetear_informe(inf_id):
    with get_db() as db:
        for tabla in ['hoja_cuorum','hoja_ministracion','hoja_misional','hoja_templo','hoja_general']:
            db.execute(f'DELETE FROM {tabla} WHERE informe_id=?', (inf_id,))
        db.commit()
    flash('Todas las hojas del informe fueron eliminadas. El asesor puede volver a diligenciarlas.', 'success')
    return redirect(url_for('admin_ver_informe', inf_id=inf_id))


@app.route('/admin/aprobar/<int:inf_id>/<hoja_key>', methods=['POST'])
@login_required
@admin_required
def admin_aprobar_hoja(inf_id, hoja_key):
    tabla = HOJAS_INFO.get(hoja_key, [None])[0]
    if not tabla:
        flash('Hoja no válida.', 'error')
        return redirect(url_for('admin_ver_informe', inf_id=inf_id))
    obs = request.form.get('observacion', '')
    aprobado_por = session['nombre']
    with get_db() as db:
        try:
            db.execute(f"ALTER TABLE {tabla} ADD COLUMN aprobado_por TEXT")
            db.commit()
        except: pass
        try:
            db.execute(f"ALTER TABLE {tabla} ADD COLUMN fecha_aprobacion TEXT")
            db.commit()
        except: pass
        db.execute(f"""UPDATE {tabla}
            SET estado='aprobado',
                observacion_presidencia=?,
                aprobado_por=?,
                fecha_aprobacion=datetime('now')
            WHERE informe_id=?""", (obs, aprobado_por, inf_id))
        db.commit()
    nombre = HOJAS_INFO[hoja_key][2]
    flash(f'Hoja "{nombre}" aprobada. El asesor ya no puede editarla.', 'success')
    return redirect(url_for('admin_ver_informe', inf_id=inf_id))

@app.route('/admin/devolver/<int:inf_id>/<hoja_key>', methods=['POST'])
@login_required
@admin_required
def admin_devolver_hoja(inf_id, hoja_key):
    tabla = HOJAS_INFO.get(hoja_key, [None])[0]
    if not tabla:
        flash('Hoja no válida.', 'error')
        return redirect(url_for('admin_ver_informe', inf_id=inf_id))
    obs = request.form.get('observacion', '')
    with get_db() as db:
        try:
            db.execute(f"ALTER TABLE {tabla} ADD COLUMN observacion_presidencia TEXT")
            db.commit()
        except: pass
        db.execute(f"""UPDATE {tabla}
            SET estado='devuelto',
                observacion_presidencia=?
            WHERE informe_id=?""", (obs, inf_id))
        db.commit()
    nombre = HOJAS_INFO[hoja_key][2]
    flash(f'Hoja "{nombre}" devuelta al asesor para corrección.', 'success')
    return redirect(url_for('admin_ver_informe', inf_id=inf_id))

if __name__ == '__main__':
    init_db()
    app.run(host='0.0.0.0', port=5000, debug=False)
