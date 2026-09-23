# 01 — Business Rules

> Source documents: the assessment brief, the company's blank *Drivers Daily Log* template, and FMCSA's
> *Interstate Truck Driver's Guide to Hours of Service* (2022). Page numbers (p.X) refer to that guide.
> Rule IDs (R-xx) and assumption IDs (A-xx) are referenced by code comments, tests and the plans in **both** repos.
>
> **This is the canonical copy.** It lives in `eld-trip-planner-api` because the rules are enforced here (`hos/`).
> The web repo links to it and must not keep its own copy.

---

## 1. The product in one paragraph

A trip planner for a truck driver. You enter **where the truck is now**, **where to pick up the load**,
**where to drop it off**, and **how many hours the driver has already worked this cycle**. The app works out
a **legal** plan — when to drive, when to take breaks, when to fuel, when to sleep — shows it on a **map**,
and fills in the driver's **daily log sheets** (the legally required record of every hour), one sheet per day.

## 2. Why it exists (goal)

US law limits how long a truck driver may drive and work so tired drivers don't cause crashes, and every
driver must record every hour of every day. Planning a legal multi-day trip and drawing those logs by hand
is slow and error-prone.

**Product goal:** trip details in → a plan that obeys the Hours-of-Service rules + correctly completed logs out.

**Assessment goal:** prove you can turn written regulations into correct code and wrap it in an app that
looks and feels good. Graders test accuracy on the hosted app; good UI/UX can compensate for small inaccuracies.

---

## 3. Glossary

### People, places, paperwork

| Term | Plain meaning |
|---|---|
| **FMCSA** | US federal agency that writes trucking safety rules. |
| **HOS (Hours of Service)** | The rules limiting how long a driver may drive and work. |
| **CMV** | Commercial Motor Vehicle — the truck. |
| **Property-carrying driver** | Hauls goods, not passengers. Our driver type. |
| **Carrier** | The trucking company the driver works for. |
| **Main office** | The carrier's headquarters address (city + state is enough, p.16). |
| **Home terminal** | The driver's home base. **All log times use its time zone**, even across time zones (p.16). |
| **Shipping documents** | The load's paperwork number (e.g. manifest / bill of lading), *or* shipper name + commodity. |

### The log

| Term | Plain meaning |
|---|---|
| **Log / Driver's Daily Log / RODS** | Record of Duty Status: one page = one calendar day (midnight → midnight). |
| **ELD** | Electronic Logging Device — the digital version of the log. We produce the paper-style version. |
| **Graph grid** | The 24-hour chart with 4 rows and 15-minute ticks. A single continuous line shows the driver's status all day. |
| **Remarks** | Section under the grid. At every change of duty status: **city/town + state** and why (p.17). |
| **Total hours** | The number to the right of each grid row. The four totals must add up to **24** (p.16). |
| **Recap** | Bottom block: hours on duty today, hours used in the last 7 / 5 days, hours available tomorrow. |

### The four duty statuses (the four grid rows)

| Row | Status | Code | Examples |
|---|---|---|---|
| 1 | **Off duty** | `OFF` | Free time, meal off-duty, 30-min break, 34-hr restart, time before/after the trip |
| 2 | **Sleeper berth** | `SB` | Resting in the truck's bunk — our 10-hr overnight rests |
| 3 | **Driving** | `D` | Behind the wheel, truck moving |
| 4 | **On duty (not driving)** | `ON` | Loading, unloading, fueling, inspections, paperwork (p.5) |

### The limits

| Term | Plain meaning |
|---|---|
| **Shift / 14-hour window** | Starts the moment the driver begins **any** work after 10+ hours off. After 14 hours have passed, no more driving. Breaks do **not** pause it. |
| **11-hour driving limit** | Max 11 hours of driving inside a shift. |
| **30-minute break** | After 8 hours of (cumulative) driving, 30 consecutive minutes not driving are required. |
| **10-hour reset** | 10 consecutive hours off duty and/or sleeper berth. Starts a fresh shift (new 11 and 14). |
| **Cycle / 70-hour/8-day limit** | Max 70 hours **on duty** (driving + on-duty) in any rolling 8 days. The driver's "weekly budget". |
| **Current cycle used** | Hours of that 70-hour budget already spent — an input. |
| **34-hour restart** | 34 consecutive hours off duty/sleeper. Resets the cycle to 0 (full 70 available). |
| **Pre-trip / post-trip inspection** | Checking the truck before / after driving. On-duty time. |

