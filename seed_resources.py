"""
Alta inicial de publishers y resources usando la API de administración GraphQL.

Publishers: organismos publicadores (upsert por acronimo).
Resources:  fuentes de datos fundacionales (upsert por nombre).

Idempotente — safe to run múltiples veces en despliegue.
"""
from __future__ import annotations

import json
import sys
from typing import Any, Dict, List, Optional

from app.graphql.schema import schema


# ── 1. PUBLISHERS ────────────────────────────────────────────────────────────

PUBLISHERS: List[Dict[str, Any]] = [
    {"nombre": "Secretaría de Estado de Función Pública",    "acronimo": "MPTFP",     "nivel": "ESTATAL",    "pais": "España", "portal_url": "https://administracionelectronica.gob.es"},
    {"nombre": "Instituto Nacional de Estadística",          "acronimo": "INE",       "nivel": "ESTATAL",    "pais": "España", "portal_url": "https://www.ine.es"},
    {"nombre": "Ministerio de Hacienda",                     "acronimo": "MINHAC",    "nivel": "ESTATAL",    "pais": "España", "portal_url": "https://www.hacienda.gob.es"},
    {"nombre": "Plataforma de Contratación del Sector Público", "acronimo": "PLACSP", "nivel": "ESTATAL",    "pais": "España", "portal_url": "https://contrataciondelestado.es"},
    {"nombre": "Intervención General de la Administración del Estado", "acronimo": "IGAE", "nivel": "ESTATAL", "pais": "España", "portal_url": "https://www.igae.pap.hacienda.gob.es"},
    {"nombre": "Ministerio de Justicia",                     "acronimo": "MJUST",     "nivel": "ESTATAL",    "pais": "España", "portal_url": "https://www.mjusticia.gob.es"},
    {"nombre": "Fiscalía General del Estado",                "acronimo": "FGE",       "nivel": "ESTATAL",    "pais": "España", "portal_url": "https://www.fiscalia.es"},
    {"nombre": "Consejo General del Notariado",              "acronimo": "CGN",       "nivel": "ESTATAL",    "pais": "España", "portal_url": "https://www.notariado.org"},
    {"nombre": "Dirección General del Catastro",             "acronimo": "DGC",       "nivel": "ESTATAL",    "pais": "España", "portal_url": "https://www.catastro.meh.es"},
    {"nombre": "Junta de Andalucía",                         "acronimo": "JDA",       "nivel": "AUTONOMICO", "pais": "España", "comunidad_autonoma": "Andalucía", "portal_url": "https://www.juntadeandalucia.es"},
    {"nombre": "Base de Datos Nacional de Subvenciones",     "acronimo": "BDNS",      "nivel": "ESTATAL",    "pais": "España", "portal_url": "https://www.infosubvenciones.es"},
    {"nombre": "Colegio de Registradores de la Propiedad, Bienes Muebles y Mercantiles de España", "acronimo": "CORPME", "nivel": "ESTATAL", "pais": "España", "portal_url": "https://www.registradores.org"},
    {"nombre": "Consejo Superior de los Colegios de Arquitectos de España", "acronimo": "CSCAE", "nivel": "ESTATAL", "pais": "España", "portal_url": "https://www.cscae.com"},
    {"nombre": "Consejo General de la Arquitectura Técnica de España", "acronimo": "CGATE", "nivel": "ESTATAL", "pais": "España", "portal_url": "https://www.cgate.es"},
    {"nombre": "Conferencia Episcopal Española",             "acronimo": "CEE",       "nivel": "ESTATAL",    "pais": "España", "portal_url": "https://www.conferenciaepiscopal.es"},
    {"nombre": "Fotocasa (Schibsted Spain)",                 "acronimo": "FOTOCASA",  "nivel": "PRIVADO",    "pais": "España", "portal_url": "https://www.fotocasa.es"},
    {"nombre": "Servicio Público de Empleo Estatal",         "acronimo": "SEPE",      "nivel": "ESTATAL",    "pais": "España", "portal_url": "https://sede.sepe.gob.es"},
    {"nombre": "Tribunal de Cuentas",                        "acronimo": "TRIBUCON",  "nivel": "ESTATAL",    "pais": "España", "portal_url": "https://www.rendiciondecuentas.es"},
    {"nombre": "Ministerio de Hacienda — Entidades Locales", "acronimo": "MINHAC-EL", "nivel": "ESTATAL",    "pais": "España", "portal_url": "https://serviciostelematicosext.hacienda.gob.es"},
    {
        "nombre": "Ayuntamiento de Jerez de la Frontera",
        "acronimo": "AJFRA",
        "nivel": "LOCAL",
        "pais": "España",
        "comunidad_autonoma": "Andalucía",
        "provincia": "Cádiz",
        "municipio": "Jerez de la Frontera",
        "portal_url": "https://transparencia.jerez.es",
    },
]


