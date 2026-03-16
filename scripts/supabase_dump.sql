--
-- PostgreSQL database dump
--

\restrict NcBSyFLimUv4R4mwT0d9xYQKgi1lBfw002XAIPmFeWE8UI1E1GG769v6tWNqBI7

-- Dumped from database version 17.6
-- Dumped by pg_dump version 18.1 (Ubuntu 18.1-1.pgdg25.10+2)

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET transaction_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

--
-- Name: opendata; Type: SCHEMA; Schema: -; Owner: -
--

CREATE SCHEMA opendata;


SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- Name: alembic_version; Type: TABLE; Schema: opendata; Owner: -
--

CREATE TABLE opendata.alembic_version (
    version_num character varying(32) NOT NULL
);


--
-- Name: application; Type: TABLE; Schema: opendata; Owner: -
--

CREATE TABLE opendata.application (
    id uuid NOT NULL,
    name character varying(100) NOT NULL,
    description text,
    models_path character varying(255) NOT NULL,
    subscribed_resources jsonb NOT NULL,
    active boolean,
    webhook_url character varying(500),
    webhook_secret character varying(100)
);


--
-- Name: application_notification; Type: TABLE; Schema: opendata; Owner: -
--

CREATE TABLE opendata.application_notification (
    id uuid NOT NULL,
    application_id uuid NOT NULL,
    dataset_id uuid,
    sent_at timestamp without time zone,
    status_code integer,
    response_body text,
    error_message text
);


--
-- Name: dataset; Type: TABLE; Schema: opendata; Owner: -
--

CREATE TABLE opendata.dataset (
    id uuid NOT NULL,
    resource_id uuid NOT NULL,
    execution_id uuid,
    major_version integer NOT NULL,
    minor_version integer NOT NULL,
    patch_version integer NOT NULL,
    schema_json jsonb NOT NULL,
    data_path character varying(500) NOT NULL,
    record_count integer,
    checksum character varying(64),
    created_at timestamp without time zone
);


--
-- Name: dataset_subscription; Type: TABLE; Schema: opendata; Owner: -
--

CREATE TABLE opendata.dataset_subscription (
    id uuid NOT NULL,
    application_id uuid NOT NULL,
    resource_id uuid NOT NULL,
    pinned_version character varying(20),
    auto_upgrade character varying(20),
    current_version character varying(20),
    notified_at timestamp without time zone
);


--
-- Name: fetcher; Type: TABLE; Schema: opendata; Owner: -
--

CREATE TABLE opendata.fetcher (
    id uuid NOT NULL,
    name character varying(50) NOT NULL,
    description text,
    class_path character varying(255)
);


--
-- Name: field_metadata; Type: TABLE; Schema: opendata; Owner: -
--

CREATE TABLE opendata.field_metadata (
    id uuid NOT NULL,
    table_name character varying(100) NOT NULL,
    field_name character varying(100) NOT NULL,
    label character varying(255),
    help_text text,
    placeholder character varying(255)
);


--
-- Name: resource; Type: TABLE; Schema: opendata; Owner: -
--

CREATE TABLE opendata.resource (
    id uuid NOT NULL,
    name character varying(100) NOT NULL,
    publisher character varying(50) NOT NULL,
    fetcher_id uuid NOT NULL,
    active boolean,
    description text,
    target_table character varying(100),
    enable_load boolean,
    load_mode character varying(20),
    max_workers integer DEFAULT 1 NOT NULL,
    timeout_seconds integer DEFAULT 300 NOT NULL,
    retry_attempts integer DEFAULT 0 NOT NULL,
    retry_delay_seconds integer DEFAULT 60 NOT NULL,
    execution_priority integer DEFAULT 0 NOT NULL
);


--
-- Name: resource_execution; Type: TABLE; Schema: opendata; Owner: -
--

CREATE TABLE opendata.resource_execution (
    id uuid NOT NULL,
    resource_id uuid NOT NULL,
    started_at timestamp without time zone,
    completed_at timestamp without time zone,
    status character varying(20),
    total_records integer,
    records_loaded integer,
    staging_path character varying(500),
    error_message text
);


--
-- Name: resource_param; Type: TABLE; Schema: opendata; Owner: -
--

CREATE TABLE opendata.resource_param (
    id uuid NOT NULL,
    resource_id uuid NOT NULL,
    key character varying(100) NOT NULL,
    value text NOT NULL
);


--
-- Name: type_fetcher_params; Type: TABLE; Schema: opendata; Owner: -
--

CREATE TABLE opendata.type_fetcher_params (
    id uuid NOT NULL,
    fetcher_id uuid NOT NULL,
    param_name character varying(100) NOT NULL,
    required boolean,
    data_type character varying(20),
    default_value jsonb,
    enum_values jsonb,
    description text
);


--
-- Data for Name: alembic_version; Type: TABLE DATA; Schema: opendata; Owner: -
--

COPY opendata.alembic_version (version_num) FROM stdin;
add_cascade_deletes
\.


--
-- Data for Name: application; Type: TABLE DATA; Schema: opendata; Owner: -
--

COPY opendata.application (id, name, description, models_path, subscribed_resources, active, webhook_url, webhook_secret) FROM stdin;
fb1b5be1-cecc-4585-99a5-15033690e6c6	Portal de Transparencia	Portal público de transparencia del gobierno	/apps/transparency/models/	["dir3_units", "dir3_offices", "bdns_grants"]	t	https://transparency.gob.es/webhook/odm	secret_transparency_2024
2f070ef5-a893-40bc-beb5-07d951bdf81c	Sistema de Gestión de Subvenciones	Aplicación interna para gestión de subvenciones	/apps/grants/models/	["bdns_grants", "dir3_units"]	t	https://grants-internal.gob.es/api/odm-webhook	secret_grants_mgmt_2024
1edeb02d-b90f-49d6-aa96-5ee404ed78dd	Dashboard Analítico	Dashboard de análisis de datos públicos	/apps/analytics/models/	["ine_population", "bdns_grants"]	t	https://analytics-dashboard.gob.es/webhooks/data-update	secret_analytics_2024
050a0ab5-d083-4e6f-b92f-c7f18df28f90	App Móvil Ciudadana	Aplicación móvil para ciudadanos (en desarrollo)	/apps/mobile/models/	["dir3_offices"]	f	https://mobile-api.gob.es/odm/notify	secret_mobile_dev_2024
\.


--
-- Data for Name: application_notification; Type: TABLE DATA; Schema: opendata; Owner: -
--

COPY opendata.application_notification (id, application_id, dataset_id, sent_at, status_code, response_body, error_message) FROM stdin;
\.


--
-- Data for Name: dataset; Type: TABLE DATA; Schema: opendata; Owner: -
--

