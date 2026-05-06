# -*- coding: utf-8 -*-
# Copyright 2026 Soltein SA. de CV.
# License LGPL-3 or later (http://www.gnu.org/licenses/lgpl.html)
from babel import Locale
from odoo import models


class ResLang(models.Model):
    _inherit = "res.lang"

    def get_babel_month_names(
        self, code: str = None, format: str = "abbreviated"
    ) -> dict:
        """
        Obtiene los nombres de los meses en un formato específico para un idioma dado.

        :param code: Código del idioma (opcional). Por defecto es 'es_MX'.
        :type code: str
        :param format: Formato de los nombres de los meses ('abbreviated', 'narrow', 'wide'). Por defecto es 'abbreviated'.
        :type format: str
        :return: Un diccionario con los nombres de los meses en el formato especificado.
        :rtype: dict
        """
        return Locale.parse(
            code or self.env.context.get("lang") or self.env.user.lang or "es_MX"
        ).months["format"][format]

    def get_babel_day_names(
        self, code: str = "es_MX", format: str = "abbreviated"
    ) -> dict:
        """
        Obtiene los nombres de los días de la semana en un formato específico para un idioma dado.

        :param code: Código del idioma (opcional). Por defecto es 'es_MX'.
        :type code: str
        :param format: Formato de los nombres de los días ('abbreviated', 'narrow', 'wide'). Por defecto es 'abbreviated'.
        :type format: str
        :return: Un diccionario con los nombres de los días de la semana en el formato especificado.
        :rtype: dict
        """
        return Locale.parse(
            code or self.env.context.get("lang") or self.env.user.lang or "es_MX"
        ).days["format"][format]

    def get_date_format_of_lang(self, code: str = None) -> str:
        """
        Obtiene el formato de fecha para un idioma específico.

        :param code: Código del idioma (opcional).
        :type code: str
        :return: Formato de fecha del idioma.
        :rtype: str
        """
        return self._lang_get(
            code or self.env.context.get("lang") or self.env.user.lang or "es_MX"
        ).date_format

    def get_start_day_of_lang(self, code: str = None) -> int:
        """
        Obtiene el día de inicio de la semana para un idioma específico.

        :param code: Código del idioma (opcional).
        :type code: str
        :return: Día de inicio de la semana del idioma.
        :rtype: int
        """
        return (
            int(
                self._lang_get(
                    code
                    or self.env.context.get("lang")
                    or self.env.user.lang
                    or "es_MX"
                ).week_start
            )
            - 1
        )

    def get_time_format_of_lang(self, code: str = None) -> str:
        """
        Obtiene el formato de hora para un idioma específico.

        :param code: Código del idioma (opcional).
        :type code: str
        :return: Formato de hora del idioma.
        :rtype: str
        """
        return self._lang_get(
            code or self.env.context.get("lang") or self.env.user.lang or "es_MX"
        ).time_format
