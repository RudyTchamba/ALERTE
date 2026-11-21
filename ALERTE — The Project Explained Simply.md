# ALERTE — The Project Explained Simply

Oct 3, 2026 · @baudouin

ALERTE is a practice ground where artificial intelligence plays the government services of Cameroon during a flood, so that the weak points in the rules show up in a drill instead of in a real disaster.

## How to read this document

This document explains ALERTE in three steps, in the order a building is designed: first what we want and why, then how each room works, then how the rooms fit together. It deliberately says nothing about programming languages, tools or code; those come later, in the implementation phase.

| Step | Question it answers | Usual name of this kind of document | In French |
| --- | --- | --- | --- |
| Part 1, Describe | What problem do we solve, for whom, in which situations, and what must the solution do? | Project description and requirements (sometimes called a "product requirements document" or "functional specification") | Cahier des charges fonctionnel, expression des besoins |
| Part 2, Design | Which features does the system have, how does each one behave, what information does it handle? | Functional design | Conception fonctionnelle, spécifications fonctionnelles détaillées |
| Part 3, Architecture | What are the big building blocks, how do they talk to each other, where is information kept? | Logical (or high-level) architecture | Architecture logique, architecture fonctionnelle |
| Later, Implement | Which tools, languages and models do we use, and how do we build it? | Technical specification, implementation plan | Spécifications techniques, dossier de réalisation |

**A simple comparison.** Building a house: Part 1 is the family saying "we are five, we need three bedrooms, it rains a lot here". Part 2 is the floor plan: each room, its doors, what happens in it. Part 3 is the structure: foundations, walls that carry weight, water and power lines. Only then does the builder choose bricks or concrete, which is implementation.

