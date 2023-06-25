import csv
import json

# Create mapping file

uccs_filepath = "josh_scratch/uccs_schema.csv"
name_to_uccs_filepath = "josh_scratch/results.csv"
json_outpath = "josh_scratch/charge_name_to_descs.json"
with open(uccs_filepath, mode="r") as file:
    # reading the CSV file
    csvFile = csv.DictReader(file)

    # create a dictionary
    uccs_to_descriptions = {
        row["uccs_code"]: {
            "charge_desc": row["charge_desc"],
            "offense_category_desc": row["offense_category_desc"],
            "offense_type_desc": row["offense_type_desc"],
        }
        for row in csvFile
    }

with open(name_to_uccs_filepath, mode="r") as file:
    # reading the CSV file
    csvFile = csv.DictReader(file)

    # create a dictionary
    charge_name_to_descs = {
        row["charge_name"]: uccs_to_descriptions[row["uccs_code"]] for row in csvFile
    }

with open(json_outpath, "w") as f:
    json.dump(charge_name_to_descs, f)