# ── 2. RESOURCES ─────────────────────────────────────────────────────────────
#
# Cada resource define:
#   fetcher_name    : nombre del fetcher (resuelto a ID en tiempo de ejecución)
#   publisher_acronimo: acrónimo del publisher (resuelto a ID, opcional)
#   name, target_table, active, schedule
#   params          : dict key→value o key→{"value": ..., "is_external": True}

_BASE_JEREZ = "https://transparencia.jerez.es/infopublica/economica"

RESOURCES: List[Dict[str, Any]] = [

    # ── DIR3 ──────────────────────────────────────────────────────────────────
    {
        "name": "DIR3 - Unidades Orgánicas de España",
        "fetcher_name": "API REST",
        "publisher_acronimo": "JDA",
        "target_table": "dir3_unidades",
        "schedule": "0 3 * * 0",
        "params": {
            "url":      "https://datos.juntadeandalucia.es/api/v0/dir3/all?format=json",
            "method":   "GET",
            "timeout":  "120",
            "id_field": "id",
        },
    },

    # ── Geografía ─────────────────────────────────────────────────────────────
    {
        "name": "España - Municipios (INE)",
        "fetcher_name": "File Download",
        "publisher_acronimo": "INE",
        "target_table": "geo_municipios",
        "schedule": "0 4 1 1 *",
        "params": {
            "url":       "https://www.ine.es/daco/daco42/codmun/26codmun.xlsx",
            "format":    "xlsx",
            "skip_rows": "2",
            "timeout":   "60",
            "headers":   '{"User-Agent": "Mozilla/5.0", "Referer": "https://www.ine.es/"}',
        },
    },
    {
        "name": "España - Provincias (INE)",
        "fetcher_name": "API REST",
        "publisher_acronimo": "INE",
        "target_table": "geo_provincias",
        "schedule": "0 4 1 1 *",
        "params": {
            "url":     "https://servicios.ine.es/wstempus/js/ES/VALORES_VARIABLE/20",
            "method":  "GET",
            "timeout": "60",
        },
    },
    {
        "name": "España - Comunidades Autónomas (INE)",
        "fetcher_name": "API REST",
        "publisher_acronimo": "INE",
        "target_table": "geo_ccaa",
        "schedule": "0 4 1 1 *",
        "params": {
            "url":     "https://servicios.ine.es/wstempus/js/ES/VALORES_VARIABLE/70",
            "method":  "GET",
            "timeout": "60",
        },
    },
    {
        "name": "Geonames - Entidades de Población (España)",
        "fetcher_name": "Compressed File",
        "publisher_acronimo": None,
        "target_table": "geo_elm",
        "schedule": "0 3 1 1 *",
        "params": {
            "url":          "https://download.geonames.org/export/dump/ES.zip",
            "format":       "zip",
            "entry":        "ES.txt",
            "inner_format": "tsv",
            "timeout":      "120",
            "headers":      '{"User-Agent": "ODMGR/1.0 (investigacion patrimonial)"}',
            "columns":      '["geonameid","name","asciiname","alternatenames","lat","lon","feature_class","feature_code","country","cc2","admin1","admin2","admin3","admin4","population","elevation","dem","timezone","modification"]',
        },
    },

    # ── FACE ──────────────────────────────────────────────────────────────────
    {
        "name": "FACE - Relaciones OC/OG/UT (Nacional)",
        "fetcher_name": "API REST Paginada",
        "publisher_acronimo": "MPTFP",
        "target_table": "face_relations",
        "schedule": "0 4 * * 0",
        "params": {
            "url":             "https://proveedores.face.gob.es/api/v1/relations",
            "method":          "GET",
            "timeout":         "60",
            "page_param":      "page",
            "page_size_param": "limit",
            "page_size":       "1000",
            "content_field":   "items",
            "id_field":        "",
            "headers":         '{"User-Agent": "Python/requests", "Accept": "application/json"}',
            "page_start":      "1",
        },
    },

    # ── Notarías ──────────────────────────────────────────────────────────────
    {
        "name": "Notarías - Guía Notarial (CGN)",
        "fetcher_name": "REST Loop",
        "publisher_acronimo": "CGN",
        "target_table": "notarios",
        "schedule": "0 2 * * 0",
        "params": {
            "url":              "https://guianotarial.notariado.org/guianotarial/rest/buscar/notarios",
            "method":           "POST",
            "payload_template": '{"nombre":"","apellidos":"","direccion":"","codigoPostal":"","codigoProvincia":"{pivot}","municipio":"","codigoSituacionNotario":"","idiomaExtranjero":""}',
            "id_field":         "codigoNotaria",
            "delay":            "3",
            "timeout":          "60",
        },
    },

    # ── Catastro ──────────────────────────────────────────────────────────────
    {
        "name": "Catastro - Parcelas (Sevilla)",
        "fetcher_name": "WFS",
        "publisher_acronimo": "DGC",
        "target_table": "catastro_parcelas",
        "schedule": "0 3 1 * *",
        "params": {
            "endpoint":     "http://ovc.catastro.meh.es/INSPIRE/wfsCP.aspx",
            "typenames":    "cp:CadastralParcel",
            "bbox":         "-6.4,36.9,-5.3,37.9",
            "outputFormat": "application/gml+xml; version=3.2",
            "srsName":      "EPSG:4326",
            "count":        "500",
            "id_field":     "nationalCadastralReference",
            "timeout":      "120",
        },
    },

    # ── OSM ───────────────────────────────────────────────────────────────────
    {
        "name": "OSM - Inmuebles Eclesiásticos (España)",
        "fetcher_name": "OSM Overpass",
        "publisher_acronimo": None,
        "target_table": "osm_inmuebles_eclesiasticos",
        "schedule": "0 2 * * 0",
        "params": {
            "use_types":     '[{"preset": "RELIGIOUS_ALL"}, {"preset": "RELIGIOUS_BUILDING_EXTRA"}]',
            "demarcacion":   "España",
            "element_types": "node,way,relation",
            "out_format":    "center",
            "timeout":       "1800",
            "max_elements":  "0",
        },
    },
    {
        "name": "OSM - Equipamientos públicos en España",
        "fetcher_name": "OSM Overpass",
        "publisher_acronimo": None,
        "description": (
            "Colegios, hospitales, farmacias, bibliotecas y otros equipamientos "
            "públicos de España extraídos de OpenStreetMap via Overpass API."
        ),
        "target_table": "osm_equipamientos",
        "active": False,
        "params": {
            "use_types":     '[{"preset": "EDUCATION_STRICT", "mode": "and"}]',
            "demarcacion":   "Madrid",
            "element_types": "node",
            "out_format":    "center",
            "timeout":       "60",
            "max_elements":  "200",
        },
    },

    # ── BDNS ──────────────────────────────────────────────────────────────────
    {
        "name": "BDNS - Concesiones de Subvenciones",
        "fetcher_name": "API REST Paginada",
        "publisher_acronimo": "BDNS",
        "target_table": "bdns_concesiones",
        "schedule": "0 4 * * 1",
        "params": {
            "url":              "https://www.infosubvenciones.es/bdnstrans/api/concesiones/busqueda",
            "page_param":       "page",
            "page_size_param":  "pageSize",
            "page_size":        "10000",
            "content_field":    "content",
            "id_field":         "id",
            "fechaDesde":       {"value": "01/01/2026", "is_external": True},
            "fechaHasta":       {"value": "31/12/2026", "is_external": True},
        },
    },
    {
        "name": "BDNS - Convocatorias de Subvenciones",
        "fetcher_name": "API REST Paginada",
        "publisher_acronimo": "BDNS",
        "target_table": "bdns_grants",
        "schedule": "0 3 * * 1",
        "params": {
            "url":              "https://www.infosubvenciones.es/bdnstrans/api/convocatorias/busqueda",
            "method":           "get",
            "page_param":       "page",
            "page_size_param":  "pageSize",
            "page_size":        "10000",
            "content_field":    "content",
            "id_field":         "id",
            "timeout":          "60",
            "query_params":     '{"page": "0", "pageSize": "100", "order": "numeroConvocatoria", "direccion": "desc", "vpd": "GE"}',
            "fechaDesde":       {"value": "01/01/2026", "is_external": True},
            "fechaHasta":       {"value": "31/12/2026", "is_external": True},
        },
    },

    # ── Registros ─────────────────────────────────────────────────────────────
    {
        "name": "Registros de la Propiedad (CORPME)",
        "fetcher_name": "File Download",
        "publisher_acronimo": "CORPME",
        "target_table": "registros_propiedad",
        "schedule": "0 3 1 * *",
        "params": {
            "url":       "https://www.registradores.org/documents/20122/573720/Listado_Registros_Propiedad.xlsx",
            "format":    "xlsx",
            "skip_rows": "1",
            "timeout":   "60",
            "headers":   '{"User-Agent": "Mozilla/5.0", "Referer": "https://www.registradores.org/"}',
        },
    },

    # ── Inmobiliario ──────────────────────────────────────────────────────────
    {
        "name": "Agencias Inmobiliarias (Fotocasa)",
        "fetcher_name": "URL Loop HTML",
        "publisher_acronimo": "FOTOCASA",
        "target_table": "agencias_inmobiliarias",
        "schedule": "0 2 1 * *",
        "params": {
            "url_template":   "https://www.fotocasa.es/buscar-agencias-inmobiliarias/{value}/todas-las-zonas/l",
            "pivot_values": (
                '["a-coruna-provincia","albacete-provincia","alicante-provincia",'
                '"almeria-provincia","araba-alava-provincia","asturias-provincia",'
                '"avila-provincia","badajoz-provincia","barcelona-provincia",'
                '"bizkaia-provincia","burgos-provincia","caceres-provincia",'
                '"cadiz-provincia","cantabria-provincia","castellon-provincia",'
                '"ceuta-provincia","ciudad-real-provincia","cordoba-provincia",'
                '"cuenca-provincia","gipuzkoa-provincia","girona-provincia",'
                '"granada-provincia","guadalajara-provincia","huelva-provincia",'
                '"huesca-provincia","illes-balears-provincia","jaen-provincia",'
                '"la-rioja-provincia","las-palmas-provincia","leon-provincia",'
                '"lleida-provincia","lugo-provincia","madrid-provincia",'
                '"malaga-provincia","melilla-provincia","murcia-provincia",'
                '"navarra-provincia","ourense-provincia","palencia-provincia",'
                '"pontevedra-provincia","salamanca-provincia",'
                '"santa-cruz-de-tenerife-provincia","segovia-provincia",'
                '"sevilla-provincia","soria-provincia","tarragona-provincia",'
                '"teruel-provincia","toledo-provincia","valencia-provincia",'
                '"valladolid-provincia","zamora-provincia","zaragoza-provincia"]'
            ),
            "record_selector":      "article[data-agency-id]",
            "field_attrs":          '{"agency_id": "data-agency-id", "nombre": "data-agency-name"}',
            "field_attr_selectors": '{"url_busqueda": {"selector": "button[data-promiseref]", "attr": "data-promiseref"}}',
            "field_all_text":       '{"estadisticas": ".re-description-item label"}',
            "next_page_selector":   'a[rel="next"]',
            "pivot_field":          "provincia",
            "delay_between_pages":  "1.5",
            "delay_between_pivots": "2.0",
            "max_pages":            "500",
            "timeout":              "30",
        },
    },
    {
        "name": "Agencias Inmobiliarias (RERA Andalucía)",
        "fetcher_name": "API REST Paginada",
        "publisher_acronimo": "JDA",
        "target_table": "agencias_inmobiliarias",
        "schedule": "0 4 * * 0",
        "params": {
            "url":              "https://datos.juntadeandalucia.es/api/action/datastore_search",
            "method":           "GET",
            "page_param":       "offset",
            "page_size_param":  "limit",
            "page_size":        "1000",
            "content_field":    "result.records",
            "id_field":         "_id",
            "timeout":          "60",
            "resource_id":      {"value": "d84a2543-e94b-4d9e-854b-58e4d0b7db38", "is_external": True},
        },
    },
    {
        "name": "Oferta Inmobiliaria en Venta (Fotocasa)",
        "fetcher_name": "URL Loop HTML",
        "publisher_acronimo": "FOTOCASA",
        "target_table": "fotocasa_inmuebles",
        "schedule": "0 3 * * 1",
        "params": {
            "url_template":             "{value}",
            "page_base_url":            "https://www.fotocasa.es",
            "pivot_source_odmgr_query": "agenciasInmobiliariasFotocasa",
            "pivot_source_field":       "url_busqueda",
            "pivot_values": (
                '["https://www.fotocasa.es/es/inmobiliaria-ikesa/comprar/inmuebles/sevilla-provincia/todas-las-zonas/l?clientId=9202760540246",'
                ' "https://www.fotocasa.es/es/inmobiliaria-winning-properties/comprar/inmuebles/sevilla-provincia/todas-las-zonas/l?clientId=9202751942277"]'
            ),
            "pivot_field":          "agencia_provincia_url",
            "record_selector":      "article",
            "field_attr_selectors": (
                '{"url_path":       {"selector": "h3 a", "attr": "href"},'
                ' "agencia_url":    {"selector": "a[data-panot-component=\'link-box-raised\']", "attr": "href"},'
                ' "agencia_nombre": {"selector": "a[data-panot-component=\'link-box-raised\'] img", "attr": "alt"}}'
            ),
            "field_selectors": (
                '{"precio":    "[class*=\'text-display-3\'] span",'
                ' "titulo":    "h3",'
                ' "municipio": "p[class*=\'opacity-75\']"}'
            ),
            "field_all_text":       '{"caracteristicas": "ul[class*=\'text-body-1\'] li"}',
            "next_page_selector":   'a[aria-label="Página siguiente"]',
            "required_field":       "url_path",
            "delay_between_pages":  "2.0",
            "delay_between_pivots": "5.0",
            "max_pages":            "500",
            "timeout":              "30",
        },
    },

    # ── Entidades religiosas ──────────────────────────────────────────────────
    {
        "name": "Diócesis y Entidades Religiosas (CEE)",
        "fetcher_name": "File Download",
        "publisher_acronimo": "CEE",
        "target_table": "entidades_religiosas",
        "schedule": "0 3 1 1 *",
        "params": {
            "url":       "https://www.conferenciaepiscopal.es/data/diocesis.xlsx",
            "format":    "xlsx",
            "skip_rows": "1",
            "timeout":   "30",
            "headers":   '{"User-Agent": "Mozilla/5.0"}',
        },
    },
    {
        "name": "RER - Entidades Religiosas",
        "fetcher_name": "HTML SearchLoop",
        "publisher_acronimo": "MJUST",
        "target_table": "rer_entidades",
        "schedule": "0 3 * * 0",
        "params": {
            "url":                    "http://maper.mjusticia.gob.es/Maper/RER.action",
            "search_field_name":      "comunidadAutonoma",
            "rows_selector":          "table.resultado tr",
            "method":                 "POST",
            "delay_between_searches": "2",
            "timeout":                "60",
        },
    },

    # ── INE series temporales ─────────────────────────────────────────────────
    {
        "name": "INE - Padrón Municipal (todos los municipios)",
        "fetcher_name": "JSON Time Series",
        "publisher_acronimo": "INE",
        "target_table": "ine_padron_municipal",
        "schedule": "0 5 15 6 *",
        "params": {
            "url":              "https://servicios.ine.es/wstempus/js/ES/DATOS_TABLA/2852",
            "query_params":     '{"nult": "10", "det": "2"}',
            "headers":          '{"User-Agent": "Mozilla/5.0 (OpenDataManager/1.0; +https://github.com/PepeluiMoreno)"}',
            "timeout":          "180",
            "meta_container":   "MetaData",
            "meta_code_field":  "Codigo",
            "meta_name_field":  "Nombre",
            "meta_dim_path":    "Variable.Codigo",
            "data_container":   "Data",
            "period_field":     "Anyo",
            "subperiod_field":  "",
            "value_field":      "Valor",
            "secret_field":     "Secreto",
            "serie_name_field": "Nombre",
            "flatten_mode":     "long",
            "batch_size":       "1000",
        },
    },
    {
        "name": "INE - Atlas de Distribución de Renta (municipios)",
        "fetcher_name": "JSON Time Series",
        "publisher_acronimo": "INE",
        "target_table": "ine_renta_municipal",
        "schedule": "0 5 1 11 *",
        "params": {
            "url":              "https://servicios.ine.es/wstempus/js/ES/DATOS_TABLA/30896",
            "query_params":     '{"nult": "8", "det": "2"}',
            "headers":          '{"User-Agent": "Mozilla/5.0 (OpenDataManager/1.0)"}',
            "timeout":          "180",
            "meta_container":   "MetaData",
            "meta_code_field":  "Codigo",
            "meta_name_field":  "Nombre",
            "meta_dim_path":    "Variable.Codigo",
            "data_container":   "Data",
            "period_field":     "Anyo",
            "subperiod_field":  "",
            "value_field":      "Valor",
            "secret_field":     "Secreto",
            "serie_name_field": "Nombre",
            "flatten_mode":     "long",
            "batch_size":       "500",
        },
    },
    {
        "name": "INE - Encuesta Ocupación Hotelera (municipios)",
        "fetcher_name": "JSON Time Series",
        "publisher_acronimo": "INE",
        "target_table": "ine_eoh_municipal",
        "schedule": "0 6 25 * *",
        "params": {
            "url":              "https://servicios.ine.es/wstempus/js/ES/DATOS_TABLA/2066",
            "query_params":     '{"nult": "24", "det": "2"}',
            "headers":          '{"User-Agent": "Mozilla/5.0 (OpenDataManager/1.0)"}',
            "timeout":          "180",
            "meta_container":   "MetaData",
            "meta_code_field":  "Codigo",
            "meta_name_field":  "Nombre",
            "meta_dim_path":    "Variable.Codigo",
            "data_container":   "Data",
            "period_field":     "Anyo",
            "subperiod_field":  "Periodo",
            "value_field":      "Valor",
            "secret_field":     "Secreto",
            "serie_name_field": "Nombre",
            "flatten_mode":     "long",
            "batch_size":       "500",
        },
    },
    {
        "name": "INE - Población por Municipios",
        "fetcher_name": "API REST",
        "publisher_acronimo": "INE",
        "target_table": "ine_population",
        "schedule": "0 2 1 1 *",
        "params": {
            "url":         "https://servicios.ine.es/wstempus/js/ES/DATOS_TABLA/2852",
            "method":      "get",
            "timeout":     "60",
            "max_retries": "3",
        },
    },
    {
        "name": "Catalogos del INE",
        "fetcher_name": "API REST",
        "publisher_acronimo": "INE",
        "target_table": "",
        "schedule": None,
        "params": {
            "url": "https://datos.gob.es/apidata/catalog/dataset.json",
        },
    },

    # ── SEPE / Hacienda ───────────────────────────────────────────────────────
    {
        "name": "SEPE - Paro Registrado por Municipio",
        "fetcher_name": "File Download",
        "publisher_acronimo": "SEPE",
        "target_table": "sepe_paro_municipal",
        "schedule": "0 7 10 1 *",
        "params": {
            "url":       {"value": "https://sede.sepe.gob.es/es/portaltrabaja/resources/sede/datos_abiertos/datos/Paro_por_municipios_2025_csv.csv", "is_external": True},
            "format":    "csv",
            "encoding":  "latin-1",
            "delimiter": ";",
            "timeout":   "120",
            "headers":   '{"User-Agent": "Mozilla/5.0 (OpenDataManager/1.0)"}',
        },
    },
    {
        "name": "Hacienda - Periodo Medio de Pago (Entidades Locales)",
        "fetcher_name": "File Download",
        "publisher_acronimo": "MINHAC-EL",
        "target_table": "hacienda_pmp_el",
        "schedule": "0 7 20 * *",
        "params": {
            "url":       {"value": "https://serviciostelematicosext.hacienda.gob.es/SGFAL/CONPREL/pmp/PMPEL_202503.csv", "is_external": True},
            "format":    "csv",
            "encoding":  "utf-8-sig",
            "delimiter": ";",
            "timeout":   "60",
        },
    },
    {
        "name": "Hacienda - Deuda Viva de los Ayuntamientos",
        "fetcher_name": "File Download",
        "publisher_acronimo": "MINHAC-EL",
        "target_table": "hacienda_deuda_viva_el",
        "schedule": "0 5 1 7 *",
        "params": {
            "url":     {"value": "https://www.hacienda.gob.es/CDI/Sist%20Financiacion%20y%20Deuda/InformacionEELLs/2023/Deuda-viva-ayuntamientos-202312.xlsx", "is_external": True},
            "format":  "xlsx",
            "timeout": "120",
            "headers": '{"User-Agent": "Mozilla/5.0 (OpenDataManager/1.0)"}',
        },
    },

    # ── Junta de Andalucía ────────────────────────────────────────────────────
    {
        "name": "Bienes Inmuebles - Junta de Andalucía",
        "fetcher_name": "Feeds ATOM/RSS",
        "publisher_acronimo": "JDA",
        "target_table": "",
        "schedule": None,
        "params": {
            "base_url":      "https://www.juntadeandalucia.es/ssdigitales/datasets/contentapi/1.0.0/search/",
            "dataset_id":    "jda_buscador_bienes_inmuebles.atom",
            "format":        "atom",
            "page_size":     "50",
            "start_index":   "0",
            "max_pages":     "1",
            "sort":          "date:desc",
            "source_filter": "data",
            "verify_ssl":    "true",
            "timeout":       "30",
        },
    },

    # ── Justicia ──────────────────────────────────────────────────────────────
    {
        "name": "Fundaciones - Registro de Fundaciones",
        "fetcher_name": "HTML Paginated",
        "publisher_acronimo": "MJUST",
        "target_table": "fundaciones",
        "active": False,
        "schedule": None,
        "params": {
            "url":           "https://www.mjusticia.gob.es/es/RegistroMercantil/RegistroFundaciones/",
            "rows_selector": "table tr",
            "timeout":       "60",
        },
    },
    {
        "name": "Contrataciones del Estado - Licitaciones por Provincia",
        "fetcher_name": "HTML SearchLoop",
        "publisher_acronimo": "MINHAC",
        "target_table": "contrataciones_estado",
        "active": False,
        "schedule": None,
        "params": {
            "url":                    "https://contrataciondelestado.es/wps/portal/plataforma",
            "search_field_name":      "provincia",
            "rows_selector":          "table tr",
            "delay_between_searches": "2",
            "timeout":                "60",
        },
    },
    {
        "name": "Datos.gob.es - Catálogo",
        "fetcher_name": "HTML Forms",
        "publisher_acronimo": "MINHAC",
        "target_table": "datosgob_catalog",
        "schedule": None,
        "params": {
            "url":     "https://datos.gob.es/apidata/catalog/dataset",
            "method":  "GET",
            "timeout": "45",
        },
    },

    # ── Fiscalía ──────────────────────────────────────────────────────────────
    {
        "name": "Fiscalías - Directorio por Comunidad Autónoma",
        "fetcher_name": "HTML SearchLoop",
        "publisher_acronimo": "FGE",
        "target_table": "fiscalias",
        "schedule": "0 3 1 1 *",
        "params": {
            "url_template":           "https://www.fiscal.es/{value}",
            "search_field_name":      "comunidad",
            "search_field_values":    ",".join([
                "andalucia", "aragon", "asturias", "baleares", "canarias",
                "cantabria", "castilla-la-mancha", "castilla-y-leon", "cataluna",
                "comunidad-valenciana", "extremadura", "galicia", "la-rioja",
                "madrid", "murcia", "navarra", "pais-vasco",
            ]),
            "field_selectors": json.dumps({
                "fiscal_superior":      ".mj-aside__list li:nth-child(1) p.mb-10",
                "teniente_fiscal":      ".mj-aside__list li:nth-child(2) p.mb-10",
                "ultima_actualizacion": ".mj-fiscalias__update-block p",
            }),
            "field_attr_selectors": json.dumps({
                "email":    {"selector": ".mj-contactInfo a.mj-link[href^='mailto:']", "attr": "href"},
                "telefono": {"selector": ".mj-contactInfo a[href^='tel:']",            "attr": "href"},
            }),
            "field_all_selectors": json.dumps({
                "telefonos":  ".mj-contactInfo a[href^='tel:']",
                "provincias": ".mj-fiscalias__list li.mj-fiscalias__list--item p.mj-box__default--text",
            }),
            "field_label_selectors": json.dumps({
                "direccion": {"container": ".mj-contactInfo", "label": "Dirección"},
            }),
            "field_all_separator":    " | ",
            "delay_between_searches": "1.5",
            "timeout":                "30",
        },
    },

    # ── Jerez — datos presupuestarios (PDFs) ──────────────────────────────────
    {
        "name": "Jerez - PMP Mensual (Ley 15/2010)",
        "fetcher_name": "PDF_TABLE",
        "publisher_acronimo": "AJFRA",
        "target_table": "jerez_pmp_mensual",
        "schedule": "0 3 10 * *",
        "params": {
            "url_template": f"{_BASE_JEREZ}/c-deuda/{{year}}/pmp/Informe_PMP_{{year}}_{{month}}.pdf",
            "granularity":  "monthly",
            "year_from":    "2020",
            "year_to":      {"value": "2025", "is_external": True},
            "table_index":  "0",
            "header_row":   "0",
        },
    },
    {
        "name": "Jerez - Morosidad Trimestral (Ley 15/2010)",
        "fetcher_name": "PDF_TABLE",
        "publisher_acronimo": "AJFRA",
        "target_table": "jerez_morosidad_trimestral",
        "schedule": "0 3 15 1,4,7,10 *",
        "params": {
            "url_template": f"{_BASE_JEREZ}/c-deuda/{{year}}/morosidad/Informe_Ta_Ley_15_10-{{year}}-{{quarter}}oT.pdf",
            "granularity":  "quarterly",
            "year_from":    "2020",
            "year_to":      {"value": "2025", "is_external": True},
            "table_index":  "0",
            "header_row":   "0",
        },
    },
    {
        "name": "Jerez - Deuda Financiera Anual",
        "fetcher_name": "PDF_TABLE",
        "publisher_acronimo": "AJFRA",
        "target_table": "jerez_deuda_financiera",
        "schedule": "0 3 1 7 *",
        "params": {
            "url_template": f"{_BASE_JEREZ}/c-deuda/{{year}}/deuda/DEUDA_FINANCIERA_31-12-{{year}}.pdf",
            "granularity":  "annual",
            "year_from":    "2020",
            "year_to":      {"value": "2024", "is_external": True},
            "table_index":  "0",
            "header_row":   "0",
        },
    },
    {
        "name": "Jerez - Coste Efectivo de Servicios (CESEL)",
        "fetcher_name": "PDF_TABLE",
        "publisher_acronimo": "AJFRA",
        "target_table": "jerez_cesel",
        "schedule": "0 3 1 7 *",
        "params": {
            "url_template": f"{_BASE_JEREZ}/e-otrainfo/costeservicios/CESEL-{{year}}.xlsx",
            "granularity":  "annual",
            "year_from":    "2015",
            "year_to":      {"value": "2021", "is_external": True},
        },
    },

    # ── Jerez — Portal transparencia económica (XLSX/XLS/CSV) ─────────────────
    {
        "name": "jerez_transparencia_economica_xlsx",
        "fetcher_name": "Portal Documental",
        "publisher_acronimo": "AJFRA",
        "target_table": "jerez_transparencia_docs",
        "active": True,
        "schedule": None,
        "params": {
            "start_url":              "https://transparencia.jerez.es/infopublica/economica",
            "max_depth":              "2",
            "same_domain_only":       "true",
            "page_include_patterns":  '["transparencia.jerez.es/infopublica/economica"]',
            "page_exclude_patterns":  '["buscador", "novedades", "interes", "dchoinformacion", "#", "mailto:"]',
            "allowed_extensions":     '["xlsx", "xls", "csv"]',
            "navigation_link_selector": "a[href]",
            "file_link_selector":     "a[href]",
            "page_context_selectors": '{"seccion": ".breadcrumb li:nth-last-child(3)", "subseccion": ".breadcrumb li:nth-last-child(2)"}',
            "page_delay":             "1.0",
            "file_delay":             "2.0",
            "timeout":                "90",
            "batch_size":             "1000",
            "common_parser_options":  '{"header_row": 0, "skip_rows": 0}',
        },
    },
]


