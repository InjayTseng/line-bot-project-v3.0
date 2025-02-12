# UpdateDate：2021/01/27

import sys
import os
from urllib import request, parse, error
from http import HTTPStatus
import base64
import json
from pprint import pprint

HOST = 'xxxx.xxxxx.xxx'       # You will receive it when the license is issued.
ACCEPT = 'application/json;charset=utf-8'

# --------------------------------------------------------------------------------
# 1. Authentication

AUTH_URI = 'https://' + HOST + '/api/1/printing/oauth2/auth/token?subject=printer'
CLIENT_ID = 'xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx'
SECRET = 'xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx'
DEVICE = 'xxxxxxxxxxxxxx@xxx.xxx.xxx'

auth = base64.b64encode((CLIENT_ID + ':' + SECRET).encode()).decode()

query_param = {
    'grant_type': 'password',
    'username': DEVICE,
    'password': ''
}
query_string = parse.urlencode(query_param)

headers = {
    'Authorization': 'Basic ' + auth,
    'Content-Type': 'application/x-www-form-urlencoded; charset=utf-8'
}

req, res, body, err_str = '', '', '', '';
try:
    req = request.Request(AUTH_URI, data=query_string.encode('utf-8'), headers=headers, method='POST')
    with request.urlopen(req) as res:
        body = res.read()
except error.HTTPError as err:
    err_str = str(err.code) + ':' + err.reason + ':' + str(err.read())
except error.URLError as err:
    err_str = err.reason

pprint('1. Authentication: ---------------------------------')
pprint(AUTH_URI)
pprint(query_string)
if res == '':
    pprint(err_str)
else:
    pprint(str(res.status) + ':' + res.reason)
    pprint(json.loads(body))

if err_str != '' or res.status != HTTPStatus.OK:
    sys.exit(1)

# --------------------------------------------------------------------------------
# 2. Create print job

subject_id = json.loads(body).get('subject_id')
access_token = json.loads(body).get('access_token')

job_uri = 'https://' + HOST + '/api/1/printing/printers/' + subject_id + '/jobs'

data_param = {
    'job_name': 'SampleJob1',
    'print_mode': 'document'
}
data = json.dumps(data_param)

headers = {
    'Authorization': 'Bearer ' + access_token,
    'Content-Type': 'application/json;charset=utf-8'
}

req, res, body, err_str = '', '', '', '';
try:
    req = request.Request(job_uri, data=data.encode('utf-8'), headers=headers, method='POST')
    with request.urlopen(req) as res:
        body = res.read()
except error.HTTPError as err:
    err_str = str(err.code) + ':' + err.reason + ':' + str(err.read())
except error.URLError as err:
    err_str = err.reason

pprint('2. Create print job: -------------------------------')
pprint(job_uri)
pprint(data)
if res == '':
    pprint(err_str)
else:
    pprint(str(res.status) + ':' + res.reason)
    pprint(json.loads(body))

if err_str != '' or res.status != HTTPStatus.CREATED:
    sys.exit(1)

# --------------------------------------------------------------------------------
# 3. Upload print file

job_id = json.loads(body).get('id')
base_uri = json.loads(body).get('upload_uri')

local_file_path = './SampleDoc.pdf'

_, ext = os.path.splitext(local_file_path)
file_name = '1' + ext
upload_uri = base_uri + '&File=' + file_name

headers = {
    'Content-Length': str(os.path.getsize(local_file_path)),
    'Content-Type': 'application/octet-stream'
}

req, res, body, err_str = '', '', '', '';
try:
    with open(local_file_path, 'rb') as f:
        req = request.Request(upload_uri, data=f, headers=headers, method='POST')
        with request.urlopen(req) as res:
            body = res.read()
except error.HTTPError as err:
    err_str = str(err.code) + ':' + err.reason + ':' + str(err.read())
except error.URLError as err:
    err_str = err.reason

pprint('3. Upload print file: ------------------------------')
pprint(base_uri)
if res == '':
    pprint(err_str)
else:
    pprint(str(res.status) + ':' + res.reason)

if err_str != '' or res.status != HTTPStatus.OK:
    sys.exit(1)

# --------------------------------------------------------------------------------
# 4. Execute print

print_uri = 'https://' + HOST + '/api/1/printing/printers/' + subject_id + '/jobs/' + job_id + '/print'
data=''

headers = {
    'Authorization': 'Bearer ' + access_token,
    'Content-Type': 'application/json; charset=utf-8'
}

req, res, body, err_str = '', '', '', '';
try:
    req = request.Request(print_uri, data=data.encode('utf-8'), headers=headers, method='POST')
    with request.urlopen(req) as res:
        body = res.read()
except error.HTTPError as err:
    err_str = str(err.code) + ':' + err.reason + ':' + str(err.read())
except error.URLError as err:
    err_str = err.reason

pprint('4. Execute print: ----------------------------------')
pprint(print_uri)
if res == '':
    pprint(err_str)
else:
    pprint(str(res.status) + ':' + res.reason)
    pprint(json.loads(body))
