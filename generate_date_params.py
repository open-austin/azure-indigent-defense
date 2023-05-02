import json
from datetime import date, timedelta
import sys

def daterange(start_date, end_date):
     for n in range(0, int((end_date - start_date).days) + 1, 7):
         yield (start_date + timedelta(n), start_date + timedelta(n + 6))

# create empty list to store dates
datelist = []
# define start and end date for list of dates
end_dt=date.today()
start_dt = end_dt - timedelta(5 * 365)

for dt_tuple in daterange(start_dt, end_dt):
    #print(dt_tuple[0].strftime("%Y-%m-%d"))
    dt_str=(dt_tuple[0].strftime("%Y-%m-%d"), dt_tuple[1].strftime("%Y-%m-%d"))
    datelist.append(dt_str)

with open("logic-app-dates.json", "w") as write_file:
    json.dump(datelist, write_file)