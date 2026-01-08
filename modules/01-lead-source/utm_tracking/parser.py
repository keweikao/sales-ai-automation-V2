"""
UTM parameter parser.

Extracts and validates UTM parameters from URLs.
"""

from typing import Optional
from urllib.parse import urlparse, parse_qs
from core.schemas.lead import UTMData


class UTMParser:
    """Parses UTM parameters from URLs."""

    UTM_PARAMS = [
        "utm_source",
        "utm_medium",
        "utm_campaign",
        "utm_term",
        "utm_content",
    ]

    def parse_url(self, url: str) -> Optional[UTMData]:
        """
        Extract UTM parameters from a URL.

        Args:
            url: URL string to parse

        Returns:
            UTMData object if any UTM params found, None otherwise
        """
        try:
            parsed = urlparse(url)
            params = parse_qs(parsed.query)
        except Exception:
            return None

        utm_values = {}
        for param in self.UTM_PARAMS:
            if param in params:
                # parse_qs returns lists, get first value
                value = params[param][0] if params[param] else None
                # Remove utm_ prefix for our model
                key = param.replace("utm_", "")
                utm_values[key] = value

        if not utm_values:
            return None

        return UTMData(**utm_values)

    def parse_dict(self, params: dict) -> Optional[UTMData]:
        """
        Extract UTM parameters from a dictionary.

        Args:
            params: Dictionary of query parameters

        Returns:
            UTMData object if any UTM params found
        """
        utm_values = {}

        for param in self.UTM_PARAMS:
            if param in params:
                key = param.replace("utm_", "")
                utm_values[key] = params[param]

        if not utm_values:
            return None

        return UTMData(**utm_values)

    def validate(self, utm: UTMData) -> bool:
        """
        Validate UTM data has required fields.

        At minimum, utm_source should be present.
        """
        return utm.source is not None
