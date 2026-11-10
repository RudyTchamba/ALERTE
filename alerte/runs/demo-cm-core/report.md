# ALERTE report: Rising Waters, Cameroon (core drill)

> **Fictional exercise. Not a real alert. HydroSense and all numbers in the events are invented; places and institutions are real.**

Run `cm-core-offline-20261110-101334-eb08` · country CM · brain: offline · 12 events · 28 decisions · 17 gaps (11 confirmed by text) · 0.07 s

## Summary

- Gaps by type: G1 Nobody in charge (3), G2 Two in charge (1), G3 No procedure (6), G6 Nobody answers for harm (1), G7 People left out (2), G8 AI unchecked (3), G9 Channel unprotected (1)
- Planned gaps found (test T3): 12 of 13 (92%); missed: event 11: G2
- Quotes verified (test T2): 6 of 6 (100%)
- Decisions with no legal basis found: 16
- Who wrote the decisions: rule engine (no AI) 26, scripted (HydroSense) 2

## Gap report

### G8-01 · AI unchecked: Check and validate an AI-generated forecast before it is used for a public decision

- **Type:** G8 AI unchecked · **Severity:** 3 (risk to life or rights) · **Status:** confirmed by text
- **When:** event(s) 2, 8, first at D1 06:20
- **What is missing:** No institution holds the power or duty to check and validate an AI-generated forecast before it is used for a public decision
- **Institutions concerned:** HYDRO, MET
- **Texts checked:** CM-S03, CM-S04, CM-S05
- **Evidence:** Who-does-what map (CM): no institution holds 'validate_ai_forecast'; drill:MET@2
- **How others handle it:**
    - *European Union*: [Regulation (EU) 2024/1689 (AI Act), Articles 14 and 26](https://eur-lex.europa.eu/eli/reg/2024/1689/oj). High-risk AI must allow effective human oversight, guard against over-reliance, and deployers must assign competent people to oversee it. *Fit for Cameroon:* Cameroon could require a named forecaster to validate AI forecasts before public use, without adopting the whole AI Act.
    - *United States*: [FCC findings on the Hawaii false missile alert (2018)](https://www.fcc.gov/node/215906). Recommended second-person verification before any live alert is released. *Fit for Cameroon:* A simple procedure rule, cheap to adopt.

### G3-02 · No procedure: Decide to alert the public

- **Type:** G3 No procedure · **Severity:** 3 (risk to life or rights) · **Status:** confirmed by text
- **When:** event(s) 3, first at D1 06:45
- **What is missing:** No procedure, deadline or form for: decide to alert the public
- **Institutions concerned:** DPC
- **Texts checked:** CM-S01, CM-S03, CM-S04
- **Evidence:** CM-L03: DPC duty, procedure: none found (documented)
- **How others handle it:**
    - *Japan*: [J-Alert](https://www.city.inagi.tokyo.jp/en/kurashi/iza/1002270/1010142/1012096.html). For some hazards the national government pushes alerts automatically, removing delays in local decisions. *Fit for Cameroon:* Useful for fast-onset hazards.
    - *United States*: [47 CFR Part 10 (Wireless Emergency Alerts)](https://www.ecfr.gov/current/title-47/chapter-I/subchapter-A/part-10). Only authorised alerting authorities may originate alerts. *Fit for Cameroon:* Cameroon could name the authorised originators per hazard.
    - *European Union*: [Regulation (EU) 2024/1689 (AI Act), Articles 14 and 26](https://eur-lex.europa.eu/eli/reg/2024/1689/oj). High-risk AI must allow effective human oversight, and deployers must assign competent people to oversee it. *Fit for Cameroon:* A named person validating an AI-drafted alert before release can be required without adopting the whole Act.

### G3-03 · No procedure: Approve an AI-drafted alert through a human validation step before release

- **Type:** G3 No procedure · **Severity:** 3 (risk to life or rights) · **Status:** confirmed by text
- **When:** event(s) 3, 12, first at D1 06:45
- **What is missing:** No institution holds the power or duty to approve an AI-drafted alert through a human validation step before release
- **Institutions concerned:** DPC, OPS
- **Texts checked:** CM-S01, CM-S04, CM-S05
- **Evidence:** Who-does-what map (CM): no institution holds 'human_validate_ai_alert'
- **How others handle it:**
    - *European Union*: [Regulation (EU) 2024/1689 (AI Act), Articles 14 and 26](https://eur-lex.europa.eu/eli/reg/2024/1689/oj). High-risk AI must allow effective human oversight, and deployers must assign competent people to oversee it. *Fit for Cameroon:* A named person validating an AI-drafted alert before release can be required without adopting the whole Act.
    - *United States*: [FCC findings on the Hawaii false missile alert (2018)](https://www.fcc.gov/node/215906). Recommended second-person verification before any live alert is released and pre-scripted correction procedures. *Fit for Cameroon:* A simple procedure rule, cheap to adopt.
    - *Mauritius*: [Common Alerting Protocol adoption (2023)](https://www.preventionweb.net/quick/96844). Written roles between the weather service, disaster agency and regulator, and one message format. *Fit for Cameroon:* Writing the procedure down is the first step.

### G1-04 · Nobody in charge: Order mobile operators to relay a public alert

- **Type:** G1 Nobody in charge · **Severity:** 3 (risk to life or rights) · **Status:** confirmed by text
- **When:** event(s) 4, first at D1 07:10
- **What is missing:** No institution holds the power or duty to order mobile operators to relay a public alert
- **Institutions concerned:** OPS
- **Texts checked:** CM-S01, CM-S03
- **Evidence:** Who-does-what map (CM): no institution holds 'compel_operator_alert'
- **How others handle it:**
    - *European Union*: [Directive (EU) 2018/1972 (European Electronic Communications Code), Article 110](https://eur-lex.europa.eu/eli/dir/2018/1972/oj). Mobile operators must relay public warnings from the national public warning system to the end-users concerned. *Fit for Cameroon:* A decree or ART decision could create the same duty; Cameroon would need to name the authority that originates the warning.
    - *Philippines*: [Republic Act No. 10639, Free Mobile Disaster Alerts Act (2014), Sections 4 and 6](https://issuances-library.senate.gov.ph/sites/default/files/2023-02/ra%252010639.pdf). Operators must send free alerts with content from named agencies; fines and franchise suspension for non-compliance. *Fit for Cameroon:* Close to Cameroon's situation (a developing country with frequent hazards); requires naming content providers and setting penalties.
    - *United States*: [47 CFR Part 10 (Wireless Emergency Alerts) and WARN Act, Part 10](https://www.ecfr.gov/current/title-47/chapter-I/subchapter-A/part-10). Separates who originates alerts (authorised authorities), the national gateway, and the operators who transmit them. *Fit for Cameroon:* Participation is voluntary in the US; a mandatory duty (EU, Philippines) may suit Cameroon better.

### G3-05 · No procedure: Technically send the alert to phones (SMS or cell broadcast)

- **Type:** G3 No procedure · **Severity:** 3 (risk to life or rights) · **Status:** suspected (needs expert check)
- **When:** event(s) 4, first at D1 07:10
- **What is missing:** No procedure, deadline or form for: technically send the alert to phones (SMS or cell broadcast)
- **Institutions concerned:** OPS
- **Texts checked:** CM-S01, CM-S03, CM-S04
- **Evidence:** CM-L09: OPS power, procedure: none found (inferred)
- **How others handle it:**
    - *Mauritius*: [Common Alerting Protocol adoption (2023)](https://www.preventionweb.net/quick/96844). One alert created once and shared across TV, radio, SMS, apps, sirens and social media by three coordinated agencies. *Fit for Cameroon:* An African example; requires an agreed alert format and roles between the weather service, disaster agency and regulator.
    - *International*: [Recommendation ITU-T X.1303 (CAP 1.2)](https://www.itu.int/rec/T-REC-X.1303). Standard format for alerts, with status, urgency, severity, area, several languages, and update or cancel messages. *Fit for Cameroon:* Free to adopt; supported by ITU under Early Warnings for All.
    - *European Union*: [Regulation (EU) 2024/1689 (AI Act), Articles 14 and 26](https://eur-lex.europa.eu/eli/reg/2024/1689/oj). High-risk AI must allow effective human oversight, and deployers must assign competent people to oversee it. *Fit for Cameroon:* A named person validating an AI-drafted alert before release can be required without adopting the whole Act.

### G6-06 · Nobody answers for harm: Answer for harm caused by a wrong alert

- **Type:** G6 Nobody answers for harm · **Severity:** 3 (risk to life or rights) · **Status:** confirmed by text
- **When:** event(s) 5, first at D1 08:30
- **What is missing:** No institution holds the power or duty to answer for harm caused by a wrong alert
- **Institutions concerned:** ART, DPC
- **Texts checked:** CM-S01, CM-S04, CM-S05, CM-S06
- **Evidence:** Who-does-what map (CM): no institution holds 'liability_alert_harm'; drill:DPC@5; drill:ART@5
- **How others handle it:**
    - *United States*: [WARN Act (2006)](https://www.ecfr.gov/current/title-47/chapter-I/subchapter-A/part-10). Limits the liability of operators that transmit alerts in good faith. *Fit for Cameroon:* Protects operators but does not say who compensates victims; Cameroon would need to decide both.
    - *European Union*: [Regulation (EU) 2024/1689 (AI Act), Articles 26 and 73](https://eur-lex.europa.eu/eli/reg/2024/1689/oj). Sets obligations for AI providers and deployers, including monitoring and serious-incident reporting, which help establish who failed. *Fit for Cameroon:* Liability for damages itself is left to other EU and national rules.

### G8-07 · AI unchecked: Report that sensors feeding the AI are down and the forecast is unreliable

- **Type:** G8 AI unchecked · **Severity:** 3 (risk to life or rights) · **Status:** confirmed by text
- **When:** event(s) 8, first at D11 04:00
- **What is missing:** No institution holds the power or duty to report that sensors feeding the AI are down and the forecast is unreliable
- **Institutions concerned:** HYDRO, MET
- **Texts checked:** CM-S01, CM-S02, CM-S05, CM-S06
- **Evidence:** Who-does-what map (CM): no institution holds 'report_sensor_outage'; drill:MET@8
- **How others handle it:**
    - *European Union*: [Regulation (EU) 2024/1689 (AI Act), Articles 12 and 13](https://eur-lex.europa.eu/eli/reg/2024/1689/oj). Automatic logging and instructions describing accuracy, limits and the conditions under which the system works as intended. *Fit for Cameroon:* A purchase contract can require the vendor to show data-quality warnings on the dashboard.
    - *United States*: [NIST AI Risk Management Framework 1.0](https://www.nist.gov/itl/ai-risk-management-framework). Measure and monitor AI systems in operation, including data quality. *Fit for Cameroon:* Voluntary method.

### G3-08 · No procedure: Act on a local, informal warning that contradicts the AI

- **Type:** G3 No procedure · **Severity:** 3 (risk to life or rights) · **Status:** suspected (needs expert check)
- **When:** event(s) 9, first at D11 09:00
- **What is missing:** No procedure, deadline or form for: act on a local, informal warning that contradicts the AI
- **Institutions concerned:** CTD
- **Texts checked:** CM-S01, CM-S03, CM-S05, CM-S06
- **Evidence:** CM-L11: CTD power, procedure: none found (assumed); drill:DPC@9; drill:MET@9
- **How others handle it:**
    - *International*: [Early Warnings for All](https://wmo.int/resources/wmo-bulletin/wmo-bulletin-vol-72-1-2023/overview-of-early-warnings-all-executive-action-plan-2023-2027). People-centred warning systems include community observations and feedback. *Fit for Cameroon:* Formalise a channel from village chiefs to the crisis committee.
    - *European Union*: [Regulation (EU) 2024/1689 (AI Act), Articles 14 and 26](https://eur-lex.europa.eu/eli/reg/2024/1689/oj). High-risk AI must allow effective human oversight, and deployers must assign competent people to oversee it. *Fit for Cameroon:* A named person validating an AI-drafted alert before release can be required without adopting the whole Act.
    - *United States*: [FCC findings on the Hawaii false missile alert (2018)](https://www.fcc.gov/node/215906). Recommended second-person verification before any live alert is released and pre-scripted correction procedures. *Fit for Cameroon:* A simple procedure rule, cheap to adopt.

### G7-09 · People left out: Send alerts in the languages people understand

- **Type:** G7 People left out · **Severity:** 3 (risk to life or rights) · **Status:** confirmed by text
- **When:** event(s) 10, first at D11 11:30
- **What is missing:** No institution holds the power or duty to send alerts in the languages people understand
- **Institutions concerned:** ART, DPC, OPS
- **Texts checked:** CM-S02, CM-S03, CM-S05, CM-S06
- **Evidence:** Who-does-what map (CM): no institution holds 'multilingual_alerting'; drill:DPC@10; drill:OPS@10; drill:ART@10
- **How others handle it:**
    - *International*: [Recommendation ITU-T X.1303 (CAP 1.2)](https://www.itu.int/rec/T-REC-X.1303). One alert can carry several info blocks, each in a different language. *Fit for Cameroon:* Pre-translated templates for local languages.
    - *Mauritius*: [Common Alerting Protocol adoption (2023)](https://www.preventionweb.net/quick/96844). Alerts reach people through many channels, including radio and sirens. *Fit for Cameroon:* An African example.
    - *Japan*: [J-Alert, National Instantaneous Warning System](https://www.city.inagi.tokyo.jp/en/kurashi/iza/1002270/1010142/1012096.html). Triggers municipal radio and outdoor loudspeakers automatically, reaching people without phones. *Fit for Cameroon:* Loudspeakers and radio reach people phones miss.

### G7-10 · People left out: Reach people without phones or network coverage

- **Type:** G7 People left out · **Severity:** 3 (risk to life or rights) · **Status:** confirmed by text
- **When:** event(s) 10, first at D11 11:30
- **What is missing:** No institution holds the power or duty to reach people without phones or network coverage
- **Institutions concerned:** ART, DPC, OPS
- **Texts checked:** CM-S02, CM-S03, CM-S04, CM-S05
- **Evidence:** Who-does-what map (CM): no institution holds 'reach_unconnected'
- **How others handle it:**
    - *Japan*: [J-Alert, National Instantaneous Warning System](https://www.city.inagi.tokyo.jp/en/kurashi/iza/1002270/1010142/1012096.html). Automatically triggers municipal radio and outdoor loudspeakers, reaching people without phones. *Fit for Cameroon:* Community radio and loudspeakers exist in many Cameroonian towns.
    - *International*: [Early Warnings for All (ITU pillar)](https://wmo.int/resources/wmo-bulletin/wmo-bulletin-vol-72-1-2023/overview-of-early-warnings-all-executive-action-plan-2023-2027). Uses AI and satellite imagery to map unconnected populations, and promotes multi-channel alerting. *Fit for Cameroon:* ITU support is available to Cameroon.
    - *Mauritius*: [Common Alerting Protocol adoption (2023)](https://www.preventionweb.net/quick/96844). Alerts reach people through many channels, including radio and sirens. *Fit for Cameroon:* Channels that do not need a smartphone widen reach.

### G3-11 · No procedure: Order the evacuation of a danger zone

- **Type:** G3 No procedure · **Severity:** 3 (risk to life or rights) · **Status:** suspected (needs expert check)
- **When:** event(s) 11, first at D11 18:00
- **What is missing:** No procedure, deadline or form for: order the evacuation of a danger zone
- **Institutions concerned:** DPC
- **Texts checked:** CM-S01, CM-S03
- **Evidence:** CM-L05: DPC power, procedure: none found (inferred)
- **How others handle it:**
    - *Japan*: [J-Alert](https://www.city.inagi.tokyo.jp/en/kurashi/iza/1002270/1010142/1012096.html). Pre-defined local channels carry evacuation instructions. *Fit for Cameroon:* Pre-defined evacuation areas speed decisions.
    - *European Union*: [Regulation (EU) 2024/1689 (AI Act), Articles 14 and 26](https://eur-lex.europa.eu/eli/reg/2024/1689/oj). High-risk AI must allow effective human oversight, and deployers must assign competent people to oversee it. *Fit for Cameroon:* A named person validating an AI-drafted alert before release can be required without adopting the whole Act.
    - *United States*: [FCC findings on the Hawaii false missile alert (2018)](https://www.fcc.gov/node/215906). Recommended second-person verification before any live alert is released and pre-scripted correction procedures. *Fit for Cameroon:* A simple procedure rule, cheap to adopt.

### G8-12 · AI unchecked: Authorise automatic release of AI-drafted alerts without human validation

- **Type:** G8 AI unchecked · **Severity:** 3 (risk to life or rights) · **Status:** confirmed by text
- **When:** event(s) 12, first at D11 20:00
- **What is missing:** No institution holds the power or duty to authorise automatic release of AI-drafted alerts without human validation
- **Institutions concerned:** DPC, OPS
- **Texts checked:** CM-S01, CM-S04, CM-S05
- **Evidence:** Who-does-what map (CM): no institution holds 'authorise_automatic_ai_alert'; drill:DPC@12; drill:OPS@12
- **How others handle it:**
    - *European Union*: [Regulation (EU) 2024/1689 (AI Act), Articles 14 and 26](https://eur-lex.europa.eu/eli/reg/2024/1689/oj). High-risk AI must allow effective human oversight and guard against over-reliance; deployers assign competent people to oversee it. *Fit for Cameroon:* Automatic release without a human step would need an explicit legal basis and safeguards.
    - *United States*: [FCC findings on the Hawaii false missile alert (2018)](https://www.fcc.gov/node/215906). Recommended second-person verification before any live alert is released. *Fit for Cameroon:* Speed gained by removing the check is the risk the Hawaii case illustrates.

### G2-13 · Two in charge: Issue an official weather or flood warning

- **Type:** G2 Two in charge · **Severity:** 2 (delay or extra cost) · **Status:** suspected (needs expert check)
- **When:** event(s) 1, first at D1 06:00
- **What is missing:** Several institutions hold 'issue an official weather or flood warning' and no text says who leads
- **Institutions concerned:** MET, ONR
- **Texts checked:** CM-S01, CM-S03, CM-S04, CM-S06
- **Evidence:** CM-L06: MET duty (assumed); CM-L07: ONR power (documented); drill:MET@1
- **How others handle it:**
    - *Mauritius*: [Common Alerting Protocol adoption (2023)](https://www.preventionweb.net/quick/96844). Clear roles: the meteorological service issues, the disaster centre coordinates, the ICT authority disseminates. *Fit for Cameroon:* An African example.
    - *Philippines*: [Republic Act No. 10639, Section 4](https://issuances-library.senate.gov.ph/sites/default/files/2023-02/ra%252010639.pdf). Names the agencies whose information makes up the alerts. *Fit for Cameroon:* Naming one lead per hazard avoids overlaps.
    - *United States*: [47 CFR Part 10 (Wireless Emergency Alerts)](https://www.ecfr.gov/current/title-47/chapter-I/subchapter-A/part-10). Separates who originates alerts (authorised authorities), the national gateway, and the operators who transmit them. *Fit for Cameroon:* A list of authorised originators per hazard settles who may decide.

### G3-14 · No procedure: Issue an official weather or flood warning

- **Type:** G3 No procedure · **Severity:** 2 (delay or extra cost) · **Status:** suspected (needs expert check)
- **When:** event(s) 1, first at D1 06:00
- **What is missing:** No procedure, deadline or form for: issue an official weather or flood warning
- **Institutions concerned:** MET, ONR
- **Texts checked:** CM-S01, CM-S03, CM-S04, CM-S06
- **Evidence:** CM-L06: MET duty, procedure: none found (assumed); CM-L07: ONR power, procedure: none found (documented); drill:MET@1
- **How others handle it:**
    - *Mauritius*: [Common Alerting Protocol adoption (2023)](https://www.preventionweb.net/quick/96844). Clear roles: the meteorological service issues, the disaster centre coordinates, the ICT authority disseminates. *Fit for Cameroon:* An African example.
    - *Philippines*: [Republic Act No. 10639, Section 4](https://issuances-library.senate.gov.ph/sites/default/files/2023-02/ra%252010639.pdf). Names the agencies whose information makes up the alerts. *Fit for Cameroon:* Naming one lead per hazard avoids overlaps.
    - *European Union*: [Regulation (EU) 2024/1689 (AI Act), Articles 14 and 26](https://eur-lex.europa.eu/eli/reg/2024/1689/oj). High-risk AI must allow effective human oversight, and deployers must assign competent people to oversee it. *Fit for Cameroon:* A named person validating an AI-drafted alert before release can be required without adopting the whole Act.

### G1-15 · Nobody in charge: Correct or cancel a false alert

- **Type:** G1 Nobody in charge · **Severity:** 2 (delay or extra cost) · **Status:** confirmed by text
- **When:** event(s) 6, first at D1 12:00
- **What is missing:** No institution holds the power or duty to correct or cancel a false alert
- **Institutions concerned:** ART, DPC, MET, OPS
- **Texts checked:** CM-S01, CM-S02, CM-S04, CM-S06
- **Evidence:** Who-does-what map (CM): no institution holds 'correct_false_alert'; drill:MET@6; drill:DPC@6; drill:OPS@6; drill:ART@6
- **How others handle it:**
    - *United States*: [FCC findings on the Hawaii false missile alert (2018)](https://www.fcc.gov/node/215906). No correction procedure existed; 38 minutes passed before a correction reached phones. Pre-scripted correction messages were recommended. *Fit for Cameroon:* Cameroon can prepare correction templates before any AI alert goes live.
    - *International*: [Recommendation ITU-T X.1303 (CAP 1.2)](https://www.itu.int/rec/T-REC-X.1303). Update and cancel message types let a wrong alert be corrected or withdrawn in a standard way. *Fit for Cameroon:* Free to adopt.
    - *European Union*: [Directive (EU) 2018/1972 (European Electronic Communications Code), Article 110](https://eur-lex.europa.eu/eli/dir/2018/1972/oj). Mobile operators must relay public warnings from the national public warning system to the end-users concerned. *Fit for Cameroon:* A decree or regulator decision could create the same duty and name the authority that originates the warning.

### G1-16 · Nobody in charge: Explain publicly what went wrong after an error

- **Type:** G1 Nobody in charge · **Severity:** 2 (delay or extra cost) · **Status:** confirmed by text
- **When:** event(s) 6, first at D1 12:00
- **What is missing:** No institution holds the power or duty to explain publicly what went wrong after an error
- **Institutions concerned:** ART, DPC, MET, OPS
- **Texts checked:** CM-S01, CM-S02, CM-S03, CM-S04
- **Evidence:** Who-does-what map (CM): no institution holds 'public_communication_after_error'
- **How others handle it:**
    - *United States*: [FCC findings on the Hawaii false missile alert (2018)](https://www.fcc.gov/node/215906). Social media corrected the alert faster than the official system, showing the need for a planned public explanation. *Fit for Cameroon:* Name a spokesperson in the plan.
    - *European Union*: [Directive (EU) 2018/1972 (European Electronic Communications Code), Article 110](https://eur-lex.europa.eu/eli/dir/2018/1972/oj). Mobile operators must relay public warnings from the national public warning system to the end-users concerned. *Fit for Cameroon:* A decree or regulator decision could create the same duty and name the authority that originates the warning.
    - *Philippines*: [Republic Act No. 10639, Free Mobile Disaster Alerts Act (2014), Sections 4 and 6](https://issuances-library.senate.gov.ph/sites/default/files/2023-02/ra%252010639.pdf). Operators must send free alerts with content from named agencies; fines and franchise suspension for non-compliance. *Fit for Cameroon:* Requires naming content providers and setting penalties.

### G9-17 · Channel unprotected: Stop fake alerts that imitate the official channel

- **Type:** G9 Channel unprotected · **Severity:** 2 (delay or extra cost) · **Status:** suspected (needs expert check)
- **When:** event(s) 7, first at D1 15:00
- **What is missing:** No procedure, deadline or form for: stop fake alerts that imitate the official channel
- **Institutions concerned:** ANTIC
- **Texts checked:** CM-S01, CM-S03, CM-S04
- **Evidence:** CM-L10: ANTIC power, procedure: none found (inferred)
- **How others handle it:**
    - *United States*: [47 CFR Part 10 (Wireless Emergency Alerts)](https://www.ecfr.gov/current/title-47/chapter-I/subchapter-A/part-10). Only authorised alerting authorities can originate alerts through a single national gateway, which limits imitation. *Fit for Cameroon:* Cameroon could designate one authenticated originator and a short code for official alerts.
    - *International*: [Recommendation ITU-T X.1303 (CAP 1.2)](https://www.itu.int/rec/T-REC-X.1303). Alerts carry an identified sender and can be digitally signed. *Fit for Cameroon:* Free to adopt.

## Decision timeline

| Story time | Seat | Decision | Legal basis | Quote check | Confidence | By |
| --- | --- | --- | --- | --- | --- | --- |
| D1 06:00 | MET | Act: Issue an official weather or flood warning (no written procedure found; acting on general powers) | NO LEGAL BASIS FOUND | - | low | rules |
| D1 06:20 | MET | No legal basis found to check and validate an AI-generated forecast before it is used for a public decision. Flagging a gap. | NO LEGAL BASIS FOUND | - | low | rules |
| D1 06:20 | HYDRO | Output produced. HydroSense informs; it does not decide. Validity limits are in its model card. | - | - | medium | scripted |
| D1 06:45 | DPC | Act: Decide to alert the public (no written procedure found; acting on general powers) | CM-S01 Early warning and public alerting | ok | medium | rules |
| D1 07:10 | OPS | Act: Technically send the alert to phones (SMS or cell broadcast) (no written procedure found; acting on general powers) | CM-S03 Operators | ok | medium | rules |
| D1 08:30 | DPC | No legal basis found to answer for harm caused by a wrong alert. Flagging a gap. | NO LEGAL BASIS FOUND | - | low | rules |
| D1 08:30 | ART | No legal basis found to answer for harm caused by a wrong alert. Flagging a gap. | NO LEGAL BASIS FOUND | - | low | rules |
| D1 12:00 | MET | No legal basis found to correct or cancel a false alert. Flagging a gap. | NO LEGAL BASIS FOUND | - | low | rules |
| D1 12:00 | DPC | No legal basis found to correct or cancel a false alert. Flagging a gap. | NO LEGAL BASIS FOUND | - | low | rules |
| D1 12:00 | OPS | No legal basis found to correct or cancel a false alert. Flagging a gap. | NO LEGAL BASIS FOUND | - | low | rules |
| D1 12:00 | ART | No legal basis found to correct or cancel a false alert. Flagging a gap. | NO LEGAL BASIS FOUND | - | low | rules |
| D1 15:00 | ANTIC | Act: Stop fake alerts that imitate the official channel (no written procedure found; acting on general powers) | CM-S04 Institutions | ok | medium | rules |
| D1 15:00 | ART | Ask ANTIC to stop fake alerts that imitate the official channel | - | - | low | rules |
| D11 04:00 | MET | No legal basis found to report that sensors feeding the AI are down and the forecast is unreliable. Flagging a gap. | NO LEGAL BASIS FOUND | - | low | rules |
| D11 04:00 | HYDRO | Output produced. HydroSense informs; it does not decide. Validity limits are in its model card. | - | - | medium | scripted |
| D11 09:00 | DPC | No legal basis found to act on a local, informal warning that contradicts the AI. Flagging a gap. | NO LEGAL BASIS FOUND | - | low | rules |
| D11 09:00 | MET | No legal basis found to act on a local, informal warning that contradicts the AI. Flagging a gap. | NO LEGAL BASIS FOUND | - | low | rules |
| D11 11:30 | DPC | No legal basis found to send alerts in the languages people understand. Flagging a gap. | NO LEGAL BASIS FOUND | - | low | rules |
| D11 11:30 | OPS | No legal basis found to send alerts in the languages people understand. Flagging a gap. | NO LEGAL BASIS FOUND | - | low | rules |
| D11 11:30 | ART | No legal basis found to send alerts in the languages people understand. Flagging a gap. | NO LEGAL BASIS FOUND | - | low | rules |
| D11 18:00 | MET | Ask DPC to coordinate the multi-sector response | - | - | low | rules |
| D11 18:00 | DPC | Act: Coordinate the multi-sector response | CM-S01 Civil Protection Directorate (MINAT / DPC) | ok | high | rules |
| D11 18:00 | DPC | Act: Activate the emergency and rescue plan | CM-S01 Cameroon disaster management law: summary of the IFRC legal mapping (2021) / Leg | ok | medium | rules |
| D11 18:00 | DPC | Act: Order the evacuation of a danger zone (no written procedure found; acting on general powers) | CM-S07 Warnings | ok | medium | rules |
| D11 18:00 | OPS | Ask DPC to coordinate the multi-sector response | - | - | low | rules |
| D11 18:00 | ART | Ask DPC to coordinate the multi-sector response | - | - | low | rules |
| D11 20:00 | DPC | No legal basis found to authorise automatic release of AI-drafted alerts without human validation. Flagging a gap. | NO LEGAL BASIS FOUND | - | low | rules |
| D11 20:00 | OPS | No legal basis found to authorise automatic release of AI-drafted alerts without human validation. Flagging a gap. | NO LEGAL BASIS FOUND | - | low | rules |

## Readiness scorecard (ITU AI Readiness Framework, 13 dimensions)

Scores describe what this drill revealed (5 = no gap found, 0 = many serious gaps); they are not an official rating.

| # | Dimension | Score | Evidence |
| --- | --- | --- | --- |
| 1 | Data/Model Marketplace | not assessed | not assessed by this story |
| 2 | Generated Content Marketplace | 0.7 / 5 | G8-01 AI unchecked: Check and validate an AI-generated forecast before it is used for a public decision; G8-07 AI unchecked: Report that sensors feeding the AI are down and the forecast is unreliable; G8-12 AI unchecked: Authorise automatic release of AI-drafted alerts without human validation |
| 3 | Cross-Domain Correlation Analysis | 4.4 / 5 | G2-13 Two in charge: Issue an official weather or flood warning |
| 4 | Contextualization and Regional Impact | 2.5 / 5 | G7-09 People left out: Send alerts in the languages people understand; G7-10 People left out: Reach people without phones or network coverage |
| 5 | Level of Integration of AI in Workflows | 0.0 / 5 | G8-01 AI unchecked: Check and validate an AI-generated forecast before it is used for a public decision; G3-02 No procedure: Decide to alert the public; G3-03 No procedure: Approve an AI-drafted alert through a human validation step before release |
| 6 | Human Interface | 2.5 / 5 | G7-09 People left out: Send alerts in the languages people understand; G7-10 People left out: Reach people without phones or network coverage |
| 7 | Strategy Alignment | 0.0 / 5 | G3-02 No procedure: Decide to alert the public; G3-03 No procedure: Approve an AI-drafted alert through a human validation step before release; G1-04 Nobody in charge: Order mobile operators to relay a public alert |
| 8 | Collaboration with AI | 1.2 / 5 | G8-01 AI unchecked: Check and validate an AI-generated forecast before it is used for a public decision; G8-07 AI unchecked: Report that sensors feeding the AI are down and the forecast is unreliable; G8-12 AI unchecked: Authorise automatic release of AI-drafted alerts without human validation |
| 9 | Impacts of Humans in AI Integration | 1.2 / 5 | G8-01 AI unchecked: Check and validate an AI-generated forecast before it is used for a public decision; G8-07 AI unchecked: Report that sensors feeding the AI are down and the forecast is unreliable; G8-12 AI unchecked: Authorise automatic release of AI-drafted alerts without human validation |
| 10 | AI & Policies | 0.5 / 5 | G1-04 Nobody in charge: Order mobile operators to relay a public alert; G6-06 Nobody answers for harm: Answer for harm caused by a wrong alert; G1-15 Nobody in charge: Correct or cancel a false alert |
| 11 | AI for Inclusion | 2.5 / 5 | G7-09 People left out: Send alerts in the languages people understand; G7-10 People left out: Reach people without phones or network coverage |
| 12 | Granular Priorities | not assessed | not assessed by this story |
| 13 | Digital Infrastructure | 4.4 / 5 | G9-17 Channel unprotected: Stop fake alerts that imitate the official channel |

## Assumptions and sources to confirm

Lines of the who-does-what map that are not directly documented:

- `CM-L04` DPC power *activate_contingency_plan*: Emergency and rescue plans are organised by Decree 98/031 [inferred]
- `CM-L05` DPC power *evacuate_zone*: Administrative authorities order the evacuation of danger zones [inferred]
- `CM-L06` MET duty *issue_weather_warning*: The national meteorology service issues weather forecasts and warnings [assumed (assumed by ALERTE team, 2026-10-07: organisation decree of the meteorology service to obtain)]
- `CM-L09` OPS power *send_mass_alert*: Licensed operators run the networks and can technically send SMS to subscribers [inferred]
- `CM-L10` ANTIC power *block_spoofed_alert*: ANTIC is the national body in charge of electronic security; spoofing and fraudulent links are cybercrimes (Law 2010/012) [inferred]
- `CM-L11` CTD power *act_on_local_warning*: Local councils take part in local civil protection and receive community reports [assumed (assumed by ALERTE team, 2026-10-07: to verify in Law 2019/024)]
- `CM-L12` MINSANTE duty *cholera_response*: The State must detect, assess, notify and report outbreaks (International Health Regulations) [inferred]

National documents used as summaries (official text still to obtain or confirm): CM-S01, CM-S02, CM-S03, CM-S04, CM-S05, CM-S06, CM-S07

## Logbook

Every step of this drill is in `ledger.jsonl`, chained by SHA-256 fingerprints. Check it with `python -m alerte verify cm-core-offline-20261110-101334-eb08`.


*Fictional exercise. Not a real alert. HydroSense and all numbers in the events are invented; places and institutions are real.*