**How this differs from the first specification.** The earlier [ALERTE Project Specification](https://claude.ai/code/artifact/e430f513-a80d-4d2e-a9b0-979f67393e06) mixed all four steps and went deep into tools, code and planning. This document stops before any tool is chosen. When the two disagree on what the system should do, this document wins; the earlier one remains the reference for tools, the document list with links, the team plan and Slack.

**How to use it.**

- Everyone reads Part 1. It is the shared understanding of the project.
- The policy analyst and the project lead check Part 1 and Part 2 against reality and the hackathon rules.
- The engineers read all three parts before writing any code.
- If you want to change what ALERTE does, change Part 1 first, then follow the change into Parts 2 and 3.

**Writing conventions.** Each requirement has a code such as **R-12**, each use case **UC-05**, each feature **F-03**. These codes let us check that every requirement has a feature and every feature a building block. Words in *italics* are explained in the word list at the end.

# Part 1 — Describing the project

## 1.1 The project in plain words

### A short story

It is 6 in the morning in Douala. A new computer program that predicts floods says: "Big flood in 6 hours." Someone sends a text message to every phone in the city. People panic, roads jam, some are hurt. No flood comes.

Two weeks later, in the Far North, the same program says "low risk", because some of its river sensors are broken. The flood is real. The warning comes late, only in French, and many villages have no phone signal.

Afterwards, everyone asks: who should have checked the prediction? Who was allowed to send the message? Who answers for the injuries? The honest answer is that nobody knows, because no text says so.

ALERTE exists so that these questions are asked and answered **during a drill**, not after a real disaster.

### The problem

- **Floods are frequent and deadly in Cameroon.** In 2024, floods in the Far North affected about 410,000 people and flooded 262 schools and 65 health centres. Cholera followed.
- **Warning people is the weak link.** In the 2023 Mbankolo landslide in Yaoundé, a warning existed, but it did not lead people to move in time.
- **Artificial intelligence (AI) is arriving in warning systems.** Around the world, AI now helps predict floods, choose which areas to warn, and write or translate warning messages. Cameroon will likely use such tools soon.
- **The rules have not caught up.** Cameroon's disaster laws mention warnings only indirectly. No text says who checks an AI prediction, who may order phone companies to send a message to everyone, or who is responsible when the AI is wrong.
- **These gaps stay invisible until a crisis.** Governments rarely run full crisis drills, because bringing all the ministries together is slow and expensive.

### The idea

A fire drill teaches a school what to do before a real fire. A flight simulator lets a pilot practise an engine failure without risking a plane. **ALERTE is a simulator for the institutions in charge of a crisis.**

1. ALERTE reads the real laws, decrees, plans and strategies of a country.
2. It plays a realistic crisis story, step by step, in which an AI warning system fails.
3. Each institution (civil protection, telecom regulator, weather service, health ministry, data protection authority, phone companies, local councils) is played by a *virtual institution*: an AI that only knows what that institution would know and only has the powers that the law gives it. A real person can take any seat instead.
4. The virtual institutions react, ask each other for help, and take decisions, always saying which article of law allows them to act.
5. When no rule exists, or two institutions both think they are in charge, or nobody is, ALERTE notes a *gap*.
6. For each gap, ALERTE shows how other countries deal with the same problem.
7. Everything is written in a logbook that nobody can secretly change, so anyone can check and replay the drillALERTE reads the real laws, decrees, plans and strategies of a country.
8. It plays a realistic crisis story, step by step, in which an AI warning system fails.
9. Each institution (civil protection, telecom regulator, weather service, health ministry, data protection authority, phone companies, local councils) is played by a *virtual institution*: an AI that only knows what that institution would know and only has the powers that the law gives it. A real person can take any seat instead.
10. The virtual institutions react, ask each other for help, and take decisions, always saying which article of law allows them to act.
11. When no rule exists, or two institutions both think they are in charge, or nobody is, ALERTE notes a *gap*.
12. For each gap, ALERTE shows how other countries deal with the same problem.
13. Everything is written in a logbook that nobody can secretly change, so anyone can check and replay the drill.

### What ALERTE is, and is not

| ALERTE is | ALERTE is not |
| --- | --- |
| A drill (practice exercise) for institutions | A real warning system that sends messages to people |
| A team of virtual institutions, each with its own information and powers | One chatbot that knows everything |
| A tool that points to the exact article behind each decision | A summary of the law written from memory |
| A gap finder that explains why something is a gap | An AI giving its opinion on what is wrong |
| A support for human decisions | A replacement for officials, lawyers or experts |
| A practice ground for any AI-based warning system | A flood prediction model |

### In one sentence

ALERTE lets a country rehearse an AI-assisted crisis, find the holes in its rules before people get hurt, and learn how other countries have filled the same holes.

## 1.2 Who ALERTE is for

ALERTE has people who use it directly, people who benefit from its results, and people who are only represented inside it. The design must serve the first two groups and respect the third.

### People who use ALERTE directly

| Who | What they want from ALERTE | How often |
| --- | --- | --- |
| **Facilitator** (the person who runs a drill: a trainer, a civil protection officer, an ITU expert) | Prepare a drill quickly, run it, pause it, add a surprise event, and end with a clear report | Each drill |
| **Player** (an official, student or judge who takes the seat of one institution) | Receive information, decide, ask questions, and see the consequences | During a drill |
| **Observer** (a minister, a hackathon judge, a journalist invited to watch) | Follow what is happening without touching anything | During or after a drill |
| **Scenario writer** (a disaster expert or our policy analyst) | Write a new crisis story: events, timing, who receives what | Before drills |
| **Knowledge keeper** (a lawyer or analyst who maintains the library) | Add new laws, mark outdated ones, update who has which power | When laws change |
| **Auditor** (anyone checking the work: judge, inspector, researcher) | Check that each decision and each gap is based on real sources and that the logbook was not changed | After a drill |

### People who use the results

| Who | What they need | What they get |
| --- | --- | --- |
| Lawmakers and policy makers | Know which texts to write or update | The gap report with global examples |
| Heads of civil protection, regulators, ministries | Know where coordination breaks down | The decision timeline and the gap report |
| Buyers of AI systems (a ministry about to buy an AI warning tool) | Know what to demand from the seller and what rules to put in place first | A drill of that AI's failure types and the list of gaps it triggers |
| International partners (ITU, World Meteorological Organization, Red Cross, development banks) | Compare countries and plan support | Readiness scorecards and twin-country comparisons |
| Researchers and students | Study how institutions behave with AI | Anonymous logbooks and reports |

### People represented, but never present

The drill involves the population: residents of Douala, villagers in the Far North, people without phones, people who do not read French. They are not users, but the drill must take them into account: who is reached, in which language, who is left out.

### Short portraits

- **Aminatou, 34, civil protection officer in Maroua.** Has lived through the 2024 floods. Wants to know, before next rainy season, who will validate a warning if the new AI system says "red". Uses ALERTE as a player, from her phone.
- **Mr Ndi, 52, legal adviser at a ministry.** Has to draft a decree on public alerts. Uses the gap report and the global examples to write a first draft.
- **Sara, 41, ITU trainer.** Runs a workshop with officials from three countries. Uses ALERTE as a facilitator, with the same story played for each country.
- **A hackathon judge in Dubai.** Has ten minutes. Watches the drill, clicks on one decision, checks its source, and verifies the logbook.

## 1.3 Situations where ALERTE is used

ALERTE is useful at ten moments, from long before a crisis to long after it. It is never used to manage a real crisis while it is happening.

| # | Situation | Who starts it | What they want to learn | What ALERTE gives them |
| --- | --- | --- | --- | --- |
| S1 | **Getting ready for the rainy season** | Civil protection, regional governor's office | Does our plan work? Does everyone know their role? | A full drill, the decision timeline, the gaps to fix before the rains |
| S2 | **Before buying or switching on an AI warning system** | Ministry, weather service, phone company | What happens when this AI is wrong? What rules must exist first? | A drill with that AI's failure types, a list of conditions to demand from the seller |
| S3 | **Before rolling out mass phone alerts** (text messages or *cell broadcast*) | Telecom regulator, ministry of telecoms, phone companies | Who may order an alert, who pays, who is liable? | Gaps on powers, costs and liability, with how other countries organised it |
| S4 | **Writing or updating a law or decree** | Legal advisers, parliament committees | Which holes must the new text fill? | The gap report, organised by topic, with examples of laws abroad |
| S5 | **Training officials** | Schools of administration, ITU, Red Cross, universities | Practise roles and coordination safely | Repeated drills with human players, scores, a debrief |
| S6 | **After a real disaster** (lessons learned) | Inspectors, crisis committee, researchers | Would the rules have handled what happened? | A drill rebuilt from the real timeline, gaps compared with what really went wrong |
| S7 | **When a new law comes into force** | Knowledge keeper | Does the new law close old gaps or create new ones? | The same drill run before and after the change, side by side |
| S8 | **Comparing countries** | ITU, regional organisations, the 2027 AI for Good Summit | How do two legal systems handle the same AI failure? | Twin drills (for example Cameroon and the UAE) and their scorecards side by side |
| S9 | **Research and teaching** | Universities, students | How do institutions behave when AI is involved? | Anonymous logbooks and reports that can be studied |
| S10 | **The hackathon** (November and December 2026) | Our team | Convince judges in a few minutes | A fully recorded drill, the gap report, the logbook check, a live demonstration |

### Where it happens

- **In a meeting room**, with one facilitator, a projector and several players with phones or laptops.
- **Remotely**, with players in different towns (for example Yaoundé, Douala and Maroua), each from their own device.
- **On one laptop with no internet**, for example in a regional office or during power and network cuts.
- **On a stage** (Dubai final, summit), in front of an audience, with a recorded run ready as a backup.

### When ALERTE must not be used

- **To decide during a real crisis.** ALERTE plays fictional stories and its answers are for practice. In a real emergency, officials follow their real procedures. ALERTE says this on every screen.
- **As legal advice.** The legal answers point to texts and examples; a qualified lawyer must confirm them.
- **To judge or rank individual people.** ALERTE looks at rules and institutions, never at the performance of named persons.
- **With real personal data.** No real names, phone numbers, locations or health records are ever put into ALERTE.

## 1.4 Crisis stories ALERTE can play

Every drill is a story built from three ingredients: a **hazard** (what nature or circumstance does), the **sectors** it touches, and the **way the AI fails**. The prototype plays one full Cameroon story and its UAE twin; the design must allow any combination later.

### The main story: "Rising Waters" (Cameroon)

A fictional AI system called **HydroSense** predicts floods and drafts warning messages for the authorities. It is being tested in Douala and in the Far North.

| Act | Where | What happens | Main questions raised |
| --- | --- | --- | --- |
| 1. The false alarm | Douala | HydroSense predicts a major flood. A message goes to every phone. Panic, traffic jams, people hurt in a crowd. No flood. A fake follow-up message with a fraudulent link spreads. | Who checks an AI prediction? Who may order phone companies to alert everyone? Who answers for the injuries? Who stops fake alerts? |
| 2. The missed flood | Far North, Logone river | Three of seven river sensors are broken; HydroSense says "low risk". A village chief reports rising water. The warning goes out late, in French only, and 30% of the area has no signal. About 40,000 people are displaced. | Who acts when local people and the AI disagree? Must warnings be in several languages? Who reaches people without phones? |
| 3. The aftermath | Displacement sites | Cholera cases appear. The health ministry wants phone location data to follow people's movements. The AI seller offers to analyse the data on its servers abroad. Parliament asks who was responsible for each failure. | Can health authorities use phone data? Can data leave the country, and who authorises it? Can anyone draw a clear map of responsibilities? |

### The twin story (United Arab Emirates)

The same three acts, with the same AI failure, played with UAE institutions and laws: Act 1 in Dubai, Act 2 in Al Ain (inspired by the record rain of 16 April 2024), Act 3 with the same health-data question. The goal is to compare how two very different legal systems handle the same problem.

### Other stories the design must support

| Story family | Example | Sectors | Status |
| --- | --- | --- | --- |
| Floods | Rising Waters | Telecom, public services, health, education | **Prototype** |
| Floods, twin country | UAE twin | Same | **Prototype** |
| AI in health care | An AI that reads tuberculosis X-rays, hosted abroad, gets worse after an update | Health, data protection | Later (if time allows) |
| Landslides | Heavy rain over unstable slopes in a city (like Mbankolo, 2023) | Public services, urban planning, telecom | Later |
| Epidemics alone | A cholera or measles outbreak where AI predicts hotspots | Health, data protection, telecom | Later |
| Droughts and food | An AI that predicts poor harvests and triggers aid | Agriculture, social protection | Later |
| Heat waves | Heat alerts for schools and outdoor workers | Health, education, labour | Later |
| Volcano or lake gas | Mount Cameroon eruption; a gas release like Lake Nyos (1986) | Public services, telecom | Later |
| Cyclones and storms (other countries) | Storm warnings in coastal countries | Telecom, public services | Later |
| Technology accidents | A nationwide mobile network outage during a storm | Telecom, public services | Later |

### The ways an AI can fail (the failure menu)

Each story must include at least six of these. They are the heart of the drill.

| Failure | In simple words | Where in Rising Waters |
| --- | --- | --- |
| False alarm | The AI warns of a danger that does not come | Act 1 |
| Missed danger | The AI says "low risk" and the disaster happens | Act 2 |
| Bad input | Broken or wrong sensors, and the AI does not say so | Act 2 |
| Wrong place | The warning goes to the wrong neighbourhoods | Spare |
| Wrong language | The message is in one language only, or badly translated | Act 2 |
| People left out | People without phones, signal or reading skills are not reached | Act 2 |
| Made-up instructions | The AI writes advice that is wrong ("go to the stadium" when it is flooded) | Spare |
| Fake alerts | Someone imitates the official channel | Act 1 |
| Blind trust | People follow the AI without checking it | Act 1 |
| Privacy breach | Personal or location data used without a legal basis | Act 3 |
| Data sent abroad | Data processed in another country without permission | Act 3 |
| Getting worse over time | The AI's quality drops after an update or as conditions change | Health story |

### The kinds of events inside a story

To feel real, a story mixes different kinds of events, called *injects*:

- **Measurements:** rain gauges, river levels, sensor status.
- **AI outputs:** predictions, risk levels, draft messages.
- **Official messages:** an email from the weather service, a phone call from civil protection.
- **Field reports:** a village chief, a Red Cross volunteer, a hospital.
- **Public reaction:** social media, journalists' questions, rumours.
- **Technical incidents:** network down, sensors offline, power cut.
- **Political or legal pressure:** parliament asks for a report, a court is seized.
- **Wrong or contradicting information:** a false rumour, a report that turns out to be wrong.

Each event goes only to the institutions that would receive it in real life, sometimes late, sometimes incomplete.

## 1.5 Use cases

A *use case* is one thing a person does with ALERTE to reach one goal. ALERTE has 24 use cases in four groups: preparing, running, reviewing, and special uses. The 10 most important are described step by step after the overview.

### Overview

| Code | Use case | Main person | Situations |
| --- | --- | --- | --- |
| **Preparing a drill** |  |  |  |
| UC-01 | Add a country's library of documents | Knowledge keeper | S1 to S10 |
| UC-02 | Build or update the map of who does what | Knowledge keeper | S1 to S10 |
| UC-03 | Write or edit a crisis story | Scenario writer | S1 to S6 |
| UC-04 | Set up a drill (country, story, who plays what, speed, language) | Facilitator | All |
| UC-05 | Invite players and give them their seats | Facilitator | S1, S5, S8 |
| **Running a drill** |  |  |  |
| UC-06 | Start, pause, resume, speed up or stop a drill | Facilitator | All |
| UC-07 | Let all institutions be played by the AI (autopilot) | Facilitator | S2, S4, S7, S10 |
| UC-08 | Play an institution's seat as a human | Player | S1, S5, S8 |
| UC-09 | Receive an event and take a decision | Player or virtual institution | All |
| UC-10 | Ask another institution for action or information | Player or virtual institution | All |
| UC-11 | Ask the legal adviser a question | Anyone | All |
| UC-12 | Add a surprise event during the drill | Facilitator | S1, S5 |
| UC-13 | Watch the drill without taking part | Observer | S8, S10 |
| **Reviewing a drill** |  |  |  |
| UC-14 | Read the gap report | Policy maker, facilitator | All |
| UC-15 | Check the sources behind a decision or a gap | Auditor | All |
| UC-16 | Replay a past drill step by step | Anyone | All |
| UC-17 | Check that the logbook has not been changed | Auditor | S9, S10 |
| UC-18 | Read the readiness scorecard | Policy maker, partner | S1, S8 |
| UC-19 | Have an expert confirm or reject a gap | Expert, knowledge keeper | All |
| UC-20 | Export and share the report | Facilitator | All |
| **Special uses** |  |  |  |
| UC-21 | Compare two countries on the same story | Partner, trainer | S8 |
| UC-22 | Compare before and after a change in the law | Knowledge keeper, lawmaker | S4, S7 |
| UC-23 | Rebuild a real past event as a drill | Inspector, researcher | S6 |
| UC-24 | Test the failure profile of a specific AI system before buying it | Buyer | S2, S3 |

### UC-01 Add a country's library

**Goal:** make a country's laws, decrees, plans and strategies available to the drill.

1. The knowledge keeper lists the documents to add, with their exact title, date, link and language.
2. For each document, they say what kind it is (law, decree, plan, strategy, report, news) and how sure we are of it (official text, reliable summary, or not yet found).
3. ALERTE reads each document and cuts it into passages, one per article where possible.
4. ALERTE proposes, for each passage, which institutions and topics it concerns; the knowledge keeper checks the important ones.
5. The knowledge keeper runs a set of test questions to confirm the right passages come back.

**Result:** the library is ready, each passage traceable to its source. **If something goes wrong:** a document that cannot be read is listed as "unreadable" and is not used; a missing document is listed as "not found", which may itself become a gap.

### UC-02 Build the map of who does what

**Goal:** write down, for each institution, what it may do (powers), what it must do (duties), and which article says so.

1. ALERTE reads the main texts and proposes lines such as "Civil protection must spread the warning once a plan is activated (Decree 98/031)".
2. The knowledge keeper accepts, corrects or rejects each line.
3. Where no text exists but the story needs an answer, the line is added as an *assumption*, with who said it and when.
4. Each line is marked: written in a text, deduced from a text, or assumed.

**Result:** a map that the virtual institutions use to know their limits, and that the gap finder uses to find holes.

### UC-03 Write a crisis story

**Goal:** create a realistic drill.

1. The writer chooses a hazard, a place, the sectors and at least six AI failure types.
2. They write the events in order, with a story time (for example "Day 1, 07:10"), who receives each event, and its text.
3. For each event, they note which rule or responsibility it is meant to test (the "expected gaps").
4. They describe the fictional AI: what it does, the data it needs, its limits.
5. They mark everything as fictional.

**Result:** a story that can be played again and again, and later checked: did the drill find the expected gaps?

### UC-04 Set up a drill

1. The facilitator chooses the country, the story, the language, and the speed (for example one story day in 15 minutes).
2. For each institution, they choose: played by the AI, or by a named human seat.
3. They choose what observers may see (everything, or only the public parts).
4. ALERTE checks that every needed piece exists (library, map, story, seats) and warns if something is missing.

### UC-08 and UC-09 Play a seat and take a decision

1. The player receives a short role card: who they are, what powers the law gives them, who they can contact.
2. Events arrive in their inbox as the story moves on. They only see their own inbox.
3. For each event they write what they know, what they do not know, and what they decide.
4. They must say on which text their decision rests, or say "no legal basis found".
5. They can search the library (limited to the texts their institution would use), ask another institution, or ask the legal adviser.

**Result:** the decision is recorded with its reasons and sources. **If something goes wrong:** if the human does not answer in time, the AI takes over the seat and this is noted.

### UC-10 Ask another institution

1. An institution posts a request, for example civil protection to a phone company: "Send a message to every phone in Douala."
2. The receiving institution answers: accepted, refused (with reason), or "not our role".
3. If no one accepts a request, or two institutions both claim it, ALERTE notes a gap.

### UC-11 Ask the legal adviser

1. Anyone asks a question in plain words, for example "Can the health ministry use phone location data to follow cholera?"
2. The adviser answers in four parts: what the national texts say (with articles); what is unclear or missing; how at least two other countries handle it; a suggestion, clearly marked as a suggestion.
3. Every answer ends with "for practice only; confirm with a lawyer".

### UC-14 Read the gap report

1. At the end, ALERTE lists the gaps, most serious first.
2. Each gap shows: what happened, at what moment, which texts were checked, what is missing, how other countries do it, how sure we are, and the evidence.
3. The reader can filter by type, institution or sector, and open any source.

### UC-16 and UC-17 Replay and check the logbook

1. The auditor opens a past drill and moves a time slider; the screens show exactly what each institution knew and did at that moment.
2. They press "check the logbook"; ALERTE answers "intact" or shows the first entry that was changed.

### UC-24 Test a specific AI system before buying it

1. The buyer describes the AI system: what it predicts, what data it needs, how accurate it claims to be, where its data is processed.
2. ALERTE builds a story that uses that AI's likely failures (from the failure menu).
3. The drill is run on autopilot.
4. The report lists the gaps triggered by this AI, and turns them into a list of conditions to put in the purchase contract and the rules to adopt before switching it on.

## 1.6 What ALERTE must do, and how well

The requirements below are the promises ALERTE makes. "Must" means the prototype cannot be submitted without it; "Should" means we build it if time allows; "Later" means after the hackathon.

### What ALERTE must do

| Code | ALERTE must… | Priority | Use cases |
| --- | --- | --- | --- |
| **Library** |  |  |  |
| R-01 | Keep the laws, decrees, plans and strategies of at least Cameroon and the UAE, plus examples from other countries | Must | UC-01 |
| R-02 | Remember, for every passage, its document, article, language, date and link | Must | UC-01, UC-15 |
| R-03 | Say how sure it is of each document: official text, reliable summary, or not found | Must | UC-01 |
| R-04 | Find the right passages when asked a question in French or English (Arabic later) | Must | UC-09, UC-11 |
| **Who does what** |  |  |  |
| R-05 | Keep a map of each institution's powers and duties, each linked to its article or marked as an assumption | Must | UC-02 |
| R-06 | Let a human expert accept, correct or reject each line of that map | Must | UC-02, UC-19 |
| **Stories and drills** |  |  |  |
| R-07 | Play a story whose events arrive one by one, at set story times | Must | UC-06 |
| R-08 | Send each event only to the institutions that should receive it | Must | UC-09 |
| R-09 | Let the facilitator start, pause, resume, speed up, stop, and add a surprise event | Must (surprise: Should) | UC-06, UC-12 |
| R-10 | Let a new story be written without changing the system | Should | UC-03 |
| **Virtual institutions** |  |  |  |
| R-11 | Give each institution its own inbox, memory, powers and allowed documents, and never show it another institution's inbox | Must | UC-08, UC-09 |
| R-12 | Make each institution write, for each decision: what it knows, what it does not know, its options, its choice, its legal basis, and how sure it is | Must | UC-09 |
| R-13 | Make an institution say "no legal basis found" rather than invent one | Must | UC-09 |
| R-14 | Let institutions send each other requests, answers, objections and gap alerts | Must | UC-10 |
| R-15 | Let a human take any seat, from a computer or a phone, and let the AI take it back if the human does not answer | Should | UC-08 |
| R-16 | Offer a legal adviser that anyone can ask, answering in four parts with sources | Must | UC-11 |
| **Gaps and examples** |  |  |  |
| R-17 | Detect gaps by checking the story's needs and the decisions against the map, using clear rules | Must | UC-14 |
| R-18 | For each gap, show the evidence, a seriousness level and a confidence level | Must | UC-14 |
| R-19 | For each gap, find at least two examples from different countries or organisations, with sources | Must | UC-14 |
| R-20 | Check every quoted article against the library and flag any quote that cannot be found | Must | UC-15 |
| **Records and reports** |  |  |  |
| R-21 | Write every event, search, AI answer, message and decision into a logbook in order | Must | UC-15, UC-16 |
| R-22 | Make any change to the logbook detectable | Must | UC-17 |
| R-23 | Replay any past drill without calling the AI again | Must | UC-16 |
| R-24 | Produce a gap report, a decision timeline and a readiness scorecard on the 13 dimensions of the ITU AI Readiness Framework | Must | UC-14, UC-18 |
| R-25 | Export reports in common formats (document and PDF) | Should | UC-20 |
| **Comparisons** |  |  |  |
| R-26 | Run the same story for two countries and show results side by side | Must (twin), Later (any pair) | UC-21 |
| R-27 | Run the same drill before and after a change in the law and show the difference | Later | UC-22 |
| R-28 | Build a drill from a real past timeline | Later | UC-23 |
| R-29 | Build a drill from the description of a specific AI system | Later | UC-24 |

### How well ALERTE must do it (qualities)

| Code | Quality | What it means in practice |
| --- | --- | --- |
| Q-01 | **Honest** | Never presents a guess as a fact; every claim shows its source or is marked as an assumption |
| Q-02 | **Traceable** | From any decision or gap, a reader reaches the original text in two clicks |
| Q-03 | **Understandable** | A non-specialist understands each screen and each report without training |
| Q-04 | **Bilingual** | Every screen and report in French and English; Arabic for the UAE twin later |
| Q-05 | **Works with weak connections** | Can run a full drill on one laptop without internet, even if answers are slower or simpler |
| Q-06 | **Fast enough** | A full Rising Waters drill on autopilot finishes in under 20 minutes |
| Q-07 | **Repeatable** | Running the same drill three times finds mostly the same gaps |
| Q-08 | **Safe** | No real personal data, ever; "Fictional exercise" shown on every screen |
| Q-09 | **Open** | The Cameroon library and its map can be shared with ITU as an open resource |
| Q-10 | **Adaptable** | Adding a country, a story, a language or an institution does not require redesigning the system |
| Q-11 | **Independent of one AI provider** | The AI "brain" can be swapped without changing the rest |
| Q-12 | **Respectful** | Names institutions, never individuals; neutral tone; avoids political topics |

### Hackathon check

Every requirement of the hackathon is covered:

| Hackathon asks for | Covered by |
| --- | --- |
| A knowledge base of country documents, built with ITU's method | R-01 to R-04 |
| Agents in the roles of innovative solution, policy and legal adviser, institutional participant, multi-agent coordination | R-11 to R-16 (the fictional AI system plays the "innovative solution" under test) |
| Error scenarios released progressively, with uneven information | R-07, R-08 |
| Audit logging and reasoning traces | R-12, R-20 to R-23 |
| Gap identification with global examples | R-17 to R-19 |
| Alignment with ITU-T Y.3172 and the AI Readiness Framework | R-24 and Part 3 |

## 1.7 Unusual situations, limits and success

A good drill tool must behave sensibly when things are missing, wrong or broken. This section lists what ALERTE must do in each unusual situation we can foresee, what it cannot promise, and how we will judge success.

### Unusual situations and the expected behaviour

| Area | Situation | What ALERTE must do |
| --- | --- | --- |
| Information | A law exists but we only have a summary | Use it, but label every answer based on it "from a summary" |
| Information | A law is missing entirely | Say "no text found"; consider it a possible gap; never fill the hole by guessing |
| Information | Two texts contradict each other | Show both, say which is more recent or higher in rank, and note a possible gap |
| Information | A text is outdated or replaced | Keep it for history, mark it "replaced by…", and never use it as the current rule |
| Information | The French and English versions differ | Treat the official language version as the reference and note the difference |
| Information | Two events in the story contradict each other | Normal: institutions must notice it and say which they trust |
| People | A human player does not answer in time | The AI takes the seat back; the logbook notes the switch |
| People | A human player tries to see another institution's inbox | Impossible by design; each seat sees only its own inbox and the public board |
| People | A player takes a decision with no legal basis | Allowed (as in real life), but recorded as "no legal basis" and counted as a possible gap |
| People | The facilitator makes a mistake (wrong event, wrong seat) | Can pause and correct; the correction is written in the logbook, never hidden |
| People | An expert disagrees with a gap | The gap is marked "disputed" with the expert's reason; nothing is deleted |
| AI | The AI quotes an article that does not exist | Caught by the quote check, shown in red, and the institution is asked to correct it once |
| AI | The AI steps outside its role (a phone company declaring a state of emergency) | Refused by the rules of its role; noted in the logbook |
| AI | A document contains hidden instructions ("ignore your rules") | Documents are treated as information, never as orders |
| AI | Two institutions keep messaging each other without end | A limit on exchanges per event; the drill leader closes the round |
| AI | The AI service is slow or down | Switch to the backup "brain" on the laptop, or replay a recorded drill |
| AI | Answers differ between two runs | Expected to some degree; we measure how stable the gaps are (Q-07) |
| Drill | A power or network cut stops a drill | The drill can resume where it stopped, from the logbook |
| Drill | The same gap appears several times | Merged into one gap with all its evidence |
| Results | A finding is politically sensitive | Written neutrally, about rules and institutions, never people; framed as an opportunity to improve |

### What ALERTE cannot promise

- **Perfect legal answers.** It points to texts and examples; lawyers decide.
- **That every gap is found.** A drill only tests what its story touches. A new story may reveal new gaps.
- **That every gap found is real.** That is why each gap has a confidence level and can be checked by an expert.
- **Real-world procedures it was never told about.** Many Cameroonian procedures are not written publicly. ALERTE marks what it assumes and invites experts to correct it.
- **Predicting what real people will do.** Virtual institutions act on texts and logic; real people also act on habit, fear and politics.

### How we will know ALERTE works

| What we check | How | Target |
| --- | --- | --- |
| The library finds the right text | 40 test questions with known answers; is the right article among the first 5 results? | 8 out of 10 or better |
| Quotes are real | Share of quotes that pass the quote check | 95% or more |
| Planned gaps are found | Share of the gaps the story was designed to reveal that appear in the report | 80% or more |
| Gaps are not invented | A team member and an outside expert review every gap | 85% or more judged real or partly real |
| Results are stable | Same drill run three times | 80% of gaps found in at least two runs |
| The drill is fast enough | Time for a full autopilot drill | Under 20 minutes |
| People understand it | Two people outside the team read a gap report and explain it back | Both explain it correctly |
| Independent agreement | Compare our gaps with those already listed by the Red Cross (IFRC) study of Cameroon's disaster law | Most IFRC gaps related to our story are also found |

# Part 2 — Designing the system

Part 1 said what ALERTE must do. Part 2 turns those needs into **features** (the visible tools of the system), the **information** it handles, the **stages** a drill goes through, and the **screens** people use. It still says nothing about technology.

## 2.1 The feature map

ALERTE has 14 features, grouped by the three moments of a drill, plus a logbook that records everything and a language switch on every screen.

&#91;embedded content: feature map · 3 stages, 14 features, 1 logbook\]

Read it from left to right: what is prepared before a drill feeds the drill itself, whose results are reviewed afterwards; the logbook underneath records all three stages.

| Code | Feature | In one sentence | Requirements it serves |
| --- | --- | --- | --- |
| F-01 | Library | Keeps all documents, cut into passages, each linked to its source | R-01 to R-04 |
| F-02 | Who-does-what map | Lists each institution's powers and duties with the article behind each one | R-05, R-06 |
| F-03 | Story studio | Lets a writer build a crisis story: events, times, recipients, expected gaps | R-07, R-10 |
| F-04 | Control panel | Lets the facilitator set up, start, pause, speed up, stop and surprise | R-09 |
| F-05 | Event dispatcher | Delivers each event to the right inboxes at the right story time | R-07, R-08 |
| F-06 | Seats | One seat per institution, held by a virtual institution or a human player | R-11 to R-13, R-15 |
| F-07 | Coordination room | The shared space where institutions send requests, answers and objections | R-14 |
| F-08 | Legal adviser | Answers legal questions in four parts with sources | R-16 |
| F-09 | Quote checker | Checks that every quoted article really exists in the library | R-20 |
| F-10 | Gap finder | Finds holes in the rules by comparing the story, the decisions and the map | R-17, R-18 |
| F-11 | World examples | Finds how other countries handle each gap | R-19 |
| F-12 | Scorecard | Rates what the drill revealed on the 13 ITU readiness dimensions | R-24 |
| F-13 | Reports and comparisons | Produces the reports, exports them, and compares twins or before/after | R-24 to R-29 |
| F-14 | Logbook and replay | Records everything, detects changes, replays any drill | R-21 to R-23 |
| F-15 | Languages | French and English everywhere, Arabic later | Q-04 |

## 2.2 Each feature in detail

Each feature is described the same way: why it exists, who uses it, what goes in, what comes out, and the rules it follows.

### F-01 Library

- **Why:** institutions can only act on rules they can find and quote.
- **Used by:** knowledge keeper (to fill it); every seat, the legal adviser and the gap finder (to search it).
- **Goes in:** documents with their title, date, link, language, type and reliability (official text, summary, not found).
- **Comes out:** passages that answer a question, each with its document, article and link.
- **Rules:** laws are cut article by article; each passage is tagged with the institutions and topics it concerns; a search by a seat only looks in the documents that institution would use; outdated texts stay but are marked "replaced".
- **Collections:** Cameroon, United Arab Emirates, world examples (EU, Philippines, USA, Japan, Mauritius, African Union and others), ITU standards, and our own fictional story material (always marked fictional).

### F-02 Who-does-what map

- **Why:** to know whether a power exists, who holds it, and on which basis, so that gaps can be found by rule rather than by opinion.
- **Used by:** knowledge keeper and experts (to build and correct it); seats (to know their limits); gap finder (to compare).
- **Goes in:** lines of the form "institution — may / must — action — article — procedure — how sure".
- **Comes out:** for any action, the list of institutions that may or must do it, and what they depend on.
- **Rules:** every line is "written in a text", "deduced from a text" or "assumed (by whom, when)"; no line is deleted, only replaced with a reason.

### F-03 Story studio

- **Why:** so experts can write new crises without help from programmers.
- **Used by:** scenario writers.
- **Goes in:** hazard, places, sectors, the fictional AI's description, and the list of events (story time, recipients, text, expected gaps, failure type).
- **Comes out:** a story ready to play, and a checklist showing whether it covers at least six AI failure types and every planned gap.
- **Rules:** every story is marked fictional; every event has at least one recipient; branches ("if civil protection refuses, then…") are allowed but optional.

### F-04 Control panel

- **Why:** the facilitator is the referee of the drill.
- **Used by:** facilitator.
- **Actions:** choose country, story, language and speed; assign each seat to AI or a human; start, pause, resume, speed up, slow down, stop; inject a surprise event; correct a mistake.
- **Rules:** every action of the facilitator is written in the logbook; nothing can be undone silently.

### F-05 Event dispatcher

- **Why:** in a real crisis, information arrives in pieces, late, and to different people. This is what makes the drill realistic.
- **Goes in:** the story's events and the drill clock.
- **Comes out:** each event delivered, at its story time, into the inbox of its recipients only.
- **Rules:** events can be delayed, partial or wrong if the story says so; an event never leaks into an inbox it was not addressed to.

### F-06 Seats (virtual institutions and human players)

- **Why:** each institution must act with only its own information and its own legal powers.
- **Each seat has:** a role card (who it is, its mission, its powers from the map, its contacts, its language), an inbox, a memory of its own past decisions, and four abilities: search the library, ask the legal adviser, post in the coordination room, record a decision.
- **Every decision contains:** what is known, what is unknown, the options, the choice, the legal basis (or "no legal basis found"), how sure it is, and a short explanation.
- **Human or AI:** any seat can be held by a person; if the person is silent too long, the AI takes over and the switch is recorded.
- **The seats in the Cameroon story:**

| Seat | Plays | Main job in the drill | Prototype |
| --- | --- | --- | --- |
| HydroSense | The fictional AI warning system under test | Gives predictions and draft messages; fails as the story says; answers questions about its confidence and data | Yes |
| Weather | National meteorology service, with the climate observatory (ONACC) | Issues weather warnings; judges the AI's prediction | Yes |
| Civil protection | Civil Protection Directorate, Ministry of Territorial Administration | Decides public alerts and evacuations; activates plans | Yes |
| Phone company | A generic mobile network operator | Can send messages to phones; asks for legal cover | Yes |
| Telecom regulator | Telecommunications Regulatory Board (ART), with the ministry of telecoms | Says what phone companies may or must do | Yes |
| Health | Ministry of Public Health | Leads the cholera response | Yes |
| Data protection | Personal Data Protection Authority (APDP) | Rules on location and health data and on sending data abroad | Yes |
| Local councils | Douala City Council, Far North communes | Local warnings, shelters, schools | Later |
| Cybersecurity | National Agency for Information and Communication Technologies (ANTIC) | Handles fake alerts and fraudulent links | Later |
| Drill leader | Stands for the national crisis committee | Runs each round, routes requests, raises gap alerts, writes the debrief | Yes |

### F-07 Coordination room

- **Why:** institutions must work together, and the way they do it reveals gaps.
- **Five message types:** *Information* (sharing a fact), *Request* (asking someone to act), *Decision* (what I do and why), *Objection* (contesting a decision), *Gap alert* (a missing or unclear rule).
- **Rules:** for each event, seats first assess, then exchange for at most two rounds, then decide; the drill leader closes the round. A request nobody accepts, two seats claiming the same decision, or two contradicting decisions are automatically noted.

### F-08 Legal adviser

- **Why:** the hackathon asks for a "policy and legal adviser" that can be questioned during the crisis.
- **Used by:** any seat, the facilitator, observers.
- **Answer in four parts:** what the national texts say (with articles); what is unclear or missing; how at least two other countries handle it; a suggestion, clearly marked as such.
- **Rules:** the only seat allowed to search the whole library; ends every answer with "for practice only; confirm with a lawyer".

### F-09 Quote checker

- **Why:** the most common AI mistake is inventing laws.
- **What it does:** for every quoted article, checks that the passage exists in the library and contains what is quoted.
- **Rules:** a failed quote is shown in red as "not verified"; the seat is asked once to correct it; the result is recorded either way.

### F-10 Gap finder

- **Why:** this is what ALERTE is for.
- **How it finds a gap:** by applying ten simple rules to the story, the decisions and the map (listed below). A gap is kept only if a rule fires on the map, or a seat found "no legal basis", or the coordination room showed an unanswered request or a conflict.
- **For each gap:** type, seriousness (1 = inconvenience, 2 = delay or extra cost, 3 = risk to life or rights), confidence ("confirmed by text" or "suspected, needs expert check"), the moment it appeared, the texts checked, and the evidence.

| Code | Gap type | Simple rule | Example in Rising Waters |
| --- | --- | --- | --- |
| G1 | Nobody in charge | An action is needed but no institution has the power | Nobody can order phone companies to send alerts |
| G2 | Two in charge | Two institutions hold the same power and no text says who leads | Weather service and civil protection both "warn the population" |
| G3 | No procedure | A power exists but no steps, deadline or form | No time limit to check an AI prediction |
| G4 | Missing piece | A power depends on a text or body that is missing or not ready | Authorisation to send data abroad |
| G5 | Conflicting goals | Two duties pull in opposite directions | Warn everyone fast vs. protect location data |
| G6 | Nobody answers for harm | Harm is possible and no text says who is responsible | Injuries after a false AI alarm |
| G7 | People left out | No duty about languages, disability or people without phones | French-only message, no signal |
| G8 | AI unchecked | AI output used in a public decision with no rule on human checks, records or limits | HydroSense used with broken sensors |
| G9 | Channel unprotected | A channel can be abused and no one must protect it | Fake alert message |
| G10 | Cross-border | Action needs a foreign actor and no agreement exists | Seller's servers abroad |

### F-11 World examples

- **Why:** the hackathon judges value "relevant global policy examples" for each gap.
- **What it does:** for each gap, finds two or three examples from different countries or organisations, preferring binding laws over guidelines, and contexts close to Cameroon's when relevance is equal.
- **Each example says:** country, text, article, what it does, and what would need to change for it to work in Cameroon.
- **Rules:** never two examples from the same country for one gap; if fewer than two good examples exist, it says so.

### F-12 Scorecard

- **What it does:** gives each of the 13 dimensions of the ITU AI Readiness Framework a score from 0 to 5, with the evidence from the drill.
- **Rules:** the score describes what this drill revealed, not an official rating of the country.

### F-13 Reports and comparisons

- **Gives out:** the gap report, the decision timeline, the scorecard, the list of assumptions, and a short summary for decision makers; in French and English.
- **Compares:** two countries on the same story (twins), or the same country before and after a change in the law.

### F-14 Logbook and replay

- **Records:** every event delivered, every search, every AI question and answer, every message, every decision, every quote check, every gap, every facilitator and human action, every error.
- **Protects:** each entry carries a fingerprint linked to the previous one, so any later change breaks the chain and is detected.
- **Replays:** rebuilds any moment of a past drill without calling the AI again.

### F-15 Languages

- Every screen and report in French and English; the story chooses the language of the seats; quotes stay in their original language with a translation if needed; Arabic for the UAE twin later.

## 2.3 The information ALERTE handles

ALERTE works with 16 kinds of information. Some are prepared once and reused (the library, the map, the stories); others are created during each drill (messages, decisions, gaps). None of them contains real personal data.

### Prepared before drills (reused many times)

| Information | What it contains | Linked to |
| --- | --- | --- |
| **Document** | Title, number, date, country, type (law, decree, plan…), language, link, reliability, status (current or replaced) | Its passages |
| **Passage** | A piece of a document (usually one article), its article number, its topics, the institutions it concerns | Its document |
| **Institution** | Name, country, mission, contacts, language | Its powers and duties; its seat |
| **Power or duty** (a line of the map) | What the institution may or must do, the procedure, what it depends on, how sure we are | An institution; the passage that supports it, or the person who assumed it |
| **Story** | Title, hazard, places, sectors, fictional notice, the fictional AI's description | Its events |
| **Event** | Story time, recipients, text, failure type, expected gaps, language | A story |
| **Role card** | What a seat knows about itself at the start | An institution; its powers |
| **World example** | Country, text, article, what it does, fit for Cameroon | A passage in the world collection |

### Created during each drill

| Information | What it contains | Linked to |
| --- | --- | --- |
| **Drill** | Country, story, language, speed, who holds each seat, start and end times, status | Everything below |
| **Seat assignment** | Which institution, held by AI or by which human, switches over time | A drill, an institution |
| **Message** | Type (information, request, decision, objection, gap alert), sender, receiver, text, time | A drill, an event |
| **Decision** | Known, unknown, options, choice, legal basis, confidence, explanation | A seat, an event, the passages it quotes |
| **Quote check** | Quoted article, passage found or not, result | A decision or an answer |
| **Gap** | Type, seriousness, confidence, moment, texts checked, evidence, status (suspected, confirmed, disputed, rejected) | Events, decisions, messages, map lines, world examples |
| **Score** | Dimension, score 0 to 5, evidence | A drill |
| **Logbook entry** | Order number, real time, story time, kind, author, content, fingerprint, previous fingerprint | A drill |

### How the pieces connect, in one chain

A **document** is cut into **passages** → passages support **powers and duties** of **institutions** → a **story** sends **events** to institutions' **seats** → seats exchange **messages** and take **decisions** that quote passages → quotes are **checked** → the gap finder compares decisions and events with the map and creates **gaps** → each gap receives **world examples** → everything is written as **logbook entries**.

### Information rules

- Nothing is ever deleted during or after a drill; corrections are new entries that point to what they correct.
- Every piece created during a drill knows which drill, which event and which seat it belongs to.
- Every statement of law points to a passage, or says plainly that it is an assumption.
- Information meant for one seat is never visible to another seat during the drill; after the drill, everything is visible to the facilitator and auditors.

## 2.4 The life of a drill and of a gap

A drill moves through six stages, and can be paused or interrupted while it runs. A gap starts as suspected and only counts in the final report once a text or an expert supports it.

&#91;embedded content: life of a drill (6 stages + 2 side states) and of a gap (3 stages, 3 outcomes)\]

Only confirmed gaps carry full weight in the report; disputed gaps stay visible with the reason, and rejected gaps are kept in the logbook but left out of the summary.

### What moves a drill from one stage to the next

| Stage | What it means | Moves on when… |
| --- | --- | --- |
| Draft | The facilitator is choosing country, story, seats, language, speed | The facilitator asks ALERTE to check the set-up |
| Ready | All checks passed: library, map and story exist, every seat is assigned | The facilitator presses Start |
| Running | Events arrive, seats decide, the coordination room is active | The last event is handled, or the facilitator stops the drill |
| Paused | The clock is stopped on purpose (questions, coffee, correction) | The facilitator resumes |
| Interrupted | The drill stopped by accident (power or network cut) | Someone resumes it; it restarts from the last logbook entry |
| Finished | No more events; the gap finder, world examples and scorecard run | The facilitator or an expert has looked at the gaps |
| Reviewed | Gaps confirmed, disputed or rejected; report ready | The report is exported and shared |
| Archived | Kept for replay, comparison and research; can no longer change | Never; it is final |

### What happens inside one event (the round)

1. **Delivery.** The event dispatcher puts the event in the inboxes of its recipients only.
2. **Assessment.** Each recipient reads its inbox, searches its allowed documents, and writes what it knows and does not know.
3. **Exchange.** Seats post requests, answers and objections in the coordination room: at most two rounds.
4. **Decision.** Each concerned seat records a decision with its legal basis, or "no legal basis found".
5. **Checks.** The quote checker verifies every article quoted; the drill leader notes unanswered requests, double claims and contradictions.
6. **Closing.** The drill leader closes the round; the clock moves to the next event.

### The life of a gap

| Stage | Meaning |
| --- | --- |
| Suspected | A rule fired, or a seat found no legal basis, or a request went unanswered |
| Confirmed by text | The texts checked clearly show the absence, overlap or conflict |
| Expert review | A lawyer or field expert looks at the gap and its evidence |
| Confirmed | Accepted as real; goes into the report with world examples |
| Disputed | The expert disagrees or is unsure; stays in the report with their reason |
| Rejected | Not a real gap (for example, a text we had missed); kept in the logbook, left out of the summary |

## 2.5 Screens

ALERTE has 11 screens. Each person sees only the screens of their role: a player sees three, the facilitator sees almost all, an observer sees the public view.

| # | Screen | Who sees it | What is on it | What they can do |
| --- | --- | --- | --- | --- |
| 1 | Home | Everyone | The list of drills (draft, running, finished, archived) and the stories available | Open a drill, start a new one, open a replay |
| 2 | Drill set-up | Facilitator | Country, story, language, speed, and one line per seat (AI or a named human) | Choose, check the set-up, start |
| 3 | Control room | Facilitator | Story clock, next events, status of every seat, the coordination room, gap alerts as they appear | Pause, resume, speed up, add a surprise event, correct, stop |
| 4 | My seat | Player | My role card, my inbox (only mine), my past decisions, a decision form | Read events, search my documents, ask another institution, ask the legal adviser, record a decision |
| 5 | Coordination room | Players, facilitator, observers | All messages between institutions, with type and time | Post requests, answers, objections, gap alerts |
| 6 | Legal adviser | Everyone | A question box and four-part answers with sources | Ask, open a source |
| 7 | Public view | Observers, audience | Story clock, events already public, decisions and gaps as they appear; no private inbox | Watch only |
| 8 | Gap report | Facilitator, policy makers, auditors | Gap cards, most serious first, with evidence and world examples | Filter, open sources, mark confirmed, disputed or rejected, export |
| 9 | Scorecard | Everyone after the drill | The 13 readiness dimensions with score and evidence; twins side by side | Open the evidence, export |
| 10 | Replay and check | Auditors, facilitator | A time slider over the whole drill and a "check the logbook" button | Move in time, see what each seat knew, check the logbook |
| 11 | Library and map | Knowledge keeper, scenario writer | Documents with status, the who-does-what map, the story studio | Add documents, accept or correct map lines, write stories |

### The "My seat" screen, in more detail

This is the screen most people will use, often on a phone.

- **Top:** who I am ("Telecom regulator"), the story clock, and the banner "Fictional exercise, not a real alert".
- **Inbox:** newest event on top; unread events in bold; each event shows its story time and sender.
- **Decision form:** five short fields (what I know, what I don't know, my decision, my legal basis, how sure I am) and a "Record" button. A "No legal basis found" button is always visible.
- **Help:** "Search my documents", "Ask another institution", "Ask the legal adviser".
- **History:** my past decisions with their quote checks (green = verified, red = not verified).

### Design rules for every screen

- **Language switch** (French / English) at the top of every screen.
- **"Fictional exercise"** banner always visible.
- **Colours always come with a word**: red "gap" or "not verified", amber "low confidence", green "verified".
- **Large and readable** on a projector for the control room and public view.
- **Works on a phone** for the "My seat" screen.
- **Every legal statement is clickable** and opens the passage and the original document.
- **Plain words** everywhere; technical terms appear only in the word list.

## 2.6 Golden rules, and how the design handles the unexpected

Ten golden rules apply everywhere in ALERTE. Every feature must respect them, and any future change that breaks one of them is refused.

### The ten golden rules

1. **No decision without a basis.** Every decision quotes a text or says "no legal basis found". There is no third option.
2. **No invented law.** Every quoted article is checked against the library; a failed check is shown, never hidden.
3. **Everyone sees only their own inbox.** During a drill, no seat can see what another seat received.
4. **Powers come from the map.** A seat may only claim powers listed for it in the who-does-what map; anything else is recorded as "acting outside its role".
5. **Assumptions are labelled.** Anything not found in a text is marked as an assumption, with who made it and when.
6. **Nothing is erased.** Corrections are added, never substituted; the logbook keeps everything in order and detects changes.
7. **Gaps come from rules and evidence, not opinion.** A gap needs a rule that fires or a recorded fact behind it.
8. **Every gap gets world examples, or says why not.** At least two, from different countries or organisations.
9. **Documents inform; they never command.** Text inside a document is never treated as an instruction to the system.
10. **Fiction stays fiction.** Stories are marked fictional, no real personal data is used, and no individual is named or judged.

### Which feature handles each unusual situation

This table links the situations of section 1.7 to the features that deal with them.

| Situation | Feature in charge | How |
| --- | --- | --- |
| Only a summary of a law exists | F-01 Library | Reliability label "summary" travels with every passage and every answer that uses it |
| A law is missing | F-01, F-10 | Search returns nothing; the seat must answer "no legal basis found"; the gap finder considers G1 or G3 |
| Two texts contradict each other | F-01, F-08, F-10 | Both passages shown, with date and rank; the legal adviser explains; possible G2 or G5 |
| A text was replaced | F-01 | Old passage marked "replaced by…" and excluded from current searches |
| A human player is silent | F-06 Seats | After a set time, the AI takes the seat; switch written in the logbook |
| A player wants another seat's information | F-06, F-05 | Impossible: each seat reads only its own inbox and the shared room |
| Facilitator mistake | F-04 Control panel | Pause and correct; the correction is a new logbook entry |
| Expert disagrees with a gap | F-10, F-13 | Gap marked "disputed" with the reason, still visible |
| The AI invents an article | F-09 Quote checker | Shown in red; one correction request; recorded either way |
| A seat acts outside its role | F-06, F-02 | Compared with the map; recorded as "acting outside its role" |
| Hidden instructions in a document | F-01, F-06 | Golden rule 9; passages are given to seats as quoted material only |
| Endless messaging | F-07 Coordination room | At most two exchange rounds per event; the drill leader closes |
| The AI service fails | F-04, F-14 | Switch to the backup brain, or replay a recorded drill |
| Power or network cut | F-14 Logbook | Drill restarts from its last entry |
| The same gap appears several times | F-10 Gap finder | Merged into one gap; all evidence kept |
| A finding is sensitive | F-13 Reports | Neutral wording rules; institutions named, people never |

## 2.7 What is in the prototype, and what comes later

The prototype submitted on 10 November must show the full chain once, from documents to gap report, on one Cameroon story and its UAE twin. Everything else is designed now but built later.

| Feature | Prototype (by 10 November) | If time allows (before the Dubai final) | After the hackathon |
| --- | --- | --- | --- |
| F-01 Library | Cameroon, UAE and world examples needed by Rising Waters | More Cameroon texts as they are found | Any country; Arabic texts |
| F-02 Who-does-what map | About 50 to 100 checked lines for the story's institutions | Lines confirmed by experts | Maps for other countries |
| F-03 Story studio | Stories written as simple structured files by the team | A simple editing screen | Full editor with branches |
| F-04 Control panel | Start, pause, resume, stop, speed | Surprise events, corrections | Multi-room workshops |
| F-05 Event dispatcher | Full |  |  |
| F-06 Seats | 8 seats played by AI (7 institutions + HydroSense) and the drill leader | Human seat from a computer or a phone, local councils and cybersecurity seats | Any institution, any country |
| F-07 Coordination room | Full, five message types |  |  |
| F-08 Legal adviser | Full |  |  |
| F-09 Quote checker | Full |  |  |
| F-10 Gap finder | Ten gap rules | Expert review screen | Rules tuned per country |
| F-11 World examples | Prepared for the story's gaps, with automatic search |  | Larger world library |
| F-12 Scorecard | 13 dimensions, twins side by side |  |  |
| F-13 Reports | Gap report, timeline, assumptions list; on screen and as a document | PDF export, decision-maker summary | Before/after comparison, real-event rebuild, AI purchase check |
| F-14 Logbook and replay | Full |  |  |
| F-15 Languages | French and English |  | Arabic, local languages for alert messages |
| Stories | Rising Waters (Cameroon) and its UAE twin | AI in health care (X-ray reader) | Landslides, epidemics, droughts, heat, volcano, network outage |

**The test for the prototype:** a judge who knows nothing about Cameroon watches a 10-minute run, opens one decision and sees its source, reads two gap cards with world examples, checks the logbook, and sees the Cameroon and UAE scorecards side by side.

# Part 3 — The system architecture

Part 2 described the rooms; Part 3 describes the structure that holds them: the big building blocks, how they talk, where information lives, and where the walls are. It still names no programming language, product or AI model. Those choices belong to the implementation phase, which must respect this architecture.

## 3.1 Principles and building blocks

ALERTE is made of seven building blocks. The country, the story and the AI model are all things you plug in, not things built into the system, so ALERTE can grow without being rebuilt.

### Eight design principles

1. **Knowledge is separate from the drill.** The library, the map and the stories can be updated without touching the drill engine; a new country is new knowledge, not new software.
2. **One door to the AI.** All blocks reach AI models through a single "AI brain access" block, so the model can be changed, and every AI call is recorded in one place.
3. **Everything goes through the logbook.** No block acts without leaving an entry. This makes checking and replay possible.
4. **Walls between seats.** Each seat can only reach its own inbox and its allowed documents; walls are part of the structure, not left to good behaviour.
5. **Rules before AI.** Where a rule can decide (gap rules, quote checks, delivery of events), a rule decides. AI is used where judgement or language is needed (seats, legal adviser, finding examples).
6. **Works with or without internet.** Every block has a way to run on a single laptop, with a backup AI brain.
7. **Replaceable parts.** Each block can be improved or replaced without changing the others, as long as it keeps the same inputs and outputs.
8. **Fiction by design.** No block accepts real personal data; every output carries the fictional notice.

&#91;embedded content: ALERTE building blocks · 7 blocks, 15 features\]

Requests enter through the doors, flow from drill management to the virtual institutions and on to analysis; the knowledge block and the AI brain serve them from below; the analysis block also reads the knowledge block (the map, the library); and the logbook records everything.

### What each block does

| Block | Contains | Its job | Talks to |
| --- | --- | --- | --- |
| 1. Doors | All screens (F-15 languages applies here) | Show each person only what their role allows; receive their actions | Drill management, institutions, analysis |
| 2. Drill management | F-04, F-05 | Holds the drill's stage and clock; delivers events at the right time to the right seats | Knowledge (stories), institutions, logbook |
| 3. Virtual institutions | F-06, F-07, F-08 | Plays each institution, runs the coordination room, answers legal questions | Knowledge (library, map), AI brain, analysis, logbook |
| 4. Analysis | F-09 to F-13 | Checks quotes, finds gaps, finds world examples, scores and writes reports | Knowledge, AI brain (for examples and summaries), logbook |
| 5. Knowledge | F-01, F-02, F-03 | Keeps documents, passages, the powers map, stories and world examples | Everyone reads it; only knowledge keepers change it |
| 6. AI brain access | (no feature of its own) | The single door to AI models: sends questions, receives answers, chooses main or backup brain, records each call | Institutions, analysis, logbook |
| 7. Logbook and replay | F-14 | Receives an entry from every block, chains them, detects changes, rebuilds any moment | Everyone writes; doors read for replay |

## 3.2 The journey of one event

Following one event from start to finish shows how the blocks work together. The example is event 4 of Rising Waters: at Day 1, 07:10, civil protection asks the phone company to send a message to every phone in Douala.

&#91;embedded content: journey of one event · 6 blocks, 8 steps\]

The highlighted step is where the gap appears: the phone company finds no text obliging it to relay public alerts, says so, and the analysis block turns that statement into a suspected gap.

### The same journey in words

1. **Delivery.** The story clock reaches 07:10 and puts the event into the phone company's inbox only.
2. **Search.** The phone company's seat asks the knowledge block for texts about its duties to relay public alerts. Because of the wall, it only searches the documents a phone company would use (telecom law, regulator decisions, its own licence).
3. **Passages.** The knowledge block returns the closest passages, each with its article and source.
4. **Thinking.** The seat sends its role card, its inbox and the passages through the single AI door.
5. **Proposal.** The AI returns a proposed decision in the fixed form: known, unknown, options, choice, legal basis, confidence.
6. **Quote check.** Every article quoted is checked against the library. Here they are verified, but none creates a duty to send alerts.
7. **Decision and gap alert.** The seat posts its decision in the coordination room ("We send, under protest: no legal basis found") together with a gap alert.
8. **Gap noted.** The analysis block applies its rules: an action was required ("compel the operator to alert") and no institution holds that power. It records gap G1 ("nobody in charge") as suspected, with all the evidence.

In parallel, civil protection's seat receives the reply, and the drill leader notes the outcome before closing the round. Every one of these steps is written in the logbook, so the whole journey can be replayed and checked.

## 3.3 Where information is kept, and the walls

ALERTE keeps information in four separate stores, and decides who may read or change each one by role. The walls between seats are built into the structure, so a seat cannot see another seat's inbox even by mistake.

### The four stores

| Store | What it holds | Shared or per drill | Who may change it |
| --- | --- | --- | --- |
| **Knowledge store** | Documents, passages, the powers map, stories, world examples | Shared by all drills of a country | Knowledge keepers and scenario writers only |
| **Drill store** | One drill's settings, seats, inboxes, messages, decisions, quote checks, gaps, scores | One per drill | The drill blocks while the drill runs; frozen once archived |
| **Logbook** | The chained record of every step of a drill | One per drill | Nobody: entries can only be added, never changed |
| **Report archive** | Exported reports and comparisons | Shared | Facilitators (to add); nobody deletes |

### Who can see and do what

| Role | Knowledge store | Drill store during a drill | Drill store after a drill | Logbook | Reports |
| --- | --- | --- | --- | --- | --- |
| Player (one seat) | Read the documents allowed for my institution | Read my inbox, my decisions and the coordination room; write my decisions and messages | Read all | Read (replay) | Read |
| Virtual institution (AI seat) | Same as a player | Same as a player | Seat closed | Writes through the system only | No access |
| Legal adviser | Read all | Read questions asked to it; write answers | Seat closed | Writes through the system only | No access |
| Facilitator | Read | Read all; control the drill; add surprise events | Read all; confirm, dispute or reject gaps | Read, check | Create, share |
| Observer | No | Read the public view only | Read the report if shared | No | Read if shared |
| Knowledge keeper, scenario writer | Read and change | No | Read | Read | Read |
| Auditor | Read | No | Read all | Read, check | Read |

### The walls in practice

- **Inbox wall.** Each seat has its own inbox; the event dispatcher is the only block that writes into inboxes, and it follows the story's recipient list.
- **Document wall.** Each seat searches the knowledge store through a filter that lists the institutions and countries it may consult. The legal adviser is the only seat without this filter.
- **AI wall.** When a seat thinks through the AI door, it sends only its own role card, inbox and passages. The AI never receives another seat's information in that call.
- **Time wall.** A seat never sees an event before its story time, even if the story file is already complete.
- **Change wall.** Nobody can change a past logbook entry; any attempt breaks the chain of fingerprints and is detected at the next check.

### Safety and privacy by design

- **No real personal data.** Stores accept only fictional story material and public documents; there is no place in the design for real names, numbers, locations or health records.
- **Documents are information, not orders.** Passages reach the AI as quoted material; any instruction they contain is ignored.
- **Every AI exchange is recorded.** What was asked and what was answered, by which brain, at what time.
- **Fictional notice everywhere.** Every output (screen, report, export) carries "Fictional exercise".
- **Respect for licences.** Documents whose licence is unclear are kept as a reference with their link, not copied into shared exports.

## 3.4 How the architecture matches ITU standards

The hackathon judges check two ITU references. ALERTE's seven blocks map directly onto the pipeline of [ITU-T Y.3172](https://www.itu.int/rec/T-REC-Y.3172/en), and its scorecard uses the 13 dimensions of the [ITU AI Readiness Framework](https://www.itu.int/dms_pub/itu-t/opb/ai4g/T-AI4G-AI4GOOD-2025-6-PDF-E.pdf).

### ITU-T Y.3172 in simple words

Y.3172 describes how to organise a machine-learning system as a chain: information comes from **sources**, is **collected**, **prepared**, given to a **model**, checked by **policies**, **distributed**, and used at a **destination**. An **orchestrator** manages the chain, and a **sandbox** lets you test everything safely before real use.

| Y.3172 element | Plain meaning | ALERTE block and feature |
| --- | --- | --- |
| Intent | What the user wants the system to do | Doors and drill management: the drill set-up (country, story, seats) |
| Source | Where information comes from | Knowledge: documents; drill management: story events, simulated sensor readings |
| Collector | Gathers the information | Knowledge: adding documents; drill management: the event dispatcher |
| Pre-processor | Cleans and prepares it | Knowledge: cutting documents into passages, tagging, preparing for search |
| Model | Produces the output | Virtual institutions through the AI brain door; the fictional HydroSense |
| Policy | Rules applied to the output before use | Analysis: quote checker, powers map, gap rules, golden rules |
| Distributor | Sends outputs where needed | Virtual institutions: coordination room and inboxes |
| Destination (sink) | Where outputs are used | Doors (screens), reports, logbook |
| Orchestrator | Manages the whole chain | Drill management: control and drill leader |
| Sandbox | Safe place to test before real use | ALERTE as a whole: AI warning systems are tested here before going live |

### ITU AI Readiness Framework: what the scorecard looks at

| # | Dimension | Question ALERTE asks during the drill |
| --- | --- | --- |
| 1 | Data and model marketplace | Are sensor and warning data shared under clear rules between institutions? |
| 2 | Generated content | Are there safeguards for AI-written warning messages (made-up content, fakes)? |
| 3 | Cross-domain links | Do flood, telecom and health actions connect, for example cholera after floods? |
| 4 | Local context | Are local languages, local warnings and regional realities taken into account? |
| 5 | AI in work processes | Is there a defined step where AI output enters the official warning process? |
| 6 | Human interface | Do warnings reach people through suitable channels (text, broadcast, radio, loudspeakers)? |
| 7 | Strategy alignment | Do institutions coordinate, in line with the national AI strategy? |
| 8 | Working with AI | Do humans check AI predictions, or trust them blindly? |
| 9 | People and skills | Do staff know their role with AI tools? |
| 10 | AI and policies | Is there a legal basis for AI-driven warnings, data use and liability? |
| 11 | AI for inclusion | Are people without phones, signal, literacy or the main language reached? |
| 12 | Priorities | Which use of AI matters most here: predicting, targeting, writing or translating? |
| 13 | Digital infrastructure | Network coverage, broadcast readiness, sensors, energy |

The hackathon also lists eight perspectives (open data and open source, generative AI content, local context, cross-domain integration, human supervision, policy opportunities, social inclusion, digital infrastructure and energy). Each one is covered by at least one dimension above and by at least one gap type in F-10.

## 3.5 Where ALERTE runs, how it grows, and what is left to decide

The same seven blocks must work in four settings, from one laptop with no internet to an online workshop for several countries. Growth (a new country, story, language or seat) happens by adding knowledge, not by changing the blocks.

### Four settings, same architecture

| Setting | Example | What changes | What stays the same |
| --- | --- | --- | --- |
| One laptop, offline | A regional office in Maroua during a network cut; the backup plan on stage in Dubai | All blocks on one machine; backup AI brain; replay of recorded drills | Blocks, rules, logbook, walls |
| One room, one server | A training day with 10 players on phones over the room's network | Doors open to several devices on the same network | Same |
| Online | Players in Yaoundé, Douala and Maroua at the same time | Doors reachable over the internet; main AI brain online | Same |
| Multi-country | A 2027 summit exercise with Cameroon, the UAE and others | One knowledge store per country; twin drills run side by side; comparison reports | Same |

### How ALERTE grows without being rebuilt

| To add… | What you add | Blocks touched |
| --- | --- | --- |
| A new country | Its documents, its powers map, role cards for its institutions | Knowledge only |
| A new story | Its events, its fictional AI description, its expected gaps | Knowledge only |
| A new institution | Its role card and its lines in the powers map | Knowledge only |
| A new language | Translations of screens and reports; documents in that language | Doors and knowledge |
| A new gap rule | One more rule in the gap finder, with its example | Analysis only |
| A new AI model | A new connection behind the AI brain door | AI brain access only |
| A new door (for example a messaging app such as Slack) | A new way for players to receive events and send decisions | Doors only |
| A new report | A new layout fed by the same drill store | Analysis only |

### Following each need from start to finish

This table checks that every important need from Part 1 reaches a feature (Part 2) and a block (Part 3).

| Need (Part 1) | Use cases | Features (Part 2) | Blocks (Part 3) |
| --- | --- | --- | --- |
| Real texts, traceable | UC-01, UC-15 | F-01, F-09 | Knowledge, Analysis |
| Who does what | UC-02 | F-02 | Knowledge |
| Realistic, uneven events | UC-03, UC-06 | F-03, F-05 | Knowledge, Drill management |
| Institutions with their own information and powers | UC-08, UC-09, UC-10 | F-06, F-07 | Virtual institutions, AI brain |
| Legal questions answered | UC-11 | F-08 | Virtual institutions, Knowledge, AI brain |
| Gaps with world examples | UC-14, UC-19 | F-10, F-11 | Analysis, Knowledge |
| Proof and replay | UC-16, UC-17 | F-14 | Logbook |
| Readiness and comparisons | UC-18, UC-21, UC-22 | F-12, F-13 | Analysis |
| Run anywhere | All | F-04 | Drill management, AI brain, Doors |

### Decisions left for the implementation phase

These choices are deliberately not made here. The implementation team makes them, guided by the requirements and principles above.

| Decision | What the architecture requires of it |
| --- | --- |
| Programming language and tools | Must allow the seven blocks to stay separate and replaceable (principle 7) |
| How the library searches by meaning | Must work in French and English, return the article and source, and respect the document wall |
| Which AI models (main and backup) | Must sit behind the single AI door, run offline for the backup, and be allowed by the hackathon rules |
| How the logbook is protected | Must make any change detectable and allow full replay |
| How screens are built | Must work on a projector and a phone, in two languages |
| Where it is hosted | Must support all four settings, including fully offline |
| How the messaging-app door is built (later) | Must respect the inbox wall and record everything in the logbook |

The earlier [ALERTE Project Specification](https://claude.ai/code/artifact/e430f513-a80d-4d2e-a9b0-979f67393e06) contains proposals for each of these decisions; they should be confirmed against this document before building starts.

# Word list and sources

## Word list

| Word | Simple meaning |
| --- | --- |
| AI (artificial intelligence) | Computer programs that do tasks needing judgement or language, such as predicting floods or writing text |
| AI brain | The AI model that the virtual institutions use to read, reason and write |
| AI brain access | The single door through which every block reaches an AI model |
| APDP | Cameroon's Personal Data Protection Authority |
| Architecture | The big building blocks of a system and how they connect, before choosing any tool |
| Assumption | Something we had to suppose because no text says it; always labelled |
| Building block | A large part of the system with one clear job |
| Cell broadcast | Sending one message to every phone in an area at once |
| Coordination room | The shared space where institutions talk to each other during a drill |
| Drill | A practice exercise that plays a crisis without real danger |
| Drill leader | The virtual seat that runs each round, like a crisis committee chair |
| Event (inject) | A piece of news delivered during a drill to some institutions only |
| Facilitator | The person who runs a drill, like a referee |
| Feature | A tool of the system that users can see or use |
| Functional design | The description of features, information and screens, before the architecture |
| Gap | A missing, unclear or conflicting rule or responsibility revealed by a drill |
| HydroSense | The fictional AI warning system in our story |
| Inbox | The place where a seat receives its events and messages |
| ITU | International Telecommunication Union, the United Nations agency for digital technologies, organiser of the hackathon |
| ITU AI Readiness Framework | ITU's method for assessing how ready a country is to use AI, with 13 dimensions |
| Library | All the documents ALERTE knows, cut into passages |
| Logbook | The record of every step of a drill, which cannot be secretly changed |
| Passage | A short piece of a document, usually one article of a law |
| Powers map (who-does-what map) | The list of what each institution may or must do, and which article says so |
| Prototype | The first working version, built for the hackathon |
| Quote check | The automatic check that a quoted article really exists |
| Replay | Rebuilding a past drill step by step without calling the AI again |
| Requirement | A promise of what the system must do or how well |
| Role card | A short description given to a seat: who it is, its powers, its contacts |
| Sandbox | A safe place to test something before using it for real |
| Seat | The place of one institution in a drill, held by AI or by a person |
| Story | A written crisis with its events, times and recipients |
| Twin | The same story played for another country, to compare |
| Use case | One thing a person does with the system to reach one goal |
| Virtual institution | An AI that plays one institution, with only that institution's information and powers |
| Wall | A built-in barrier that stops one seat from seeing another seat's information |
| Y.3172 | An ITU standard describing how to organise a machine-learning system as a chain of steps |

## Sources

Facts in this document come from sources opened on 2 and 3 October 2026; the full list of documents for the library, with links, is in the earlier specification.

- [ITU, AI for Good Lab Hackathon: United Arab Emirates](https://aiforgood.itu.int/event/ai-for-good-sandbox-hackathon-united-arab-emirates/)
- [ITU-T Recommendation Y.3172](https://www.itu.int/rec/T-REC-Y.3172/en)
- [ITU, AI Ready: Analysis Towards a Standardized Readiness Framework](https://www.itu.int/dms_pub/itu-t/opb/ai4g/T-AI4G-AI4GOOD-2025-6-PDF-E.pdf)
- [IFRC, Cameroon: Mapping of International Disaster Response Laws](https://disasterlaw.ifrc.org/sites/default/files/media/disaster_law/2021-10/IDRL_research_Cameroon.pdf)
- [UNICEF Cameroon Floods Flash Update No. 5 (ReliefWeb)](https://reliefweb.int/report/cameroon/unicef-cameroon-floods-flash-update-no-5-far-north-24-october-2024)
- [Gavi, Cholera in Cameroon after the floods](https://www.gavi.org/vaccineswork/cholera-cameroon-when-climate-disaster-unleashes-epidemic)
- [Down To Earth, Mbankolo landslide](https://www.downtoearth.org.in/natural-disasters/landslide-in-cameroon-capital-kills-at-least-30-ministers-blame-residents-for-construction-in-floodplain-region-92223)
- [Gulf News, UAE record rainfall of 16 April 2024](https://gulfnews.com/uae/weather/uae-witnesses-largest-amount-of-rainfall-in-75-years-1.1713319645595)
- [ALERTE Project Specification (earlier document)](https://claude.ai/code/artifact/e430f513-a80d-4d2e-a9b0-979f67393e06)
