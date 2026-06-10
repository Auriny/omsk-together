from enums import LabelsEnum

_labels = {
    LabelsEnum.EMERGENCY: 5,
    LabelsEnum.CRITICAL: 4,
    LabelsEnum.SERIOUS: 3,
    LabelsEnum.MODERATE: 2,
    LabelsEnum.SMALL: 1
}

def convert_diff_str_to_int(item: LabelsEnum) -> int:
    return _labels[item]
