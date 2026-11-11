"""Terrain and public node inputs for the MeshCore plotter."""
import json
import math
import re
import ssl
import tempfile
import time
from datetime import datetime, timezone
from propagation import load_dem, path_loss, MissingElevation
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode

import certifi
from PIL import Image

CACHE = Path(tempfile.gettempdir()) / 'meshcore-plotter'
MILE = 1609.344
FOOT = 0.3048
LOS_RADIUS = 5000
EARTH = 6_371_000
NODE_FEED = 'https://map.meshcore.io/api/v1/nodes'

TLS_CONTEXT = ssl.create_default_context()
TLS_CONTEXT.load_verify_locations(cafile=certifi.where())

def request(url, timeout=35):
    return urlopen(Request(url, headers={'User-Agent': 'MeshCore-Coverage-Plotter/0.1'}),
                   timeout=timeout, context=TLS_CONTEXT)

def geocode(address):
    query = urlencode(dict(address=address, benchmark='Public_AR_Current', format='json'))
    url = 'https://geocoding.geo.census.gov/geocoder/locations/onelineaddress?' + query
    payload = None
    for attempt in range(3):
        try:
            with request(url, timeout=20) as response:
                payload = json.load(response)
            break
        except HTTPError as error:
            if error.code in (408, 429, 500, 502, 503, 504) and attempt < 2:
                time.sleep(attempt + 1)
                continue
            raise ValueError(f'Census address lookup returned HTTP {error.code}. Try again or enter GPS coordinates.') from error
        except (URLError, TimeoutError, OSError) as error:
            if attempt < 2:
                time.sleep(attempt + 1)
                continue
            reason = getattr(error, 'reason', error)
            raise ValueError(f'Could not reach the Census address service ({reason}). Check internet access and try again, or enter GPS coordinates.') from error
        except (ValueError, KeyError, TypeError) as error:
            raise ValueError('The Census address service returned an invalid response. Try again or enter GPS coordinates.') from error
    try:
        matches = payload['result']['addressMatches']
    except (TypeError, KeyError) as error:
        raise ValueError('The Census address service returned an invalid response. Try again or enter GPS coordinates.') from error
    if not matches:
        raise ValueError('No address match. Check the street, city, state and ZIP, or enter GPS coordinates.')
    if len(matches) != 1:
        raise ValueError('The address has multiple matches. Add the ZIP code or enter GPS coordinates.')
    match = matches[0]
    entered_zip = re.search(r'\b(\d{5})(?:-\d{4})?\b', address)
    matched_zip = match.get('addressComponents', {}).get('zip')
    if entered_zip and matched_zip and entered_zip.group(1) != matched_zip:
        raise ValueError(f"Census matched this address to ZIP {matched_zip}, not the entered ZIP {entered_zip.group(1)}. Verify the address or enter GPS coordinates.")
    directions = dict(north='N', south='S', east='E', west='W',
                      northeast='NE', northwest='NW', southeast='SE', southwest='SW')
    prefix = re.match(r'^\d+[A-Za-z]?\s+([A-Za-z]+)\.?\s+', address)
    if prefix:
        token = prefix[1].lower()
        expected = directions.get(token, token.upper())
        if expected in directions.values() and expected != match.get('addressComponents', {}).get('preDirection'):
            raise ValueError(f"The address lookup returned {match['matchedAddress']}. "
                             "Check the street direction or enter GPS coordinates.")
    coords = match['coordinates']
    return (coords['y'], coords['x']), match['matchedAddress']

def cached(url, name, ttl=None, record=None):
    import time
    path = CACHE / name
    if path.exists() and (ttl is None or time.time() - path.stat().st_mtime < ttl):
        if record:
            record('Reused cache', path.stat().st_mtime)
        return path
    if record:
        record("Downloading", time.time())
    CACHE.mkdir(parents=True, exist_ok=True)
    for attempt in range(3):
        try:
            with request(url,timeout=90 if not name.endswith('.json') else 35) as response:
                data = response.read()
            break
        except (HTTPError,URLError,TimeoutError) as error:
            if attempt==2 or (isinstance(error,HTTPError) and error.code not in (408,429,500,502,503,504)):
                raise
            if record:
                record('Retrying download',time.time())
            time.sleep(attempt+1)
    # Validate before publishing to the cache.
    if name.endswith('.json'):
        json.loads(data)
    else:
        import io
        with Image.open(io.BytesIO(data)) as tif:
            tif.verify()
    with tempfile.NamedTemporaryFile(dir=CACHE, delete=False) as out:
        out.write(data)
    Path(out.name).replace(path)
    if record:
        record('Downloaded', path.stat().st_mtime)
    return path

