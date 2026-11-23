# ALERTE report: Rising Waters, UAE (core drill)

> **Fictional exercise. Not a real alert. HydroSense and all numbers in the events are invented; places and institutions are real.**

Run `ae-core-offline-20261110-101333-293d` · country AE · brain: offline · 12 events · 29 decisions · 18 gaps (10 confirmed by text) · 0.07 s

## Summary

- Gaps by type: G1 Nobody in charge (3), G2 Two in charge (3), G3 No procedure (5), G6 Nobody answers for harm (1), G7 People left out (2), G8 AI unchecked (3), G9 Channel unprotected (1)
- Planned gaps found (test T3): 14 of 14 (100%)
- Quotes verified (test T2): 8 of 8 (100%)
- Decisions with no legal basis found: 11
- Who wrote the decisions: rule engine (no AI) 27, scripted (HydroSense) 2

## Gap report

### G8-01 · AI unchecked: Check and validate an AI-generated forecast before it is used for a public decision

- **Type:** G8 AI unchecked · **Severity:** 3 (risk to life or rights) · **Status:** confirmed by text
- **When:** event(s) 2, 8, first at D1 06:20
- **What is missing:** No institution holds the power or duty to check and validate an AI-generated forecast before it is used for a public decision
- **Institutions concerned:** HYDRO, MET
- **Texts checked:** AE-S02, AE-S03, AE-S04, AE-S06
- **Evidence:** Who-does-what map (AE): no institution holds 'validate_ai_forecast'; drill:MET@2
- **How others handle it:**
    - *European Union*: [Regulation (EU) 2024/1689 (AI Act), Articles 14 and 26](https://eur-lex.europa.eu/eli/reg/2024/1689/oj). High-risk AI must allow effective human oversight, guard against over-reliance, and deployers must assign competent people to oversee it. *Note (written for Cameroon):* Cameroon could require a named forecaster to validate AI forecasts before public use, without adopting the whole AI Act.
    - *United States*: [FCC findings on the Hawaii false missile alert (2018)](https://www.fcc.gov/node/215906). Recommended second-person verification before any live alert is released. *Note (written for Cameroon):* A simple procedure rule, cheap to adopt.

### G2-02 · Two in charge: Decide to alert the public

- **Type:** G2 Two in charge · **Severity:** 3 (risk to life or rights) · **Status:** suspected (needs expert check)
- **When:** event(s) 3, first at D1 06:45
- **What is missing:** Several institutions hold 'decide to alert the public' and no text says who leads
- **Institutions concerned:** DPC, MOI
- **Texts checked:** AE-S02
- **Evidence:** AE-L02: DPC power (inferred); AE-L14: MOI power (inferred)
- **How others handle it:**
    - *Japan*: [J-Alert](https://www.city.inagi.tokyo.jp/en/kurashi/iza/1002270/1010142/1012096.html). For some hazards the national government pushes alerts automatically, removing delays in local decisions. *Note (written for Cameroon):* Useful for fast-onset hazards.
    - *United States*: [47 CFR Part 10 (Wireless Emergency Alerts)](https://www.ecfr.gov/current/title-47/chapter-I/subchapter-A/part-10). Only authorised alerting authorities may originate alerts. *Note (written for Cameroon):* Cameroon could name the authorised originators per hazard.
    - *Mauritius*: [Common Alerting Protocol adoption (2023)](https://www.preventionweb.net/quick/96844). Clear roles: the weather service issues, the disaster centre coordinates, the ICT authority disseminates, with one common alert format. *Note (written for Cameroon):* Naming one lead per step avoids two bodies claiming the same decision.

### G3-03 · No procedure: Approve an AI-drafted alert through a human validation step before release

- **Type:** G3 No procedure · **Severity:** 3 (risk to life or rights) · **Status:** confirmed by text
- **When:** event(s) 3, 12, first at D1 06:45
- **What is missing:** No institution holds the power or duty to approve an AI-drafted alert through a human validation step before release
- **Institutions concerned:** DPC, OPS
- **Texts checked:** AE-S02, AE-S03, AE-S06
- **Evidence:** Who-does-what map (AE): no institution holds 'human_validate_ai_alert'
- **How others handle it:**
    - *European Union*: [Regulation (EU) 2024/1689 (AI Act), Articles 14 and 26](https://eur-lex.europa.eu/eli/reg/2024/1689/oj). High-risk AI must allow effective human oversight, and deployers must assign competent people to oversee it. *Note (written for Cameroon):* A named person validating an AI-drafted alert before release can be required without adopting the whole Act.
    - *United States*: [FCC findings on the Hawaii false missile alert (2018)](https://www.fcc.gov/node/215906). Recommended second-person verification before any live alert is released and pre-scripted correction procedures. *Note (written for Cameroon):* A simple procedure rule, cheap to adopt.
    - *Mauritius*: [Common Alerting Protocol adoption (2023)](https://www.preventionweb.net/quick/96844). Written roles between the weather service, disaster agency and regulator, and one message format. *Note (written for Cameroon):* Writing the procedure down is the first step.

### G1-04 · Nobody in charge: Order mobile operators to relay a public alert

- **Type:** G1 Nobody in charge · **Severity:** 3 (risk to life or rights) · **Status:** confirmed by text
- **When:** event(s) 4, first at D1 07:10
- **What is missing:** No institution holds the power or duty to order mobile operators to relay a public alert
- **Institutions concerned:** OPS
- **Texts checked:** AE-S02
- **Evidence:** Who-does-what map (AE): no institution holds 'compel_operator_alert'
- **How others handle it:**
    - *European Union*: [Directive (EU) 2018/1972 (European Electronic Communications Code), Article 110](https://eur-lex.europa.eu/eli/dir/2018/1972/oj). Mobile operators must relay public warnings from the national public warning system to the end-users concerned. *Note (written for Cameroon):* A decree or ART decision could create the same duty; Cameroon would need to name the authority that originates the warning.
    - *Philippines*: [Republic Act No. 10639, Free Mobile Disaster Alerts Act (2014), Sections 4 and 6](https://issuances-library.senate.gov.ph/sites/default/files/2023-02/ra%252010639.pdf). Operators must send free alerts with content from named agencies; fines and franchise suspension for non-compliance. *Note (written for Cameroon):* Close to Cameroon's situation (a developing country with frequent hazards); requires naming content providers and setting penalties.
    - *United States*: [47 CFR Part 10 (Wireless Emergency Alerts) and WARN Act, Part 10](https://www.ecfr.gov/current/title-47/chapter-I/subchapter-A/part-10). Separates who originates alerts (authorised authorities), the national gateway, and the operators who transmit them. *Note (written for Cameroon):* Participation is voluntary in the US; a mandatory duty (EU, Philippines) may suit Cameroon better.

### G6-05 · Nobody answers for harm: Answer for harm caused by a wrong alert

- **Type:** G6 Nobody answers for harm · **Severity:** 3 (risk to life or rights) · **Status:** confirmed by text
- **When:** event(s) 5, first at D1 08:30
- **What is missing:** No institution holds the power or duty to answer for harm caused by a wrong alert
- **Institutions concerned:** ART, DPC
- **Texts checked:** AE-S02, AE-S03
- **Evidence:** Who-does-what map (AE): no institution holds 'liability_alert_harm'; drill:DPC@5; drill:ART@5
- **How others handle it:**
    - *United States*: [WARN Act (2006)](https://www.ecfr.gov/current/title-47/chapter-I/subchapter-A/part-10). Limits the liability of operators that transmit alerts in good faith. *Note (written for Cameroon):* Protects operators but does not say who compensates victims; Cameroon would need to decide both.
    - *European Union*: [Regulation (EU) 2024/1689 (AI Act), Articles 26 and 73](https://eur-lex.europa.eu/eli/reg/2024/1689/oj). Sets obligations for AI providers and deployers, including monitoring and serious-incident reporting, which help establish who failed. *Note (written for Cameroon):* Liability for damages itself is left to other EU and national rules.

### G8-06 · AI unchecked: Report that sensors feeding the AI are down and the forecast is unreliable

- **Type:** G8 AI unchecked · **Severity:** 3 (risk to life or rights) · **Status:** confirmed by text
- **When:** event(s) 8, first at D11 04:00
- **What is missing:** No institution holds the power or duty to report that sensors feeding the AI are down and the forecast is unreliable
- **Institutions concerned:** HYDRO, MET
- **Texts checked:** AE-S01, AE-S03, AE-S04
- **Evidence:** Who-does-what map (AE): no institution holds 'report_sensor_outage'; drill:MET@8
- **How others handle it:**
    - *European Union*: [Regulation (EU) 2024/1689 (AI Act), Articles 12 and 13](https://eur-lex.europa.eu/eli/reg/2024/1689/oj). Automatic logging and instructions describing accuracy, limits and the conditions under which the system works as intended. *Note (written for Cameroon):* A purchase contract can require the vendor to show data-quality warnings on the dashboard.
    - *United States*: [NIST AI Risk Management Framework 1.0](https://www.nist.gov/itl/ai-risk-management-framework). Measure and monitor AI systems in operation, including data quality. *Note (written for Cameroon):* Voluntary method.

### G2-07 · Two in charge: Act on a local, informal warning that contradicts the AI

- **Type:** G2 Two in charge · **Severity:** 3 (risk to life or rights) · **Status:** suspected (needs expert check)
- **When:** event(s) 9, first at D11 09:00
- **What is missing:** Several institutions hold 'act on a local, informal warning that contradicts the AI' and no text says who leads
- **Institutions concerned:** CTD, DPC
- **Texts checked:** AE-S02, AE-S03, AE-S04
- **Evidence:** AE-L13: CTD power (assumed); AE-L17: DPC power (inferred)
- **How others handle it:**
    - *International*: [Early Warnings for All](https://wmo.int/resources/wmo-bulletin/wmo-bulletin-vol-72-1-2023/overview-of-early-warnings-all-executive-action-plan-2023-2027). People-centred warning systems include community observations and feedback. *Note (written for Cameroon):* Formalise a channel from village chiefs to the crisis committee.
    - *Mauritius*: [Common Alerting Protocol adoption (2023)](https://www.preventionweb.net/quick/96844). Clear roles: the weather service issues, the disaster centre coordinates, the ICT authority disseminates, with one common alert format. *Note (written for Cameroon):* Naming one lead per step avoids two bodies claiming the same decision.
    - *United States*: [47 CFR Part 10 (Wireless Emergency Alerts)](https://www.ecfr.gov/current/title-47/chapter-I/subchapter-A/part-10). Separates who originates alerts (authorised authorities), the national gateway, and the operators who transmit them. *Note (written for Cameroon):* A list of authorised originators per hazard settles who may decide.

### G3-08 · No procedure: Act on a local, informal warning that contradicts the AI

- **Type:** G3 No procedure · **Severity:** 3 (risk to life or rights) · **Status:** suspected (needs expert check)
- **When:** event(s) 9, first at D11 09:00
- **What is missing:** No procedure, deadline or form for: act on a local, informal warning that contradicts the AI
- **Institutions concerned:** CTD, DPC
- **Texts checked:** AE-S02, AE-S03, AE-S04
- **Evidence:** AE-L13: CTD power, procedure: none found (assumed); AE-L17: DPC power, procedure: none found (inferred)
- **How others handle it:**
    - *International*: [Early Warnings for All](https://wmo.int/resources/wmo-bulletin/wmo-bulletin-vol-72-1-2023/overview-of-early-warnings-all-executive-action-plan-2023-2027). People-centred warning systems include community observations and feedback. *Note (written for Cameroon):* Formalise a channel from village chiefs to the crisis committee.
    - *European Union*: [Regulation (EU) 2024/1689 (AI Act), Articles 14 and 26](https://eur-lex.europa.eu/eli/reg/2024/1689/oj). High-risk AI must allow effective human oversight, and deployers must assign competent people to oversee it. *Note (written for Cameroon):* A named person validating an AI-drafted alert before release can be required without adopting the whole Act.
    - *United States*: [FCC findings on the Hawaii false missile alert (2018)](https://www.fcc.gov/node/215906). Recommended second-person verification before any live alert is released and pre-scripted correction procedures. *Note (written for Cameroon):* A simple procedure rule, cheap to adopt.

### G7-09 · People left out: Send alerts in the languages people understand

- **Type:** G7 People left out · **Severity:** 3 (risk to life or rights) · **Status:** suspected (needs expert check)
- **When:** event(s) 10, first at D11 11:30
- **What is missing:** No procedure, deadline or form for: send alerts in the languages people understand
- **Institutions concerned:** ART
- **Texts checked:** AE-S02, AE-S03
- **Evidence:** AE-L16: ART duty, procedure: none found (inferred)
- **How others handle it:**
    - *International*: [Recommendation ITU-T X.1303 (CAP 1.2)](https://www.itu.int/rec/T-REC-X.1303). One alert can carry several info blocks, each in a different language. *Note (written for Cameroon):* Pre-translated templates for local languages.
    - *Mauritius*: [Common Alerting Protocol adoption (2023)](https://www.preventionweb.net/quick/96844). Alerts reach people through many channels, including radio and sirens. *Note (written for Cameroon):* An African example.
    - *Japan*: [J-Alert, National Instantaneous Warning System](https://www.city.inagi.tokyo.jp/en/kurashi/iza/1002270/1010142/1012096.html). Triggers municipal radio and outdoor loudspeakers automatically, reaching people without phones. *Note (written for Cameroon):* Loudspeakers and radio reach people phones miss.

### G7-10 · People left out: Reach people without phones or network coverage

- **Type:** G7 People left out · **Severity:** 3 (risk to life or rights) · **Status:** confirmed by text
- **When:** event(s) 10, first at D11 11:30
- **What is missing:** No institution holds the power or duty to reach people without phones or network coverage
- **Institutions concerned:** ART, DPC, OPS
- **Texts checked:** AE-S02
- **Evidence:** Who-does-what map (AE): no institution holds 'reach_unconnected'
- **How others handle it:**
    - *Japan*: [J-Alert, National Instantaneous Warning System](https://www.city.inagi.tokyo.jp/en/kurashi/iza/1002270/1010142/1012096.html). Automatically triggers municipal radio and outdoor loudspeakers, reaching people without phones. *Note (written for Cameroon):* Community radio and loudspeakers exist in many Cameroonian towns.
    - *International*: [Early Warnings for All (ITU pillar)](https://wmo.int/resources/wmo-bulletin/wmo-bulletin-vol-72-1-2023/overview-of-early-warnings-all-executive-action-plan-2023-2027). Uses AI and satellite imagery to map unconnected populations, and promotes multi-channel alerting. *Note (written for Cameroon):* ITU support is available to Cameroon.
    - *Mauritius*: [Common Alerting Protocol adoption (2023)](https://www.preventionweb.net/quick/96844). Alerts reach people through many channels, including radio and sirens. *Note (written for Cameroon):* Channels that do not need a smartphone widen reach.

### G2-11 · Two in charge: Coordinate the multi-sector response

- **Type:** G2 Two in charge · **Severity:** 3 (risk to life or rights) · **Status:** suspected (needs expert check)
- **When:** event(s) 11, first at D11 18:00
- **What is missing:** Several institutions hold 'coordinate the multi-sector response' and no text says who leads
- **Institutions concerned:** DPC, MOI
- **Texts checked:** AE-S02, AE-S04
- **Evidence:** AE-L01: DPC power (inferred); AE-L15: MOI power (inferred)
- **How others handle it:**
    - *Mauritius*: [Common Alerting Protocol adoption (2023)](https://www.preventionweb.net/quick/96844). Clear roles: the weather service issues, the disaster centre coordinates, the ICT authority disseminates, with one common alert format. *Note (written for Cameroon):* Naming one lead per step avoids two bodies claiming the same decision.
    - *United States*: [47 CFR Part 10 (Wireless Emergency Alerts)](https://www.ecfr.gov/current/title-47/chapter-I/subchapter-A/part-10). Separates who originates alerts (authorised authorities), the national gateway, and the operators who transmit them. *Note (written for Cameroon):* A list of authorised originators per hazard settles who may decide.
    - *Japan*: [J-Alert, National Instantaneous Warning System](https://www.city.inagi.tokyo.jp/en/kurashi/iza/1002270/1010142/1012096.html). The national government pushes urgent warnings automatically to all local channels. *Note (written for Cameroon):* Useful for fast-onset hazards where local decisions would add delay.

### G3-12 · No procedure: Activate the emergency and rescue plan

- **Type:** G3 No procedure · **Severity:** 3 (risk to life or rights) · **Status:** suspected (needs expert check)
- **When:** event(s) 11, first at D11 18:00
- **What is missing:** No procedure, deadline or form for: activate the emergency and rescue plan
- **Institutions concerned:** DPC
- **Texts checked:** AE-S02
- **Evidence:** AE-L06: DPC power, procedure: none found (inferred)
- **How others handle it:**
    - *European Union*: [Regulation (EU) 2024/1689 (AI Act), Articles 14 and 26](https://eur-lex.europa.eu/eli/reg/2024/1689/oj). High-risk AI must allow effective human oversight, and deployers must assign competent people to oversee it. *Note (written for Cameroon):* A named person validating an AI-drafted alert before release can be required without adopting the whole Act.
    - *United States*: [FCC findings on the Hawaii false missile alert (2018)](https://www.fcc.gov/node/215906). Recommended second-person verification before any live alert is released and pre-scripted correction procedures. *Note (written for Cameroon):* A simple procedure rule, cheap to adopt.
    - *Mauritius*: [Common Alerting Protocol adoption (2023)](https://www.preventionweb.net/quick/96844). Written roles between the weather service, disaster agency and regulator, and one message format. *Note (written for Cameroon):* Writing the procedure down is the first step.

### G3-13 · No procedure: Order the evacuation of a danger zone

- **Type:** G3 No procedure · **Severity:** 3 (risk to life or rights) · **Status:** suspected (needs expert check)
- **When:** event(s) 11, first at D11 18:00
- **What is missing:** No procedure, deadline or form for: order the evacuation of a danger zone
- **Institutions concerned:** DPC
- **Texts checked:** AE-S01
- **Evidence:** AE-L07: DPC power, procedure: none found (inferred)
- **How others handle it:**
    - *Japan*: [J-Alert](https://www.city.inagi.tokyo.jp/en/kurashi/iza/1002270/1010142/1012096.html). Pre-defined local channels carry evacuation instructions. *Note (written for Cameroon):* Pre-defined evacuation areas speed decisions.
    - *European Union*: [Regulation (EU) 2024/1689 (AI Act), Articles 14 and 26](https://eur-lex.europa.eu/eli/reg/2024/1689/oj). High-risk AI must allow effective human oversight, and deployers must assign competent people to oversee it. *Note (written for Cameroon):* A named person validating an AI-drafted alert before release can be required without adopting the whole Act.
    - *United States*: [FCC findings on the Hawaii false missile alert (2018)](https://www.fcc.gov/node/215906). Recommended second-person verification before any live alert is released and pre-scripted correction procedures. *Note (written for Cameroon):* A simple procedure rule, cheap to adopt.

### G8-14 · AI unchecked: Authorise automatic release of AI-drafted alerts without human validation

- **Type:** G8 AI unchecked · **Severity:** 3 (risk to life or rights) · **Status:** confirmed by text
- **When:** event(s) 12, first at D11 20:00
- **What is missing:** No institution holds the power or duty to authorise automatic release of AI-drafted alerts without human validation
- **Institutions concerned:** DPC, OPS
- **Texts checked:** AE-S01, AE-S02, AE-S03
- **Evidence:** Who-does-what map (AE): no institution holds 'authorise_automatic_ai_alert'; drill:DPC@12; drill:OPS@12
- **How others handle it:**
    - *European Union*: [Regulation (EU) 2024/1689 (AI Act), Articles 14 and 26](https://eur-lex.europa.eu/eli/reg/2024/1689/oj). High-risk AI must allow effective human oversight and guard against over-reliance; deployers assign competent people to oversee it. *Note (written for Cameroon):* Automatic release without a human step would need an explicit legal basis and safeguards.
    - *United States*: [FCC findings on the Hawaii false missile alert (2018)](https://www.fcc.gov/node/215906). Recommended second-person verification before any live alert is released. *Note (written for Cameroon):* Speed gained by removing the check is the risk the Hawaii case illustrates.

### G3-15 · No procedure: Issue an official weather or flood warning

- **Type:** G3 No procedure · **Severity:** 2 (delay or extra cost) · **Status:** confirmed by text
- **When:** event(s) 1, first at D1 06:00
- **What is missing:** No procedure, deadline or form for: issue an official weather or flood warning
- **Institutions concerned:** MET
- **Texts checked:** AE-S01, AE-S02, AE-S06
- **Evidence:** AE-L05: MET duty, procedure: none found (documented)
- **How others handle it:**
    - *Mauritius*: [Common Alerting Protocol adoption (2023)](https://www.preventionweb.net/quick/96844). Clear roles: the meteorological service issues, the disaster centre coordinates, the ICT authority disseminates. *Note (written for Cameroon):* An African example.
    - *Philippines*: [Republic Act No. 10639, Section 4](https://issuances-library.senate.gov.ph/sites/default/files/2023-02/ra%252010639.pdf). Names the agencies whose information makes up the alerts. *Note (written for Cameroon):* Naming one lead per hazard avoids overlaps.
    - *European Union*: [Regulation (EU) 2024/1689 (AI Act), Articles 14 and 26](https://eur-lex.europa.eu/eli/reg/2024/1689/oj). High-risk AI must allow effective human oversight, and deployers must assign competent people to oversee it. *Note (written for Cameroon):* A named person validating an AI-drafted alert before release can be required without adopting the whole Act.

### G1-16 · Nobody in charge: Correct or cancel a false alert

- **Type:** G1 Nobody in charge · **Severity:** 2 (delay or extra cost) · **Status:** confirmed by text
- **When:** event(s) 6, first at D1 12:00
- **What is missing:** No institution holds the power or duty to correct or cancel a false alert
- **Institutions concerned:** ART, DPC, MET, OPS
- **Texts checked:** AE-S02, AE-S03
- **Evidence:** Who-does-what map (AE): no institution holds 'correct_false_alert'; drill:MET@6; drill:DPC@6; drill:OPS@6; drill:ART@6
- **How others handle it:**
    - *United States*: [FCC findings on the Hawaii false missile alert (2018)](https://www.fcc.gov/node/215906). No correction procedure existed; 38 minutes passed before a correction reached phones. Pre-scripted correction messages were recommended. *Note (written for Cameroon):* Cameroon can prepare correction templates before any AI alert goes live.
    - *International*: [Recommendation ITU-T X.1303 (CAP 1.2)](https://www.itu.int/rec/T-REC-X.1303). Update and cancel message types let a wrong alert be corrected or withdrawn in a standard way. *Note (written for Cameroon):* Free to adopt.
    - *European Union*: [Directive (EU) 2018/1972 (European Electronic Communications Code), Article 110](https://eur-lex.europa.eu/eli/dir/2018/1972/oj). Mobile operators must relay public warnings from the national public warning system to the end-users concerned. *Note (written for Cameroon):* A decree or regulator decision could create the same duty and name the authority that originates the warning.

### G1-17 · Nobody in charge: Explain publicly what went wrong after an error

- **Type:** G1 Nobody in charge · **Severity:** 2 (delay or extra cost) · **Status:** confirmed by text
- **When:** event(s) 6, first at D1 12:00
- **What is missing:** No institution holds the power or duty to explain publicly what went wrong after an error
- **Institutions concerned:** ART, DPC, MET, OPS
- **Texts checked:** AE-S02, AE-S03
- **Evidence:** Who-does-what map (AE): no institution holds 'public_communication_after_error'
- **How others handle it:**
    - *United States*: [FCC findings on the Hawaii false missile alert (2018)](https://www.fcc.gov/node/215906). Social media corrected the alert faster than the official system, showing the need for a planned public explanation. *Note (written for Cameroon):* Name a spokesperson in the plan.
    - *European Union*: [Directive (EU) 2018/1972 (European Electronic Communications Code), Article 110](https://eur-lex.europa.eu/eli/dir/2018/1972/oj). Mobile operators must relay public warnings from the national public warning system to the end-users concerned. *Note (written for Cameroon):* A decree or regulator decision could create the same duty and name the authority that originates the warning.
    - *Philippines*: [Republic Act No. 10639, Free Mobile Disaster Alerts Act (2014), Sections 4 and 6](https://issuances-library.senate.gov.ph/sites/default/files/2023-02/ra%252010639.pdf). Operators must send free alerts with content from named agencies; fines and franchise suspension for non-compliance. *Note (written for Cameroon):* Requires naming content providers and setting penalties.

### G9-18 · Channel unprotected: Stop fake alerts that imitate the official channel

- **Type:** G9 Channel unprotected · **Severity:** 2 (delay or extra cost) · **Status:** suspected (needs expert check)
- **When:** event(s) 7, first at D1 15:00
- **What is missing:** No procedure, deadline or form for: stop fake alerts that imitate the official channel
- **Institutions concerned:** ANTIC
- **Texts checked:** AE-S01, AE-S02
- **Evidence:** AE-L11: ANTIC power, procedure: none found (assumed); drill:ANTIC@7
- **How others handle it:**
    - *United States*: [47 CFR Part 10 (Wireless Emergency Alerts)](https://www.ecfr.gov/current/title-47/chapter-I/subchapter-A/part-10). Only authorised alerting authorities can originate alerts through a single national gateway, which limits imitation. *Note (written for Cameroon):* Cameroon could designate one authenticated originator and a short code for official alerts.
    - *International*: [Recommendation ITU-T X.1303 (CAP 1.2)](https://www.itu.int/rec/T-REC-X.1303). Alerts carry an identified sender and can be digitally signed. *Note (written for Cameroon):* Free to adopt.

## Decision timeline

| Story time | Seat | Decision | Legal basis | Quote check | Confidence | By |
| --- | --- | --- | --- | --- | --- | --- |
| D1 06:00 | MET | Act: Issue an official weather or flood warning (no written procedure found; acting on general powers) | AE-S05 Authority statement | ok | medium | rules |
| D1 06:20 | MET | No legal basis found to check and validate an AI-generated forecast before it is used for a public decision. Flagging a gap. | NO LEGAL BASIS FOUND | - | low | rules |
| D1 06:20 | HYDRO | Output produced. HydroSense informs; it does not decide. Validity limits are in its model card. | - | - | medium | scripted |
| D1 06:45 | DPC | Act: Decide to alert the public | AE-S02 How a public alert reaches phones in the UAE: summary / National framework | ok | medium | rules |
| D1 07:10 | OPS | Act: Technically send the alert to phones (SMS or cell broadcast) | AE-S02 Technology and standards | ok | medium | rules |
| D1 08:30 | DPC | No legal basis found to answer for harm caused by a wrong alert. Flagging a gap. | NO LEGAL BASIS FOUND | - | low | rules |
| D1 08:30 | ART | No legal basis found to answer for harm caused by a wrong alert. Flagging a gap. | NO LEGAL BASIS FOUND | - | low | rules |
| D1 12:00 | MET | No legal basis found to correct or cancel a false alert. Flagging a gap. | NO LEGAL BASIS FOUND | - | low | rules |
| D1 12:00 | DPC | No legal basis found to correct or cancel a false alert. Flagging a gap. | NO LEGAL BASIS FOUND | - | low | rules |
| D1 12:00 | OPS | No legal basis found to correct or cancel a false alert. Flagging a gap. | NO LEGAL BASIS FOUND | - | low | rules |
| D1 12:00 | ART | No legal basis found to correct or cancel a false alert. Flagging a gap. | NO LEGAL BASIS FOUND | - | low | rules |
| D1 15:00 | ANTIC | Act: Stop fake alerts that imitate the official channel (no written procedure found; acting on general powers) | NO LEGAL BASIS FOUND | - | low | rules |
| D1 15:00 | ART | Ask ANTIC to stop fake alerts that imitate the official channel | - | - | low | rules |
| D1 15:00 | ANTIC | Accepted: we will stop fake alerts that imitate the official channel. | - | - | medium | rules |
| D11 04:00 | MET | No legal basis found to report that sensors feeding the AI are down and the forecast is unreliable. Flagging a gap. | NO LEGAL BASIS FOUND | - | low | rules |
| D11 04:00 | HYDRO | Output produced. HydroSense informs; it does not decide. Validity limits are in its model card. | - | - | medium | scripted |
| D11 09:00 | DPC | Act: Act on a local, informal warning that contradicts the AI (no written procedure found; acting on general powers) | AE-S02 How a public alert reaches phones in the UAE: summary / National framework | ok | medium | rules |
| D11 09:00 | MET | Ask DPC to act on a local, informal warning that contradicts the AI | - | - | low | rules |
| D11 11:30 | DPC | Ask ART to send alerts in the languages people understand | - | - | low | rules |
| D11 11:30 | OPS | Ask ART to send alerts in the languages people understand | - | - | low | rules |
| D11 11:30 | ART | Act: Send alerts in the languages people understand (no written procedure found; acting on general powers) | AE-S02 Weather warnings | ok | medium | rules |
| D11 18:00 | MET | Ask DPC to coordinate the multi-sector response | - | - | low | rules |
| D11 18:00 | DPC | Act: Coordinate the multi-sector response | AE-S02 How a public alert reaches phones in the UAE: summary / National framework | ok | medium | rules |
| D11 18:00 | DPC | Act: Activate the emergency and rescue plan (no written procedure found; acting on general powers) | AE-S02 How a public alert reaches phones in the UAE: summary / National framework | ok | medium | rules |
| D11 18:00 | DPC | Act: Order the evacuation of a danger zone (no written procedure found; acting on general powers) | AE-S02 How a public alert reaches phones in the UAE: summary / National framework | ok | medium | rules |
| D11 18:00 | OPS | Ask DPC to coordinate the multi-sector response | - | - | low | rules |
| D11 18:00 | ART | Ask DPC to coordinate the multi-sector response | - | - | low | rules |
| D11 20:00 | DPC | No legal basis found to authorise automatic release of AI-drafted alerts without human validation. Flagging a gap. | NO LEGAL BASIS FOUND | - | low | rules |
| D11 20:00 | OPS | No legal basis found to authorise automatic release of AI-drafted alerts without human validation. Flagging a gap. | NO LEGAL BASIS FOUND | - | low | rules |

## Readiness scorecard (ITU AI Readiness Framework, 13 dimensions)

Scores describe what this drill revealed (5 = no gap found, 0 = many serious gaps); they are not an official rating.

| # | Dimension | Score | Evidence |
| --- | --- | --- | --- |
| 1 | Data/Model Marketplace | not assessed | not assessed by this story |
| 2 | Generated Content Marketplace | 0.7 / 5 | G8-01 AI unchecked: Check and validate an AI-generated forecast before it is used for a public decision; G8-06 AI unchecked: Report that sensors feeding the AI are down and the forecast is unreliable; G8-14 AI unchecked: Authorise automatic release of AI-drafted alerts without human validation |
| 3 | Cross-Domain Correlation Analysis | 2.8 / 5 | G2-02 Two in charge: Decide to alert the public; G2-07 Two in charge: Act on a local, informal warning that contradicts the AI; G2-11 Two in charge: Coordinate the multi-sector response |
| 4 | Contextualization and Regional Impact | 3.0 / 5 | G7-09 People left out: Send alerts in the languages people understand; G7-10 People left out: Reach people without phones or network coverage |
| 5 | Level of Integration of AI in Workflows | 0.0 / 5 | G8-01 AI unchecked: Check and validate an AI-generated forecast before it is used for a public decision; G3-03 No procedure: Approve an AI-drafted alert through a human validation step before release; G8-06 AI unchecked: Report that sensors feeding the AI are down and the forecast is unreliable |
| 6 | Human Interface | 3.0 / 5 | G7-09 People left out: Send alerts in the languages people understand; G7-10 People left out: Reach people without phones or network coverage |
| 7 | Strategy Alignment | 0.0 / 5 | G2-02 Two in charge: Decide to alert the public; G3-03 No procedure: Approve an AI-drafted alert through a human validation step before release; G1-04 Nobody in charge: Order mobile operators to relay a public alert |
| 8 | Collaboration with AI | 1.2 / 5 | G8-01 AI unchecked: Check and validate an AI-generated forecast before it is used for a public decision; G8-06 AI unchecked: Report that sensors feeding the AI are down and the forecast is unreliable; G8-14 AI unchecked: Authorise automatic release of AI-drafted alerts without human validation |
| 9 | Impacts of Humans in AI Integration | 1.2 / 5 | G8-01 AI unchecked: Check and validate an AI-generated forecast before it is used for a public decision; G8-06 AI unchecked: Report that sensors feeding the AI are down and the forecast is unreliable; G8-14 AI unchecked: Authorise automatic release of AI-drafted alerts without human validation |
| 10 | AI & Policies | 0.5 / 5 | G1-04 Nobody in charge: Order mobile operators to relay a public alert; G6-05 Nobody answers for harm: Answer for harm caused by a wrong alert; G1-16 Nobody in charge: Correct or cancel a false alert |
| 11 | AI for Inclusion | 3.0 / 5 | G7-09 People left out: Send alerts in the languages people understand; G7-10 People left out: Reach people without phones or network coverage |
| 12 | Granular Priorities | not assessed | not assessed by this story |
| 13 | Digital Infrastructure | 4.4 / 5 | G9-18 Channel unprotected: Stop fake alerts that imitate the official channel |

## Assumptions and sources to confirm

Lines of the who-does-what map that are not directly documented:

- `AE-L01` DPC power *coordinate_response*: NCEMA coordinates national emergency management; press and summaries differ on how it shares this role with other authorities [inferred]
- `AE-L02` DPC power *decide_public_alert*: NCEMA coordinates public warnings through the national alert framework (summaries; the text that authorises each alert is not yet found) [inferred]
- `AE-L03` ART power *set_alert_standard*: TDRA sets the technical specifications under which operators and handsets deliver UAE-Alert cell broadcast messages; no text found that lets TDRA or anyone oblige operators to relay an alert [inferred]
- `AE-L04` OPS duty *send_mass_alert*: Operators transmit cell broadcast alerts to compatible devices in the targeted cells [inferred]
- `AE-L06` DPC power *activate_contingency_plan*: NCEMA coordinates emergency plans nationally [inferred]
- `AE-L07` DPC power *evacuate_zone*: Emergency instructions to the public are coordinated through the national framework [inferred]
- `AE-L09` MINSANTE power *access_location_data*: The PDPL lists cases where processing without consent is allowed, including public health cases [inferred]
- `AE-L11` ANTIC power *block_spoofed_alert*: The UAE Cybersecurity Council handles national cybersecurity incidents [assumed (assumed by ALERTE team, 2026-10-07: official mandate text to obtain)]
- `AE-L12` MINSANTE duty *cholera_response*: The State must detect, assess, notify and report outbreaks (International Health Regulations) [inferred]
- `AE-L13` CTD power *act_on_local_warning*: Dubai Municipality manages local drainage and public works response [assumed (assumed by ALERTE team, 2026-10-07: to verify)]
- `AE-L14` MOI power *decide_public_alert*: Press descriptions name the Ministry of Interior as supervising or issuing public alerts; sources give different launch years and roles [inferred]
- `AE-L15` MOI power *coordinate_response*: Civil defence has historically sat under the Ministry of Interior; the 2025 reorganisation moved parts to the Civil Defence Authority inside NCEMA (to verify) [inferred]
- `AE-L16` ART duty *multilingual_alerting*: TDRA handset specification TS040 requires English and Arabic (per summary); no duty found for other languages or channels [inferred]
- `AE-L17` DPC power *act_on_local_warning*: NCEMA coordinates emergency plans nationally and can act on local reports [inferred]

National documents used as summaries (official text still to obtain or confirm): AE-S01, AE-S02, AE-S03, AE-S04, AE-S05, AE-S06

## Logbook

Every step of this drill is in `ledger.jsonl`, chained by SHA-256 fingerprints. Check it with `python -m alerte verify ae-core-offline-20261110-101333-293d`.


*Fictional exercise. Not a real alert. HydroSense and all numbers in the events are invented; places and institutions are real.*
