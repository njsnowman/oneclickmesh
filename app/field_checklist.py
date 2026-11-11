"""Compact, printable checklist; one page for the supported ten destinations."""
from xml.sax.saxutils import escape
from reportlab.platypus import Paragraph,Table,TableStyle
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.colors import white
from terrain import FOOT

def append(pdf,s,r):
    pdf.start('PRINT & TAKE TO SITE','Field test checklist','Repeat this sheet for each station height and candidate site tested')
    style=ParagraphStyle('field',fontSize=8,leading=10,textColor=pdf.navy)
    pdf.p('<b>Site:</b> '+escape(s['site']),pdf.small,3)
    lat,lon=s['origin']
    heights=' / '.join(f'{h/FOOT:g} ft' for h in s['heights'])
    pdf.p(f'<b>GPS:</b> {lat:.6f}, {lon:.6f} &nbsp; <b>Planned station heights:</b> {heights} AGL',pdf.small,3)
    f,bw,sf,cr=s['radio']
    pdf.p(f'<b>Radio:</b> {f:g} MHz / {bw:g} kHz / SF{sf} / CR 4/{cr} &nbsp; <b>Margin target:</b> {s["budget"]["reserve"]:g} dB',pdf.small,3)
    pdf.p('Date/time: __________________  Operator: __________________  Actual mount: ______ ft',pdf.small,5)
    targets=r.get('_targets',s['targets'])
    headers=['Destination / GPS / endpoint height','Down: sent / received','Up: sent / received','RSSI dBm D / U','SNR dB D / U']
    rows=[[Paragraph(escape(h),ParagraphStyle('fh',parent=style,textColor=white)) for h in headers]]
    for name,point,rx,kind,seen in targets:
        label=f'<b>{escape(name)}</b><br/>{point[0]:.5f}, {point[1]:.5f} | {rx/FOOT:g} ft | {escape(kind)}'
        label_box=Paragraph(label,style)
        if label_box.wrap(210,100)[1]>29:
            label_box=Paragraph(label,ParagraphStyle('compact',parent=style,fontSize=7,leading=9))
        rows.append([label_box,'____ / ____','____ / ____','____ / ____','____ / ____'])
    if not targets:
        for _ in range(3):rows.append([Paragraph('Destination: ______________________<br/>GPS: __________________ RX: _____ ft',style),'____ / ____','____ / ____','____ / ____','____ / ____'])
    table=Table(rows,colWidths=[220,78,78,70,70],rowHeights=[28]+[35]*(len(rows)-1))
    table.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),pdf.navy),('ROWBACKGROUNDS',(0,1),(-1,-1),[white,pdf.light]),('VALIGN',(0,0),(-1,-1),'MIDDLE'),('FONTSIZE',(0,1),(-1,-1),8),('TEXTCOLOR',(0,1),(-1,-1),pdf.navy),('LINEBELOW',(0,1),(-1,-1),.4,pdf.rule),('LEFTPADDING',(0,0),(-1,-1),5),('RIGHTPADDING',(0,0),(-1,-1),5)]))
    _,height=table.wrap(516,700)
    table.drawOn(pdf.c,48,pdf.y-height);pdf.y-=height+7
    pdf.p('D = station to endpoint; U = endpoint to station. Record RSSI/SNR at the receiving end. Delivery = received / sent. Repeat for every planned height; use blank rows if discovery found no destinations.',style,4)
    pdf.p('[ ] Confirm antenna GPS, actual heights, hardware and matching radio settings.<br/>[ ] Send numbered packets both ways at a fixed cadence; record counts, RSSI and SNR.<br/>[ ] Record repeater heard / hop route, indoor or outdoor location, and obstructions.<br/>[ ] Retest weak paths; record changes to height, antenna, power or location.',style,4)
    pdf.p('Route / repeater heard / conditions: __________________________________________________<br/>_____________________________________________________________________________',style,2)
    pdf.end()
