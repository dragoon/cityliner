# Cityliner

This repository contains a script to process GTFS data and generate visually appealing posters with customizable color schemes. Suitable for transit enthusiasts, city planners, and those looking to visualize transit data in an elegant manner.

## Table of Contents

1. [Features](#features)
2. [Installation and Setup](#installation-and-setup)
3. [Usage](#usage)
4. [Gallery](#gallery)
5. [Contribution](#contribution)
6. [License](#license)
7. [History](#history)

## Features

- Visualize GTFS routes based on their frequency and route types.
- Renders result as a PDF.
- Multiple color schemes: default, pastel, inferno, earthy, cool.
- Water body visualization (beta).

## Installation and Setup

1. Clone this repository:
    ```shell
    git clone git@github.com:dragoon/cityliner.git
    cd cityliner
    ```
2. Install required dependencies:
```shell
pip install -r requirements.txt
```

## Usage
Run the script using the following command:
```shell
python main.py --gtfs [path_to_gtfs_directory] --out [output_directory] --center [center_coordinates] [other_options]
```

### Options:
- `--gtfs`: Path to the GTFS directory. **(Required)**
- `--out`: Path to the output directory (will be created if it doesn't exist). **(Required)**
- `--center`: Coordinates of the center in the format `latitude,longitude`. **(Required)**
- `--max-dist`: Maximum distance from the center on y-axis (in km). Default is 20 km.
- `--size`: Size of the output drawing (in px). **(Either `--size` or `--poster` must be provided)**
- `--poster`: Create a drawing for A0 poster size.
- `--water`: Add water bodies to the poster (beta).
- `--color-scheme`: Choose a color scheme for the poster. Allowed values are: `default`, `pastel`, `inferno`, `earthy`, `cool`. Default is `default`.

Example:
```shell
python script_name.py --gtfs ./gtfs/helsinki --out ./output --center 40.730610,-73.935242 --color-scheme pastel --water
```

## Gallery
Here are some sample posters generated using the script:

![Helsinki Default Scheme Poster](./sample_images/default_poster.pdf)
*Helsinki Default Scheme Poster*

![Tallinn Pastel Scheme Poster](./sample_images/pastel_poster.pdf)
*Tallinn Pastel Scheme Poster*

![Berlin Inferno Scheme Poster](./sample_images/pastel_poster.pdf)
*Berlin Inferno Scheme Poster*

## Contribution

Feel free to fork this repository, open issues, or submit pull requests. Any contribution is welcome!

## License

### Gallery

	The gallery photos are licensed under the Creative Commons Attribution
	4.0 International license: http://creativecommons.org/licenses/by/4.0/.

This project is licensed under [Your License Name]. See the `LICENSE` file for more details.

## History
This project is inspired by Michael Mueller's [gtfs-visualizations](https://github.com/cmichi/gtfs-visualizations) repository (implemented with Node.js and Processing),
and my fork: https://github.com/dragoon/gtfs-visualizations,
which allowed to process large GTFS files, added actual poster-generation code,
and a possibility to restrict the visualization area within a certain radius, among other improvements.

This implementation has been designed from scratch with Python,
with ReportLab used for PDF rendering, and adds a possibility to visualize water bodies using OpenSteetMap data, among other changes.



