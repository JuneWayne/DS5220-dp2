import os
import json
import boto3
import requests
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from datetime import datetime, timezone
from decimal import Decimal
import seaborn as sns

# Configuration
LOCATION = "Charlottesville, VA"
LAT = 38.0293
LON = -78.4767
TABLE_NAME = os.environ.get("DYNAMODB_TABLE", "cville-weather")
S3_BUCKET = os.environ.get("S3_BUCKET", "")
REGION = os.environ.get("AWS_REGION", "us-east-1")

# Clients 
dynamodb = boto3.resource("dynamodb", region_name=REGION)
table = dynamodb.Table(TABLE_NAME)
s3 = boto3.client("s3", region_name=REGION)


def fetch_weather():
    """
    Fetch current weather data for Charlottesville, VA from Open-Meteo API.
    returns a dict with temperature (°F), wind speed (mph), precipitation (in), cloud cover (%), and API timestamp.
    """
    url = (
        "https://api.open-meteo.com/v1/forecast"
        f"?latitude={LAT}&longitude={LON}"
        "&current=temperature_2m,wind_speed_10m,precipitation,cloud_cover"
        "&temperature_unit=fahrenheit"
        "&wind_speed_unit=mph"
        "&precipitation_unit=inch"
        "&timezone=America%2FNew_York"
    )
    resp = requests.get(url, timeout=10)
    resp.raise_for_status()
    data = resp.json()
    current = data["current"]
    return {
        "temperature_f": current["temperature_2m"],
        "wind_speed_mph": current["wind_speed_10m"],
        "precipitation_in": current["precipitation"],
        "cloud_cover_pct": current["cloud_cover"],
        "api_time": current["time"],
    }


def write_to_dynamo(record):
    """
    Write a weather record to DynamoDB. The partition key is the location, and the sort key is the timestamp.
    """
    item = {
        "location": LOCATION,
        "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "temperature_f": Decimal(str(record["temperature_f"])),
        "wind_speed_mph": Decimal(str(record["wind_speed_mph"])),
        "precipitation_in": Decimal(str(record["precipitation_in"])),
        "cloud_cover_pct": Decimal(str(record["cloud_cover_pct"])),
        "api_time": record["api_time"],
    }
    table.put_item(Item=item)
    return item


def load_history():
    """
    Load all weather records for the location from DynamoDB, sorted by timestamp ascending.

    """
    resp = table.query(
        KeyConditionExpression=boto3.dynamodb.conditions.Key("location").eq(LOCATION),
        ScanIndexForward=True,
    )
    return resp["Items"]


def generate_plot(history, out_path="/tmp/plot.png"):
    # Convert timestamps to US eastern timezone for plotting
    import zoneinfo
    ET = zoneinfo.ZoneInfo("America/New_York")
 
    timestamps = [
        datetime.strptime(r["timestamp"], "%Y-%m-%dT%H:%M:%SZ")
        .replace(tzinfo=timezone.utc)
        .astimezone(ET)
        for r in history
    ]
    temps = [float(r["temperature_f"]) for r in history]
    winds = [float(r["wind_speed_mph"]) for r in history]
    clouds = [float(r["cloud_cover_pct"]) for r in history]
    precip = [float(r["precipitation_in"]) for r in history]
 
    sns.set_theme(style="whitegrid")
    fig, axes = plt.subplots(4, 1, figsize=(12, 10), sharex=True)
    fig.suptitle(
        f"Charlottesville, VA Weather Tracker\n({len(history)} observations)",
        fontsize=14,
        fontweight="bold"
    )
    # temperature 
    sns.lineplot(x=timestamps, y=temps, ax=axes[0], color="#e05c2e", linewidth=1.5)
    axes[0].fill_between(timestamps, temps, alpha=0.15, color="#e05c2e")
    axes[0].set_ylabel("Temperature (°F)")
    
    # wind speed
    sns.lineplot(x=timestamps, y=winds, ax=axes[1], color="#2e7de0", linewidth=1.5)
    axes[1].fill_between(timestamps, winds, alpha=0.15, color="#2e7de0")
    axes[1].set_ylabel("Wind Speed (mph)")
    
    # cloud cover
    sns.lineplot(x=timestamps, y=clouds, ax=axes[2], color="#555555", linewidth=1)
    axes[2].fill_between(timestamps, clouds, alpha=0.4, color="#888888")
    axes[2].set_ylabel("Cloud Cover (%)")
    axes[2].set_ylim(0, 100)
    
    # precipitation (bar plot since precipitation is a sum of the hourly output, not instantenous)
    sns.barplot(x=timestamps, y=precip, ax=axes[3], color="#4ab8c1", native_scale=True)
    axes[3].set_ylabel("Precipitation (in)")
 
    for ax in axes:
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%m/%d %H:%M", tz=ET))
        ax.set_xlabel("")
 
    plt.xticks(rotation=30, ha="right")
    plt.tight_layout()
    plt.savefig(out_path, dpi=150, bbox_inches="tight")
    plt.close()
    print(f"Plot saved to {out_path}")

def generate_csv(history, out_path="/tmp/data.csv"):
    """
    Write all accumulated records to a CSV file for download
    """
    with open(out_path, "w") as f:
        f.write("timestamp,temperature_f,wind_speed_mph,precipitation_in,cloud_cover_pct\n")
        for r in history:
            f.write(
                f"{r['timestamp']},"
                f"{r['temperature_f']},"
                f"{r['wind_speed_mph']},"
                f"{r['precipitation_in']},"
                f"{r['cloud_cover_pct']}\n"
            )
    print(f"CSV saved to {out_path}")


def upload_to_s3(local_path, s3_key):
    """ 
    Upload a file to S3 with the correct content type based on the file extension.
    """
    content_type = "image/png" if local_path.endswith(".png") else "text/csv"
    s3.upload_file(
        local_path, S3_BUCKET, s3_key,
        ExtraArgs={"ContentType": content_type},
    )
    print(f"Uploaded {s3_key} to s3://{S3_BUCKET}")


if __name__ == "__main__":
    print(f"--- Cville Weather Tracker at {datetime.now(timezone.utc).isoformat()} ---")

    weather = fetch_weather()
    item = write_to_dynamo(weather)

    print(
        f"Recorded | temp={item['temperature_f']}°F | "
        f"wind={item['wind_speed_mph']}mph | "
        f"precip={item['precipitation_in']}in | "
        f"cloud={item['cloud_cover_pct']}% | "
        f"ts={item['timestamp']}"
    )

    history = load_history()
    print(f"Total records in DynamoDB: {len(history)}")

    generate_plot(history)
    generate_csv(history)

    if S3_BUCKET:
        upload_to_s3("/tmp/plot.png", "plot.png")
        upload_to_s3("/tmp/data.csv", "data.csv")
    else:
        print("S3_BUCKET not set — skipping upload")