# Predicting Sydney Apartment Sale Prices

## Overview
This project analyses historical apartment/unit sales across the Sydney metropolitan region to identify the key drivers of sale prices and to develop predictive models using property, temporal, and regional features.

## Business Question
Which factors most strongly influence apartment sale prices in Sydney, and how accurately can historical data be used to predict unit prices? Particularly focusing on 2 and 3 bedroom units in Canada Bay, Ryde and the City of Parramatta Local Government Area.

## Data Sources
- NSW Property Sales Data 
    - Bulk Sales Information is available on https://valuation.property.nsw.gov.au/embed/propertySalesInformation. There was a format change in 2001, so sales prior to that are not being considered.
- Australian Bureau of Statistics (ABS)
- Reserve Bank of Australia (interest rates) 
    The webpage https://www.rba.gov.au/statistics/tables/ has statistical data,specifically
    - https://www.rba.gov.au/statistics/tables/csv/g1-data.csv?v=2026-01-19-13-03-25  has the Consumer Price Index dating back to 1922. 
    - https://www.rba.gov.au/statistics/tables/csv/f5-data.csv?v=2026-01-19-13-03-25 has Indicator Lending rates dating back to 1959
- Domain API (Current listings) to be considered for future enhancement
### Data Dictionary
see `entity_relationship_diagram.md` for a mermaid ERD with data definitions. 

[sales]: https://valuation.property.nsw.gov.au/embed/propertySalesInformation
[spatial]: https://portal.spatial.nsw.gov.au/server/rest/services/NSW_Land_Parcel_Property_Theme_multiCRS/FeatureServer/12/query
## Planned Approach
# Property Project Research
Using this document to save and collect thoughts.
## Current Process to collect data
1. Use Google Maps to define a polygon that includes all the Local Government Areas (LGAs) of interest, save as a KML (?) file.
2. Re-write `nsw_units_pipeline.py`, `01_import_from_NSW_arcGIS_REST.ipynb` to deal with 
    a polygon. Create a new module to accept the KML file and re-write it for input into
    [NSW Spatial][spatial].\
    Data to extract from [N]



## Deliverables
- Clean analytical dataset
- Predictive price models
- Visual insights and interpretation

## Possible Enhancements
- Domain API (Current listings) integration

## Process 
1.  Specify a rectangle that includes all properties of interest using Google Plus Codes. 
    This will include the LGAs of Canada Bay, Ryde, and the City of Parramatta. Naturally,
    it will overlap into other LGAs. __Future development__ supply a polygon.
2.  Convert the Google Plus Codes to Lat/Long for input to [Spatial][spatial]
3.  Tile the input area and extract data into Pandas data frames: 
    1.  Extract the 'Principal Addresses' where\
    `principaladdresstype = 1 AND superlot='Y' AND enddate = 32503680000000`\
    This selects the blocks of units that are still in existance.
    May want to use `urbanity='U'`. Only interested in the following fields, :\ 
    `[valnetlotcount, propid, address, centroid.x, centroid.y, OBJECTID]`\
    (NB: **OBJECTID** is unique)
    2. Extract the 'Secondary Address' where\
    `principaladdresstype = 2 AND propid IN {SELECT propid FROM step 1}`\
    The output fields of interest are, note `(housenumber,propid)` is unique:\
    `[housenumber, propid, OBJECTID]`

    NB 1: The documents suggest that I should be able to get the `council` and 
    `deliverypointid`. If so, I will.\
    NB 2: The `propid` is the link to the NSW Valuer Generals data
4.  Extract Property sales data from [Valuer General][valgen]. Note:
    1.  Two fields are required for uniqueness `propid,unit`
    2.  Historical data will be processed locally from Annual Sales (~340 MB) reducing 
    it to just the desired LGAs and property types. 
    3.  For the current year - upload the weekly ZIP files to AWS S3 and process.
    4.  Wish to keep all sales.

[valgen]: https://valuation.property.nsw.gov.au/embed/propertySalesInformation
[spatial]: https://portal.spatial.nsw.gov.au/server/rest/services/NSW_Land_Parcel_Property_Theme_multiCRS/FeatureServer/12/quer
