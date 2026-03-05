"""
services/morningstar_parser.py

Parses Morningstar XML API responses into flat Python dicts.

The Morningstar data API returns XML where each API's data lives
inside an <api> element. Within that, field values are direct child
elements with text content (e.g., <DayEndNAV>125.43</DayEndNAV>).

This parser extracts all leaf elements into a {tag_name: text_value}
dict. Type conversion is left to the caller via safe_float/safe_int/safe_date.
"""

from __future__ import annotations
from datetime import date, datetime
from xml.etree import ElementTree

import structlog

logger = structlog.get_logger(__name__)


def parse_xml_response(xml_text: str) -> dict[str, str]:
    """
    Parse Morningstar XML response and return a flat dict of tag names to values.

    The XML structure is typically:
        <root>
          <api>
            <Field1>value1</Field1>
            <Field2>value2</Field2>
            ...
          </api>
        </root>

    Returns all leaf-level elements as {tag: text}. Tags with no text are skipped.
    If multiple <api> elements exist, data from all are merged (last value wins).
    """
    if not xml_text or not xml_text.strip():
        logger.warning("morningstar_parser_empty_response")
        return {}

    try:
        root = ElementTree.fromstring(xml_text)
    except ElementTree.ParseError as exc:
        logger.error("morningstar_parser_xml_error", error=str(exc))
        return {}

    result: dict[str, str] = {}

    # Walk the entire tree and collect leaf nodes (nodes with text and no children)
    for element in root.iter():
        # Skip container elements that have child elements
        if len(element) > 0:
            continue
        # Only include elements that have actual text content
        if element.text and element.text.strip():
            # Strip namespace prefix if present
            tag = element.tag
            if "}" in tag:
                tag = tag.split("}", 1)[1]
            result[tag] = element.text.strip()

    if not result:
        logger.warning("morningstar_parser_no_data_extracted", xml_length=len(xml_text))

    return result


def safe_float(value: str | None) -> float | None:
    """Convert string to float, returning None for missing or invalid values."""
    if value is None or value.strip() == "":
        return None
    try:
        parsed = float(value)
        # Morningstar sometimes uses extreme sentinel values for missing data
        if abs(parsed) > 1e15:
            return None
        return parsed
    except (ValueError, TypeError):
        return None


def safe_int(value: str | None) -> int | None:
    """Convert string to int, returning None for missing or invalid values."""
    if value is None or value.strip() == "":
        return None
    try:
        # Handle values like "3.0" from XML
        return int(float(value))
    except (ValueError, TypeError):
        return None


def safe_date(value: str | None) -> date | None:
    """
    Convert string to date, returning None for missing or invalid values.

    Handles common Morningstar date formats:
      - 2024-03-15 (ISO)
      - 2024-03-15T00:00:00 (ISO with time)
      - 03/15/2024 (US format)
    """
    if value is None or value.strip() == "":
        return None
    try:
        # Try ISO format first (most common from Morningstar)
        if "T" in value:
            return datetime.fromisoformat(value.replace("Z", "+00:00")).date()
        if "-" in value:
            return date.fromisoformat(value)
        # US format fallback
        if "/" in value:
            return datetime.strptime(value, "%m/%d/%Y").date()
    except (ValueError, TypeError):
        pass
    return None
