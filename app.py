import os
import uuid
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify, send_from_directory
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
import json
from functools import wraps

# Configuración de la aplicación
app = Flask(__name__)
app.secret_key = 'clave_secreta_restaurante_2024'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///restaurante.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = 'static/uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

# Asegurar que la carpeta de uploads existe
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Inicializar base de datos
db = SQLAlchemy(app)

# Modelos de la base de datos
class Configuracion(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nombre_restaurante = db.Column(db.String(100), default="Mi Restaurante")
    telefono = db.Column(db.String(20), default="+1234567890")
    direccion = db.Column(db.String(200), default="Dirección del restaurante")
    logo = db.Column(db.String(200), default="logo.png")
    impuesto = db.Column(db.Float, default=0.0)
    max_extras = db.Column(db.Integer, default=5)

class Categoria(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100), nullable=False)
    descripcion = db.Column(db.Text)
    activa = db.Column(db.Boolean, default=True)
    platos = db.relationship('Plato', backref='categoria_obj', lazy=True)

class Producto(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100), nullable=False)
    precio_compra = db.Column(db.Float, nullable=False)
    unidad_medida = db.Column(db.String(50), nullable=False)
    cantidad = db.Column(db.Float, nullable=False)
    activo = db.Column(db.Boolean, default=True)
    fecha_creacion = db.Column(db.DateTime, default=datetime.utcnow)

class Plato(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100), nullable=False)
    descripcion = db.Column(db.Text)
    precio_venta = db.Column(db.Float, nullable=False)
    imagen = db.Column(db.String(200))
    activo = db.Column(db.Boolean, default=True)
    categoria_id = db.Column(db.Integer, db.ForeignKey('categoria.id'))
    fecha_creacion = db.Column(db.DateTime, default=datetime.utcnow)
    ingredientes = db.relationship('IngredientePlato', backref='plato', lazy=True)

class IngredientePlato(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    plato_id = db.Column(db.Integer, db.ForeignKey('plato.id'), nullable=False)
    producto_id = db.Column(db.Integer, db.ForeignKey('producto.id'), nullable=False)
    cantidad = db.Column(db.Float, nullable=False)
    producto = db.relationship('Producto', backref='ingredientes')

class Extra(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100), nullable=False)
    precio = db.Column(db.Float, nullable=False)
    activo = db.Column(db.Boolean, default=True)

