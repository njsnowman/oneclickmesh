# Architecture

The Windows desktop app uses Python's Tkinter interface. The modules are kept small and grouped in `app/`; they are launched as a flat application directory so PyInstaller and the existing module imports remain simple.

| Module | Responsibility |
| --- | --- |
| `plotter.py` | Main form, input validation, progress reporting, and orchestration |
| `terrain.py` | Address lookup, public-node discovery, USGS 3DEP downloads, terrain sampling, and LOS |
| `propagation.py` | Terrain raster access and NTIA ITM native-library binding |
| `context_maps.py` | Aerial, topo, street, and Street View context |
| `map_picker.py` | Click-to-place map dialog |
| `planning.py` | Radio link budgets, project files, and field-test CSV data |
| `deployment.py` | Coverage grid, path assessments, and candidate-site comparisons |
| `project_ui.py` | Planning tools and detailed result inspection UI |
| `field_checklist.py` | Printable one-page field-test checklist |
| `report.py` | Main PDF creation and shared PDF layout helpers |
| `report_maps.py` | Report maps and map annotations |
| `report_deployment.py` | Deployment comparison and field-measurement report sections |

The ITM native library is resolved beside `app/propagation.py`; the Windows bundle places it at the application root within PyInstaller's extracted runtime. Network inputs are fetched by the application and cached locally. Report files and site projects are not embedded in the executable.
