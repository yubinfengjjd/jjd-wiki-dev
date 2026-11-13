"""Portable renderer for a completed Python draw adapter and sizing policy."""
from pathlib import Path
import argparse
import importlib.util
import importlib
import json
import sys
from uuid import uuid4

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import pandas as pd


def main():
    parser=argparse.ArgumentParser()
    for flag in ['data','out']:parser.add_argument('--'+flag,type=Path,required=True)
    parser.add_argument('--style',type=Path)
    args=parser.parse_args()
    root=Path(__file__).resolve().parents[1]
    spec=json.loads((root/'spec.json').read_text(encoding='utf-8'))
    style=dict(spec['style'])
    if args.style:
        override=json.loads(args.style.read_text(encoding='utf-8'))
        unknown=override.keys()-style.keys()
        if unknown:raise ValueError(f'Unknown style keys: {sorted(unknown)}')
        for key,value in override.items():
            style[key]=(style.get(key,{})|value) if key=='sizing' and isinstance(value,dict) else value
    tables={key:pd.read_csv(args.data/f"{table['interface']}.csv") for key,table in spec['tables'].items()}
    name='portable_'+uuid4().hex
    module_spec=importlib.util.spec_from_file_location(name,root/'code/__init__.py',
                         submodule_search_locations=[str(root/'code')])
    package=importlib.util.module_from_spec(module_spec);sys.modules[name]=package
    module_spec.loader.exec_module(package)
    panel=importlib.import_module(name+'.'+Path(spec['panel']).stem)
    sizing=importlib.import_module(name+'.sizing')
    with plt.rc_context({'font.family':style.get('font_family','DejaVu Sans'),
                         'pdf.fonttype':42,'svg.fonttype':'none'}):
        fig,handles,plan=sizing.draw_figure(panel.draw,tables,style)
        args.out.mkdir(parents=True,exist_ok=True)
        for ext in ['png','pdf','svg']:
            fig.savefig(args.out/f'figure.{ext}',dpi=style.get('dpi',300),facecolor='white')
        plt.close(fig)
    (args.out/'sizing.json').write_text(json.dumps(plan,ensure_ascii=False,indent=2),encoding='utf-8')


if __name__=='__main__':main()
