from pathlib import Path

from reportlab.lib.enums import TA_RIGHT
from reportlab.lib.pagesizes import A0
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.graphics.shapes import Path as PdfPath
from reportlab.pdfgen import canvas
from reportlab.graphics import renderPDF
from reportlab.lib.colors import Color
import math

from svglib.svglib import svg2rlg


def create_font(font_name, size):
    return font_name, size


def draw_svg_on_pdf(canvas, svg_path, x, y, width=None, height=None):
    drawing = svg2rlg(svg_path)

    # Optionally, scale the drawing to the desired width and height
    if width and height:
        scaling_x = width / drawing.width
        scaling_y = height / drawing.height
        drawing.width = width
        drawing.height = height
        drawing.scale(scaling_x, scaling_y)

    renderPDF.draw(drawing, canvas, x, y)


def draw_poster(input_dir: Path, cities: list[str], provider_icon: str | None, size_x=9933, size_y=14043, poster=False):
    if poster:
        size_x, size_y = A0
    if provider_icon:
        provider_icon_path = f"{provider_icon}.svg"
    # pdfmetrics.registerFont(TTFont('Lato', 'Lato.ttf'))

    c = canvas.Canvas(f"output.pdf", pagesize=(size_x, size_y))
    c.setLineWidth(1)
    c.setFillColorRGB(0.1, 0.1, 0.1)
    c.rect(0, 0, size_x, size_y, fill=1)
    c.translate(50, 50)

    maxmin = load_lines(input_dir, cities)
    draw_routes(c, input_dir, cities, maxmin)

    # Handle the poster condition
    if poster:
        c.setFont("Lato", 88)  # This sets the font to Lato with size 88
        # Drawing the provider_icon (adapted for image drawing in reportlab)
        # provider_h = 564.0
        # provider_w = provider_icon.width * provider_h / provider_icon.height
        # draw_svg_on_pdf(c, provider_icon_path, 200, size_y - provider_h - 190, provider_w, provider_h)
        #
        # # Loading the text file and writing the lines
        # with open(f"../texts/{cities[0]}.txt", "r") as file:
        #     lines = file.readlines()
        #     text = "\n".join(lines)
        #     c.drawString(380 + provider_w, size_y - 600, text)

        # Adding additional text on the poster
        text_object = c.beginText()
        text_object.setTextOrigin(size_x, size_y)  # Set the starting position of the text.
        text_object.setTextAlign(TA_RIGHT)
        text_to_add = "\n\nGenerated on cityliner.io\nLicense Creative Commons Attribution 4.0 Unported"
        c.drawString(size_x - 1500, size_y - 600, text_to_add)

    c.showPage()
    c.save()


def load_lines(input_dir: Path, cities) -> list:
    maxmin = []
    for city in cities:
        with open(input_dir / city / "maxmin.lines", 'r') as file:
            max_val = float(file.readline().strip())
            maxmin.append(max_val)
    return maxmin


def get_route_color(route_type: str) -> Color:
    match route_type:
        case "7":
            return Color(0.97, 0.38, 0.75)  # funicular
        case "6":
            return Color(0.65, 0.33, 0.16)  # gondola
        case "5":
            return Color(1, 1, 0.2)  # cable car
        case "4":
            return Color(1, 0.5, 0)  # ferry
        case "3":
            return Color(0.89, 0.1, 0.11)  # bus
        case "2":
            return Color(0.44, 0.53, 0.57)  # rail, inter-city
        case "1":
            return Color(0.3, 0.69, 0.29)  # subway, metro
        case "0":
            return Color(0.1, 0.46, 0.82)  # tram
        case _:
            raise ValueError(f"Unknown route type: {route_type}")


def draw_routes(c, input_dir: Path, cities, maxmin):
    c.saveState()
    c.translate(0, A0[1])
    c.scale(1, -1)  #

    for city in cities:
        with open(input_dir / city / "data.lines", 'r') as file:
            for lineS in file:
                line = lineS.split("\t")
                trips = line[0]
                route_types = line[1].split(",")

                for route_type in route_types:
                    color = get_route_color(route_type)
                    points = line[2].split(",")

                    factor = 1.7
                    stroke_weight = math.log(float(trips) * factor) * 3
                    if stroke_weight < 0:
                        stroke_weight = 1.0 * factor

                    c.setLineWidth(stroke_weight)
                    alph = 100 * (float(trips) / maxmin[0])
                    if alph < 20.0:
                        alph = 20.0
                    color_alpha = Color(color.red, color.green, color.blue, alph / 255.0)

                    c.setStrokeColor(color_alpha)
                    c.setLineCap(2)  # square

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


if __name__ == "__main__":
    draw_poster(Path("."), cities=["ulm"], provider_icon=None)
