# Motor Maintenance Guide

## Overview
Electric motors drive pumps, compressors, conveyors, and fans across industrial facilities.
A structured PM programme minimises unplanned failures and extends motor service life.

## Inspection Intervals
- **Small motors (< 15 kW):** visual inspection monthly; detailed inspection annually.
- **Medium motors (15–75 kW):** visual inspection weekly; detailed inspection semi-annually.
- **Large critical motors (> 75 kW):** visual inspection weekly; detailed inspection quarterly.

## Winding Insulation Testing
- Measure insulation resistance (IR) with a megohmmeter at 500 V DC for motors rated < 1 kV.
- Compare against manufacturer limits; a general guideline is > 1 MΩ per kV of rated voltage
  at minimum, with > 100 MΩ preferred for a healthy winding.
- Polarisation Index (PI = IR at 10 min ÷ IR at 1 min): PI > 2.0 indicates acceptable insulation;
  PI < 1.5 warrants immediate investigation.
- Perform IR tests with the motor de-energised and at roughly stable temperature.

## Vibration Monitoring
- Motor vibration should remain within ISO 10816-3 severity zone A or B for continuous operation.
- Elevated vibration at 1× running speed often indicates rotor imbalance or misalignment.
- Elevated vibration at 2× running speed often indicates misalignment or mechanical looseness.
- Electrical vibration (at 2× line frequency) disappears when power is removed — useful for
  distinguishing electrical from mechanical sources.

## Temperature Limits
- Check nameplate for insulation class: Class F allows 155 °C maximum winding temperature;
  Class H allows 180 °C.
- Operating at 10 °C above the insulation class rating roughly halves insulation life.
- Use RTDs or thermocouples to trend winding and bearing temperatures during operation.

## Lubrication (Motor Bearings)
- Follow manufacturer re-lubrication schedule; over-lubrication is a common cause of bearing
  failure in motors.
- For sealed bearings, replace rather than re-grease when bearing life is reached.
- Record grease type and quantity applied in the maintenance log.

## Coupling and Alignment
- Check shaft alignment at every planned maintenance stop and after any significant thermal
  change or foundation work.
- Angular and parallel misalignment tolerances depend on coupling type; refer to coupling
  manufacturer data.
- Soft-foot must be corrected before final alignment; use a dial indicator at each foot.

## Corrective Actions by Condition
| Condition | Action |
|---|---|
| IR < 1 MΩ per rated kV | Dry out winding or rewind; do not return to service until IR recovers |
| PI < 1.5 | Schedule rewind or replacement within 30 days |
| Vibration in ISO zone C | Schedule planned correction within next maintenance window |
| Vibration in ISO zone D | Immediate shutdown |
| Winding temperature > class limit | Reduce load or improve ventilation; investigate cause |

## Record Keeping
- Log every maintenance action with date, technician ID, findings, and actions taken.
- Track hours run between maintenance events to refine future intervals.