COPY opendata.dataset (id, resource_id, execution_id, major_version, minor_version, patch_version, schema_json, data_path, record_count, checksum, created_at) FROM stdin;
e280beca-f5d0-4f32-bef6-22bc9b97e608	f3796775-a248-4919-a67d-ebffc42dd6d0	d1fa23c9-5ae2-41fc-800f-cd3c16ba43af	1	0	0	{"type": "object", "required": ["FK_Unidad", "Nombre", "COD", "FK_Escala", "Data"], "properties": {"COD": {"type": "string"}, "Data": {"type": "array", "items": {"type": "object", "properties": {"Anyo": {"type": "integer"}, "Fecha": {"type": "integer"}, "Valor": {"type": "number"}, "Secreto": {"type": "boolean"}, "FK_Periodo": {"type": "integer"}, "FK_TipoDato": {"type": "integer"}}}}, "Nombre": {"type": "string"}, "FK_Escala": {"type": "integer"}, "FK_Unidad": {"type": "integer"}}}	data/artifacts/f3796775-a248-4919-a67d-ebffc42dd6d0/e280beca-f5d0-4f32-bef6-22bc9b97e608/data.jsonl	159	14fd79c14f5f7ef6dd8b80a2ed9d6b1ff4b1c796bbee5b29d9592b4b1c766876	2026-01-10 22:56:15.969928
37b00000-b6d9-4f0a-97dd-e86e82ec3cc6	a3ba818c-6eb4-4bf1-9c3f-5f69c8f6104f	87d3af2f-cd2d-420c-832a-8f4811267e22	1	0	0	{"type": "object", "required": ["advertencia", "totalPages", "sort", "content", "last", "first", "size", "pageable", "number", "empty", "totalElements", "numberOfElements"], "properties": {"last": {"type": "boolean"}, "size": {"type": "integer"}, "sort": {"type": "object", "properties": {"empty": {"type": "boolean"}, "sorted": {"type": "boolean"}, "unsorted": {"type": "boolean"}}}, "empty": {"type": "boolean"}, "first": {"type": "boolean"}, "number": {"type": "integer"}, "content": {"type": "array", "items": {"type": "object", "properties": {"id": {"type": "integer"}, "mrr": {"type": "boolean"}, "nivel1": {"type": "string"}, "nivel2": {"type": "string"}, "nivel3": {"type": "string"}, "descripcion": {"type": "string"}, "codigoInvente": {"type": "string"}, "fechaRecepcion": {"type": "string"}, "descripcionLeng": {"type": "string"}, "numeroConvocatoria": {"type": "string"}}}}, "pageable": {"type": "object", "properties": {"sort": {"type": "object", "properties": {"empty": {"type": "boolean"}, "sorted": {"type": "boolean"}, "unsorted": {"type": "boolean"}}}, "paged": {"type": "boolean"}, "offset": {"type": "integer"}, "unpaged": {"type": "boolean"}, "pageSize": {"type": "integer"}, "pageNumber": {"type": "integer"}}}, "totalPages": {"type": "integer"}, "advertencia": {"type": "string"}, "totalElements": {"type": "integer"}, "numberOfElements": {"type": "integer"}}}	data/artifacts/a3ba818c-6eb4-4bf1-9c3f-5f69c8f6104f/37b00000-b6d9-4f0a-97dd-e86e82ec3cc6/data.jsonl	1	ce8ac80e8ebe8f7ecd7ee7e7340c267b21e4eca97b8142e39d9071ffc91df6b4	2026-01-10 19:35:36.717246
ba3ab87b-6666-4110-ac4e-59d06f806170	a3ba818c-6eb4-4bf1-9c3f-5f69c8f6104f	18a71f01-d93a-4a53-80c3-de83a5231f42	1	0	1	{"type": "object", "required": ["empty", "size", "sort", "numberOfElements", "number", "totalPages", "first", "advertencia", "content", "totalElements", "pageable", "last"], "properties": {"last": {"type": "boolean"}, "size": {"type": "integer"}, "sort": {"type": "object", "properties": {"empty": {"type": "boolean"}, "sorted": {"type": "boolean"}, "unsorted": {"type": "boolean"}}}, "empty": {"type": "boolean"}, "first": {"type": "boolean"}, "number": {"type": "integer"}, "content": {"type": "array", "items": {"type": "object", "properties": {"id": {"type": "integer"}, "mrr": {"type": "boolean"}, "nivel1": {"type": "string"}, "nivel2": {"type": "string"}, "nivel3": {"type": "string"}, "descripcion": {"type": "string"}, "codigoInvente": {"type": "string"}, "fechaRecepcion": {"type": "string"}, "descripcionLeng": {"type": "string"}, "numeroConvocatoria": {"type": "string"}}}}, "pageable": {"type": "object", "properties": {"sort": {"type": "object", "properties": {"empty": {"type": "boolean"}, "sorted": {"type": "boolean"}, "unsorted": {"type": "boolean"}}}, "paged": {"type": "boolean"}, "offset": {"type": "integer"}, "unpaged": {"type": "boolean"}, "pageSize": {"type": "integer"}, "pageNumber": {"type": "integer"}}}, "totalPages": {"type": "integer"}, "advertencia": {"type": "string"}, "totalElements": {"type": "integer"}, "numberOfElements": {"type": "integer"}}}	data/artifacts/a3ba818c-6eb4-4bf1-9c3f-5f69c8f6104f/ba3ab87b-6666-4110-ac4e-59d06f806170/data.jsonl	1	ce8ac80e8ebe8f7ecd7ee7e7340c267b21e4eca97b8142e39d9071ffc91df6b4	2026-01-10 21:52:12.886123
040cbbc9-b4cc-4d75-a83b-b31e50fae6ce	a3ba818c-6eb4-4bf1-9c3f-5f69c8f6104f	8496db57-89bb-455a-b947-3eee59850728	1	0	2	{"type": "object", "required": ["advertencia", "totalElements", "empty", "content", "size", "number", "numberOfElements", "pageable", "sort", "totalPages", "first", "last"], "properties": {"last": {"type": "boolean"}, "size": {"type": "integer"}, "sort": {"type": "object", "properties": {"empty": {"type": "boolean"}, "sorted": {"type": "boolean"}, "unsorted": {"type": "boolean"}}}, "empty": {"type": "boolean"}, "first": {"type": "boolean"}, "number": {"type": "integer"}, "content": {"type": "array", "items": {"type": "object", "properties": {"id": {"type": "integer"}, "mrr": {"type": "boolean"}, "nivel1": {"type": "string"}, "nivel2": {"type": "string"}, "nivel3": {"type": "string"}, "descripcion": {"type": "string"}, "codigoInvente": {"type": "string"}, "fechaRecepcion": {"type": "string"}, "descripcionLeng": {"type": "string"}, "numeroConvocatoria": {"type": "string"}}}}, "pageable": {"type": "object", "properties": {"sort": {"type": "object", "properties": {"empty": {"type": "boolean"}, "sorted": {"type": "boolean"}, "unsorted": {"type": "boolean"}}}, "paged": {"type": "boolean"}, "offset": {"type": "integer"}, "unpaged": {"type": "boolean"}, "pageSize": {"type": "integer"}, "pageNumber": {"type": "integer"}}}, "totalPages": {"type": "integer"}, "advertencia": {"type": "string"}, "totalElements": {"type": "integer"}, "numberOfElements": {"type": "integer"}}}	data/artifacts/a3ba818c-6eb4-4bf1-9c3f-5f69c8f6104f/040cbbc9-b4cc-4d75-a83b-b31e50fae6ce/data.jsonl	1	6c02f28352b913543474c4451c4f6199210f0d86d380076f124dc86d026976f7	2026-01-10 22:02:10.913784
95f4804c-1fd5-4fdc-a8be-1755da9801a5	a3ba818c-6eb4-4bf1-9c3f-5f69c8f6104f	e8f9337e-da65-4b71-af35-ac661cbec4cf	1	0	3	{"type": "object", "required": ["pageable", "totalElements", "numberOfElements", "number", "advertencia", "content", "last", "first", "sort", "totalPages", "empty", "size"], "properties": {"last": {"type": "boolean"}, "size": {"type": "integer"}, "sort": {"type": "object", "properties": {"empty": {"type": "boolean"}, "sorted": {"type": "boolean"}, "unsorted": {"type": "boolean"}}}, "empty": {"type": "boolean"}, "first": {"type": "boolean"}, "number": {"type": "integer"}, "content": {"type": "array", "items": {"type": "object", "properties": {"id": {"type": "integer"}, "mrr": {"type": "boolean"}, "nivel1": {"type": "string"}, "nivel2": {"type": "string"}, "nivel3": {"type": "string"}, "descripcion": {"type": "string"}, "codigoInvente": {"type": "string"}, "fechaRecepcion": {"type": "string"}, "descripcionLeng": {"type": "string"}, "numeroConvocatoria": {"type": "string"}}}}, "pageable": {"type": "object", "properties": {"sort": {"type": "object", "properties": {"empty": {"type": "boolean"}, "sorted": {"type": "boolean"}, "unsorted": {"type": "boolean"}}}, "paged": {"type": "boolean"}, "offset": {"type": "integer"}, "unpaged": {"type": "boolean"}, "pageSize": {"type": "integer"}, "pageNumber": {"type": "integer"}}}, "totalPages": {"type": "integer"}, "advertencia": {"type": "string"}, "totalElements": {"type": "integer"}, "numberOfElements": {"type": "integer"}}}	data/artifacts/a3ba818c-6eb4-4bf1-9c3f-5f69c8f6104f/95f4804c-1fd5-4fdc-a8be-1755da9801a5/data.jsonl	1	ce8ac80e8ebe8f7ecd7ee7e7340c267b21e4eca97b8142e39d9071ffc91df6b4	2026-01-10 22:02:25.296559
8ca0fdb0-a050-4ae1-8200-32efd964bd29	a3ba818c-6eb4-4bf1-9c3f-5f69c8f6104f	cd83d0fc-3520-4282-a933-cee2e787bd65	1	0	4	{"type": "object", "required": ["pageable", "first", "totalElements", "sort", "last", "size", "number", "numberOfElements", "empty", "advertencia", "content", "totalPages"], "properties": {"last": {"type": "boolean"}, "size": {"type": "integer"}, "sort": {"type": "object", "properties": {"empty": {"type": "boolean"}, "sorted": {"type": "boolean"}, "unsorted": {"type": "boolean"}}}, "empty": {"type": "boolean"}, "first": {"type": "boolean"}, "number": {"type": "integer"}, "content": {"type": "array", "items": {"type": "object", "properties": {"id": {"type": "integer"}, "mrr": {"type": "boolean"}, "nivel1": {"type": "string"}, "nivel2": {"type": "string"}, "nivel3": {"type": "string"}, "descripcion": {"type": "string"}, "codigoInvente": {"type": "string"}, "fechaRecepcion": {"type": "string"}, "descripcionLeng": {"type": "string"}, "numeroConvocatoria": {"type": "string"}}}}, "pageable": {"type": "object", "properties": {"sort": {"type": "object", "properties": {"empty": {"type": "boolean"}, "sorted": {"type": "boolean"}, "unsorted": {"type": "boolean"}}}, "paged": {"type": "boolean"}, "offset": {"type": "integer"}, "unpaged": {"type": "boolean"}, "pageSize": {"type": "integer"}, "pageNumber": {"type": "integer"}}}, "totalPages": {"type": "integer"}, "advertencia": {"type": "string"}, "totalElements": {"type": "integer"}, "numberOfElements": {"type": "integer"}}}	data/artifacts/a3ba818c-6eb4-4bf1-9c3f-5f69c8f6104f/8ca0fdb0-a050-4ae1-8200-32efd964bd29/data.jsonl	1	ce8ac80e8ebe8f7ecd7ee7e7340c267b21e4eca97b8142e39d9071ffc91df6b4	2026-01-10 22:33:52.857663
9bf341df-ee20-4ee4-9d61-3d592f7b0518	a3ba818c-6eb4-4bf1-9c3f-5f69c8f6104f	d1fda079-6b31-4ff6-9a78-d04d599bac35	1	0	5	{"type": "object", "required": ["size", "totalElements", "pageable", "empty", "sort", "totalPages", "first", "numberOfElements", "last", "number", "advertencia", "content"], "properties": {"last": {"type": "boolean"}, "size": {"type": "integer"}, "sort": {"type": "object", "properties": {"empty": {"type": "boolean"}, "sorted": {"type": "boolean"}, "unsorted": {"type": "boolean"}}}, "empty": {"type": "boolean"}, "first": {"type": "boolean"}, "number": {"type": "integer"}, "content": {"type": "array", "items": {"type": "object", "properties": {"id": {"type": "integer"}, "mrr": {"type": "boolean"}, "nivel1": {"type": "string"}, "nivel2": {"type": "string"}, "nivel3": {"type": "string"}, "descripcion": {"type": "string"}, "codigoInvente": {"type": "string"}, "fechaRecepcion": {"type": "string"}, "descripcionLeng": {"type": "string"}, "numeroConvocatoria": {"type": "string"}}}}, "pageable": {"type": "object", "properties": {"sort": {"type": "object", "properties": {"empty": {"type": "boolean"}, "sorted": {"type": "boolean"}, "unsorted": {"type": "boolean"}}}, "paged": {"type": "boolean"}, "offset": {"type": "integer"}, "unpaged": {"type": "boolean"}, "pageSize": {"type": "integer"}, "pageNumber": {"type": "integer"}}}, "totalPages": {"type": "integer"}, "advertencia": {"type": "string"}, "totalElements": {"type": "integer"}, "numberOfElements": {"type": "integer"}}}	data/artifacts/a3ba818c-6eb4-4bf1-9c3f-5f69c8f6104f/9bf341df-ee20-4ee4-9d61-3d592f7b0518/data.jsonl	1	ce8ac80e8ebe8f7ecd7ee7e7340c267b21e4eca97b8142e39d9071ffc91df6b4	2026-01-10 22:34:36.293001
1e706073-e242-4944-8f8d-853269b06da9	a3ba818c-6eb4-4bf1-9c3f-5f69c8f6104f	ed178697-bc07-47cc-b40a-6a17772aa6d5	1	0	6	{"type": "object", "required": ["number", "numberOfElements", "size", "empty", "totalElements", "sort", "advertencia", "pageable", "content", "last", "first", "totalPages"], "properties": {"last": {"type": "boolean"}, "size": {"type": "integer"}, "sort": {"type": "object", "properties": {"empty": {"type": "boolean"}, "sorted": {"type": "boolean"}, "unsorted": {"type": "boolean"}}}, "empty": {"type": "boolean"}, "first": {"type": "boolean"}, "number": {"type": "integer"}, "content": {"type": "array", "items": {"type": "object", "properties": {"id": {"type": "integer"}, "mrr": {"type": "boolean"}, "nivel1": {"type": "string"}, "nivel2": {"type": "string"}, "nivel3": {"type": "string"}, "descripcion": {"type": "string"}, "codigoInvente": {"type": "string"}, "fechaRecepcion": {"type": "string"}, "descripcionLeng": {"type": "string"}, "numeroConvocatoria": {"type": "string"}}}}, "pageable": {"type": "object", "properties": {"sort": {"type": "object", "properties": {"empty": {"type": "boolean"}, "sorted": {"type": "boolean"}, "unsorted": {"type": "boolean"}}}, "paged": {"type": "boolean"}, "offset": {"type": "integer"}, "unpaged": {"type": "boolean"}, "pageSize": {"type": "integer"}, "pageNumber": {"type": "integer"}}}, "totalPages": {"type": "integer"}, "advertencia": {"type": "string"}, "totalElements": {"type": "integer"}, "numberOfElements": {"type": "integer"}}}	data/artifacts/a3ba818c-6eb4-4bf1-9c3f-5f69c8f6104f/1e706073-e242-4944-8f8d-853269b06da9/data.jsonl	1	ce8ac80e8ebe8f7ecd7ee7e7340c267b21e4eca97b8142e39d9071ffc91df6b4	2026-01-10 22:53:57.354336
32bcb871-90da-4026-b8fd-93b63191d24b	a3ba818c-6eb4-4bf1-9c3f-5f69c8f6104f	5d961117-176c-4c9a-b459-460152345e38	1	0	7	{"type": "object", "required": ["size", "advertencia", "empty", "pageable", "content", "sort", "last", "numberOfElements", "number", "totalPages", "first", "totalElements"], "properties": {"last": {"type": "boolean"}, "size": {"type": "integer"}, "sort": {"type": "object", "properties": {"empty": {"type": "boolean"}, "sorted": {"type": "boolean"}, "unsorted": {"type": "boolean"}}}, "empty": {"type": "boolean"}, "first": {"type": "boolean"}, "number": {"type": "integer"}, "content": {"type": "array", "items": {"type": "object", "properties": {"id": {"type": "integer"}, "mrr": {"type": "boolean"}, "nivel1": {"type": "string"}, "nivel2": {"type": "string"}, "nivel3": {"type": "string"}, "descripcion": {"type": "string"}, "codigoInvente": {"type": "string"}, "fechaRecepcion": {"type": "string"}, "descripcionLeng": {"type": "string"}, "numeroConvocatoria": {"type": "string"}}}}, "pageable": {"type": "object", "properties": {"sort": {"type": "object", "properties": {"empty": {"type": "boolean"}, "sorted": {"type": "boolean"}, "unsorted": {"type": "boolean"}}}, "paged": {"type": "boolean"}, "offset": {"type": "integer"}, "unpaged": {"type": "boolean"}, "pageSize": {"type": "integer"}, "pageNumber": {"type": "integer"}}}, "totalPages": {"type": "integer"}, "advertencia": {"type": "string"}, "totalElements": {"type": "integer"}, "numberOfElements": {"type": "integer"}}}	data/artifacts/a3ba818c-6eb4-4bf1-9c3f-5f69c8f6104f/32bcb871-90da-4026-b8fd-93b63191d24b/data.jsonl	1	ce8ac80e8ebe8f7ecd7ee7e7340c267b21e4eca97b8142e39d9071ffc91df6b4	2026-01-10 22:54:48.720051
2b3c75dc-1996-4c01-bbbc-2ae2fdb741ad	a3ba818c-6eb4-4bf1-9c3f-5f69c8f6104f	27533b0f-4093-4a9a-86b8-cd087f1ae371	1	0	8	{"type": "object", "required": ["totalElements", "last", "number", "advertencia", "pageable", "empty", "size", "numberOfElements", "first", "content", "sort", "totalPages"], "properties": {"last": {"type": "boolean"}, "size": {"type": "integer"}, "sort": {"type": "object", "properties": {"empty": {"type": "boolean"}, "sorted": {"type": "boolean"}, "unsorted": {"type": "boolean"}}}, "empty": {"type": "boolean"}, "first": {"type": "boolean"}, "number": {"type": "integer"}, "content": {"type": "array", "items": {"type": "object", "properties": {"id": {"type": "integer"}, "mrr": {"type": "boolean"}, "nivel1": {"type": "string"}, "nivel2": {"type": "string"}, "nivel3": {"type": "string"}, "descripcion": {"type": "string"}, "codigoInvente": {"type": "string"}, "fechaRecepcion": {"type": "string"}, "descripcionLeng": {"type": "string"}, "numeroConvocatoria": {"type": "string"}}}}, "pageable": {"type": "object", "properties": {"sort": {"type": "object", "properties": {"empty": {"type": "boolean"}, "sorted": {"type": "boolean"}, "unsorted": {"type": "boolean"}}}, "paged": {"type": "boolean"}, "offset": {"type": "integer"}, "unpaged": {"type": "boolean"}, "pageSize": {"type": "integer"}, "pageNumber": {"type": "integer"}}}, "totalPages": {"type": "integer"}, "advertencia": {"type": "string"}, "totalElements": {"type": "integer"}, "numberOfElements": {"type": "integer"}}}	data/datasets/a3ba818c-6eb4-4bf1-9c3f-5f69c8f6104f/2b3c75dc-1996-4c01-bbbc-2ae2fdb741ad/data.jsonl	1	6c02f28352b913543474c4451c4f6199210f0d86d380076f124dc86d026976f7	2026-01-10 23:21:52.146046
dca2848d-542a-4193-90ca-d26055cb814c	a3ba818c-6eb4-4bf1-9c3f-5f69c8f6104f	1701b52f-c7fc-433b-85c3-55587f4ff45a	1	0	9	{"type": "object", "required": ["number", "advertencia", "pageable", "sort", "last", "numberOfElements", "size", "empty", "totalPages", "content", "totalElements", "first"], "properties": {"last": {"type": "boolean"}, "size": {"type": "integer"}, "sort": {"type": "object", "properties": {"empty": {"type": "boolean"}, "sorted": {"type": "boolean"}, "unsorted": {"type": "boolean"}}}, "empty": {"type": "boolean"}, "first": {"type": "boolean"}, "number": {"type": "integer"}, "content": {"type": "array", "items": {"type": "object", "properties": {"id": {"type": "integer"}, "mrr": {"type": "boolean"}, "nivel1": {"type": "string"}, "nivel2": {"type": "string"}, "nivel3": {"type": "string"}, "descripcion": {"type": "string"}, "codigoInvente": {"type": "string"}, "fechaRecepcion": {"type": "string"}, "descripcionLeng": {"type": "string"}, "numeroConvocatoria": {"type": "string"}}}}, "pageable": {"type": "object", "properties": {"sort": {"type": "object", "properties": {"empty": {"type": "boolean"}, "sorted": {"type": "boolean"}, "unsorted": {"type": "boolean"}}}, "paged": {"type": "boolean"}, "offset": {"type": "integer"}, "unpaged": {"type": "boolean"}, "pageSize": {"type": "integer"}, "pageNumber": {"type": "integer"}}}, "totalPages": {"type": "integer"}, "advertencia": {"type": "string"}, "totalElements": {"type": "integer"}, "numberOfElements": {"type": "integer"}}}	data/datasets/a3ba818c-6eb4-4bf1-9c3f-5f69c8f6104f/dca2848d-542a-4193-90ca-d26055cb814c/data.jsonl	1	ce8ac80e8ebe8f7ecd7ee7e7340c267b21e4eca97b8142e39d9071ffc91df6b4	2026-01-10 23:27:40.387039
15663588-c4bf-4d12-b187-dbf2dea3be88	a3ba818c-6eb4-4bf1-9c3f-5f69c8f6104f	2579aeb9-3cec-42f4-b371-0e97892be485	1	0	10	{"type": "object", "required": ["size", "totalElements", "content", "advertencia", "pageable", "numberOfElements", "empty", "sort", "number", "first", "totalPages", "last"], "properties": {"last": {"type": "boolean"}, "size": {"type": "integer"}, "sort": {"type": "object", "properties": {"empty": {"type": "boolean"}, "sorted": {"type": "boolean"}, "unsorted": {"type": "boolean"}}}, "empty": {"type": "boolean"}, "first": {"type": "boolean"}, "number": {"type": "integer"}, "content": {"type": "array", "items": {"type": "object", "properties": {"id": {"type": "integer"}, "mrr": {"type": "boolean"}, "nivel1": {"type": "string"}, "nivel2": {"type": "string"}, "nivel3": {"type": "string"}, "descripcion": {"type": "string"}, "codigoInvente": {"type": "string"}, "fechaRecepcion": {"type": "string"}, "descripcionLeng": {"type": "string"}, "numeroConvocatoria": {"type": "string"}}}}, "pageable": {"type": "object", "properties": {"sort": {"type": "object", "properties": {"empty": {"type": "boolean"}, "sorted": {"type": "boolean"}, "unsorted": {"type": "boolean"}}}, "paged": {"type": "boolean"}, "offset": {"type": "integer"}, "unpaged": {"type": "boolean"}, "pageSize": {"type": "integer"}, "pageNumber": {"type": "integer"}}}, "totalPages": {"type": "integer"}, "advertencia": {"type": "string"}, "totalElements": {"type": "integer"}, "numberOfElements": {"type": "integer"}}}	data/datasets/a3ba818c-6eb4-4bf1-9c3f-5f69c8f6104f/15663588-c4bf-4d12-b187-dbf2dea3be88/data.jsonl	1	ce8ac80e8ebe8f7ecd7ee7e7340c267b21e4eca97b8142e39d9071ffc91df6b4	2026-01-10 23:28:03.535872
bbd9c3f1-c399-4bd7-8839-0a0159292435	a3ba818c-6eb4-4bf1-9c3f-5f69c8f6104f	b01bfe20-3faf-4da7-a727-3ed038795793	1	0	11	{"type": "object", "required": ["empty", "sort", "totalPages", "pageable", "content", "first", "size", "advertencia", "last", "numberOfElements", "totalElements", "number"], "properties": {"last": {"type": "boolean"}, "size": {"type": "integer"}, "sort": {"type": "object", "properties": {"empty": {"type": "boolean"}, "sorted": {"type": "boolean"}, "unsorted": {"type": "boolean"}}}, "empty": {"type": "boolean"}, "first": {"type": "boolean"}, "number": {"type": "integer"}, "content": {"type": "array", "items": {"type": "object", "properties": {"id": {"type": "integer"}, "mrr": {"type": "boolean"}, "nivel1": {"type": "string"}, "nivel2": {"type": "string"}, "nivel3": {"type": "string"}, "descripcion": {"type": "string"}, "codigoInvente": {"type": "string"}, "fechaRecepcion": {"type": "string"}, "descripcionLeng": {"type": "string"}, "numeroConvocatoria": {"type": "string"}}}}, "pageable": {"type": "object", "properties": {"sort": {"type": "object", "properties": {"empty": {"type": "boolean"}, "sorted": {"type": "boolean"}, "unsorted": {"type": "boolean"}}}, "paged": {"type": "boolean"}, "offset": {"type": "integer"}, "unpaged": {"type": "boolean"}, "pageSize": {"type": "integer"}, "pageNumber": {"type": "integer"}}}, "totalPages": {"type": "integer"}, "advertencia": {"type": "string"}, "totalElements": {"type": "integer"}, "numberOfElements": {"type": "integer"}}}	data/datasets/a3ba818c-6eb4-4bf1-9c3f-5f69c8f6104f/bbd9c3f1-c399-4bd7-8839-0a0159292435/data.jsonl	1	41bb0951ff5673c8154c05cabf0ae2317fb3fc75bf5a406267028fbd630d672e	2026-01-11 10:39:45.870501
d750b254-f71d-4e16-9380-4c89b83bfff9	a3ba818c-6eb4-4bf1-9c3f-5f69c8f6104f	88fd0f97-6aec-4456-98ad-27f083a08df9	1	0	12	{"type": "object", "required": ["totalPages", "advertencia", "content", "empty", "number", "numberOfElements", "pageable", "sort", "size", "first", "last", "totalElements"], "properties": {"last": {"type": "boolean"}, "size": {"type": "integer"}, "sort": {"type": "object", "properties": {"empty": {"type": "boolean"}, "sorted": {"type": "boolean"}, "unsorted": {"type": "boolean"}}}, "empty": {"type": "boolean"}, "first": {"type": "boolean"}, "number": {"type": "integer"}, "content": {"type": "array", "items": {"type": "object", "properties": {"id": {"type": "integer"}, "mrr": {"type": "boolean"}, "nivel1": {"type": "string"}, "nivel2": {"type": "string"}, "nivel3": {"type": "string"}, "descripcion": {"type": "string"}, "codigoInvente": {"type": "string"}, "fechaRecepcion": {"type": "string"}, "descripcionLeng": {"type": "string"}, "numeroConvocatoria": {"type": "string"}}}}, "pageable": {"type": "object", "properties": {"sort": {"type": "object", "properties": {"empty": {"type": "boolean"}, "sorted": {"type": "boolean"}, "unsorted": {"type": "boolean"}}}, "paged": {"type": "boolean"}, "offset": {"type": "integer"}, "unpaged": {"type": "boolean"}, "pageSize": {"type": "integer"}, "pageNumber": {"type": "integer"}}}, "totalPages": {"type": "integer"}, "advertencia": {"type": "string"}, "totalElements": {"type": "integer"}, "numberOfElements": {"type": "integer"}}}	data/datasets/a3ba818c-6eb4-4bf1-9c3f-5f69c8f6104f/d750b254-f71d-4e16-9380-4c89b83bfff9/data.jsonl	1	1bdad3ecba82915fad488b677ab927ef659257c06ff50aa4a457493313b2c292	2026-01-11 10:40:07.776475
a84f0664-8898-4ede-b7e8-6dad9af4849e	a3ba818c-6eb4-4bf1-9c3f-5f69c8f6104f	fc6a61d8-2ccb-4eba-803f-6d048195e206	1	0	13	{"type": "object", "required": ["totalPages", "numberOfElements", "first", "pageable", "sort", "advertencia", "totalElements", "last", "content", "empty", "number", "size"], "properties": {"last": {"type": "boolean"}, "size": {"type": "integer"}, "sort": {"type": "object", "properties": {"empty": {"type": "boolean"}, "sorted": {"type": "boolean"}, "unsorted": {"type": "boolean"}}}, "empty": {"type": "boolean"}, "first": {"type": "boolean"}, "number": {"type": "integer"}, "content": {"type": "array", "items": {"type": "object", "properties": {"id": {"type": "integer"}, "mrr": {"type": "boolean"}, "nivel1": {"type": "string"}, "nivel2": {"type": "string"}, "nivel3": {"type": "string"}, "descripcion": {"type": "string"}, "codigoInvente": {"type": "string"}, "fechaRecepcion": {"type": "string"}, "descripcionLeng": {"type": "string"}, "numeroConvocatoria": {"type": "string"}}}}, "pageable": {"type": "object", "properties": {"sort": {"type": "object", "properties": {"empty": {"type": "boolean"}, "sorted": {"type": "boolean"}, "unsorted": {"type": "boolean"}}}, "paged": {"type": "boolean"}, "offset": {"type": "integer"}, "unpaged": {"type": "boolean"}, "pageSize": {"type": "integer"}, "pageNumber": {"type": "integer"}}}, "totalPages": {"type": "integer"}, "advertencia": {"type": "string"}, "totalElements": {"type": "integer"}, "numberOfElements": {"type": "integer"}}}	data/datasets/a3ba818c-6eb4-4bf1-9c3f-5f69c8f6104f/a84f0664-8898-4ede-b7e8-6dad9af4849e/data.jsonl	1	41bb0951ff5673c8154c05cabf0ae2317fb3fc75bf5a406267028fbd630d672e	2026-01-11 10:48:10.75781
6d6e7722-0204-417d-9995-c303bf5d23c8	a3ba818c-6eb4-4bf1-9c3f-5f69c8f6104f	82b04bfe-7218-470b-b43f-7a53ef56c723	1	0	14	{"type": "object", "required": ["content", "number", "sort", "advertencia", "first", "last", "pageable", "size", "numberOfElements", "totalPages", "totalElements", "empty"], "properties": {"last": {"type": "boolean"}, "size": {"type": "integer"}, "sort": {"type": "object", "properties": {"empty": {"type": "boolean"}, "sorted": {"type": "boolean"}, "unsorted": {"type": "boolean"}}}, "empty": {"type": "boolean"}, "first": {"type": "boolean"}, "number": {"type": "integer"}, "content": {"type": "array", "items": {"type": "object", "properties": {"id": {"type": "integer"}, "mrr": {"type": "boolean"}, "nivel1": {"type": "string"}, "nivel2": {"type": "string"}, "nivel3": {"type": "string"}, "descripcion": {"type": "string"}, "codigoInvente": {"type": "string"}, "fechaRecepcion": {"type": "string"}, "descripcionLeng": {"type": "string"}, "numeroConvocatoria": {"type": "string"}}}}, "pageable": {"type": "object", "properties": {"sort": {"type": "object", "properties": {"empty": {"type": "boolean"}, "sorted": {"type": "boolean"}, "unsorted": {"type": "boolean"}}}, "paged": {"type": "boolean"}, "offset": {"type": "integer"}, "unpaged": {"type": "boolean"}, "pageSize": {"type": "integer"}, "pageNumber": {"type": "integer"}}}, "totalPages": {"type": "integer"}, "advertencia": {"type": "string"}, "totalElements": {"type": "integer"}, "numberOfElements": {"type": "integer"}}}	data/datasets/a3ba818c-6eb4-4bf1-9c3f-5f69c8f6104f/6d6e7722-0204-417d-9995-c303bf5d23c8/data.jsonl	1	41bb0951ff5673c8154c05cabf0ae2317fb3fc75bf5a406267028fbd630d672e	2026-01-11 10:48:57.055713
1ad4d853-15ca-4d61-b62d-860be666bf9f	a3ba818c-6eb4-4bf1-9c3f-5f69c8f6104f	6dc5d3dd-46b4-4fff-b312-cb40fa02302d	1	0	15	{"type": "object", "required": ["numberOfElements", "size", "first", "totalPages", "sort", "totalElements", "advertencia", "pageable", "number", "empty", "last", "content"], "properties": {"last": {"type": "boolean"}, "size": {"type": "integer"}, "sort": {"type": "object", "properties": {"empty": {"type": "boolean"}, "sorted": {"type": "boolean"}, "unsorted": {"type": "boolean"}}}, "empty": {"type": "boolean"}, "first": {"type": "boolean"}, "number": {"type": "integer"}, "content": {"type": "array", "items": {"type": "object", "properties": {"id": {"type": "integer"}, "mrr": {"type": "boolean"}, "nivel1": {"type": "string"}, "nivel2": {"type": "string"}, "nivel3": {"type": "string"}, "descripcion": {"type": "string"}, "codigoInvente": {"type": "string"}, "fechaRecepcion": {"type": "string"}, "descripcionLeng": {"type": "string"}, "numeroConvocatoria": {"type": "string"}}}}, "pageable": {"type": "object", "properties": {"sort": {"type": "object", "properties": {"empty": {"type": "boolean"}, "sorted": {"type": "boolean"}, "unsorted": {"type": "boolean"}}}, "paged": {"type": "boolean"}, "offset": {"type": "integer"}, "unpaged": {"type": "boolean"}, "pageSize": {"type": "integer"}, "pageNumber": {"type": "integer"}}}, "totalPages": {"type": "integer"}, "advertencia": {"type": "string"}, "totalElements": {"type": "integer"}, "numberOfElements": {"type": "integer"}}}	data/datasets/a3ba818c-6eb4-4bf1-9c3f-5f69c8f6104f/1ad4d853-15ca-4d61-b62d-860be666bf9f/data.jsonl	1	044dafb6c72167f143b251efe625bce71e1c5822ad63e00ee51570ee36981913	2026-01-11 18:53:35.287476
227528b9-8a34-48e8-baae-c41c6e22f02a	a3ba818c-6eb4-4bf1-9c3f-5f69c8f6104f	dd2dbec3-d4da-4c9b-ab10-54ce27e95e17	1	0	16	{"type": "object", "required": ["first", "totalElements", "advertencia", "number", "pageable", "content", "size", "empty", "sort", "totalPages", "numberOfElements", "last"], "properties": {"last": {"type": "boolean"}, "size": {"type": "integer"}, "sort": {"type": "object", "properties": {"empty": {"type": "boolean"}, "sorted": {"type": "boolean"}, "unsorted": {"type": "boolean"}}}, "empty": {"type": "boolean"}, "first": {"type": "boolean"}, "number": {"type": "integer"}, "content": {"type": "array", "items": {"type": "object", "properties": {"id": {"type": "integer"}, "mrr": {"type": "boolean"}, "nivel1": {"type": "string"}, "nivel2": {"type": "string"}, "nivel3": {"type": "string"}, "descripcion": {"type": "string"}, "codigoInvente": {"type": "string"}, "fechaRecepcion": {"type": "string"}, "descripcionLeng": {"type": "string"}, "numeroConvocatoria": {"type": "string"}}}}, "pageable": {"type": "object", "properties": {"sort": {"type": "object", "properties": {"empty": {"type": "boolean"}, "sorted": {"type": "boolean"}, "unsorted": {"type": "boolean"}}}, "paged": {"type": "boolean"}, "offset": {"type": "integer"}, "unpaged": {"type": "boolean"}, "pageSize": {"type": "integer"}, "pageNumber": {"type": "integer"}}}, "totalPages": {"type": "integer"}, "advertencia": {"type": "string"}, "totalElements": {"type": "integer"}, "numberOfElements": {"type": "integer"}}}	data/datasets/a3ba818c-6eb4-4bf1-9c3f-5f69c8f6104f/227528b9-8a34-48e8-baae-c41c6e22f02a/data.jsonl	1	b3fa75bff2e7f7d20f70891fb544f7447eaa871ded3e99f7a9631f59bbcff748	2026-01-11 18:54:04.316992
7327829a-8318-4a08-99aa-167c76171165	a3ba818c-6eb4-4bf1-9c3f-5f69c8f6104f	450e6291-219a-40b2-887b-8405cbc4d065	1	0	17	{"type": "object", "required": ["size", "totalPages", "content", "first", "sort", "totalElements", "last", "empty", "advertencia", "pageable", "number", "numberOfElements"], "properties": {"last": {"type": "boolean"}, "size": {"type": "integer"}, "sort": {"type": "object", "properties": {"empty": {"type": "boolean"}, "sorted": {"type": "boolean"}, "unsorted": {"type": "boolean"}}}, "empty": {"type": "boolean"}, "first": {"type": "boolean"}, "number": {"type": "integer"}, "content": {"type": "array", "items": {"type": "object", "properties": {"id": {"type": "integer"}, "mrr": {"type": "boolean"}, "nivel1": {"type": "string"}, "nivel2": {"type": "string"}, "nivel3": {"type": "string"}, "descripcion": {"type": "string"}, "codigoInvente": {"type": "string"}, "fechaRecepcion": {"type": "string"}, "descripcionLeng": {"type": "string"}, "numeroConvocatoria": {"type": "string"}}}}, "pageable": {"type": "object", "properties": {"sort": {"type": "object", "properties": {"empty": {"type": "boolean"}, "sorted": {"type": "boolean"}, "unsorted": {"type": "boolean"}}}, "paged": {"type": "boolean"}, "offset": {"type": "integer"}, "unpaged": {"type": "boolean"}, "pageSize": {"type": "integer"}, "pageNumber": {"type": "integer"}}}, "totalPages": {"type": "integer"}, "advertencia": {"type": "string"}, "totalElements": {"type": "integer"}, "numberOfElements": {"type": "integer"}}}	data/datasets/a3ba818c-6eb4-4bf1-9c3f-5f69c8f6104f/7327829a-8318-4a08-99aa-167c76171165/data.jsonl	1	b3fa75bff2e7f7d20f70891fb544f7447eaa871ded3e99f7a9631f59bbcff748	2026-01-11 18:54:23.696984
759fca73-22f5-4e3d-8e1c-ee8024c13159	a3ba818c-6eb4-4bf1-9c3f-5f69c8f6104f	104688e4-5c2c-4864-9064-1a1af5a0c081	1	0	18	{"type": "object", "required": ["numberOfElements", "number", "totalPages", "first", "empty", "content", "advertencia", "totalElements", "size", "sort", "pageable", "last"], "properties": {"last": {"type": "boolean"}, "size": {"type": "integer"}, "sort": {"type": "object", "properties": {"empty": {"type": "boolean"}, "sorted": {"type": "boolean"}, "unsorted": {"type": "boolean"}}}, "empty": {"type": "boolean"}, "first": {"type": "boolean"}, "number": {"type": "integer"}, "content": {"type": "array", "items": {"type": "object", "properties": {"id": {"type": "integer"}, "mrr": {"type": "boolean"}, "nivel1": {"type": "string"}, "nivel2": {"type": "string"}, "nivel3": {"type": "string"}, "descripcion": {"type": "string"}, "codigoInvente": {"type": "string"}, "fechaRecepcion": {"type": "string"}, "descripcionLeng": {"type": "string"}, "numeroConvocatoria": {"type": "string"}}}}, "pageable": {"type": "object", "properties": {"sort": {"type": "object", "properties": {"empty": {"type": "boolean"}, "sorted": {"type": "boolean"}, "unsorted": {"type": "boolean"}}}, "paged": {"type": "boolean"}, "offset": {"type": "integer"}, "unpaged": {"type": "boolean"}, "pageSize": {"type": "integer"}, "pageNumber": {"type": "integer"}}}, "totalPages": {"type": "integer"}, "advertencia": {"type": "string"}, "totalElements": {"type": "integer"}, "numberOfElements": {"type": "integer"}}}	data/datasets/a3ba818c-6eb4-4bf1-9c3f-5f69c8f6104f/759fca73-22f5-4e3d-8e1c-ee8024c13159/data.jsonl	1	044dafb6c72167f143b251efe625bce71e1c5822ad63e00ee51570ee36981913	2026-01-12 00:26:19.851154
3c6856d1-eb6a-4378-9860-25dec76e8cdb	a3ba818c-6eb4-4bf1-9c3f-5f69c8f6104f	4f5fbce1-8844-48ad-845d-396c49d97002	1	0	19	{"type": "object", "required": ["first", "totalElements", "number", "empty", "advertencia", "sort", "last", "numberOfElements", "size", "pageable", "content", "totalPages"], "properties": {"last": {"type": "boolean"}, "size": {"type": "integer"}, "sort": {"type": "object", "properties": {"empty": {"type": "boolean"}, "sorted": {"type": "boolean"}, "unsorted": {"type": "boolean"}}}, "empty": {"type": "boolean"}, "first": {"type": "boolean"}, "number": {"type": "integer"}, "content": {"type": "array", "items": {"type": "object", "properties": {"id": {"type": "integer"}, "mrr": {"type": "boolean"}, "nivel1": {"type": "string"}, "nivel2": {"type": "string"}, "nivel3": {"type": "string"}, "descripcion": {"type": "string"}, "codigoInvente": {"type": "string"}, "fechaRecepcion": {"type": "string"}, "descripcionLeng": {"type": "string"}, "numeroConvocatoria": {"type": "string"}}}}, "pageable": {"type": "object", "properties": {"sort": {"type": "object", "properties": {"empty": {"type": "boolean"}, "sorted": {"type": "boolean"}, "unsorted": {"type": "boolean"}}}, "paged": {"type": "boolean"}, "offset": {"type": "integer"}, "unpaged": {"type": "boolean"}, "pageSize": {"type": "integer"}, "pageNumber": {"type": "integer"}}}, "totalPages": {"type": "integer"}, "advertencia": {"type": "string"}, "totalElements": {"type": "integer"}, "numberOfElements": {"type": "integer"}}}	data/datasets/a3ba818c-6eb4-4bf1-9c3f-5f69c8f6104f/3c6856d1-eb6a-4378-9860-25dec76e8cdb/data.jsonl	1	b3fa75bff2e7f7d20f70891fb544f7447eaa871ded3e99f7a9631f59bbcff748	2026-01-12 00:27:07.461828
24a3fe8f-4249-4151-8a88-006e846b29e9	a3ba818c-6eb4-4bf1-9c3f-5f69c8f6104f	13892239-0a1a-4dc1-8235-045294291d0b	1	0	20	{"type": "object", "required": ["last", "number", "empty", "pageable", "first", "content", "size", "totalPages", "totalElements", "advertencia", "numberOfElements", "sort"], "properties": {"last": {"type": "boolean"}, "size": {"type": "integer"}, "sort": {"type": "object", "properties": {"empty": {"type": "boolean"}, "sorted": {"type": "boolean"}, "unsorted": {"type": "boolean"}}}, "empty": {"type": "boolean"}, "first": {"type": "boolean"}, "number": {"type": "integer"}, "content": {"type": "array", "items": {"type": "object", "properties": {"id": {"type": "integer"}, "mrr": {"type": "boolean"}, "nivel1": {"type": "string"}, "nivel2": {"type": "string"}, "nivel3": {"type": "string"}, "descripcion": {"type": "string"}, "codigoInvente": {"type": "string"}, "fechaRecepcion": {"type": "string"}, "descripcionLeng": {"type": "string"}, "numeroConvocatoria": {"type": "string"}}}}, "pageable": {"type": "object", "properties": {"sort": {"type": "object", "properties": {"empty": {"type": "boolean"}, "sorted": {"type": "boolean"}, "unsorted": {"type": "boolean"}}}, "paged": {"type": "boolean"}, "offset": {"type": "integer"}, "unpaged": {"type": "boolean"}, "pageSize": {"type": "integer"}, "pageNumber": {"type": "integer"}}}, "totalPages": {"type": "integer"}, "advertencia": {"type": "string"}, "totalElements": {"type": "integer"}, "numberOfElements": {"type": "integer"}}}	data/datasets/a3ba818c-6eb4-4bf1-9c3f-5f69c8f6104f/24a3fe8f-4249-4151-8a88-006e846b29e9/data.jsonl	1	b3fa75bff2e7f7d20f70891fb544f7447eaa871ded3e99f7a9631f59bbcff748	2026-01-12 00:47:09.846655
f9c82ed8-10cb-4172-8995-83b0db85d7c4	a3ba818c-6eb4-4bf1-9c3f-5f69c8f6104f	af7f47b8-36f4-4964-a59e-ab0820f37c7e	1	0	21	{"type": "object", "required": ["pageable", "first", "numberOfElements", "advertencia", "number", "last", "totalPages", "content", "totalElements", "empty", "sort", "size"], "properties": {"last": {"type": "boolean"}, "size": {"type": "integer"}, "sort": {"type": "object", "properties": {"empty": {"type": "boolean"}, "sorted": {"type": "boolean"}, "unsorted": {"type": "boolean"}}}, "empty": {"type": "boolean"}, "first": {"type": "boolean"}, "number": {"type": "integer"}, "content": {"type": "array", "items": {"type": "object", "properties": {"id": {"type": "integer"}, "mrr": {"type": "boolean"}, "nivel1": {"type": "string"}, "nivel2": {"type": "string"}, "nivel3": {"type": "string"}, "descripcion": {"type": "string"}, "codigoInvente": {"type": "string"}, "fechaRecepcion": {"type": "string"}, "descripcionLeng": {"type": "string"}, "numeroConvocatoria": {"type": "string"}}}}, "pageable": {"type": "object", "properties": {"sort": {"type": "object", "properties": {"empty": {"type": "boolean"}, "sorted": {"type": "boolean"}, "unsorted": {"type": "boolean"}}}, "paged": {"type": "boolean"}, "offset": {"type": "integer"}, "unpaged": {"type": "boolean"}, "pageSize": {"type": "integer"}, "pageNumber": {"type": "integer"}}}, "totalPages": {"type": "integer"}, "advertencia": {"type": "string"}, "totalElements": {"type": "integer"}, "numberOfElements": {"type": "integer"}}}	data/datasets/a3ba818c-6eb4-4bf1-9c3f-5f69c8f6104f/f9c82ed8-10cb-4172-8995-83b0db85d7c4/data.jsonl	1	b3fa75bff2e7f7d20f70891fb544f7447eaa871ded3e99f7a9631f59bbcff748	2026-01-12 00:50:16.028753
e23ef360-f857-49cd-8bb7-2d39ebd52882	a3ba818c-6eb4-4bf1-9c3f-5f69c8f6104f	dac91de5-1ae4-41f2-935d-54dce72331b9	1	0	22	{"type": "object", "required": ["pageable", "size", "sort", "last", "first", "empty", "advertencia", "content", "totalPages", "totalElements", "number", "numberOfElements"], "properties": {"last": {"type": "boolean"}, "size": {"type": "integer"}, "sort": {"type": "object", "properties": {"empty": {"type": "boolean"}, "sorted": {"type": "boolean"}, "unsorted": {"type": "boolean"}}}, "empty": {"type": "boolean"}, "first": {"type": "boolean"}, "number": {"type": "integer"}, "content": {"type": "array", "items": {"type": "object", "properties": {"id": {"type": "integer"}, "mrr": {"type": "boolean"}, "nivel1": {"type": "string"}, "nivel2": {"type": "string"}, "nivel3": {"type": "string"}, "descripcion": {"type": "string"}, "codigoInvente": {"type": "string"}, "fechaRecepcion": {"type": "string"}, "descripcionLeng": {"type": "string"}, "numeroConvocatoria": {"type": "string"}}}}, "pageable": {"type": "object", "properties": {"sort": {"type": "object", "properties": {"empty": {"type": "boolean"}, "sorted": {"type": "boolean"}, "unsorted": {"type": "boolean"}}}, "paged": {"type": "boolean"}, "offset": {"type": "integer"}, "unpaged": {"type": "boolean"}, "pageSize": {"type": "integer"}, "pageNumber": {"type": "integer"}}}, "totalPages": {"type": "integer"}, "advertencia": {"type": "string"}, "totalElements": {"type": "integer"}, "numberOfElements": {"type": "integer"}}}	data/datasets/a3ba818c-6eb4-4bf1-9c3f-5f69c8f6104f/e23ef360-f857-49cd-8bb7-2d39ebd52882/data.jsonl	1	044dafb6c72167f143b251efe625bce71e1c5822ad63e00ee51570ee36981913	2026-01-12 00:51:09.331063
4fa52612-b973-4b7a-86b1-599f0ea4f0b8	a3ba818c-6eb4-4bf1-9c3f-5f69c8f6104f	f0c00799-361e-46be-ad56-370ee3f57c8d	1	0	23	{"type": "object", "required": ["totalElements", "sort", "number", "advertencia", "first", "last", "content", "empty", "pageable", "numberOfElements", "totalPages", "size"], "properties": {"last": {"type": "boolean"}, "size": {"type": "integer"}, "sort": {"type": "object", "properties": {"empty": {"type": "boolean"}, "sorted": {"type": "boolean"}, "unsorted": {"type": "boolean"}}}, "empty": {"type": "boolean"}, "first": {"type": "boolean"}, "number": {"type": "integer"}, "content": {"type": "array", "items": {"type": "object", "properties": {"id": {"type": "integer"}, "mrr": {"type": "boolean"}, "nivel1": {"type": "string"}, "nivel2": {"type": "string"}, "nivel3": {"type": "string"}, "descripcion": {"type": "string"}, "codigoInvente": {"type": "string"}, "fechaRecepcion": {"type": "string"}, "descripcionLeng": {"type": "string"}, "numeroConvocatoria": {"type": "string"}}}}, "pageable": {"type": "object", "properties": {"sort": {"type": "object", "properties": {"empty": {"type": "boolean"}, "sorted": {"type": "boolean"}, "unsorted": {"type": "boolean"}}}, "paged": {"type": "boolean"}, "offset": {"type": "integer"}, "unpaged": {"type": "boolean"}, "pageSize": {"type": "integer"}, "pageNumber": {"type": "integer"}}}, "totalPages": {"type": "integer"}, "advertencia": {"type": "string"}, "totalElements": {"type": "integer"}, "numberOfElements": {"type": "integer"}}}	data/datasets/a3ba818c-6eb4-4bf1-9c3f-5f69c8f6104f/4fa52612-b973-4b7a-86b1-599f0ea4f0b8/data.jsonl	1	044dafb6c72167f143b251efe625bce71e1c5822ad63e00ee51570ee36981913	2026-01-12 00:51:29.833199
ea87f46e-cd6e-4af2-a47d-e749a85bcd86	a3ba818c-6eb4-4bf1-9c3f-5f69c8f6104f	32e603ff-03f3-443f-a086-a5d267a3a5ea	1	0	24	{"type": "object", "required": ["totalPages", "numberOfElements", "empty", "size", "totalElements", "advertencia", "number", "last", "pageable", "content", "first", "sort"], "properties": {"last": {"type": "boolean"}, "size": {"type": "integer"}, "sort": {"type": "object", "properties": {"empty": {"type": "boolean"}, "sorted": {"type": "boolean"}, "unsorted": {"type": "boolean"}}}, "empty": {"type": "boolean"}, "first": {"type": "boolean"}, "number": {"type": "integer"}, "content": {"type": "array", "items": {"type": "object", "properties": {"id": {"type": "integer"}, "mrr": {"type": "boolean"}, "nivel1": {"type": "string"}, "nivel2": {"type": "string"}, "nivel3": {"type": "string"}, "descripcion": {"type": "string"}, "codigoInvente": {"type": "string"}, "fechaRecepcion": {"type": "string"}, "descripcionLeng": {"type": "string"}, "numeroConvocatoria": {"type": "string"}}}}, "pageable": {"type": "object", "properties": {"sort": {"type": "object", "properties": {"empty": {"type": "boolean"}, "sorted": {"type": "boolean"}, "unsorted": {"type": "boolean"}}}, "paged": {"type": "boolean"}, "offset": {"type": "integer"}, "unpaged": {"type": "boolean"}, "pageSize": {"type": "integer"}, "pageNumber": {"type": "integer"}}}, "totalPages": {"type": "integer"}, "advertencia": {"type": "string"}, "totalElements": {"type": "integer"}, "numberOfElements": {"type": "integer"}}}	data/datasets/a3ba818c-6eb4-4bf1-9c3f-5f69c8f6104f/ea87f46e-cd6e-4af2-a47d-e749a85bcd86/data.jsonl	1	044dafb6c72167f143b251efe625bce71e1c5822ad63e00ee51570ee36981913	2026-01-12 00:52:45.659894
4e11464b-a2a0-44d8-b81b-11d72fb786c0	a3ba818c-6eb4-4bf1-9c3f-5f69c8f6104f	3a2073bd-913c-417f-8016-775aafc89aa1	1	0	25	{"type": "object", "required": ["empty", "content", "numberOfElements", "sort", "number", "last", "first", "totalPages", "pageable", "size", "totalElements", "advertencia"], "properties": {"last": {"type": "boolean"}, "size": {"type": "integer"}, "sort": {"type": "object", "properties": {"empty": {"type": "boolean"}, "sorted": {"type": "boolean"}, "unsorted": {"type": "boolean"}}}, "empty": {"type": "boolean"}, "first": {"type": "boolean"}, "number": {"type": "integer"}, "content": {"type": "array", "items": {"type": "object", "properties": {"id": {"type": "integer"}, "mrr": {"type": "boolean"}, "nivel1": {"type": "string"}, "nivel2": {"type": "string"}, "nivel3": {"type": "string"}, "descripcion": {"type": "string"}, "codigoInvente": {"type": "string"}, "fechaRecepcion": {"type": "string"}, "descripcionLeng": {"type": "string"}, "numeroConvocatoria": {"type": "string"}}}}, "pageable": {"type": "object", "properties": {"sort": {"type": "object", "properties": {"empty": {"type": "boolean"}, "sorted": {"type": "boolean"}, "unsorted": {"type": "boolean"}}}, "paged": {"type": "boolean"}, "offset": {"type": "integer"}, "unpaged": {"type": "boolean"}, "pageSize": {"type": "integer"}, "pageNumber": {"type": "integer"}}}, "totalPages": {"type": "integer"}, "advertencia": {"type": "string"}, "totalElements": {"type": "integer"}, "numberOfElements": {"type": "integer"}}}	data/datasets/a3ba818c-6eb4-4bf1-9c3f-5f69c8f6104f/4e11464b-a2a0-44d8-b81b-11d72fb786c0/data.jsonl	1	b3fa75bff2e7f7d20f70891fb544f7447eaa871ded3e99f7a9631f59bbcff748	2026-01-12 00:53:05.604168
\.


