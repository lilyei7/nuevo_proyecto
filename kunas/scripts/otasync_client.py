"""Cliente ligero para OTASync Public API.

Funciones:
- login(token, username, password, remember=0) -> devuelve pkey o None
- logout(key) -> devuelve response object
- edit_one_signal(key, player_id) -> devuelve response object

El cliente intenta parsear JSON; si la respuesta viene como text/html busca el campo "pkey" con regex.
"""
from typing import Optional, Tuple, Any, Dict
import requests
import re
import json

BASE_URL = "https://app.otasync.me/api"
DEFAULT_HEADERS = {"Content-Type": "application/json"}


class OTASyncClient:
    def __init__(self, base_url: str = BASE_URL, session: Optional[requests.Session] = None):
        self.base_url = base_url.rstrip('/')
        self.session = session or requests.Session()
        self.session.headers.update(DEFAULT_HEADERS)

    def _post(self, path: str, json: Dict[str, Any]) -> requests.Response:
        url = f"{self.base_url}/{path.lstrip('/')}"
        resp = self.session.post(url, json=json, timeout=15)
        # Don't raise for status automatically to handle errors gracefully
        return resp

    def _extract_pkey_from_text(self, text: str) -> Optional[str]:
        # Intenta parsear JSON si existe
        try:
            data = requests.utils.json.loads(text)
            # posibilidad que userInf.pkey exista
            if isinstance(data, dict):
                if "userInf" in data and isinstance(data["userInf"], dict):
                    return data["userInf"].get("pkey")
                if "pkey" in data:
                    return data.get("pkey")
        except Exception:
            pass
        # Fallback: buscar con regex
        m = re.search(r'"pkey"\s*:\s*"([0-9a-fA-F]+)"', text)
        if m:
            return m.group(1)
        return None

    def login(self, token: str, username: str, password: str, remember: int = 0) -> Tuple[Optional[str], requests.Response]:
        """Hace POST a /user/auth/login y devuelve (pkey, response).
        pkey puede venir en JSON o estar embebido en HTML/text.
        """
        body = {"token": token, "username": username, "password": password, "remember": remember}
        resp = self._post("user/auth/login", json=body)

        # intentar parseo JSON
        try:
            data = resp.json()
            # estructuras observadas: userInf.pkey o pkey
            if isinstance(data, dict):
                if "userInf" in data and isinstance(data["userInf"], dict):
                    return data["userInf"].get("pkey"), resp
                if "pkey" in data:
                    return data.get("pkey"), resp
        except ValueError:
            # no JSON
            pass

        # parsear texto
        pkey = self._extract_pkey_from_text(resp.text)
        return pkey, resp

    def _extract_properties_from_text(self, text: str) -> Optional[list]:
        """Intentar extraer lista `properties` desde texto (JSON embebido o HTML)."""
        # intentar parsear JSON
        try:
            data = requests.utils.json.loads(text)
            if isinstance(data, dict) and "properties" in data and isinstance(data["properties"], list):
                return data["properties"]
        except Exception:
            pass
        # Fallback: buscar el primer '[' tras la clave "properties" y extraer el array con balanceo de corchetes
        idx = text.find('"properties"')
        if idx == -1:
            return None
        start = text.find('[', idx)
        if start == -1:
            return None
        depth = 0
        end = None
        for i in range(start, len(text)):
            if text[i] == '[':
                depth += 1
            elif text[i] == ']':
                depth -= 1
                if depth == 0:
                    end = i
                    break
        if end is None:
            return None
        arr_text = text[start:end+1]
        try:
            return json.loads(arr_text)
        except Exception:
            return None

    def get_properties_via_login(self, token: str, username: str, password: str, remember: int = 0) -> Tuple[Optional[list], requests.Response]:
        """Realiza login y devuelve (properties_list or None, response).
        Las properties suelen venir en la respuesta del login bajo la clave `properties`.
        """
        pkey, resp = self.login(token, username, password, remember=remember)
        # intentar extraer properties desde JSON
        try:
            data = resp.json()
            if isinstance(data, dict) and "properties" in data and isinstance(data["properties"], list):
                return data["properties"], resp
        except Exception:
            pass

        # intentar extraer desde texto
        props = self._extract_properties_from_text(resp.text)
        return props, resp

    def extract_properties_from_response(self, resp: requests.Response) -> Optional[list]:
        """Extrae la lista `properties` a partir de un objeto Response ya obtenido.
        Intenta JSON primero, luego texto embebido.
        """
        try:
            data = resp.json()
            if isinstance(data, dict) and "properties" in data and isinstance(data["properties"], list):
                return data["properties"]
        except Exception:
            pass
        return self._extract_properties_from_text(resp.text)

    def logout(self, key: str) -> requests.Response:
        body = {"key": key}
        return self._post("user/auth/logout", json=body)

    def edit_one_signal(self, key: str, player_id: str) -> requests.Response:
        body = {"key": key, "player_id": player_id}
        return self._post("user/edit/one_signal", json=body)

    def update_boards_prices(self, token: str, key: str, id_properties: int, boards: list) -> requests.Response:
        """POST /boards/edit/boards
        Updates prices for multiple boards. Returns the Response object.
        Body requires token, key, id_properties and boards (list of dicts).
        """
        body = {"token": token, "key": key, "id_properties": id_properties, "boards": boards}
        return self._post("boards/edit/boards", json=body)

    def update_prices(self, token: str, key: str, id_properties: int, id_pricing_plans: int,
                      dfrom: str, dto: str, rooms: list, variation_type: int = 0, weekdays: list = None) -> requests.Response:
        """POST /prices/edit/prices
        Update room prices for a date range.

        rooms: list of {"id_room_types": int, "value": number}
        variation_type: 0 means set to value
        weekdays: optional list of 7 integers (1/0) starting Sunday
        """
        body = {
            "token": token,
            "key": key,
            "id_properties": id_properties,
            "id_pricing_plans": id_pricing_plans,
            "dfrom": dfrom,
            "dto": dto,
            "rooms": rooms,
            "variation_type": variation_type,
        }
        if weekdays is not None:
            body["weekdays"] = weekdays
        return self._post("prices/edit/prices", json=body)

    def update_calendar(self, token: str, key: str, id_properties: int, dates_data: list) -> requests.Response:
        """POST /calendar/edit/calendar
        Update calendar data including prices per date.
        dates_data: list of {"date": "YYYY-MM-DD", "id_room_types": int, "price": number, ...}
        """
        body = {
            "token": token,
            "key": key,
            "id_properties": id_properties,
            "dates": dates_data
        }
        return self._post("calendar/edit/calendar", json=body)

    def get_calendar(self, token: str, key: str, id_properties: int, date: str = None, id_pricing_plans: int = None,
                     id_restriction_plans: int = None, avail: int = None, price: int = None, min: int = None,
                     days: int = None, scroll: int = None, type: str = None) -> requests.Response:
        """POST /calendar/data/calendar
        Retrieves calendar data. Optional filters may be provided.
        """
        body = {"token": token, "key": key, "id_properties": id_properties}
        # add optional parameters if provided
        if date is not None:
            body["date"] = date
        if id_pricing_plans is not None:
            body["id_pricing_plans"] = id_pricing_plans
        if id_restriction_plans is not None:
            body["id_restriction_plans"] = id_restriction_plans
        if avail is not None:
            body["avail"] = avail
        if price is not None:
            body["price"] = price
        if min is not None:
            body["min"] = min
        if days is not None:
            body["days"] = days
        if scroll is not None:
            body["scroll"] = scroll
        if type is not None:
            body["type"] = type

        return self._post("calendar/data/calendar", json=body)


if __name__ == "__main__":
    print("OTASyncClient module. Import and use in scripts/tests.")
