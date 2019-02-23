# waning-keyboard

project waning keyboard.


Using flask_migrate for dabase management.
For some reason I had to set waning-keyboard as PYTHONPATH. Once done, autodetecting migrations work. without it, models weren't detected.

## Installation
1. Clone repo, e.g.: `git clone https://github.com/TuxedoFish/GFBHack-IWOCA.git'
1. Create virtualenv, e.g.: `virtualenv -p python3 venv`
1. Activate virtualenv, e.g.: `source env/bin/activate`
1. Install requirements, e.g.: `pip install -r requirements.txt`
1. `export FLASK_APP=wk_client`
1. Create DB: `flask db migrate` and `flask db upgrade`
1. For https, generate self-signed security certificate: `openssl req -x509 -newkey rsa:4096 -nodes -out cert.pem -keyout key.pem -days 365`
1. If gunicorn is to be used for production server: `pip install gunicorn` 

## Setting up environment variables
A few things (bank account) require secret environment variables to be setup. These obviously shouldn't be public, e.g. don't commit them to version control.  Also don't use the default ones.
One option is to make a untracked copy of `env_variables_local_template.sh` locally. E.g.
1. `cp env_variables_local_template.sh env_variables_local.sh`
1. Define the variables in the local copy.
1. `source env_variables_local.sh`

## Setting up bank account
The script in `setup_banking_script.py` registers a new account with the bank. 
1. Make sure that the required environment variables are set.
1. `python setup_banking_script.py`
1. If successful account number will be printed in the terminal and stored in `bank_account_list.csv`. Set this as the bank account number in your project. (`BANK_ACCOUNT` in `settings.py`)


## Run Server
Example dev server:
1.`flask run --cert cert.pem --key key.pem --host 0.0.0.0`

prod server:
1. `pip install gunicorn`
1. `gunicorn --certfile cert.pem --keyfile key.pem -b IP_ADDR:PORT wk_client:app` 

## API
The payload of all post requests and responses is in json.
The game loop is expected to supply `Timestamp` (isoformat string) in
request header.


### /get_info (GET)
Returns basic info on the products available. Keyed by product name.  
Each product should return at least: `amount`, `duration`, `interest` and `fee_rate` (`_min` and `_max`) and `fee_flat` and `interest_type` (`Compound` or `Simple`). Also their representative values and `repayment_type` and `repayment_frequency`.

### /register (POST)
Create a customer account.
Post body to contain `username`, `password` and `bank_account`.
Returns `username` if successful. 

### /get_decision (GET, POST)
Makes a decision if able, returns data requirements for decision.

Body: input data, structured as specified in requirements. (TODO: write more on input structure
)
Returns (dict):  `requirements` (always), `decision` (if decision could be made.) 


### /request_funding (POST)
Creates a loan and funding.

Body: `amount`, `approval_reference`

Returns (dict): `funding_reference`, `repayment_schedule`, `repayment_account`.

### /get_schedule (GET)
Returns (dict): `balance`, `repayment_schedule`.


## Auth
Authentication is implemented using basic https authentication, with username and password encoded in the url: e.g. `https://username:password@127.0.0.1:5000/get_decision`.


## Glossary
### Interest
Simple - Simple interest (interest charged on principal only, no interest on interest)

Compound - Compount interest (interest charged on full balance)

### Repayment Type
`Equal Principal` - Waterfall (fees then interest then principal) repayments, each repayment repays full fees+interest and 1/x principal, where x is number of scheduled repayments.

`Equal Repayment` - Each repayment is equal in size, following amortization schedule.

`Bullet` - Full balance paid off in one go at the end of the term.  



