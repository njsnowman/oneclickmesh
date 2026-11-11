# One Click Mesh
Indiana Mesh Alliance (IMA) | 501(c)(3) nonprofit

## Start
For the packaged Windows app, open `One-Click-Mesh.exe`. Python installation is not required. To run from source, follow the setup steps in the repository README.
Internet access is needed for fresh USGS terrain, address lookup, maps and public repeater discovery. Existing terrain files can be reused from the local cache.

## Generate a report
1. Enter GPS coordinates OR a complete street address. GPS takes precedence when both are filled. Verify the antenna location, especially when using a street-address estimate.
2. Enter station heights in feet and radius in miles. Add Prepared for if needed.
3. Review radio settings and Advanced settings. Station, handheld and repeater transmit power and receive sensitivity are separate. Loss fields are cable/system losses at each endpoint.
4. Choose Quick or Detailed geographic sampling. Detailed increases sample density, not terrain resolution.
5. Click Generate assessment, then Open PDF. Reports are saved in your chosen folder. Save/open projects, map placement, planning tools, and path inspection are grouped under More tools.

Scroll vertically or horizontally when using a smaller display or increased Windows scaling. Advanced settings expand below the report controls; destination fields stay visible.

## New planning tools
- Place on map (More tools > Place on map): load aerial or street imagery, pan/zoom, click a point and use it as the station, a destination or a candidate site. If GPS is empty, the picker starts at the Aurora example; it does not geocode the address. Map-added destinations start as handhelds at 5 ft; edit their height/type in the main form if necessary.
- Planning tools (More tools > Planning tools): enter up to two additional candidate sites. All candidates use the same heights and the primary site's entered/discovered destinations. A comparison with no destinations cannot rank sites.
- Save/Open project (More tools): preserve the form, candidates and imported measurements in an .ocm.json file. Open the project and generate again to refresh model results. Reports and terrain are not embedded in project files.
- Inspect paths (More tools > Inspect paths): after generation, select a destination to see each direction's margin, terrain/Fresnel clearance and ITM flags. The PDF includes terrain profiles at the middle tested height.

## Field-test CSV
Use `resources/Field-Test-Template.csv` as a header template. Add one record per test location.
Required: latitude, longitude, sent, received.
Optional: rssi (dBm), snr (dB), repeater, timestamp.
GPS uses decimal degrees. Sent must be positive; received must be between zero and sent. Counts must be whole numbers. Up to 2,000 records are supported.
Import through Planning tools. Imported points are stored in the project and included in the next PDF. Clear field tests removes them from the current form.

The measured overlay displays packet delivery; the separate prediction uses a direct handheld path and the entered hardware settings. Logs may involve different equipment or multiple hops. The app does not automatically calibrate ITM from those logs. Predictions are unavailable for tests outside the chosen radius or within 345 ft of the modeled station.

## Interpretation
Green predicted samples mean BOTH directions meet the selected margin target. Gold means both meet sensitivity but at least one misses the margin target. Rust means at least one is below sensitivity. Gray means unavailable.
Quick uses a 25-by-25 candidate grid; Detailed uses 51-by-51. Only points within the circular radius and outside the central 345 ft are modeled. Colored squares identify discrete samples; they do not establish continuous or guaranteed coverage.
Terrain uses USGS 3DEP bare-earth data. Propagation uses the bundled NTIA ITM v1.4 engine. The independent 3.11-mile LOS screening remains available. Imagery and street maps are context layers; Street View opens through a PDF link where imagery is available.
Buildings, foliage, interference and actual packet routing are not modeled. Confirm radio sensitivity for your hardware/preset and validate both directions in the field. Cache timestamps reflect retrieval, not terrain survey dates. The data record shows reused or downloaded inputs.

## Progress and field checklist
The fixed progress panel shows five stages: location, terrain/repeater inputs, path modeling, context maps, and PDF creation. Its scrollable activity log records elapsed time and whether inputs were downloaded, reused from cache, or unavailable. The moving bar indicates activity, not a percentage or time estimate.

Every new report includes a one-page Field test checklist near the front. Print one copy per station height or candidate site tested. Destinations, GPS coordinates, endpoint heights, planned station heights and radio settings are prefilled. Record actual mounting height, two-way sent/received packet counts, RSSI, SNR, route/repeater heard and field conditions. When there are no destinations, blank rows are provided.

## Extended coverage radius
The default remains 8 mi. For radii above 20 mi, open Advanced settings and select Allow extended coverage radius, then enter a radius up to 40 mi in the main site fields. The setting is saved in projects. The form shows nominal geographic sampling spacing before generation. At 40 mi, Quick spacing is 3.33 mi and Detailed spacing is 1.60 mi. These are sparse regional predictions, not continuous service coverage.

Larger areas can take longer to download and model. The progress log and PDF report actual USGS raster spacing. The raster is capped at 3,072 cells per side, so large extents may be coarser than typical local studies; resampling a profile does not restore lost terrain detail. Terrain spacing above approximately 115 ft triggers a report note. Named destination paths remain limited to 40 mi; LOS screening remains 3.11 mi.

Extended studies download four smaller terrain tiles rather than one large export. Temporary network/server failures are retried up to two times and shown in the activity log. Cached tiles are reused on later runs.


## Demo site
Choose Help > Load demo site to fill in Aurora Fire Department Station 500 and sample destinations from the original example. This replaces the site and destination inputs. It is optional and is not part of normal report generation.


## Maps in the coverage report
The site overview numbers the primary station, destinations / public repeaters and candidate stations; the register gives each marker's role, GPS coordinates and endpoint height. Direct station-to-destination links are colored at each tested station height by the weaker direction's margin. Separate terrain-bottleneck markers show the most restrictive sampled 60% Fresnel point on named paths; click a marker in a PDF viewer to open that path's profile. Candidate maps compare replacing the primary location with that candidate on the common sample grid, using the same radio settings and margin target. They do not model adding a relay. Unavailable or out-of-range samples stay gray/unknown. The report notes the map imagery source and the terrain-source spacing.
