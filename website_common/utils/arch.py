# Copyright 2026 Soltein SA. de CV.
# License LGPL-3 or later (http://www.gnu.org/licenses/lgpl.html)

from typing import Any, Dict, List

from lxml import etree
from odoo import _, models
from odoo.api import Environment
from odoo.fields import Field
from odoo.http import request
from odoo.tools.safe_eval import safe_eval


class SearchViewParser:
    """Parser para arch de search views de Odoo 17.0"""

    def __init__(self, arch: str):
        """
        Args:
            arch: String XML con la definición de la vista
        """
        self.arch = arch
        self.root = etree.fromstring(arch.encode("utf-8"))

        # Validar que existe un elemento search
        self._validate_search_element()

    def parse(self, **kwargs) -> Dict[str, Any]:
        """
        Parsea la vista en secciones organizadas

        Returns:
            Diccionario con las secciones de la vista
        """
        return {
            "fields": self._parse_fields(**kwargs),
            "filters": self._parse_filters(**kwargs),
            "groups": self._parse_groups(),
            "separators": self._parse_separators(),
            "search_panel": self._parse_search_panel(),
        }

    def _validate_search_element(self):
        """
        Valida que el elemento search sea el root del XML

        Raises:
            ValueError: Si el elemento raíz no es 'search'
        """
        if self.root.tag != "search":
            raise ValueError(
                "El elemento raíz debe ser 'search', encontrado: '{}'".format(
                    self.root.tag
                )
            )

    def _parse_fields(self, **kwargs) -> List[Dict[str, Any]]:
        """Extrae los campos de búsqueda"""
        fields = []
        include_fields_on_search_panel = kwargs.get(
            "include_fields_on_search_panel", False
        )

        # Si include_fields_on_search_panel es True, excluir campos dentro de searchpanel
        if include_fields_on_search_panel:
            xpath_query = ".//field[not(ancestor::searchpanel)]"
        else:
            xpath_query = ".//field"

        for field in self.root.xpath(xpath_query):
            field_data = {
                "name": field.get("name"),
                "string": field.get("string"),
                "filter_domain": field.get("filter_domain"),
                "operator": field.get("operator"),
                "domain": field.get("domain"),
                "context": field.get("context"),
            }
            # Limpiar valores None
            fields.append({k: v for k, v in field_data.items() if v is not None})
        return fields

    def _parse_filters(self, **kwargs) -> List[Dict[str, Any]]:
        """Extrae los filtros predefinidos"""
        filters = []
        include_first_level_filters_only = kwargs.get(
            "include_first_level_filters_only", False
        )

        # Si include_first_level_filters_only es True, solo obtener filtros hijos directos de search
        if include_first_level_filters_only:
            xpath_query = "./filter"
        else:
            xpath_query = ".//filter"

        for filter_elem in self.root.xpath(xpath_query):
            filter_data = {
                "name": filter_elem.get("name"),
                "string": filter_elem.get("string"),
                "domain": filter_elem.get("domain"),
                "context": filter_elem.get("context"),
                "help": filter_elem.get("help"),
                "invisible": filter_elem.get("invisible"),
                "date": filter_elem.get("date"),  # Para filtros de fecha
                "default_period": filter_elem.get("default_period"),
            }
            filters.append({k: v for k, v in filter_data.items() if v is not None})
        return filters

    def _parse_groups(self) -> List[Dict[str, Any]]:
        """Extrae grupos de filtros (Group By)"""
        groups = []
        for group in self.root.xpath(".//group"):
            group_data = {
                "expand": group.get("expand"),
                "string": group.get("string"),
                "filters": [],
            }
            # Obtener filtros dentro del grupo
            for filter_elem in group.xpath("./filter"):
                filter_info = {
                    "name": filter_elem.get("name"),
                    "string": filter_elem.get("string"),
                    "context": filter_elem.get("context"),
                    "domain": filter_elem.get("domain"),
                }
                group_data["filters"].append(
                    {k: v for k, v in filter_info.items() if v is not None}
                )
            groups.append(group_data)
        return groups

    def _parse_separators(self) -> List[Dict[str, Any]]:
        """Extrae separadores"""
        separators = []
        for sep in self.root.xpath(".//separator"):
            sep_data = {
                "string": sep.get("string"),
                "invisible": sep.get("invisible"),
            }
            separators.append({k: v for k, v in sep_data.items() if v is not None})
        return separators

    def _parse_search_panel(self) -> Dict[str, Any]:
        """Extrae la configuración del search panel"""
        search_panel = self.root.find("./searchpanel")
        if search_panel is None:
            return {}

        panel_data = {"fields": []}

        for field in search_panel.xpath("./field"):
            field_data = {
                "name": field.get("name"),
                "string": field.get("string"),
                "select": field.get("select"),  # multi o one
                "icon": field.get("icon"),
                "color": field.get("color"),
                "enable_counters": field.get("enable_counters"),
                "expand": field.get("expand"),
                "domain": field.get("domain"),
            }
            panel_data["fields"].append(
                {k: v for k, v in field_data.items() if v is not None}
            )

        return panel_data


