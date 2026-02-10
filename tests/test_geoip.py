"""Tests for the geo-IP pipeline (bpl.geoip)."""

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from bpl.config import BplConfig
from bpl.geoip import (
    CLOUD_ASN_MAP,
    CLOUD_REGION_COORDS,
    GeoIPReader,
    _haversine_km,
    enrich,
    infer_cloud_region,
)
from bpl.models import NodeLocation

# ---------------------------------------------------------------------------
# Helpers: fake MaxMind response objects
# ---------------------------------------------------------------------------


def _fake_city_response(
    city: str = "Frankfurt",
    country: str = "Germany",
    country_code: str = "DE",
    latitude: float = 50.11,
    longitude: float = 8.68,
) -> SimpleNamespace:
    """Build a minimal object mimicking ``geoip2.models.City``."""
    return SimpleNamespace(
        city=SimpleNamespace(name=city),
        country=SimpleNamespace(name=country, iso_code=country_code),
        location=SimpleNamespace(latitude=latitude, longitude=longitude),
    )


def _fake_asn_response(
    asn: int = 24940,
    org: str = "Hetzner Online GmbH",
) -> SimpleNamespace:
    """Build a minimal object mimicking ``geoip2.models.ASN``."""
    return SimpleNamespace(
        autonomous_system_number=asn,
        autonomous_system_organization=org,
    )


def _make_node(ip: str = "1.2.3.4", port: int = 30303) -> NodeLocation:
    """Create a bare NodeLocation with no geo fields."""
    return NodeLocation(ip=ip, port=port, network="test")


# ---------------------------------------------------------------------------
# Tests: haversine
# ---------------------------------------------------------------------------


class TestHaversine:
    """Unit tests for the haversine distance helper."""

    def test_same_point_is_zero(self) -> None:
        assert _haversine_km(50.0, 8.0, 50.0, 8.0) == pytest.approx(0.0)

    def test_known_distance(self) -> None:
        # Frankfurt (50.11, 8.68) → London (51.51, -0.13) ≈ 636 km
        dist = _haversine_km(50.11, 8.68, 51.51, -0.13)
        assert dist == pytest.approx(636, abs=10)


# ---------------------------------------------------------------------------
# Tests: infer_cloud_region
# ---------------------------------------------------------------------------


class TestInferCloudRegion:
    """Region inference from coordinates."""

    def test_aws_frankfurt_resolves_eu_central_1(self) -> None:
        region = infer_cloud_region("AWS", 50.11, 8.68)
        assert region == "eu-central-1"

    def test_hetzner_nuremberg(self) -> None:
        # Nuremberg coords → closest Hetzner region is nbg1
        region = infer_cloud_region("Hetzner", 49.45, 11.08)
        assert region == "nbg1"

    def test_unknown_provider_returns_none(self) -> None:
        region = infer_cloud_region("UnknownCloud", 50.0, 8.0)
        assert region is None


# ---------------------------------------------------------------------------
# Tests: GeoIPReader
# ---------------------------------------------------------------------------


class TestGeoIPReader:
    """Tests for the MaxMind reader wrapper."""

    def test_no_paths_returns_none_lookups(self) -> None:
        reader = GeoIPReader(city_db_path=None, asn_db_path=None)
        assert reader.lookup_city("1.2.3.4") is None
        assert reader.lookup_asn("1.2.3.4") is None
        reader.close()

    def test_missing_file_does_not_raise(self) -> None:
        reader = GeoIPReader(
            city_db_path="/nonexistent/City.mmdb",
            asn_db_path="/nonexistent/ASN.mmdb",
        )
        assert reader.lookup_city("1.2.3.4") is None
        assert reader.lookup_asn("1.2.3.4") is None
        reader.close()

    @patch("bpl.geoip.geoip2.database.Reader")
    def test_lookup_city_returns_fields(self, mock_reader_cls: MagicMock) -> None:
        mock_instance = MagicMock()
        mock_instance.city.return_value = _fake_city_response()
        mock_reader_cls.return_value = mock_instance

        reader = GeoIPReader(city_db_path="/fake/City.mmdb")
        result = reader.lookup_city("1.2.3.4")

        assert result is not None
        assert result["city"] == "Frankfurt"
        assert result["country"] == "Germany"
        assert result["country_code"] == "DE"
        assert result["latitude"] == 50.11
        assert result["longitude"] == 8.68
        reader.close()

    @patch("bpl.geoip.geoip2.database.Reader")
    def test_lookup_asn_returns_fields(self, mock_reader_cls: MagicMock) -> None:
        mock_instance = MagicMock()
        mock_instance.asn.return_value = _fake_asn_response()
        mock_reader_cls.return_value = mock_instance

        reader = GeoIPReader(asn_db_path="/fake/ASN.mmdb")
        result = reader.lookup_asn("1.2.3.4")

        assert result is not None
        assert result["asn"] == 24940
        assert result["asn_org"] == "Hetzner Online GmbH"
        reader.close()

    @patch("bpl.geoip.geoip2.database.Reader")
    def test_lookup_city_address_not_found(self, mock_reader_cls: MagicMock) -> None:
        import geoip2.errors

        mock_instance = MagicMock()
        mock_instance.city.side_effect = geoip2.errors.AddressNotFoundError("not found")
        mock_reader_cls.return_value = mock_instance

        reader = GeoIPReader(city_db_path="/fake/City.mmdb")
        assert reader.lookup_city("192.168.1.1") is None
        reader.close()


