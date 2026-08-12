#!/usr/bin/env python3
"""
seismo_fetch.py — Fetches seismic and infrasound data for hurricanes.

Uses IRIS Web Services (FDSN) to retrieve ground displacement and pressure
waveforms from stations near the storm track. Based on the methodology of
Ji et al. (2024) in Science.
"""

import datetime
import requests
import numpy as np
import pandas as pd
from typing import List, Optional, Tuple
from dataclasses import dataclass
from pathlib import Path
import obspy
from obspy.clients.fdsn import Client
from obspy import UTCDateTime

@dataclass
class SeismoObs:
    """One observation from a seismo-acoustic station."""
    timestamp: datetime.datetime
    ground_displacement_nm: float  # in nanometers (vertical component)
    infrasound_pressure_pa: float  # in Pascals
    station_id: str
    latitude: float
    longitude: float
    quality_flag: str  # 'good', 'noisy', 'clipped'

class SeismoFetcher:
    """
    Fetches seismic and infrasound data for a given hurricane.
    Uses FDSN client to query USArray Transportable Array stations.
    """

    def __init__(self, network: str = "TA", station: str = None, channel: str = "BHZ"):
        """
        Args:
            network: IRIS network code (e.g., 'TA' for Transportable Array)
            station: specific station code (if None, will find closest)
            channel: seismic channel (BHZ for vertical broadband)
        """
        self.client = Client("IRIS")
        self.network = network
        self.station = station
        self.channel = channel

    def find_nearest_station(self, lat: float, lon: float, starttime: UTCDateTime, endtime: UTCDateTime,
                             radius_deg: float = 5.0) -> Optional[str]:
        """
        Find the nearest seismic station to the hurricane's position within a radius.
        """
        inventory = self.client.get_stations(
            network=self.network,
            channel=self.channel,
            latitude=lat,
            longitude=lon,
            maxradius=radius_deg,
            starttime=starttime,
            endtime=endtime,
            level="channel"
        )
        stations = []
        for net in inventory:
            for sta in net:
                for cha in sta:
                    if cha.code == self.channel:
                        dist = np.sqrt((sta.latitude - lat)**2 + (sta.longitude - lon)**2)
                        stations.append((sta.code, dist, sta.latitude, sta.longitude))
        if not stations:
            return None
        stations.sort(key=lambda x: x[1])
        return stations[0][0], stations[0][2], stations[0][3]

    def fetch_waveforms(self, station: str, lat: float, lon: float, starttime: UTCDateTime, endtime: UTCDateTime,
                        channel: str = "BHZ") -> Tuple[np.ndarray, np.ndarray]:
        """
        Fetch seismic waveform (ground displacement) for given time window.
        Returns (timestamps_seconds, displacement_nm)
        """
        try:
            st = self.client.get_waveforms(
                network=self.network,
                station=station,
                location="*",
                channel=channel,
                starttime=starttime,
                endtime=endtime,
                attach_response=True
            )
            # Remove instrument response to get displacement (nm)
            st.remove_response(output="DISP", water_level=100)
            tr = st[0]
            data = tr.data * 1e9  # convert m -> nm
            times = tr.times()  # seconds from start
            return times, data
        except Exception as e:
            print(f"Error fetching seismic data: {e}")
            return None, None

    def fetch_infrasound(self, station: str, lat: float, lon: float, starttime: UTCDateTime, endtime: UTCDateTime) -> Tuple[np.ndarray, np.ndarray]:
        """
        Fetch infrasound pressure data (if available) – typically from infrasound arrays.
        For demo, we synthesize a pressure signal if no real data exists.
        We'll look for a dedicated infrasound channel (e.g., 'BDF' for barometer).
        """
        # Try to fetch barometer data if available
        try:
            st = self.client.get_waveforms(
                network=self.network,
                station=station,
                location="*",
                channel="BDF",  # Barometer channel
                starttime=starttime,
                endtime=endtime
            )
            tr = st[0]
            data = tr.data  # pressure in Pa
            times = tr.times()
            return times, data
        except:
            # If no real data, we generate a synthetic from seismic using the known relation
            # (or we can use a proxy: pressure ~ seismic amplitude)
            print("Infrasound not available; using synthetic proxy from seismic.")
            times, disp = self.fetch_waveforms(station, lat, lon, starttime, endtime)
            if disp is None:
                return None, None
            # Rough model: pressure fluctuation ~ derivative of displacement * constant
            pressure = np.gradient(disp) * 1e-3  # heuristic scaling
            return times, pressure

    def fetch_for_hurricane(self, hurricane_track: pd.DataFrame, station_id: Optional[str] = None) -> List[SeismoObs]:
        """
        Iterate over hurricane track positions and fetch data from the nearest station
        at each time step.
        """
        observations = []
        for idx, row in hurricane_track.iterrows():
            lat = row['lat']
            lon = row['lon']
            time = UTCDateTime(row['timestamp'])

            # Find nearest station if not provided
            if station_id is None:
                station_info = self.find_nearest_station(lat, lon, time, time + 3600)
                if station_info is None:
                    continue
                station_id, sta_lat, sta_lon = station_info

            # Fetch seismic and infrasound for a 1-hour window around this time
            start = time - 1800
            end = time + 1800
            times_seis, disp = self.fetch_waveforms(station_id, sta_lat, sta_lon, start, end)
            times_infra, press = self.fetch_infrasound(station_id, sta_lat, sta_lon, start, end)

            if disp is None or press is None:
                continue

            # Compute mean values over the window
            mean_disp = np.mean(np.abs(disp))  # RMS? Use absolute average
            mean_press = np.mean(np.abs(press))

            observations.append(SeismoObs(
                timestamp=pd.Timestamp(row['timestamp']),
                ground_displacement_nm=mean_disp,
                infrasound_pressure_pa=mean_press,
                station_id=station_id,
                latitude=sta_lat,
                longitude=sta_lon,
                quality_flag='good'
            ))
            # Update station if tracking moves – for simplicity we keep same station
        return observations

# Example usage (for demo only)
if __name__ == "__main__":
    # Dummy track data
    track = pd.DataFrame({
        'timestamp': pd.date_range('2024-09-01 00:00', periods=10, freq='1H'),
        'lat': np.linspace(25, 30, 10),
        'lon': np.linspace(-80, -75, 10)
    })
    fetcher = SeismoFetcher()
    obs = fetcher.fetch_for_hurricane(track, station_id="T25A")  # example station
    for o in obs:
        print(o)
