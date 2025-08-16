# v0.9

import os
import csv
from xml.etree.ElementTree import Element, SubElement, tostring
from xml.dom import minidom
import dialogs
import ui

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

def process_csv(csv_file, output_dir):
    input_basename = os.path.splitext(os.path.basename(csv_file))[0]
    output_file = os.path.join(output_dir, input_basename + ".kml")
    
    with open(csv_file, newline='', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames
        
        ts_col = find_column(fieldnames, POSSIBLE_HEADERS["timestamp"])
        lat_col = find_column(fieldnames, POSSIBLE_HEADERS["latitude"])
        lon_col = find_column(fieldnames, POSSIBLE_HEADERS["longitude"])
        ele_col = find_column(fieldnames, POSSIBLE_HEADERS["elevation"])
        
        log = []
        log.append(f"Processing: {os.path.basename(csv_file)}")
        log.append("Detected columns:")
        log.append(f"  timestamp -> {repr(ts_col)}")
        log.append(f"  latitude  -> {repr(lat_col)}")
        log.append(f"  longitude -> {repr(lon_col)}")
        log.append(f"  elevation -> {repr(ele_col)}")
        
        if not all([ts_col, lat_col, lon_col, ele_col]):
            log.append("Error: Could not detect all required columns. Skipping.")
            return "\n".join(log)
        
        kml = Element('kml', xmlns="http://www.opengis.net/kml/2.2", **{"xmlns:gx": "http://www.google.com/kml/ext/2.2"})
        doc = SubElement(kml, 'Document')
        name = SubElement(doc, 'name')
        name.text = f"Drone Flight Track - {input_basename}"
        
        placemark = SubElement(doc, 'Placemark')
        pm_name = SubElement(placemark, 'name')
        pm_name.text = f"Flight Path - {input_basename}"
        
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
        with open(output_file, 'w', encoding='utf-8') as out:
            out.write(reparsed.toprettyxml(indent="  "))
        
        log.append(f"Saved KML: {output_file}")
        log.append(f"Rows processed: {total_rows}")
        log.append(f"  Rows written: {rows_written}")
        log.append(f"  Rows skipped (invalid/missing data): {rows_skipped}")
        log.append(f"  Rows skipped due to invalid coordinates (0.0): {rows_invalid_coords}")
        
        return "\n".join(log)

def main():
    base_dir = os.path.expanduser('~/Documents')
    input_dir = os.path.join(base_dir, 'DroneCSV_Input')
    output_dir = os.path.join(base_dir, 'KML_Output')
    
    os.makedirs(input_dir, exist_ok=True)
    os.makedirs(output_dir, exist_ok=True)
    
    csv_files = [os.path.join(input_dir, f) for f in os.listdir(input_dir) if f.lower().endswith('.csv')]
    if not csv_files:
        dialogs.alert("No CSV files found", f"No CSV files found in:\n{input_dir}", "OK")
        return
    
    logs = []
    for f in csv_files:
        logs.append(process_csv(f, output_dir))
    
    summary = f"Input folder:\n{input_dir}\n\nOutput folder:\n{output_dir}\n\n" + "\n\n".join(logs)
    
    text_view = ui.TextView()
    text_view.text = summary
    text_view.editable = False
    text_view.font = ('Menlo', 12)
    text_view.present('sheet')

if __name__ == '__main__':
    main()