### Map terms

| Term | Plain meaning |
|---|---|
| **Leg** | One part of the trip. Leg 1: current → pickup. Leg 2: pickup → dropoff. |
| **Geocoding / reverse geocoding** | Address → coordinates / coordinates → "City, ST". |
| **HGV routing** | Heavy-goods-vehicle (truck) routing profile. |
| **Mile marker** | Distance along the route from the trip start, used to place stops on the map. |

---

## 4. Hours-of-Service rules (what the engine enforces)

| ID | Rule | Guide |
|---|---|---|
| **R-01** | **11-hour driving limit.** At most 11 hours of driving per shift. Then driving stops until a 10-hr reset. | p.6 |
| **R-02** | **14-hour window.** The shift starts at the first on-duty or driving minute after a 10-hr reset. No **driving** after 14 hours have elapsed since shift start. Off-duty time inside the window does **not** extend it. On-duty (not driving) work **is allowed** after the 14th hour. | p.6, p.18 |
| **R-03** | **30-minute break.** After **8 cumulative hours of driving** since the last qualifying break, the driver must have **30 consecutive minutes not driving** before driving again. Any non-driving status qualifies (OFF, SB, ON); consecutive non-driving periods combine (e.g. 15 ON + 15 OFF). | p.10 |
| **R-04** | **70-hour / 8-day limit.** No **driving** once on-duty hours (D + ON) in the cycle reach 70. On-duty work is still allowed. A **34-hr restart** (34 consecutive hours OFF/SB) resets the cycle to 0. | p.10–11 |
| **R-05** | **10-hour reset.** 10 consecutive hours OFF and/or SB resets R-01 and R-02 (new shift). | p.6–7 |
| **R-06** | **Fueling** at least once every **1,000 miles** driven. Each fuel stop = **30 min ON**. | brief |
| **R-07** | **Pickup = 1 hr ON**, **dropoff = 1 hr ON**. | brief |
| **R-08** | **One log per calendar day**, midnight → midnight in the **home-terminal time zone**. The four row totals must equal **exactly 24.00 hrs**. | p.15–16 |
| **R-09** | **Remarks at every change of duty status**: city/town + state abbreviation (or highway + nearest city when not in a town) and a short reason. | p.17 |
| **R-10** | **Multi-day trips produce multiple log sheets**, one per calendar day the trip touches (padded with OFF before start / after finish). | brief, p.15 |
| **R-11** | **Every required log field is filled**: date, from/to, total miles driving today, total mileage today, truck/trailer numbers, carrier name, main office address, home terminal address, shipping document(s), remarks, recap. | p.15–16, template |
| **R-12** | **Recap (70-hr/8-day)**: on-duty today (lines 3 + 4); **A** = on-duty last 7 days incl. today; **B** = 70 − A (available tomorrow); **C** = on-duty last 5 days incl. today. After a 34-hr restart, 70 is available again. | template, p.11 |

### Derived-counter rules (how the engine tracks the clocks)

The engine never "decides" a rest resets something because of *why* it was taken. It **derives** resets from
the timeline:

- A consecutive non-driving stretch **≥ 30 min** → resets the 8-hr driving-since-break counter (R-03).
- A consecutive OFF/SB stretch **≥ 10 h** → new shift: resets driving-in-shift (R-01) and the 14-hr window (R-02).
- A consecutive OFF/SB stretch **≥ 34 h** → cycle used = 0 (R-04).

This makes fuel stops and pickups count as breaks automatically, which the guide allows.

---

## 5. Assumptions and product decisions

