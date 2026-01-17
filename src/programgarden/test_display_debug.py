"""DisplayNode 데이터 디버깅"""
import json
import os
from dotenv import load_dotenv
load_dotenv()

from programgarden import ProgramGarden

with open('examples/workflows/condition/04-condition-volumespike-historical-stock.json') as f:
    workflow = json.load(f)

workflow['credentials'][0]['data']['appkey'] = os.getenv('APPKEY')
workflow['credentials'][0]['data']['appsecret'] = os.getenv('APPSECRET')

pg = ProgramGarden()
result = pg.run(workflow)

nodes = result.get('nodes', {})

# volumeSpikeCondition의 values 확인
vs_node = nodes.get('volumeSpikeCondition', {}).get('outputs', {})
values = vs_node.get('values', [])
print('=== volumeSpikeCondition.values ===')
print(f'type: {type(values)}, len: {len(values)}')
if values:
    first = values[0]
    print(f'첫번째 keys: {list(first.keys()) if isinstance(first, dict) else first}')
    ts = first.get('time_series', []) if isinstance(first, dict) else []
    print(f'time_series 개수: {len(ts)}')
    if ts:
        print(f'time_series[0]: {ts[0]}')
        print(f'time_series[-1]: {ts[-1]}')

# display 노드 확인
display_node = nodes.get('display', {}).get('outputs', {})
print('\n=== display outputs ===')
print(f'keys: {list(display_node.keys())}')
data = display_node.get('data')
print(f'data type: {type(data)}')
if isinstance(data, list):
    print(f'data len: {len(data)}')
    if data:
        print(f'data[0]: {data[0]}')
elif data is None:
    print('data is None!')
else:
    print(f'data: {data}')
