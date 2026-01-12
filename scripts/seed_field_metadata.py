"""
Script para poblar metadata de campos en la base de datos.
Ejecutar con: python -m scripts.seed_field_metadata
"""
from uuid import uuid4
from app.database import SessionLocal
from app.models import FieldMetadata


FIELD_METADATA = [
    # Resource fields
    {
        "table_name": "resource",
        "field_name": "name",
        "label": "Nombre del Resource",
        "help_text": "Nombre único e identificativo para este origen de datos. Ejemplo: 'API Clientes ACME'",
        "placeholder": "e.g., API Clientes ACME"
    },
    {
        "table_name": "resource",
        "field_name": "project",
        "label": "Proyecto",
        "help_text": "Proyecto o dominio al que pertenece este source. Usado para agrupar sources relacionados. Ejemplo: 'clientes', 'ventas', 'inventario'",
        "placeholder": "e.g., clientes"
    },
    {
        "table_name": "resource",
        "field_name": "fetcher_id",
        "label": "Tipo de Servicio Web",
        "help_text": "Tipo de servicio web que se usará para obtener los datos (API REST, SOAP, archivos, etc.)",
        "placeholder": None
    },
    {
        "table_name": "resource",
        "field_name": "active",
        "label": "Activo",
        "help_text": "Si está activo, este resource se ejecutará automáticamente en las actualizaciones programadas",
        "placeholder": None
    },
    # ResourceParam fields (REST específicos)
    {
        "table_name": "resource_param",
        "field_name": "url",
        "label": "URL",
        "help_text": "URL completa del endpoint de la API. Ejemplo: https://api.ejemplo.com/v1/clientes",
        "placeholder": "https://api.ejemplo.com/v1/endpoint"
    },
    {
        "table_name": "resource_param",
        "field_name": "method",
        "label": "Método HTTP",
        "help_text": "Método HTTP a utilizar (GET, POST, PUT, DELETE, etc.). GET es el más común para consultar datos",
        "placeholder": "GET"
    },
    {
        "table_name": "resource_param",
        "field_name": "headers",
        "label": "Headers",
        "help_text": "Headers HTTP en formato JSON. Ejemplo: {\"Authorization\": \"Bearer token123\", \"Content-Type\": \"application/json\"}",
        "placeholder": "{\"Authorization\": \"Bearer ...\"}"
    },
    {
        "table_name": "resource_param",
        "field_name": "timeout",
        "label": "Timeout",
        "help_text": "Tiempo máximo de espera en segundos para la petición HTTP. Por defecto es 30 segundos",
        "placeholder": "30"
    },
    # ResourceParam fields (RER - Registro Entidades Religiosas específicos)
    {
        "table_name": "resource_param",
        "field_name": "nombreEntidad",
        "label": "Nombre Entidad",
        "help_text": "Nombre de la entidad religiosa a buscar (texto libre). Usado en búsquedas del RER del Ministerio de Justicia",
        "placeholder": "e.g., Iglesia Católica"
    },
    {
        "table_name": "resource_param",
        "field_name": "numeroRegistro",
        "label": "Número de Registro",
        "help_text": "Número de registro oficial de la entidad en el RER",
        "placeholder": "e.g., 005476"
    },
    {
        "table_name": "resource_param",
        "field_name": "numeroRegistroAntiguo",
        "label": "Número de Registro Antiguo",
        "help_text": "Número de registro antiguo de la entidad (antes de reorganizaciones del registro)",
        "placeholder": "e.g., 12345"
    },
    {
        "table_name": "resource_param",
        "field_name": "confesion",
        "label": "Confesión Religiosa",
        "help_text": "Confesión religiosa de la entidad. Valores: CATÓLICOS, EVANGÉLICOS, JUDÍOS, MUSULMANES, BUDISTAS, ORTODOXOS, etc.",
        "placeholder": "e.g., CATÓLICOS"
    },
    {
        "table_name": "resource_param",
        "field_name": "subconfesion",
        "label": "Subconfesión",
        "help_text": "Subgrupo dentro de la confesión religiosa. Ejemplos: ADVENTISTAS, BAUTISTAS, PENTECOSTALES, etc.",
        "placeholder": "e.g., BAUTISTAS"
    },
    {
        "table_name": "resource_param",
        "field_name": "seccion",
        "label": "Sección del Registro",
        "help_text": "Sección administrativa del registro. Valores: TODAS, GENERAL, ESPECIAL",
        "placeholder": "e.g., GENERAL"
    },
    {
        "table_name": "resource_param",
        "field_name": "tipoEntidad",
        "label": "Tipo de Entidad",
        "help_text": "Tipo jurídico de la entidad religiosa. Ejemplos: IGLESIA, COMUNIDAD, ASOCIACIÓN, FEDERACIÓN, FUNDACIÓN, ORDEN",
        "placeholder": "e.g., ASOCIACIÓN"
    },
    {
        "table_name": "resource_param",
        "field_name": "comunidad",
        "label": "Comunidad Autónoma",
        "help_text": "Comunidad Autónoma donde está registrada la entidad. Ejemplos: ANDALUCIA, MADRID, CATALUÑA, etc.",
        "placeholder": "e.g., MADRID"
    },
    {
        "table_name": "resource_param",
        "field_name": "provincia",
        "label": "Provincia",
        "help_text": "Provincia donde está registrada la entidad religiosa",
        "placeholder": "e.g., Madrid"
    },
    {
        "table_name": "resource_param",
        "field_name": "municipio",
        "label": "Municipio",
        "help_text": "Municipio donde está registrada la entidad religiosa",
        "placeholder": "e.g., Madrid"
    },
    {
        "table_name": "resource_param",
        "field_name": "page",
        "label": "Página",
        "help_text": "Número de página para paginación de resultados. Usar en búsquedas que devuelven múltiples resultados",
        "placeholder": "1"
    },
    {
        "table_name": "resource_param",
        "field_name": "numeroInscripcion",
        "label": "Número de Inscripción",
        "help_text": "Número de inscripción para obtener el detalle completo de una entidad específica (endpoint DetalleEntidadReligiosa)",
        "placeholder": "e.g., 005476"
    },
    # Application fields
    {
        "table_name": "application",
        "field_name": "name",
        "label": "Nombre de la Aplicación",
        "help_text": "Nombre de la aplicación que recibirá los modelos generados automáticamente",
        "placeholder": "e.g., MiApp Backend"
    },
    {
        "table_name": "application",
        "field_name": "models_path",
        "label": "Ruta de Modelos",
        "help_text": "Ruta absoluta donde se escribirán los archivos de modelos generados. Ejemplo: /app/core/models",
        "placeholder": "/app/core/models"
    },
    {
        "table_name": "application",
        "field_name": "subscribed_projects",
        "label": "Proyectos Suscritos",
        "help_text": "Lista de proyectos a los que esta aplicación está suscrita. Recibirá modelos de sources que pertenezcan a estos proyectos",
        "placeholder": '["clientes", "ventas"]'
    },
]


