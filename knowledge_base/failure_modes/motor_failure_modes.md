# Motor Failure Modes

## 1. Winding Insulation Breakdown
**Description:** Gradual degradation of winding insulation leading to inter-turn, phase-to-phase,
or phase-to-ground faults.

**Sensor signatures:**
- Declining insulation resistance (IR) trend on periodic megohm tests.
- Polarisation Index (PI) falling below 2.0.
- Partial discharge activity detectable with PD monitoring.
- Elevated winding temperature at the affected coil group.

**Causes:**
- Thermal ageing (cumulative effect of operating above insulation class temperature).
- Moisture ingress causing IR reduction.
- Voltage transients (VFD switching surges, power line disturbances).
- Contamination with oil, dust, or chemicals.
- Mechanical abrasion on coil ends.

**Recommended Action:** Dry out winding if moisture is the cause; apply varnish if minor
tracking is found; rewind if IR < 1 MΩ per kV or PI < 1.5.

---

## 2. Rotor Eccentricity / Broken Rotor Bar
**Description:** A broken or cracked rotor bar causes asymmetric magnetic flux, producing
torque pulsations and heating in adjacent bars.

**Sensor signatures:**
- Sidebands at 1× ± 2sf (where s = slip, f = supply frequency) in the current spectrum (MCSA).
- Torque pulsations visible as speed fluctuations under load.
- Elevated temperature in the rotor.

**Causes:**
- Thermal stress from repeated starts or overloading.
- Casting defects in squirrel-cage rotors.
- Mechanical fatigue from torsional vibration.

**Recommended Action:** Confirm with Motor Current Signature Analysis (MCSA); plan rotor
rewind or rotor replacement at next scheduled outage.

---

## 3. Overheating
**Description:** Sustained operation above the thermal class rating degrades insulation life
exponentially and can cause catastrophic winding failure.

**Sensor signatures:**
- RTD / thermocouple readings exceeding rated class temperature.
- Elevated motor housing temperature detectable by infrared thermography.
- Discolouration or burning odour from enclosure.

**Causes:**
- Overloading beyond nameplate rating.
- Blocked ventilation (dirt-clogged fins, obstructed air inlet).
- High ambient temperature.
- Frequent starts (thermal cycling).
- Single-phasing (one supply phase lost).

**Recommended Action:** Identify and eliminate thermal source. If winding temperature has
exceeded class rating for an extended period, perform full insulation test before return to service.

---

## 4. Shaft Misalignment
**Description:** Angular or parallel misalignment between the motor shaft and the driven
equipment shaft imposes cyclic bending loads and accelerates bearing and coupling wear.

**Sensor signatures:**
- Elevated 1× and 2× running-speed vibration at the motor and driven-end bearing housings.
- High axial vibration relative to radial — often > 50% of radial level indicates angular
  misalignment.
- Coupling wear (rubber elements, grid springs) on inspection.

**Causes:**
- Inadequate alignment at installation.
- Foundation or baseplate settling.
- Differential thermal growth between motor and driven machine.

**Recommended Action:** Correct alignment using laser alignment tools. Re-check after thermal
soak at operating temperature. Replace coupling if worn.

---

## 5. Unbalance
**Description:** Asymmetric mass distribution on the rotor generates a centrifugal force rotating
at running speed, loading bearings and structure.

**Sensor signatures:**
- Dominant 1× running-speed vibration peak in radial direction.
- Vibration amplitude proportional to square of speed.
- Phase angle stable under steady-state conditions.

**Causes:**
- Loss of a balancing weight.
- Accumulated deposits (dust, scale) on rotor.
- Rotor damage (erosion, corrosion).
- Thermal bow causing uneven expansion.

**Recommended Action:** Clean rotor surfaces; perform dynamic balancing in-place or in a
balancing machine; repair or replace damaged rotor sections.
