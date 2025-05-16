from flask import Flask, render_template, request, redirect, url_for, session
import mysql.connector
from mysql.connector import Error

app = Flask(__name__)
app.secret_key = 'clave_secreta_segura'  # Necesario para usar sesiones

# Formulario registro
@app.route('/')
def formulario():
    return render_template('formulario.html')

# Guardar usuario (rol dinámico según formulario)
@app.route('/guardar', methods=['POST'])
def guardar():
    nombre = request.form.get('nombre')
    correo = request.form.get('correo')
    password = request.form.get('password')
    rol = request.form.get('rol')

    if not nombre or not correo or not password or not rol:
        return "Faltan datos."

    try:
        conexion = mysql.connector.connect(
            host='localhost',
            user='root',
            password='',
            database='gestion_tareas'
        )
        cursor = conexion.cursor()
        cursor.execute("INSERT INTO usuarios (nombre, correo, password, rol) VALUES (%s, %s, %s, %s)",
                       (nombre, correo, password, rol))
        conexion.commit()
        return redirect(url_for('login'))

    except Error as e:
        return f"Error: {e}"

    finally:
        if conexion.is_connected():
            cursor.close()
            conexion.close()

# Página login
@app.route('/login')
def login():
    return render_template('login.html')

# Procesar login
@app.route('/iniciar_sesion', methods=['POST'])
def iniciar_sesion():
    correo = request.form.get('correo')
    password = request.form.get('password')
    rol_seleccionado = request.form.get('rol')

    try:
        conexion = mysql.connector.connect(
            host='localhost',
            user='root',
            password='',
            database='gestion_tareas'
        )
        cursor = conexion.cursor()
        cursor.execute("SELECT id, nombre, rol FROM usuarios WHERE correo = %s AND password = %s", (correo, password))
        usuario = cursor.fetchone()

        if usuario:
            if usuario[2] != rol_seleccionado:
                return "El rol seleccionado no coincide con el usuario."

            session['usuario_id'] = usuario[0]
            session['usuario_nombre'] = usuario[1]
            session['usuario_rol'] = usuario[2]

            if usuario[2] == 'admin':
                return redirect(url_for('admin_dashboard'))
            else:
                return redirect(url_for('mostrar_tareas'))

        else:
            return "Credenciales incorrectas"

    except Error as e:
        return f"Error: {e}"

    finally:
        if conexion.is_connected():
            cursor.close()
            conexion.close()

# Dashboard admin - Mostrar tareas con fechas
@app.route('/admin')
def admin_dashboard():
    if 'usuario_rol' not in session or session['usuario_rol'] != 'admin':
        return "Acceso denegado. No eres administrador."

    try:
        conexion = mysql.connector.connect(
            host='localhost',
            user='root',
            password='',
            database='gestion_tareas'
        )
        cursor = conexion.cursor()
        cursor.execute("SELECT id, nombre FROM usuarios WHERE rol = 'usuario'")
        usuarios = cursor.fetchall()

        # Obtener todas las tareas con fechas para mostrar y eliminar
        cursor.execute("""
            SELECT tareas.id, usuarios.nombre, tareas.titulo, tareas.estado, tareas.fecha_inicio, tareas.fecha_fin 
            FROM tareas 
            JOIN usuarios ON tareas.usuario_id = usuarios.id
            """)
        tareas = cursor.fetchall()

        return render_template('admin_dashboard.html', nombre=session['usuario_nombre'], usuarios=usuarios, tareas=tareas)

    except Error as e:
        return f"Error: {e}"

    finally:
        if conexion.is_connected():
            cursor.close()
            conexion.close()

# Admin agrega tarea a cualquier usuario, ahora con fechas inicio y fin
@app.route('/admin/tareas/nueva', methods=['POST'])
def admin_nueva_tarea():
    if 'usuario_rol' not in session or session['usuario_rol'] != 'admin':
        return "Acceso denegado."

    usuario_id = request.form.get('usuario_id')
    titulo = request.form.get('titulo')
    descripcion = request.form.get('descripcion')
    fecha_inicio = request.form.get('fecha_inicio')
    fecha_fin = request.form.get('fecha_fin')

    if not usuario_id or not titulo:
        return "Faltan datos para crear la tarea."

    try:
        conexion = mysql.connector.connect(
            host='localhost',
            user='root',
            password='',
            database='gestion_tareas'
        )
        cursor = conexion.cursor()
        cursor.execute(
            "INSERT INTO tareas (usuario_id, titulo, descripcion, estado, fecha_inicio, fecha_fin) VALUES (%s, %s, %s, %s, %s, %s)",
            (usuario_id, titulo, descripcion, 'Pendiente', fecha_inicio, fecha_fin)
        )
        conexion.commit()
        return redirect(url_for('admin_dashboard'))

    except Error as e:
        return f"Error: {e}"

    finally:
        if conexion.is_connected():
            cursor.close()
            conexion.close()

