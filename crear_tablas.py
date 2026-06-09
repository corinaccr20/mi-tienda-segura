import psycopg2
import os

# ⚠️ PEGÁ AQUÍ TU EXTERNAL DATABASE URL (de Render)
DATABASE_URL = "postgresql://tienda_user:Ft6oIusqowhVE49ocvDCDc6uQmimH2fC@dpg-d8jhk5ojo6nc73ecjhhg-a.oregon-postgres.render.com/tienda_6cyq"

def crear_tablas():
    try:
        conn = psycopg2.connect(DATABASE_URL)
        cur = conn.cursor()
        
        # Crear tablas
        cur.execute("""
            CREATE TABLE IF NOT EXISTS rol (
                id SERIAL PRIMARY KEY,
                nombre VARCHAR(50) NOT NULL
            );
            
            CREATE TABLE IF NOT EXISTS usuario (
                id SERIAL PRIMARY KEY,
                nombre VARCHAR(100) NOT NULL,
                email VARCHAR(100) UNIQUE NOT NULL,
                password VARCHAR(200) NOT NULL,
                rol_id INTEGER REFERENCES rol(id)
            );
            
            CREATE TABLE IF NOT EXISTS categoria (
                id SERIAL PRIMARY KEY,
                nombre VARCHAR(50) NOT NULL
            );
            
            CREATE TABLE IF NOT EXISTS producto (
                id SERIAL PRIMARY KEY,
                nombre VARCHAR(100) NOT NULL,
                descripcion VARCHAR(300) NOT NULL,
                precio FLOAT NOT NULL,
                stock INTEGER NOT NULL,
                categoria_id INTEGER REFERENCES categoria(id),
                imagen_url VARCHAR(300)
            );
            
            CREATE TABLE IF NOT EXISTS imagen (
                id SERIAL PRIMARY KEY,
                url VARCHAR(300) NOT NULL,
                producto_id INTEGER REFERENCES producto(id)
            );
            
            CREATE TABLE IF NOT EXISTS carrito (
                id SERIAL PRIMARY KEY,
                usuario_id INTEGER REFERENCES usuario(id),
                estado VARCHAR(20) DEFAULT 'activo'
            );
            
            CREATE TABLE IF NOT EXISTS detalle_carrito (
                id SERIAL PRIMARY KEY,
                carrito_id INTEGER REFERENCES carrito(id),
                producto_id INTEGER REFERENCES producto(id),
                cantidad INTEGER NOT NULL
            );
            
            CREATE TABLE IF NOT EXISTS estado_orden (
                id SERIAL PRIMARY KEY,
                nombre VARCHAR(50) NOT NULL
            );
            
            CREATE TABLE IF NOT EXISTS orden (
                id SERIAL PRIMARY KEY,
                usuario_id INTEGER REFERENCES usuario(id),
                total FLOAT NOT NULL,
                estado_orden_id INTEGER REFERENCES estado_orden(id)
            );
            
            CREATE TABLE IF NOT EXISTS log_sistema (
                id SERIAL PRIMARY KEY,
                mensaje VARCHAR(500),
                nivel VARCHAR(20)
            );
        """)
        
        conn.commit()
        
        # Insertar datos iniciales
        cur.execute("""
            INSERT INTO rol (nombre) VALUES ('admin'), ('cliente')
            ON CONFLICT (id) DO NOTHING;
            
            INSERT INTO categoria (nombre) VALUES ('Electrónica'), ('Ropa'), ('Hogar')
            ON CONFLICT (id) DO NOTHING;
            
            INSERT INTO producto (nombre, descripcion, precio, stock, categoria_id) VALUES
                ('Laptop Gamer', 'Laptop de alta gama con 16GB RAM y 512GB SSD ideal para gaming', 1200.00, 10, 1),
                ('Audífonos Bluetooth', 'Audífonos inalámbricos con cancelación de ruido y 20 horas de batería', 89.99, 25, 1),
                ('Camiseta Deportiva', 'Camiseta transpirable 100% algodón para hacer ejercicio', 25.50, 50, 2),
                ('Lámpara LED', 'Lámpara de escritorio con ajuste de brillo y temperatura', 35.00, 15, 3),
                ('Mouse Inalámbrico', 'Mouse ergonómico con conexión USB y 3 niveles de DPI', 19.99, 40, 1)
            ON CONFLICT (id) DO NOTHING;
        """)
        
        conn.commit()
        print("✅ Tablas y datos creados exitosamente")
        
        cur.close()
        conn.close()
        
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    crear_tablas()