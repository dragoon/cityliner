from dataclasses import dataclass


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

color_schemes = {
    'default': default_scheme,
    'pastel': pastel_scheme,
    'inferno': inferno_scheme,
    'earthy': earthy_scheme,
    'cool': cool_scheme
}