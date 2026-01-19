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

## Planned Approach
- Cloud-based SQL analysis using AWS Athena
- Data cleaning and feature engineering in Python
- Regression and tree-based machine learning models
- Model evaluation and interpretability analysis

## Deliverables
- Clean analytical dataset
- Predictive price models
- Visual insights and interpretation

## Possible Enhancements
- Domain API (Current listings) integration

## Process 
1. Extract data locally from Annual Sales (~340 MB) reducing it to just the desired
LGAs and property types. Save the result as historical-sales.csv (or zip) for upload
to Amazon S3 bucket arn:aws:s3:::sydney-units-raw