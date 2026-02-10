"""Geo-IP pipeline: MaxMind reader, cloud detection, region inference."""

import logging
import math

import geoip2.database
import geoip2.errors

from bpl.config import BplConfig
from bpl.models import NodeLocation

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Cloud-provider ASN map (~20 well-known cloud ASNs)
# ---------------------------------------------------------------------------

CLOUD_ASN_MAP: dict[int, str] = {
    # AWS
    16509: "AWS",
    14618: "AWS",
    # Google Cloud
    15169: "GCP",
    396982: "GCP",
    # Microsoft Azure
    8075: "Azure",
    8068: "Azure",
    # Oracle Cloud
    31898: "Oracle",
    # DigitalOcean
    14061: "DigitalOcean",
    # Hetzner
    24940: "Hetzner",
    # OVH
    16276: "OVH",
    # Linode / Akamai Cloud
    63949: "Linode",
    # Vultr
    20473: "Vultr",
    # Alibaba Cloud
    45102: "Alibaba",
    # Tencent Cloud
    132203: "Tencent",
    # Scaleway / Online SAS
    12876: "Scaleway",
    # Equinix Metal (formerly Packet)
    54825: "Equinix",
    # IBM Cloud / SoftLayer
    36351: "IBM",
    # Cloudflare (often used for edge/proxy)
    13335: "Cloudflare",
    # Leaseweb
    60781: "Leaseweb",
    # Contabo
    40021: "Contabo",
    # Cherry Servers
    59642: "Cherry",
    # Latitude.sh
    28186: "Latitude",
}

# ---------------------------------------------------------------------------
# Cloud-region coordinates (provider/region → approximate lat, lon)
# ---------------------------------------------------------------------------

CLOUD_REGION_COORDS: dict[str, tuple[float, float]] = {
    # AWS
    "AWS/us-east-1": (39.04, -77.49),
    "AWS/us-east-2": (39.96, -83.00),
    "AWS/us-west-1": (37.35, -121.96),
    "AWS/us-west-2": (45.59, -122.60),
    "AWS/eu-west-1": (53.35, -6.26),
    "AWS/eu-west-2": (51.51, -0.13),
    "AWS/eu-west-3": (48.86, 2.35),
    "AWS/eu-central-1": (50.11, 8.68),
    "AWS/eu-north-1": (59.33, 18.07),
    "AWS/ap-southeast-1": (1.35, 103.82),
    "AWS/ap-southeast-2": (-33.87, 151.21),
    "AWS/ap-northeast-1": (35.68, 139.69),
    "AWS/ap-northeast-2": (37.57, 126.98),
    "AWS/ap-south-1": (19.08, 72.88),
    "AWS/sa-east-1": (-23.55, -46.63),
    "AWS/ca-central-1": (45.50, -73.57),
    # GCP
    "GCP/us-central1": (41.26, -95.86),
    "GCP/us-east1": (33.20, -80.02),
    "GCP/us-east4": (39.04, -77.49),
    "GCP/us-west1": (45.60, -121.18),
    "GCP/us-west4": (36.20, -115.14),
    "GCP/europe-west1": (50.45, 3.82),
    "GCP/europe-west2": (51.51, -0.13),
    "GCP/europe-west3": (50.11, 8.68),
    "GCP/europe-west4": (53.44, 6.84),
    "GCP/europe-north1": (60.57, 27.19),
    "GCP/asia-east1": (24.05, 120.52),
    "GCP/asia-northeast1": (35.68, 139.69),
    "GCP/asia-southeast1": (1.35, 103.82),
    "GCP/australia-southeast1": (-33.87, 151.21),
    "GCP/southamerica-east1": (-23.55, -46.63),
    # Azure
    "Azure/eastus": (37.37, -79.46),
    "Azure/eastus2": (36.67, -78.93),
    "Azure/westus": (37.78, -122.42),
    "Azure/westus2": (47.23, -119.85),
    "Azure/centralus": (41.88, -93.10),
    "Azure/northeurope": (53.35, -6.26),
    "Azure/westeurope": (52.37, 4.90),
    "Azure/uksouth": (51.51, -0.13),
    "Azure/southeastasia": (1.35, 103.82),
    "Azure/eastasia": (22.27, 114.16),
    "Azure/japaneast": (35.68, 139.69),
    "Azure/australiaeast": (-33.87, 151.21),
    "Azure/brazilsouth": (-23.55, -46.63),
    # Hetzner
    "Hetzner/fsn1": (50.47, 12.37),
    "Hetzner/nbg1": (49.45, 11.08),
    "Hetzner/hel1": (60.17, 24.94),
    "Hetzner/ash": (39.04, -77.49),
    # OVH
    "OVH/gra": (50.10, 2.39),
    "OVH/sbg": (48.57, 7.75),
    "OVH/bhs": (46.39, -72.74),
    "OVH/sgp": (1.35, 103.82),
    # DigitalOcean
    "DigitalOcean/nyc": (40.71, -74.01),
    "DigitalOcean/sfo": (37.77, -122.42),
    "DigitalOcean/ams": (52.37, 4.90),
    "DigitalOcean/sgp": (1.35, 103.82),
    "DigitalOcean/lon": (51.51, -0.13),
    "DigitalOcean/fra": (50.11, 8.68),
    "DigitalOcean/blr": (12.97, 77.59),
    "DigitalOcean/syd": (-33.87, 151.21),
}


