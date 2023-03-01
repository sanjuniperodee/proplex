# def application(env, start_response):
#     start_response('200 OK', [('Content-Type'), ('text/html')])
#     return [b"Hellow World"]
import json

import requests
header = {
    'SS-Token': 'b859f200c0ed4ba491f9a4185f6fb64f',
    'Content-Type': 'application/json-patch+json',
    'accept': 'application/json'
}
payload = {
"projectIds": [
    '27316'
  ],
  "includeHidden": True
}
result = requests.post('https://api.survey-studio.com/projects/counters', data=json.dumps(payload), headers=header)
# print(result)
# response = result.json()
print(result)
response = result.json()
print(response['body'][0]['counters']['name'=='Ucell']['value'])
# ucell_all = 0
# beeline_all = 0
# mobiuz_all = 0
# uzmobile_all = 0
# for i in range(2, 29):
#     if i % 2 == 0:
#         ucell_all += response['body'][0]['counters'][i]['value']
# for i in range(31, 58):
#     if i % 2 != 0:
#         # print(response['body'][i]['quota'])
#         beeline_all += response['body'][0]['counters'][i]['value']
# for i in range(60, 87):
#     if i % 2 == 0:
#         mobiuz_all += response['body'][0]['counters'][i]['value']
# for i in range(89, 116):
#     if i % 2 != 0:
#         uzmobile_all += response['body'][0]['counters'][i]['value']
# context = {
#     'ucell_all': ucell_all,
#     'beeline_all': beeline_all,
#     'mobiuz_all': mobiuz_all,
#     'uzmobile_all': uzmobile_all
# }
# print(context)
