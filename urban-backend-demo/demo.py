import time

import requests

URL = 'http://localhost:8000'

print(requests.get(f'{URL}/echo?foo=bar').text)

# should not have an entry, error
response = requests.get(f'{URL}/jobs?id=foo')
print(response.status_code, response.text)

# If we POST a job and then get its status, we should get a valid status.
response = requests.post(f'{URL}/jobs', data={'wait_time_s': 5})
print(response.json())
job_id = response.json()['job_id']
response = requests.get(f'{URL}/jobs?id={job_id}')
print(response.status_code, response.text)

while True:
    response = requests.get(f'{URL}/jobs?id={job_id}')
    print(response.status_code, response.text)
    time.sleep(0.5)
    if response.json()['status'] == 'complete':
        break;
