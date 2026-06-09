from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
import os                           # ✅ IMPORTANTE: DEBE IR ANTES DE USAR os.getenv
from dotenv import load_dotenv
import sentry_sdk
from flask_mail import Mail, Message
import boto3
import resource
resource.setrlimit(resource.RLIMIT_AS, (256 * 1024 * 1024, 256 * 1024 * 1024))

# ========== CARGAR VARIABLES DE ENTORNO ==========
load_dotenv()

# ========== SENTRY ==========
sentry_sdk.init(
    dsn="https://68972cd08be171eb4bf5412b571b4fb4@04511526618529792.ingest.us.sentry.io/451152",
    traces_sample_rate=1.0,
)

app = Flask(__name__)
app.config['SECRET_KEY'] = 'tu-clave-secreta-cambiala'

# ========== BASE DE DATOS (PostgreSQL en Render) ==========
database_url = os.getenv('DATABASE_URL')
if database_url and database_url.startswith('postgres://'):
    database_url = database_url.replace('postgres://', 'postgresql://', 1)
app.config['SQLALCHEMY_DATABASE_URI'] = database_url or 'sqlite:///tienda.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# ========== CORREO ==========
# ========== CONFIGURACIÓN DE CORREO ==========
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USE_SSL'] = False
app.config['MAIL_USERNAME'] = os.getenv('MAIL_USERNAME')
app.config['MAIL_PASSWORD'] = os.getenv('MAIL_PASSWORD')
app.config['MAIL_DEFAULT_SENDER'] = os.getenv('MAIL_USERNAME', 'mitienda448@gmail.com')
# ========== S3 ==========
app.config['S3_BUCKET'] = os.getenv('S3_BUCKET')
app.config['AWS_ACCESS_KEY'] = os.getenv('AWS_ACCESS_KEY')
app.config['AWS_SECRET_KEY'] = os.getenv('AWS_SECRET_KEY')

s3_client = boto3.client(
    's3',
    aws_access_key_id=app.config['AWS_ACCESS_KEY'],
    aws_secret_access_key=app.config['AWS_SECRET_KEY'],
    region_name='us-east-2'
)

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

# ========== FUNCIÓN SUBIR A S3 ==========
def subir_imagen_a_s3(archivo, producto_id):
    try:
        nombre_archivo = f"producto_{producto_id}_{secure_filename(archivo.filename)}"
        s3_client.upload_fileobj(
            archivo,
            app.config['S3_BUCKET'],
            nombre_archivo,
            ExtraArgs={'ACL': 'public-read'}
        )
        return f"https://{app.config['S3_BUCKET']}.s3.amazonaws.com/{nombre_archivo}"
    except Exception as e:
        print(f"Error: {e}")
        return None

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
        flash('Registro exitoso', 'success')
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
    return render_template('productos.html', productos=Producto.query.all())

@app.route('/comprar/<int:producto_id>')
@login_required
def comprar(producto_id):
    producto = Producto.query.get_or_404(producto_id)
    
    try:
        print(f"Intentando enviar correo a: {current_user.email}")
        
        msg = Message(
            subject=f'Compra: {producto.nombre}',
            recipients=[current_user.email],
            body=f'Hola {current_user.nombre},\n\nCompraste: {producto.nombre}\nPrecio: ${producto.precio}\n\nGracias por tu compra.'
        )
        
        mail.send(msg)
        print("Correo enviado exitosamente")
        flash(f'✅ Compra realizada. Correo enviado a {current_user.email}', 'success')
        
    except Exception as e:
        print(f"❌ ERROR al enviar correo: {e}")
        flash(f'✅ Compra simulada (error de correo: {str(e)})', 'warning')
    
    return redirect(url_for('productos'))

@app.route('/admin/productos')
@login_required
def admin_productos():
    if current_user.rol_id != 1:
        flash('Acceso denegado', 'danger')
        return redirect(url_for('productos'))
    return render_template('admin_productos.html', productos=Producto.query.all())

@app.route('/admin/subir-imagen/<int:producto_id>', methods=['POST'])
@login_required
def subir_imagen(producto_id):
    if current_user.rol_id != 1:
        return 'Acceso denegado', 403
    archivo = request.files.get('imagen')
    if not archivo or archivo.filename == '':
        flash('Selecciona un archivo', 'danger')
        return redirect(url_for('admin_productos'))
    url = subir_imagen_a_s3(archivo, producto_id)
    if url:
        producto = Producto.query.get(producto_id)
        producto.imagen_url = url
        db.session.commit()
        flash('Imagen subida', 'success')
    else:
        flash('Error', 'danger')
    return redirect(url_for('admin_productos'))

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        if not Rol.query.first():
            db.session.add_all([Rol(nombre='admin'), Rol(nombre='cliente')])
            db.session.commit()
        if not Categoria.query.first():
            db.session.add_all([Categoria(nombre='Electrónica'), Categoria(nombre='Ropa'), Categoria(nombre='Hogar')])
            db.session.commit()
        if not Producto.query.first():
            db.session.add_all([
                Producto(nombre='Laptop Gamer', descripcion='Laptop de alta gama con 16GB RAM y 512GB SSD ideal para gaming', precio=1200.00, stock=10, categoria_id=1),
                Producto(nombre='Audífonos Bluetooth', descripcion='Audífonos inalámbricos con cancelación de ruido y 20 horas de batería', precio=89.99, stock=25, categoria_id=1),
                Producto(nombre='Camiseta Deportiva', descripcion='Camiseta transpirable 100% algodón para hacer ejercicio', precio=25.50, stock=50, categoria_id=2),
                Producto(nombre='Lámpara LED', descripcion='Lámpara de escritorio con ajuste de brillo y temperatura', precio=35.00, stock=15, categoria_id=3),
                Producto(nombre='Mouse Inalámbrico', descripcion='Mouse ergonómico con conexión USB y 3 niveles de DPI', precio=19.99, stock=40, categoria_id=1)
            ])
            db.session.commit()
    app.run(debug=True)