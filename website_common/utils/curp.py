# Copyright 2026 Soltein SA. de CV.
# License LGPL-3 or later (http://www.gnu.org/licenses/lgpl.html)

import re
from datetime import date
from typing import Optional, Tuple

from odoo import _
from odoo.http import request


def validate_curp_digits(curp_str: str) -> int:
    """
    Calculates the CURP control digit for a given CURP string.

    The function uses a specific dictionary and weighting system to compute the control digit
    according to the official Mexican CURP algorithm.

    :param curp_str: The first 17 characters of a CURP string.
    :type curp_str: str
    :return: The calculated control digit (0-9).
    :rtype: int
    """
    dictionary = "0123456789ABCDEFGHIJKLMNÑOPQRSTUVWXYZ"
    lng_sum = 0.0
    i = 0
    while i < 17:
        lng_sum = lng_sum + dictionary.index(curp_str[i]) * (18 - i)
        i += 1
    lng_digit = 10 - lng_sum % 10
    if lng_digit == 10:
        return 0
    return lng_digit


def validate_curp_re(curp: str) -> re.Match | None:
    """
    Validates a CURP string against the official CURP regular expression.

    :param curp: The CURP string to validate.
    :type curp: str
    :return: A re.Match object if the CURP matches the pattern, None otherwise.
    :rtype: re.Match | None
    """
    return re.search(
        r"^([A-Z][AEIOUX][A-Z]{2}\d{2}(?:0[1-9]|1[0-2])(?:0[1-9]|[12]\d|3[01])[HM](?:AS|B[CS]|C[CLMSH]|D[FG]|G[TR]|HG|JC|M[CNS]|N[ETL]|OC|PL|Q[TR]|S[PLR]|T[CSL]|VZ|YN|ZS)[B-DF-HJ-NP-TV-Z]{3}[A-Z\d])(\d)$",
        curp,
    )


def invalid_curp_re_part(curp: str) -> str:
    """
    Returns a descriptive error message indicating which part of the CURP string is invalid.

    The function checks the CURP string step by step against the official CURP regular expression components.
    For each failed step, it returns a corresponding error message. It also checks if the CURP length is
    greater or less than expected and appends a message accordingly.

    :param curp: The CURP string to validate.
    :type curp: str
    :return: A string describing the invalid part of the CURP.
    :rtype: str
    """
    re_steps: list = [
        r"[A-Z][AEIOUX][A-Z]{2}",
        r"\d{2}(?:0[1-9]|1[0-2])(?:0[1-9]|[12]\d|3[01])",
        r"[HM]",
        r"(?:AS|B[CS]|C[CLMSH]|D[FG]|G[TR]|HG|JC|M[CNS]|N[ETL]|OC|PL|Q[TR]|S[PLR]|T[CSL]|VZ|YN|ZS)",
        r"[B-DF-HJ-NP-TV-Z]{3}",
        r"[A-Z\d]",
    ]
    error_messages: list = [
        _("Invalid name initials."),
        _("Invalid birthdate."),
        _("Invalid sex definition."),
        _("Invalid state definition."),
        _("Invalid name complementary value."),
        _("Invalid birthdate check value."),
    ]
    index: int = 0
    step: str = ""
    message: str = ""
    while index < len(re_steps):
        step += re_steps[index]
        if not re.search("^(%s)" % step, curp):
            message = error_messages[index]
            break
        index += 1
    message += (
        _("Has more characters than expected.")
        if len(curp) > 18
        else _("Has less characters than expected.")
        if len(curp) < 18
        else ""
    )
    return message


def validate_curp_sex(curp: str, sex: Optional[str] = None) -> bool:
    """
    Validates the sex field in a CURP (Clave Única de Registro de Población) string.

    This function checks if the provided `sex` matches the sex encoded in the CURP string.
    The CURP encodes sex as 'H' for male and 'M' for female at the 11th character (index 10).

    :param curp: The CURP string to validate.
    :type curp: str
    :param sex: The sex to validate against the CURP. It can be "male", "female", or None.
                If None or an invalid value (e.g., "", "other") is provided, the function
                assumes no validation is required.
    :type sex: Optional[str]
    :return: True if the `sex` matches the CURP or if no validation is required, False otherwise.
    :rtype: bool
    """
    if (
        sex
        and sex not in ["", "other"]
        and curp[10:11] != ("H" if sex == "male" else "M")
    ):
        return False
    return True


