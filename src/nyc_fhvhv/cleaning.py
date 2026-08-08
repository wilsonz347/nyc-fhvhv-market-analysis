def clean_fhvhv(con, raw_table, clean_table):
    con.execute(f"""
        CREATE OR REPLACE TABLE {clean_table} AS
        SELECT
            CASE 
                WHEN hvfhs_license_num = 'HV0003' THEN 'Uber'
                WHEN hvfhs_license_num = 'HV0005' THEN 'Lyft'
                ELSE hvfhs_license_num
            END AS provider_name,

            -- License number
            t.dispatching_base_num,
            t.originating_base_num,

            -- Datetime columns
            t.request_datetime,
            t.on_scene_datetime,
            t.pickup_datetime,
            t.dropoff_datetime,

            -- Pickup location
            t.PULocationID,
            pu.Borough AS pickup_borough,
            pu.Zone AS pickup_zone,
            pu.service_zone AS pickup_service_zone,

            -- Dropoff location
            t.DOLocationID,
            dz.Borough AS dropoff_borough,
            dz.Zone AS dropoff_zone,
            dz.service_zone AS dropoff_service_zone,

            -- Numeric columns
            t.trip_miles,
            t.trip_time,
            t.base_passenger_fare,
            t.tolls,
            t.bcf,
            t.sales_tax,
            t.congestion_surcharge,
            t.airport_fee,
            t.tips,
            t.driver_pay,
            t.cbd_congestion_fee,

            -- Flags
            (t.shared_request_flag = 'Y') AS shared_request_flag,
            (t.shared_match_flag = 'Y') AS shared_match_flag,
            (t.access_a_ride_flag = 'Y') AS access_a_ride_flag,
            (t.wav_request_flag = 'Y') AS wav_request_flag,
            (t.wav_match_flag = 'Y') AS wav_match_flag

        FROM {raw_table} t
        JOIN zone_lookup pu
            ON t.PULocationID = pu.LocationID
        JOIN zone_lookup dz
            ON t.DOLocationID = dz.LocationID

        WHERE t.trip_miles > 0
            AND t.dropoff_datetime > t.pickup_datetime
            AND t.base_passenger_fare > 0
            AND t.driver_pay > 0
            AND t.on_scene_datetime >= t.request_datetime
            AND t.on_scene_datetime <= t.pickup_datetime;
    """)

    return clean_table