| ID | Assumption / decision | Why |
|---|---|---|
| **A-01** | Property-carrying driver, **70 hr / 8 day** cycle, solo driver. | Brief |
| **A-02** | **No adverse driving conditions** exception; **no sleeper-berth split**; no short-haul exceptions. | Brief; keeps scope tight — documented as out of scope |
| **A-03** | Driver starts the trip **rested** (≥10 h off before the start time) and with a **full tank** at the current location. | A trip planner can't know the prior shift; this is the standard planning assumption |
| **A-04** | **Current cycle used is treated as not rolling off during the trip.** We only receive one number, not per-day history, so we don't know which hours drop off. This is the conservative (never illegal) choice. Stretch: optional `prior_daily_hours[7]` enables true rolling math. | Safety > optimism |
| **A-05** | If cycle used ≥ 70 at start, the plan begins with a 34-hr restart. | R-04 |
| **A-06** | **Pre-trip inspection 15 min ON** at the start and **post-trip inspection 15 min ON** at the end. On by default, toggleable. | Guide's completed example includes inspections; realistic logs |
| **A-07** | **10-hr resets are logged as Sleeper Berth (row 2).** 30-min breaks and 34-hr restarts are logged **Off Duty (row 1)**. | Typical long-haul behavior; uses all four grid rows |
| **A-08** | **Driving speed** per leg = routing distance ÷ routing duration (truck profile). Driving time per leg is **rounded up** to the next 15 min. | Realistic, and aligns with the 15-min grid |
| **A-09** | **Fuel timing** is rounded **down** to 15 min, so fuel stops happen at or before 1,000 mi, never after. Fuel is not taken at pickup/dropoff. | R-06 compliance |
| **A-10** | **All times are whole 15-minute units.** | Paper grid resolution (p.16) |
| **A-11** | **Trip start time** is an input (default: next quarter-hour, now). Time zone = home terminal; default = time zone of the current location. | R-08 |
| **A-12** | **Tie-break when several limits hit at the same moment:** do fuel first (if due), then the single longest rest needed (34 h > 10 h > 30 min). A longer rest satisfies the shorter ones. | Minimizes stops, stays legal |
| **A-13** | **Total mileage today = total miles driving today** (single truck, no unloaded moves). | Template has both fields |
| **A-14** | **Recap A and C** include the full starting cycle-used hours (A-04), then add trip on-duty hours per day; both reset after a 34-hr restart. | Conservative, consistent with A-04 |
| **A-15** | Log header fields the planner can't know (driver name, carrier, truck/trailer #, shipping doc) come from an optional **"Log details"** form with demo defaults. | R-11 |

---

## 6. Which duty status each activity uses

| Activity | Status (row) | Duration | Rule |
|---|---|---|---|
| Before trip start / after trip end | OFF (1) | pad to midnight | R-08, R-10 |
| Pre-trip inspection | ON (4) | 15 min | A-06 |
| Driving a leg | D (3) | from routing | A-08 |
| Pickup (loading) | ON (4) | 1 h | R-07 |
| Fueling | ON (4) | 30 min | R-06 |
| 30-minute break | OFF (1) | 30 min | R-03 |
| 10-hour reset | SB (2) | 10 h | R-05, A-07 |
| 34-hour restart | OFF (1) | 34 h | R-04 |
| Dropoff (unloading) | ON (4) | 1 h | R-07 |
| Post-trip inspection | ON (4) | 15 min | A-06 |

---

## 7. Scheduling algorithm (plain-English version)

Repeat until the leg is fully driven:

1. Work out **how long the driver may keep driving right now** — the smallest of:
   remaining leg time · 11 h − driving in shift · 14 h − time since shift start · 8 h − driving since break ·
   70 h − cycle used · time until 1,000 mi since last fuel.
2. **Drive** that long (if > 0).
3. Whichever limit was hit decides the stop: leg end → next activity · fuel → fuel stop · 8-h → 30-min break ·
   11/14 → 10-h reset · 70 → 34-h restart. Apply the A-12 tie-break.

Trip order: *(34-h restart if cycle full)* → pre-trip → leg 1 → pickup → leg 2 → dropoff → post-trip.
Then split the timeline at each home-terminal midnight into daily logs, pad with OFF, compute totals and recap.

---

## 8. Worked example (the reference scenario `SC-2`, see `04-testing-strategy.md`)

**Inputs:** start 06:00, cycle used 20 h. Leg 1: 120 mi / 2 h. Leg 2: 1,080 mi / 18 h (avg 60 mph).

