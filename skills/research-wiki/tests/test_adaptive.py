"""Copied into staged tests after preserving the existing regression suite."""
import json, shutil, subprocess
from pathlib import Path
from dataclasses import replace
import pytest
from PIL import Image
from conftest import ENTRY_ID, update_gallery, write_interface
from rwiki.config import load_config
from rwiki.errors import WikiError
from rwiki.ingest import ingest_figure
from rwiki.templates import scaffold_template, render
from rwiki.sizing import DEFAULTS

import os
# The plotting interpreter (matplotlib/pandas); override on another machine.
PY=Path(os.environ.get('RWIKI_PLOT_PYTHON',Path.home()/'.codex/venvs/sci-figure-replica/Scripts/python.exe'))
needs_plot_python=pytest.mark.skipif(not PY.is_file(),reason='set RWIKI_PLOT_PYTHON to a Python with matplotlib/pandas')


@pytest.mark.parametrize('defaults',[[],{'unknown':2},{'sizing':{'item_width_in':-1}}])
def test_invalid_function_defaults(workspace,defaults):
    config,path=workspace
    obj=json.loads(path.read_text(encoding='utf-8'));obj['function_defaults']=defaults
    path.write_text(json.dumps(obj),encoding='utf-8')
    with pytest.raises(WikiError):load_config(path)


@needs_plot_python
def test_new_scaffold_render_and_portable_copy(workspace,tmp_path):
    config,path=workspace
    config=replace(config,python_exe=PY,function_defaults={'sizing':DEFAULTS})
    update_gallery(config,status='approved')  # synthetic fixture, never real gallery
    ingest_figure(config,ENTRY_ID)
    scaffold_template(config,ENTRY_ID,'bar',['A','D'])
    target=config.wiki_root/'templates'/(ENTRY_ID+'--bar')
    assert (target/'code/sizing.py').is_file() and (target/'code/render.py').is_file()
    spec=json.loads((target/'spec.json').read_text(encoding='utf-8'))
    assert spec['style']['sizing']['max_width_in'] is None
    assert spec['style']['sizing']['profile']=='unbound'
    write_interface(config.wiki_root,'values',{'group':{'type':'str','description':'类别'},'value':{'type':'float','description':'值'}})
    spec['tables']={'values':{'interface':'values','description':'synthetic layout check'}}
    spec['style']={'font_family':'DejaVu Sans','dpi':100,'sizing':{**spec['style']['sizing'],
                     'profile':'categorical_x','table':'values','x':'group'}}
    (target/'spec.json').write_text(json.dumps(spec),encoding='utf-8')
    (target/'code/panel.py').write_text('''def draw(fig,rect,tables,style):
    import numpy as np
    ax=fig.add_axes(rect);frame=tables['values']
    ax.bar(np.arange(len(frame)),frame.value)
    ax.set_xticks(range(len(frame)),frame.group,rotation=45,ha='right')
    ax.tick_params(labelsize=11)
    return ax
''',encoding='utf-8')
    widths=[]
    for n in [4,6,8]:
        data=tmp_path/f'data-{n}';data.mkdir()
        (data/'values.csv').write_text('group,value\n'+''.join(f'G{i},{i+1}\n' for i in range(n)),encoding='utf-8')
        out=tmp_path/f'render-{n}';render(config,ENTRY_ID+'--bar',data,out)
        sizing=json.loads((out/'sizing.json').read_text(encoding='utf-8'));widths.append(sizing['width_in'])
        assert sizing['counts']['x']==n
        assert all((out/f'figure.{ext}').stat().st_size>0 for ext in ['png','pdf','svg'])
    assert widths==pytest.approx([4.35,5.95,7.55])
    copied=tmp_path/'other-project/template';shutil.copytree(target,copied)
    out=tmp_path/'copied-output'
    proc=subprocess.run([str(PY),'-X','utf8',str(copied/'code/render.py'),'--data',str(tmp_path/'data-8'),
                         '--out',str(out)],cwd=tmp_path,capture_output=True,text=True,encoding='utf-8')
    assert proc.returncode==0,proc.stderr
    assert (out/'figure.png').read_bytes()==(tmp_path/'render-8/figure.png').read_bytes()
    override=tmp_path/'style.json';override.write_text('{"sizing":{"item_width_in":1.2}}',encoding='utf-8')
    render(config,ENTRY_ID+'--bar',tmp_path/'data-8',tmp_path/'wide',override)
    p=json.loads((tmp_path/'wide/sizing.json').read_text(encoding='utf-8'))
    assert p['width_in']==pytest.approx(10.75) and p['counts']['x']==8
    override.write_text('{"sizing":{"max_width_in":5}}',encoding='utf-8')
    with pytest.raises(WikiError,match='user limit'):
        render(config,ENTRY_ID+'--bar',tmp_path/'data-8',tmp_path/'limited',override)


@needs_plot_python
def test_compose_checks_adaptive_space_without_resizing(layout_workspace,tmp_path):
    from rwiki.layouts import compose
    config,_,target,layout=layout_workspace
    config=replace(config,python_exe=PY)
    first=layout['panels'][0]
    template=config.wiki_root/'templates'/first['template']
    spec=json.loads((template/'spec.json').read_text(encoding='utf-8'))
    spec['style']['sizing']={'profile':'categorical_x','table':'values','x':'group',
                             'item_width_in':3,'plot_height_in':1.2,'min_height_in':.5,
                             'margins_in':[0,0,0,0]}
    (template/'spec.json').write_text(json.dumps(spec),encoding='utf-8')
    (target/'example/values.csv').write_text('value,group\n2,G1\n',encoding='utf-8')
    with pytest.raises(WikiError,match='Panel region'):
        compose(config,target,target/'example',tmp_path/'small-compose',None)
    layout['canvas']['width_in']=12
    (target/'layout.json').write_text(json.dumps(layout),encoding='utf-8')
    compose(config,target,target/'example',tmp_path/'large-compose',None)
    with Image.open(tmp_path/'large-compose/figure.png') as im:assert im.size==(600,100)
