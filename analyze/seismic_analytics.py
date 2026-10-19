"""Seismic analytics: population-exposure scoring + spatial cluster detection.

Reads fct_earthquakes from the DuckDB warehouse and writes back two tables:
  - main.quake_exposure : nearest major city + a proximity-weighted exposure index
  - main.quake_clusters : DBSCAN spatial clusters (active zones / aftershock sequences)
"""
from __future__ import annotations

import duckdb
import numpy as np
import pandas as pd
from sklearn.cluster import DBSCAN

DB_PATH = "warehouse.duckdb"
EARTH_RADIUS_KM = 6371.0

# Compact reference set of major, seismically-relevant cities.
CITIES = pd.DataFrame([
    ("Tokyo", "Japan", 35.68, 139.69, 37400000),
    ("Osaka", "Japan", 34.69, 135.50, 19000000),
    ("Manila", "Philippines", 14.60, 120.98, 13900000),
    ("Davao", "Philippines", 7.19, 125.46, 1800000),
    ("Jakarta", "Indonesia", -6.21, 106.85, 10600000),
    ("Palu", "Indonesia", -0.90, 119.87, 370000),
    ("Padang", "Indonesia", -0.95, 100.35, 900000),
    ("Santiago", "Chile", -33.45, -70.67, 6800000),
    ("Calama", "Chile", -22.46, -68.93, 165000),
    ("Lima", "Peru", -12.05, -77.04, 9750000),
    ("Mexico City", "Mexico", 19.43, -99.13, 21800000),
    ("Istanbul", "Turkey", 41.01, 28.98, 15500000),
    ("Los Angeles", "USA", 34.05, -118.24, 12500000),
    ("San Francisco", "USA", 37.77, -122.42, 4700000),
    ("Anchorage", "USA", 61.22, -149.90, 290000),
    ("Kathmandu", "Nepal", 27.70, 85.32, 1400000),
    ("Tehran", "Iran", 35.69, 51.39, 9000000),
    ("Taipei", "Taiwan", 25.03, 121.57, 2600000),
    ("Wellington", "New Zealand", -41.29, 174.78, 420000),
    ("Christchurch", "New Zealand", -43.53, 172.64, 380000),
    ("Naples", "Italy", 40.85, 14.27, 3000000),
    ("Athens", "Greece", 37.98, 23.73, 3150000),
    ("Petropavlovsk-Kamchatsky", "Russia", 53.02, 158.65, 180000),
    ("Quito", "Ecuador", -0.18, -78.47, 2800000),
    ("Bogota", "Colombia", 4.71, -74.07, 11000000),
    ("Guatemala City", "Guatemala", 14.63, -90.51, 3000000),
    ("Mandalay", "Myanmar", 21.95, 96.09, 1500000),
    ("Port-au-Prince", "Haiti", 18.59, -72.31, 2800000),
    ("Dunhuang", "China", 40.14, 94.66, 190000),
], columns=["city", "country", "city_lat", "city_lon", "population"])


def haversine_km(lat1, lon1, lat2, lon2):
    """Vectorised great-circle distance in km."""
    lat1, lon1, lat2, lon2 = map(np.radians, (lat1, lon1, lat2, lon2))
    dlat, dlon = lat2 - lat1, lon2 - lon1
    a = np.sin(dlat / 2) ** 2 + np.cos(lat1) * np.cos(lat2) * np.sin(dlon / 2) ** 2
    return 2 * EARTH_RADIUS_KM * np.arcsin(np.sqrt(a))


def compute_exposure(quakes: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for q in quakes.itertuples():
        d = haversine_km(q.latitude, q.longitude,
                         CITIES["city_lat"].values, CITIES["city_lon"].values)
        i = int(np.argmin(d))
        nearest = CITIES.iloc[i]
        dist_km = float(d[i])
        # Transparent RELATIVE index (not a calibrated casualty estimate):
        # higher magnitude and more people raise it; greater distance lowers it.
        exposure = nearest["population"] * (q.magnitude ** 2) / (dist_km + 50)
        rows.append({
            "id": q.id,
            "magnitude": q.magnitude,
            "place": q.place,
            "nearest_city": nearest["city"],
            "nearest_country": nearest["country"],
            "distance_km": round(dist_km, 1),
            "city_population": int(nearest["population"]),
            "exposure_index": round(exposure, 0),
        })
    return pd.DataFrame(rows)


def compute_clusters(quakes: pd.DataFrame, eps_km=150.0, min_samples=3) -> pd.DataFrame:
    coords = np.radians(quakes[["latitude", "longitude"]].values)
    db = DBSCAN(eps=eps_km / EARTH_RADIUS_KM, min_samples=min_samples,
                metric="haversine").fit(coords)
    out = quakes[["id", "magnitude", "place"]].copy()
    out["cluster_id"] = db.labels_   # -1 = noise / isolated quake
    return out


def main():
    con = duckdb.connect(DB_PATH)
    quakes = con.execute("""
        SELECT id, occurred_at, magnitude, place, latitude, longitude
        FROM main.fct_earthquakes
        WHERE latitude IS NOT NULL AND longitude IS NOT NULL
    """).fetchdf()
    print(f"Loaded {len(quakes)} earthquakes.\n")

    exposure = compute_exposure(quakes)
    clusters = compute_clusters(quakes)

    con.register("exposure_df", exposure)
    con.register("clusters_df", clusters)
    con.execute("CREATE OR REPLACE TABLE main.quake_exposure AS SELECT * FROM exposure_df")
    con.execute("CREATE OR REPLACE TABLE main.quake_clusters AS SELECT * FROM clusters_df")

    print("Top 5 by population-exposure index:")
    print(exposure.sort_values("exposure_index", ascending=False)
          .head(5)[["magnitude", "place", "nearest_city", "distance_km", "exposure_index"]]
          .to_string(index=False))

    n_clusters = clusters.loc[clusters.cluster_id != -1, "cluster_id"].nunique()
    print(f"\nDetected {n_clusters} spatial clusters (active zones / sequences).")
    summary = (clusters[clusters.cluster_id != -1]
               .groupby("cluster_id")
               .agg(quakes=("id", "count"), max_mag=("magnitude", "max"))
               .sort_values("quakes", ascending=False).head(5))
    print(summary.to_string())
    con.close()


if __name__ == "__main__":
    main()