def seed_field_metadata():
    """Puebla la tabla field_metadata con los metadatos de campos"""
    db = SessionLocal()
    try:
        for meta_data in FIELD_METADATA:
            # Verificar si ya existe
            existing = db.query(FieldMetadata).filter(
                FieldMetadata.table_name == meta_data["table_name"],
                FieldMetadata.field_name == meta_data["field_name"]
            ).first()

            if existing:
                print(f"[OK] Metadata para '{meta_data['table_name']}.{meta_data['field_name']}' ya existe")
                # Actualizar por si cambió
                existing.label = meta_data["label"]
                existing.help_text = meta_data["help_text"]
                existing.placeholder = meta_data["placeholder"]
            else:
                # Crear nuevo
                metadata = FieldMetadata(
                    id=uuid4(),
                    table_name=meta_data["table_name"],
                    field_name=meta_data["field_name"],
                    label=meta_data["label"],
                    help_text=meta_data["help_text"],
                    placeholder=meta_data["placeholder"]
                )
                db.add(metadata)
                print(f"[+] Creado metadata para '{meta_data['table_name']}.{meta_data['field_name']}'")

        db.commit()
        print("\n[OK] Field metadata poblado correctamente")

    except Exception as e:
        db.rollback()
        print(f"\n[ERROR] Error al poblar field metadata: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    seed_field_metadata()
