
EXAMPLE_DOC_REQUIREMENTS = ['basic_questions', 'credit_report', 'company_report']

EXAMPLE_PERSON = {
    'basic_questions': {
        'first_name': 'Jim',
        'last_name': 'Stephens',
        'date_of_birth': '1973-05-10',
        'full_address': 'Flat 21, Sycamore Gardens, Nottingham, NN12 4VF, United Kingdom',
        'postcode': 'NN124VF',
        'country': 'United Kingdom',
    },  # Self supplied - more fields avaiable, request explicitly, a.k.a filled in on signup.
    'driving_licence': {
        'document_type': 'driving_licence',
        'first_name': 'James',
        'middle_names': '',
        'last_name': 'Stephens',
        'date_of_birth': '1973-05-10',
        'licence_number': 5673123,
        'date_of_issuance': '2005-03-01',
        'date_of_expiry': '2025-03-01',
        'categories':  ['A1', 'B1', 'B'],
        'country_of_issuance': 'United Kingdom',
        'restrictions': [],
    },  # Scan or smth.
    'credit_report': {
        'score': 104,
        'credit_limit': 5000,
        'credit_utilisation': 0.1,
        'number_of_accounts': 4,
        'age_of_oldest_account': 37,
        'missed_payments_last_12m': 0,
        'credit_searches_last_12m': 1,
    },  # External provider. Leaves imprint.
}
EXAMPLE_COMPANY  = {
    'identification': {
        'company_number': 53123,
        'company_name': 'Decent Trinkets ltd',
        'company_type': 'Limited Liability Company',
        'incorporation_date': '2012-05-01',
        'business_description': 'Manufacturing of useful trinkets.',
        'business_sector': 'Manufacturing',
    },
    'company_report': {
        'company_number': 53123,
        'company_name': 'Decent Trinkets ltd',
        'company_type': 'Limited Liability Company',
        'incorporation_date': '2012-05-01',
        'report_date': '2017-04-01',
        'assets': 50100,
        'liabilities': 12033,
        'score': 51,
        'opinion': 'Good',
        'turnover': 170403,
        'number_of_employees': 2,
        'sic_code': 46460,
        'region': 'East Midlands',
    }
}
SAMPLE_APPLICATION = {
    'basic_questions': EXAMPLE_PERSON['basic_questions'],
    'credit_report': EXAMPLE_PERSON['credit_report'],
    'company_report': EXAMPLE_COMPANY['company_report']
}

# Code constants
FUNDING_TYPE=0
REPAYMENT_TYPE=1
FEE_TYPE=2

APPROVED_STATE_NAME = 'Approved'
DECLINED_STATE_NAME = 'Declined'
REPAYMENT_TYPES = {0: 'Bullet', 1: 'Equal Repayment', 2: 'Equal Principal'}  # Define what these ideas mean - how to allow different/do we allow different, or do we tightly "regulate" how repayments are to be computed?
INTEREST_TYPES = {'compound': 'Compound', 'simple': 'Simple'}


# Product constants
PRODUCT_NAME = 'Standard'
AMOUNT_THRESHOLD = 0.01
MIN_LOAN_AMOUNT = 100.
MAX_LOAN_AMOUNT = 50000.
DECISION_VALID_FOR_DAYS = 7