--
-- Data for Name: dataset_subscription; Type: TABLE DATA; Schema: opendata; Owner: -
--

COPY opendata.dataset_subscription (id, application_id, resource_id, pinned_version, auto_upgrade, current_version, notified_at) FROM stdin;
\.


--
-- Data for Name: fetcher; Type: TABLE DATA; Schema: opendata; Owner: -
--

COPY opendata.fetcher (id, name, description, class_path) FROM stdin;
3f98aef5-d183-4d5b-8263-e350c147c3bd	Fetcher of CSV files downloade from a  url	Just a simple fetcher of data from a download link	app.fetchers.csv.CSVFetcher
1fbdb7e0-c9ae-4054-9f8e-bc26de3de2be	API REST	API RESTful con soporte para JSON/XML	app.fetchers.rest.RestFetcher
7f29b59b-7c09-4ced-bf84-07becd2f4bf9	HTML Forms	Formularios web HTML (scraping de páginas y formularios)	app.fetchers.html.HTMLFetcher
b2660544-0e67-4341-bee4-a76e2b101aa7	Portales CKAN	Fetcher genérico para portales CKAN (Comprehensive Knowledge Archive Network). Soporta datos.gob.es, data.gov, data.gov.uk y cualquier portal basado en CKAN. Permite extraer datasets, recursos y metadatos desde cualquier portal que implemente la API CKAN estándar.	app.fetchers.ckan.CKANFetcher
202a7314-6952-4f19-9000-5f44b04beea6	Servicios Geográficos	Fetcher universal para datos geográficos y geoespaciales. Soporta estándares OGC (WFS, WMS) y formatos GeoJSON, Shapefile. Ideal para catastro, límites administrativos, cartografía, mapas base y cualquier tipo de información georreferenciada. Permite filtrado espacial, transformación de coordenadas y simplificación de geometrías.	app.fetchers.geo.GeoFetcher
7631f4de-bc1d-4a14-9f54-85add6bd92fc	Servicios SOAP/WSDL	Fetcher para servicios web SOAP/WSDL. Soporta operaciones SOAP estándar con autenticación WS-Security. Permite invocar métodos de servicios web empresariales, procesamiento de WSDL automático, selección de servicios y puertos específicos, y configuración de timeouts y validación SSL.	app.fetchers.soap.SoapFetcher
d8c425be-ea01-4fa3-9251-16d4e4bd177c	Feeds ATOM/RSS	Fetcher para feeds ATOM y RSS estándar, compatible con ContentAPI de la Junta de Andalucía y otros portales de datos abiertos que usan sindicación XML. Soporta paginación OpenSearch (startIndex, itemsPerPage, totalResults) y parsing de entries ATOM con múltiples campos.	app.fetchers.atom.AtomFetcher
\.


