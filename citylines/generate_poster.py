import json
from dataclasses import dataclass
from pathlib import Path

from PIL import Image, ImageDraw

from pdf2image import convert_from_path

from reportlab.pdfbase import pdfmetrics
from reportlab.graphics.shapes import Polygon, Drawing
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas
from reportlab.graphics import renderPDF
from reportlab.lib.colors import Color, HexColor
import math

from reportlab.pdfgen.canvas import Canvas
from svglib.svglib import svg2rlg

from citylines.gtfs.domain import RenderArea
from citylines.util.colors import ColorScheme


@dataclass
class Poster:
    render_area: RenderArea
    out_path: Path
    input_dir: Path
    city: str
    text: str
    logos: list[str]

    def __post_init__(self):
        self.logo_gap = 70*self.scaling_w
        self.target_logo_h = 564*self.scaling_h
        self.logo_start_x = 200*self.scaling_w
        self.logo_start_y = 100*self.scaling_h
        self.font_size = 88*self.scaling_h
        self.heading_font_size = 600*self.scaling_h
        self.heading_start_x = 250*self.scaling_w
        self.heading_start_y = self.render_area.height_px - 650*self.scaling_h

        self.extra_text_start_x = 250*self.scaling_w
        self.extra_text_start_y = 120*self.scaling_h
        self.extra_text_gap_y = 140 * self.scaling_h

    @property
    def scaling_w(self) -> float:
        return self.render_area.width_px / 9933

    @property
    def scaling_h(self) -> float:
        return self.render_area.height_px / 14043

    def _draw_logos(self, c: Canvas):
        total_w = 0
        for logo in self.logos:
            provider_w, _ = self._draw_svg_on_pdf(c, f"assets/logos/{self.city}/{logo}",
                                                  self.logo_start_x + total_w,
                                                  self.logo_start_y, height=self.target_logo_h)
            total_w += provider_w + self.logo_gap
        return total_w

    def generate_single(self,  color_scheme: ColorScheme, add_water: bool = False, add_admin_borders: bool = False):
        pdfmetrics.registerFont(TTFont('Lato', 'assets/fonts/Lato-Regular.ttf'))
        pdfmetrics.registerFont(TTFont('Garamond', 'assets/fonts/EBGaramond-VariableFont_wght.ttf'))

        self.out_path.parent.mkdir(parents=True, exist_ok=True)

        # reportlab measures in physical mm, not px, 0.24 is a scale factor
        c = canvas.Canvas(str(self.out_path),
                          pagesize=(self.render_area.width_px*0.24, self.render_area.height_px*0.24))
        c.scale(0.24, 0.24)
        c.setLineWidth(1)
        c.setFillColorRGB(0, 0, 0)
        c.rect(0, 0, self.render_area.width_px, self.render_area.height_px, fill=1)

        if add_water:
            self._draw_water_bodies(c)
        if add_admin_borders:
            self._draw_admin_borders(c)
        self._draw_routes(c, color_scheme)

        c.setFont("Lato", self.font_size)
        total_w = self._draw_logos(c)

        gray_value = 200 / 255
        c.setFillColorRGB(gray_value, gray_value, gray_value)
        # WRITE EXTRA TEXT
        for i, line in enumerate(self.text.split('\n')):
            c.drawString(total_w + self.extra_text_start_x, self.extra_text_start_y + i * self.extra_text_gap_y, line.strip())

        # Adding additional text on the poster
        # c.drawRightString(self.render_area.width_px - 200, 260, "Generated on cityliner.io.")
        # c.drawRightString(self.render_area.width_px - 200, 120,
        #                   "License for personal use only. Redistribution or commercial use is prohibited.")

        # Add city name on top
        c.setFont("Garamond", self.heading_font_size)
        c.drawString(self.heading_start_x, self.heading_start_y, self.city.title())

        c.showPage()
        c.save()

    def _draw_svg_on_pdf(self, canvas, svg_path, x, y, height):
        drawing = svg2rlg(svg_path)

        # If only height is provided, calculate the scaling factor based on the height,
        # then compute the resultant width based on the original aspect ratio.
        scaling_factor = height / drawing.height
        resultant_width = drawing.width * scaling_factor
        drawing.width = resultant_width
        drawing.height = height
        drawing.scale(scaling_factor, scaling_factor)
        renderPDF.draw(drawing, canvas, x, y)

        return drawing.width, drawing.height

    def apply_fade_effect(self):
        out_path = self._convert_pdf_to_png()
        image = Image.open(out_path)
        fade_distance = int(min(*image.size) / 10)
        mask = Image.new('L', image.size, 255)

        draw = ImageDraw.Draw(mask)

        for i in range(fade_distance):
            alpha = int(255 * (i / fade_distance))
            draw.rectangle((i, i, image.size[0] - i, image.size[1] - i), outline=alpha)

        # Ensure that image and backdrop image are in the same mode (either RGB or RGBA)
        backdrop_image = Image.new(image.mode, image.size, (0, 0, 0, 255))
        faded_image = Image.composite(image, backdrop_image, mask)
        faded_image.save(out_path)

    def _convert_pdf_to_png(self):
        images = convert_from_path(self.out_path, dpi=200)
        # Assuming the PDF has one page
        out_path = self.out_path.with_suffix(".png")
        images[0].save(out_path, 'PNG')
        return out_path

    def get_max_lines(self) -> float:
        with open(self.input_dir / "maxmin.lines", 'r') as file:
            max_val = float(file.readline().strip())
            return max_val

    def _draw_routes(self, c: Canvas, color_scheme: ColorScheme):
        max_trips = self.get_max_lines()
        c.saveState()
        c.translate(self.render_area.width_px / 2, self.render_area.height_px / 2)
        c.scale(1, -1)

        with open(self.input_dir / "data.lines", 'r') as file:
            for lineS in file:
                line = lineS.split("\t")
                trips = line[0]
                route_types = line[1].split(",")

                for route_type in route_types:
                    simple_route_type = to_simple_gtfs_type(int(route_type))
                    color = get_route_color(simple_route_type, color_scheme)
                    points = line[2].split(",")

                    factor = 1.7
                    stroke_weight = math.log(float(trips) * factor) * 3
                    if stroke_weight < 0:
                        stroke_weight = 1.0 * factor

                    c.setLineWidth(stroke_weight*self.scaling_w)
                    alph = 100 * (float(trips) / max_trips)
                    if alph < 20.0:
                        alph = 20.0

                    c.setLineCap(2)  # square

                    if simple_route_type == 15:
                        # water transport
                        c.setDash(10, 30)
                        color_alpha = Color(color.red, color.green, color.blue, 0.4)
                        c.setStrokeColor(color_alpha)
                    else:
                        color_alpha = Color(color.red, color.green, color.blue, alph / 255.0)
                        c.setStrokeColor(color_alpha)
                        c.setDash([])

                    path = c.beginPath()
                    for index, point in enumerate(points):
                        x, y = float(point.split(" ")[0]), float(point.split(" ")[1])
                        if index == 0:
                            path.moveTo(x, y)
                        else:
                            path.lineTo(x, y)
                    c.drawPath(path)
                    path.close()
        c.restoreState()

    def _draw_water_bodies(self, c):
        c.saveState()
        c.translate(self.render_area.width_px / 2, self.render_area.height_px / 2)
        c.scale(1, -1)

        with open(self.input_dir / "water_bodies_osm.json", 'r') as f:
            water_bodies = json.load(f)

        c.setDash([])
        canvas_width = c._pagesize[0]
        canvas_height = c._pagesize[1]

        # Create a Drawing with the same size as the Canvas
        d = Drawing(canvas_width, canvas_height)
        for body in water_bodies:
            points = [coord for point in body["nodes"] for coord in (point["x"], point["y"])]
            # Add a Polygon or any other shapes to the Drawing
            if len(points) > 2:
                polygon = Polygon(points, fillColor='#0e142a')
                d.add(polygon)

            # add islands with black on top
            if "interiors" in body:
                for interior in body["interiors"]:
                    int_points = [coord for point in interior for coord in (point["x"], point["y"])]
                    if len(int_points) > 2:
                        polygon = Polygon(int_points, fillColor='#000000')
                        d.add(polygon)
        renderPDF.draw(d, c, 0, 0)

        c.restoreState()

    def _draw_admin_borders(self, c):
        c.saveState()
        c.translate(self.render_area.width_px / 2, self.render_area.height_px / 2)
        c.scale(1, -1)

        with open(self.input_dir / "borders_osm.json", 'r') as f:
            way_paths = json.load(f)

        # Create a Drawing with the same size as the Canvas
        c.setDash(2, 10)
        c.setStrokeColorRGB(150, 150, 150)
        c.setLineWidth(2)

        for way_path in way_paths:
            if not way_path:
                continue

            path = c.beginPath()
            path.moveTo(way_path[0]['x'], way_path[0]['y'])

            for node in way_path[1:]:
                path.lineTo(node['x'], node['y'])

            c.drawPath(path)
            path.close()

        c.restoreState()


