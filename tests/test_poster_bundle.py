import gzip
import json
from pathlib import Path

import pytest

from citylines.gtfs.domain import RenderArea
from citylines.poster_bundle import prepare_bundle
from citylines.generate_poster import heading_font_path


def test_poster_bundle_preserves_paths_modes_peaks_and_projection(tmp_path):
    bundle = tmp_path/'bundle'; bundle.mkdir()
    (bundle/'manifest.json').write_text(json.dumps({'bounds':[-1000,-1000,1000,1000],'geometry':'geometry.json.gz'}))
    geometry = {'sections':[
        {'mode':'tram','peakDepartures':2.5,'paths':[[[0,0],[100,200]],[[300,400],[500,600]]]},
        {'mode':'bus','peakDepartures':0,'paths':[[[0,0],[100,100]]]}],
        'water':[[[[0,0],[100,0],[100,100],[0,0]],[[20,20],[30,20],[20,30],[20,20]]]]}
    (bundle/'geometry.json.gz').write_bytes(gzip.compress(json.dumps(geometry).encode()))
    out=tmp_path/'inputs';prepare_bundle(bundle,out,RenderArea(1000,2000))
    assert (out/'data.lines').read_text().splitlines()==['2.5\t0\t0.000 0.000,100.000 -200.000','2.5\t0\t300.000 -400.000,500.000 -600.000']
    assert (out/'maxmin.lines').read_text()=='2.5\n2.5\n'
    water=json.loads((out/'water_bodies_osm.json').read_text())
    assert water[0]['nodes'][2]=={'x':100,'y':-100}
    assert len(water[0]['interiors'])==1


def test_explicit_heading_font_never_falls_back_silently(tmp_path):
    with pytest.raises(FileNotFoundError,match='heading font not found'):
        heading_font_path(tmp_path/'missing.ttf')


def test_heading_font_override_precedence(tmp_path, monkeypatch):
    bundled = Path(__file__).resolve().parents[1] / 'assets/fonts/Lato-Regular.ttf'
    monkeypatch.setenv('CITYLINER_HEADING_FONT', str(tmp_path / 'missing.ttf'))
    with pytest.raises(FileNotFoundError, match='heading font not found'):
        heading_font_path()
    assert heading_font_path(bundled) == bundled


def test_bundled_heading_font_needs_no_configuration(tmp_path, monkeypatch):
    monkeypatch.delenv('CITYLINER_HEADING_FONT', raising=False)
    monkeypatch.chdir(tmp_path)
    from reportlab.pdfbase.ttfonts import TTFont
    path = heading_font_path()
    assert TTFont('BundledHeading', str(path)).face.familyName == b'Gelasio'
