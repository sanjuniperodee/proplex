# def application(env, start_response):
#     start_response('200 OK', [('Content-Type'), ('text/html')])
#     return [b"Hellow World"]
import json

import requests
headers = {
    'SS-Token': 'b859f200c0ed4ba491f9a4185f6fb64f'
}
result = requests.get('https://api.survey-studio.com/projects/17169/counters', headers=headers)
response = result.json()
print(response['body'][9]['quota'])
