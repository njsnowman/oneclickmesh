# One Click Mesh

Desktop coverage planning tool from Indiana Mesh Alliance (IMA), a 501(c)(3) nonprofit.

One Click Mesh combines USGS 3DEP terrain, local terrain and map views, 5 km line-of-sight screening, Longley–Rice / NTIA ITM propagation, candidate-site comparisons, field-test data, and a formatted PDF assessment. It is a planning aid; field measurements are needed to validate radio performance.

## Run on Windows

1. Install Python 3.10 or newer with Tcl/Tk and the Python launcher.
2. From the repository folder, run `py -3 -m pip install -r requirements.txt`.
3. Start the app with `scripts\\run-windows.cmd`.

The first run needs an internet connection for address lookup, USGS elevation, basemaps, and optional public repeater discovery. Elevation inputs are cached locally between runs.

## Build a Windows executable

Run `scripts\\build-windows.ps1` from PowerShell on Windows. The build uses PyInstaller and the bundled NTIA ITM library. The output is written to `dist\\One-Click-Mesh.exe`.

## Build for macOS

Pushes to `main` build downloadable macOS app archives for Apple Silicon and Intel in GitHub Actions. Open the repository's Actions tab, select **Build macOS app**, and download the artifact matching the Mac's processor. The ZIP contains `One-Click-Mesh.app`; drag it to Applications to install. The app is not code-signed or notarized, so macOS may require opening it with Control-click → **Open** the first time.

The macOS build compiles the NTIA ITM v1.4 source into a native library before packaging. To reproduce locally on a Mac, install Python 3.12 and Xcode Command Line Tools, install `requirements-build.txt`, clone `https://github.com/NTIA/itm` at tag `v1.4`, run `scripts/build-itm-macos.sh <path-to-ntia-itm>`, then run `python -m PyInstaller --noconfirm --clean packaging/one-click-mesh.spec`.

## Repository layout

```text
app/          Desktop interface and coverage, mapping, propagation, and PDF modules
docs/         User guide, architecture notes, and data-source notes
licenses/     Third-party notices and the NTIA ITM software disclaimer
resources/    Reusable CSV templates
scripts/      Windows run and build helpers
packaging/    PyInstaller configuration
```

## Data and privacy

Reports are saved to a local `Reports` folder by default. Terrain cache files go under the operating system's temporary directory. The repository does not include generated customer reports, site-specific project files, terrain downloads, or local build outputs.

## Modeling limits

The tool targets the contiguous United States. Terrain and propagation outputs depend on input coordinates, terrain resolution, radio assumptions, and model settings. Buildings, vegetation, interference, antenna installation, and live mesh routing can change actual results. See the user guide for detailed interpretation and known limits.

## License

No license has been selected for the One Click Mesh application source. Until its owner chooses one, the application source remains under its default copyright. The NTIA ITM library has separate terms; see `licenses/NTIA-ITM-LICENSE.md`.
