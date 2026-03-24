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
    }
]

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
        "latitude": 42.5063,
        "longitude": 27.4678,
        "status": "station"
    },
    {
        "id": 104,
        "type": "Rescue Vehicle",
        "location": "Burgas Station 2 - Industrial Zone",
        "team": [],
        "latitude": 42.4815,
        "longitude": 27.4412,
        "status": "station"
    },
    {
        "id": 105,
        "type": "Ambulance",
        "location": "Burgas Station 1",
        "team": [],
        "latitude": 42.5132,
        "longitude": 27.4628,
        "status": "station"
    }
]
incidents = []