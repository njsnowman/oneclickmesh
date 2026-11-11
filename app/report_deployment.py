"""Deployment decision pages, georeferenced predictions and measured overlays."""
from xml.sax.saxutils import escape
from reportlab.lib.utils import ImageReader
from PIL import ImageDraw
from planning import margins
from deployment import scenario_rows
from terrain import FOOT
from context_maps import point_on_map

def append_planning(pdf,s,r):
    pdf.start('DEPLOYMENT PLANNING','Site and height comparison','Same destinations, radio assumptions and two-way margin target')
    rows=scenario_rows(s,r)
    for offset in range(0,len(rows),6):
        if offset:
            pdf.end()
            pdf.start('DEPLOYMENT PLANNING','Site comparison continued','Same destinations and radio assumptions')
        pdf.table(['Candidate site','Height','Target met','Data status'],rows[offset:offset+6],[235,70,100,111])
    pdf.p(f"Each score counts destinations where BOTH directions meet the {s['budget']['reserve']:g} dB reserve. The comparison uses {r['common_count']} common destinations; missing results do not count as passing.",pdf.small)
    if r['common_count']:
        complete=[row for row in rows if row[3]=='Complete']
        if complete:
            best=max(int(row[2].split('/')[0]) for row in complete)
            winners=[row for row in complete if int(row[2].split('/')[0])==best]
            winner=min(winners,key=lambda row:float(row[1].split()[0]))
            pdf.callout('First configuration to field-test',f'{escape(winner[0])} at {winner[1]} reaches {winner[2]} common destinations. This is the lowest tested height among equally scoring complete scenarios. It is not a guarantee of service or a construction recommendation.')
    else:
        pdf.p('Add common test destinations to rank sites. No site ranking is possible without destinations.',pdf.small)
    for scenario in r['scenarios']:
        if scenario['error']:
            pdf.p(f"{escape(scenario['name'])}: {escape(scenario['error'][:240])}",pdf.small,4)
    for scenario in r['scenarios'][1:]:
        if scenario.get('spacing'):
            x,y=scenario['spacing']
            pdf.p(f'Terrain spacing at {escape(scenario["name"])}: approximately {x/FOOT:.0f} ft east-west / {y/FOOT:.0f} ft north-south. Grid extent and resampling can affect comparisons.',pdf.small,4)
    pdf.end()

def append(pdf,s,r):
    for i,h in enumerate(s['heights']):
        pdf.start('GEOGRAPHIC COVERAGE',f'Two-way coverage | {h/FOOT:g} ft',f"{s['quality']} sampling | {s['radius']:g} mi radius | north up")
        pdf.c.drawImage(ImageReader(r['overlays'][i]),96,180,420,420)
        pdf.y=169
        pdf.p(f"Green: both margins meet {s['budget']['reserve']:g} dB. Gold: both meet sensitivity only. Rust: at least one direction falls below sensitivity. Gray: unavailable. White center: station.",pdf.small,5)
        pdf.p(f"{len(r['grid'])} discrete path samples; nominal spacing {r['grid_spacing']:.2f} mi. Colored squares mark sampled points, not validated service areas. The map spans {2*s['radius']:g} mi east-west at the center.",pdf.small,5)
        flagged=sum(bool(cell['losses'][i][1]) for cell in r['grid'])
        pdf.p(f'{flagged} samples have ITM or terrain flags. Predictions near model limits require extra field checks.',pdf.small,3)
        pdf.p('Basemap: '+escape(r['overlay_base']['credit'])+'. Retrieved '+r['overlay_base']['fetched']+'.',pdf.small,3)
        pdf.end()
    pdf.start('TWO-WAY RADIO SETTINGS','Endpoint assumptions','Independent transmit power, sensitivity, gain and cable loss')
    b=s['budget']
    pdf.table(['Endpoint','TX dBm','RX dBm','Gain dBi','Loss dB'],[
        ['Station',b['power'],b['station_sensitivity'],b['tx_gain'],b['loss']],
        ['Handheld',b['handheld_power'],b['handheld_sensitivity'],b['handheld_gain'],b['handheld_loss']],
        ['Repeater',b['repeater_power'],b['repeater_sensitivity'],b['repeater_gain'],b['repeater_loss']],
    ],[156,90,90,90,90])
    pdf.p('For each direction, margin = transmit power + both antenna gains - both cable losses - ITM path loss - the receiving endpoint sensitivity. Two-way margin is the smaller direction margin.')
    pdf.p('The same terrain path loss is used in both directions under reciprocal propagation at the same frequency. Sensitivity must match the actual radio and modem preset. Building penetration, foliage, interference, antenna patterns and protocol behavior are not represented.')
    pdf.p('Quick and Detailed change geographic sampling density, not terrain resolution or the propagation model. USGS terrain can be cached; rapid completion is not evidence of fabricated data. Consult the data record for cache status.')
    pdf.end()
    if r['field']:
        image=r['overlay_base']['image'].copy()
        draw=ImageDraw.Draw(image)
        plotted=0
        for item in r['field']:
            x,y=point_on_map(r['overlay_base']['bounds'],(item['latitude'],item['longitude']))
            if 0<=x<=1 and 0<=y<=1:
                plotted+=1
                rate=item['received']/item['sent']
                color='#007A60' if rate>=.9 else '#BF9526' if rate>=.5 else '#B33F28'
                draw.ellipse((x*800-5,y*800-5,x*800+5,y*800+5),fill=color,outline='white',width=1)
        pdf.start('FIELD MEASUREMENTS','Measured packet delivery','Imported observations, separate from propagation predictions')
        pdf.c.drawImage(ImageReader(image),96,180,420,420)
        pdf.y=169
        sent=sum(row['sent'] for row in r['field']);received=sum(row['received'] for row in r['field'])
        pdf.p(f'{len(r["field"])} records; {plotted} inside map extent. Aggregate delivery: {received/sent:.1%} ({received:g} / {sent:g} packets). Green: 90% or higher; gold: 50-89%; rust: below 50%. These are display bands, not acceptance criteria.',pdf.small,5)
        pdf.p('Logs may describe multi-hop traffic or different equipment. These observations do not automatically calibrate or validate direct-path ITM predictions. Basemap: '+escape(r['overlay_base']['credit']),pdf.small,3)
        pdf.end()
        for offset in range(0,len(r['field']),12):
            pdf.start('FIELD LOG',f'Measurements {offset+1}-{min(offset+12,len(r["field"]))}','Direct modeled margin uses the highest tested station height')
            rows=[]
            for item in r['field'][offset:offset+12]:
                loss=item['prediction'][-1][0] if item['prediction'] else None
                value=f'{margins(loss,b,True)[2]:+.1f}' if loss is not None else 'N/A'
                rows.append([f'{item["latitude"]:.5f}\r\n{item["longitude"]:.5f}',f'{item["received"]/item["sent"]:.0%}',
                             '-' if item.get('rssi') is None else f'{item["rssi"]:g}',
                             '-' if item.get('snr') is None else f'{item["snr"]:g}',value,item.get('repeater','')[:35]])
            pdf.table(['GPS','Delivery','RSSI dBm','SNR dB','Model dB','Repeater heard'],rows,[110,65,70,65,70,136])
            pdf.p('N/A: outside modeled radius, within 345 ft of the station, or elevation / ITM unavailable. Modeled margin is relative to sensitivity; RSSI is received power. They are different quantities.',pdf.small)
            pdf.end()
