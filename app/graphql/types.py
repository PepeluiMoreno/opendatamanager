"""
Tipos GraphQL para la API.
"""
import strawberry
from typing import Optional, List


@strawberry.type
class FetcherTypeType:
    """Tipo de fetcher disponible (REST, SOAP, CSV, etc.)"""
    id: str
    code: str
    class_path: str
    description: Optional[str] = None
    params_def: Optional[strawberry.scalars.JSON] = None


@strawberry.type
class TypeFetcherParamType:
    """Parámetro requerido por un tipo de fetcher"""
    id: str
    param_name: str
    required: bool
    data_type: str


@strawberry.type
class ResourceParamType:
    """Parámetro configurado para un resource"""
    id: str
    key: str
    value: str


@strawberry.type
class ResourceType:
    """Fuente de datos configurada"""
    id: str
    name: str
    publisher: str
    target_table: str
    active: bool
    fetcher_type: FetcherTypeType
    params: List[ResourceParamType]


@strawberry.type
class ApplicationType:
    """Aplicación suscrita al sistema"""
    id: str
    name: str
    description: Optional[str] = None
    models_path: str
    subscribed_projects: List[str]
    active: bool


@strawberry.input
class ResourceParamInput:
    """Input para parámetros de Resource"""
    key: str
    value: str


@strawberry.input
class CreateResourceInput:
    """Input para crear un nuevo Resource"""
    name: str
    publisher: str
    target_table: str
    fetcher_type_id: str
    params: List[ResourceParamInput]
    active: bool = True


@strawberry.input
class UpdateResourceInput:
    """Input para actualizar un Resource"""
    name: Optional[str] = None
    publisher: Optional[str] = None
    target_table: Optional[str] = None
    fetcher_type_id: Optional[str] = None
    params: Optional[List[ResourceParamInput]] = None
    active: Optional[bool] = None


@strawberry.input
class CreateFetcherTypeInput:
    """Input para crear un nuevo FetcherType"""
    code: str
    class_path: str
    description: Optional[str] = None


@strawberry.input
class UpdateFetcherTypeInput:
    """Input para actualizar un FetcherType"""
    code: Optional[str] = None
    class_path: Optional[str] = None
    description: Optional[str] = None


@strawberry.type
class ExecutionResult:
    """Resultado de ejecutar un Resource"""
    success: bool
    message: str
    resource_id: Optional[str] = None
    sample_data: Optional[strawberry.scalars.JSON] = None


@strawberry.type
class FieldMetadataType:
    """Metadata de un campo para tooltips"""
    id: str
    table_name: str
    field_name: str
    label: Optional[str] = None
    help_text: Optional[str] = None
    placeholder: Optional[str] = None