# Admin elimina tarea
@app.route('/admin/tareas/eliminar/<int:tarea_id>', methods=['POST'])
def admin_eliminar_tarea(tarea_id):
    if 'usuario_rol' not in session or session['usuario_rol'] != 'admin':
        return "Acceso denegado."

    try:
        conexion = mysql.connector.connect(
            host='localhost',
            user='root',
            password='',
            database='gestion_tareas'
        )
        cursor = conexion.cursor()
        cursor.execute("DELETE FROM tareas WHERE id = %s", (tarea_id,))
        conexion.commit()
        return redirect(url_for('admin_dashboard'))

    except Error as e:
        return f"Error: {e}"

    finally:
        if conexion.is_connected():
            cursor.close()
            conexion.close()

# **Nueva ruta: Admin reasigna tarea a otro usuario**
@app.route('/admin/tareas/reasignar', methods=['POST'])
def admin_reasignar_tarea():
    if 'usuario_rol' not in session or session['usuario_rol'] != 'admin':
        return "Acceso denegado. No eres administrador."

    tarea_id = request.form.get('tarea_id')
    nuevo_usuario_id = request.form.get('nuevo_usuario_id')

    if not tarea_id or not nuevo_usuario_id:
        return "Faltan datos para reasignar la tarea."

    try:
        conexion = mysql.connector.connect(
            host='localhost',
            user='root',
            password='',
            database='gestion_tareas'
        )
        cursor = conexion.cursor()

        # Verificar que la tarea existe
        cursor.execute("SELECT id FROM tareas WHERE id = %s", (tarea_id,))
        if cursor.fetchone() is None:
            return "La tarea no existe."

        # Verificar que el usuario existe y tiene rol 'usuario'
        cursor.execute("SELECT id FROM usuarios WHERE id = %s AND rol = 'usuario'", (nuevo_usuario_id,))
        if cursor.fetchone() is None:
            return "El usuario destino no existe o no es un usuario válido."

        # Actualizar la tarea con el nuevo usuario
        cursor.execute(
            "UPDATE tareas SET usuario_id = %s WHERE id = %s",
            (nuevo_usuario_id, tarea_id)
        )
        conexion.commit()

        return redirect(url_for('admin_dashboard'))

    except Error as e:
        return f"Error: {e}"

    finally:
        if conexion.is_connected():
            cursor.close()
            conexion.close()

# Ver tareas del usuario (usuario normal)
@app.route('/tareas')
def mostrar_tareas():
    if 'usuario_id' not in session:
        return redirect(url_for('login'))

    usuario_id = session['usuario_id']

    try:
        conexion = mysql.connector.connect(
            host='localhost',
            user='root',
            password='',
            database='gestion_tareas'
        )
        cursor = conexion.cursor()
        cursor.execute("""
            SELECT id, titulo, descripcion, estado, fecha_inicio, fecha_fin 
            FROM tareas 
            WHERE usuario_id = %s
            """, (usuario_id,))
        tareas = cursor.fetchall()
        return render_template('tareas.html', tareas=tareas, nombre_usuario=session['usuario_nombre'])

    except Error as e:
        return f"Error: {e}"

    finally:
        if conexion.is_connected():
            cursor.close()
            conexion.close()

# Usuario actualiza estado de una tarea (avance paso a paso)
@app.route('/tareas/actualizar_estado/<int:tarea_id>', methods=['POST'])
def actualizar_estado(tarea_id):
    if 'usuario_id' not in session:
        return redirect(url_for('login'))

    nuevo_estado = request.form.get('estado')
    if not nuevo_estado:
        return "Debe seleccionar un estado válido."

    usuario_id = session['usuario_id']

    try:
        conexion = mysql.connector.connect(
            host='localhost',
            user='root',
            password='',
            database='gestion_tareas'
        )
        cursor = conexion.cursor()

        # Verificar que la tarea pertenece al usuario
        cursor.execute("SELECT usuario_id FROM tareas WHERE id = %s", (tarea_id,))
        resultado = cursor.fetchone()
        if not resultado or resultado[0] != usuario_id:
            return "No puedes modificar esta tarea."

        cursor.execute("UPDATE tareas SET estado = %s WHERE id = %s", (nuevo_estado, tarea_id))
        conexion.commit()
        return redirect(url_for('mostrar_tareas'))

    except Error as e:
        return f"Error: {e}"

    finally:
        if conexion.is_connected():
            cursor.close()
            conexion.close()

# Cerrar sesión
@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(debug=True)
