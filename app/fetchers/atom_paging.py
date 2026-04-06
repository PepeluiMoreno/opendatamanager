import requests
import xmltodict
import json
import time
from typing import Generator, List, Dict, Any, Optional
from app.fetchers.base import BaseFetcher, RawData, ParsedData, DomainData

class AtomPagingFetcher(BaseFetcher):
    """
    Fetcher especializado en canales Atom con paginación (rel="next").
    Ideal para la Plataforma de Contratación del Sector Público (PLACSP).
    """

    @staticmethod
    def _text(val) -> Optional[str]:
        """Extract plain text from an xmltodict value (may be a dict with @attrs and #text)."""
        if val is None:
            return None
        if isinstance(val, dict):
            return val.get("#text")
        return str(val)

    @staticmethod
    def _normalize_entry(entry: Dict) -> Dict:
        # --- Atom envelope fields ---
        link = entry.get("link", {})
        result: Dict[str, Any] = {
            "id": entry.get("id"),
            "title": entry.get("title"),
            "updated": entry.get("updated"),
            "link": link.get("@href") if isinstance(link, dict) else None,
        }

        # --- CODICE fields (PLACSP CODICE v3: directly on entry, no <content> wrapper) ---
        cfs = entry.get("cac-place-ext:ContractFolderStatus") or {}
        if not cfs:
            # Fallback: some feeds wrap it in <content type="text/xml">
            content = entry.get("content") or {}
            cfs = content.get("cac-place-ext:ContractFolderStatus") or {}

        if not cfs:
            result["raw_xml_content"] = entry
            return result

        t = AtomPagingFetcher._text  # shorthand

        result["expediente"] = t(cfs.get("cbc:ContractFolderID"))
        result["estado"] = t(cfs.get("cbc-place-ext:ContractFolderStatusCode"))

        # Órgano contratante (PLACSP uses cac-place-ext: prefix)
        lcp = cfs.get("cac-place-ext:LocatedContractingParty") or cfs.get("cac:LocatedContractingParty") or {}
        party = lcp.get("cac:Party", {}) if isinstance(lcp, dict) else {}

        party_name = party.get("cac:PartyName", {}) if isinstance(party, dict) else {}
        result["organo"] = t(party_name.get("cbc:Name")) if isinstance(party_name, dict) else None

        party_ids = party.get("cac:PartyIdentification", []) if isinstance(party, dict) else []
        if isinstance(party_ids, dict):
            party_ids = [party_ids]
        nif_organo = dir3_organo = None
        for pid in party_ids:
            id_elem = pid.get("cbc:ID", {})
            scheme = id_elem.get("@schemeName", "") if isinstance(id_elem, dict) else ""
            val = t(id_elem)
            if scheme == "NIF":
                nif_organo = val
            elif scheme == "DIR3":
                dir3_organo = val
            elif nif_organo is None:
                nif_organo = val
        result["nif_organo"] = nif_organo
        result["dir3_organo"] = dir3_organo

        # Proyecto
        pp = cfs.get("cac:ProcurementProject", {})
        if isinstance(pp, dict):
            result["objeto"] = t(pp.get("cbc:Name"))
            result["tipo_contrato"] = t(pp.get("cbc:TypeCode"))

            budget = pp.get("cac:BudgetAmount", {})
            if isinstance(budget, dict):
                result["presupuesto_sin_iva"] = t(budget.get("cbc:TaxExclusiveAmount"))
                result["presupuesto_con_iva"] = t(budget.get("cbc:TotalAmount"))
            else:
                result["presupuesto_sin_iva"] = result["presupuesto_con_iva"] = None

            loc = pp.get("cac:RealizedLocation", {})
            result["lugar_ejecucion"] = t(loc.get("cbc:CountrySubentityCode")) if isinstance(loc, dict) else None

            cpv_elem = pp.get("cac:RequiredCommodityClassification", {})
            if isinstance(cpv_elem, list):
                cpv_elem = cpv_elem[0] if cpv_elem else {}
            result["cpv"] = t(cpv_elem.get("cbc:ItemClassificationCode")) if isinstance(cpv_elem, dict) else None
        else:
            result.update({"objeto": None, "tipo_contrato": None, "presupuesto_sin_iva": None,
                           "presupuesto_con_iva": None, "lugar_ejecucion": None, "cpv": None})

        # Procedimiento
        tp = cfs.get("cac:TenderingProcess", {})
        result["procedimiento"] = t(tp.get("cbc:ProcedureCode")) if isinstance(tp, dict) else None

        # Resultado adjudicación (puede ser lista si hay varios lotes)
        tr = cfs.get("cac:TenderResult")
        if isinstance(tr, list):
            tr = tr[0] if tr else None
        if isinstance(tr, dict):
            result["resultado"] = t(tr.get("cbc:ResultCode"))
            result["fecha_adjudicacion"] = t(tr.get("cbc:AwardDate"))
            result["num_ofertas"] = t(tr.get("cbc:ReceivedTenderQuantity"))

            atp = tr.get("cac:AwardedTenderedProject", {})
            lmt = atp.get("cac:LegalMonetaryTotal", {}) if isinstance(atp, dict) else {}
            result["importe_adjudicacion"] = t(lmt.get("cbc:TaxExclusiveAmount")) if isinstance(lmt, dict) else None

            wp = tr.get("cac:WinningParty", {})
            if isinstance(wp, list):
                wp = wp[0] if wp else {}
            if isinstance(wp, dict):
                wp_name = wp.get("cac:PartyName", {})
                result["adjudicatario"] = t(wp_name.get("cbc:Name")) if isinstance(wp_name, dict) else None
                wp_id = wp.get("cac:PartyIdentification", {})
                result["nif_adjudicatario"] = t(wp_id.get("cbc:ID")) if isinstance(wp_id, dict) else None
            else:
                result["adjudicatario"] = result["nif_adjudicatario"] = None
        else:
            result.update({"resultado": None, "fecha_adjudicacion": None, "num_ofertas": None,
                           "importe_adjudicacion": None, "adjudicatario": None, "nif_adjudicatario": None})

        result["raw_xml_content"] = entry
        return result

    def stream(self) -> Generator[List[Dict], None, None]:
        """Yields one page of normalized Atom entries at a time.

        Si el parámetro 'anio' está presente, filtra las entradas por ese año
        usando el campo 'updated' del Atom envelope (formato ISO 8601).
        Como el feed va en orden cronológico inverso, para el stream en cuanto
        detecta una entrada con 'updated' anterior al año buscado.

        max_pages: si no se especifica (o 0), itera sin límite hasta agotar el feed.
        """
        url = self.params.get("url")
        _mp = self.params.get("max_pages")
        max_pages = int(_mp) if _mp else None   # None = sin límite
        timeout = int(self.params.get("timeout", 30))
        headers = self.params.get("headers") or {}
        if isinstance(headers, str):
            headers = json.loads(headers)

        anio = self.params.get("anio")
        mes  = self.params.get("mes")   # "1"–"12" o None

        # Calcular rango como prefijo YYYY-MM (7 chars) para comparación de strings
        if anio and mes:
            month_prefix = f"{anio}-{int(mes):02d}"   # e.g. "2025-03"
            range_start  = month_prefix                # stop cuando updated[:7] < range_start
            range_end    = month_prefix                # skip cuando updated[:7] > range_end
            range_label  = month_prefix
        elif anio:
            range_start  = f"{anio}-01"               # "2025-01"
            range_end    = f"{anio}-12"               # "2025-12"
            range_label  = anio
        else:
            range_start = range_end = range_label = None

        # Resume protocol: start from saved URL if resuming
        resume_state = self.params.get("_resume_state") or {}
        if isinstance(resume_state, str):
            import json as _json; resume_state = _json.loads(resume_state)
        current_url = resume_state.get("resume_url") or url
        pages_fetched = int(resume_state.get("pages_fetched", 0))
        if pages_fetched:
            print(f"  [FETCH] Resuming from page {pages_fetched + 1}: {current_url}")

        while current_url and (max_pages is None or pages_fetched < max_pages):
            print(f"  [FETCH] Descargando página Atom: {current_url}")

            response = self._request(None, "GET", current_url,
                                      headers=headers, timeout=timeout)

            data = xmltodict.parse(response.text)
            feed = data.get("feed", {})

            entries = feed.get("entry", [])
            if isinstance(entries, dict):
                entries = [entries]

            normalized = [self._normalize_entry(e) for e in entries]

            # Determine next_url BEFORE yielding so we can set current_state first.
            # If FetcherManager breaks at yield, code after yield won't run.
            links = feed.get("link", [])
            if isinstance(links, dict):
                links = [links]
            next_url = None
            for link in links:
                if link.get("@rel") == "next":
                    next_url = link.get("@href")
                    break

            # Set savepoint state before any yield on this iteration
            self.current_state = {"resume_url": next_url, "pages_fetched": pages_fetched + 1}

            if range_start:
                page_out = []
                stop = False
                for rec in normalized:
                    ym = (rec.get("updated") or "")[:7]   # YYYY-MM
                    if ym < range_start:
                        stop = True
                        break
                    if ym <= range_end:
                        page_out.append(rec)
                    # ym > range_end → entrada más reciente que el rango, la saltamos
                if page_out:
                    yield page_out
                if stop:
                    print(f"  [FETCH] Rango {range_label}: entrada anterior al rango — parando.")
                    break
            else:
                if normalized:
                    yield normalized

            current_url = next_url
            pages_fetched += 1
            if current_url:
                time.sleep(1)

    def fetch(self) -> RawData:
        """Accumulates raw entries — used by execute() for backwards compat."""
        all_entries = []
        url = self.params.get("url")
        max_pages = int(self.params.get("max_pages", 10))
        timeout = int(self.params.get("timeout", 30))
        headers = self.params.get("headers", {})
        if isinstance(headers, str):
            headers = json.loads(headers)

        current_url = url
        pages_fetched = 0
        while current_url and pages_fetched < max_pages:
            response = requests.get(current_url, headers=headers, timeout=timeout)
            response.raise_for_status()
            data = xmltodict.parse(response.text)
            feed = data.get("feed", {})
            entries = feed.get("entry", [])
            if isinstance(entries, dict):
                entries = [entries]
            all_entries.extend(entries)
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
            if current_url:
                time.sleep(1)
        return all_entries

    def parse(self, raw: RawData) -> ParsedData:
        return raw

    def normalize(self, parsed: ParsedData) -> DomainData:
        return [self._normalize_entry(e) for e in parsed]