--
-- Data for Name: field_metadata; Type: TABLE DATA; Schema: opendata; Owner: -
--

COPY opendata.field_metadata (id, table_name, field_name, label, help_text, placeholder) FROM stdin;
053a3f1e-5825-426a-8fba-f33b2c9d1a5e	source	name	Nombre del Source	Nombre único e identificativo para este origen de datos. Ejemplo: 'API Clientes ACME'	e.g., API Clientes ACME
c6362941-5422-4778-95ab-96fcede0ba7a	source	project	Proyecto	Proyecto o dominio al que pertenece este source. Usado para agrupar sources relacionados. Ejemplo: 'clientes', 'ventas', 'inventario'	e.g., clientes
ccde487a-ba67-49c0-b009-821e3e425c00	source	fetcher_type_id	Tipo de Servicio Web	Tipo de servicio web que se usará para obtener los datos (API REST, SOAP, archivos, etc.)	\N
119c5f6f-e298-4a40-ac4a-da0a90b10e62	source	active	Activo	Si está activo, este source se ejecutará automáticamente en las actualizaciones programadas	\N
aa5b9188-15d2-4b13-8d19-ef25ed92f11f	source_param	url	URL	URL completa del endpoint de la API. Ejemplo: https://api.ejemplo.com/v1/clientes	https://api.ejemplo.com/v1/endpoint
69da5393-a5e0-47a0-8d1d-251691c122da	source_param	method	Método HTTP	Método HTTP a utilizar (GET, POST, PUT, DELETE, etc.). GET es el más común para consultar datos	GET
4bcf1eea-df9d-4b1b-b837-562916029800	source_param	headers	Headers	Headers HTTP en formato JSON. Ejemplo: {"Authorization": "Bearer token123", "Content-Type": "application/json"}	{"Authorization": "Bearer ..."}
66ff6f44-f13a-44c2-a755-3f5c1301174f	source_param	timeout	Timeout	Tiempo máximo de espera en segundos para la petición HTTP. Por defecto es 30 segundos	30
36dad4a3-bd28-4508-a769-111525dbff76	application	name	Nombre de la Aplicación	Nombre de la aplicación que recibirá los modelos generados automáticamente	e.g., MiApp Backend
42e9b00a-6ea9-407e-bd5f-b8f493b7d65f	application	models_path	Ruta de Modelos	Ruta absoluta donde se escribirán los archivos de modelos generados. Ejemplo: /app/core/models	/app/core/models
255578df-f5d7-4a75-813f-c9e8ae4c8572	application	subscribed_projects	Proyectos Suscritos	Lista de proyectos a los que esta aplicación está suscrita. Recibirá modelos de sources que pertenezcan a estos proyectos	["clientes", "ventas"]
5d466ff3-1129-4335-a8c3-8772cdfd8f06	source_param	nombreEntidad	Nombre Entidad	Nombre de la entidad religiosa a buscar (texto libre). Usado en búsquedas del RER del Ministerio de Justicia	e.g., Iglesia Católica
00ae4622-7ff8-466d-8e64-6f87bf77904e	source_param	numeroRegistro	Número de Registro	Número de registro oficial de la entidad en el RER	e.g., 005476
3a0f0071-d9a6-4a29-b108-4fce9193b790	source_param	numeroRegistroAntiguo	Número de Registro Antiguo	Número de registro antiguo de la entidad (antes de reorganizaciones del registro)	e.g., 12345
03756583-a56c-472b-8d1d-fc3eb162e8f1	source_param	confesion	Confesión Religiosa	Confesión religiosa de la entidad. Valores: CATÓLICOS, EVANGÉLICOS, JUDÍOS, MUSULMANES, BUDISTAS, ORTODOXOS, etc.	e.g., CATÓLICOS
b5b561c7-a5b7-4e4e-b6d9-9181e62c1a69	source_param	subconfesion	Subconfesión	Subgrupo dentro de la confesión religiosa. Ejemplos: ADVENTISTAS, BAUTISTAS, PENTECOSTALES, etc.	e.g., BAUTISTAS
dc29dae1-b890-47a1-8165-eacd512e0e78	source_param	seccion	Sección del Registro	Sección administrativa del registro. Valores: TODAS, GENERAL, ESPECIAL	e.g., GENERAL
e1da7c9a-89f0-4b12-a784-b85fef827767	source_param	tipoEntidad	Tipo de Entidad	Tipo jurídico de la entidad religiosa. Ejemplos: IGLESIA, COMUNIDAD, ASOCIACIÓN, FEDERACIÓN, FUNDACIÓN, ORDEN	e.g., ASOCIACIÓN
26baf899-d531-4267-8201-af1fc76e525d	source_param	comunidad	Comunidad Autónoma	Comunidad Autónoma donde está registrada la entidad. Ejemplos: ANDALUCIA, MADRID, CATALUÑA, etc.	e.g., MADRID
d43b69d5-0f32-4b26-9325-58f1eaef8e87	source_param	provincia	Provincia	Provincia donde está registrada la entidad religiosa	e.g., Madrid
7ead19ad-c03d-4fff-86d5-9af259298cbf	source_param	municipio	Municipio	Municipio donde está registrada la entidad religiosa	e.g., Madrid
db96b8cc-50a0-4c29-8687-6526528aeeaa	source_param	page	Página	Número de página para paginación de resultados. Usar en búsquedas que devuelven múltiples resultados	1
beb01ea4-c7ad-4f1c-a7b7-ca8dfc33f9bc	source_param	numeroInscripcion	Número de Inscripción	Número de inscripción para obtener el detalle completo de una entidad específica (endpoint DetalleEntidadReligiosa)	e.g., 005476
\.


