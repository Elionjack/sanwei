from pyproj import CRS, Transformer
from pyproj.exceptions import ProjError
import math


class CoordinateTransformer:
    def __init__(self, source_crs_wkt, origin=None):
        self.source_crs = CRS.from_wkt(source_crs_wkt)
        self.target_crs = CRS.from_epsg(4326)
        self.transformer = Transformer.from_crs(
            self.source_crs,
            self.target_crs,
            always_xy=True
        )
        self.origin = origin

    def local_to_wgs84(self, x_local, y_local, z_local=0):
        if self.origin:
            x_absolute = self.origin["x"] + x_local
            y_absolute = self.origin["y"] + y_local
            z_absolute = self.origin["z"] + z_local
        else:
            x_absolute = x_local
            y_absolute = y_local
            z_absolute = z_local

        try:
            lon, lat, height = self.transformer.transform(
                x_absolute, y_absolute, z_absolute,
                errcheck=True
            )
            return {"lon": lon, "lat": lat, "height": height}
        except ProjError as e:
            print(f"Projection error: {e}")
            return None

    def wgs84_to_local(self, lon, lat, height=0):
        try:
            x_absolute, y_absolute, z_absolute = self.transformer.transform(
                lon, lat, height,
                direction="INVERSE",
                errcheck=True
            )

            if self.origin:
                x_local = x_absolute - self.origin["x"]
                y_local = y_absolute - self.origin["y"]
                z_local = z_absolute - self.origin["z"]
            else:
                x_local = x_absolute
                y_local = y_absolute
                z_local = z_absolute

            return {"x": x_local, "y": y_local, "z": z_local}
        except ProjError as e:
            print(f"Projection error: {e}")
            return None

    def bounding_box_to_wgs84(self, min_x, min_y, min_z, max_x, max_y, max_z):
        corners = [
            (min_x, min_y, min_z),
            (min_x, min_y, max_z),
            (min_x, max_y, min_z),
            (min_x, max_y, max_z),
            (max_x, min_y, min_z),
            (max_x, min_y, max_z),
            (max_x, max_y, min_z),
            (max_x, max_y, max_z),
        ]

        lons = []
        lats = []
        heights = []

        for x, y, z in corners:
            result = self.local_to_wgs84(x, y, z)
            if result:
                lons.append(result["lon"])
                lats.append(result["lat"])
                heights.append(result["height"])

        if not lons:
            return None

        return {
            "min_lon": min(lons),
            "min_lat": min(lats),
            "min_height": min(heights),
            "max_lon": max(lons),
            "max_lat": max(lats),
            "max_height": max(heights)
        }

    def bounding_sphere_to_wgs84(self, center_x, center_y, center_z, radius):
        center_wgs84 = self.local_to_wgs84(center_x, center_y, center_z)
        if not center_wgs84:
            return None

        corner_x = center_x + radius
        corner_y = center_y + radius
        corner_z = center_z + radius

        corner_wgs84 = self.local_to_wgs84(corner_x, corner_y, corner_z)
        if not corner_wgs84:
            return None

        dist_lon = abs(corner_wgs84["lon"] - center_wgs84["lon"])
        dist_lat = abs(corner_wgs84["lat"] - center_wgs84["lat"])
        dist_height = abs(corner_wgs84["height"] - center_wgs84["height"])

        return {
            "center": center_wgs84,
            "radius": radius,
            "region": {
                "west": center_wgs84["lon"] - dist_lon,
                "south": center_wgs84["lat"] - dist_lat,
                "east": center_wgs84["lon"] + dist_lon,
                "north": center_wgs84["lat"] + dist_lat,
                "min_height": center_wgs84["height"] - dist_height,
                "max_height": center_wgs84["height"] + dist_height
            }
        }

    def create_region(self, bounding_spheres):
        if not bounding_spheres:
            return None

        all_lons = []
        all_lats = []
        all_heights = []

        for bs in bounding_spheres:
            result = self.bounding_sphere_to_wgs84(
                bs["center_x"],
                bs["center_y"],
                bs["center_z"],
                bs["radius"]
            )
            if result and "region" in result:
                r = result["region"]
                all_lons.extend([r["west"], r["east"]])
                all_lats.extend([r["south"], r["north"]])
                all_heights.extend([r["min_height"], r["max_height"]])

        if not all_lons:
            return None

        return [
            math.radians(min(all_lons)),
            math.radians(min(all_lats)),
            math.radians(max(all_lons)),
            math.radians(max(all_lats)),
            min(all_heights),
            max(all_heights)
        ]

    def get_tile_region(self, tile_name, boundary_wgs84):
        if not boundary_wgs84:
            return None

        lons = [p["lon"] for p in boundary_wgs84]
        lats = [p["lat"] for p in boundary_wgs84]
        heights = [p["height"] for p in boundary_wgs84]

        return [
            math.radians(min(lons)),
            math.radians(min(lats)),
            math.radians(max(lons)),
            math.radians(max(lats)),
            min(heights),
            max(heights)
        ]

    @staticmethod
    def deg_to_rad(degrees):
        return math.radians(degrees)

    @staticmethod
    def rad_to_deg(radians):
        return math.degrees(radians)