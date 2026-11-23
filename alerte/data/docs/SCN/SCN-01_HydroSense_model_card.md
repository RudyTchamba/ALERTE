> FICTIONAL exercise material written by the ALERTE team.

# HydroSense model card (FICTIONAL system used in the ALERTE exercise)

## What it does
HydroSense forecasts river floods 6 to 24 hours ahead and drafts public warning messages (SMS text) for the authorities. It is being piloted in Douala (Wouri river) and the Far North (Logone river).

## Inputs
Rain gauges, river level sensors (7 on the Logone), satellite rainfall estimates and weather model outputs.

## Validity conditions
Forecasts are reliable only when at least 5 of 7 river sensors report data. Below that, HydroSense keeps producing forecasts but does not flag reduced reliability on its dashboard.

## Reported accuracy
In tests, about 80 percent of floods were detected 6 hours ahead, with about 1 false alarm for every 3 alerts.

## Outputs
Risk level (GREEN, YELLOW, ORANGE, RED), probability, expected time, affected area, draft SMS in French.

## Data processing
The vendor processes data on cloud servers outside Cameroon.

## Known limits
French-only messages; no correction or cancel message template; no human validation step built in.