--
-- Data for Name: resource; Type: TABLE DATA; Schema: opendata; Owner: -
--

COPY opendata.resource (id, name, publisher, fetcher_id, active, description, target_table, enable_load, load_mode, max_workers, timeout_seconds, retry_attempts, retry_delay_seconds, execution_priority) FROM stdin;
dc468e7d-b7d6-456f-9db1-c6b8366c0457	Datos.gob.es - Catálogo	Ministerio de Hacienda	7f29b59b-7c09-4ced-bf84-07becd2f4bf9	t	Catálogo de datos abiertos del sector público español	datosgob_catalog	f	replace	1	300	0	60	0
57b84116-f187-40b3-98e4-3fce7e659a3d	Catalogos del INE	INE	1fbdb7e0-c9ae-4054-9f8e-bc26de3de2be	t	\N	\N	f	replace	1	300	0	60	0
f3796775-a248-4919-a67d-ebffc42dd6d0	INE - Población por Municipios	Instituto Nacional de Estadística	1fbdb7e0-c9ae-4054-9f8e-bc26de3de2be	t	Instituto Nacional de Estadística - Cifras oficiales de población municipal	ine_population	f	replace	1	300	0	60	0
a3ba818c-6eb4-4bf1-9c3f-5f69c8f6104f	BDNS - Convocatorias de Subvenciones	IGAE	1fbdb7e0-c9ae-4054-9f8e-bc26de3de2be	t	Base de Datos Nacional de Subvenciones - Convocatorias publicadas via API REST	bdns_grants	t	replace	1	300	0	60	0
afa36e79-336b-4701-81b9-a7a6a8a6b5b2	Bienes Inmuebles - Junta de Andalucía	Junta de Andalucía	d8c425be-ea01-4fa3-9251-16d4e4bd177c	t	\N	\N	f	replace	1	300	0	60	0
\.


