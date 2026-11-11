import math
from terrain import FOOT, MILE, LOS_RADIUS
from context_maps import ASPECT, street_view
from pathlib import Path
from xml.sax.saxutils import escape
from reportlab.pdfgen import canvas
from reportlab.lib.colors import HexColor, white
from reportlab.lib.utils import ImageReader
from reportlab.lib.styles import ParagraphStyle
from reportlab.platypus import Paragraph, Table, TableStyle

navy,teal,gray,light,rule,orange=map(HexColor,['#132C3D','#006C65','#49616D','#EDF5F4','#D7E2E5','#9C5123'])
body=ParagraphStyle('body',fontSize=11,leading=16,textColor=navy)
small=ParagraphStyle('small',fontSize=9,leading=13,textColor=gray)
cell=ParagraphStyle('cell',fontSize=9.5,leading=12,textColor=navy)
head=ParagraphStyle('head',fontName='Helvetica-Bold',fontSize=9.5,leading=12,textColor=white)
y=0
page=0

def text(x,y,s,size=10,color=navy,bold=False):
    c.setFillColor(color)
    c.setFont('Helvetica-Bold' if bold else 'Helvetica',size)
    c.drawString(x,y,s)

def start(label,title,subtitle):
    global y,page
    page+=1
    c.bookmarkPage(str(page))
    c.addOutlineEntry(title,str(page))
    c.setFillColor(navy)
    c.rect(0,641,612,151,fill=1,stroke=0)
    c.setFillColor(teal)
    c.rect(48,746,28,4,fill=1,stroke=0)
    text(87,743,label,9,white,True)
    size=min(31,516/max(1,c.stringWidth(title,'Helvetica-Bold',1)))
    text(48,699,title,size,white,True)
    text(49,668,subtitle,11,white)
    y=614

def end():
    assert y>49,(page,y)
    c.setStrokeColor(rule)
    c.line(48,43,564,43)
    text(48,26,'INDIANA MESH ALLIANCE  /  ONE CLICK MESH',8,gray,True)
    text(538,26,f'{page:02d}',8,gray)
    c.showPage()

def p(value,style=body,gap=11):
    global y
    box=Paragraph(value,style)
    _,h=box.wrap(516,700)
    if y-h-gap<60:
        end()
        start('ASSESSMENT CONTINUED','Assessment continued','Additional details and source notes')
    box.drawOn(c,48,y-h)
    y-=h+gap

def sub(value):
    global y
    y-=4
    text(48,y-12,value,13,teal,True)
    y-=22

def basemap(item):
    global y
    sub(item['title'])
    width=516
    height=width/ASPECT
    left,bottom=48,y-height
    if item['image'] is not None:
        c.drawImage(ImageReader(item['image']),left,bottom,width,height)
        cx,cy=left+width/2,bottom+height/2
        c.setFillColor(white)
        c.setStrokeColor(navy)
        c.setLineWidth(1.2)
        c.circle(cx,cy,7,fill=1,stroke=1)
        c.setFillColor(teal)
        c.circle(cx,cy,3,fill=1,stroke=0)
        scale=.25 if item['width_miles']<2 else 1
        length=scale/item['width_miles']*width
        c.setFillColor(white)
        c.rect(left+8,bottom+8,length+14,26,fill=1,stroke=0)
        c.setStrokeColor(navy)
        c.setLineWidth(1)
        c.line(left+15,bottom+15,left+15+length,bottom+15)
        text(left+15,bottom+21,f'{scale:g} mi',8,navy,True)
        c.setFillColor(white)
        c.rect(left+width-29,bottom+height-28,20,19,fill=1,stroke=0)
        text(left+width-22,bottom+height-22,'N',9,navy,True)
    else:
        c.setFillColor(light)
        c.rect(left,bottom,width,height,fill=1,stroke=0)
        text(left+16,bottom+height/2,'Map provider did not return imagery for this run.',11,gray)
    y=bottom-5
    p(f'Source: <link href="{item["source"]}" color="#006C65">{escape(item["credit"])}</link>',small,5)

