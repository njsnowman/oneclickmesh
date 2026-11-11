"""Click-to-place antenna and destination map."""
import queue
import threading
import tkinter as tk
from tkinter import ttk, simpledialog
from PIL import ImageTk
import context_maps
import terrain

def open_picker(app):
    try:
        from plotter import point
        origin=point(app.fields['lat'].get(),app.fields['lon'].get())
    except ValueError:
        origin=(39.0357339,-84.929813)
    window=tk.Toplevel(app.root)
    window.title('One Click Mesh | Place locations')
    window.transient(app.root)
    center=list(origin)
    radius=[1.0]
    selection=[None]
    bounds=[None]
    responses=queue.Queue()
    generation=[0]
    frame=ttk.Frame(window,padding=12)
    frame.pack(fill='both',expand=True)
    status=tk.StringVar(value='Loading map...')
    layer=tk.StringVar(value='Aerial')
    toolbar=ttk.Frame(frame)
    toolbar.pack(fill='x')
    canvas=tk.Canvas(frame,width=520,height=520,highlightthickness=0,bg='#E3EBEF')
    canvas.pack(pady=8)
    ttk.Label(frame,textvariable=status,wraplength=520).pack(anchor='w')
    ttk.Label(frame,text='Maps: USDA / USGS and Esri World Street Map contributors.',wraplength=520).pack(anchor='w')
    actions=ttk.Frame(frame)
    actions.pack(fill='x',pady=8)

    def load():
        generation[0]+=1
        token=generation[0]
        selection[0]=None
        bounds[0]=None
        status.set('Loading map...')
        # Tk variables must be read on the UI thread.
        selected_layer=layer.get()
        selected_center,selected_radius=tuple(center),radius[0]
        def worker():
            try:
                value=context_maps.square(selected_center,selected_radius,terrain.request,selected_layer)
                responses.put((token,value,None))
            except Exception as error:
                responses.put((token,None,str(error)))
        threading.Thread(target=worker,daemon=True).start()

    def poll():
        if not window.winfo_exists():
            return
        while not responses.empty():
            token,value,error=responses.get_nowait()
            if token!=generation[0]:
                continue
            if error:
                status.set(error)
                continue
            bounds[0]=value['bounds']
            photo=ImageTk.PhotoImage(value['image'].resize((520,520)),master=window)
            canvas.photo=photo
            canvas.delete('all')
            canvas.create_image(0,0,image=photo,anchor='nw')
            status.set(f'Click a location. Map width {radius[0]*2:g} mi. North is up.')
        window.after(100,poll)

    def select(event):
        if bounds[0] is None:
            return
        selection[0]=context_maps.map_point(bounds[0],event.x/520,event.y/520)
        canvas.delete('pin')
        canvas.create_oval(event.x-6,event.y-6,event.x+6,event.y+6,fill='#00796B',outline='white',width=2,tags='pin')
        lat,lon=selection[0]
        status.set(f'Selected {lat:.6f}, {lon:.6f}')

    def use(mode):
        if selection[0] is None:
            status.set('Click a location on the map first.')
            return
        lat,lon=selection[0]
        if not 24<=lat<=50 or not -125<=lon<=-66:
            status.set('Select a location in the supported contiguous US area.')
            return
        if mode=='site':
            app.fields['lat'].set(f'{lat:.7f}')
            app.fields['lon'].set(f'{lon:.7f}')
            app.fields['address'].set('')
        else:
            name=simpledialog.askstring('Location name','Name for this location',parent=window)
            if not name:
                return
            name=name.replace(',',' ').strip()[:60]
            if mode=='target':
                current=app.targets.get('1.0','end').strip()
                if len(current.splitlines())>=5:
                    status.set('Up to five destinations are supported.')
                    return
                app.targets.insert('end',('\n' if current else '')+f'{name}, {lat:.7f}, {lon:.7f}, 5, handheld\n')
            else:
                current=app.alternatives_text.get().strip()
                if len(current.splitlines())>=2:
                    status.set('Up to two additional sites are supported.')
                    return
                app.alternatives_text.set(current+('\n' if current else '')+f'{name}, {lat:.7f}, {lon:.7f}')
        status.set('Location added to the assessment.')

    def zoom(factor):
        if selection[0]:
            center[:]=selection[0]
        radius[0]=max(.1,min(20,radius[0]*factor))
        load()

    def pan(dx,dy):
        if bounds[0]:
            center[:]=context_maps.map_point(bounds[0],.5+dx,.5+dy)
            load()

    ttk.Combobox(toolbar,textvariable=layer,values=('Aerial','Street'),state='readonly',width=10).pack(side='left')
    for label,command in [('Load',load),('+',lambda:zoom(.5)),('-',lambda:zoom(2)),
                          ('West',lambda:pan(-.35,0)),('East',lambda:pan(.35,0)),
                          ('North',lambda:pan(0,-.35)),('South',lambda:pan(0,.35))]:
        ttk.Button(toolbar,text=label,command=command).pack(side='left')
    for label,mode in [('Use as site','site'),('Add destination','target'),('Add candidate','candidate')]:
        ttk.Button(actions,text=label,command=lambda mode=mode:use(mode)).pack(side='left',padx=3)
    canvas.bind('<Button-1>',select)
    load()
    poll()
