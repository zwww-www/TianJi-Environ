# Reproducibility Notes

The current release supports three levels of inspection.

1. Direct inspection: final figures, figure source-data CSV files, H1/H2 branch tables, diagnostic-task figures, and summarized system-trace tables can be inspected directly from this repository.
2. Lightweight reruns: selected figure-building and diagnostic scripts are included under `scripts/` and `configs/`. These are intended to document the transformation from curated tables to manuscript-facing artifacts.
3. Full WRF-Chem reproduction: reproducing the original simulations requires a configured WRF-Chem environment, meteorological and emissions inputs, model physics and chemistry settings, and compute resources. These third-party/model assets are not redistributed here.

For manuscript consistency, H1 refers to the North China Plain summertime ozone-response case, and H2 refers to the Guanzhong Basin wintertime black-carbon/PM2.5 feedback case.
