import requests
import xmltodict
import json
import time
from typing import List, Dict, Any, Optional
from app.fetchers.base import BaseFetcher, RawData, ParsedData, DomainData

class AtomPagingFetcher(BaseFetcher):
    """
    Fetcher especializado en canales Atom con paginación (rel="next").
    Ideal para la Plataforma de Contratación del Sector Público (PLACSP).
    """

    def fetch(self) -> RawData:
        """
        Realiza la descarga recursiva de todas las páginas Atom.
        """
        url = self.params.get("url")
        max_pages = int(self.params.get("max_pages", 10)) # Límite de seguridad
        timeout = int(self.params.get("timeout", 30))
        headers = self.params.get("headers", {})
        
        if isinstance(headers, str):
            headers = json.loads(headers)

        all_entries = []
        current_url = url
        pages_fetched = 0

        while current_url and pages_fetched < max_pages:
            print(f"  [FETCH] Descargando página Atom: {current_url}")
            response = requests.get(current_url, headers=headers, timeout=timeout)
            response.raise_for_status()
            
            # Parsear XML a dict
            data = xmltodict.parse(response.text)
            feed = data.get("feed", {})
            
            # Extraer entradas (pueden ser una lista o un solo dict)
            entries = feed.get("entry", [])
            if isinstance(entries, dict):
                entries = [entries]
            all_entries.extend(entries)
            
            # Buscar enlace 'next'
            links = feed.get("link", [])
            if isinstance(links, dict):
                links = [links]
            
            next_url = None
            for link in links:
                if link.get("@rel") == "next":
                    next_url = link.get("@href")
                    break
            
            current_url = next_url
            pages_fetched += 1
            
            # Pequeño delay para no saturar el servidor
            if current_url:
                time.sleep(1)

        return all_entries

    def parse(self, raw: RawData) -> ParsedData:
        """
        El raw ya es una lista de dicts (entries) extraídos en fetch().
        """
        return raw

    def normalize(self, parsed: ParsedData) -> DomainData:
        """
        Normalización básica. Se puede extender para aplanar el XML de la PLACSP.
        """
        normalized = []
        for entry in parsed:
            # Aplanamos un poco la estructura de Atom para que sea más usable
            item = {
                "id": entry.get("id"),
                "title": entry.get("title"),
                "updated": entry.get("updated"),
                "summary": entry.get("summary", {}).get("#text") if isinstance(entry.get("summary"), dict) else entry.get("summary"),
                "link": entry.get("link", {}).get("@href") if isinstance(entry.get("link"), dict) else None,
                "raw_xml_content": entry # Mantenemos el resto por si acaso
            }
            normalized.append(item)
        return normalized
