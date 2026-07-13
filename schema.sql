-- Script DDL para la creación de la base de datos y tablas para Calificaciones Tributarias
-- NUAMPY - Migración a MySQL (AWS RDS)

CREATE DATABASE IF NOT EXISTS nuampy_db;
USE nuampy_db;

-- 1. Tabla de Usuarios
CREATE TABLE IF NOT EXISTS usuarios (
    id INT AUTO_INCREMENT PRIMARY KEY,
    nombre VARCHAR(100) NOT NULL UNIQUE,
    contrasena VARCHAR(256) NOT NULL, -- Almacena el hash SHA-256
    rol VARCHAR(50) NOT NULL, -- 'ADMIN', 'CORREDOR', 'INVITADO'
    correo VARCHAR(255) DEFAULT '',
    rut VARCHAR(20) DEFAULT '',
    empresa_corredora VARCHAR(100) DEFAULT NULL, -- Específico de CORREDOR
    mercado VARCHAR(50) DEFAULT NULL,            -- Específico de CORREDOR
    fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_nombre (nombre)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 2. Tabla de Calificaciones Tributarias
CREATE TABLE IF NOT EXISTS calificaciones_tributarias (
    id INT AUTO_INCREMENT PRIMARY KEY,
    mercado VARCHAR(50) NOT NULL,
    instrumento VARCHAR(100) NOT NULL,
    anio INT NOT NULL, -- Periodo comercial, >= 1900
    fecha_pago DATETIME NOT NULL, -- >= 1900
    secuencia_evento INT NOT NULL, -- >= 1000
    dividendo DECIMAL(18, 8) NOT NULL, -- 8 decimales, sin negativos
    valor_historico DECIMAL(18, 8) NOT NULL, -- 8 decimales, sin negativos
    descripcion TEXT NOT NULL,
    isfut TINYINT(1) NOT NULL DEFAULT 0, -- Booleano (0 o 1)
    factor_actualizacion DECIMAL(18, 8) NOT NULL, -- 8 decimales, sin negativos
    tipo_sociedad VARCHAR(50) NOT NULL,
    corredor VARCHAR(100) NOT NULL, -- Origen
    monto_total DECIMAL(18, 8) DEFAULT NULL,
    calificacion_valor DECIMAL(18, 8) DEFAULT NULL,
    
    -- Estructura de factores y montos del 8 al 37
    factores JSON DEFAULT NULL,
    montos JSON DEFAULT NULL,
    
    -- Hash único para control de duplicados en la carga masiva (SHA-256)
    hash VARCHAR(64) UNIQUE NOT NULL,
    fecha_registro TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    INDEX idx_filtros (mercado, instrumento, anio, corredor, tipo_sociedad),
    CONSTRAINT chk_anio CHECK (anio >= 1900),
    CONSTRAINT chk_secuencia CHECK (secuencia_evento >= 1000),
    CONSTRAINT chk_dividendo CHECK (dividendo >= 0),
    CONSTRAINT chk_valor_historico CHECK (valor_historico >= 0),
    CONSTRAINT chk_factor_actualizacion CHECK (factor_actualizacion >= 0)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 3. Tabla de Solicitudes de Eliminación
CREATE TABLE IF NOT EXISTS solicitudes_eliminacion (
    id INT AUTO_INCREMENT PRIMARY KEY,
    calificacion_id INT NOT NULL,
    solicitante VARCHAR(100) NOT NULL,
    motivo TEXT,
    estado VARCHAR(20) NOT NULL DEFAULT 'PENDIENTE', -- 'PENDIENTE', 'APROBADA', 'RECHAZADA'
    fecha_solicitud TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (calificacion_id) REFERENCES calificaciones_tributarias(id) ON DELETE CASCADE,
    INDEX idx_estado (estado)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 4. Tabla de Auditoría / Logs (Migrada a MySQL para eliminar dependencia de MongoDB/PyMongo)
CREATE TABLE IF NOT EXISTS logs (
    id INT AUTO_INCREMENT PRIMARY KEY,
    accion VARCHAR(100) NOT NULL,
    usuario VARCHAR(100) DEFAULT NULL,
    fecha TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    detalle JSON DEFAULT NULL,
    INDEX idx_fecha (fecha)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
