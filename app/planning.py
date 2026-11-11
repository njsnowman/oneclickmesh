"""Planning comparisons, radio budgets, projects and measured data."""
import csv
import json
import math
import os
import tempfile
from pathlib import Path

def margins(loss,budget,handheld):
    kind='handheld' if handheld else 'repeater'
    gain=budget[kind+'_gain']
    cable=budget['loss']+budget[kind+'_loss']
    common=budget['tx_gain']+gain-cable-loss
    down=budget['power']+common-budget[kind+'_sensitivity']
    up=budget[kind+'_power']+common-budget['station_sensitivity']
    return down,up,min(down,up)

def number(value,minimum,maximum,label):
    try:
        result=float(value)
    except (ValueError,TypeError):
        raise ValueError(f'{label} must be a number.')
    if not math.isfinite(result) or not minimum<=result<=maximum:
        raise ValueError(f'{label} must be between {minimum:g} and {maximum:g}.')
    return result

def alternatives(text):
    rows=[]
    for i,line in enumerate(text.splitlines(),1):
        if not line.strip():
            continue
        parts=next(csv.reader([line]))
        if len(parts)!=3 or not parts[0].strip():
            raise ValueError(f'Candidate site line {i} needs name, latitude, longitude.')
        name,lat,lon=parts
        if len(name)>60:
            raise ValueError('Candidate site names must be 60 characters or fewer.')
        rows.append((name.strip(),(number(lat,24,50,'Latitude'),number(lon,-125,-66,'Longitude'))))
    if len(rows)>2:
        raise ValueError('Enter at most two additional candidate sites.')
    return rows

def measurements(path):
    rows=[]
    with open(path,encoding='utf-8-sig',newline='') as source:
        reader=csv.DictReader(source)
        required={'latitude','longitude','sent','received'}
        if not required.issubset(reader.fieldnames or []):
            raise ValueError('CSV needs latitude, longitude, sent and received columns.')
        for i,row in enumerate(reader,2):
            if len(rows)>=2000:
                raise ValueError('Import up to 2,000 field-test points per project.')
            lat=number(row['latitude'],24,50,f'Line {i} latitude')
            lon=number(row['longitude'],-125,-66,f'Line {i} longitude')
            sent=number(row['sent'],1,1e8,f'Line {i} packets sent')
            received=number(row['received'],0,sent,f'Line {i} packets received')
            if sent!=int(sent) or received!=int(received):
                raise ValueError(f'Line {i} packet counts must be whole numbers.')
            item=dict(latitude=lat,longitude=lon,sent=int(sent),received=int(received))
            for key,lo,hi in [('rssi',-200,0),('snr',-60,60)]:
                item[key]=number(row[key],lo,hi,f'Line {i} {key}') if row.get(key,'').strip() else None
            item['repeater']=row.get('repeater','').strip()[:100]
            item['timestamp']=row.get('timestamp','').strip()[:60]
            rows.append(item)
    if not rows:
        raise ValueError('The field-test CSV has no measurements.')
    return rows

def write_project(path,payload):
    parent=Path(path).parent
    fd,tmp=tempfile.mkstemp(dir=parent,suffix='.tmp')
    try:
        with os.fdopen(fd,'w',encoding='utf-8') as out:
            json.dump(dict(format='one-click-mesh',version=1,**payload),out,indent=2,allow_nan=False)
        os.replace(tmp,path)
    finally:
        Path(tmp).unlink(missing_ok=True)

def read_project(path):
    if Path(path).stat().st_size>4_000_000:
        raise ValueError('Project file exceeds 4 MB.')
    data=json.loads(Path(path).read_text(encoding='utf-8'))
    if data.get('format')!='one-click-mesh' or data.get('version')!=1:
        raise ValueError('Unsupported One Click Mesh project format.')
    if not isinstance(data.get('fields'),dict) or not all(isinstance(v,str) for v in data['fields'].values()):
        raise ValueError('Project fields must contain text.')
    if any(not isinstance(data.get(key,''),str) for key in ('targets','alternatives','folder','quality')):
        raise ValueError('Invalid project options.')
    if not isinstance(data.get('discover'),bool):
        raise ValueError('Invalid discovery setting.')
    if not isinstance(data.get('extended_radius',False),bool):
        raise ValueError('Invalid extended radius setting.')
    # Use the same CSV validation for embedded measurements.
    rows=data.get('measurements',[])
    if not isinstance(rows,list) or len(rows)>2000:
        raise ValueError('Invalid field measurements.')
    for row in rows:
        if not isinstance(row,dict):
            raise ValueError('Invalid field measurement.')
        for key,lo,hi in [('latitude',24,50),('longitude',-125,-66),('sent',1,1e8)]:
            row[key]=number(row.get(key),lo,hi,key)
        row['received']=number(row.get('received'),0,float(row['sent']),'received')
        if any(float(row[k])!=int(float(row[k])) for k in ('sent','received')):
            raise ValueError('Packet counts must be integers.')
        for key,lo,hi in [('rssi',-200,0),('snr',-60,60)]:
            if row.get(key) is not None:
                row[key]=number(row[key],lo,hi,key)
        for key in ('repeater','timestamp'):
            if not isinstance(row.get(key,''),str):
                raise ValueError('Invalid measurement text.')
    return data
