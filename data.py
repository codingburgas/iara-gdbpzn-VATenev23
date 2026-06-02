firefighters = [
    {
        "id": 1,
        "name": "Ivan Petrov",
        "rank": "Commander",
        "status": "available",
        "vehicle_id": 101
    },
    {
        "id": 2,
        "name": "Georgi Ivanov",
        "rank": "Firefighter",
        "status": "available",
        "vehicle_id": 101
    },
    {
        "id": 3,
        "name": "Dimitar Georgiev",
        "rank": "Firefighter",
        "status": "available",
        "vehicle_id": 101
    },
    {
        "id": 4,
        "name": "Nikolay Dimitrov",
        "rank": "Driver",
        "status": "available",
        "vehicle_id": 102
    },
    {
        "id": 5,
        "name": "Petar Nikolov",
        "rank": "Firefighter",
        "status": "on_duty",
        "vehicle_id": 102
    },
    {
        "id": 6,
        "name": "Hristo Hristov",
        "rank": "Firefighter",
        "status": "vacation",
        "vehicle_id": None
    },
    {
        "id": 7,
        "name": "Todor Todorov",
        "rank": "Commander",
        "status": "available",
        "vehicle_id": 103
    },
    {
        "id": 8,
        "name": "Stoyan Stoyanov",
        "rank": "Firefighter",
        "status": "sick",
        "vehicle_id": None
    },
    {
        "id": 9,
        "name": "Aleksandar Kolev",
        "rank": "Driver",
        "status": "available",
        "vehicle_id": 104
    },
    {
        "id": 10,
        "name": "Martin Vasilev",
        "rank": "Paramedic",
        "status": "available",
        "vehicle_id": 105
    },
    {
        "id": 11,
        "name": "Kaloyan Iliev",
        "rank": "Firefighter",
        "status": "available",
        "vehicle_id": 106
    },
    {
        "id": 12,
        "name": "Viktor Angelov",
        "rank": "Driver",
        "status": "available",
        "vehicle_id": 107
    },
    {
        "id": 13,
        "name": "Borislav Marinov",
        "rank": "Firefighter",
        "status": "available",
        "vehicle_id": 108
    },
    {
        "id": 14,
        "name": "Yordan Stefanov",
        "rank": "Firefighter",
        "status": "on_duty",
        "vehicle_id": 109
    },
    {
        "id": 15,
        "name": "Emil Petkov",
        "rank": "Paramedic",
        "status": "available",
        "vehicle_id": 110
    }
]

# Vehicles are spread across Burgas so dispatch routes look realistic on the map.
vehicles = [
    {
        "id": 101,
        "type": "Fire Truck - Aerial Ladder",
        "location": "Burgas Central Station",
        "team": [1, 2, 3],
        "latitude": 42.5063,
        "longitude": 27.4678,
        "status": "station"
    },
    {
        "id": 102,
        "type": "Fire Engine - Water Tanker",
        "location": "Burgas Central Station",
        "team": [4, 5],
        "latitude": 42.5063,
        "longitude": 27.4678,
        "status": "station"
    },
    {
        "id": 103,
        "type": "Command Vehicle",
        "location": "Burgas Central Station",
        "team": [7],
        "latitude": 42.5070,
        "longitude": 27.4690,
        "status": "station"
    },
    {
        "id": 104,
        "type": "Rescue Vehicle",
        "location": "Station 2 - Industrial Zone",
        "team": [9],
        "latitude": 42.4815,
        "longitude": 27.4412,
        "status": "station"
    },
    {
        "id": 105,
        "type": "Ambulance",
        "location": "Station 1 - Lazur",
        "team": [10],
        "latitude": 42.5132,
        "longitude": 27.4628,
        "status": "station"
    },
    {
        "id": 106,
        "type": "Fire Engine - Pumper",
        "location": "Station 3 - Meden Rudnik",
        "team": [11],
        "latitude": 42.4699,
        "longitude": 27.4361,
        "status": "station"
    },
    {
        "id": 107,
        "type": "Fire Truck - Heavy Rescue",
        "location": "Station 4 - Slaveykov",
        "team": [12],
        "latitude": 42.5301,
        "longitude": 27.4520,
        "status": "station"
    },
    {
        "id": 108,
        "type": "Fire Engine - Water Tanker",
        "location": "Station 5 - Port of Burgas",
        "team": [13],
        "latitude": 42.4925,
        "longitude": 27.4760,
        "status": "station"
    },
    {
        "id": 109,
        "type": "Hazmat Unit",
        "location": "Station 2 - Industrial Zone",
        "team": [14],
        "latitude": 42.4830,
        "longitude": 27.4445,
        "status": "station"
    },
    {
        "id": 110,
        "type": "Ambulance",
        "location": "Station 4 - Slaveykov",
        "team": [15],
        "latitude": 42.5288,
        "longitude": 27.4555,
        "status": "station"
    },
    {
        "id": 111,
        "type": "Fire Engine - Pumper",
        "location": "Station 1 - Lazur",
        "team": [],
        "latitude": 42.5145,
        "longitude": 27.4665,
        "status": "station"
    },
    {
        "id": 112,
        "type": "Water Tanker - Large",
        "location": "Station 3 - Meden Rudnik",
        "team": [],
        "latitude": 42.4710,
        "longitude": 27.4390,
        "status": "station"
    },
    {
        "id": 113,
        "type": "Command Vehicle",
        "location": "Station 5 - Port of Burgas",
        "team": [],
        "latitude": 42.4940,
        "longitude": 27.4735,
        "status": "station"
    },
    {
        "id": 114,
        "type": "Rescue Vehicle",
        "location": "Station 4 - Slaveykov",
        "team": [],
        "latitude": 42.5275,
        "longitude": 27.4498,
        "status": "station"
    },
    {
        "id": 115,
        "type": "Aerial Platform",
        "location": "Burgas Central Station",
        "team": [],
        "latitude": 42.5055,
        "longitude": 27.4662,
        "status": "station"
    }
]
incidents = []