| Time | Event | Status | Why |
|---|---|---|---|
| **Day 1** 00:00–06:00 | Before trip | OFF | R-10 |
| 06:00–06:15 | Pre-trip inspection — **shift starts** | ON | A-06, R-02 |
| 06:15–08:15 | Drive leg 1 (120 mi) | D | |
| 08:15–09:15 | Pickup — also a qualifying break | ON | R-07, R-03 |
| 09:15–17:15 | Drive 8 h (480 mi) — 8-h break limit hit | D | R-03 |
| 17:15–17:45 | 30-min break | OFF | R-03 |
| 17:45–18:45 | Drive 1 h (60 mi) — 11-h limit hit | D | R-01 |
| 18:45–24:00 | 10-hr reset (starts) | SB | R-05, A-07 |
| **Day 2** 00:00–04:45 | 10-hr reset (ends) | SB | |
| 04:45–10:15 | Drive 5.5 h (330 mi) — 990 mi since start, next 15 min would pass 1,000 | D | R-06, A-09 |
| 10:15–10:45 | Fuel — also a qualifying break | ON | R-06 |
| 10:45–14:15 | Drive 3.5 h (210 mi) — leg complete | D | |
| 14:15–15:15 | Dropoff | ON | R-07 |
| 15:15–15:30 | Post-trip inspection | ON | A-06 |
| 15:30–24:00 | After trip | OFF | R-10 |

**Expected daily totals (hrs):**

| Sheet | OFF | SB | D | ON | Total | Miles |
|---|---|---|---|---|---|---|
| Day 1 | 6.50 | 5.25 | 11.00 | 1.25 | **24** | 660 |
| Day 2 | 8.50 | 4.75 | 9.00 | 1.75 | **24** | 540 |

**Recap:** Day 1 on-duty 12.25 → A = 32.25, B = 37.75. Day 2 on-duty 10.75 → A = 43.00, B = 27.00.

## 9. Golden reference: the guide's "John Doe" log (p.18–19)

Richmond, VA → Newark, NJ. Used as a golden test for the log builder and grid renderer.

| From | To | Status | Remark |
|---|---|---|---|
| 00:00 | 06:00 | OFF | |
| 06:00 | 07:30 | ON | Richmond, VA — reported, loaded, pre-trip |
| 07:30 | 09:00 | D | |
| 09:00 | 09:30 | ON | Fredericksburg, VA — fueled |
| 09:30 | 12:00 | D | |
| 12:00 | 13:00 | OFF | Baltimore, MD — lunch |
| 13:00 | 15:00 | D | |
| 15:00 | 15:30 | ON | Philadelphia, PA — delivery |
| 15:30 | 16:00 | D | |
| 16:00 | 17:45 | SB | Cherry Hill, NJ — sleeper berth |
| 17:45 | 19:00 | D | |
| 19:00 | 21:00 | ON | Newark, NJ — post-trip, paperwork |
| 21:00 | 24:00 | OFF | |

**Totals:** OFF 10 · SB 1.75 · D 7.75 · ON 4.5 = **24**. Note John is on duty past the 14th hour — legal, because he doesn't *drive* after it (R-02).

---

## 10. Edge cases the engine must handle

| Case | Expected behavior |
|---|---|
| Cycle used = 70 at start | 34-h restart first (A-05) |
| Cycle used high (e.g. 65) on a long trip | 34-h restart inserted mid-trip when 70 is reached |
| 14-h window expires during pickup/dropoff | Work continues (ON allowed); rest before next driving |
| A leg longer than 1,000 mi | Multiple fuel stops |
| Current location = pickup | Leg 1 has 0 miles; no driving, pickup immediately |
| Rest crosses midnight | Split across two sheets; each sheet still totals 24 |
| Several limits hit simultaneously | A-12 tie-break; never two back-to-back rests |
| Cross-country (~2,800 mi) | 4+ sheets, multiple fuel stops and resets, all rules hold |
| Unroutable address | Clear user-facing error, no crash |
| Cycle used < 0 or > 70, missing location | Validation error on the form and API |

## 11. Out of scope (state in README)

Sleeper-berth split provisions · adverse driving conditions · 16-hour short-haul and other exceptions ·
60-hr/7-day cycle · team drivers · personal conveyance / yard moves · driver accounts / auth · ELD data transfer.