--
-- Data for Name: resource_execution; Type: TABLE DATA; Schema: opendata; Owner: -
--

COPY opendata.resource_execution (id, resource_id, started_at, completed_at, status, total_records, records_loaded, staging_path, error_message) FROM stdin;
e8f9337e-da65-4b71-af35-ac661cbec4cf	a3ba818c-6eb4-4bf1-9c3f-5f69c8f6104f	2026-01-10 22:02:21.98574	2026-01-10 22:02:25.359345	completed	1	\N	data/staging/a3ba818c-6eb4-4bf1-9c3f-5f69c8f6104f/e8f9337e-da65-4b71-af35-ac661cbec4cf.jsonl	\N
cd83d0fc-3520-4282-a933-cee2e787bd65	a3ba818c-6eb4-4bf1-9c3f-5f69c8f6104f	2026-01-10 22:33:49.800631	2026-01-10 22:33:52.944431	completed	1	\N	data/staging/a3ba818c-6eb4-4bf1-9c3f-5f69c8f6104f/cd83d0fc-3520-4282-a933-cee2e787bd65.jsonl	\N
d1fda079-6b31-4ff6-9a78-d04d599bac35	a3ba818c-6eb4-4bf1-9c3f-5f69c8f6104f	2026-01-10 22:34:33.07096	2026-01-10 22:34:36.345265	completed	1	\N	data/staging/a3ba818c-6eb4-4bf1-9c3f-5f69c8f6104f/d1fda079-6b31-4ff6-9a78-d04d599bac35.jsonl	\N
ed178697-bc07-47cc-b40a-6a17772aa6d5	a3ba818c-6eb4-4bf1-9c3f-5f69c8f6104f	2026-01-10 22:53:54.003624	2026-01-10 22:53:57.43147	completed	1	\N	data/staging/a3ba818c-6eb4-4bf1-9c3f-5f69c8f6104f/ed178697-bc07-47cc-b40a-6a17772aa6d5.jsonl	\N
5d961117-176c-4c9a-b459-460152345e38	a3ba818c-6eb4-4bf1-9c3f-5f69c8f6104f	2026-01-10 22:54:45.531113	2026-01-10 22:54:48.764193	completed	1	\N	data/staging/a3ba818c-6eb4-4bf1-9c3f-5f69c8f6104f/5d961117-176c-4c9a-b459-460152345e38.jsonl	\N
d1fa23c9-5ae2-41fc-800f-cd3c16ba43af	f3796775-a248-4919-a67d-ebffc42dd6d0	2026-01-10 22:56:14.183044	2026-01-10 22:56:16.020888	completed	159	\N	data/staging/f3796775-a248-4919-a67d-ebffc42dd6d0/d1fa23c9-5ae2-41fc-800f-cd3c16ba43af.jsonl	\N
27533b0f-4093-4a9a-86b8-cd087f1ae371	a3ba818c-6eb4-4bf1-9c3f-5f69c8f6104f	2026-01-10 23:21:49.092282	2026-01-10 23:21:52.221887	completed	1	\N	data/staging/a3ba818c-6eb4-4bf1-9c3f-5f69c8f6104f/27533b0f-4093-4a9a-86b8-cd087f1ae371.jsonl	\N
1701b52f-c7fc-433b-85c3-55587f4ff45a	a3ba818c-6eb4-4bf1-9c3f-5f69c8f6104f	2026-01-10 23:27:37.355574	2026-01-10 23:27:40.439431	completed	1	\N	data/staging/a3ba818c-6eb4-4bf1-9c3f-5f69c8f6104f/1701b52f-c7fc-433b-85c3-55587f4ff45a.jsonl	\N
2579aeb9-3cec-42f4-b371-0e97892be485	a3ba818c-6eb4-4bf1-9c3f-5f69c8f6104f	2026-01-10 23:28:00.310578	2026-01-10 23:28:03.595843	completed	1	\N	data/staging/a3ba818c-6eb4-4bf1-9c3f-5f69c8f6104f/2579aeb9-3cec-42f4-b371-0e97892be485.jsonl	\N
b01bfe20-3faf-4da7-a727-3ed038795793	a3ba818c-6eb4-4bf1-9c3f-5f69c8f6104f	2026-01-11 10:39:42.204785	2026-01-11 10:39:45.93941	completed	1	\N	data/staging/a3ba818c-6eb4-4bf1-9c3f-5f69c8f6104f/b01bfe20-3faf-4da7-a727-3ed038795793.jsonl	\N
87d3af2f-cd2d-420c-832a-8f4811267e22	a3ba818c-6eb4-4bf1-9c3f-5f69c8f6104f	2026-01-10 19:35:32.93118	2026-01-10 19:35:36.769236	completed	1	\N	data/staging/a3ba818c-6eb4-4bf1-9c3f-5f69c8f6104f/87d3af2f-cd2d-420c-832a-8f4811267e22.jsonl	\N
18a71f01-d93a-4a53-80c3-de83a5231f42	a3ba818c-6eb4-4bf1-9c3f-5f69c8f6104f	2026-01-10 21:52:09.609544	2026-01-10 21:52:12.961865	completed	1	\N	data/staging/a3ba818c-6eb4-4bf1-9c3f-5f69c8f6104f/18a71f01-d93a-4a53-80c3-de83a5231f42.jsonl	\N
f0c00799-361e-46be-ad56-370ee3f57c8d	a3ba818c-6eb4-4bf1-9c3f-5f69c8f6104f	2026-01-12 00:51:26.777762	2026-01-12 00:51:29.879575	completed	1	\N	data/staging/a3ba818c-6eb4-4bf1-9c3f-5f69c8f6104f/f0c00799-361e-46be-ad56-370ee3f57c8d.jsonl	\N
8496db57-89bb-455a-b947-3eee59850728	a3ba818c-6eb4-4bf1-9c3f-5f69c8f6104f	2026-01-10 22:02:07.613486	2026-01-10 22:02:10.969859	completed	1	\N	data/staging/a3ba818c-6eb4-4bf1-9c3f-5f69c8f6104f/8496db57-89bb-455a-b947-3eee59850728.jsonl	\N
88fd0f97-6aec-4456-98ad-27f083a08df9	a3ba818c-6eb4-4bf1-9c3f-5f69c8f6104f	2026-01-11 10:40:04.390382	2026-01-11 10:40:07.838831	completed	1	\N	data/staging/a3ba818c-6eb4-4bf1-9c3f-5f69c8f6104f/88fd0f97-6aec-4456-98ad-27f083a08df9.jsonl	\N
fc6a61d8-2ccb-4eba-803f-6d048195e206	a3ba818c-6eb4-4bf1-9c3f-5f69c8f6104f	2026-01-11 10:48:07.489694	2026-01-11 10:48:10.818922	completed	1	\N	data/staging/a3ba818c-6eb4-4bf1-9c3f-5f69c8f6104f/fc6a61d8-2ccb-4eba-803f-6d048195e206.jsonl	\N
82b04bfe-7218-470b-b43f-7a53ef56c723	a3ba818c-6eb4-4bf1-9c3f-5f69c8f6104f	2026-01-11 10:48:53.589534	2026-01-11 10:48:57.115805	completed	1	\N	data/staging/a3ba818c-6eb4-4bf1-9c3f-5f69c8f6104f/82b04bfe-7218-470b-b43f-7a53ef56c723.jsonl	\N
6dc5d3dd-46b4-4fff-b312-cb40fa02302d	a3ba818c-6eb4-4bf1-9c3f-5f69c8f6104f	2026-01-11 18:53:32.161504	2026-01-11 18:53:35.360023	completed	1	\N	data/staging/a3ba818c-6eb4-4bf1-9c3f-5f69c8f6104f/6dc5d3dd-46b4-4fff-b312-cb40fa02302d.jsonl	\N
dd2dbec3-d4da-4c9b-ab10-54ce27e95e17	a3ba818c-6eb4-4bf1-9c3f-5f69c8f6104f	2026-01-11 18:54:01.370783	2026-01-11 18:54:04.370218	completed	1	\N	data/staging/a3ba818c-6eb4-4bf1-9c3f-5f69c8f6104f/dd2dbec3-d4da-4c9b-ab10-54ce27e95e17.jsonl	\N
450e6291-219a-40b2-887b-8405cbc4d065	a3ba818c-6eb4-4bf1-9c3f-5f69c8f6104f	2026-01-11 18:54:20.851647	2026-01-11 18:54:23.741847	completed	1	\N	data/staging/a3ba818c-6eb4-4bf1-9c3f-5f69c8f6104f/450e6291-219a-40b2-887b-8405cbc4d065.jsonl	\N
104688e4-5c2c-4864-9064-1a1af5a0c081	a3ba818c-6eb4-4bf1-9c3f-5f69c8f6104f	2026-01-12 00:26:16.907963	2026-01-12 00:26:19.903605	completed	1	\N	data/staging/a3ba818c-6eb4-4bf1-9c3f-5f69c8f6104f/104688e4-5c2c-4864-9064-1a1af5a0c081.jsonl	\N
4f5fbce1-8844-48ad-845d-396c49d97002	a3ba818c-6eb4-4bf1-9c3f-5f69c8f6104f	2026-01-12 00:27:04.542495	2026-01-12 00:27:07.510652	completed	1	\N	data/staging/a3ba818c-6eb4-4bf1-9c3f-5f69c8f6104f/4f5fbce1-8844-48ad-845d-396c49d97002.jsonl	\N
13892239-0a1a-4dc1-8235-045294291d0b	a3ba818c-6eb4-4bf1-9c3f-5f69c8f6104f	2026-01-12 00:47:06.238821	2026-01-12 00:47:09.913431	completed	1	\N	data/staging/a3ba818c-6eb4-4bf1-9c3f-5f69c8f6104f/13892239-0a1a-4dc1-8235-045294291d0b.jsonl	\N
af7f47b8-36f4-4964-a59e-ab0820f37c7e	a3ba818c-6eb4-4bf1-9c3f-5f69c8f6104f	2026-01-12 00:50:12.987135	2026-01-12 00:50:16.08917	completed	1	\N	data/staging/a3ba818c-6eb4-4bf1-9c3f-5f69c8f6104f/af7f47b8-36f4-4964-a59e-ab0820f37c7e.jsonl	\N
dac91de5-1ae4-41f2-935d-54dce72331b9	a3ba818c-6eb4-4bf1-9c3f-5f69c8f6104f	2026-01-12 00:51:06.172961	2026-01-12 00:51:09.39232	completed	1	\N	data/staging/a3ba818c-6eb4-4bf1-9c3f-5f69c8f6104f/dac91de5-1ae4-41f2-935d-54dce72331b9.jsonl	\N
32e603ff-03f3-443f-a086-a5d267a3a5ea	a3ba818c-6eb4-4bf1-9c3f-5f69c8f6104f	2026-01-12 00:52:42.720036	2026-01-12 00:52:45.714013	completed	1	\N	data/staging/a3ba818c-6eb4-4bf1-9c3f-5f69c8f6104f/32e603ff-03f3-443f-a086-a5d267a3a5ea.jsonl	\N
3a2073bd-913c-417f-8016-775aafc89aa1	a3ba818c-6eb4-4bf1-9c3f-5f69c8f6104f	2026-01-12 00:53:02.543801	2026-01-12 00:53:05.662074	completed	1	\N	data/staging/a3ba818c-6eb4-4bf1-9c3f-5f69c8f6104f/3a2073bd-913c-417f-8016-775aafc89aa1.jsonl	\N
d3f759c1-5eac-47f0-a262-eb052aa397ff	a3ba818c-6eb4-4bf1-9c3f-5f69c8f6104f	2026-01-12 00:56:36.051548	2026-01-12 00:56:38.975682	completed	1	\N	data/staging/a3ba818c-6eb4-4bf1-9c3f-5f69c8f6104f/d3f759c1-5eac-47f0-a262-eb052aa397ff.jsonl	\N
6fa78ecd-b5f1-49e0-80dd-c29b571dd107	dc468e7d-b7d6-456f-9db1-c6b8366c0457	2026-01-12 15:59:06.567667	2026-01-12 15:59:06.6904	failed	\N	\N	\N	FetcherType 'API REST' no tiene class_path definido
c8f0b30b-70bc-4d90-a09d-c1b060c08861	dc468e7d-b7d6-456f-9db1-c6b8366c0457	2026-01-12 16:14:17.28779	2026-01-12 16:14:18.149908	failed	\N	\N	\N	No module named 'bs4'
4f12ded1-01b3-4090-866f-681f16f57a35	dc468e7d-b7d6-456f-9db1-c6b8366c0457	2026-01-12 16:15:27.12367	2026-01-12 16:15:28.323642	failed	\N	\N	\N	No module named 'bs4'
c577d840-13d5-438f-b3b5-ca003ca9eddf	dc468e7d-b7d6-456f-9db1-c6b8366c0457	2026-01-12 16:15:29.470956	2026-01-12 16:15:30.360531	failed	\N	\N	\N	No module named 'bs4'
8150c091-4d7f-48fe-b362-ffd5f487cbb4	dc468e7d-b7d6-456f-9db1-c6b8366c0457	2026-01-12 16:17:23.251461	2026-01-12 16:17:24.047726	failed	\N	\N	\N	No module named 'bs4'
16c0694e-4a53-49f9-a600-b7be6151f53c	dc468e7d-b7d6-456f-9db1-c6b8366c0457	2026-01-12 16:17:25.192556	2026-01-12 16:17:25.988804	failed	\N	\N	\N	No module named 'bs4'
76c724c0-1f67-409e-9bc5-35f5c57d3195	dc468e7d-b7d6-456f-9db1-c6b8366c0457	2026-01-13 12:50:22.11829	2026-01-13 12:50:23.008401	completed	1	\N	data/staging/dc468e7d-b7d6-456f-9db1-c6b8366c0457/76c724c0-1f67-409e-9bc5-35f5c57d3195.jsonl	\N
\.


