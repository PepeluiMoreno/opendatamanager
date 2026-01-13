"""
Script para registrar el PaginatedHtmlFetcher y sus parámetros en la base de datos.

Este fetcher está diseñado específicamente para buscadores HTML con paginación
como el caso de las Entidades Religiosas del Ministerio de Justicia.
"""

from sqlalchemy.orm import SessionLocal
from app.models import Fetcher, FetcherParams
from uuid import uuid4
import json

def setup_paginated_html_fetcher():
    """Registra el fetcher y sus parámetros en la BD"""
    session = SessionLocal()
    
    try:
        # 1. Crear el Fetcher para HTML Paginated
        fetcher = Fetcher(
            id=uuid4(),
            code="HTML_PAGINATED",
            class_path="app.fetchers.paginated_html.PaginatedHtmlFetcher",
            description="""Buscadores HTML con paginación automática.

Soporta múltiples mecanismos de paginación (links, forms), extracción mediante selectores CSS, y configuración completa de headers y delays. Ideal para portales gubernamentales con resultados paginados."""
        )
        
        session.add(fetcher)
        session.flush()  # Para obtener el ID
        
        # 2. Definir los parámetros obligatorios y opcionales
        parameters = [
            # Parámetros obligatorios
            ("url", True, "string", "URL base del buscador"),
            ("rows_selector", True, "string", "Selector CSS para las filas de datos (ej: 'table tr', '.result-row')"),
            
            # Parámetros de configuración de tabla
            ("has_header", False, "boolean", "La primera fila contiene encabezados"),
            ("header_selectors", False, "string", "Selectores para extraer encabezados (ej: 'th,td') separados por comas"),
            
            # Parámetros de paginación
            ("pagination_type", False, "string", "Tipo de paginación: 'links' o 'form'"),
            ("page_size", False, "integer", "Registros por página para cálculos"),
            ("max_pages", False, "integer", "Límite máximo de páginas para seguridad"),
            
            # Para paginación por links
            ("next_page_selector", False, "string", "Selector CSS para botón 'siguiente'"),
            ("prev_page_selector", False, "string", "Selector CSS para botón 'anterior'"),
            ("total_text_selector", False, "string", "Selector para texto de total (ej: '.total-results')"),
            
            # Para paginación por form
            ("next_form_selector", False, "string", "Selector CSS del form de paginación"),
            ("page_param", False, "string", "Nombre del parámetro de página en el form"),
            
            # Configuración de request
            ("method", False, "string", "Método HTTP (GET/POST)"),
            ("headers", False, "string", "Headers en formato JSON"),
            ("timeout", False, "integer", "Timeout en segundos"),
            ("max_retries", False, "integer", "Número máximo de reintentos"),
            ("retry_delay", False, "float", "Delay base entre reintentos"),
            ("delay_between_pages", False, "float", "Delay entre páginas para evitar bloqueos"),
            
            # Manejo de errores
            ("error_selectors", False, "string", "Selectores CSS que indican página de error"),
            
            # Transformación de datos
            ("clean_html", False, "boolean", "Limpiar HTML y normalizar espacios"),
            ("field_transformations", False, "string", "Transformaciones por campo en formato JSON"),
            ("include_row_metadata", False, "boolean", "Incluir metadata de fila en resultados"),
        ]
        
        # 3. Insertar parámetros
        for param_name, required, data_type, description in parameters:
            param = FetcherParams(
                id=uuid4(),
                fetcher_id=fetcher.id,
                param_name=param_name,
                required=required,
                data_type=data_type
            )
            session.add(param)
        
        session.commit()
        
        print(f"✅ Fetcher HTML_PAGINATED registrado con ID: {fetcher.id}")
        print(f"✅ {len(parameters)} parámetros configurados")
        
        # 4. Mostrar ejemplo de configuración para el caso RER
        print("\n📋 Ejemplo de configuración para Entidades Religiosas (RER):")
        example_config = {
            "url": "https://maper.mjusticia.gob.es/Maper/buscarRER.action",
            "method": "POST",
            "rows_selector": "table tr",
            "has_header": True,
            "pagination_type": "form",
            "page_size": 10,
            "max_pages": 1500,  # 14836 registros / 10 por página ≈ 1484 páginas
            "delay_between_pages": 2.0,
            "timeout": 30,
            "max_retries": 3,
            "total_text_selector": ".total-resultados, .result-count",
            "next_form_selector": "form[name='paginationForm'], .pagination-form",
            "page_param": "pagina",
            "headers": json.dumps({
                "User-Agent": "Mozilla/5.0 (compatible; OpenDataManager/1.0)",
                "Accept": "text/html,application/xhtml+xml"
            }),
            "error_selectors": ".error-message, .pagina-error",
            "clean_html": True,
            "field_transformations": json.dumps({
                "Número": "trim",
                "Nombre": "trim",
                "Confesión": "trim"
            })
        }
        
        print(json.dumps(example_config, indent=2, ensure_ascii=False))
        
        print("\n🎯 Para usar este fetcher:")
        print("1. Crea un nuevo Resource con fetcher_id = HTML_PAGINATED")
        print("2. Configura los parámetros según el ejemplo anterior")
        print("3. Ajusta los selectores CSS según el HTML real del sitio")
        print("4. El sistema manejará automáticamente la paginación completa")
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        session.rollback()
        raise
    finally:
        session.close()

if __name__ == "__main__":
    setup_paginated_html_fetcher()