def to_simple_gtfs_type(route_type: int):
    if 0 <= route_type <= 12:
        return route_type
    elif 100 <= route_type <= 199:  # rail service
        return 2  # map to rail
    elif 200 <= route_type <= 299:  # coach service
        return 3  # map to bus
    elif 400 <= route_type <= 404:  # urban rail (subway)
        return 1  # map to subway
    elif route_type == 405:  # monorail
        return 12
    elif 700 <= route_type <= 799:  # bus service
        return 3  # map to bus
    elif 800 <= route_type <= 899:  # trolleybus
        return 11
    elif 900 <= route_type <= 999:  # tram service
        return 0
    elif route_type == 1000:  # water transport
        return 15
    elif 1300 <= route_type <= 1399:  # aerial lift service
        return 6
    elif route_type == 1400:  # aerial lift service
        return 6
    else:
        raise ValueError(f"Unknown route type: {route_type}")


def get_route_color(simple_route_type: int, color_scheme: ColorScheme) -> Color:
    match simple_route_type:
        case 7:
            return HexColor(color_scheme.funicular_cable_gondola)
        case 6:
            return HexColor(color_scheme.funicular_cable_gondola)
        case 5:
            return HexColor(color_scheme.funicular_cable_gondola)
        case 4:
            return HexColor(color_scheme.ferry_water)
        case 3:
            return HexColor(color_scheme.bus)
        case 2:
            return HexColor(color_scheme.rail)
        case 1:
            return HexColor(color_scheme.subway)
        case 0:
            return HexColor(color_scheme.tram)
        case 11:
            return HexColor(color_scheme.tram)
        case 15:
            return HexColor(color_scheme.ferry_water)
        case _:
            raise ValueError(f"Unknown route type: {simple_route_type}")
