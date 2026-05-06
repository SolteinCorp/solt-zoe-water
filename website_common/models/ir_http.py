# Copyright 2026 Soltein SA. de CV.
# License LGPL-3 or later (http://www.gnu.org/licenses/lgpl.html)

from odoo import models, tools

RES_COUNTRY_STATE_CODE_TO_CURP_CODE = {
    "AGU": "AS",
    "BCN": "BC",
    "BCS": "BS",
    "CAM": "CC",
    "CHP": "CS",
    "CHH": "CH",
    "CMX": "DF",
    "COA": "CL",
    "COL": "CM",
    "DUR": "DG",
    "GUA": "GT",
    "GRO": "GR",
    "HID": "HG",
    "JAL": "JC",
    "MEX": "MC",
    "MIC": "MN",
    "MOR": "MS",
    "NAY": "NT",
    "NLE": "NL",
    "OAX": "OC",
    "PUE": "PL",
    "QUE": "QT",
    "ROO": "QR",
    "SLP": "SP",
    "SIN": "SL",
    "SON": "SR",
    "TAB": "TC",
    "TAM": "TS",
    "TLA": "TL",
    "VER": "VZ",
    "YUC": "YN",
    "ZAC": "ZS",
}


class IrHttp(models.AbstractModel):
    _inherit = "ir.http"

    @tools.ormcache()
    def code_convertion(self) -> dict[int, str]:
        """Build and cache a mapping of `res.country.state` ids to CURP state codes.

        - Includes a default entry `{0: "NE"}` for unknown/not specified.
        - Fetches Mexican states (`base.mx`) and converts their Odoo codes to CURP codes.
        - Uses `tools.ormcache()` to cache the result per environment.

        Returns:
            dict[int, str]: Mapping from state id to CURP state code.
        """
        result = {0: "NE"}
        for state in self.env["res.country.state"].search(
            [("country_id", "=", self.env.ref("base.mx").id)], order="id"
        ):
            code = RES_COUNTRY_STATE_CODE_TO_CURP_CODE.get(state.code, False)
            if code:
                result[state.id] = code
        return result

    def get_frontend_session_info(self) -> dict:
        """Extend frontend session info with CURP state code mapping.

        Returns:
            dict: Session info dict updated with `curp_state_code`.
        """
        result = super().get_frontend_session_info()
        result.update(curp_state_code=self.code_convertion())
        return result
