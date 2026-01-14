"""
CSV Fetcher implementation
"""
import requests
import pandas as pd
from app.fetchers.base import BaseFetcher, RawData, ParsedData, DomainData

class CSVFetcher(BaseFetcher):
    """Fetcher para endpoints que devuelven archivos CSV"""
    def fetch(self) -> RawData:
        """Realiza el request HTTP y retorna el contenido CSV crudo"""
        url = self.params.get("url")
        if not url:
            raise ValueError("El parámetro 'url' es obligatorio para CSVFetcher")

        response = requests.get(url)
        response.raise_for_status()
        if response.status_code == 200:
            # Leer el contenido como un DataFrame de pandas
            df = pd.read_csv(pd.compat.StringIO(response.text))
        else:
            raise ValueError("Error al obtener el archivo CSV")

        return df