def _haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Return the great-circle distance in km between two points.

    Args:
        lat1: Latitude of point 1 (degrees).
        lon1: Longitude of point 1 (degrees).
        lat2: Latitude of point 2 (degrees).
        lon2: Longitude of point 2 (degrees).

    Returns:
        Distance in kilometres.
    """
    r = 6371.0  # Earth radius in km
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (
        math.sin(dlat / 2) ** 2
        + math.cos(math.radians(lat1))
        * math.cos(math.radians(lat2))
        * math.sin(dlon / 2) ** 2
    )
    return r * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def infer_cloud_region(
    provider: str,
    latitude: float,
    longitude: float,
) -> str | None:
    """Infer the cloud region closest to the given coordinates.

    Only regions belonging to *provider* are considered.

    Args:
        provider: Cloud provider name (must match keys in
            ``CLOUD_REGION_COORDS``, e.g. ``"AWS"``).
        latitude: Node latitude (degrees).
        longitude: Node longitude (degrees).

    Returns:
        Region identifier (e.g. ``"us-east-1"``) or ``None`` if no regions
        are known for this provider.
    """
    prefix = f"{provider}/"
    best_region: str | None = None
    best_dist = float("inf")

    for key, (rlat, rlon) in CLOUD_REGION_COORDS.items():
        if not key.startswith(prefix):
            continue
        dist = _haversine_km(latitude, longitude, rlat, rlon)
        if dist < best_dist:
            best_dist = dist
            best_region = key.removeprefix(prefix)

    return best_region


class GeoIPReader:
    """Wrapper around MaxMind GeoLite2 database readers.

    The reader is tolerant of missing database files — if a path is ``None``
    or points to a non-existent file, the corresponding lookups simply return
    ``None``.

    Args:
        city_db_path: Path to ``GeoLite2-City.mmdb``, or ``None``.
        asn_db_path: Path to ``GeoLite2-ASN.mmdb``, or ``None``.
    """

    def __init__(
        self,
        city_db_path: str | None = None,
        asn_db_path: str | None = None,
    ) -> None:
        self._city_reader: geoip2.database.Reader | None = None
        self._asn_reader: geoip2.database.Reader | None = None

        if city_db_path:
            try:
                self._city_reader = geoip2.database.Reader(city_db_path)
                logger.debug("Opened GeoLite2-City DB: %s", city_db_path)
            except FileNotFoundError:
                logger.warning(
                    "GeoLite2-City DB not found at %s; "
                    "city/country enrichment disabled",
                    city_db_path,
                )

        if asn_db_path:
            try:
                self._asn_reader = geoip2.database.Reader(asn_db_path)
                logger.debug("Opened GeoLite2-ASN DB: %s", asn_db_path)
            except FileNotFoundError:
                logger.warning(
                    "GeoLite2-ASN DB not found at %s; ASN enrichment disabled",
                    asn_db_path,
                )

    def close(self) -> None:
        """Close underlying database readers."""
        if self._city_reader:
            self._city_reader.close()
        if self._asn_reader:
            self._asn_reader.close()

    def lookup_city(self, ip: str) -> dict | None:
        """Look up city/country/coordinates for an IP address.

        Args:
            ip: IPv4 or IPv6 address string.

        Returns:
            A dict with keys ``city``, ``country``, ``country_code``,
            ``latitude``, ``longitude``; or ``None`` if the lookup fails.
        """
        if not self._city_reader:
            return None
        try:
            resp = self._city_reader.city(ip)
        except (geoip2.errors.AddressNotFoundError, ValueError):
            logger.debug("City lookup failed for %s", ip)
            return None

        return {
            "city": resp.city.name,
            "country": resp.country.name,
            "country_code": resp.country.iso_code,
            "latitude": resp.location.latitude,
            "longitude": resp.location.longitude,
        }

    def lookup_asn(self, ip: str) -> dict | None:
        """Look up ASN information for an IP address.

        Args:
            ip: IPv4 or IPv6 address string.

        Returns:
            A dict with keys ``asn`` and ``asn_org``; or ``None`` if the
            lookup fails.
        """
        if not self._asn_reader:
            return None
        try:
            resp = self._asn_reader.asn(ip)
        except (geoip2.errors.AddressNotFoundError, ValueError):
            logger.debug("ASN lookup failed for %s", ip)
            return None

        return {
            "asn": resp.autonomous_system_number,
            "asn_org": resp.autonomous_system_organization,
        }


def enrich(nodes: list[NodeLocation], config: BplConfig) -> list[NodeLocation]:
    """Enrich a list of nodes with geo-IP, cloud, and region data.

    Mutates each ``NodeLocation`` in place, filling in the geo-enrichment
    fields (city, country, coordinates, ASN, cloud provider, cloud region).

    Args:
        nodes: Node locations produced by a probe (geo fields may be empty).
        config: Application configuration containing MaxMind DB paths.

    Returns:
        The same list, with geo fields populated where data was available.
    """
    reader = GeoIPReader(
        city_db_path=config.maxmind_city_db,
        asn_db_path=config.maxmind_asn_db,
    )

    try:
        for node in nodes:
            _enrich_node(node, reader)
    finally:
        reader.close()

    return nodes


def _enrich_node(node: NodeLocation, reader: GeoIPReader) -> None:
    """Enrich a single node with geo-IP data.

    Args:
        node: The node to enrich (mutated in place).
        reader: An open GeoIPReader instance.
    """
    # City / country / coordinates
    city_data = reader.lookup_city(node.ip)
    if city_data:
        node.city = city_data["city"]
        node.country = city_data["country"]
        node.country_code = city_data["country_code"]
        node.latitude = city_data["latitude"]
        node.longitude = city_data["longitude"]

    # ASN
    asn_data = reader.lookup_asn(node.ip)
    if asn_data:
        node.asn = asn_data["asn"]
        node.asn_org = asn_data["asn_org"]

    # Cloud detection
    if node.asn is not None and node.asn in CLOUD_ASN_MAP:
        node.is_cloud = True
        node.cloud_provider = CLOUD_ASN_MAP[node.asn]

        # Region inference (requires coordinates)
        if node.latitude is not None and node.longitude is not None:
            node.cloud_region = infer_cloud_region(
                node.cloud_provider, node.latitude, node.longitude
            )
    else:
        node.is_cloud = False
