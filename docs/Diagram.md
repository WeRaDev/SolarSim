# Diagram


## Online
Open link to view the chart: 
https://www.mermaidchart.com/app/diagrams/7b9d6222-be50-4692-9cdc-b0e12a5f6c8c?ref=vscode


## SVG

![Alt text](./Diagram.svg)

### Source
```
graph TD
    A[Solar Panels 947.52 kWp] --> B[MPPT Charge Controllers]
    B --> C{Smart Power Distribution Unit}
    C -->|Priority 1| D[Inverter for Servers]
    C -->|Priority 2| E[Inverter for Irrigation]
    C -->|Priority 3| F[Inverter for GPUs]
    C -->|Priority 4| G[Inverter for Batteries]
    G --> H[Lithium-ion Batteries 500 kWh]
    H -.->|Backup Power| D
    H -.->|Excess Capacity| F
    D --> I[Data Center Servers]
    E --> J[Irrigation System]
    F --> K[GPU Cluster]
```