--
-- Data for Name: resource_param; Type: TABLE DATA; Schema: opendata; Owner: -
--

COPY opendata.resource_param (id, resource_id, key, value) FROM stdin;
359007d5-35f6-44eb-8f6e-64e0498e933f	57b84116-f187-40b3-98e4-3fce7e659a3d	url	https://datos.gob.es/apidata/catalog/dataset.json
7144161a-df05-4a02-8f02-f486e9a30d40	f3796775-a248-4919-a67d-ebffc42dd6d0	url	https://servicios.ine.es/wstempus/js/ES/DATOS_TABLA/2852
bd86b919-cdef-4e02-803c-af8dc434825d	f3796775-a248-4919-a67d-ebffc42dd6d0	method	get
81f97d8a-b7e9-468b-adc0-a6a9a56b07c0	f3796775-a248-4919-a67d-ebffc42dd6d0	timeout	60
96e24fd2-7a19-4ab3-9879-a65c57eec236	f3796775-a248-4919-a67d-ebffc42dd6d0	max_retries	3
114f1832-db5a-44b3-b6c8-6364eeb42ed0	a3ba818c-6eb4-4bf1-9c3f-5f69c8f6104f	url	https://www.infosubvenciones.es/bdnstrans/api/convocatorias/busqueda
fdc62e4b-f279-4ef3-b351-64c184b73eef	a3ba818c-6eb4-4bf1-9c3f-5f69c8f6104f	method	get
8508a3dc-4981-4b19-b724-337154cbaec3	a3ba818c-6eb4-4bf1-9c3f-5f69c8f6104f	query_params	{"page": "0", "pageSize": "100", "order": "numeroConvocatoria", "direccion": "desc", "vpd": "GE"}
9189ec6d-59ee-48bb-aa21-e9be018299bc	a3ba818c-6eb4-4bf1-9c3f-5f69c8f6104f	timeout	60
ab33b3cb-8fa0-48fb-801f-2438a08fc14d	a3ba818c-6eb4-4bf1-9c3f-5f69c8f6104f	page-size	100
b3d4c3db-ba13-4040-b468-9a092d87b3b6	afa36e79-336b-4701-81b9-a7a6a8a6b5b2	base_url	https://www.juntadeandalucia.es/ssdigitales/datasets/contentapi/1.0.0/search/
9a762fed-c01a-443c-8923-b1f26467c7a8	afa36e79-336b-4701-81b9-a7a6a8a6b5b2	dataset_id	jda_buscador_bienes_inmuebles.atom
f4fa7dea-002d-4af0-82e1-db16f8e4dbad	afa36e79-336b-4701-81b9-a7a6a8a6b5b2	format	atom
17fc04cc-681a-4aef-b92f-1a76a875da7d	afa36e79-336b-4701-81b9-a7a6a8a6b5b2	page_size	50
002e3c22-9193-41c9-990d-a4a69a5cc449	afa36e79-336b-4701-81b9-a7a6a8a6b5b2	start_index	0
daa35381-1020-476d-838e-4d7367859d18	afa36e79-336b-4701-81b9-a7a6a8a6b5b2	sort	date:desc
787169a6-44ac-4c8b-a538-6423a6b7130e	afa36e79-336b-4701-81b9-a7a6a8a6b5b2	source_filter	data
4ae71f8d-c1e8-4010-b469-e1acb381728c	afa36e79-336b-4701-81b9-a7a6a8a6b5b2	timeout	30
2f0572eb-842b-4ece-87dd-40424dd44453	afa36e79-336b-4701-81b9-a7a6a8a6b5b2	verify_ssl	true
d9c92999-8c94-4933-afa6-061ddaf2a435	afa36e79-336b-4701-81b9-a7a6a8a6b5b2	max_pages	1
309bb9ab-f99d-44d2-8428-1bfa2204625a	dc468e7d-b7d6-456f-9db1-c6b8366c0457	url	https://datos.gob.es/apidata/catalog/dataset
1eec98b2-7485-4267-95a8-41ba04d98a6e	dc468e7d-b7d6-456f-9db1-c6b8366c0457	method	GET
8cb8e7eb-1ccd-4ec4-8dd1-03373fb6ba4b	dc468e7d-b7d6-456f-9db1-c6b8366c0457	timeout	45
\.


--
-- Data for Name: type_fetcher_params; Type: TABLE DATA; Schema: opendata; Owner: -
--

