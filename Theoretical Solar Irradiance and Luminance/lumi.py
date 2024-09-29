import numpy as np
import xarray as xr
from datetime import datetime, timedelta
from skyfield.api import Topos, load, utc
import multiprocessing as mp
import os
import re

# Load ephemeris data from Skyfield
eph = load('de421.bsp')
sun = eph['sun']
earth = eph['earth']

# Define the datetime range
start_date = datetime(2019, 1, 1, tzinfo=utc)
end_date = datetime(2022, 1, 1, tzinfo=utc)  # Adjust this to your desired end date
ts = load.timescale()

# Create a grid of latitude and longitude coordinates
latitudes = np.arange(-90, 90, 1)
longitudes = np.arange(-180, 180, 1)

# Solar constant (W/m²)
solar_constant = 1361  # W/m²

# Conversion factor from solar irradiance (W/m²) to luminance (lux)
conversion_factor = 93  # lumens/m² per W/m²

def calculate_solar_data(time):
    solar_irradiance = np.zeros((len(latitudes), len(longitudes)))
    luminance = np.zeros((len(latitudes), len(longitudes)))

    for i, lat in enumerate(latitudes):
        for j, lon in enumerate(longitudes):
            location = earth + Topos(latitude_degrees=lat, longitude_degrees=lon)
            astrometric = location.at(time).observe(sun)
            alt, _, _ = astrometric.apparent().altaz()

            if alt.degrees > 0:
                irradiance = solar_constant * np.sin(np.radians(alt.degrees))
                solar_irradiance[i, j] = irradiance
                luminance[i, j] = irradiance * conversion_factor

    return solar_irradiance, luminance

def create_netcdf(date):
    times = [date + timedelta(hours=6*i) for i in range(8)]  # 8 intervals of 3 hours over a 24-hour period
    skyfield_times = ts.from_datetimes(times)
    
    # Convert skyfield_times to numpy.datetime64 for xarray compatibility
    times_np = np.array([t.utc_strftime('%Y-%m-%dT%H:%M:%S') for t in skyfield_times])  # ISO 8601 format

    solar_irradiance_data = []
    luminance_data = []

    for time in skyfield_times:
        irradiance, lum = calculate_solar_data(time)
        solar_irradiance_data.append(irradiance)
        luminance_data.append(lum)

    # Create xarray dataset
    ds = xr.Dataset(
        {
            "solar_irradiance": (["time", "latitude", "longitude"], np.array(solar_irradiance_data)),
            "luminance": (["time", "latitude", "longitude"], np.array(luminance_data)),
        },
        coords={
            "longitude": longitudes,
            "latitude": latitudes,
            "time": times_np,  # Use the numpy datetime64 array
        },
    )

    # Set time encoding
    ds.time.encoding['units'] = 'hours since 1950-01-01 00:00:00'
    ds.time.encoding['calendar'] = 'gregorian'

    # Set variable attributes
    ds.solar_irradiance.attrs['units'] = 'W/m²'
    ds.solar_irradiance.attrs['long_name'] = 'Solar Irradiance'
    ds.luminance.attrs['units'] = 'lux'
    ds.luminance.attrs['long_name'] = 'Luminance'

    # Set global attributes
    ds.attrs['Conventions'] = 'CF-1.6'
    ds.attrs['title'] = 'Theoretical Solar Irradiance and Luminance Data'
    ds.attrs['MadeBy'] = 'NitroxHead'
    ds.attrs['source'] = 'Generated from Skyfield calculations'
    ds.attrs['constants'] = '93  # lumens/m² per W/m² \n 1361  # W/m²'
    ds.attrs['history'] = f'Created on {datetime.now(utc).strftime("%Y-%m-%d %H:%M:%S UTC")}'

    # Save to NetCDF file
    filename = f'solar_data_{date.strftime("%Y%m%d")}.nc'
    ds.to_netcdf(filename, engine='h5netcdf')
    print(f'Created {filename}')

def get_latest_completed_date(directory="."):
    """
    This function checks for existing NetCDF files and returns the latest completed date.
    If no files are found, it returns None.
    """
    netcdf_files = [f for f in os.listdir(directory) if f.startswith("solar_data_") and f.endswith(".nc")]
    
    if not netcdf_files:
        return None
    
    # Extract dates from filenames using regex
    date_strings = [re.search(r"solar_data_(\d{8})\.nc", f).group(1) for f in netcdf_files]
    dates = [datetime.strptime(date_str, "%Y%m%d").replace(tzinfo=utc) for date_str in date_strings]
    
    # Return the latest date
    return max(dates)


def process_date_range(start, end):
    current_date = start
    while current_date < end:
        create_netcdf(current_date)
        current_date += timedelta(days=1)


if __name__ == '__main__':
    # Get the latest completed date
    latest_completed_date = get_latest_completed_date()

    # Set the start date to the day after the latest completed date if it exists
    if latest_completed_date:
        start_date = latest_completed_date + timedelta(days=1)
        print(f"Resuming from {start_date.strftime('%Y-%m-%d')}")
    else:
        print(f"Starting from {start_date.strftime('%Y-%m-%d')}")

    # Calculate the number of days in the date range
    total_days = (end_date - start_date).days

    # Calculate the number of days each process should handle
    num_cores = 4
    days_per_process = total_days // num_cores

    # Create a list of start and end dates for each process
    date_ranges = [
        (start_date + timedelta(days=i*days_per_process), 
         start_date + timedelta(days=(i+1)*days_per_process))
        for i in range(num_cores)
    ]

    # Ensure the last process covers any remaining days
    date_ranges[-1] = (date_ranges[-1][0], end_date)

    # Create a pool of worker processes
    with mp.Pool(processes=num_cores) as pool:
        # Use pool.starmap to apply process_date_range to each date range
        pool.starmap(process_date_range, date_ranges)

    print("All NetCDF files have been generated.")

