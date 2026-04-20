from app.schemas.record import StructuredClinicalData


class MedicationValidatorService:
    def __init__(self) -> None:
        self.known_drugs = {
            "acetaminophen": "paracetamol",
            "paracetamol": "paracetamol",
            "crocin": "paracetamol",
            "dolo": "paracetamol",
            "ibuprofen": "ibuprofen",
            "combiflam": "ibuprofen",
            "amoxicillin": "amoxicillin",
            "azithromycin": "azithromycin",
            "metformin": "metformin",
            "cetirizine": "cetirizine",
            "omeprazole": "omeprazole",
        }

    def normalize(self, structured_data: StructuredClinicalData) -> StructuredClinicalData:
        normalized: list[str] = []
        seen: set[str] = set()

        for medication in structured_data.medications:
            candidate = medication.strip()
            if not candidate:
                continue

            lookup = candidate.lower().replace("tablet", "").replace("tab", "").strip()
            canonical = self.known_drugs.get(lookup, candidate.lower().title())
            if canonical.lower() in seen:
                continue
            seen.add(canonical.lower())
            normalized.append(canonical)

        structured_data.medications = normalized
        return structured_data

