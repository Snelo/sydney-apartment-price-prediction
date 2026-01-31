# Property Project Research
Using this document to save and collect thoughts.
## Current Process to collect data
1. Use Google Maps to define a polygon that includes all the Local Government Areas (LGAs) of interest, save as a KML (?) file.
2. Re-write `nsw_units_pipeline.py`, `01_import_from_NSW_arcGIS_REST.ipynb` to deal with 
    a polygon. Create a new module to accept the KML file and re-write it for input into
    [NSW Spatial][spatial].\
    Data to extract from [N]


[valgen]: https://valuation.property.nsw.gov.au/embed/propertySalesInformation
[spatial]: https://portal.spatial.nsw.gov.au/server/rest/services/NSW_Land_Parcel_Property_Theme_multiCRS/FeatureServer/12/query