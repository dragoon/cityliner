from dataclasses import dataclass


@dataclass
class ColorScheme:
    funicular_cable_gondola: str
    ferry_water: str
    bus: str
    rail: str
    subway: str
    tram: str


# Ivory and graphite: a restrained, mostly neutral map.
default_scheme = ColorScheme(
    funicular_cable_gondola="#C9BBA7",
    ferry_water="#9FB6C4",
    bus="#E8E2D5",
    rail="#909FA9",
    subway="#BCCAC3",
    tram="#BAC8D3"
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

# Apricot and rose: a warm map with distinct pink tram corridors.
inferno_scheme = ColorScheme(
    funicular_cable_gondola="#D3ABCB",
    ferry_water="#DABDA0",
    bus="#F1BD8E",
    rail="#E2D3B6",
    subway="#CBA8A0",
    tram="#DA91AE"
)

# Sea glass and moss: green carries the dominant bus network.
earthy_scheme = ColorScheme(
    funicular_cable_gondola="#D8C7A1",
    ferry_water="#82B9CB",
    bus="#94D2BC",
    rail="#CAD4D6",
    subway="#79AEA1",
    tram="#C0D59F"
)

# Lavender and ice blue: a cool map with violet bus corridors.
cool_scheme = ColorScheme(
    funicular_cable_gondola="#D4A0BE",
    ferry_water="#A0CBD0",
    bus="#BEA3E1",
    rail="#DBCDDF",
    subway="#ABBFD8",
    tram="#8EBEDB"
)

color_schemes = {
    'pastel': pastel_scheme,
    'default': default_scheme,
    'inferno': inferno_scheme,
    'earthy': earthy_scheme,
    'cool': cool_scheme
}
