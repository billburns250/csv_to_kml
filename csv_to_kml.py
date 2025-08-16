#!/usr/bin/env python3
#
# Last Revised August 15, 2025  
# Copyright © 2025 Bill Burns. This work is openly licensed via CC BY 4.0
# https://creativecommons.org/licenses/by/4.0/
#

"""
csv_to_kml.py
Convert drone CSV -> KML (gx:Track).
Auto-detects common column name variants, prints detected columns, skips invalid coordinates (0.0), and summarizes results.

Usage:
    python3 csv_to_kml.py input.csv output.kml
"""
import csv
import sys
import os
from xml.etree.ElementTree import Element, SubElement, tostring
from xml.dom import minidom

POSSIBLE_HEADERS = {
    "timestamp": ["timestamp", "time", "time_utc", "datetime", "date_time", "gpstime", "utc_time"],
    "latitude":  ["latitude", "lat", "lat_deg", "lat_dd", "latitude_deg"],
    "longitude": ["longitude", "lon", "long", "lng", "lon_deg", "lon_dd", "longitude_deg"],
    "elevation": ["elevation", "altitude", "alt", "height", "elev", "alt_m"]
}

def find_column(fieldnames, possible_names):
    if not fieldnames:
        return None
    lower_to_original = {h.strip().lower(): h for h in fieldnames if h}
    for name in possible_names:
        if name in lower_to_original:
            return lower_to_original[name]
    for name in possible_names:
        candidates = [orig for lower, orig in lower_to_original.items() if name in lower]
        if candidates:
            candidates.sort(key=len)
            return candidates[0]
    return None

def print_detected_columns(fieldnames, ts_col, lat_col, lon_col, ele_col):
    print("Available CSV headers:")
    if fieldnames:
        print("  " + ", ".join([f"'{h}'" for h in fieldnames]))
    else:
        print("  (no headers detected)")
    print("Detected columns:")
    print(f"  timestamp -> {repr(ts_col)}")
    print(f"  latitude  -> {repr(lat_col)}")
    print(f"  longitude -> {repr(lon_col)}")
    print(f"  elevation -> {repr(ele_col)}")

def csv_to_kml(csv_file, kml_file):
    input_basename = os.path.splitext(os.path.basename(csv_file))[0]

    with open(csv_file, newline='', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames

        ts_col = find_column(fieldnames, POSSIBLE_HEADERS["timestamp"])
        lat_col = find_column(fieldnames, POSSIBLE_HEADERS["latitude"])
        lon_col = find_column(fieldnames, POSSIBLE_HEADERS["longitude"])
        ele_col = find_column(fieldnames, POSSIBLE_HEADERS["elevation"])

        print_detected_columns(fieldnames, ts_col, lat_col, lon_col, ele_col)

        if not all([ts_col, lat_col, lon_col, ele_col]):
            print("\nError: Could not detect all required columns in CSV. Aborting.")
            sys.exit(1)

        kml = Element('kml', xmlns="http://www.opengis.net/kml/2.2", **{"xmlns:gx": "http://www.google.com/kml/ext/2.2"})
        doc = SubElement(kml, 'Document')
        name = SubElement(doc, 'name')
        name.text = f"Drone Flight Track - {input_basename}"

        placemark = SubElement(doc, 'Placemark')
        pm_name = SubElement(placemark, 'name')
        pm_name.text = f"UAS - {input_basename}"

        track = SubElement(placemark, 'gx:Track')

        rows_written = 0
        rows_skipped = 0
        rows_invalid_coords = 0
        total_rows = 0

        for row in reader:
            total_rows += 1
            try:
                ts_val = (row.get(ts_col) or "").strip()
                lat_s = (row.get(lat_col) or "").strip()
                lon_s = (row.get(lon_col) or "").strip()
                ele_s = (row.get(ele_col) or "").strip()

                if not ts_val:
                    rows_skipped += 1
                    continue

                lat = float(lat_s)
                lon = float(lon_s)
                ele = float(ele_s)

                # Check for invalid coordinates (0.0)
                if lat == 0.0 or lon == 0.0:
                    rows_invalid_coords += 1
                    continue

                when = SubElement(track, 'when')
                when.text = ts_val

                coord = SubElement(track, 'gx:coord')
                coord.text = f"{lon} {lat} {ele}"

                rows_written += 1
            except (ValueError, TypeError, KeyError):
                rows_skipped += 1
                continue

    rough = tostring(kml, 'utf-8')
    reparsed = minidom.parseString(rough)
    with open(kml_file, 'w', encoding='utf-8') as out:
        out.write(reparsed.toprettyxml(indent="  "))

    print(f"\nFinished writing KML to: {kml_file}")
    print(f"Rows processed: {total_rows}")
    print(f"  Rows written: {rows_written}")
    print(f"  Rows skipped (invalid/missing data): {rows_skipped}")
    print(f"  Rows skipped due to invalid coordinates (0.0): {rows_invalid_coords}")
    if rows_written == 0:
        print("Warning: no valid rows were written to KML. Check your CSV and detected columns above.")

if __name__ == '__main__':
    if len(sys.argv) != 3:
        print("Usage: python3 csv_to_kml.py input.csv output.kml")
        sys.exit(1)
    csv_to_kml(sys.argv[1], sys.argv[2])