def callout(title,value):
    global y
    box=Paragraph(value,body)
    _,h=box.wrap(486,700)
    if y-h-57<60:
        end()
        start('ASSESSMENT CONTINUED','Assessment continued','Planning conclusions')
    c.setFillColor(light)
    c.rect(48,y-h-46,516,h+46,fill=1,stroke=0)
    c.setFillColor(teal)
    c.rect(48,y-h-46,3,h+46,fill=1,stroke=0)
    text(63,y-18,title,11,teal,True)
    box.drawOn(c,63,y-31-h)
    y-=h+57

def table(headers,rows,widths,highlight=()):
    global y
    data=[[Paragraph(escape(str(v)),head) for v in headers]]
    data.extend([[Paragraph(escape(str(v)),cell) for v in row] for row in rows])
    t=Table(data,colWidths=widths)
    t.setStyle(TableStyle([
        ('BACKGROUND',(0,0),(-1,0),navy),
        ('ROWBACKGROUNDS',(0,1),(-1,-1),[white,light]),
        ('VALIGN',(0,0),(-1,-1),'MIDDLE'),
        ('TOPPADDING',(0,0),(-1,-1),7),
        ('BOTTOMPADDING',(0,0),(-1,-1),7),
        ('LINEBELOW',(0,1),(-1,-1),.35,rule),
        *[('BACKGROUND',(col,row),(col,row),HexColor('#CCE8E2')) for col,row in highlight]
    ]))
    _,h=t.wrap(516,700)
    if y-h-10<60:
        end()
        start('ASSESSMENT CONTINUED','Assessment continued','Additional assessment tables')
    t.drawOn(c,48,y-h)
    y-=h+10

def chart(profile):
    global y
    rows=[(d,s/FOOT,ray/FOOT,fresnel/FOOT) for d,s,ray,fresnel in profile['rows']]
    values=[v for row in rows for v in row[1:]]
    tick=max(20,20*math.ceil((max(values)-min(values))/80))
    lo,hi=math.floor(min(values)/tick)*tick,math.ceil(max(values)/tick)*tick
    text(48,y-9,profile['name'],11,teal,True)
    top,bottom,left,right=y-26,y-119,89,553
    dist=rows[-1][0]
    x=lambda d:left+(right-left)*d/dist
    z=lambda e:bottom+(top-bottom)*(e-lo)/(hi-lo)
    for v in range(lo,hi+1,tick):
        c.setStrokeColor(rule)
        c.setLineWidth(.45)
        c.line(left,z(v),right,z(v))
        text(50,z(v)-3,f'{v} ft',8,gray)
    for col,color,dash in [(1,gray,[]),(2,teal,[]),(3,orange,[4,3])]:
        path=c.beginPath()
        path.moveTo(x(rows[0][0]),z(rows[0][col]))
        for row in rows[1:]:
            path.lineTo(x(row[0]),z(row[col]))
        c.setStrokeColor(color)
        c.setLineWidth(1.15)
        c.setDash(dash)
        c.drawPath(path)
    c.setDash([])
    for frac in [0,.25,.5,.75,1]:
        d=dist*frac
        c.setFillColor(gray)
        c.setFont('Helvetica',8)
        c.drawCentredString(x(d),bottom-12,f'{d:.1f} mi')
    y-=145



from datetime import date
import os
import tempfile

def plot(samples,index,cx,cy,radius,limit,colors):
    c.setStrokeColor(rule)
    c.setLineWidth(.45)
    for frac in (.25,.5,.75,1):
        c.circle(cx,cy,radius*frac,stroke=1,fill=0)
    c.line(cx-radius,cy,cx+radius,cy)
    c.line(cx,cy-radius,cx,cy+radius)
    for miles,bearing,scores in samples:
        angle=math.radians(bearing)
        r=miles/limit*radius
        score=scores[index]
        c.setFillColor(colors[score] if score is not None else HexColor('#BFC4C8'))
        c.circle(cx+r*math.sin(angle),cy+r*math.cos(angle),1.05,stroke=0,fill=1)
    c.setFillColor(navy)
    c.circle(cx,cy,2.2,stroke=0,fill=1)
    text(cx-3,cy+radius+6,'N',8,gray,True)

