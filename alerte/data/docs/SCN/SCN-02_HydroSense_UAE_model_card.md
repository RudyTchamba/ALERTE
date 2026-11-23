> FICTIONAL exercise material written by the ALERTE team.

# HydroSense model card, UAE configuration (FICTIONAL system used in the ALERTE exercise)

## What it does
HydroSense forecasts flash floods 6 to 24 hours ahead and drafts public warning messages for the authorities. In this exercise it is piloted for Dubai and for the Al Ain wadi catchment.

## Inputs
Rain gauges, wadi level sensors (7 in the Al Ain catchment), satellite rainfall estimates and weather model outputs.

## Validity conditions
Forecasts are reliable only when at least 5 of 7 wadi sensors report data. Below that, HydroSense keeps producing forecasts but does not flag reduced reliability on its dashboard.

## Reported accuracy
In tests, about 80 percent of floods were detected 6 hours ahead, with about 1 false alarm for every 3 alerts.

## Outputs
Risk level (GREEN, YELLOW, ORANGE, RED), probability, expected time, affected area, draft message in English and Arabic.

## Data processing
The vendor processes data on cloud servers outside the UAE.

## Known limits
English and Arabic messages only; no correction or cancel message template; no human validation step built in; the vendor offers an optional automatic release mode that skips human validation.