def distance(a,b):
    lat1,lon1=map(math.radians,a)
    lat2,lon2=map(math.radians,b)
    k=math.sin((lat2-lat1)/2)**2+math.cos(lat1)*math.cos(lat2)*math.sin((lon2-lon1)/2)**2
    return 2*EARTH*math.asin(min(1,math.sqrt(k)))

def destination(origin,bearing,meters):
    lat,lon=map(math.radians,origin)
    d=meters/EARTH
    angle=math.radians(bearing)
    y=math.asin(math.sin(lat)*math.cos(d)+math.cos(lat)*math.sin(d)*math.cos(angle))
    x=lon+math.atan2(math.sin(angle)*math.sin(d)*math.cos(lat),math.cos(d)-math.sin(lat)*math.sin(y))
    return math.degrees(y),math.degrees(x)

def nearby(site,radius,radio,read_cache):
    nodes=json.loads(read_cache(NODE_FEED,'nodes.json',6*3600).read_bytes())
    matches=[]
    for n in nodes:
        point=(n.get('adv_lat'),n.get('adv_lon'))
        if n.get('type')!=2 or not all(isinstance(v,(int,float)) for v in point):
            continue
        if not (abs(point[0]-site[0])<1 and abs(point[1]-site[1])<2):
            continue
        params=n.get('params') or {}
        if tuple(params.get(k) for k in ('freq','bw','sf','cr'))!=radio:
            continue
        d=distance(site,point)
        if 105<=d<=radius*MILE:
            matches.append((d,str(n.get('adv_name') or 'Unnamed repeater')[:60],point,
                            (n.get('last_advert') or n.get('updated_date') or 'unknown')[:10]))
    return sorted(matches)[:5]