def path_row(path,mode):
    values=path['ratios'] if mode=='ratio' else path['clearance']
    vals=[f'{v*100:.0f}%' if mode=='ratio' else f'{v/FOOT:.1f} ft' for v in values]
    return [path['name'],f"{path['miles']:.1f}",f"{path['rx']/FOOT:g}",*vals]

def link_margin(path_loss,budget,handheld):
    from planning import margins
    return margins(path_loss,budget,handheld)[2]


def build(filename,settings,result):
    # Publish only after the complete PDF has been written.
    fd,temporary=tempfile.mkstemp(suffix='.pdf',dir=Path(filename).parent)
    os.close(fd)
    try:
        write_report(temporary,settings,result)
        os.replace(temporary,filename)
    finally:
        Path(temporary).unlink(missing_ok=True)

def write_report(filename,s,r):
    global c,y,page
    c=canvas.Canvas(filename,pagesize=(612,792))
    c.setTitle(f"MeshCore coverage assessment | {s['site']}")
    c.setAuthor('Indiana Mesh Alliance (IMA)')
    c.setSubject('One Click Mesh | Site maps, terrain clearance and Longley-Rice propagation')
    page=0
    heights=s['heights']
    budget=s['budget']
    target_margin=budget['reserve']
    heights_label=' / '.join(f'{h/FOOT:g} ft' for h in heights)
    lat,lon=s['origin']
    freq,bw,sf,cr=s['radio']
    repeater=[p for p in r['paths'] if p['kind']!='Handheld']
    handheld=[p for p in r['paths'] if p['kind']=='Handheld']
    margins=[[link_margin(loss,budget,item['kind']=='Handheld') if loss is not None else None
              for loss,_ in item['losses']] for item in r['paths']]
    by_path=list(zip(r['paths'],margins))
    start('INDIANA MESH ALLIANCE (IMA)  /  501(c)(3) NONPROFIT','MeshCore Coverage Assessment','One Click Mesh  |  '+date.today().isoformat())
    p('<b>'+escape(s['site'])+'</b>')
    if s.get('prepared_for'):
        p('<b>Prepared for</b>  '+escape(s['prepared_for']))
    table(['Planning input','Value'],[
        ['Modeled location',f"{lat:.6f}, {lon:.6f} ({s['location_source']})"],
        *([['Street address',s['address']]] if s['address'] else []),
        ['Endpoint elevation',f"{r['start_z']/FOOT:.1f} ft ({r['base']})"],
        ['Station antenna heights',heights_label+' above ground'],
        ['Radio preset',f'{freq:g} MHz / {bw:g} kHz / SF{sf} / CR 4/{cr}'],
        ['Handheld plot',f"{s['handheld']/FOOT:g} ft AGL | LOS {LOS_RADIUS/MILE:.2f} mi | ITM {s['radius']:g} mi"],
        ['Public repeater lookup','Enabled' if s['discover'] else 'Disabled'],
    ],[165,351])
    candidates=[(item,values) for item,values in by_path if item['kind']!='Handheld'
                and (item['kind']!='Public repeater' or 'observ' not in item['name'].lower())]
    candidate=next(((i,item,values[i]) for i in range(len(heights)) for item,values in candidates
                    if item['ratios'][i]>=.6 and values[i] is not None and values[i]>=target_margin),None)
    if candidate:
        i,item,margin=candidate
        callout('First repeater path to test',f"At {heights[i]/FOOT:g} ft, {escape(item['name'])} ({item['miles']:.1f} mi) meets the 60% Fresnel target and has {margin:+.1f} dB estimated margin against a {target_margin:g} dB target.")
    elif repeater:
        callout('Repeater paths need field validation','None of the tested forwarding candidates meets both the 60% Fresnel target and the selected margin target. Confirm forwarding roles and endpoint mounts before choosing a site.')
    else:
        callout('Repeater paths','No repeater paths were modeled. The radial plots show local surface clearance. A known repeater can be entered as a test destination.')
    strongest=[(values[-1],item['name']) for item,values in candidates if values[-1] is not None]
    priority=[(values[-1],item['name']) for item,values in by_path
              if item['seen'] is None and values[-1] is not None]
    if strongest:
        value,name=max(strongest)
        p(f'<b>Strongest repeater at {heights[-1]/FOOT:g} ft</b>  {escape(name)} ({value:+.1f} dB).',small,4)
    if priority:
        value,name=min(priority)
        p(f'<b>Weakest entered destination at {heights[-1]/FOOT:g} ft</b>  {escape(name)} ({value:+.1f} dB).',small,4)
    if s['location_source']=='Census address estimate':
        p('The <link href="https://geocoding.geo.census.gov/geocoder/" color="#006C65">Census Geocoder</link> estimates the location along a street address range. Verify the plotted point and use the antenna mount GPS coordinates for a site-specific assessment.',small)
    p('The assessment estimates terrain clearance and median propagation loss. Packet delivery, measured signal strength and indoor service require field measurements.',small)
    end()

    import sys, report_maps
    report_maps.append(sys.modules[__name__],s,r)

    if r.get('context_maps'):
        aerial,topo,street=r['context_maps']
        start('SITE CONTEXT  /  01','Aerial site overview','Proposed antenna location and surrounding land cover')
        p(f"<b>{escape(s['site'])}</b>  |  {lat:.6f}, {lon:.6f}",small,4)
        basemap(aerial)
        p('The center marker identifies the modeled antenna location. Imagery can predate changes to buildings, vegetation or access roads.',small)
        link=escape(street_view(s['origin']))
        callout('Street-level imagery',
                f'<link href="{link}" color="#006C65"><b>Open nearby Google Street View</b></link><br/>Panorama availability varies by site. The browser link opens at the modeled coordinates.')
        end()

        start('SITE CONTEXT  /  02','Topography and streets','Regional terrain context and local road access')
        basemap(topo)
        basemap(street)
        end()

    start('01  /  USGS 3DEP','Local elevation map','Bare-earth elevation, centered on the modeled antenna site')
    image,low,high=r['terrain_image']
    p(f"Site elevation is <b>{r['start_z']/FOOT:.1f} ft</b>. USGS raster spacing near the site is approximately {r['spacing'][0]/FOOT:.0f} ft east-west and {r['spacing'][1]/FOOT:.0f} ft north-south.")
    cx,cy,half=306,361,163
    c.drawImage(ImageReader(image),cx-half,cy-half,2*half,2*half)
    c.setStrokeColor(white)
    c.setLineWidth(.9)
    c.circle(cx,cy,half,fill=0,stroke=1)
    c.line(cx-6,cy,cx+6,cy)
    c.line(cx,cy-6,cx,cy+6)
    text(cx-3,cy+half+6,'N',10,gray,True)
    y=175
    table(['Map symbol','Meaning'],[
        ['Light to dark',f'{low/FOOT:.0f} to {high/FOOT:.0f} ft elevation across the map'],
        ['White ring and cross',f'{LOS_RADIUS/MILE:.2f} mi radius and modeled antenna location'],
        ['Gray','USGS data unavailable'],
    ],[146,370])
    end()

    start(f'02  /  {LOS_RADIUS/MILE:.2f} MI TERRAIN LOS','Line-of-sight screening',f'Handheld paths sampled every {LOS_RADIUS/10/MILE:.2f} mi at 5-degree bearing intervals')
    p(f"Each dot is a direct path to a receiver at {s['handheld']/FOOT:g} ft above bare ground. North is up. The outer ring is {LOS_RADIUS/MILE:.2f} mi from the site.",small)
    los_colors=[HexColor('#A34F2B'),HexColor('#BC8A2E'),teal]
    for i,h in enumerate(heights):
        cx=306+(i-(len(heights)-1)/2)*170
        plot(r['los'],i,cx,465,68,LOS_RADIUS/MILE,los_colors)
        text(cx-16,380,f'{h/FOOT:g} ft',11,navy,True)
    y=355
    table(['Mark','Terrain classification'],[
        ['Green','Direct line of sight with at least 60% first Fresnel clearance.'],
        ['Gold','Direct line of sight with less than 60% first Fresnel clearance.'],
        ['Rust','Terrain blocks direct line of sight.'],
        ['Gray','Elevation data gap.'],
    ],[92,424])
    rows=[]
    for i,h in enumerate(heights):
        scores=[sample[i] for _,_,sample in r['los']]
        valid=[score for score in scores if score is not None]
        rows.append([f'{h/FOOT:g} ft',f'{sum(s>0 for s in valid)} / {len(valid)}',
                     f'{valid.count(2)} / {len(valid)}',scores.count(None)])
    table(['Station height','LOS clear','60% Fresnel clear','Data gaps'],rows,[115,135,150,116])
    p('Counts are for the sampled paths. They do not represent a percentage of the area.',small)
    end()

    start('03  /  LONGLEY-RICE ITM','Propagation loss','NTIA ITM v1.4 point-to-point modeling using USGS terrain profiles')
    p(f"The outer ring is {s['radius']:g} mi from the site. Each dot shows predicted median basic transmission loss to an outdoor antenna at {s['handheld']/FOOT:g} ft above ground. Lower dB means less loss.",small)
    cuts=(105,120,135,150)
    itm_colors=list(map(HexColor,['#006B64','#42908C','#B39937','#BA6F37','#A44934']))
    def loss_bin(loss):
        return sum(loss>=cut for cut in cuts) if loss is not None else None
    samples=[(d,b,[loss_bin(loss) for loss,_ in row]) for d,b,row in r['itm']]
    for i,h in enumerate(heights):
        cx=306+(i-(len(heights)-1)/2)*170
        plot(samples,i,cx,465,68,s['radius'],itm_colors)
        text(cx-16,380,f'{h/FOOT:g} ft',11,navy,True)
    y=355
    for i,label in enumerate(['<105','105-119','120-134','135-149','150+','Unavailable']):
        x=48+i*84
        c.setFillColor((itm_colors+[HexColor('#BFC4C8')])[i])
        c.circle(x+5,y-7,3,fill=1,stroke=0)
        text(x+12,y-10,label,8,gray)
    y-=24
    rows=[]
    for i,h in enumerate(heights):
        readings=[sample[i] for _,_,sample in r['itm']]
        valid=[loss for loss,_ in readings if loss is not None]
        warned=sum(loss is not None and bool(flag) for loss,flag in readings)
        rows.append([f'{h/FOOT:g} ft',len(valid),warned,len(readings)-len(valid)])
    table(['Station height','Predictions','ITM warnings','Unavailable'],rows,[115,135,150,116])
    p('Legend values are dB. Warnings indicate that some model assumptions are near or outside preferred limits, including short paths. Predictions exclude antenna gains, feedline losses, vegetation, buildings and interference.',small)
    end()

    start('LINK BUDGET','Estimated handheld coverage','Weaker direction margin at sampled locations')
    p(f'Each dot compares estimated received power with the selected receiver sensitivity. Green reaches the {target_margin:g} dB planning target. The outer ring is {s["radius"]:g} mi from the site.',small)
    samples=[]
    for dist,bearing,row in r['itm']:
        scores=[]
        for loss,_ in row:
            margin=link_margin(loss,budget,True) if loss is not None else None
            scores.append(None if margin is None else 2 if margin>=target_margin else 1 if margin>=0 else 0)
        samples.append((dist,bearing,scores))
    for i,h in enumerate(heights):
        cx=306+(i-(len(heights)-1)/2)*170
        plot(samples,i,cx,465,68,s['radius'],los_colors)
        text(cx-16,380,f'{h/FOOT:g} ft',11,navy,True)
    y=355
    p('Green: target met. Gold: sensitivity met, target missed. Rust: below sensitivity. Gray: unavailable.',small,7)
    coverage_rows=[]
    for i,h in enumerate(heights):
        counts=[row[i] for _,_,row in samples]
        coverage_rows.append([f'{h/FOOT:g} ft',counts.count(2),counts.count(1),counts.count(0),counts.count(None)])
    table(['Station height','Meets margin target','Sensitivity met only','Below sensitivity','Unavailable'],
          coverage_rows,[91,112,125,105,83])
    table(['Radio assumptions','Settings used for this assessment'],[
        ['Station transmit',f"{budget['power']:g} dBm power | {budget['tx_gain']:g} dBi antenna gain"],
        ['Receiver',f"{budget['handheld_gain']:g} dBi handheld gain | {budget['repeater_gain']:g} dBi repeater gain"],
        ['Loss and thresholds',f"{budget['loss']:g} dB station cable loss | {target_margin:g} dB target margin; see endpoint assumptions for both radios"],
    ],[148,368])
    p('The smaller direction margin is shown. See Endpoint assumptions for separate radio inputs and the two-way formula.',small)
    end()

    if r['paths']:
        start('04  /  NAMED PROPAGATION PATHS','ITM path loss by destination','Median basic transmission loss in dB at each station antenna height')
        rows=[]
        for item in r['paths']:
            values=[f'{loss:.1f}'+('*' if flag else '') if loss is not None else 'Unavailable'
                    for loss,flag in item['losses']]
            rows.append([item['name'],f"{item['miles']:.1f}",*values])
        table(['Destination','Miles',*[f'{h/FOOT:g} ft' for h in heights]],rows,
              [516-48-72*len(heights),48,*([72]*len(heights))])
        p('An asterisk marks an ITM warning. Unavailable indicates a model error or missing result for that path and height.',small)
        for item in r['paths']:
            flags=[flag for _,flag in item['losses'] if flag]
            if flags:
                p(f"{escape(item['name'])}  |  {escape(', '.join(dict.fromkeys(flags)))}",small,2)
        end()
        start('LINK BUDGET  /  NAMED DESTINATIONS','Link margin by destination','Weaker direction dB above sensitivity at each station antenna height')
        table(['Destination','Miles',*[f'{h/FOOT:g} ft' for h in heights]],
              [[item['name'],f"{item['miles']:.1f}",
                *[f'{margin:+.1f}' if margin is not None else 'Unavailable' for margin in values]]
               for item,values in by_path],
              [516-48-72*len(heights),48,*([72]*len(heights))])
        p(f'Target margin is {target_margin:g} dB. Negative values fall below the entered receiver sensitivity. See the ITM path-loss table for individual model warnings.',small)
        end()
    for entries,mode,label in [(repeater,'ratio','Repeater paths'),(handheld,'clearance','Handheld paths')]:
        if not entries:
            continue
        start('05  /  NAMED DESTINATIONS',label,'Straight-line paths at the selected station antenna heights')
        table(['Destination','Miles','RX ft',*[f'{h/FOOT:g} ft' for h in heights]],
              [path_row(item,mode) for item in entries],
              [516-46-46-60*len(heights),46,46,*([60]*len(heights))])
        p('Negative values indicate direct path obstruction. Repeater values show minimum clearance as a percentage of the local first Fresnel radius. Handheld values show minimum vertical clearance in feet.',small)
        sub('Endpoint data')
        for item in entries:
            plat,plon=item['point']
            seen=f" | map advert {item['seen']}" if item['seen'] else ''
            p(f"{escape(item['name'])} | {plat:.5f}, {plon:.5f} | {escape(item['source'])}{seen}",small,3)
        end()

    profiles=r['paths']
    for offset in range(0,len(profiles),3):
        start('06  /  TERRAIN PROFILES','Terrain along the path',f'Station antenna at {heights[len(heights)//2]/FOOT:g} ft above ground')
        p('Gray shows the modeled surface. Teal shows the direct antenna path. The dashed line marks the lower edge of the 60% Fresnel clearance target. Vertical scales vary by path.',small)
        for path_index,item in enumerate(profiles[offset:offset+3],offset):
            c.bookmarkHorizontalAbsolute('terrain-profile-'+str(path_index),y)
            chart({'name':item['name'],'rows':item['profile']})
        end()

    if r.get('scenarios'):
        import sys, report_deployment
        report_deployment.append(sys.modules[__name__],s,r)

    start('DATA PROVENANCE','Data and model record','Sources, download history and cache status for this assessment')
    records=[[name,status,when] for name,(status,when) in r['provenance'].items()]
    records.extend([item['title'],'Downloaded' if item['image'] is not None else 'Unavailable',item['fetched']]
                   for item in r.get('context_maps',[]))
    records.append(['Propagation engine','Bundled NTIA ITM v1.4','Local calculation'])
    table(['Input','Run status','Downloaded / cached at'],records,[180,165,171])
    p(f"USGS 3DEP raster spacing near the site is approximately {r['spacing'][0]/FOOT:.0f} ft east-west and {r['spacing'][1]/FOOT:.0f} ft north-south. Cache timestamps describe the local file and do not indicate the provider's survey or publication date.",small)
    if r['warnings']:
        sub('Data availability notes')
        for warning in r['warnings']:
            p(escape(warning),small,4)
    end()

    start('07  /  METHODS AND VALIDATION','From model to field test','Inputs, interpretation and what to measure on site')
    sub('Terrain and public node data')
    p('The app extracts USGS 3DEP bare-earth elevations as a georeferenced raster and samples profiles at intervals no greater than about 82 ft. The separate LOS calculation uses a 4/3 effective Earth radius. ITM receives unadjusted terrain elevations and applies its own refraction model.')
    p('Public discovery takes the five nearest repeater listings with an exact match to all four radio settings, within the chosen radius. Advertised positions can be approximate. Entries without matching settings are omitted. The public feed cache refreshes after six hours.')
    sub('Field validation')
    p('Mount a temporary antenna at the proposed coordinates and height. Send numbered packets at a controlled cadence in both directions to each priority repeater. Record delivery rate, RSSI, SNR, and hop path where available. Repeat from the priority handheld locations, indoors and outdoors separately.')
    p('Use the lowest tested mounting height that meets the site delivery requirement. If a target remains obstructed or unreliable, model a relay from a second site that can reach both ends.')
    sub('Source register')
    links=[
        ('USGS 3DEP ImageServer','https://elevation.nationalmap.gov/arcgis/rest/services/3DEPElevation/ImageServer'),
        ('NTIA ITM v1.4','https://github.com/NTIA/itm/releases/tag/v1.4'),
        ('Public MeshCore map','https://map.meshcore.io/'),
        ('ITU-R P.526','https://www.itu.int/rec/R-REC-P.526/en')
    ]
    p(' &nbsp; | &nbsp; '.join(f'<link href="{url}" color="#006C65">{label}</link>' for label,url in links),small)
    p('Propagation uses the unmodified NTIA Irregular Terrain Model v1.4. Defaults are continental temperate climate, vertical polarization, refractivity 301 N-units, relative permittivity 15, conductivity 0.001524 S/ft, single-message variability, and 50% time, location and situation.',small)
    end()
    c.save()


