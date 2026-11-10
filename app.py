import sqlite3
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, flash

app = Flask(__name__)
app.secret_key = 'clave_secreta_para_mensajes'

# --- CONEXIONES A BASES DE DATOS ---
def get_db_productos():
    conn = sqlite3.connect('productos.db')
    conn.row_factory = sqlite3.Row
    return conn

def get_db_inventario():
    conn = sqlite3.connect('inventario.db')
    conn.row_factory = sqlite3.Row
    return conn

# --- INICIALIZACIÓN DE TABLAS ---
def init_dbs():
    # 1. Base de datos de Productos (Catálogo)
    conn_prod = get_db_productos()
    conn_prod.execute('''
        CREATE TABLE IF NOT EXISTS productos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            codigo TEXT NOT NULL UNIQUE,
            nombre TEXT NOT NULL,
            categoria TEXT NOT NULL,
            proveedor TEXT NOT NULL,
            precio REAL NOT NULL
        )
    ''')
    conn_prod.commit()
    conn_prod.close()

    # 2. Base de datos de Inventario (Existencias y Fechas)
    conn_inv = get_db_inventario()
    conn_inv.execute('''
        CREATE TABLE IF NOT EXISTS movimientos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            producto_id INTEGER NOT NULL,
            cantidad INTEGER NOT NULL,
            ubicacion TEXT NOT NULL,
            fecha_ingreso TEXT NOT NULL,
            fecha_vencimiento TEXT
        )
    ''')
    conn_inv.commit()
    conn_inv.close()

# --- RUTA PRINCIPAL: LEER (READ) ---
@app.route('/')
def index():
    conn_prod = get_db_productos()
    conn_inv = get_db_inventario()

    productos = conn_prod.execute('SELECT * FROM productos ORDER BY id DESC').fetchall()
    movimientos = conn_inv.execute('SELECT * FROM movimientos').fetchall()

    conn_prod.close()
    conn_inv.close()

    # Combinar datos de ambas bases de datos por producto_id
    inv_dict = {m['producto_id']: m for m in movimientos}
    catalogo_completo = []
    for p in productos:
        inv = inv_dict.get(p['id'])
        catalogo_completo.append({
            'id': p['id'],
            'codigo': p['codigo'],
            'nombre': p['nombre'],
            'categoria': p['categoria'],
            'proveedor': p['proveedor'],
            'precio': p['precio'],
            'cantidad': inv['cantidad'] if inv else 0,
            'ubicacion': inv['ubicacion'] if inv else 'Sin asignar',
            'fecha_ingreso': inv['fecha_ingreso'] if inv else '',
            'fecha_vencimiento': inv['fecha_vencimiento'] if inv else ''
        })

    return render_template('index.html', items=catalogo_completo)

# --- RUTA: AGREGAR (CREATE) ---
@app.route('/agregar', methods=['GET', 'POST'])
def agregar():
    if request.method == 'POST':
        codigo = request.form['codigo']
        nombre = request.form['nombre']
        categoria = request.form['categoria']
        proveedor = request.form['proveedor']
        precio = float(request.form['precio'])
        cantidad = int(request.form['cantidad'])
        ubicacion = request.form['ubicacion']
        fecha_ingreso = request.form['fecha_ingreso']
        fecha_vencimiento = request.form['fecha_vencimiento']

        try:
            # Guardar en productos.db
            conn_prod = get_db_productos()
            cursor = conn_prod.cursor()
            cursor.execute('''
                INSERT INTO productos (codigo, nombre, categoria, proveedor, precio)
                VALUES (?, ?, ?, ?, ?)
            ''', (codigo, nombre, categoria, proveedor, precio))
            nuevo_producto_id = cursor.lastrowid
            conn_prod.commit()
            conn_prod.close()

            # Guardar en inventario.db
            conn_inv = get_db_inventario()
            conn_inv.execute('''
                INSERT INTO movimientos (producto_id, cantidad, ubicacion, fecha_ingreso, fecha_vencimiento)
                VALUES (?, ?, ?, ?, ?)
            ''', (nuevo_producto_id, cantidad, ubicacion, fecha_ingreso, fecha_vencimiento))
            conn_inv.commit()
            conn_inv.close()

            flash('Producto e inventario agregados correctamente.', 'success')
            return redirect(url_for('index'))
        except sqlite3.IntegrityError:
            flash('Error: El código de producto ya existe.', 'danger')

    hoy = datetime.today().strftime('%Y-%m-%d')
    return render_template('agregar.html', hoy=hoy)

# --- RUTA: MODIFICAR (UPDATE) ---
@app.route('/editar/<int:id>', methods=['GET', 'POST'])
def editar(id):
    conn_prod = get_db_productos()
    conn_inv = get_db_inventario()

    if request.method == 'POST':
        codigo = request.form['codigo']
        nombre = request.form['nombre']
        categoria = request.form['categoria']
        proveedor = request.form['proveedor']
        precio = float(request.form['precio'])
        cantidad = int(request.form['cantidad'])
        ubicacion = request.form['ubicacion']
        fecha_ingreso = request.form['fecha_ingreso']
        fecha_vencimiento = request.form['fecha_vencimiento']

        conn_prod.execute('''
            UPDATE productos
            SET codigo = ?, nombre = ?, categoria = ?, proveedor = ?, precio = ?
            WHERE id = ?
        ''', (codigo, nombre, categoria, proveedor, precio, id))
        conn_prod.commit()

        conn_inv.execute('''
            UPDATE movimientos
            SET cantidad = ?, ubicacion = ?, fecha_ingreso = ?, fecha_vencimiento = ?
            WHERE producto_id = ?
        ''', (cantidad, ubicacion, fecha_ingreso, fecha_vencimiento, id))
        conn_inv.commit()

        conn_prod.close()
        conn_inv.close()
        flash('Registro actualizado con éxito.', 'info')
        return redirect(url_for('index'))

    producto = conn_prod.execute('SELECT * FROM productos WHERE id = ?', (id,)).fetchone()
    inventario = conn_inv.execute('SELECT * FROM movimientos WHERE producto_id = ?', (id,)).fetchone()
    conn_prod.close()
    conn_inv.close()

    return render_template('editar.html', producto=producto, inventario=inventario)

# --- RUTA: BORRAR (DELETE) ---
@app.route('/borrar/<int:id>', methods=['POST'])
def borrar(id):
    conn_prod = get_db_productos()
    conn_inv = get_db_inventario()

    conn_prod.execute('DELETE FROM productos WHERE id = ?', (id,))
    conn_inv.execute('DELETE FROM movimientos WHERE producto_id = ?', (id,))

    conn_prod.commit()
    conn_inv.commit()
    conn_prod.close()
    conn_inv.close()

    flash('Registro eliminado de ambas bases de datos.', 'warning')
    return redirect(url_for('index'))

if __name__ == '__main__':
    init_dbs()
    app.run(debug=True)
