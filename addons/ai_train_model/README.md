# Módulo de Entrenamiento IA para Odoo

Este módulo proporciona funcionalidades para el entrenamiento y gestión de modelos de inteligencia artificial en Odoo, con integración específica para Google Analytics 4 (GA4).

## Características Principales

### 1. Gestión de Operaciones

#### Descarga de Datos
- Interfaz para la descarga de datos predictivos
- Integración con Google Analytics 4
- Gestión automática de datos incrementales

#### Entrenamiento de Modelos
- Sistema de entrenamiento de modelos personalizados
- Evaluación de rendimiento del modelo
- Gestión de pipelines de entrenamiento
- Soporte para columnas de entrenamiento configurables

### 2. Configuración

#### Credenciales GA4
- Gestión de credenciales para Google Analytics 4
- Verificación de permisos GA4
- Configuración de conexión segura

## Estructura Técnica

El módulo está organizado en los siguientes componentes principales:

### Modelos
- Gestión de credenciales (`model_credential.py`)
- Control de descargas (`model_download.py`)
- Sistema de entrenamiento (`model_trainer.py`)

### Controladores
- Gestión de descargas de modelos
- Control de acceso y permisos

### Utilidades
- Procesamiento de datos (`datos.py`)
- Evaluación de modelos (`evaluacion.py`)
- Gestión incremental (`incremental.py`)
- Configuración de pipelines (`pipelines.py`)
- Entrenamiento por columnas (`train_column.py`)

### Wizards
- Asistente para importación CSV

## Requisitos
- Odoo 17.0
- Acceso a Google Analytics 4
- Permisos de API configurados en Google Cloud Platform

## Instalación

1. Copiar el módulo en la carpeta addons de Odoo
2. Actualizar la lista de módulos en Odoo
3. Instalar el módulo "AI Train Model"
4. Configurar las credenciales de GA4 en la sección de configuración

## Uso

1. Configurar las credenciales de GA4 en el menú de configuración
2. Utilizar el menú de operaciones para:
   - Descargar datos de GA4
   - Entrenar modelos con los datos descargados
3. Revisar los resultados del entrenamiento en la interfaz del modelo

## Seguridad

El módulo incluye un sistema de control de acceso detallado definido en `security/ir.model.access.csv`.
