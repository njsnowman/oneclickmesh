"""Geographic sampling and comparable deployment scenarios."""
import terrain as t
from datetime import datetime,timezone
import context_maps as maps
from planning import margins
from PIL import Image, ImageDraw

def enhance(s,r,progress):
    dem=r.pop('_dem')
    bounds=maps.square_geometry(s['origin'],s['radius'])
    n=25 if s['quality']=='Quick' else 51
    grid=[]
    for row in range(n):
        progress(f"Geographic {s['quality'].lower()} coverage: row {row+1} of {n}...")
        for col in range(n):
            point=maps.map_point(bounds,col/(n-1),row/(n-1))
            distance=t.distance(s['origin'],point)
            if not 105<=distance<=s['radius']*t.MILE:
                continue
            try:
                losses=t.assess(dem,s['origin'],point,s['heights'],s['handheld'],s['radio'][0])['losses']
            except t.MissingElevation:
                losses=[(None,'Elevation gap')]*len(s['heights'])
            grid.append(dict(point=point,x=col/(n-1),y=row/(n-1),losses=losses))
    r['grid']=grid
    r['grid_spacing']=2*s['radius']/(n-1)
    try:
        progress('Loading geographic coverage basemap...')
        background=maps.square(s['origin'],s['radius'],t.request,'Street')
    except (OSError,ValueError):
        background=dict(image=Image.new('RGB',(800,800),'#EDF1F4'),bounds=bounds,
                        credit='Basemap unavailable; geographic sample positions retained',source='',fetched='-')
    progress('Data: Coverage basemap - '+('Downloaded' if background['fetched']!='-' else 'Unavailable'))
    r['overlay_base']=background
    r['overlays']=[]
    for i,h in enumerate(s['heights']):
        image=background['image'].convert('RGBA')
        layer=Image.new('RGBA',image.size)
        draw=ImageDraw.Draw(layer)
        for cell in grid:
            loss=cell['losses'][i][0]
            margin=margins(loss,s['budget'],True)[2] if loss is not None else None
            color=(0,110,85,185) if margin is not None and margin>=s['budget']['reserve'] else (195,148,30,185) if margin is not None and margin>=0 else (178,63,40,185) if margin is not None else (130,130,130,185)
            x,y=cell['x']*800,cell['y']*800
            size=max(3,800/(n-1)*.38)
            draw.rectangle((x-size,y-size,x+size,y+size),fill=color)
        draw.ellipse((394,394,406,406),fill='white',outline='black',width=2)
        r['overlays'].append(Image.alpha_composite(image,layer).convert('RGB'))
    r['field']=[]
    for j,item in enumerate(s['measurements']):
        if j%50==0:
            progress(f'Modeling field-test points: {j+1} of {len(s["measurements"])}...')
        item=dict(item)
        point=(item['latitude'],item['longitude'])
        item['prediction']=None
        if 105<=t.distance(s['origin'],point)<=s['radius']*t.MILE:
            try:
                item['prediction']=t.assess(dem,s['origin'],point,s['heights'],s['handheld'],s['radio'][0])['losses']
            except t.MissingElevation:
                pass
        r['field'].append(item)
    r['scenarios']=[dict(name=s['site'],paths=r['paths'],error='',origin=s['origin'])]
    common=r['_targets']
    r['map_locations']=location_register(s,r)
    r['deployment_base']=deployment_basemap(s,r,progress)
    for name,point in s['alternatives']:
        progress(f'Comparing candidate site: {name}...')
        scenario=dict(name=name,origin=point,paths=[],error='',grid_losses=[[(None,'Not assessed')]*len(s['heights']) for cell in grid])
        try:
            if any(not 105<=t.distance(point,dest)<=40*t.MILE for _,dest,_,_,_ in common):
                raise ValueError('A common destination is outside the supported 345 ft to 40 mi path range.')
            def record(status,timestamp):
                progress(f'Data: Candidate terrain {name} - {status}')
                if status in ('Downloading','Retrying download'):
                    return
                r['provenance']['Candidate terrain: '+name]=(status,datetime.fromtimestamp(timestamp,timezone.utc).strftime('%Y-%m-%d %H:%M UTC'))
            def read_cache(url,filename,ttl=None):
                return t.cached(url,filename,ttl,record)
            supported=[cell['point'] for cell in grid if 105<=t.distance(point,cell['point'])<=40*t.MILE]
            other=t.load_dem(point,max(t.LOS_RADIUS,s['radius']*t.MILE),[x[1] for x in common]+supported,read_cache)
            import math
            scenario['spacing']=(other.dx*111195*math.cos(math.radians(point[0])),other.dy*111195)
            for label,dest,rx,kind,seen in common:
                try:
                    path=t.assess(other,point,dest,s['heights'],rx,s['radio'][0],True)
                    scenario['paths'].append(dict(name=label,point=dest,rx=rx,kind=kind,seen=seen,**path))
                except t.MissingElevation:
                    scenario['error']='One or more destination paths cross missing terrain.'
            for cell_index,cell in enumerate(grid):
                if cell_index%25==0:
                    progress(f'Comparing candidate coverage: {name}, sample {cell_index+1} of {len(grid)}...')
                if not 105<=t.distance(point,cell['point'])<=40*t.MILE:
                    continue
                try:
                    scenario['grid_losses'][cell_index]=t.assess(other,point,cell['point'],s['heights'],s['handheld'],s['radio'][0])['losses']
                except t.MissingElevation:
                    scenario['grid_losses'][cell_index]=[(None,'Elevation gap')]*len(s['heights'])
        except (OSError,ValueError,t.MissingElevation) as error:
            scenario['error']=str(error)
        r['scenarios'].append(scenario)
    r['common_count']=len(common)


