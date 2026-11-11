"""Single-screen Windows interface for the MeshCore coverage plotter."""
import math
import time
import os
import queue
import re
import sys
import threading
import traceback
from datetime import datetime
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, ttk

import report
import terrain
import context_maps
import planning
import deployment
import map_picker
from project_ui import Tools

def number(value, minimum, maximum, label):
    try:
        x=float(value)
    except ValueError:
        x=math.nan
    if not minimum<=x<=maximum:
        raise ValueError(f'{label} must be between {minimum:g} and {maximum:g}.')
    return x

def point(lat,lon):
    return (number(lat,24,50,'Latitude'),number(lon,-125,-66,'Longitude'))

class App(Tools):
    def __init__(self,root):
        self.root=root
        root.title('One Click Mesh | Indiana Mesh Alliance')
        root.minsize(760,690)
        root.columnconfigure(0,weight=1)
        root.configure(background='#F2F6F8')
        self.fields={}
        self.alternatives_text=tk.StringVar()
        self.quality=tk.StringVar(value="Quick")
        self.extended_radius=tk.BooleanVar(value=False)
        self.measurements=[]
        self.last_result=None
        self.output=None
        self.running=False
        self.events=queue.Queue()
        style=ttk.Style(root)
        style.theme_use('clam')
        style.configure('.',font=('Segoe UI',10),background='#F2F6F8',foreground='#172D3E')
        style.configure('TEntry',fieldbackground='white',bordercolor='#C4D4DC',
                        lightcolor='white',darkcolor='white',padding=(7,3))
        style.configure('TLabelframe',bordercolor='#C4D4DC',relief='solid')
        style.configure('TLabelframe.Label',font=('Segoe UI',10,'bold'),foreground='#006B64')
        style.configure('TButton',padding=(12,6),background='#E3EBEF',bordercolor='#C4D4DC',
                        lightcolor='#E3EBEF',darkcolor='#E3EBEF')
        style.configure('Primary.TButton',background='#006B64',foreground='white',
                        bordercolor='#006B64',lightcolor='#006B64',darkcolor='#006B64')
        style.map('Primary.TButton',background=[('disabled','#788F98'),('active','#00544F')],
                  foreground=[('disabled','white'),('active','white')])
        style.configure('Brand.TFrame',background='#132C3D')
        style.configure('Brand.TLabel',background='#132C3D',foreground='#A9E1D6',
                        font=('Segoe UI',9,'bold'))
        style.configure('Title.TLabel',background='#132C3D',foreground='white',
                        font=('Segoe UI',23,'bold'))
        style.configure('Subtitle.TLabel',background='#132C3D',foreground='#DCE9EE')
        style.configure('Status.TLabel',foreground='#315366')
        header=ttk.Frame(root,padding=(25,11),style='Brand.TFrame')
        header.grid(row=0,column=0,sticky='ew')
        ttk.Label(header,text='INDIANA MESH ALLIANCE (IMA)  /  501(c)(3) NONPROFIT',
                  style='Brand.TLabel').grid(sticky='w')
        ttk.Label(header,text='One Click Mesh',style='Title.TLabel').grid(sticky='w',pady=(3,2))
        ttk.Label(header,text='Site maps, USGS terrain, line of sight and Longley-Rice propagation',
                  style='Subtitle.TLabel').grid(sticky='w')
        root.rowconfigure(1,weight=1)
        viewport=ttk.Frame(root)
        viewport.grid(row=1,column=0,sticky='nsew')
        viewport.columnconfigure(0,weight=1)
        viewport.rowconfigure(0,weight=1)
        canvas=tk.Canvas(viewport,highlightthickness=0,background='#F2F6F8')
        canvas.grid(row=0,column=0,sticky='nsew')
        vertical=ttk.Scrollbar(viewport,orient='vertical',command=canvas.yview)
        vertical.grid(row=0,column=1,sticky='ns')
        horizontal=ttk.Scrollbar(viewport,orient='horizontal',command=canvas.xview)
        horizontal.grid(row=1,column=0,sticky='ew')
        canvas.configure(yscrollcommand=vertical.set,xscrollcommand=horizontal.set)
        frame=ttk.Frame(canvas,padding=(24,12))
        content=canvas.create_window(0,0,window=frame,anchor='nw')
        frame.bind('<Configure>',lambda e:canvas.configure(scrollregion=canvas.bbox('all')))
        canvas.bind('<Configure>',lambda e:canvas.itemconfigure(content,width=max(e.width,frame.winfo_reqwidth())))
        def wheel(event):
            if event.widget.winfo_toplevel()==root and not isinstance(event.widget,tk.Text):
                canvas.yview_scroll(-int(event.delta/120),'units')
        root.bind_all('<MouseWheel>',wheel,add='+')
        root.geometry('1040x850')
        frame.columnconfigure(0,weight=1)
        site=ttk.LabelFrame(frame,text='Deployment site',padding=8)
        site.grid(row=0,column=0,sticky='ew')
        self.entry(site,'site','Site name','',0,0,28)
        self.entry(site,'lat','Latitude','',0,1,22)
        self.entry(site,'lon','Longitude','',0,2,22)
        self.entry(site,'heights','Station heights (ft)','20, 40, 65',1,0,18)
        self.entry(site,'radius','ITM radius (mi)','8',1,1,13)
        self.entry(site,'handheld','Handheld height (ft)','5',1,2,13)
        self.fields['address']=tk.StringVar()
        ttk.Label(site,text='Street address, city, state and ZIP (GPS takes precedence)').grid(
            row=4,column=0,columnspan=2,sticky='w',padx=5)
        ttk.Entry(site,textvariable=self.fields['address']).grid(
            row=5,column=0,columnspan=2,sticky='ew',padx=5,pady=(2,5))
        self.entry(site,'prepared_for','Prepared for (optional)','',2,2,22)

        radio=ttk.LabelFrame(frame,text='Radio and public repeaters',padding=8)
        radio.grid(row=1,column=0,sticky='ew',pady=7)
        for i,(key,label,value) in enumerate([
            ('freq','Frequency (MHz)','910.525'),('bw','Bandwidth (kHz)','62.5'),
            ('sf','Spreading factor','7'),('cr','CR denominator','5'),
            ('repeater','Repeater RX height (ft)','33'),
        ]):
            self.entry(radio,key,label,value,0,i,15)
        self.discover=tk.BooleanVar(value=True)
        ttk.Checkbutton(radio,text='Look up nearby public repeaters with matching radio settings',
                        variable=self.discover).grid(row=2,columnspan=5,sticky='w',padx=5,pady=(4,0))

        target=ttk.LabelFrame(frame,text='Optional test destinations',padding=8)
        self.destination_panel=target
        target.grid(row=2,column=0,sticky='ew')
        ttk.Label(target,text='One per line: Name, latitude, longitude, RX height in feet, handheld or repeater').grid(sticky='w',pady=(0,4))
        self.targets=tk.Text(target,height=3,font=('Consolas',10),wrap='none',undo=True,
                             bg='white',fg='#172D3E',padx=8,pady=5,relief='flat',
                             highlightthickness=1,highlightbackground='#C4D4DC',highlightcolor='#006B64')
        self.targets.grid(row=1,column=0,sticky='ew')
        target_scroll=ttk.Scrollbar(target,orient='vertical',command=self.targets.yview)
        target_scroll.grid(row=1,column=1,sticky='ns',padx=(4,0))
        self.targets.configure(yscrollcommand=target_scroll.set)
        target.columnconfigure(0,weight=1)

        folder=ttk.Frame(frame)
        folder.grid(row=3,column=0,sticky='ew',pady=(9,5))
        folder.columnconfigure(1,weight=1)
        launch_path=sys.executable if getattr(sys,'frozen',False) else __file__
        self.folder=tk.StringVar(value=str(Path(launch_path).resolve().parent/'Reports'))
        ttk.Label(folder,text='Save reports to').grid(row=0,column=0,padx=(0,8))
        ttk.Entry(folder,textvariable=self.folder).grid(row=0,column=1,sticky='ew')
        ttk.Button(folder,text='Browse',command=self.browse).grid(row=0,column=2,padx=(6,0))

        actions=ttk.Frame(frame)
        actions.grid(row=4,column=0,sticky='ew',pady=(4,5))
        self.generate=ttk.Button(actions,text='Generate assessment',command=self.submit,
                                 style='Primary.TButton')
        self.generate.pack(side='left')
        self.open_report=ttk.Button(actions,text='Open PDF',command=self.open,state='disabled')
        self.open_report.pack(side='left',padx=(8,0))
        self.advanced=ttk.LabelFrame(frame,text='Link budget and coverage options',padding=8)
        self.budget_fields=(
            ('power','TX power (dBm)','20',-20,40),
            ('tx_gain','Station gain (dBi)','2',-15,35),
            ('handheld_gain','Handheld gain (dBi)','0',-15,35),
            ('repeater_gain','Repeater gain (dBi)','2',-15,35),
            ('loss','Station cable loss (dB)','1',0,40),
            ('station_sensitivity','Station RX (dBm)','-120',-150,-70),
            ('handheld_power','Handheld TX (dBm)','20',-20,40),
            ('handheld_sensitivity','Handheld RX (dBm)','-120',-150,-70),
            ('handheld_loss','Handheld loss (dB)','0',0,40),
            ('repeater_power','Repeater TX (dBm)','20',-20,40),
            ('repeater_sensitivity','Repeater RX (dBm)','-120',-150,-70),
            ('repeater_loss','Repeater loss (dB)','0',0,40),
            ('reserve','Target margin (dB)','10',0,50),
        )
        for i,(key,label,default,_,_) in enumerate(self.budget_fields):
            self.entry(self.advanced,key,label,default,i//4,i%4,15)
        ttk.Checkbutton(self.advanced,text='Allow extended coverage radius (up to 40 mi)',
                        variable=self.extended_radius).grid(row=8,column=0,columnspan=4,sticky='w',padx=5,pady=6)
        self.advanced_open=tk.BooleanVar(value=False)
        ttk.Checkbutton(actions,text='Advanced settings',variable=self.advanced_open,
                        command=self.toggle_advanced).pack(side='right')
        self.status=tk.StringVar(value='Step 1: Enter your deployment site and radio preset, then generate the assessment.')
        self.status_label=ttk.Label(frame,textvariable=self.status,style='Status.TLabel',wraplength=710)
        self.status_label.grid(row=5,column=0,sticky='w')
        tools=ttk.Frame(frame)
        tools.grid(row=6,column=0,sticky='ew',pady=8)
        for label,command in [('Save project',self.save_project),('Open project',self.load_project),
                              ('Place on map',lambda:map_picker.open_picker(self)),
                              ('Planning tools',self.planning_tools),('Inspect paths',self.inspect_results)]:
            ttk.Button(tools,text=label,command=command).pack(side='left',padx=(0,5))
        quality=ttk.Frame(frame);quality.grid(row=7,column=0,sticky='ew')
        ttk.Label(quality,text='Geographic sampling').pack(side='left',padx=(0,8))
        ttk.Combobox(quality,textvariable=self.quality,values=('Quick','Detailed'),state='readonly',width=12).pack(side='left')
        ttk.Label(quality,text='Detailed uses a denser grid; terrain remains USGS resolution.').pack(side='left',padx=8)
        self.sampling_note=tk.StringVar()
        ttk.Label(frame,textvariable=self.sampling_note,wraplength=850,style='Status.TLabel').grid(row=8,column=0,sticky='w',pady=5)
        for variable in (self.fields['radius'],self.quality,self.extended_radius):
            variable.trace_add('write',self.update_sampling_note)
        self.update_sampling_note()
        progress_panel=ttk.LabelFrame(root,text='Assessment progress',padding=(12,6))
        progress_panel.grid(row=2,column=0,sticky='ew',padx=12,pady=(0,8))
        progress_panel.columnconfigure(0,weight=1)
        self.phase=tk.StringVar(value='Ready - location, terrain, modeling, maps, PDF')
        ttk.Label(progress_panel,textvariable=self.phase).grid(row=0,column=0,sticky='w')
        self.progress_bar=ttk.Progressbar(progress_panel,mode='indeterminate')
        self.progress_bar.grid(row=1,column=0,sticky='ew',pady=4)
        self.activity=tk.Text(progress_panel,height=4,font=('Segoe UI',9),wrap='word',state='disabled',
                              bg='white',fg='#315366',relief='flat')
        self.activity.grid(row=2,column=0,sticky='ew')
        activity_scroll=ttk.Scrollbar(progress_panel,command=self.activity.yview)
        activity_scroll.grid(row=2,column=1,sticky='ns')
        self.activity.configure(yscrollcommand=activity_scroll.set)
        self.started_at=None
        self.phase_number=0
        self.last_activity=''
        menu=tk.Menu(root)
        help_menu=tk.Menu(menu,tearoff=False)
        help_menu.add_command(label='Load demo site',command=self.load_demo_site)
        menu.add_cascade(label='Help',menu=help_menu)
        root.configure(menu=menu)
        root.after(100,self.poll)

    def update_sampling_note(self,*args):
        try:
            radius=float(self.fields['radius'].get())
            if not math.isfinite(radius) or radius<=0:
                raise ValueError()
        except ValueError:
            self.sampling_note.set('Enter a radius to see geographic sampling spacing.')
            return
        count=25 if self.quality.get()=='Quick' else 51
        limit=40 if self.extended_radius.get() else 20
        message=f'Nominal sample spacing: {2*radius/(count-1):.2f} mi. Current radius limit: {limit} mi.'
        if radius>limit:
            message+=' Enable extended radius under Advanced settings.' if radius<=40 else ' Maximum supported radius is 40 mi.'
        elif radius>20:
            message+=' Larger areas can take longer and use coarser terrain. Actual terrain spacing is reported after download.'
        self.sampling_note.set(message)

    def log_activity(self,message):
        # Keep stage transitions and data provenance; avoid one line per grid sample.
        if message==self.last_activity:
            return
        self.last_activity=message
        elapsed=int(time.monotonic()-self.started_at) if self.started_at else 0
        self.activity.configure(state='normal')
        self.activity.insert('end',f'{elapsed//60:02d}:{elapsed%60:02d}  {message}\n')
        self.activity.see('end')
        self.activity.configure(state='disabled')

    def show_progress(self,message):
        stage=self.phase_number
        if message.startswith(('Checking','Looking up the street')):stage=1
        elif message.startswith(('Looking up public','Extracting USGS')):stage=2
        elif message.startswith(('Mapping the local','Modeling','Screening','Running Longley','Geographic','Loading geographic','Comparing')):stage=3
        elif message.startswith('Fetching aerial'):stage=4
        elif message.startswith('Writing PDF'):stage=5
        names={1:'Checking location',2:'Getting terrain and repeater data',3:'Modeling paths and coverage',4:'Fetching context maps',5:'Building PDF and field checklist'}
        stage=max(stage,self.phase_number)
        if stage!=self.phase_number:
            self.phase_number=stage
            self.log_activity(f'Stage {stage}/5: {names[stage]}')
        if message.startswith('Data:'):
            self.log_activity(message)
        else:
            self.phase.set(f'Stage {stage}/5 - {message}')
        self.status.set(message)

    def toggle_advanced(self):
        if self.advanced_open.get():
            self.destination_panel.grid_remove()
            self.advanced.grid(row=2,column=0,sticky='ew')
        else:
            self.advanced.grid_remove()
            self.destination_panel.grid()

    def entry(self,parent,key,label,initial,row,col,width):
        var=tk.StringVar(value=initial)
        self.fields[key]=var
        ttk.Label(parent,text=label).grid(row=row*2,column=col,sticky='w',padx=5)
        ttk.Entry(parent,textvariable=var,width=width).grid(row=row*2+1,column=col,sticky='w',padx=5,pady=(2,5))

    def browse(self):
        folder=filedialog.askdirectory(parent=self.root)
        if folder:
            self.folder.set(folder)

    def load_demo_site(self):
        if self.running:
            self.status.set('Wait for the assessment to finish before loading the demo site.')
            return
        self.example()
        self.status.set('Demo site loaded: Aurora Fire Department Station 500. Review the sample inputs before generating a report.')

    def example(self):
        for key,value in [('site','Aurora Fire Department Station 500'),('lat','39.0357339'),('lon','-84.929813'),
                          ('heights','20, 40, 65'),('radius','8'),('handheld','5'),('freq','910.525'),
                          ('bw','62.5'),('sf','7'),('cr','5'),('repeater','33')]:
            self.fields[key].set(value)
        self.discover.set(True)
        self.fields['address'].set('5950 Dutch Hollow Road, Aurora, IN 47001')
        self.targets.delete('1.0','end')
        self.targets.insert('1.0','Aurora City Hall, 39.05528, -84.90000, 5, handheld\n'
                                 'Downtown Lawrenceburg, 39.0913, -84.8499, 5, handheld\n'
                                 'Dillsboro town center, 39.0178, -85.0580, 5, handheld')

    def settings(self):
        values={key:var.get().strip() for key,var in self.fields.items()}
        if len(values['site'])>90:
            raise ValueError('Site name must be 90 characters or fewer.')
        if len(values['prepared_for'])>100:
            raise ValueError('Prepared for must be 100 characters or fewer.')
        address=values['address']
        if len(address)>100:
            raise ValueError('Address must be 100 characters or fewer.')
        if bool(values['lat'])!=bool(values['lon']):
            raise ValueError('Enter both latitude and longitude, or clear both to use the address.')
        origin=point(values['lat'],values['lon']) if values['lat'] else None
        if origin is None and not address:
            raise ValueError('Enter a street address or GPS coordinates.')
        heights=sorted(set(number(h,3.3,492,'Station antenna height (ft)')*terrain.FOOT for h in values['heights'].split(',')))
        if len(heights)>3:
            raise ValueError('Enter up to three different station heights.')
        lines=[line.strip() for line in self.targets.get('1.0','end').splitlines() if line.strip()]
        if len(lines)>5:
            raise ValueError('Enter up to five test destinations.')
        targets=[]
        for i,line in enumerate(lines,1):
            parts=[part.strip() for part in line.split(',')]
            if len(parts)!=5 or not 1<=len(parts[0])<=60 or parts[-1].lower() not in ('handheld','repeater'):
                raise ValueError(f'Test destination {i} needs a name, latitude, longitude, height, and type.')
            name,lat,lon,h,kind=parts
            dest=point(lat,lon)
            targets.append((name,dest,number(h,1.65,492,'Destination height (ft)')*terrain.FOOT,kind.title(),None))
        if values['sf'] not in tuple(str(i) for i in range(5,13)) or values['cr'] not in ('5','6','7','8'):
            raise ValueError('Enter an integer SF from 5 to 12 and CR denominator from 5 to 8.')
        if not self.folder.get().strip():
            raise ValueError('Choose a report folder.')
        budget={key:number(values[key],minimum,maximum,label)
                for key,label,_,minimum,maximum in self.budget_fields}
        return dict(quality=self.quality.get(),alternatives=planning.alternatives(self.alternatives_text.get()),measurements=[dict(x) for x in self.measurements],site=values['site'],prepared_for=values['prepared_for'],budget=budget,
                    origin=origin,address=address,heights=heights,
                    radius=number(values['radius'],1,40 if self.extended_radius.get() else 20,'Plot radius (enable extended radius in Advanced settings for up to 40 mi)'),
                    handheld=number(values['handheld'],1.65,32.8,'Handheld height (ft)')*terrain.FOOT,
                    repeater_height=number(values['repeater'],3.3,492,'Repeater RX height (ft)')*terrain.FOOT,
                    discover=self.discover.get(),targets=targets,
                    radio=(number(values['freq'],902,928,'Frequency'),
                           number(values['bw'],7.8,500,'Bandwidth'),int(values['sf']),int(values['cr'])))

    def submit(self):
        if self.running:
            return
        try:
            settings=self.settings()
            folder=Path(self.folder.get().strip()).expanduser()
            folder.mkdir(parents=True,exist_ok=True)
        except (ValueError,OSError) as error:
            self.status.set(str(error))
            return
        self.running=True
        self.generate.configure(state='disabled')
        self.open_report.configure(state='disabled')
        self.started_at=time.monotonic()
        self.phase_number=0
        self.last_activity=''
        self.activity.configure(state='normal')
        self.activity.delete('1.0','end')
        self.activity.configure(state='disabled')
        self.progress_bar.start(12)
        self.show_progress('Checking the location...')
        threading.Thread(target=self.worker,args=(settings,folder),daemon=True).start()

    def worker(self,settings,folder):
        stage='Checking the location'
        def progress(message):
            nonlocal stage
            stage=message.rstrip('.')
            self.events.put(('progress',message))
        try:
            settings['location_source']='Entered GPS coordinates'
            if settings['origin'] is None:
                progress('Looking up the street address...')
                (lat,lon),settings['address']=terrain.geocode(settings['address'])
                settings['origin']=point(str(lat),str(lon))
                settings['location_source']='Census address estimate'
            lat,lon=settings['origin']
            settings['site']=settings['site'] or settings['address'] or f'Site at {lat:.5f}, {lon:.5f}'
            for name,dest,_,_,_ in settings['targets']:
                if not 105<=terrain.distance(settings['origin'],dest)<=40*terrain.MILE:
                    raise ValueError(f'{name} must be between 345 ft and 40 mi from the site.')
            data=terrain.run(settings,progress)
            deployment.enhance(settings,data,progress)
            progress('Fetching aerial, topographic and street maps...')
            data['context_maps']=context_maps.fetch(settings['origin'],terrain.request)
            for item in data['context_maps']:
                progress('Data: '+item['title']+' - '+('Downloaded' if item['image'] is not None else 'Unavailable'))
            progress('Writing PDF assessment and field checklist...')
            slug=re.sub(r'[^A-Za-z0-9]+','-',settings['site']).strip('-') or 'Site'
            filename=folder/f'{slug}-{datetime.now():%Y%m%d-%H%M%S-%f}-MeshCore.pdf'
            report.build(filename,settings,data)
            self.events.put(('success',(filename,data['warnings'],settings,data)))
        except Exception as error:
            traceback.print_exc()
            self.events.put(('error',f'{stage}. {error}' if isinstance(error,OSError) else str(error)))

    def poll(self):
        while not self.events.empty():
            kind,value=self.events.get_nowait()
            if kind=='progress':
                self.show_progress(value)
            else:
                self.running=False
                self.progress_bar.stop()
                self.generate.configure(state='normal')
                if kind=='success':
                    self.output,warnings,settings,data=value
                    self.last_result=(settings,data)
                    self.phase.set('Complete - PDF and field checklist ready')
                    self.log_activity('Complete: PDF and one-page field checklist saved.')
                    self.status.set('PDF ready. '+(' '.join(warnings) if warnings else 'Select Open PDF to view it.'))
                    self.open_report.configure(state='normal')
                else:
                    self.phase.set('Stopped - assessment could not finish')
                    self.log_activity('Error: '+value)
                    self.status.set(f'Assessment could not finish. {value}')
        self.root.after(100,self.poll)

    def open(self):
        if self.output:
            try:
                os.startfile(self.output)
            except OSError as error:
                self.status.set(str(error))

if __name__=='__main__':
    root=tk.Tk()
    App(root)
    root.mainloop()


