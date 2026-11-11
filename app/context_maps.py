"""Site-context basemaps and street-level links."""
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from io import BytesIO
import math
from urllib.parse import urlencode

from PIL import Image

NATIONAL_MAP = 'https://basemap.nationalmap.gov/arcgis/rest/services/'
LAYERS = [
    ('Aerial imagery', NATIONAL_MAP+'USGSImageryOnly/MapServer', 1.2,
     'USDA and USGS The National Map, orthoimagery'),
    ('Topographic map', NATIONAL_MAP+'USGSTopo/MapServer', 6.22,
     'USGS The National Map, USGS Topo basemap'),
    ('Street map', 'https://server.arcgisonline.com/ArcGIS/rest/services/World_Street_Map/MapServer', 1.2,
     'Esri, HERE, Garmin, USGS, Intermap, INCREMENT P, NRCan, Esri Japan, METI, Esri China (Hong Kong), Esri Korea, Esri Thailand, NGCC, OpenStreetMap contributors, and the GIS User Community'),
]
ASPECT = 1040/440

def street_view(origin):
    lat,lon=origin
    return 'https://www.google.com/maps/@?' + urlencode(
        dict(api=1,map_action='pano',viewpoint=f'{lat:.6f},{lon:.6f}'))

def fetch(origin, request):
    lat,lon=map(math.radians,origin)
    earth=6378137
    cx=earth*lon
    cy=earth*math.asinh(math.tan(lat))

    def layer(entry):
        title,url,miles,credit=entry
        half_width=miles*1609.344/(2*math.cos(lat))
        half_height=half_width/ASPECT
        bbox=','.join(f'{value:.3f}' for value in
                      (cx-half_width,cy-half_height,cx+half_width,cy+half_height))
        query=urlencode(dict(bbox=bbox,bboxSR=3857,imageSR=3857,
                             size='1040,440',format='png24',f='image'))
        image=None
        try:
            with request(url+'/export?'+query,timeout=12) as response:
                with Image.open(BytesIO(response.read())) as png:
                    if png.size!=(1040,440) or png.convert('RGB').getextrema() == ((255,255),)*3:
                        raise ValueError('Basemap returned no usable imagery.')
                    image=png.convert('RGB')
        except (OSError, ValueError):
            pass
        fetched=datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC') if image is not None else '-'
        return dict(title=title,source=url,credit=credit,width_miles=miles,image=image,fetched=fetched)
    with ThreadPoolExecutor(max_workers=len(LAYERS)) as pool:
        return list(pool.map(layer,LAYERS))


def square_geometry(origin,radius_miles):
    lat,lon=map(math.radians,origin)
    earth=6378137
    cx,cy=earth*lon,earth*math.asinh(math.tan(lat))
    span=radius_miles*1609.344/math.cos(lat)
    return cx-span,cy-span,cx+span,cy+span

def map_point(bounds,x_fraction,y_fraction):
    west,south,east,north=bounds
    x=west+(east-west)*x_fraction
    y=north-(north-south)*y_fraction
    return math.degrees(math.atan(math.sinh(y/6378137))),math.degrees(x/6378137)

def point_on_map(bounds,point):
    lat,lon=map(math.radians,point)
    west,south,east,north=bounds
    return ((6378137*lon-west)/(east-west),
            (north-6378137*math.asinh(math.tan(lat)))/(north-south))

def square(origin,radius_miles,request,layer='Aerial'):
    bounds=square_geometry(origin,radius_miles)
    service=LAYERS[0] if layer=='Aerial' else LAYERS[1] if layer=='Topo' else LAYERS[2]
    query=urlencode(dict(bbox=','.join(map(str,bounds)),bboxSR=3857,imageSR=3857,
                         size='800,800',format='png24',f='image'))
    with request(service[1]+'/export?'+query,timeout=15) as response:
        with Image.open(BytesIO(response.read())) as image:
            if image.size!=(800,800):
                raise ValueError('Map provider returned an unexpected image.')
            return dict(image=image.convert('RGB'),bounds=bounds,credit=service[3],source=service[1],
                        fetched=datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC'))
