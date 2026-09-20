"""Split items must obey their own IfNode routing before side effects."""
import asyncio
from unittest.mock import patch
import pytest
from programgarden import WorkflowExecutor
from programgarden.executor import GenericNodeExecutor


def workflow(items, outer=True):
    return {'id':'split_guards','name':'Split guard regression','nodes':[
        {'id':'start','type':'StartNode'},
        {'id':'outer','type':'IfNode','left':outer,'operator':'==','right':True},
        {'id':'split','type':'SplitNode','array':items,'parallel':False},
        {'id':'guard','type':'IfNode','left':'{{ nodes.split.item.allowed }}','operator':'==','right':True},
        {'id':'effect','type':'HTTPRequestNode','url':'https://example.invalid/intercepted'},
        {'id':'aggregate','type':'AggregateNode','mode':'collect'},
    ],'edges':[{'from':'start','to':'outer'},{'from':'outer','to':'split','from_port':'true'},
        {'from':'split','to':'guard'},{'from':'guard','to':'effect','from_port':'true'},
        {'from':'effect','to':'aggregate'}]}


@pytest.mark.asyncio
@pytest.mark.parametrize('allowed',[[False,True],[True,False],[False,False]])
async def test_if_guard_is_local_to_each_split_item(allowed):
    captured=[]
    async def effect(self,node_id,node_type,config,context,**kwargs):
        item=context.get_output('split','item');captured.append(item['symbol'])
        return {'response':{'symbol':item['symbol']}}
    with patch.object(GenericNodeExecutor,'execute',effect):
        job=await WorkflowExecutor().execute(workflow([{'symbol':str(i),'allowed':a} for i,a in enumerate(allowed)]))
        await asyncio.wait_for(job._task,3)
    assert captured==[str(i) for i,a in enumerate(allowed) if a]
    assert job.get_state()['status']=='completed'


@pytest.mark.asyncio
async def test_outer_false_skips_split_entirely():
    async def forbidden(*args,**kwargs):raise AssertionError('Inactive split executed')
    with patch.object(GenericNodeExecutor,'execute',forbidden):
        job=await WorkflowExecutor().execute(workflow([{'symbol':'A','allowed':True}],outer=False))
        await asyncio.wait_for(job._task,3)
    assert job.get_state()['status']=='completed',job.get_state().get('errors')
    assert not job.context.get_all_outputs('split')


@pytest.mark.asyncio
async def test_taken_alternative_survives_skipped_sibling_and_is_collected():
    wf=workflow([{'symbol':'A','allowed':True},{'symbol':'B','allowed':False}])
    wf['nodes'].append({'id':'otherwise','type':'HTTPRequestNode','url':'https://example.invalid/otherwise'})
    wf['edges'] += [{'from':'guard','to':'otherwise','from_port':'false'},{'from':'otherwise','to':'aggregate'}]
    async def effect(self,node_id,node_type,config,context,**kwargs):
        return {'response':{'symbol':context.get_output('split','item')['symbol'],'branch':node_id}}
    with patch.object(GenericNodeExecutor,'execute',effect):
        job=await WorkflowExecutor().execute(wf)
        await asyncio.wait_for(job._task,3)
    outputs=job.context.get_all_outputs('aggregate')
    assert outputs['array']==[{'symbol':'A','branch':'effect'},{'symbol':'B','branch':'otherwise'}],outputs


@pytest.mark.asyncio
async def test_parallel_request_cannot_mix_item_guard_with_another_item():
    wf=workflow([{'symbol':'A','allowed':True},{'symbol':'B','allowed':False}])
    next(n for n in wf['nodes'] if n['id']=='split')['parallel']=True
    wf['nodes'].append({'id':'pause','type':'HTTPRequestNode','url':'https://example.invalid/pause'})
    wf['edges']=[e for e in wf['edges'] if not(e['from']=='split' and e['to']=='guard')]
    wf['edges'] += [{'from':'split','to':'pause'},{'from':'pause','to':'guard'}]
    captured=[]
    async def effect(self,node_id,node_type,config,context,**kwargs):
        if node_id=='pause':
            await asyncio.sleep(0.01)
            return {'response':{}}
        captured.append(context.get_output('split','item')['symbol'])
        return {'response':captured[-1]}
    with patch.object(GenericNodeExecutor,'execute',effect):
        job=await WorkflowExecutor().execute(wf)
        await asyncio.wait_for(job._task,3)
    assert captured==['A']
