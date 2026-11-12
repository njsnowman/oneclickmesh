"""USGS 3DEP raster sampling and NTIA ITM point-to-point bindings."""
from ctypes import CDLL, POINTER, byref, c_double, c_int, c_long
from functools import lru_cache
from pathlib import Path
from urllib.parse import urlencode
import hashlib
import math
import sys

from PIL import Image

SERVICE = 'https://elevation.nationalmap.gov/arcgis/rest/services/3DEPElevation/ImageServer/exportImage'

class MissingElevation(ValueError):
    pass

class DEM:
    def __init__(self, path):
        with Image.open(path) as tif:
            if tif.mode != 'F':
                raise ValueError('USGS did not return a float elevation raster.')
            self.dx, self.dy, _ = tif.tag_v2[33550]
            _, _, _, self.west, self.north, _ = tif.tag_v2[33922]
            self.pixels = tif.copy()
            self.width, self.height = self.pixels.size

    def sample(self, lat, lon):
        x = math.floor((lon - self.west) / self.dx)
        y = math.floor((self.north - lat) / self.dy)
        if 0 <= x < self.width and 0 <= y < self.height:
            z = self.pixels.getpixel((x,y))
            if math.isfinite(z) and -500 < z < 9000:
                return z
        raise MissingElevation(f'USGS elevation is unavailable at {lat:.5f}, {lon:.5f}.')

def load_dem(origin, radius_m, targets, cached):
    lat, lon = origin
    lon_scale = 111195 * math.cos(math.radians(lat))
    pad = radius_m + 125
    west, east = lon-pad/lon_scale, lon+pad/lon_scale
    south, north = lat-pad/111195, lat+pad/111195
    for y,x in targets:
        west, east = min(west,x-.002), max(east,x+.002)
        south, north = min(south,y-.002), max(north,y+.002)
    width = min(3072, math.ceil((east-west)*lon_scale/30))
    height = min(3072, math.ceil((north-south)*111195/30))
    def fetch(bounds,columns,rows):
        bbox=','.join(f'{v:.7f}' for v in bounds)
        query=urlencode(dict(bbox=bbox,bboxSR=4326,imageSR=4326,size=f'{columns},{rows}',
                             format='tiff',pixelType='F32',adjustAspectRatio='false',
                             interpolation='RSP_BilinearInterpolation',f='image'))
        name='usgs-'+hashlib.sha256(query.encode()).hexdigest()[:24]+'.tif'
        return DEM(cached(SERVICE+'?'+query,name))
    try:
        if radius_m>20*1609.344:
            # Smaller regional requests avoid oversized single USGS export jobs.
            tiles=[]
            for row in range(2):
                for col in range(2):
                    bounds=(west+(east-west)*col/2,south+(north-south)*row/2,
                            west+(east-west)*(col+1)/2,south+(north-south)*(row+1)/2)
                    tiles.append(fetch(bounds,math.ceil(width/2),math.ceil(height/2)))
            return TiledDEM(tiles)
        return fetch((west,south,east,north),width,height)
    except (OSError, KeyError, ValueError) as error:
        raise ValueError(f'USGS 3DEP terrain download could not be used. {error}') from error

class TiledDEM:
    def __init__(self,tiles):
        self.tiles=tiles
        self.dx=max(tile.dx for tile in tiles)
        self.dy=max(tile.dy for tile in tiles)

    def sample(self,lat,lon):
        for tile in self.tiles:
            if tile.west<=lon<tile.west+tile.width*tile.dx and tile.north-tile.height*tile.dy<lat<=tile.north:
                try:
                    return tile.sample(lat,lon)
                except MissingElevation:
                    continue
        raise MissingElevation(f'USGS elevation is unavailable at {lat:.5f}, {lon:.5f}.')

@lru_cache(maxsize=1)
def itm_function():
    library_name={
        'win32':'itm.dll',
        'darwin':'libitm.dylib',
    }.get(sys.platform,'libitm.so')
    locations=[Path(__file__).resolve().with_name(library_name)]
    if getattr(sys,'_MEIPASS',None):
        locations.insert(0,Path(sys._MEIPASS)/library_name)
    library_path=next((path for path in locations if path.is_file()),locations[0])
    library = CDLL(str(library_path))
    fn = library.ITM_P2P_TLS
    fn.argtypes = [c_double,c_double,POINTER(c_double),c_int,c_double,c_double,
                   c_int,c_double,c_double,c_int,c_double,c_double,c_double,
                   POINTER(c_double),POINTER(c_long)]
    fn.restype = c_int
    return fn

def path_loss(elevations, step, tx, rx, mhz):
    profile = (c_double * (len(elevations)+2))(len(elevations)-1, step, *elevations)
    attenuation, warnings = c_double(), c_long()
    status = itm_function()(tx,rx,profile,5,301,mhz,1,15,.005,0,50,50,50,
                            byref(attenuation),byref(warnings))
    if status not in (0,1) or not math.isfinite(attenuation.value):
        return None, f'ITM error {status}'
    return attenuation.value, f'0x{warnings.value:04X}' if warnings.value else ''
