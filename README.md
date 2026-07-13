# Middleware Flask API for IBM Planning Analytics (TM1)

Middleware berbasis Flask yang menerima data JSON melalui REST API, melakukan validasi, menulis data ke file CSV, dan menjalankan TurboIntegrator (TI) Process di IBM Planning Analytics (TM1) menggunakan TM1py.

## Features

- JWT Authentication (OAuth-like token endpoint)
- Dynamic route registration
- JSON schema validation
- Automatic CSV generation
- TM1 TurboIntegrator execution
- Daily rotating logs with sequence number
- Fallback configuration via `.env`
- Error CSV generation for invalid requests
- Modular service architecture

---

## Project Structure

```text
middleware-flask-tm1py/
│
├── app.py
├── run.py
├── README.md
├── .gitignore
├── secret_key.py
│
├── Core/
│   ├── auth.py
│   ├── logger.py
│   ├── response.py
│   ├── router.py
│   └── settings.py
│
├── Integrations/
│   └── tm1_connection.py
│
├── Services/
│   ├── __init__.py
│   ├── base_service.py
│   ├── masterdata_catalogue.py
│   ├── masterdata_dealer.py
│   ├── masterdata_polreg.py
│   └── workdays.py
│
├── Validation/
│   ├── validation_rules.py
│   └── validator.py
│
├── Utils/
│   └── normalizer.py
│
└── CSV/
    ├── MasterData_Catalogue.csv
    ├── MasterData_Dealer.csv
    ├── MasterData_Polreg.csv
    └── Workdays.csv


#Architecture Flow
Client System
    ↓
POST JSON Request
    ↓
JWT Authentication
    ↓
Content-Type Validation
    ↓
JSON Parsing
    ↓
Business Validation
    ↓
Normalization
    ↓
CSV Generation
    ↓
Run TM1 TurboIntegrator Process
    ↓
JSON Response


#Technology Stack
Python 3.14+
Flask
TM1py
PyJWT
python-dotenv
python-dateutil



#Authentication
#Token Endpoint
POST /oauth/token
Content-Type: application/x-www-form-urlencoded

#Request Body
grant_type=p
username=
password=
scope=
client_id=
client_secret=


#Response
{
  "access_token": "eyJhbGciOi...",
  "token_type": "Bearer",
  "expires_in": 3600,
  "scope": "api"
}


#Logging

Sistem logging memiliki fitur:

Daily log file (app_YYYYMMDD.log)
Sequence number per log entry
Automatic log rotation
Auto cleanup logs older than one month
[1] 2025-07-31 09:00:00 | INFO | Route registered: /workdays
[2] 2025-07-31 09:01:10 | INFO | [SYNC001] Start process
[3] 2025-07-31 09:01:12 | INFO | [SYNC001] Process completed: Success

#CSV Processing

Setiap request yang valid akan:

Dinormalisasi
Dikonversi ke format flat
Ditulis ke file CSV
Menjalankan TI Process TM1

Jika terjadi error, sistem tetap membuat CSV berisi:

SyncCode
Status = 0
Message
Date
Time



#TM1 Integration

Koneksi ke TM1 menggunakan TM1py.
with get_tm1() as tm1:
    tm1.processes.execute_with_return("Load_MasterData_Catalogue")


#Author
Mohamad Asep Shayfullah
GitHub: https://github.com/asepms2023
Website: https://asepms20.my.id/


#License

This project is provided for internal and educational use.