# ---------------------------------------------------------------------------
# Tests: enrich()
# ---------------------------------------------------------------------------


class TestEnrich:
    """Integration tests for the enrich() pipeline."""

    @patch("bpl.geoip.GeoIPReader")
    def test_enriches_all_geo_fields(self, mock_reader_cls: MagicMock) -> None:
        mock_reader = MagicMock()
        mock_reader.lookup_city.return_value = {
            "city": "Frankfurt",
            "country": "Germany",
            "country_code": "DE",
            "latitude": 50.11,
            "longitude": 8.68,
        }
        mock_reader.lookup_asn.return_value = {
            "asn": 24940,
            "asn_org": "Hetzner Online GmbH",
        }
        mock_reader_cls.return_value = mock_reader

        node = _make_node()
        config = BplConfig()
        result = enrich([node], config)

        assert result is not None
        assert len(result) == 1
        n = result[0]
        assert n.city == "Frankfurt"
        assert n.country == "Germany"
        assert n.country_code == "DE"
        assert n.latitude == 50.11
        assert n.longitude == 8.68
        assert n.asn == 24940
        assert n.asn_org == "Hetzner Online GmbH"
        assert n.is_cloud is True
        assert n.cloud_provider == "Hetzner"
        assert n.cloud_region == "nbg1"  # closest Hetzner DC to Frankfurt

    @patch("bpl.geoip.GeoIPReader")
    def test_non_cloud_asn_sets_is_cloud_false(
        self, mock_reader_cls: MagicMock
    ) -> None:
        mock_reader = MagicMock()
        mock_reader.lookup_city.return_value = {
            "city": "Berlin",
            "country": "Germany",
            "country_code": "DE",
            "latitude": 52.52,
            "longitude": 13.40,
        }
        mock_reader.lookup_asn.return_value = {
            "asn": 99999,  # not in CLOUD_ASN_MAP
            "asn_org": "Some ISP",
        }
        mock_reader_cls.return_value = mock_reader

        node = _make_node()
        result = enrich([node], BplConfig())

        n = result[0]
        assert n.is_cloud is False
        assert n.cloud_provider is None
        assert n.cloud_region is None

    @patch("bpl.geoip.GeoIPReader")
    def test_missing_dbs_leaves_fields_none(self, mock_reader_cls: MagicMock) -> None:
        mock_reader = MagicMock()
        mock_reader.lookup_city.return_value = None
        mock_reader.lookup_asn.return_value = None
        mock_reader_cls.return_value = mock_reader

        node = _make_node()
        enrich([node], BplConfig())

        assert node.city is None
        assert node.country is None
        assert node.asn is None
        assert node.is_cloud is False

    @patch("bpl.geoip.GeoIPReader")
    def test_enrich_returns_same_list(self, mock_reader_cls: MagicMock) -> None:
        mock_reader = MagicMock()
        mock_reader.lookup_city.return_value = None
        mock_reader.lookup_asn.return_value = None
        mock_reader_cls.return_value = mock_reader

        nodes = [_make_node("10.0.0.1"), _make_node("10.0.0.2")]
        result = enrich(nodes, BplConfig())

        assert result is nodes
        assert len(result) == 2

    @patch("bpl.geoip.GeoIPReader")
    def test_reader_closed_even_on_error(self, mock_reader_cls: MagicMock) -> None:
        mock_reader = MagicMock()
        mock_reader.lookup_city.side_effect = RuntimeError("boom")
        mock_reader_cls.return_value = mock_reader

        node = _make_node()
        with pytest.raises(RuntimeError, match="boom"):
            enrich([node], BplConfig())

        mock_reader.close.assert_called_once()


# ---------------------------------------------------------------------------
# Tests: cloud ASN map & region coords sanity checks
# ---------------------------------------------------------------------------


class TestConstants:
    """Basic sanity checks on the static data."""

    def test_cloud_asn_map_has_entries(self) -> None:
        assert len(CLOUD_ASN_MAP) >= 20

    def test_cloud_region_coords_keys_match_providers(self) -> None:
        """Every region key must start with a provider that exists in the ASN map."""
        providers_in_map = set(CLOUD_ASN_MAP.values())
        for key in CLOUD_REGION_COORDS:
            provider = key.split("/")[0]
            assert provider in providers_in_map, (
                f"Region key {key!r} references unknown provider {provider!r}"
            )

    def test_coordinates_are_valid_ranges(self) -> None:
        for key, (lat, lon) in CLOUD_REGION_COORDS.items():
            assert -90 <= lat <= 90, f"{key} latitude {lat} out of range"
            assert -180 <= lon <= 180, f"{key} longitude {lon} out of range"
