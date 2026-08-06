## Seismo-Acoustic Extension (New!)

The bridge now integrates **seismic and infrasound data** from USArray stations to monitor hurricanes. Following the breakthrough research by Ji et al. (2024) in *Science*, we compute:

- **Turbulent dissipation rate** from infrasound pressure spectra.
- **Ground displacement** from quasi-static elastic response.
- **Wind speed** from infrasound pressure.

These physical quantities are coupled with traditional buoy and satellite data to provide a **continuous, high-resolution view** of the hurricane's boundary layer. 

We also include a **JEPA manifold** that learns a predictive latent representation of the storm's seismo-acoustic state, enabling short-term intensity forecasts.

Check out `demo_seismo_jepa.ipynb` for a complete demonstration.
