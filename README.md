# Automated E-Ink Dashboard

A Python application that generates a daily 1200×1600 dashboard and automatically publishes it to a physical SwitchBot E-Ink Art Frame.

The application combines external data sources with image composition and a cloud-device API to create an end-to-end automated display pipeline:

**Data Sources → Dashboard Generation → PNG → SwitchBot Cloud API → Physical E-Ink Display**

The dashboard currently combines weather information, Disney park hours, and a "Today in Disney History" feature into a single mid-century-modern themed image.

## Features

* Retrieves and processes daily external data
* Generates a 1200×1600 dashboard image using Python
* Composites multiple data sources and graphical assets into a single display
* Uploads the completed dashboard to a SwitchBot E-Ink Art Frame
* Authenticates with the SwitchBot Cloud API using signed requests
* Keeps API credentials outside of source code using environment variables
* Provides clear error handling for unattended operation
* Supports dry-run/testing workflows without uploading to the physical device

## Project Structure

* `fetch_data.py` — Retrieves and prepares external data
* `compose.py` — Generates the final dashboard image
* `push_to_frame.py` — Uploads the completed dashboard to the SwitchBot E-Ink Art Frame
* `layout.json` — Dashboard layout configuration
* `disney_history.json` — Historical content used by the dashboard
* `assets/` — Background and other graphical assets
* `fonts/` — Fonts used during image composition
* `output/` — Generated dashboard images

## Purpose

This project was developed as a real-world automation project for a physical E-Ink display. The goal was to create a reliable pipeline that could generate fresh content each day and deliver it automatically to the display without requiring manual image transfers.

The project also serves as an example of integrating a Python application with an external cloud API and a physical IoT device.
