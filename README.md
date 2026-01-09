Server opstarten: 

Stap 1 in de terminal: 

cd Code 
cd Parking-api
cd api 

Stap 2 in de terminal: 

python server.py 

|--------------------------------------------------------|

Testen opstarten: 

Stap 1. Server opstarten 

Stap 2. tests opstarten 

Ctrl + Shift + P (tegelijk)
Selecteer -> Python: Configure Tests

Selecteer pytest 

Selecteer Code 

Klik op de "Testing" Icoon links 
om de resultaten te bekijken. 

benodigde installaties (met pip install):
flake8 pytest requests

benodigde file voor het runnen van tests en code(mkdir -p data/pdata eerst uitvoeren):
data/users.json
data/vehicles.json
data/parking_lots.json
data/reservations.json
data/payments.json
data/pdata/p1-sessions.json
