import json
import datetime as dt

# List of motions identified as evidenciary
good_motions = [
    "Motion To Suppress",
    "Motion to Reduce Bond",
    "Motion to Reduce Bond Hearing",
    "Motion for Production",
    "Motion For Speedy Trial",
    "Motion for Discovery",
    "Motion In Limine",
]

# Original Format
in_file = "josh_scratch/case_input_multicharge.json"
with open(in_file, "r") as f:
    input_dict = json.load(f)

# Get mappings of charge names to umich decsriptions
charge_name_to_umich_file = "josh_scratch/charge_name_to_descs.json"
with open(charge_name_to_umich_file, "r") as f:
    charge_name_to_umich = json.load(f)

# Cleaned Case Primary format
out_file = {}
out_file["case_number"] = input_dict["code"]
out_file["attorney_type"] = input_dict["party information"]["appointed or retained"]

# Create charges list
charge_dates = []
out_file["charges"] = []
for i, charge in enumerate(input_dict["charge information"]):
    charge_dict = {
        "charge_id": i,
        "charge_level": charge["level"],
        "orignal_charge": charge["charges"],
        "statute": charge["statute"],
        "is_primary_charge": i == 0,  # True if this is the first charge
    }
    charge_datetime = dt.datetime.strptime(charge["date"], "%m/%d/%Y")
    charge_dates.append(charge_datetime)
    charge_dict["charge_date"] = dt.datetime.strftime(charge_datetime, "%Y-%m-%d")
    # Umichigan mapping
    charge_dict.update(charge_name_to_umich[charge["charges"]])

    out_file["charges"].append(charge_dict)
out_file["earliest_charge_date"] = dt.datetime.strftime(min(charge_dates), "%Y-%m-%d")


def contains_good_motion(motion, event):
    """Recursively check if a motion exists in an event list or sublist."""
    if isinstance(event, list):
        return any(contains_good_motion(motion, item) for item in event)
    return motion.lower() in event.lower()


# Iterate through every event and see if one of our "good motions" is in it
motions_in_events = [
    motion
    for motion in good_motions
    if contains_good_motion(motion, input_dict["other events and hearings"])
]
out_file["motions"] = motions_in_events
out_file["has_evidence_of_representation"] = len(motions_in_events) > 0


# Original Format
out_filepath = "josh_scratch/cleaned_case_output_scriptresults.json"
with open(out_filepath, "w") as f:
    json.dump(out_file, f)
