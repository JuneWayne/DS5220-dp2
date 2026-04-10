# DS5220-dp2: Charlottesville Weather Tracker

## Data Source
This weather tracker app fetches hourly temperature, wind speed, precipitation, and cloud cover for CHarlottesville specifically at 38.03N, 78.48W from the Open Meteo API. Open Meteo is a free API, does not require a secret access key, and provides real-time weather data from high resolution NOAA weather models.

### Why did I choose this data?
As Spring and early summer approaches, weather around UVA and in Charlottesville seems to be stagnant in a 'winter' mode. With occasional snow, freezing wind, and cold temperature in general, I believe it is worth investigating and monitoring the weather trends of Charlottesville to see when would this college town finally enter a 'warmer spring' and 'cool summer' mode.

---

## What did you observe in the data?
- The weather for this week has been fluctuating, albeit depicting an upward trend starting from wednesday. The daily weather is often the coldest early in the morning at around 6am and hottest in the early afternoons at around 2 to 3pm. The hottest spike of the temperature occurs on this Friday, and given this trend, I believe the temperature should continue to rise and maintain at a steady warm temperature starting next week. 
- I was surprised at how wind speed seems to be at its lowest on Thursday's early morning. And how it immediately starts to get sped up as the day starts where everyone has to go out for classes and work. Quite an irony from my personal perspective in how the wind speed seem to only grow during working hours. Nevertheless, the wind speed did started to grow continuously over the next few days as the temperature grew alongside with it. 
- Cloud coverage seemed to have peaked over the late evening on wednesday and continued to fluctuate with occasional spikes on mid thursday. I wonder if its simply a group of traveling cloud passing by Charlottesville.
- Sadly, there are no precipitation over this week so I wasn't able to capture and patterns, had I set this monitoring app earlier last week, large volumes of precipitation would have been captured. 

---

## Scheduled Process
A Kubernetes CronJob that isi running on an AWS EC2 instance executets a containerized Python script every 30 minutes. On each execution, the script fetches current weather conditions from the Open-Meteo API. It then writes a record (marked with timestamp) to a DynamoDB table, queries the full history of the table's record, and generates the visualization onto the static S3 bucket website. 

---

## Output
- **`plot.png`**: a side by side time series visualization showing temperature (in Fahrenheit), wind speed (in miles per hour), cloud cover (in percentage), and precipitation (in inches) over all the timestamps it has collected. The visualization updated every 30 minutes.
- **`data.csv`** — a CSV file containing all accumulated observations with columns: `timestamp`, `temperature_f`, `wind_speed_mph`, `precipitation_in`, `cloud_cover_pct`. The CSV is also available on the S3 static website. 

---

## How your CronJob pods gain permission to read/write to AWS services without credentials appearing in any file?
The EC2 instance has an IAM role attached to it at the launch of the instance. This role allows AWS to automatically expose temporary credentials to anything running on that instance. When a CronJob pod runs, boto3 automatically calls the IMDS endpoint to retrieve temporary credentials. The IAM role that I defined dictates which DynamoDB and S3 actions are permitted, so the pod only inherits these minimally required permissions.

## One thing you'd do differently for a real production system?
I would probably add better error handling and alert mechanisms around the CronJob to counter situations of which the Open Meteo API is down. Currently, the pod will continue to run forever even if the API is down and the service would just be wasting money. I would probably implement CloudWatch alarms so I would be notified if the API goes wrong. 