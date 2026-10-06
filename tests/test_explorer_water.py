from shapely.geometry import Polygon
import pytest

from citylines.explorer.water import build_shapefile_water, build_water, query_for


def geometry(points):
    return [{"lat": y, "lon": x} for x, y in points]


def test_water_preserves_disconnected_outers_and_islands_and_clips():
    outer = [(0, 0), (.02, 0), (.02, .02), (0, .02), (0, 0)]
    hole = [(.004, .004), (.008, .004), (.008, .008), (.004, .008), (.004, .004)]
    separate = [(-.01, 0), (-.005, 0), (-.005, .005), (-.01, .005), (-.01, 0)]
    data = {"osm3s": {"timestamp_osm_base": "2026-10-06T10:00:00Z"}, "elements": [
        {"type": "relation", "id": 1, "members": [
            {"type": "way", "ref": 2, "role": "outer", "geometry": geometry(outer[:3])},
            {"type": "way", "ref": 3, "role": "outer", "geometry": geometry(outer[2:])},
            {"type": "way", "ref": 4, "role": "inner", "geometry": geometry(hole)},
            {"type": "way", "ref": 5, "role": "outer", "geometry": geometry(separate)}]},
        {"type": "way", "id": 4, "geometry": geometry(hole)}]}
    layer = build_water(data, (0, 0), 2, "2026-10-06T11:00:00Z", "https://example.test/api")
    assert len(layer["polygons"]) == 2
    assert sorted(len(p) for p in layer["polygons"]) == [1, 2]
    assert all(Polygon(p[0], p[1:]).is_valid for p in layer["polygons"])
    assert all(-2000 <= coord <= 2000 for p in layer["polygons"] for ring in p for xy in ring for coord in xy)
    assert layer["source"]["dataTimestamp"] == "2026-10-06T10:00:00Z"


def test_water_reports_unclosed_relations_instead_of_joining_them():
    data = {"elements": [
        {"type": "way", "id": 1, "geometry": geometry([(0, 0), (.01, 0), (.01, .01), (0, 0)])},
        {"type": "relation", "id": 2, "members": [
            {"type": "way", "ref": 3, "role": "outer", "geometry": geometry([(0, 0), (.01, 0), (.01, .01)])}]}]}
    layer = build_water(data, (0, 0), 2, "2026-10-06", "https://example.test/api")
    assert layer["diagnostics"]["Unclosed relation rings"] == 1
    assert len(layer["polygons"]) == 1
    with pytest.raises(ValueError, match="incomplete"):
        build_water({"remark": "runtime timeout", "elements": data["elements"]}, (0, 0), 2, "today", "endpoint")
    assert 'relation["natural"="water"]' in query_for((52, 21), 30)


def test_regional_water_preserves_holes_and_clips(tmp_path):
    import geopandas as gpd
    polygon = Polygon([(0, 0), (.02, 0), (.02, .02), (0, .02)],
                      [[(.004, .004), (.008, .004), (.008, .008), (.004, .008)]])
    path = tmp_path / "water.geojson"
    gpd.GeoDataFrame(geometry=[polygon], crs="EPSG:4326").to_file(path, driver="GeoJSON")
    result = build_shapefile_water(path, (0, 0), 2, "2026-10-06", "https://download.example", "2026-10-05")
    assert len(result["polygons"]) == 1
    assert len(result["polygons"][0]) == 2
    assert all(-2000 <= coord <= 2000 for ring in result["polygons"][0] for xy in ring for coord in xy)
