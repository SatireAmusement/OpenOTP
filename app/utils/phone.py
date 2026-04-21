from phonenumbers import (
    NumberParseException,
    PhoneNumberFormat,
    format_number,
    is_possible_number,
    is_valid_number,
    parse,
    region_code_for_number,
)


class InvalidPhoneNumberError(ValueError):
    pass


def normalize_phone_number(phone_number: str, default_region: str, allowed_countries: set[str] | None = None) -> str:
    try:
        parsed = parse(phone_number, default_region)
    except NumberParseException as exc:
        raise InvalidPhoneNumberError("Phone number could not be parsed.") from exc

    if not is_possible_number(parsed) or not is_valid_number(parsed):
        raise InvalidPhoneNumberError("Phone number is not a valid routable number.")

    region = region_code_for_number(parsed)
    if allowed_countries and region not in allowed_countries:
        raise InvalidPhoneNumberError("Phone number country is not allowed.")

    return format_number(parsed, PhoneNumberFormat.E164)
