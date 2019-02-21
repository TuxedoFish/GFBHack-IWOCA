import json
import requests
import os

BANK_USERNAME = os.getenv('BANK_USERNAME')
BANK_PASSWORD = os.getenv('BANK_PASSWORD')
BANK_HOST = os.getenv('BANK_HOST')
BANK_PORT = os.getenv('BANK_PORT')

MY_ACCOUNT = 'ade7039d-81be-42a4-bccd-9e59ec4b6112'
GOD_ACCOUNT = 'a26f3abc-a275-4987-9901-5abaf33b35ab'


if __name__ == '__main__':
    response = requests.post('{}:{}/create_account'.format(BANK_HOST, BANK_PORT),
                             data={'username': BANK_USERNAME, 'password': BANK_PASSWORD}, verify=False)

    if response.status_code == 200:
        account = json.loads(response.content)['account']
        print("Account ID: {}".format(account))
        with open('bank_account_list.csv', 'a') as f:
            f.write(account + '\n')
    else:
        print(response.content.decode())


def admin_transfer_money(account=MY_ACCOUNT, amount=100, username='admin', password='pass'):
    return requests.post('{}:{}/transaction'.format(BANK_HOST, BANK_PORT),
                  data={'account': GOD_ACCOUNT, 'account_to': account, 'amount': amount}, auth=(username, password))


def transfer_money(account_from=MY_ACCOUNT, account_to=GOD_ACCOUNT, amount=50):
    return requests.post(
        '{}:{}/transaction'.format(BANK_HOST, BANK_PORT),
        data={'account': account_from, 'account_to': account_to, 'amount': amount}, auth=(BANK_USERNAME, BANK_PASSWORD)
    )


def get_statement(account=MY_ACCOUNT):
    return requests.get(
        '{}:{}/statement?account={}'.format(BANK_HOST, BANK_PORT, account),
        auth=(BANK_USERNAME, BANK_PASSWORD))


def get_balance(account=MY_ACCOUNT):
    return requests.get(
        '{}:{}/balance?account={}'.format(BANK_HOST, BANK_PORT, account),
        auth=(BANK_USERNAME, BANK_PASSWORD))