def validate_curp_state(curp: str, state_of_birth: int | None = None) -> bool:
    """
    Validates the state code in a CURP string against a provided state of birth.

    This function checks if the state code embedded in the CURP is valid and, if a state of birth is provided,
    verifies that it matches the CURP's state code. The state codes are obtained from the Odoo server.

    :param curp: The CURP string to validate.
    :type curp: str
    :param state_of_birth: The state code to validate against the CURP. If None, validation is skipped.
    :type state_of_birth: int | None
    :return: True if the CURP state code is valid and matches the provided state code (if given), False otherwise.
    :rtype: bool
    """
    try:
        if state_of_birth is None:
            state_of_birth = -1
        else:
            state_of_birth = int(state_of_birth)
    except ValueError:
        state_of_birth = -1
    # obtains the dictionary of state codes from the Odoo server
    curp_state_codes = request.env["ir.http"].code_convertion()
    state_code = curp[11:13]
    # checks that the state code in the CURP is valid
    if state_code not in list(curp_state_codes.values()):
        return False
    # If -1 was received as the state of birth code, it means it should not be checked
    # against the CURP string. Otherwise, it checks that the state identifier in the CURP
    # matches the one received as the state of birth.
    if state_of_birth != -1 and state_code != curp_state_codes[state_of_birth]:
        return False
    return True


def validate_curp_birthdate(curp: str, birthdate: str | date | None = None) -> bool:
    """
    Validates that the birthdate encoded in the CURP matches the provided birthdate.

    :param curp: The CURP string to validate.
    :type curp: str
    :param birthdate: The birthdate to validate against the CURP. Can be a string ("YYYY-MM-DD"), a date object, or None.
    :type birthdate: str | date | None
    :return: True if the birthdate in the CURP matches the provided birthdate, False otherwise.
    :rtype: bool
    """

    # If no birthdate is provided, or it's an empty string, skip validation and return True.
    if birthdate is None or birthdate == "":
        return True

    # If birthdate is a date object, convert it to a string in "YYYY-MM-DD" format.
    if isinstance(birthdate, date):
        birthdate = birthdate.strftime("%Y-%m-%d")

    try:
        # Extract year, month, and day from CURP string.
        b_year = int(curp[4:6])
        b_month = int(curp[6:8])
        b_day = int(curp[8:10])
        # The 17th character (index 16) indicates if the year is 1900s or 2000s.
        b_homonymy = curp[16:17]
        b_year = 1900 + b_year if b_homonymy.isdigit() else 2000 + b_year
        # Create a date object from the extracted values.
        curp_date: date = date(b_year, b_month, b_day)
    except ValueError:
        # If any value is invalid, return False.
        return False

    # If the birthdate in CURP is in the future, return False.
    if curp_date > date.today():
        return False

    # If the birthdate in CURP does not match the provided birthdate, return False.
    if curp_date.strftime("%Y-%m-%d") != birthdate:
        return False

    # If all checks pass, return True.
    return True


def valid_curp(
    curp: str,
    birthdate: str | date | None = None,
    state_of_birth: int | None = None,
    sex: str | None = None,
) -> Tuple[bool, str]:
    """Validate Mexican CURP against format and optional parameters."""
    curp = curp.upper()
    validated = validate_curp_re(curp)
    if not validated:
        return False, " ".join(
            [_("Failed to match regular expression."), invalid_curp_re_part(curp)]
        )

    if not validate_curp_sex(curp, sex):
        return False, _("Provided sex and CURP sex don't match.")

    if not validate_curp_state(curp, state_of_birth):
        return False, _(
            "Invalid CURP state code or provided state code don't match CURP state code."
        )

    if not validate_curp_birthdate(curp, birthdate):
        return False, _(
            "Invalid CURP birthdate or provided birthdate doesn't match CURP birthdate."
        )

    check_digit = validate_curp_digits(validated[1])
    if int(validated[2]) != check_digit:
        return False, _(
            "Failed to check CURP control number, expected: %s, obtained: %s"
        ) % (check_digit, validated[2])

    return True, _("Correct")
