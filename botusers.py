import json

import workconfig

config = workconfig.read_config('config')


class User:
    """

    """
    def __init__(self, username='', phone='', telegram_id='', list_org=None):
        if list_org is None:
            self.list_org = []
        self.username = username
        self.telegram_id = telegram_id
        self.phone = phone


class Organization:
    def __init__(self, inn='', name='', email='', active=False):
        self.inn = inn
        self.name = name
        self.active = active
        self.email = email


def read_orgs_from_json():
    """
      :return: list organizations readed from JSON file placed in path from config
    """
    with open(config.get('PathToDocs', 'path')+'\\domain.usr.json', mode='r', encoding='windows-1251') as ff:
        list_orgs = json.load(ff)

    return list_orgs


def get_list_org_for_user_id(curr_user: User, id_telegram=None):
    list_orgs = read_orgs_from_json()
    for org in list_orgs:
        list_users = org['users']
        for usr in list_users:
            if 'id_telegram' in usr.keys():
                if id_telegram == usr['id_telegram']:
                    user_org = Organization(org['inn'], org['name'])
                    curr_user.list_org.append(user_org)
                    curr_user.username = usr['name']
    if len(curr_user.list_org) == 0:
        return False
    else:
        return True


def get_list_org_for_user_phone(curr_user: User, phone=None):
    list_orgs = read_orgs_from_json()
    for org in list_orgs:
        list_users = org['users']
        for usr in list_users:
            if 'phone' in usr.keys():
                if phone.strip() in usr['phone'].strip():
                    return True
    return False


