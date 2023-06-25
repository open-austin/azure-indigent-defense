import json
import datetime as dt


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
    charge_dict["primary_charge_date"] = dt.datetime.strftime(
        charge_datetime, "%Y-%m-%d"
    )
    # Umichigan mapping
    charge_dict.update(charge_name_to_umich[charge["charges"]])

    out_file["charges"].append(charge_dict)
out_file["earliest_charge_date"] = dt.datetime.strftime(min(charge_dates), "%Y-%m-%d")
# Original Format
out_filepath = "josh_scratch/cleaned_case_output_scriptresults.json"
with open(out_filepath, "w") as f:
    json.dump(out_file, f)
