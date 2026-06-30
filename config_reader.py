import xml.etree.ElementTree as ET
from pykml import parser
from pyproj import CRS
import json


class ConfigReader:
    def __init__(self, data_dir):
        self.data_dir = data_dir
        self.metadata = {}
        self.boundary = {}
        self.config_scp = {}

    def read_metadata(self):
        metadata_path = self.data_dir / "metadata.xml"
        if not metadata_path.exists():
            return None

        tree = ET.parse(str(metadata_path))
        root = tree.getroot()

        srs_element = root.find("SRS")
        srs_origin_element = root.find("SRSOrigin")

        if srs_element is not None:
            self.metadata["srs"] = srs_element.text.strip()

        if srs_origin_element is not None:
            origin_str = srs_origin_element.text.strip()
            origin_coords = list(map(float, origin_str.split(",")))
            self.metadata["origin"] = {
                "x": origin_coords[0],
                "y": origin_coords[1],
                "z": origin_coords[2]
            }

        return self.metadata

    def read_boundary(self):
        kml_path = self.data_dir / "boundary.kml"
        if not kml_path.exists():
            return None

        with open(str(kml_path), 'r', encoding='utf-8') as f:
            doc = parser.parse(f).getroot()

        placemarks = doc.findall(".//{http://www.opengis.net/kml/2.2}Placemark")
        for pm in placemarks:
            name = pm.find("{http://www.opengis.net/kml/2.2}name").text
            coords_str = pm.find(".//{http://www.opengis.net/kml/2.2}coordinates").text
            coords = []
            for coord in coords_str.strip().split():
                lon, lat, height = map(float, coord.split(","))
                coords.append({"lon": lon, "lat": lat, "height": height})
            self.boundary[name] = coords

        return self.boundary

    def read_config_scp(self):
        scp_path = self.data_dir / "Data" / "Config.scp"
        if not scp_path.exists():
            return None

        tree = ET.parse(str(scp_path))
        root = tree.getroot()

        ns = {"sml": "http://www.supermap.com/SuperMapCache/vectorltile"}

        version = root.find("sml:Version", ns)
        if version is not None:
            self.config_scp["version"] = version.text

        file_type = root.find("sml:FileType", ns)
        if file_type is not None:
            self.config_scp["file_type"] = file_type.text

        height_range = root.find("sml:HeightRange", ns)
        if height_range is not None:
            max_h = height_range.find("sml:MaxHeight", ns)
            min_h = height_range.find("sml:MinHeight", ns)
            self.config_scp["height_range"] = {
                "max": float(max_h.text) if max_h is not None else None,
                "min": float(min_h.text) if min_h is not None else None
            }

        position = root.find("sml:Position", ns)
        if position is not None:
            x = position.find("sml:X", ns)
            y = position.find("sml:Y", ns)
            z = position.find("sml:Z", ns)
            self.config_scp["position"] = {
                "x": float(x.text) if x is not None else None,
                "y": float(y.text) if y is not None else None,
                "z": float(z.text) if z is not None else None
            }

        bbox = root.find("sml:BoundingBox", ns)
        if bbox is not None:
            self.config_scp["bounding_box"] = {
                "min_x": float(bbox.find("sml:MinX", ns).text),
                "min_y": float(bbox.find("sml:MinY", ns).text),
                "min_z": float(bbox.find("sml:MinZ", ns).text),
                "max_x": float(bbox.find("sml:MaxX", ns).text),
                "max_y": float(bbox.find("sml:MaxY", ns).text),
                "max_z": float(bbox.find("sml:MaxZ", ns).text)
            }

        osg_files = root.find("sml:OSGFiles", ns)
        if osg_files is not None:
            files = []
            for file_elem in osg_files.findall("sml:Files", ns):
                file_name = file_elem.find("sml:FileName", ns)
                bs = file_elem.find("sml:BoundingSphere", ns)
                file_info = {
                    "file_name": file_name.text if file_name is not None else None
                }
                if bs is not None:
                    file_info["bounding_sphere"] = {
                        "center_x": float(bs.find("sml:CenterX", ns).text),
                        "center_y": float(bs.find("sml:CenterY", ns).text),
                        "center_z": float(bs.find("sml:CenterZ", ns).text),
                        "radius": float(bs.find("sml:Radius", ns).text)
                    }
                files.append(file_info)
            self.config_scp["osg_files"] = files

        crs = root.find("sml:CoordinateReferenceSystem", ns)
        if crs is not None:
            name = crs.find("sml:Name", ns)
            epsg = crs.find("sml:EPSGCode", ns)
            srs = crs.find("sml:SRS", ns)
            self.config_scp["crs"] = {
                "name": name.text if name is not None else None,
                "epsg": int(epsg.text) if epsg is not None else None,
                "srs": srs.text if srs is not None else None
            }

        return self.config_scp

    def get_crs(self):
        if "crs" in self.config_scp and self.config_scp["crs"]["srs"]:
            return CRS.from_wkt(self.config_scp["crs"]["srs"])
        elif "srs" in self.metadata:
            return CRS.from_wkt(self.metadata["srs"])
        return None

    def get_origin(self):
        if "origin" in self.metadata:
            return self.metadata["origin"]
        elif "position" in self.config_scp:
            return self.config_scp["position"]
        return None

    def get_tile_bounding_spheres(self):
        if "osg_files" not in self.config_scp:
            return {}

        result = {}
        for file_info in self.config_scp["osg_files"]:
            if file_info["file_name"]:
                tile_name = file_info["file_name"].split("/")[-1].replace(".osgb", "")
                result[tile_name] = file_info.get("bounding_sphere")
        return result

    def get_tile_boundary_wgs84(self, tile_name):
        if tile_name in self.boundary:
            return self.boundary[tile_name]
        return None

    def read_all(self):
        self.read_metadata()
        self.read_boundary()
        self.read_config_scp()
        return {
            "metadata": self.metadata,
            "boundary": self.boundary,
            "config_scp": self.config_scp
        }