# ── GraphQL fragments ─────────────────────────────────────────────────────────

_QUERY_FETCHERS = """
query {
  fetchers {
    id
    name
  }
}
"""

_QUERY_PUBLISHERS = """
query {
  publishers {
    id
    acronimo
    nombre
  }
}
"""

_QUERY_RESOURCES = """
query {
  resources {
    id
    name
  }
}
"""

_CREATE_PUBLISHER = """
mutation($input: CreatePublisherInput!) {
  createPublisher(input: $input) {
    id
    acronimo
    nombre
  }
}
"""

_UPDATE_PUBLISHER = """
mutation($id: String!, $input: UpdatePublisherInput!) {
  updatePublisher(id: $id, input: $input) {
    id
    acronimo
  }
}
"""

_CREATE_RESOURCE = """
mutation($input: CreateResourceInput!) {
  createResource(input: $input) {
    id
    name
    targetTable
  }
}
"""

_UPDATE_RESOURCE = """
mutation($id: String!, $input: UpdateResourceInput!) {
  updateResource(id: $id, input: $input) {
    id
    name
  }
}
"""


# ── Helpers ───────────────────────────────────────────────────────────────────

def _execute(query: str, variables: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    result = schema.execute_sync(query, variable_values=variables)
    if result.errors:
        messages = "; ".join(str(err) for err in result.errors)
        raise RuntimeError(messages)
    return result.data or {}


def _publisher_input(spec: Dict[str, Any]) -> Dict[str, Any]:
    inp: Dict[str, Any] = {
        "nombre": spec["nombre"],
        "nivel":  spec["nivel"],
        "pais":   spec.get("pais", "España"),
    }
    if spec.get("acronimo"):
        inp["acronimo"] = spec["acronimo"]
    if spec.get("comunidad_autonoma"):
        inp["comunidadAutonoma"] = spec["comunidad_autonoma"]
    if spec.get("provincia"):
        inp["provincia"] = spec["provincia"]
    if spec.get("municipio"):
        inp["municipio"] = spec["municipio"]
    if spec.get("portal_url"):
        inp["portalUrl"] = spec["portal_url"]
    return inp


def _build_params(raw: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Translate a params dict (possibly with is_external dicts) to ResourceParamInput list."""
    result = []
    for key, spec in raw.items():
        if isinstance(spec, dict) and "value" in spec:
            result.append({"key": key, "value": str(spec["value"]), "isExternal": bool(spec.get("is_external", False))})
        else:
            result.append({"key": key, "value": str(spec), "isExternal": False})
    return result


# ── Main seeding logic ────────────────────────────────────────────────────────

def seed() -> None:
    # Resolve fetcher name → id
    fetchers_by_name = {f["name"]: f["id"] for f in _execute(_QUERY_FETCHERS)["fetchers"]}

    # ── Publishers ───────────────────────────────────────────────────────────
    existing_pubs = {
        (p.get("acronimo") or ""): p
        for p in _execute(_QUERY_PUBLISHERS)["publishers"]
    }

    for spec in PUBLISHERS:
        acronimo = spec.get("acronimo") or ""
        current = existing_pubs.get(acronimo)
        inp = _publisher_input(spec)

        if current is None:
            _execute(_CREATE_PUBLISHER, {"input": inp})
            print(f"[seed_resources] publisher creado: {spec['nombre']}")
        else:
            _execute(_UPDATE_PUBLISHER, {"id": current["id"], "input": inp})
            print(f"[seed_resources] publisher actualizado: {spec['nombre']}")

    # Re-fetch publisher IDs after upsert
    publishers_by_acronimo = {
        (p.get("acronimo") or ""): p["id"]
        for p in _execute(_QUERY_PUBLISHERS)["publishers"]
    }

    # ── Resources ────────────────────────────────────────────────────────────
    existing_res = {r["name"]: r for r in _execute(_QUERY_RESOURCES)["resources"]}

    for spec in RESOURCES:
        fetcher_name = spec["fetcher_name"]
        fetcher_id = fetchers_by_name.get(fetcher_name)
        if fetcher_id is None:
            print(f"[seed_resources] WARNING: fetcher '{fetcher_name}' no encontrado — omitiendo '{spec['name']}'")
            continue

        publisher_acronimo = spec.get("publisher_acronimo") or ""
        publisher_id = publishers_by_acronimo.get(publisher_acronimo)

        params_list = _build_params(spec.get("params", {}))

        current = existing_res.get(spec["name"])
        if current is None:
            inp: Dict[str, Any] = {
                "name":        spec["name"],
                "fetcherId":   fetcher_id,
                "active":      spec.get("active", True),
                "params":      params_list,
            }
            if spec.get("description"):
                inp["description"] = spec["description"]
            if spec.get("target_table") is not None:
                inp["targetTable"] = spec["target_table"]
            if spec.get("schedule"):
                inp["schedule"] = spec["schedule"]
            if publisher_id:
                inp["publisherId"] = publisher_id
            _execute(_CREATE_RESOURCE, {"input": inp})
            print(f"[seed_resources] resource creado: {spec['name']}")
        else:
            inp = {
                "fetcherId":   fetcher_id,
                "active":      spec.get("active", True),
                "params":      params_list,
            }
            if spec.get("target_table") is not None:
                inp["targetTable"] = spec["target_table"]
            if spec.get("schedule") is not None:
                inp["schedule"] = spec["schedule"]
            if publisher_id:
                inp["publisherId"] = publisher_id
            _execute(_UPDATE_RESOURCE, {"id": current["id"], "input": inp})
            print(f"[seed_resources] resource actualizado: {spec['name']}")

    print(f"[seed_resources] catálogo sincronizado: {len(PUBLISHERS)} publishers, {len(RESOURCES)} resources")


if __name__ == "__main__":
    try:
        seed()
    except Exception as exc:
        print(f"[seed_resources] ERROR: {exc}", file=sys.stderr)
        sys.exit(1)
