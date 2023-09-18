import json
from dataclasses import dataclass
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter

from pdf2image import convert_from_path

from reportlab.lib.pagesizes import A0
from reportlab.pdfbase import pdfmetrics
from reportlab.graphics.shapes import Polygon, Drawing
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas
from reportlab.graphics import renderPDF
from reportlab.lib.colors import Color, HexColor
import math

from reportlab.pdfgen.canvas import Canvas
from svglib.svglib import svg2rlg


@dataclass
class ColorScheme:
    funicular_cable_gondola: str
    ferry_water: str
    bus: str
    rail: str
    subway: str
    tram: str


# Default Scheme
default_scheme = ColorScheme(
    funicular_cable_gondola="#F761BF",
    ferry_water="#FF8000",
    bus="#E31B1C",
    rail="#708A91",
    subway="#4DAF4A",
    tram="#1A75D1"
)

# Pastel Scheme
pastel_scheme = ColorScheme(
    funicular_cable_gondola="#FFA8D8",
    ferry_water="#85acff",
    bus="#FF9999",
    rail="#A6A6A6",
    subway="#98E2A2",
    tram="#99CCFF"
)

inferno_scheme = ColorScheme(
    funicular_cable_gondola="#FF5733",  # Bright Orange
    ferry_water="#C70039",  # Dark Red
    bus="#FFC300",  # Bright Yellow
    rail="#DAF7A6",  # Pale Green
    subway="#581845",  # Dark Purple
    tram="#900C3F"  # Dark Magenta
)

# Earthy Scheme
earthy_scheme = ColorScheme(
    funicular_cable_gondola="#E89005",
    ferry_water="#55AA77",
    bus="#B36500",
    rail="#5D5D5D",
    subway="#44BB44",
    tram="#3377AA"
)

# Cool Scheme
cool_scheme = ColorScheme(
    funicular_cable_gondola="#8E2DE2",
    ferry_water="#2193B0",
    bus="#C32BAD",
    rail="#5D5DAA",
    subway="#4DFFB3",
    tram="#6761A8"
)


@dataclass
class Poster:
    width: int
    height: int
    name: str
    out_dir: Path
    input_dir: Path
    city: str
    logos: list[str]

    def _draw_logos(self, c: Canvas):
        gap_pt = 70
        target_logo_h = 564
        total_w = 0
        for logo in self.logos:
            provider_w, _ = self._draw_svg_on_pdf(c, f"assets/logos/{self.city}/{logo}", 200 + total_w,
                                                  100, height=target_logo_h)
            total_w += provider_w + gap_pt
        return total_w

    def generate_single(self):
        pdfmetrics.registerFont(TTFont('Lato', 'assets/fonts/Lato-Regular.ttf'))

        c = canvas.Canvas(f"{self.name}.pdf", pagesize=(A0[0], A0[1]))
        # reportlab measures in points, and not pixels
        c.scale(A0[0] / self.width, A0[1] / self.height)
        c.setLineWidth(1)
        c.setFillColorRGB(0, 0, 0)
        c.rect(0, 0, self.width, self.height, fill=1)

        maxmin = load_lines(self.input_dir, self.city)
        self._draw_water_bodies(c)
        self._draw_routes(c, maxmin)

        c.setFont("Lato", 88)
        total_w = self._draw_logos(c)

        gray_value = 200 / 255
        c.setFillColorRGB(gray_value, gray_value, gray_value)
        # # Loading the text file and writing the lines
        with open(f"texts/{self.city}.txt", "r") as file:
            lines = file.readlines()
            start = 120
            for i, line in enumerate(lines):
                c.drawString(total_w + 250, start + i * 140, line.strip())

        # Adding additional text on the poster
        c.drawRightString(self.width - 200, 260, "Generated on cityliner.io.")
        c.drawRightString(self.width - 200, 120,
                          "License for personal use only. Redistribution or commercial use is prohibited.")

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
        fade_distance = int(min(self.width, self.height) / 10)
        mask = Image.new('L', (self.width, self.height), 255)

        draw = ImageDraw.Draw(mask)

        for i in range(fade_distance):
            alpha = int(255 * (i / fade_distance))
            draw.rectangle((i, i, self.width - i, self.height - i), outline=alpha)

        # Ensure that image and backdrop image are in the same mode (either RGB or RGBA)
        backdrop_image = Image.new(image.mode, image.size, (0, 0, 0, 255))
        faded_image = Image.composite(image, backdrop_image, mask)
        faded_image.save(out_path)

    def _convert_pdf_to_png(self):
        # images = convert_from_path(self.out_dir / f"{self.name}.pdf")
        # Assuming the PDF has one page
        out_path = self.out_dir / f"{self.name}.png"
        # images[0].save(out_path, 'PNG')
        return out_path

    def _draw_routes(self, c, maxmin: float):
        c.saveState()
        c.translate(self.width / 2, self.height / 2)
        c.scale(1, -1)

        with open(self.input_dir / self.city / "data.lines", 'r') as file:
            for lineS in file:
                line = lineS.split("\t")
                trips = line[0]
                route_types = line[1].split(",")

                for route_type in route_types:
                    simple_route_type = convert_gtfs_to_digit(int(route_type))
                    color = get_route_color(simple_route_type, inferno_scheme)
                    points = line[2].split(",")

                    factor = 1.7
                    stroke_weight = math.log(float(trips) * factor) * 3
                    if stroke_weight < 0:
                        stroke_weight = 1.0 * factor

                    c.setLineWidth(stroke_weight)
                    alph = 100 * (float(trips) / maxmin)
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
        c.translate(self.width / 2, self.height / 2)
        c.scale(1, -1)

        with open(self.input_dir / self.city / "water_bodies_osm.json", 'r') as f:
            water_bodies = json.load(f)

        c.setDash([])
        canvas_width = c._pagesize[0]
        canvas_height = c._pagesize[1]

        # Create a Drawing with the same size as the Canvas
        d = Drawing(canvas_width, canvas_height)
        for body in water_bodies:
            points = []
            for index, point in enumerate(body["nodes"]):
                x, y = point["x"], point["y"]
                points.append(x)
                points.append(y)
            # Add a Polygon or any other shapes to the Drawing
            polygon = Polygon(points, fillColor='#0e142a')
            d.add(polygon)
        renderPDF.draw(d, c, 0, 0)

        c.restoreState()


def load_lines(input_dir: Path, city) -> float:
    with open(input_dir / city / "maxmin.lines", 'r') as file:
        max_val = float(file.readline().strip())
        return max_val


def convert_gtfs_to_digit(route_type: int):
    if 0 <= route_type <= 9:
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
        case 15:
            return HexColor(color_scheme.ferry_water)
        case _:
            raise ValueError(f"Unknown route type: {simple_route_type}")


if __name__ == "__main__":
    p = Poster(9933, 14043, name="zurich", out_dir=Path("./posters"),
               input_dir=Path("./processed"), city="zurich",
               logos=["zurich_coat_of_arms.svg", "kanton_zurich.svg"])
    p.generate_single()
    # p.apply_fade_effect()
