import json
import datetime as dt

# Original Format
in_file = "josh_scratch/case_input.json"
with open(in_file, "r") as f:
    input_dict = json.load(f)

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
    # TODO: is_primary_charge, num_counts, umichigan mapping
    out_file["charges"].append(charge_dict)
out_file["earliest_charge_date"] = dt.datetime.strftime(min(charge_dates), "%Y-%m-%d")
# Original Format
out_filepath = "josh_scratch/cleaned_case_output.json"
with open(out_filepath, "w") as f:
    json.dump(out_file, f)
