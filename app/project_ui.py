"""Project tools and detailed results for One Click Mesh."""
import tkinter as tk
from tkinter import ttk, filedialog
import planning
from terrain import FOOT
from planning import margins

class Tools:
    def snapshot(self):
        return dict(fields={k:v.get() for k,v in self.fields.items()},targets=self.targets.get('1.0','end').strip(),
                    alternatives=self.alternatives_text.get(),quality=self.quality.get(),folder=self.folder.get(),
                    discover=self.discover.get(),measurements=self.measurements,extended_radius=self.extended_radius.get())

    def apply_project(self,data):
        for key,value in data['fields'].items():
            if key in self.fields:
                self.fields[key].set(value)
        self.targets.delete('1.0','end')
        self.targets.insert('1.0',data.get('targets',''))
        self.alternatives_text.set(data.get('alternatives',''))
        self.quality.set(data.get('quality','Quick'))
        self.extended_radius.set(data.get('extended_radius',False))
        self.folder.set(data.get('folder',self.folder.get()))
        self.discover.set(data['discover'])
        self.measurements=data.get('measurements',[])

    def save_project(self):
        path=filedialog.asksaveasfilename(parent=self.root,defaultextension='.ocm.json',filetypes=[('One Click Mesh project','*.json')])
        if path:
            try:
                planning.write_project(path,self.snapshot())
                self.status.set('Project saved, including imported field measurements.')
            except (OSError,ValueError) as error:
                self.status.set(str(error))

    def load_project(self):
        if self.running:
            self.status.set('Wait for the current assessment before opening another project.')
            return
        path=filedialog.askopenfilename(parent=self.root,filetypes=[('One Click Mesh project','*.json')])
        if path:
            old=self.snapshot()
            try:
                data=planning.read_project(path)
                planning.alternatives(data.get('alternatives',''))
                if data.get('quality','Quick') not in ('Quick','Detailed'):
                    raise ValueError('Unknown sampling quality.')
                self.apply_project(data)
                self.status.set('Project loaded. Generate assessment to refresh predictions.')
            except (OSError,ValueError,TypeError,KeyError,AttributeError) as error:
                self.apply_project(old)
                self.status.set(f'Project could not be opened: {error}')

    def planning_tools(self):
        win=tk.Toplevel(self.root)
        win.title('One Click Mesh | Deployment planning')
        frame=ttk.Frame(win,padding=18)
        frame.pack(fill='both',expand=True)
        ttk.Label(frame,text='Compare up to two additional sites against the same destinations.').pack(anchor='w')
        ttk.Label(frame,text='One per line: Name, latitude, longitude').pack(anchor='w',pady=(8,3))
        candidates=tk.Text(frame,width=72,height=4,font=('Consolas',10))
        candidates.pack(fill='x')
        candidates.insert('1.0',self.alternatives_text.get())
        info=tk.StringVar(value=f'{len(self.measurements)} field-test points imported.')
        ttk.Label(frame,textvariable=info,wraplength=550).pack(anchor='w',pady=10)
        ttk.Label(frame,text='CSV required: latitude, longitude, sent, received\nOptional: rssi, snr, repeater, timestamp. Maximum 2,000 rows.',wraplength=550).pack(anchor='w')
        def import_csv():
            path=filedialog.askopenfilename(parent=win,filetypes=[('Field-test CSV','*.csv')])
            if path:
                try:
                    rows=planning.measurements(path)
                    self.measurements=rows
                    info.set(f'{len(rows)} field-test points imported.')
                except (OSError,ValueError,TypeError,AttributeError) as error:
                    info.set(str(error))
        def clear():
            self.measurements=[]
            info.set('Field-test data cleared.')
        buttons=ttk.Frame(frame);buttons.pack(fill='x',pady=10)
        ttk.Button(buttons,text='Import field-test CSV',command=import_csv).pack(side='left')
        ttk.Button(buttons,text='Clear field tests',command=clear).pack(side='left',padx=8)
        def save():
            try:
                value=candidates.get('1.0','end').strip()
                planning.alternatives(value)
                self.alternatives_text.set(value)
                win.destroy()
            except ValueError as error:
                info.set(str(error))
        ttk.Button(frame,text='Apply candidate sites',command=save,style='Primary.TButton').pack(anchor='e')

    def inspect_results(self):
        if not getattr(self,'last_result',None):
            self.status.set('Generate an assessment first.')
            return
        s,r=self.last_result
        win=tk.Toplevel(self.root)
        win.title('One Click Mesh | Path inspector')
        win.geometry('950x650')
        frame=ttk.Frame(win,padding=15);frame.pack(fill='both',expand=True)
        ttk.Label(frame,text='Select a destination to inspect both directions and terrain clearance.').pack(anchor='w')
        split=ttk.Panedwindow(frame,orient='horizontal');split.pack(fill='both',expand=True,pady=10)
        left=ttk.Frame(split);right=ttk.Frame(split);split.add(left,weight=1);split.add(right,weight=3)
        listing=tk.Listbox(left,width=30,exportselection=False);listing.pack(fill='both',expand=True)
        details=tk.Text(right,wrap='word',font=('Segoe UI',11),padx=12,pady=12)
        scroll=ttk.Scrollbar(right,command=details.yview);scroll.pack(side='right',fill='y')
        details.configure(yscrollcommand=scroll.set);details.pack(fill='both',expand=True)
        entries=[]
        for scenario in r['scenarios']:
            for path in scenario['paths']:
                entries.append((scenario,path))
                listing.insert('end',f'{scenario["name"]}: {path["name"]}')
        def select(event=None):
            if not listing.curselection():return
            scenario,path=entries[listing.curselection()[0]]
            lines=[f'{scenario["name"]} → {path["name"]}',f'{path["miles"]:.2f} mi | {path["kind"]} | RX height {path["rx"]/FOOT:g} ft','']
            for i,h in enumerate(s['heights']):
                loss,flag=path['losses'][i]
                lines.append(f'Station antenna: {h/FOOT:g} ft')
                if loss is None:
                    lines.append('ITM prediction unavailable')
                else:
                    down,up,weak=margins(loss,s['budget'],path['kind']=='Handheld')
                    lines.extend([f'ITM path loss: {loss:.1f} dB',f'Station → endpoint margin: {down:+.1f} dB',
                                  f'Endpoint → station margin: {up:+.1f} dB',
                                  f'Two-way target: {"MET" if weak>=s["budget"]["reserve"] else "MISSED"}',
                                  f'Minimum terrain clearance: {path["clearance"][i]/FOOT:.1f} ft',
                                  f'Minimum Fresnel clearance: {path["ratios"][i]*100:.0f}%'])
                lines.extend([f'Model flag: {flag or "none"}',''])
            lines.append('Predictions assume reciprocal propagation. Buildings, foliage and interference are not modeled. See PDF for the terrain profile.')
            details.configure(state='normal');details.delete('1.0','end');details.insert('1.0','\n'.join(lines));details.configure(state='disabled')
        listing.bind('<<ListboxSelect>>',select)
        if entries:listing.selection_set(0);select()
