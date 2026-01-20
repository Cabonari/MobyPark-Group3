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
flake8 pytest requests pytest-mock

benodigde file voor het runnen van tests en code(mkdir -p data/pdata eerst uitvoeren):
data/users.json
data/vehicles.json
data/parking_lots.json
data/reservations.json
data/payments.json
data/pdata/p1-sessions.json

.....



Swagger opstarten: 

cd code 
cd parking-api 
cd api 
cd swagger 

in /swagger: python -m http.server 8000

Daarna in der browser: http://localhost:8000/index.html


Voor het openen van de log dashboard:
LET OP: Alleen vanaf de root van het project 
In de terminal:
python Code\Parking-api\api\server.py --logs

Dit moet los van de server draaien.
Kan ook tegelijk met de server draaien in een andere terminal.
