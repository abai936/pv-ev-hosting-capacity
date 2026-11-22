# R12: NZ export-limit and hosting-capacity context (sources for the website)

All facts below were read from the linked documents on **19 Nov 2026** (checked at that date; the documents may have changed since). They give the New Zealand context for the project. They are about rules and published methods. They are not results of this project, and this project does not implement the Electricity Authority's new assessment method.

## Electricity Authority (EA)
- **Decision paper, "Maximising benefits from local electricity generation (Export limits)", 7 Apr 2026.** A default static export limit of 10 kW for small-scale solar, and a standard export limit assessment method.
  https://www.ea.govt.nz/documents/9545/Decision_paper_-_Maximising_benefits_from_local_electricity_generation.pdf
- **Information sheet for distributors, "Export limits".** Dates: 11 May 2026 (10 kW default); 11 Sep 2026 (all low-voltage generation applications must apply "Australia A" inverter settings); 11 Nov 2026 (assessment methods required for export-limit assessments). It also says network studies "may only consider current hosting capacity and submitted applications", and that the Authority "will consider the benefit of using forecast distributed generation uptake to set export limits in a future policy consultation".
  https://www.ea.govt.nz/documents/9799/Export_limits_-_information_sheet.pdf
- The EA's 10 kW default is a limit **per connection**. This project reports hosting capacity in kW **per solar customer on one phase**. The two are different set-ups: do not compare the numbers.

## Orion (Christchurch lines company)
- **Congestion Management Policy, applicable from 1 Apr 2026 (issued 30 Mar 2026), section 8.** Hosting capacity comes from a load-flow model of each low-voltage network. Export for all distributed-generation customers is raised "in increments of 1 kW per phase" until a voltage or thermal constraint or a 10 kW per phase cap is reached.
  https://www.oriongroup.co.nz/assets/Connections/Orion-Congestion-Management-Policy-1-April-2026.pdf
- This project's method is similar in shape (per phase, load flow, stop at the first limit) but not identical: it bisects to 0.01 kW, tests three placements and uses an assumed cable rating.