def assess(dem,origin,target,heights,rx,freq,keep_profile=False,model_itm=True):
    length=distance(origin,target)
    steps=max(2,math.ceil(length/25))
    elevations=[]
    for i in range(steps+1):
        t=i/steps
        lat,lon=(a+(b-a)*t for a,b in zip(origin,target))
        elevations.append(dem.sample(lat,lon))
    clearance=[math.inf]*len(heights)
    ratios=clearance.copy()
    profile=[]
    bottlenecks=[None]*len(heights)
    for i,ground_z in enumerate(elevations):
        t=i/steps
        corrected=ground_z+length**2*t*(1-t)/(2*EARTH*4/3)
        radius=math.sqrt((299.792458/freq)*length*t*(1-t))
        rays=[(elevations[0]+h)*(1-t)+(elevations[-1]+rx)*t for h in heights]
        if 0<i<steps:
            for j,ray in enumerate(rays):
                gap=ray-corrected
                clearance[j]=min(clearance[j],gap)
                ratios[j]=min(ratios[j],gap/radius)
                if keep_profile and (bottlenecks[j] is None or gap-.6*radius<bottlenecks[j]['fresnel_clearance']):
                    bottlenecks[j]=dict(point=tuple(a+(b-a)*t for a,b in zip(origin,target)),
                                       miles=length*t/MILE,clearance=gap,fresnel_clearance=gap-.6*radius)
        if keep_profile:
            ray=rays[len(rays)//2]
            profile.append((length*t/MILE,corrected,ray,ray-.6*radius))
    losses=[path_loss(elevations,length/steps,h,rx,freq) for h in heights] if model_itm else []
    return dict(miles=length/MILE,clearance=clearance,ratios=ratios,profile=profile,losses=losses,bottlenecks=bottlenecks)

def terrain_map(dem,origin):
    size=241
    lat,lon=origin
    lon_scale=111195*math.cos(math.radians(lat))
    values=[]
    for row in range(size):
        for col in range(size):
            try:
                values.append(dem.sample(lat+(120-row)*5000/120/111195,
                                         lon+(col-120)*5000/120/lon_scale))
            except MissingElevation:
                values.append(None)
    available=[z for z in values if z is not None]
    lo,hi=min(available),max(available)
    colors=[]
    for value in values:
        if value is None:
            colors.append((225,225,225))
        else:
            t=(value-lo)/max(1,hi-lo)
            colors.append(tuple(round(a+(b-a)*t) for a,b in zip((224,242,241),(26,64,76))))
    image=Image.new('RGB',(size,size))
    image.putdata(colors)
    return image,lo,hi

def run(settings, progress):
    origin=settings['origin']
    heights=settings['heights']
    freq=settings['radio'][0]
    radius=settings['radius']*MILE
    warnings=[]
    paths=[]
    provenance={}

    def cache_reader(source):
        def record(status, timestamp):
            progress(f'Data: {source} - {status}')
            if status in ('Downloading','Retrying download'):
                return
            when=datetime.fromtimestamp(timestamp,timezone.utc)
            provenance[source]=(status,when.strftime('%Y-%m-%d %H:%M UTC'))
        return lambda url,name,ttl=None:cached(url,name,ttl,record)

    targets=list(settings['targets'])
    if settings['discover']:
        progress('Looking up public MeshCore repeaters...')
        try:
            found=nearby(origin,settings['radius'],settings['radio'],cache_reader('Public repeater feed'))
        except (OSError, ValueError) as error:
            provenance['Public repeater feed']=('Unavailable','-')
            warnings.append(f'Public repeater lookup unavailable ({type(error).__name__}).')
        else:
            targets.extend((name,point,settings['repeater_height'],'Public repeater',seen)
                           for _,name,point,seen in found)
            if not found:
                warnings.append('No matching public repeater listings found within the selected radius.')
    else:
        provenance['Public repeater feed']=('Disabled','-')
    progress('Extracting USGS 3DEP bare-earth elevations...')
    dem=load_dem(origin,max(LOS_RADIUS,radius),[point for _,point,_,_,_ in targets],
                 cache_reader('USGS 3DEP terrain grid'))
    spacing=(dem.dx*111195*math.cos(math.radians(origin[0])),dem.dy*111195)
    progress(f'Data: USGS terrain spacing - {spacing[0]/FOOT:.0f} ft east-west / {spacing[1]/FOOT:.0f} ft north-south')
    if max(spacing)>35:
        warnings.append(f'Terrain grid spacing is approximately {max(spacing)/FOOT:.0f} ft; small terrain features may be smoothed. Profile sampling does not add terrain detail.')
    if settings['radius']>20:
        warnings.append('Extended-radius assessment: geographic samples are more widely spaced. Use smaller-radius studies to inspect local coverage.')
    start_z=dem.sample(*origin)
    progress('Mapping the local terrain...')
    terrain_image=terrain_map(dem,origin)
    for name,point,rx,kind,seen in targets:
        progress(f'Modeling terrain and ITM for {name}...')
        try:
            result=assess(dem,origin,point,heights,rx,freq,True)
        except MissingElevation:
            warnings.append(f'Skipped {name}: the path crosses a USGS elevation gap.')
            continue
        paths.append(dict(name=name,point=point,rx=rx,kind=kind,seen=seen,source='USGS 3DEP DEM',**result))
    los=[]
    progress(f'Screening terrain line of sight within {LOS_RADIUS/MILE:.2f} miles...')
    for ring in range(1,11):
        meters=ring*LOS_RADIUS/10
        for bearing in range(0,360,5):
            try:
                path=assess(dem,origin,destination(origin,bearing,meters),heights,
                            settings['handheld'],freq,model_itm=False)
                scores=[2 if x>=.6 else 1 if x>=0 else 0 for x in path['ratios']]
            except MissingElevation:
                scores=[None]*len(heights)
            los.append((meters/MILE,bearing,scores))
    itm=[]
    for ring in range(1,9):
        progress(f'Running Longley-Rice ITM propagation, ring {ring} of 8...')
        meters=radius*ring/8
        for bearing in range(0,360,5):
            try:
                path=assess(dem,origin,destination(origin,bearing,meters),heights,
                            settings['handheld'],freq)
                losses=path['losses']
            except MissingElevation:
                losses=[(None,'USGS data gap')]*len(heights)
            itm.append((meters/MILE,bearing,losses))
    if not any(loss is not None for _,_,row in itm for loss,_ in row):
        raise ValueError('ITM could not compute any propagation samples. Check the site and antenna heights.')
    return dict(_dem=dem,_targets=targets,paths=paths,los=los,itm=itm,start_z=start_z,base='USGS 3DEP bare-earth DEM',
                warnings=warnings,provenance=provenance,terrain_image=terrain_image,spacing=(
                    dem.dx*111195*math.cos(math.radians(origin[0])),dem.dy*111195))
