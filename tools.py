import base64
import calendar
import datetime
import hashlib
import io
import json
import locale
import os
import pathlib
import random
import re, string, unicodedata
import shutil
import subprocess
import sys
import traceback
from django.contrib.humanize.templatetags.humanize import ordinal

import bcrypt
from django.conf import settings as conf_settings
import requests
from django.core.mail import EmailMessage, EmailMultiAlternatives
from django.http import HttpResponse
import time

from django.urls import reverse
from django.utils.html import escape
from django.utils.timezone import make_aware


class Tools():

    @staticmethod
    def sanitize_filename(name):
        if name is None:
            return ''
        name = Tools.strip_accents(name.strip())
        while ('  ' in name):
            name = name.replace('  ', ' ')
        name = name.replace(' ', '-')
        while ('--' in name):
            name = name.replace('--', '-')
        return ''.join(filter(Tools.permited_char, name))

    @staticmethod
    def make_url_name(name):
        if name is None:
            return ''
        name = Tools.strip_accents(name.strip().lower())
        while ('  ' in name):
            name = name.replace('  ', ' ')
        name = name.replace(' ', '-')
        while ('--' in name):
            name = name.replace('--', '-')
        return ''.join(filter(Tools.permited_char, name))

    @staticmethod
    def strip_accents(text):
        try:
            text = unicode(text, 'utf-8')
        except NameError:  # unicode is a default on python 3
            pass

        text = unicodedata.normalize('NFD', text) \
            .encode('ascii', 'ignore') \
            .decode("utf-8")

        return str(text).strip()

    @staticmethod
    def permited_char(s):
        if s.isalpha():
            return True
        elif bool(re.match("^[a-z0-9_-]*$", s)):
            return True
        elif s == ".":
            return True
        else:
            return False

    @staticmethod
    def send_telegram(text):
        telegram = conf_settings.TELEGRAM or None

        if telegram:

            if conf_settings.DEBUG:
                text = "[Ambiente de DEBUG] " + text

            requests.packages.urllib3.disable_warnings()
            header = {'content-type': 'application/json'}
            data = {
                'chat_id': telegram['chat_id'],
                'text': text
            }
            r1 = requests.post("https://api.telegram.org/%s/sendMessage" % (telegram['bot_id']),
                               verify=False, timeout=30,
                               headers=header,
                               data=json.dumps(data)
                               )
            if r1.status_code == 200:
                return True

        return False

    @staticmethod
    def send_telegram_contact(name, email, phone):
        telegram = conf_settings.TELEGRAM or None

        if telegram:

            if '+' not in phone:
                phone = "+55" + phone

            vcard = f"BEGIN:VCARD \nVERSION:3.0 \nPRODID:-//Sec4US.//WebSite//EN \nN:;Aluno Sec4US {name};;;\nFN:Aluno Sec4US {name} \nEMAIL;type=INTERNET;type=pref:{email} \nTEL;type=CELL;type=VOICE;type=pref:{phone} \nEND:VCARD \n"
            requests.packages.urllib3.disable_warnings()
            header = {'content-type': 'application/json'}
            data = {
                'chat_id': telegram['chat_id'],
                'phone_number': phone,
                'first_name': 'Aluno Sec4US ' + name,
                'vcard': vcard
            }
            r1 = requests.post("https://api.telegram.org/%s/sendContact" % (telegram['bot_id']),
                               verify=False, timeout=30,
                               headers=header,
                               data=json.dumps(data)
                               )
            if r1.status_code == 200:
                return True

        return False

    @staticmethod
    def get_ip(request):

        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')

        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip

    @staticmethod
    def get_user_agent(request):

        return request.META.get('HTTP_USER_AGENT')

    @staticmethod
    def resp_created(msg='Resource created', **extras):

        response = {'isSuccessfull': True, 'hasError': False, 'message': msg, 'status': 201}

        response.update(extras)

        return HttpResponse(json.dumps(response), content_type="application/json", status=201)

    @staticmethod
    def resp_sucess(msg='', **extras):

        response = {'isSuccessfull': True, 'hasError': False, 'message': msg, 'status': 200}

        response.update(extras)

        return HttpResponse(json.dumps(response), content_type="application/json", status=200)

    @staticmethod
    def resp_notallowed(msg='Undefined error'):
        response = {'isSuccessfull': True, 'hasError': True, 'error': msg, 'status': 401}
        return HttpResponse(json.dumps(response), content_type="application/json", status=401)

    @staticmethod
    def resp_notfound(msg='Resource not found'):
        response = {'isSuccessfull': True, 'hasError': True, 'error': msg, 'status': 404}
        return HttpResponse(json.dumps(response), content_type="application/json", status=404)

    @staticmethod
    def resp_precondition(msg='Undefined error', **extras):

        response = {'isSuccessfull': True, 'hasError': True, 'message': msg, 'status': 412}
        response.update(extras)
        return HttpResponse(json.dumps(response), content_type="application/json", status=412)

    @staticmethod
    def resp_badrequest(msg='Bad request'):
        response = {'isSuccessfull': True, 'hasError': True, 'error': msg, 'status': 400}
        return HttpResponse(json.dumps(response), content_type="application/json", status=400)

    @staticmethod
    def resp_error(msg='Server error', **extras):
        response = {'isSuccessfull': True, 'hasError': True, 'message': msg, 'status': 500}
        response.update(extras)
        return HttpResponse(json.dumps(response), content_type="application/json", status=500)

    @staticmethod
    def to_unicode(x, charset='utf-8', errors='strict'):
        if x is None or isinstance(x, str):
            return x
        if isinstance(x, bytes):
            return x.decode(charset, errors)
        return str(x)

    @staticmethod
    def to_string(x):
        if x is None or isinstance(x, str):
            return x
        elif x is None or isinstance(x, int):
            return str(x)
        elif x is None or isinstance(x, datetime.date):
            return x.isoformat()
        elif isinstance(x, bytes):
            return Tools.to_unicode(x)
        else:
            return str(x)

    @staticmethod
    def create_username():
        r_base = ['M', '4', 'v', '3', 'r', '1', 'c', 'k', 'm', 'a']
        current_time = str(int(time.time()))
        username = ''.join(
            random.choice(string.ascii_lowercase + string.ascii_uppercase + string.digits) for _ in range(6))
        username += ''.join([r_base[int(n)] for n in current_time])
        username += ''.join(random.choice(string.ascii_lowercase + string.ascii_uppercase + string.digits) for _ in
                            range(18 - len(username)))

        return username

    @staticmethod
    def send_email(email, subject, body, attachment=None):
        mail = Tools.build_email(email, subject, body)

        if attachment is not None:
            att = []
            if isinstance(attachment, list):
                att = attachment
            else:
                att.append(attachment)

            for a in att:
                if os.path.isfile(a):
                    fo = open(a, 'rb')
                    filename = pathlib.Path(a).name
                    mail.attach(filename, fo.read(), 'application/pdf')

        mail.send()

    @staticmethod
    def build_email(email, subject, body):
        if conf_settings.DEBUG:
            email = "junior.helvio@gmail.com"

        to = []
        if isinstance(email, list):
            to = email
        else:
            to = str(email).split(',')

        if not conf_settings.DEBUG:
            to += ["contato@sec4us.com.br"]

        if not 'text/html' in body.lower() and not '<br' in body.lower() and not '<div' in body.lower():
            # encode
            html = '<meta http-equiv="Content-Type" content="text/html; charset=utf-8">\n<div style="font-family:Arial;font-size:16px;line-height:22.4px">'
            html += escape(body).replace('\n', '<br />')
            html += "</div>"
        else:
            html = body

        eml = EmailMultiAlternatives(
            subject=subject,
            body=html,
            from_email=conf_settings.EMAIL_HOST_USER,
            to=to
        )
        eml.content_subtype = "html"  # Main content is now text/html
        return eml

    @staticmethod
    def to_real(value, symbol="R$"):
        if isinstance(value, int):
            value = float(value)

        str_value = str(value)
        try:
            locale.setlocale(locale.LC_ALL, 'pt_BR.UTF-8')
            str_value = locale.currency(value, grouping=True, symbol=None)
        except:
            str_value = str(round((float(value)), 2)).replace(",", "").replace(".", ",")

        return "%s %s" % (symbol.strip(), str_value)

    @staticmethod
    def to_base64(data):
        bdata = None
        if isinstance(data, bytes):
            bdata = data

        if isinstance(data, str):
            bdata = data.encode("utf-8")

        b64data = base64.b64encode(bdata)
        if isinstance(b64data, bytes):
            b64data = b64data.decode("utf-8")

        return b64data

    @staticmethod
    def get_human_date(date, language=None, format='informal'):

        if date is None:
            return None

        if not isinstance(date, datetime.date):
            return str(date)

        l1 = Tools.get_locale_alias(language)
        try:

            locale.setlocale(locale.LC_ALL, l1)

            if "pt_" in l1.replace('-', '_').lower():
                date_format = "%s de %s de %s" % (date.day, calendar.month_name[date.month], date.year)
            else:
                if format == 'formal':
                    date_format = "%s of %s %s" % (ordinal(date.day), calendar.month_name[date.month], date.year)
                else:
                    date_format = "%s %s, %s" % (date.day, calendar.month_name[date.month], date.year)

        except Exception as e:
            print(str(date), language, l1, format)
            exc_type, exc_value, exc_traceback = sys.exc_info()
            error = traceback.format_exception(exc_type, exc_value, exc_traceback)
            err_txt = '%s\n\n' % exc_value
            for e in error:
                err_txt += str(e.strip('\n'))

            print(err_txt)
            date_format = "%Y-%m-%d"

        return date.strftime(date_format)

    @staticmethod
    def get_locale_alias(language=None):

        if language is None:
            language = conf_settings.LANGUAGE_CODE

        if language is None:
            language = 'pt_br'

        try:
            locale.setlocale(locale.LC_ALL, language.replace('-', '_'))
            return language.replace('-', '_')
        except:
            lang = language.replace('-', '_').lower()
            lang1 = lang.split('_')[0] + '_'

            # exact match
            for k, v in locale.locale_alias.items():
                if k.lower() == lang:
                    try:
                        locale.setlocale(locale.LC_ALL, v)
                        return v
                    except:
                        pass

            # aproximado
            for k, v in locale.locale_alias.items():
                if lang in k.lower():
                    try:
                        locale.setlocale(locale.LC_ALL, v)
                        return v
                    except:
                        pass

            # aproximado
            for k, v in locale.locale_alias.items():
                if lang1 in k.lower():
                    try:
                        locale.setlocale(locale.LC_ALL, v)
                        return v
                    except:
                        pass

        return language

    @staticmethod
    def get_month_name(month, long=True):

        if month is None:
            return None

        if not isinstance(month, int):
            month = int(month)

        language = Tools.get_locale_alias()
        locale.setlocale(locale.LC_ALL, language)
        if long:
            txt = calendar.month_name[month]
        else:
            txt = calendar.month_abbr[month]

        return txt.title()

    @staticmethod
    def last_day_of_month(any_day):
        # this will never fail
        # get close to the end of the month for any day, and add 4 days 'over'
        next_month = any_day.replace(day=28) + datetime.timedelta(days=4)
        # subtract the number of remaining 'overage' days to get last day of current month, or said programattically
        # said, the previous day of the first of next month
        return next_month - datetime.timedelta(days=next_month.day)

    @staticmethod
    def current_user_label(request):
        current_user = request.user

        if current_user is None:
            return "N/A"

        if not request.user.is_authenticated:
            return "N/A"

        if request.user.first_name is not None and request.user.first_name.strip() != '':
            label = request.user.first_name

            if request.user.last_name is not None and request.user.last_name.strip() != '':
                label += " " + request.user.last_name

            return label.title()

        if request.user.email is not None and request.user.email.strip() != '':
            return request.user.email

        return str(request.user)

    @staticmethod
    def title_text(text):
        s_text = text.title().strip()
        s_text = s_text.replace("Em ", "em ")
        s_text = s_text.replace("Da ", "da ")
        s_text = s_text.replace("De ", "de ")
        s_text = s_text.replace("Di ", "di ")
        s_text = s_text.replace("Do ", "do ")
        s_text = s_text.replace("Du ", "du ")
        return s_text

    @staticmethod
    def clean_string(str_data):
        if str_data is None:
            return None
        else:
            return ''.join(filter(Tools.permited_char, str_data))

    @staticmethod
    def data(d1, language="pt"):
        if language.lower() == "pt":
            mes_ext = {1: 'Janeiro', 2: 'Fevereiro', 3: 'Março', 4: 'Abril', 5: 'Maio', 6: 'Junho', 7: 'Julho',
                       8: 'Agosto', 9: 'Setembro', 10: 'Outubro', 11: 'Novembro', 12: 'Dezembro'}
            return "%s de %s de %s" % (d1.day, mes_ext[int(d1.month)], d1.year)

        else:

            mes_ext = {1: 'January', 2: 'February', 3: 'March', 4: 'April', 5: 'May', 6: 'June', 7: 'July', 8: 'August',
                       9: 'September', 10: 'October', 11: 'November', 12: 'December'}
            return "%s %s, %s" % (d1.day, mes_ext[int(d1.month)], d1.year)

    @staticmethod
    def data2(d1):
        return "%04d_%02d_%02d" % (d1.year, d1.month, d1.day)

    @staticmethod
    def pid_is_running(pid):
        if os.path.isdir('/proc/{}'.format(pid)):
            return True
        return False

    @staticmethod
    def tipo_logradouro(endereco):
        end = endereco.lower()
        if end is None:
            return ""
        if end.strip() == '':
            return ""

        if 'rua' in end:
            return "Rua"
        if 'av.' in end or 'avenida' in end:
            return "Avenida"
        if 'bsq' in end or 'bosque' in end:
            return "Bosque"
        if 'estrada' in end:
            return "Estrada"
        if 'estância' in end:
            return "Estância"

        return "Rua"

    @staticmethod
    def to_number(n):
        if isinstance(n, str):
            return int(re.sub("[^0-9]", "", n))
        else:
            return int(re.sub("[^0-9]", "", str(n)))

    @staticmethod
    def to_currency(x):
        if x is None:
            return "---"

        v1 = round(float(x), 2)
        txt = "{:.2f}".format(v1)
        n1 = "{:,}".format(Tools.to_number(txt[:-3])).replace(",", ".")
        n2 = "{:02d}".format(Tools.to_number(txt[-3:]))

        return "R$ %s,%s" % (n1, n2)

    @staticmethod
    def get_first_name(fullname):
        firstname = ''
        try:
            firstname = fullname.split()[0]
        except Exception as e:
            print(str(e))
        return firstname

    @staticmethod
    def get_last_name(fullname):
        lastname = ''
        try:
            index = 0
            for part in fullname.split():
                if index > 0:
                    if index > 1:
                        lastname += ' '
                    lastname += part
                index += 1
        except Exception as e:
            print(str(e))
        return lastname

    @staticmethod
    def to_datetime(text):
        # Example
        # 2020-07-23 16:22:44.341971

        try:
            try:
                if conf_settings.USE_TZ:
                    return make_aware(datetime.datetime.fromisoformat(text))
                else:
                    return datetime.datetime.fromisoformat(text)
            except:

                dtt = text
                if '.' in dtt:
                    dtt = text.split('.')[0]

                dtt = dtt.replace('T', ' ')

                if conf_settings.USE_TZ:
                    return make_aware(datetime.datetime.strptime(dtt, '%Y-%m-%d %H:%M:%S'))
                else:
                    return datetime.datetime.strptime(dtt, '%Y-%m-%d %H:%M:%S')
        except Exception as e:
            print(f'Erro convertendo data e hora {text}')
            print(e)
            return None

    @staticmethod
    def md5_file(fname):
        hash_md5 = hashlib.md5()
        with open(fname, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_md5.update(chunk)
        return hash_md5.hexdigest().lower()

    @staticmethod
    def replace_in_file(file_name, find, replace):
        with open(file_name, 'r') as file:
            filedata = file.read()
            filedata = filedata.replace(find, replace)

        with open(file_name, 'w') as file:
            file.write(filedata)

    @staticmethod
    def ban(request):
        ip_addr = Tools.get_ip(request)
        print(f'BAN: {ip_addr}')

    @staticmethod
    def has_access_to_resouce(request, resource_user):
        if request.user != resource_user:
            ip_addr = Tools.get_ip(request)
            print(f'Tentativa de acesso não autorizado {request.path} do endereço {ip_addr}')
            Tools.ban(request)
            return False
        return True

    @staticmethod
    def recursive_chmod(path, mode=0o666):
        for dirpath, dirnames, filenames in os.walk(path):
            os.chmod(dirpath, mode)
            for filename in filenames:
                os.chmod(os.path.join(dirpath, filename), mode)

    @staticmethod
    def execute(command, cwd):
        my_env = os.environ.copy()
        my_env[
            "PATH"] = "/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin:/usr/games:/usr/local/games:/snap/bin:" + \
                      my_env["PATH"]
        result = subprocess.run(
            command,
            cwd=cwd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=my_env,
            shell=True
        )

        ret_txt = result.stdout.decode('utf-8')
        ret_txt += result.stderr.decode('utf-8')

        return (result.returncode, ret_txt)