def scenario_rows(s,r):
    rows=[]
    for scenario in r['scenarios']:
        for i,h in enumerate(s['heights']):
            passed=available=0
            for path in scenario['paths']:
                loss=path['losses'][i][0]
                if loss is not None:
                    available+=1
                    passed+=margins(loss,s['budget'],path['kind']=='Handheld')[2]>=s['budget']['reserve']
            rows.append([scenario['name'],f'{h/t.FOOT:g} ft',f'{passed} / {r["common_count"]}',
                         'Incomplete' if scenario['error'] or available<r['common_count'] else 'Complete'])
    return rows


def location_register(s,r):
    locations=[dict(number=1,name=s['site'],point=s['origin'],kind='Primary station')]
    for name,point,rx,kind,seen in r['_targets']:
        locations.append(dict(number=len(locations)+1,name=name,point=point,kind=kind,rx=rx))
    for name,point in s['alternatives']:
        locations.append(dict(number=len(locations)+1,name=name,point=point,kind='Candidate station'))
    return locations


def deployment_basemap(s,r,progress):
    # Fit all named endpoints; this overview extent is distinct from the coverage radius.
    points=[row['point'] for row in r['map_locations']]
    unit=maps.square_geometry(s['origin'],1)
    xy=[maps.point_on_map(unit,p) for p in points]
    xs,ys=zip(*xy)
    center=maps.map_point(unit,(min(xs)+max(xs))/2,(min(ys)+max(ys))/2)
    half=max(.5,max(max(xs)-min(xs),max(ys)-min(ys))*1.18)
    # Convert the original center's projected mile to a mile at the fitted center.
    import math
    radius=half*math.cos(math.radians(center[0]))/math.cos(math.radians(s['origin'][0]))
    bounds=maps.square_geometry(center,radius)
    progress('Loading annotated deployment basemap...')
    result=None
    existing=r.get('overlay_base')
    if existing and all(0<=v<=1 for p in points for v in maps.point_on_map(existing['bounds'],p)):
        result=dict(existing)
        progress('Data: Reused coverage basemap for numbered site overview')
    for layer in (() if result else ('Street','Street','Topo')):
        try:
            result=maps.square(center,radius,t.request,layer)
            break
        except (OSError,ValueError):
            progress(f'Data: Deployment {layer.lower()} map unavailable; trying another request...')
    if result is None:
        result=dict(image=Image.new('RGB',(800,800),'#EDF1F4'),bounds=bounds,
                    credit='Basemap unavailable; geographic positions retained',source='',fetched='-')
    result['center']=center
    result['radius']=radius
    progress('Data: Deployment basemap - '+('Downloaded' if result['fetched']!='-' else 'Unavailable'))
    r['provenance']['Deployment basemap']=('Downloaded' if result['fetched']!='-' else 'Unavailable',result['fetched'])
    return result


def improvement_category(base_loss,candidate_loss,budget):
    if base_loss is None or candidate_loss is None:
        return 'unknown'
    before=margins(base_loss,budget,True)[2]>=budget['reserve']
    after=margins(candidate_loss,budget,True)[2]>=budget['reserve']
    return 'retained' if before and after else 'gained' if after else 'lost' if before else 'neither'