COPY opendata.type_fetcher_params (id, fetcher_id, param_name, required, data_type, default_value, enum_values, description) FROM stdin;
a6985ae6-c47a-4518-a6a3-821b61bd36d3	1fbdb7e0-c9ae-4054-9f8e-bc26de3de2be	page-size	f	integer	"100"	null	\N
b2639530-9dc6-446b-b08e-be1080b3645d	1fbdb7e0-c9ae-4054-9f8e-bc26de3de2be	method	f	enum	\N	["get", "post", "put"]	\N
d271007a-3f05-4acc-bd42-11cbb95f64c9	b2660544-0e67-4341-bee4-a76e2b101aa7	base_url	t	string	null	null	URL base del portal CKAN (ej: https://datos.gob.es)
881d48a4-83f2-4a38-97e9-825799013efa	b2660544-0e67-4341-bee4-a76e2b101aa7	api_key	f	string	null	null	API key para acceso a datos privados (opcional)
30631a1e-7820-4e0a-a773-8aa0acd1fe10	b2660544-0e67-4341-bee4-a76e2b101aa7	organization	f	string	null	null	Filtrar datasets por organización específica
c55b5060-a969-41e2-bea9-be9d678b2c35	b2660544-0e67-4341-bee4-a76e2b101aa7	limit	f	integer	"100"	null	Número máximo de datasets a obtener por ejecución
925aab6d-d6d0-4c14-bdf1-afabe1f8ee9a	b2660544-0e67-4341-bee4-a76e2b101aa7	format	f	string	"json"	["json", "csv", "xml", "geojson"]	Formato preferido de descarga de recursos
bf6803c6-29dd-47c1-96e5-38b17e950dd4	b2660544-0e67-4341-bee4-a76e2b101aa7	include_private	f	boolean	"false"	null	Incluir datasets privados (requiere api_key)
ef5bb569-0030-4faf-ac74-1a831a879a58	202a7314-6952-4f19-9000-5f44b04beea6	service_type	t	string	null	["wfs", "wms", "geojson", "shapefile"]	Tipo de servicio o formato geográfico
1f8b3a40-8b50-4a70-961f-744b4bec9daf	202a7314-6952-4f19-9000-5f44b04beea6	url	t	string	null	null	URL del servicio WFS/WMS o archivo GeoJSON/Shapefile
e270efb2-1477-43c9-a303-931825c17249	202a7314-6952-4f19-9000-5f44b04beea6	layer	f	string	null	null	Nombre de la capa a consultar (requerido para WFS/WMS)
8c4ad69d-dc4b-41b7-b277-6cb5b744f25c	202a7314-6952-4f19-9000-5f44b04beea6	version	f	string	"2.0.0"	["1.0.0", "1.1.0", "2.0.0"]	Versión del servicio OGC
516e6582-a572-42ba-a700-30d60ead8099	202a7314-6952-4f19-9000-5f44b04beea6	output_format	f	string	"application/json"	["application/json", "GML2", "GML3", "text/csv"]	Formato de salida para WFS
3aca0553-5053-4791-b798-58407bb2f75b	202a7314-6952-4f19-9000-5f44b04beea6	bbox	f	string	null	null	Bounding box para filtrar geográficamente (minx,miny,maxx,maxy). Ejemplo: -10,35,5,45
4792a8bb-8d89-44e2-910f-cf5173a36975	202a7314-6952-4f19-9000-5f44b04beea6	crs	f	string	"EPSG:4326"	["EPSG:4326", "EPSG:3857", "EPSG:25830", "EPSG:25829", "EPSG:25828"]	Sistema de referencia de coordenadas (CRS/EPSG)
627513c4-a217-4db5-bfe9-cba89a6ed123	202a7314-6952-4f19-9000-5f44b04beea6	max_features	f	integer	"1000"	null	Número máximo de features a obtener
ea09d062-2532-4266-b36a-8461f5d96295	202a7314-6952-4f19-9000-5f44b04beea6	property_filter	f	string	null	null	Filtro CQL/ECQL para propiedades (ej: poblacion>10000)
58432292-d1bc-422d-a95b-78128d7fe2b5	202a7314-6952-4f19-9000-5f44b04beea6	simplify_geometry	f	boolean	"false"	null	Simplificar geometrías complejas para reducir tamaño
d9c328de-403d-45c9-9cee-bd1d385f3bc7	1fbdb7e0-c9ae-4054-9f8e-bc26de3de2be	url	t	string	\N	\N	\N
9c83a740-b6fe-4884-aa96-ebf0d995df08	1fbdb7e0-c9ae-4054-9f8e-bc26de3de2be	headers	f	json	\N	\N	\N
65c9fcbf-756c-4f59-b6c8-696dc35834b8	1fbdb7e0-c9ae-4054-9f8e-bc26de3de2be	query_params	f	json	\N	\N	\N
8fc43515-814c-44d4-a520-d8bd77651356	1fbdb7e0-c9ae-4054-9f8e-bc26de3de2be	timeout	f	integer	\N	\N	\N
9ec866f9-934c-4fed-b0c8-40d485e512cc	1fbdb7e0-c9ae-4054-9f8e-bc26de3de2be	max_retries	f	integer	\N	\N	\N
4c5b82fe-b307-4a2f-82f4-17343400ecff	7f29b59b-7c09-4ced-bf84-07becd2f4bf9	url	t	string	\N	\N	\N
4b02c35a-6688-41dc-9db1-54c334d8c433	7f29b59b-7c09-4ced-bf84-07becd2f4bf9	rows_selector	t	string	\N	\N	\N
f04fe2bf-339d-4bac-8b94-255021e0c10b	7f29b59b-7c09-4ced-bf84-07becd2f4bf9	pagination_type	f	string	\N	\N	\N
d7c16828-40a9-4d34-94bc-5a3b4ea5233b	7f29b59b-7c09-4ced-bf84-07becd2f4bf9	max_pages	f	integer	\N	\N	\N
e9d37ccd-7e67-4ee2-8d10-8802b8f0a4c2	7f29b59b-7c09-4ced-bf84-07becd2f4bf9	delay_between_requests	f	integer	\N	\N	\N
e0cd5488-902d-4509-9a81-9c53ece6fbd0	7f29b59b-7c09-4ced-bf84-07becd2f4bf9	has_header	f	boolean	\N	\N	\N
f06e0ea8-f4b6-421f-98fe-f4158980c056	7f29b59b-7c09-4ced-bf84-07becd2f4bf9	clean_html	f	boolean	\N	\N	\N
4c43440e-c8ff-485e-953c-5cacc1245af9	202a7314-6952-4f19-9000-5f44b04beea6	tolerance	f	number	"10"	null	Tolerancia para simplificación de geometrías (metros)
783092c8-725c-4886-9805-38c3c7799e95	7631f4de-bc1d-4a14-9f54-85add6bd92fc	wsdl_url	t	string	null	null	URL del archivo WSDL del servicio SOAP
7861bd63-ed12-40c5-a574-3908118a4e34	7631f4de-bc1d-4a14-9f54-85add6bd92fc	operation	t	string	null	null	Nombre de la operación SOAP a invocar
f8a3f443-b207-490e-b502-4b89a28fca7a	7631f4de-bc1d-4a14-9f54-85add6bd92fc	service_name	f	string	null	null	Nombre del servicio en el WSDL (si hay múltiples servicios)
15952d87-187b-4b3e-b27f-37e91b2ec1f5	7631f4de-bc1d-4a14-9f54-85add6bd92fc	port_name	f	string	null	null	Nombre del puerto en el WSDL
e9c15303-d25a-4679-a4e6-1336832a50b4	7631f4de-bc1d-4a14-9f54-85add6bd92fc	username	f	string	null	null	Usuario para autenticación WS-Security
def59840-8af7-4bb3-8fcf-98c9324ba233	7631f4de-bc1d-4a14-9f54-85add6bd92fc	password	f	string	null	null	Contraseña para autenticación WS-Security
bc638f10-723e-46e1-94e7-975108a395da	7631f4de-bc1d-4a14-9f54-85add6bd92fc	timeout	f	integer	"30"	null	Timeout de la petición SOAP en segundos
3fc3d3f2-e36d-4059-b17a-8acbffec87a4	7631f4de-bc1d-4a14-9f54-85add6bd92fc	verify_ssl	f	boolean	"true"	null	Verificar certificados SSL
6210e4bc-d08d-4904-b874-ec6300443e36	d8c425be-ea01-4fa3-9251-16d4e4bd177c	base_url	t	string	null	null	URL base del servicio ContentAPI (ej: https://www.juntadeandalucia.es/ssdigitales/datasets/contentapi/1.0.0/search/)
476f28f6-314c-4c01-893a-957ede61ebee	d8c425be-ea01-4fa3-9251-16d4e4bd177c	dataset_id	t	string	null	null	Identificador del dataset incluyendo extensión (ej: jda_buscador_bienes_inmuebles.atom)
a769197c-d4b0-4796-bc5e-7c4886efdd39	d8c425be-ea01-4fa3-9251-16d4e4bd177c	format	f	enum	"atom"	["atom", "rss"]	Formato del feed: 'atom' (Atom 1.0) o 'rss' (RSS 2.0)
478d55a8-ad89-4174-8218-202b5ca13b01	d8c425be-ea01-4fa3-9251-16d4e4bd177c	page_size	f	integer	"50"	null	Número de resultados por página (parámetro 'size' en la URL)
b6dd68a0-72f0-432c-93bb-f79fb7573d8b	d8c425be-ea01-4fa3-9251-16d4e4bd177c	start_index	f	integer	"0"	null	Índice de inicio para paginación (parámetro 'from' en la URL)
0fea6ce7-d6b4-4ad7-adfc-a0499738aa0a	d8c425be-ea01-4fa3-9251-16d4e4bd177c	sort	f	string	"date:desc"	null	Criterio de ordenación (ej: date:desc, date:asc, relevance)
1259398c-80ca-4e53-9320-2f8208e96694	d8c425be-ea01-4fa3-9251-16d4e4bd177c	source_filter	f	string	"data"	null	Filtro de fuente de datos (parámetro '_source' en la URL)
27307983-14d2-40eb-9f2e-8e295c778072	d8c425be-ea01-4fa3-9251-16d4e4bd177c	namespaces	f	json	null	null	Namespaces XML adicionales para parsing personalizado (JSON con prefijos y URIs)
2678ce6f-513e-4c37-b667-52cfe80dd7c4	d8c425be-ea01-4fa3-9251-16d4e4bd177c	extract_fields	f	json	null	null	Lista de campos a extraer de cada entry ATOM (JSON array). Si no se especifica, extrae todos los campos disponibles.
ef1493b3-d091-499f-8fa3-7d1fd800bffa	d8c425be-ea01-4fa3-9251-16d4e4bd177c	timeout	f	integer	"30"	null	Timeout de la petición HTTP en segundos
4c368f04-cc8a-40a8-9f4e-d5b1cab51e5a	d8c425be-ea01-4fa3-9251-16d4e4bd177c	verify_ssl	f	boolean	"true"	null	Verificar certificados SSL/TLS en peticiones HTTPS
7403cd9f-880a-41fc-b527-aed59dc3f7da	d8c425be-ea01-4fa3-9251-16d4e4bd177c	max_pages	f	integer	null	null	Número máximo de páginas a recuperar. Si no se especifica, recupera todas las páginas disponibles según totalResults.
\.


--
-- Name: alembic_version alembic_version_pkc; Type: CONSTRAINT; Schema: opendata; Owner: -
--

ALTER TABLE ONLY opendata.alembic_version
    ADD CONSTRAINT alembic_version_pkc PRIMARY KEY (version_num);


--
-- Name: application application_name_key; Type: CONSTRAINT; Schema: opendata; Owner: -
--

ALTER TABLE ONLY opendata.application
    ADD CONSTRAINT application_name_key UNIQUE (name);


--
-- Name: application_notification application_notification_pkey; Type: CONSTRAINT; Schema: opendata; Owner: -
--

ALTER TABLE ONLY opendata.application_notification
    ADD CONSTRAINT application_notification_pkey PRIMARY KEY (id);


--
-- Name: application application_pkey; Type: CONSTRAINT; Schema: opendata; Owner: -
--

ALTER TABLE ONLY opendata.application
    ADD CONSTRAINT application_pkey PRIMARY KEY (id);


--
-- Name: dataset artifact_pkey; Type: CONSTRAINT; Schema: opendata; Owner: -
--

ALTER TABLE ONLY opendata.dataset
    ADD CONSTRAINT artifact_pkey PRIMARY KEY (id);


--
-- Name: dataset_subscription artifact_subscription_pkey; Type: CONSTRAINT; Schema: opendata; Owner: -
--

ALTER TABLE ONLY opendata.dataset_subscription
    ADD CONSTRAINT artifact_subscription_pkey PRIMARY KEY (id);


--
-- Name: fetcher fetcher_type_code_key; Type: CONSTRAINT; Schema: opendata; Owner: -
--

ALTER TABLE ONLY opendata.fetcher
    ADD CONSTRAINT fetcher_type_code_key UNIQUE (name);


--
-- Name: fetcher fetcher_type_pkey; Type: CONSTRAINT; Schema: opendata; Owner: -
--

ALTER TABLE ONLY opendata.fetcher
    ADD CONSTRAINT fetcher_type_pkey PRIMARY KEY (id);


--
-- Name: field_metadata field_metadata_pkey; Type: CONSTRAINT; Schema: opendata; Owner: -
--

ALTER TABLE ONLY opendata.field_metadata
    ADD CONSTRAINT field_metadata_pkey PRIMARY KEY (id);


--
-- Name: resource_execution resource_execution_pkey; Type: CONSTRAINT; Schema: opendata; Owner: -
--

ALTER TABLE ONLY opendata.resource_execution
    ADD CONSTRAINT resource_execution_pkey PRIMARY KEY (id);


--
-- Name: resource source_name_key; Type: CONSTRAINT; Schema: opendata; Owner: -
--

ALTER TABLE ONLY opendata.resource
    ADD CONSTRAINT source_name_key UNIQUE (name);


--
-- Name: resource_param source_param_pkey; Type: CONSTRAINT; Schema: opendata; Owner: -
--

ALTER TABLE ONLY opendata.resource_param
    ADD CONSTRAINT source_param_pkey PRIMARY KEY (id);


--
-- Name: resource source_pkey; Type: CONSTRAINT; Schema: opendata; Owner: -
--

ALTER TABLE ONLY opendata.resource
    ADD CONSTRAINT source_pkey PRIMARY KEY (id);


--
-- Name: type_fetcher_params type_fetcher_params_pkey; Type: CONSTRAINT; Schema: opendata; Owner: -
--

ALTER TABLE ONLY opendata.type_fetcher_params
    ADD CONSTRAINT type_fetcher_params_pkey PRIMARY KEY (id);


--
-- Name: field_metadata uq_table_field; Type: CONSTRAINT; Schema: opendata; Owner: -
--

ALTER TABLE ONLY opendata.field_metadata
    ADD CONSTRAINT uq_table_field UNIQUE (table_name, field_name);


--
-- Name: application_notification application_notification_application_id_fkey; Type: FK CONSTRAINT; Schema: opendata; Owner: -
--

ALTER TABLE ONLY opendata.application_notification
    ADD CONSTRAINT application_notification_application_id_fkey FOREIGN KEY (application_id) REFERENCES opendata.application(id);


--
-- Name: application_notification application_notification_artifact_id_fkey; Type: FK CONSTRAINT; Schema: opendata; Owner: -
--

ALTER TABLE ONLY opendata.application_notification
    ADD CONSTRAINT application_notification_artifact_id_fkey FOREIGN KEY (dataset_id) REFERENCES opendata.dataset(id);


--
-- Name: dataset artifact_execution_id_fkey; Type: FK CONSTRAINT; Schema: opendata; Owner: -
--

ALTER TABLE ONLY opendata.dataset
    ADD CONSTRAINT artifact_execution_id_fkey FOREIGN KEY (execution_id) REFERENCES opendata.resource_execution(id) ON DELETE CASCADE;


--
-- Name: dataset artifact_resource_id_fkey; Type: FK CONSTRAINT; Schema: opendata; Owner: -
--

ALTER TABLE ONLY opendata.dataset
    ADD CONSTRAINT artifact_resource_id_fkey FOREIGN KEY (resource_id) REFERENCES opendata.resource(id) ON DELETE CASCADE;


--
-- Name: dataset_subscription artifact_subscription_application_id_fkey; Type: FK CONSTRAINT; Schema: opendata; Owner: -
--

ALTER TABLE ONLY opendata.dataset_subscription
    ADD CONSTRAINT artifact_subscription_application_id_fkey FOREIGN KEY (application_id) REFERENCES opendata.application(id) ON DELETE CASCADE;


--
-- Name: dataset_subscription artifact_subscription_resource_id_fkey; Type: FK CONSTRAINT; Schema: opendata; Owner: -
--

ALTER TABLE ONLY opendata.dataset_subscription
    ADD CONSTRAINT artifact_subscription_resource_id_fkey FOREIGN KEY (resource_id) REFERENCES opendata.resource(id) ON DELETE CASCADE;


--
-- Name: resource_execution resource_execution_resource_id_fkey; Type: FK CONSTRAINT; Schema: opendata; Owner: -
--

ALTER TABLE ONLY opendata.resource_execution
    ADD CONSTRAINT resource_execution_resource_id_fkey FOREIGN KEY (resource_id) REFERENCES opendata.resource(id) ON DELETE CASCADE;


--
-- Name: resource_param resource_param_resource_id_fkey; Type: FK CONSTRAINT; Schema: opendata; Owner: -
--

ALTER TABLE ONLY opendata.resource_param
    ADD CONSTRAINT resource_param_resource_id_fkey FOREIGN KEY (resource_id) REFERENCES opendata.resource(id) ON DELETE CASCADE;


--
-- Name: resource source_fetcher_type_id_fkey; Type: FK CONSTRAINT; Schema: opendata; Owner: -
--

ALTER TABLE ONLY opendata.resource
    ADD CONSTRAINT source_fetcher_type_id_fkey FOREIGN KEY (fetcher_id) REFERENCES opendata.fetcher(id);


--
-- Name: type_fetcher_params type_fetcher_params_fetcher_type_id_fkey; Type: FK CONSTRAINT; Schema: opendata; Owner: -
--

ALTER TABLE ONLY opendata.type_fetcher_params
    ADD CONSTRAINT type_fetcher_params_fetcher_type_id_fkey FOREIGN KEY (fetcher_id) REFERENCES opendata.fetcher(id) ON DELETE CASCADE;


--
-- PostgreSQL database dump complete
--

\unrestrict NcBSyFLimUv4R4mwT0d9xYQKgi1lBfw002XAIPmFeWE8UI1E1GG769v6tWNqBI7

