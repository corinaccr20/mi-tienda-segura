import os
from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from dotenv import load_dotenv
from flask_mail import Mail, Message

load_dotenv()

app = Flask(__name__)
app.config['SECRET_KEY'] = 'clave-secreta-para-desarrollo'

# ========== CONFIGURACIÓN DE BASE DE DATOS POSTGRESQL ==========
# Usar PostgreSQL en Render (gratis y persistente)
database_url = os.getenv('DATABASE_URL')
if database_url and database_url.startswith('postgres://'):
    database_url = database_url.replace('postgres://', 'postgresql://', 1)

if database_url:
    app.config['SQLALCHEMY_DATABASE_URI'] = database_url
else:
    # Fallback a SQLite (solo para desarrollo local)
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///tienda.db'

app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# ========== CONFIGURACIÓN DE CORREO ==========
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True


db = SQLAlchemy(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

mail = Mail(app)

# ========== MODELOS (10 TABLAS) ==========
class Rol(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(50), nullable=False)

class Usuario(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    rol_id = db.Column(db.Integer, db.ForeignKey('rol.id'))

class Categoria(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(50), nullable=False)

class Producto(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100), nullable=False)
    descripcion = db.Column(db.String(300), nullable=False)
    precio = db.Column(db.Float, nullable=False)
    stock = db.Column(db.Integer, nullable=False)
    categoria_id = db.Column(db.Integer, db.ForeignKey('categoria.id'))
    imagen_url = db.Column(db.String(300), nullable=True)

class Imagen(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    url = db.Column(db.String(300), nullable=False)
    producto_id = db.Column(db.Integer, db.ForeignKey('producto.id'))

class Carrito(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    usuario_id = db.Column(db.Integer, db.ForeignKey('usuario.id'))
    estado = db.Column(db.String(20), default='activo')

class DetalleCarrito(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    carrito_id = db.Column(db.Integer, db.ForeignKey('carrito.id'))
    producto_id = db.Column(db.Integer, db.ForeignKey('producto.id'))
    cantidad = db.Column(db.Integer, nullable=False)

class EstadoOrden(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(50), nullable=False)

class Orden(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    usuario_id = db.Column(db.Integer, db.ForeignKey('usuario.id'))
    total = db.Column(db.Float, nullable=False)
    estado_orden_id = db.Column(db.Integer, db.ForeignKey('estado_orden.id'))

class LogSistema(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    mensaje = db.Column(db.String(500))
    nivel = db.Column(db.String(20))

@login_manager.user_loader
def load_user(user_id):
    return Usuario.query.get(int(user_id))

# ========== RUTAS ==========
@app.route('/')
def index():
    return redirect(url_for('login'))

@app.route('/registro', methods=['GET', 'POST'])
def registro():
    if request.method == 'POST':
        hashed_password = generate_password_hash(request.form['password'])
        nuevo_usuario = Usuario(
            nombre=request.form['nombre'],
            email=request.form['email'],
            password=hashed_password,
            rol_id=2
        )
        db.session.add(nuevo_usuario)
        db.session.commit()
        flash('Registro exitoso. Ahora inicia sesión', 'success')
        return redirect(url_for('login'))
    return render_template('registro.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        user = Usuario.query.filter_by(email=request.form['email']).first()
        if user and check_password_hash(user.password, request.form['password']):
            login_user(user)
            return redirect(url_for('productos'))
        flash('Credenciales incorrectas', 'danger')
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

@app.route('/productos')
@login_required
def productos():
    productos_lista = Producto.query.all()
    return render_template('productos.html', productos=productos_lista)

@app.route('/comprar/<int:producto_id>')
@login_required
def comprar(producto_id):
    producto = Producto.query.get_or_404(producto_id)
    flash(f'✅ Compra simulada de: {producto.nombre} - Precio: ${producto.precio}', 'success')
    return redirect(url_for('productos'))

# ========== INICIALIZAR BASE DE DATOS ==========
with app.app_context():
    print("🔧 Creando tablas en PostgreSQL...")
    db.create_all()
    
    # Insertar roles
    if not Rol.query.first():
        print("📌 Insertando roles...")
        db.session.add_all([Rol(nombre='admin'), Rol(nombre='cliente')])
        db.session.commit()
    
    # Insertar categorías
    if not Categoria.query.first():
        print("📌 Insertando categorías...")
        db.session.add_all([Categoria(nombre='Electrónica'), Categoria(nombre='Ropa'), Categoria(nombre='Hogar')])
        db.session.commit()
    
    # Insertar productos
    if not Producto.query.first():
        print("📌 Insertando productos...")
        productos = [
            Producto(nombre='Laptop Gamer', descripcion='Laptop de alta gama con 16GB RAM y 512GB SSD ideal para gaming', precio=1200.00, stock=10, categoria_id=1),
            Producto(nombre='Audífonos Bluetooth', descripcion='Audífonos inalámbricos con cancelación de ruido y 20 horas de batería', precio=89.99, stock=25, categoria_id=1),
            Producto(nombre='Camiseta Deportiva', descripcion='Camiseta transpirable 100% algodón para hacer ejercicio', precio=25.50, stock=50, categoria_id=2),
            Producto(nombre='Lámpara LED', descripcion='Lámpara de escritorio con ajuste de brillo y temperatura', precio=35.00, stock=15, categoria_id=3),
            Producto(nombre='Mouse Inalámbrico', descripcion='Mouse ergonómico con conexión USB y 3 niveles de DPI', precio=19.99, stock=40, categoria_id=1)
        ]
        db.session.add_all(productos)
        db.session.commit()
    
    print("✅ Base de datos PostgreSQL inicializada correctamente")

if __name__ == '__main__':
    app.run(debug=True)