class Pedido(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    codigo = db.Column(db.String(20), unique=True, nullable=False)
    cliente_nombre = db.Column(db.String(100))
    cliente_telefono = db.Column(db.String(20), nullable=False)
    cliente_direccion = db.Column(db.Text, nullable=False)
    cliente_ubicacion = db.Column(db.Text)  # Coordenadas o referencia
    estado = db.Column(db.String(20), default='pendiente')  # pendiente, confirmado, preparando, enviado, entregado, cancelado
    total = db.Column(db.Float, nullable=False)
    fecha_creacion = db.Column(db.DateTime, default=datetime.utcnow)
    items = db.relationship('ItemPedido', backref='pedido', lazy=True)
    extras = db.relationship('ExtraPedido', backref='pedido', lazy=True)

class ItemPedido(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    pedido_id = db.Column(db.Integer, db.ForeignKey('pedido.id'), nullable=False)
    plato_id = db.Column(db.Integer, db.ForeignKey('plato.id'), nullable=False)
    cantidad = db.Column(db.Integer, nullable=False)
    precio_unitario = db.Column(db.Float, nullable=False)
    personalizaciones = db.Column(db.Text)  # JSON con personalizaciones
    plato = db.relationship('Plato', backref='pedidos')

class ExtraPedido(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    pedido_id = db.Column(db.Integer, db.ForeignKey('pedido.id'), nullable=False)
    extra_id = db.Column(db.Integer, db.ForeignKey('extra.id'), nullable=False)
    cantidad = db.Column(db.Integer, nullable=False)
    precio_unitario = db.Column(db.Float, nullable=False)
    extra = db.relationship('Extra', backref='pedidos')

class Usuario(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(120), nullable=False)
    rol = db.Column(db.String(20), default='admin')  # admin, empleado

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

# Decorador para requerir login
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

# Decorador para requerir admin
def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        user = Usuario.query.get(session['user_id'])
        if not user or user.rol != 'admin':
            flash('Acceso denegado. Se requieren permisos de administrador.', 'error')
            return redirect(url_for('index'))
        return f(*args, **kwargs)
    return decorated_function

# Rutas de autenticación
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        user = Usuario.query.filter_by(username=username).first()
        
        if user and user.check_password(password):
            session['user_id'] = user.id
            session['username'] = user.username
            session['rol'] = user.rol
            flash('Inicio de sesión exitoso.', 'success')
            return redirect(url_for('admin_panel'))
        else:
            flash('Usuario o contraseña incorrectos.', 'error')
    
    config = Configuracion.query.first()
    if not config:
        config = Configuracion()
        db.session.add(config)
        db.session.commit()
    return render_template('login.html',config=config)

@app.route('/logout')
def logout():
    session.clear()
    flash('Sesión cerrada.', 'info')
    return redirect(url_for('index'))

# Rutas principales
@app.route('/')
def index():
    categoria_id = request.args.get('categoria_id', type=int)
    search = request.args.get('search', '')
    categorias = Categoria.query.all()
    query:Plato = Plato.query.filter(Plato.activo == True)
    if categoria_id:
        cat:Categoria = Categoria.query.filter(id=categoria_id)
        query.categoria_nombre = cat.nombre
        query = query.filter(Plato.categoria_id == categoria_id)
    if search:
        query = query.filter(Plato.nombre.ilike(f'%{search}%'))
    platos = query.all()
    config = Configuracion.query.first()
    if not config:
        config = Configuracion()
        db.session.add(config)
        db.session.commit()
    # Detectar si es una petición AJAX
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        # Devolver solo el HTML necesario para la sección de platos
        return render_template('platos_list.html', 
                             platos=platos,
                             categorias=categorias,
                             categoria_actual=categoria_id,
                             search=search)
    return render_template('index.html', categorias=categorias, platos=platos, config=config)

@app.route('/menu')
def menu():
    categoria_id = request.args.get('categoria_id', type=int)
    search = request.args.get('search', '')
    
    query = Plato.query.filter_by(activo=True)
    
    if categoria_id:
        query = query.filter_by(categoria_id=categoria_id)
    
    if search:
        query = query.filter(Plato.nombre.ilike(f'%{search}%'))
    
    platos = query.all()
    categorias = Categoria.query.filter_by(activa=True).all()
    config = Configuracion.query.first()
    
    return render_template('menu.html', platos=platos, categorias=categorias, 
                          categoria_actual=categoria_id, search=search, config=config)

@app.route('/agregar_carrito/<int:plato_id>', methods=['POST'])
def agregar_carrito(plato_id):
    plato = Plato.query.get_or_404(plato_id)
    
    # Inicializar carrito si no existe
    if 'carrito' not in session:
        session['carrito'] = []
    
    # Verificar si el plato ya está en el carrito
    carrito = session['carrito']
    encontrado = False
    
    for item in carrito:
        if item['plato_id'] == plato_id:
            item['cantidad'] += 1
            encontrado = True
            break
    
    if not encontrado:
        carrito.append({
            'plato_id': plato_id,
            'nombre': plato.nombre,
            'precio': float(plato.precio_venta),
            'imagen': plato.imagen,
            'cantidad': 1,
            'personalizaciones': {}
        })
    
    session['carrito'] = carrito
    session.modified = True
    
    return jsonify({'success': True, 'carrito_count': len(carrito)})

@app.route('/actualizar_carrito', methods=['POST'])
def actualizar_carrito():
    data = request.get_json()
    item_index = data.get('item_index')
    cantidad = data.get('cantidad')
    
    if 'carrito' in session and 0 <= item_index < len(session['carrito']):
        if cantidad <= 0:
            # Eliminar item si la cantidad es 0
            session['carrito'].pop(item_index)
        else:
            # Actualizar cantidad
            session['carrito'][item_index]['cantidad'] = cantidad
        
        session.modified = True
        return jsonify({'success': True, 'carrito_count': len(session['carrito'])})
    
    return jsonify({'success': False})

@app.route('/carrito')
def carrito():
    carrito = session.get('carrito', [])
    config = Configuracion.query.first()
    extras = Extra.query.filter_by(activo=True).all()
    max_extras = config.max_extras if config else 5
    total = 0
    return render_template('carrito.html', config=config, extras=extras, max_extras=max_extras,total=total)

@app.route('/realizar_pedido', methods=['POST'])
def realizar_pedido():
    if 'carrito' not in session or len(session['carrito']) == 0:
        flash('El carrito está vacío.', 'error')
        return redirect(url_for('carrito'))
    
    # Obtener datos del cliente
    telefono = request.form.get('telefono')
    direccion = request.form.get('direccion')
    ubicacion = request.form.get('ubicacion')
    nombre = request.form.get('nombre', 'Cliente')
    
    if not telefono or not direccion:
        flash('Por favor, complete todos los campos obligatorios.', 'error')
        return redirect(url_for('carrito'))
    
    # Calcular total
    total = 0
    for item in session['carrito']:
        total += item['precio'] * item['cantidad']
    
    # Agregar extras si existen
    extras_seleccionados = request.form.getlist('extras')
    extras_precios = {int(extra_id): float(request.form.get(f'extra_precio_{extra_id}', 0)) 
                     for extra_id in extras_seleccionados if extra_id}
    
    for extra_id in extras_seleccionados:
        if extra_id:
            total += extras_precios[int(extra_id)]
    
    # Crear pedido
    codigo_pedido = str(uuid.uuid4())[:8].upper()
    nuevo_pedido = Pedido(
        codigo=codigo_pedido,
        cliente_nombre=nombre,
        cliente_telefono=telefono,
        cliente_direccion=direccion,
        cliente_ubicacion=ubicacion,
        total=total
    )
    
    db.session.add(nuevo_pedido)
    db.session.flush()  # Para obtener el ID del pedido
    
    # Agregar items al pedido
    for item in session['carrito']:
        nuevo_item = ItemPedido(
            pedido_id=nuevo_pedido.id,
            plato_id=item['plato_id'],
            cantidad=item['cantidad'],
            precio_unitario=item['precio'],
            personalizaciones=json.dumps(item.get('personalizaciones', {}))
        )
        db.session.add(nuevo_item)
    
    # Agregar extras al pedido
    for extra_id in extras_seleccionados:
        if extra_id:
            nuevo_extra = ExtraPedido(
                pedido_id=nuevo_pedido.id,
                extra_id=int(extra_id),
                cantidad=1,
                precio_unitario=extras_precios[int(extra_id)]
            )
            db.session.add(nuevo_extra)
    
    db.session.commit()
    
    # Limpiar carrito
    session.pop('carrito', None)
    
    # Guardar datos del cliente en cookies
    session['cliente_telefono'] = telefono
    session['cliente_direccion'] = direccion
    session['cliente_nombre'] = nombre
    
    flash(f'Pedido realizado con éxito. Su código de pedido es: {codigo_pedido}', 'success')
    return redirect(url_for('confirmacion_pedido', codigo=codigo_pedido))

@app.route('/confirmacion_pedido/<codigo>')
def confirmacion_pedido(codigo):
    pedido:Pedido = Pedido.query.filter_by(codigo=codigo).first_or_404()
    config = Configuracion.query.first()
    if not config:
        config = Configuracion()
        db.session.add(config)
        db.session.commit()
    return render_template('confirmacion_pedido.html', pedido=pedido,config=config)

# Panel de administración
@app.route('/admin')
@login_required
def admin_panel():
    pedidos_pendientes = Pedido.query.filter_by(estado='pendiente').count()
    total_platos = Plato.query.count()
    total_productos = Producto.query.count()
    config = Configuracion.query.first()
    if not config:
        config = Configuracion()
        db.session.add(config)
        db.session.commit()
    return render_template('admin/index.html', 
                         pedidos_pendientes=pedidos_pendientes,
                         total_platos=total_platos,
                         total_productos=total_productos,config=config)

# Gestión de pedidos
@app.route('/admin/pedidos')
@login_required
def admin_pedidos():
    estado = request.args.get('estado', 'pendiente')
    pedidos = Pedido.query.filter_by(estado=estado).order_by(Pedido.fecha_creacion.desc()).all()
    config = Configuracion.query.first()
    if not config:
        config = Configuracion()
        db.session.add(config)
        db.session.commit()
    return render_template('admin/pedidos.html', pedidos=pedidos, estado_actual=estado,config=config)

@app.route('/admin/pedido/<int:pedido_id>')
@login_required
def ver_pedido(pedido_id):
    pedido = Pedido.query.get_or_404(pedido_id)
    config = Configuracion.query.first()
    if not config:
        config = Configuracion()
        db.session.add(config)
        db.session.commit()
    return render_template('admin/ver_pedido.html', pedido=pedido,config=config)

@app.route('/admin/cambiar_estado_pedido/<int:pedido_id>', methods=['POST'])
@login_required
def cambiar_estado_pedido(pedido_id):
    pedido = Pedido.query.get_or_404(pedido_id)
    nuevo_estado = request.form.get('estado')
    
    if nuevo_estado in ['pendiente', 'confirmado', 'preparando', 'enviado', 'entregado', 'cancelado']:
        pedido.estado = nuevo_estado
        db.session.commit()
        flash('Estado del pedido actualizado correctamente.', 'success')
    else:
        flash('Estado no válido.', 'error')
    config = Configuracion.query.first()
    if not config:
        config = Configuracion()
        db.session.add(config)
        db.session.commit()
    return redirect(url_for('ver_pedido', pedido_id=pedido_id))

# Gestión de productos
@app.route('/admin/productos')
@login_required
def admin_productos():
    productos = Producto.query.order_by(Producto.nombre).all()
    config = Configuracion.query.first()
    if not config:
        config = Configuracion()
        db.session.add(config)
        db.session.commit()
    return render_template('admin/productos.html', productos=productos,config=config)

@app.route('/admin/producto/nuevo', methods=['GET', 'POST'])
@login_required
def nuevo_producto():
    if request.method == 'POST':
        nombre = request.form.get('nombre')
        precio_compra = float(request.form.get('precio_compra', 0))
        unidad_medida = request.form.get('unidad_medida')
        cantidad = float(request.form.get('cantidad', 0))
        
        nuevo_producto = Producto(
            nombre=nombre,
            precio_compra=precio_compra,
            unidad_medida=unidad_medida,
            cantidad=cantidad
        )
        
        db.session.add(nuevo_producto)
        db.session.commit()
        
        flash('Producto creado correctamente.', 'success')
        return redirect(url_for('admin_productos'))
    config = Configuracion.query.first()
    if not config:
        config = Configuracion()
        db.session.add(config)
        db.session.commit()
    return render_template('admin/editar_producto.html',config=config)

@app.route('/admin/producto/editar/<int:producto_id>', methods=['GET', 'POST'])
@login_required
def editar_producto(producto_id):
    producto = Producto.query.get_or_404(producto_id)
    
    if request.method == 'POST':
        producto.nombre = request.form.get('nombre')
        producto.precio_compra = float(request.form.get('precio_compra', 0))
        producto.unidad_medida = request.form.get('unidad_medida')
        producto.cantidad = float(request.form.get('cantidad', 0))
        producto.activo = 'activo' in request.form
        
        db.session.commit()
        
        flash('Producto actualizado correctamente.', 'success')
        return redirect(url_for('admin_productos'))
    config = Configuracion.query.first()
    if not config:
        config = Configuracion()
        db.session.add(config)
        db.session.commit()
    return render_template('admin/editar_producto.html', producto=producto,config=config)

@app.route('/admin/producto/eliminar/<int:producto_id>', methods=['POST'])
@login_required
def eliminar_producto(producto_id):
    producto = Producto.query.get_or_404(producto_id)
    
    # Verificar si el producto está siendo usado en algún plato
    ingredientes = IngredientePlato.query.filter_by(producto_id=producto_id).count()
    if ingredientes > 0:
        flash('No se puede eliminar el producto porque está siendo utilizado en uno o más platos.', 'error')
        return redirect(url_for('admin_productos'))
    
    db.session.delete(producto)
    db.session.commit()
    
    flash('Producto eliminado correctamente.', 'success')
    config = Configuracion.query.first()
    if not config:
        config = Configuracion()
        db.session.add(config)
        db.session.commit()
    return redirect(url_for('admin_productos'))

# Gestión de platos
@app.route('/admin/platos')
@login_required
def admin_platos():
    platos = Plato.query.all()
    config = Configuracion.query.first()
    if not config:
        config = Configuracion()
        db.session.add(config)
        db.session.commit()
    return render_template('admin/platos.html', platos=platos,config=config)

@app.route('/admin/plato/nuevo', methods=['GET', 'POST'])
@login_required
def nuevo_plato():
    categorias = Categoria.query.filter_by(activa=True).all()
    productos = Producto.query.filter_by(activo=True).all()
    
    if request.method == 'POST':
        nombre = request.form.get('nombre')
        descripcion = request.form.get('descripcion')
        precio_venta = float(request.form.get('precio_venta', 0))
        categoria_id = int(request.form.get('categoria_id', 0))
        
        # Manejar la imagen
        imagen = None
        if 'imagen' in request.files:
            archivo = request.files['imagen']
            if archivo and archivo.filename:
                filename = secure_filename(archivo.filename)
                # Agregar un timestamp para evitar colisiones
                nombre_unico = f"{datetime.now().timestamp()}_{filename}"
                archivo.save(os.path.join(app.config['UPLOAD_FOLDER'], nombre_unico))
                imagen = nombre_unico
        
        nuevo_plato = Plato(
            nombre=nombre,
            descripcion=descripcion,
            precio_venta=precio_venta,
            imagen=imagen,
            categoria_id=categoria_id
        )
        
        db.session.add(nuevo_plato)
        db.session.flush()  # Para obtener el ID del plato
        
        # Procesar ingredientes
        ingredientes_data = []
        i = 0
        while f'producto_id_{i}' in request.form:
            producto_id = int(request.form.get(f'producto_id_{i}'))
            cantidad = float(request.form.get(f'cantidad_{i}', 0))
            
            ingrediente = IngredientePlato(
                plato_id=nuevo_plato.id,
                producto_id=producto_id,
                cantidad=cantidad
            )
            db.session.add(ingrediente)
            ingredientes_data.append((producto_id, cantidad))
            i += 1
        
        db.session.commit()
        
        flash('Plato creado correctamente.', 'success')
        return redirect(url_for('admin_platos'))
    config = Configuracion.query.first()
    if not config:
        config = Configuracion()
        db.session.add(config)
        db.session.commit()
    return render_template('admin/editar_plato.html', categorias=categorias, productos=productos,config=config)

@app.route('/admin/plato/editar/<int:plato_id>', methods=['GET', 'POST'])
@login_required
def editar_plato(plato_id):
    plato = Plato.query.get_or_404(plato_id)
    categorias = Categoria.query.filter_by(activa=True).all()
    productos = Producto.query.filter_by(activo=True).all()
    
    if request.method == 'POST':
        plato.nombre = request.form.get('nombre')
        plato.descripcion = request.form.get('descripcion')
        plato.precio_venta = float(request.form.get('precio_venta', 0))
        plato.categoria_id = int(request.form.get('categoria_id', 0))
        plato.activo = 'activo' in request.form
        
        # Manejar la imagen
        if 'imagen' in request.files:
            archivo = request.files['imagen']
            if archivo and archivo.filename:
                # Eliminar imagen anterior si existe
                if plato.imagen and os.path.exists(os.path.join(app.config['UPLOAD_FOLDER'], plato.imagen)):
                    os.remove(os.path.join(app.config['UPLOAD_FOLDER'], plato.imagen))
                
                filename = secure_filename(archivo.filename)
                nombre_unico = f"{datetime.now().timestamp()}_{filename}"
                archivo.save(os.path.join(app.config['UPLOAD_FOLDER'], nombre_unico))
                plato.imagen = nombre_unico
        
        # Eliminar ingredientes existentes
        IngredientePlato.query.filter_by(plato_id=plato_id).delete()
        
        # Procesar nuevos ingredientes
        i = 0
        while f'producto_id_{i}' in request.form:
            producto_id = int(request.form.get(f'producto_id_{i}'))
            cantidad = float(request.form.get(f'cantidad_{i}', 0))
            
            ingrediente = IngredientePlato(
                plato_id=plato_id,
                producto_id=producto_id,
                cantidad=cantidad
            )
            db.session.add(ingrediente)
            i += 1
        
        db.session.commit()
        
        flash('Plato actualizado correctamente.', 'success')
        return redirect(url_for('admin_platos'))
    config = Configuracion.query.first()
    if not config:
        config = Configuracion()
        db.session.add(config)
        db.session.commit()
    return render_template('admin/editar_plato.html', plato=plato, categorias=categorias, productos=productos,config=config)

@app.route('/admin/plato/eliminar/<int:plato_id>', methods=['POST'])
@login_required
def eliminar_plato(plato_id):
    plato = Plato.query.get_or_404(plato_id)
    
    # Verificar si el plato está en algún pedido
    items_pedido = ItemPedido.query.filter_by(plato_id=plato_id).count()
    if items_pedido > 0:
        flash('No se puede eliminar el plato porque está incluido en uno o más pedidos.', 'error')
        return redirect(url_for('admin_platos'))
    
    # Eliminar imagen si existe
    if plato.imagen and os.path.exists(os.path.join(app.config['UPLOAD_FOLDER'], plato.imagen)):
        os.remove(os.path.join(app.config['UPLOAD_FOLDER'], plato.imagen))
    
    # Eliminar ingredientes
    IngredientePlato.query.filter_by(plato_id=plato_id).delete()
    
    db.session.delete(plato)
    db.session.commit()
    
    flash('Plato eliminado correctamente.', 'success')
    config = Configuracion.query.first()
    if not config:
        config = Configuracion()
        db.session.add(config)
        db.session.commit()
    return redirect(url_for('admin_platos'))


CONVERSION_FACTORS = {
    'kg': {'g': 1000, 'lb': 2.20462, 'oz': 35.274},
    'g': {'kg': 0.001, 'lb': 0.00220462, 'oz': 0.035274},
    'lb': {'kg': 0.453592, 'g': 453.592, 'oz': 16},
    'oz': {'kg': 0.0283495, 'g': 28.3495, 'lb': 0.0625},
    'lt': {'ml': 1000, 'gal': 0.264172},
    'ml': {'lt': 0.001, 'gal': 0.000264172},
    'gal': {'lt': 3.78541, 'ml': 3785.41},
    'un': {'un': 1}
}

def convert_units(quantity, from_unit, to_unit):
    """Convierte entre unidades de medida con manejo de errores mejorado"""
    if from_unit not in CONVERSION_FACTORS:
        raise ValueError(f"Unidad de origen '{from_unit}' no soportada")
    
    if to_unit not in CONVERSION_FACTORS:
        raise ValueError(f"Unidad de destino '{to_unit}' no soportada")
    
    if from_unit == to_unit:
        return quantity
    
    try:
        factor = CONVERSION_FACTORS[from_unit][to_unit]
        return quantity * factor
    except KeyError:
        # Intentar conversión a través de una unidad intermedia
        try:
            # Buscar una ruta de conversión (ej: oz → kg → g)
            for intermediate_unit in CONVERSION_FACTORS[from_unit]:
                if intermediate_unit in CONVERSION_FACTORS and to_unit in CONVERSION_FACTORS[intermediate_unit]:
                    intermediate_value = quantity * CONVERSION_FACTORS[from_unit][intermediate_unit]
                    return intermediate_value * CONVERSION_FACTORS[intermediate_unit][to_unit]
        except:
            pass
        
        raise ValueError(f"No se puede convertir de {from_unit} a {to_unit}")

# Función adicional para el problema del queso
def calculate_price_per_unit(total_price, total_quantity, quantity_unit, target_unit="g"):
    """
    Calcula el precio por unidad de medida
    Ejemplo: 10 lb de queso a $3500 → precio por 100g
    """
    # Convertir la cantidad total a la unidad objetivo
    converted_quantity = convert_units(total_quantity, quantity_unit, target_unit)
    
    # Calcular precio por unidad
    price_per_unit = total_price / converted_quantity
    
    return price_per_unit

@app.route('/admin/calcular_costo_plato', methods=['POST'])
@login_required
def calcular_costo_plato():
    data = request.get_json()
    ingredientes:Ingredient = data.get('ingredientes', [])
    
    costo_total = 0
    for ingrediente in ingredientes:
        producto_id = ingrediente.get('producto_id')
        cantidad = ingrediente.get('cantidad', 0)
        
        producto:Producto = Producto.query.get(producto_id)
        if producto:
            costo_total += calculate_price_per_unit(producto.precio_compra,producto.cantidad,producto.unidad_medida) * cantidad
    config = Configuracion.query.first()
    if not config:
        config = Configuracion()
        db.session.add(config)
        db.session.commit()
    return jsonify({'costo': round(costo_total, 2)})

# Gestión de categorías
@app.route('/admin/categorias')
@login_required
def admin_categorias():
    categorias = Categoria.query.all()
    config = Configuracion.query.first()
    if not config:
        config = Configuracion()
        db.session.add(config)
        db.session.commit()
    return render_template('admin/categorias.html', categorias=categorias,config=config)

@app.route('/admin/categoria/nueva', methods=['GET', 'POST'])
@login_required
def nueva_categoria():
    if request.method == 'POST':
        nombre = request.form.get('nombre')
        descripcion = request.form.get('descripcion')
        
        nueva_categoria = Categoria(
            nombre=nombre,
            descripcion=descripcion,
            activa='activa' in request.form
        )
        
        db.session.add(nueva_categoria)
        db.session.commit()
        
        flash('Categoría creada correctamente.', 'success')
        return redirect(url_for('admin_categorias'))
    config = Configuracion.query.first()
    if not config:
        config = Configuracion()
        db.session.add(config)
        db.session.commit()
    return render_template('admin/editar_categoria.html',config=config)

@app.route('/admin/categoria/editar/<int:categoria_id>', methods=['GET', 'POST'])
@login_required
def editar_categoria(categoria_id):
    categoria = Categoria.query.get_or_404(categoria_id)
    
    if request.method == 'POST':
        categoria.nombre = request.form.get('nombre')
        categoria.descripcion = request.form.get('descripcion')
        categoria.activa = 'activa' in request.form
        
        db.session.commit()
        
        flash('Categoría actualizada correctamente.', 'success')
        return redirect(url_for('admin_categorias'))
    config = Configuracion.query.first()
    if not config:
        config = Configuracion()
        db.session.add(config)
        db.session.commit()
    return render_template('admin/editar_categoria.html', categoria=categoria,config=config)

@app.route('/admin/categoria/eliminar/<int:categoria_id>', methods=['POST'])
@login_required
def eliminar_categoria(categoria_id):
    categoria = Categoria.query.get_or_404(categoria_id)
    
    # Verificar si la categoría tiene platos asociados
    if categoria.platos:
        flash('No se puede eliminar la categoría porque tiene platos asociados.', 'error')
        return redirect(url_for('admin_categorias'))
    
    db.session.delete(categoria)
    db.session.commit()
    
    flash('Categoría eliminada correctamente.', 'success')
    config = Configuracion.query.first()
    if not config:
        config = Configuracion()
        db.session.add(config)
        db.session.commit()
    return redirect(url_for('admin_categorias'))

# Gestión de extras
@app.route('/admin/extras')
@login_required
def admin_extras():
    extras = Extra.query.all()
    config = Configuracion.query.first()
    if not config:
        config = Configuracion()
        db.session.add(config)
        db.session.commit()
    return render_template('admin/extras.html', extras=extras,config=config)

@app.route('/admin/extra/nuevo', methods=['GET', 'POST'])
@login_required
def nuevo_extra():
    if request.method == 'POST':
        nombre = request.form.get('nombre')
        precio = float(request.form.get('precio', 0))
        
        nuevo_extra = Extra(
            nombre=nombre,
            precio=precio,
            activo='activo' in request.form
        )
        
        db.session.add(nuevo_extra)
        db.session.commit()
        
        flash('Extra creado correctamente.', 'success')
        return redirect(url_for('admin_extras'))
    config = Configuracion.query.first()
    if not config:
        config = Configuracion()
        db.session.add(config)
        db.session.commit()
    return render_template('admin/editar_extra.html',config=config)

@app.route('/admin/extra/editar/<int:extra_id>', methods=['GET', 'POST'])
@login_required
def editar_extra(extra_id):
    extra = Extra.query.get_or_404(extra_id)
    
    if request.method == 'POST':
        extra.nombre = request.form.get('nombre')
        extra.precio = float(request.form.get('precio', 0))
        extra.activo = 'activo' in request.form
        
        db.session.commit()
        
        flash('Extra actualizado correctamente.', 'success')
        return redirect(url_for('admin_extras'))
    config = Configuracion.query.first()
    if not config:
        config = Configuracion()
        db.session.add(config)
        db.session.commit()
    return render_template('admin/editar_extra.html', extra=extra,config=config)

@app.route('/admin/extra/eliminar/<int:extra_id>', methods=['POST'])
@login_required
def eliminar_extra(extra_id):
    extra = Extra.query.get_or_404(extra_id)
    
    # Verificar si el extra está en algún pedido
    extras_pedido = ExtraPedido.query.filter_by(extra_id=extra_id).count()
    if extras_pedido > 0:
        flash('No se puede eliminar el extra porque está incluido en uno o más pedidos.', 'error')
        return redirect(url_for('admin_extras'))
    
    db.session.delete(extra)
    db.session.commit()
    
    flash('Extra eliminado correctamente.', 'success')
    config = Configuracion.query.first()
    if not config:
        config = Configuracion()
        db.session.add(config)
        db.session.commit()
    return redirect(url_for('admin_extras'),config=config)

# Configuración del restaurante
@app.route('/admin/configuracion', methods=['GET', 'POST'])
@admin_required
def admin_configuracion():
    config = Configuracion.query.first()
    if not config:
        config = Configuracion()
        db.session.add(config)
        db.session.commit()
    
    if request.method == 'POST':
        config.nombre_restaurante = request.form.get('nombre_restaurante')
        config.telefono = request.form.get('telefono')
        config.direccion = request.form.get('direccion')
        config.impuesto = float(request.form.get('impuesto', 0))
        config.max_extras = int(request.form.get('max_extras', 5))
        
        # Manejar el logo
        if 'logo' in request.files:
            archivo = request.files['logo']
            if archivo and archivo.filename:
                # Eliminar logo anterior si existe y no es el default
                if config.logo and config.logo != 'logo.png' and os.path.exists(os.path.join(app.config['UPLOAD_FOLDER'], config.logo)):
                    os.remove(os.path.join(app.config['UPLOAD_FOLDER'], config.logo))
                
                filename = secure_filename(archivo.filename)
                nombre_unico = f"logo_{datetime.now().timestamp()}_{filename}"
                archivo.save(os.path.join(app.config['UPLOAD_FOLDER'], nombre_unico))
                config.logo = nombre_unico
        
        db.session.commit()
        flash('Configuración actualizada correctamente.', 'success')
        return redirect(url_for('admin_configuracion'))
    config = Configuracion.query.first()
    if not config:
        config = Configuracion()
        db.session.add(config)
        db.session.commit()
    return render_template('admin/configuracion.html', config=config)

# API para obtener información del carrito
@app.route('/api/carrito')
def api_carrito():
    carrito = session.get('carrito', [])
    config = Configuracion.query.first()
    if not config:
        config = Configuracion()
        db.session.add(config)
        db.session.commit()
    return jsonify({'count': len(carrito), 'items': carrito})

# Ruta para servir archivos subidos
@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

# Inicializar la base de datos y crear usuario admin por defecto
@app.before_first_request
def inicializar_base_datos():
    db.create_all()
    
    # Crear usuario admin por defecto si no existe
    if not Usuario.query.filter_by(username='admin').first():
        admin = Usuario(username='admin')
        admin.set_password('admin123')
        db.session.add(admin)
        db.session.commit()
        print("Usuario admin creado: admin / admin123")

if __name__ == '__main__':
    app.run(debug=True,port=443)