class FilterBarParser:
    def __init__(self, arch: dict, model_name: str, env: Environment | None):
        """
        Initializes the FilterBarParser.

        Args:
            arch (dict): The parsed architecture of the search view.
            model_name (str): The technical name of the Odoo model.
            env (Environment | None): The Odoo environment instance. If None, uses the current request environment.

        Side Effects:
            Sets instance variables and validates that the model exists in the environment.
        """
        self.arch = arch
        self.env = env or request.env
        self.model_name = model_name

        # Validar que el modelo exista en el environment
        self._validate_model_exists()

    def _validate_model_exists(self):
        """
        Valida que el modelo especificado exista en el environment

        Raises:
            ValueError: Si el modelo no existe en el registry
        """
        if self.model_name not in self.env.registry:
            raise ValueError(
                f"The model '{self.model_name}' does not exist in the registry"
            )

    def parse(self, search: str | None = None, **kwargs) -> dict:
        """
        Parses the filter bar architecture and returns mappings for group by and input fields.

        Args:
            search (str, optional): The search string to use in domain construction.

        Returns:
            dict: Contains group by mappings, input mappings, and input field definitions.
        """
        mapping, group = self._parse_group_by_mapping()
        return {
            "group_by_mapping": mapping,
            "group_by": group,
            "inputs_mapping": self._parse_inputs_mapping(search),
            "inputs": self._parse_inputs(),
            "filters": self._parse_filters(),
        }

    def _parse_filters(self) -> tuple[dict[str, Any], dict[str, Any]]:
        """
        Parses filter definitions from the search view architecture.

        Returns:
            tuple[dict[str, Any], dict[str, Any]]:
                - filters: Dictionary mapping field keys to filter info (label, domain, sequence).
                - date_filters: Dictionary mapping field keys to date filter info (label, name).
        """
        filters = {}
        date_filters = {}
        sequence = 1
        for filter_ in self.arch.get("filters", []):
            if "name" not in filter_:
                continue
            field_key = self._get_field_name_key(filter_["name"])
            field_title = self._get_field_title(filter_["name"])
            field = self._get_field_definition(
                filter_["date"] if "date" in filter_ else filter_["name"]
            )
            if (
                "domain" not in filter_
                and "date" in filter_
                and field
                and field.type in ["date", "datetime"]
            ):
                date_filters[field_key] = {
                    "label": filter_["string"] if "string" in filter_ else field_title,
                    "name": filter_["date"],
                    "sequence": sequence,
                }
            else:
                filters[field_key] = {
                    "label": filter_["string"] if "string" in filter_ else field_title,
                    "sequence": sequence,
                }
                try:
                    filters[field_key]["domain"] = safe_eval(filter_["domain"])
                except Exception:
                    filters[field_key]["domain"] = []
            sequence += 1
        return filters, date_filters

    def _parse_group_by_mapping(self) -> tuple[dict, dict]:
        """
        Parses filter and group definitions to build mappings for group by functionality.

        Returns:
            tuple[dict, dict]:
                - mapping: Maps normalized field keys to their group_by values.
                - group: Maps normalized field keys to a dict with label and input key.
        """
        mapping = {}
        group = {}

        def map_values(fd):
            """
            Maps filter/group definitions to normalized field keys.

            Args:
                fd (dict): Filter or group definition containing 'context' and optionally 'group_by'.

            Side Effects:
                Updates the `mapping` and `group` dictionaries with field key, group_by value, and label.
            """
            if "context" in fd and "group_by" in fd["context"]:
                try:
                    context = safe_eval(fd["context"])
                except Exception:
                    context = {}
                field_key = self._get_field_name_key(context["group_by"])
                mapping[field_key] = context["group_by"]
                group[field_key] = {
                    "label": fd.get(
                        "string", self._get_field_title(context["group_by"])
                    ),
                    "input": field_key,
                }

        for filter_definition in self.arch["filters"]:
            map_values(filter_definition)
        for group_definition in self.arch["groups"]:
            for filter_definition in group_definition["filters"]:
                map_values(filter_definition)
        return mapping, group

    @staticmethod
    def _get_field_name_key(field_name: str) -> str:
        """
        Returns a normalized field name key by removing the 'x_' prefix and '_id', '_ids' suffix,
        then stripping any leading/trailing whitespace.

        Args:
            field_name (str): The technical field name.

        Returns:
            str: The normalized field name key.
        """
        return (
            field_name.removeprefix("x_")
            .removesuffix("_id")
            .removesuffix("_ids")
            .strip()
        )

    def _get_field_title(self, field_name: str) -> str:
        """
        Retrieves the field description (title) for a given field name in the current model.

        Args:
            field_name (str): The technical name of the field.

        Returns:
            str: The field's description in the current language, or the field name if not found.
        """
        field_obj = (
            self.env["ir.model.fields"]
            .sudo()
            .search(
                [("model", "=", self._get_model()._name), ("name", "=", field_name)]
            )
        )
        if field_obj:
            return field_obj.with_context(
                lang=self._get_environment_lang()
            ).field_description
        return field_name

    def _parse_inputs_mapping(self, search: str | None = None) -> dict:
        """
        Constructs a mapping of input fields to their search domains.

        Args:
            search (str): The search string to use in domain construction.

        Returns:
            dict: A mapping where each key is a tuple ('all', field_key) and the value is the domain for that field.
        """
        result = {}
        for field_definition in self.arch["fields"]:
            field = self._get_field_definition(field_definition["name"])
            if field.type in ["date", "datetime"]:
                continue
            field_key = self._get_field_name_key(field_definition["name"])
            result[("all", field_key)] = self._get_domain_from_field_definition(
                field_definition, search
            )
        return result

    def _get_domain_from_field_definition(
        self, field_definition: dict, search: str | None = None
    ) -> list:
        """
        Returns the domain for a field definition based on its type and search value.

        If the field definition contains a domain, it is returned.
        Otherwise, for many2one fields, the domain is constructed to search by display_name.
        For other field types, the domain is constructed to search by the field name.

        Args:
            field_definition (dict): The field definition dictionary.
            search (str): The search string.

        Returns:
            list: The domain for the field.
        """
        domain = field_definition.get("filter_domain", [])

        def base_domain():
            """Build base domain for field filtering with ilike operator."""
            field = self._get_field_definition(field_definition["name"])
            name = (
                f"{field_definition['name']}.name"
                if field.type == "many2one"
                else field_definition["name"]
            )
            return [(name, "ilike", search or "")]

        if not domain:
            domain = base_domain()
        elif isinstance(domain, str):
            try:
                # Usar safe_eval para evaluación segura según estándares de Odoo 17.0
                domain = safe_eval(domain, {"self": search or ""})
            except Exception:
                domain = base_domain()
        return domain

    def _get_field_definition(self, field_name: str) -> Field:
        """
        Returns the field definition object for the given field name in the current model.

        Args:
            field_name (str): The technical name of the field.

        Returns:
            Field: The Odoo field object, or None if not found.
        """
        return self._get_model()._fields.get(field_name)

    def _parse_inputs(self) -> dict:
        """
        Parses the input fields from the search view architecture.

        Iterates over the field definitions in the architecture, normalizes the field name,
        retrieves the field title, and constructs a mapping for each input field.

        Returns:
            dict: A mapping of normalized field keys to their label and input key.
        """
        result = {}
        for field_definition in self.arch["fields"]:
            if "name" not in field_definition:
                continue
            field_key = self._get_field_name_key(field_definition["name"])
            field_title = self._get_field_title(field_definition["name"])
            result[field_key] = {
                "label": _("Search by {}").format(field_title),
                "input": field_key,
            }
        return result

    def _get_environment_lang(self) -> str:
        """
        Returns the language code from the environment context.

        Returns:
            str: The language code (e.g., 'en_US'). Defaults to 'en_US' if not set.
        """
        return (
            self.env.context.get("lang", "en_US")
            if self.env and self.env.context
            else "en_US"
        )

    def _get_model(self) -> models.Model:
        """
        Returns the Odoo model instance for the specified model name,
        using the current environment and language context.
        """
        return self.env[self.model_name].with_context(lang=self._get_environment_lang())
