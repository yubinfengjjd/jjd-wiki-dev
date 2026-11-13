"""Portable plotting-size policy. Copy this file with a template's code package.

No Wiki dependency, global paths, analysis, file I/O or expression evaluation.
Matplotlib is imported only when measuring text or creating a figure.
"""
from copy import deepcopy
import math
from numbers import Real


DEFAULTS = {
    'mode': 'adaptive', 'profile': 'unbound', 'table': None, 'x': None, 'y': None,
    'item_width_in': .8, 'item_height_in': .32,
    'plot_width_in': 5.4, 'plot_height_in': 4.4,
    'margins_in': [.9, .25, .85, .55],  # left, right, bottom, top
    'min_width_in': 3.2, 'min_height_in': 2.8,
    'max_width_in': None, 'max_height_in': None,
    'width_in': None, 'height_in': None,
    'label_fontsize': 11, 'label_rotation': 45, 'label_gap_in': .12,
}


def validate_policy(policy):
    if not isinstance(policy, dict):
        raise ValueError('sizing must be an object')
    unknown = policy.keys() - DEFAULTS.keys()
    if unknown:
        raise ValueError(f'Unknown sizing keys: {sorted(unknown)}')
    p = deepcopy(DEFAULTS)
    p.update(deepcopy(policy))
    if p['mode'] not in ('adaptive', 'fixed', 'replica'):
        raise ValueError('sizing.mode must be adaptive, fixed or replica')
    if p['profile'] not in ('unbound', 'categorical_x', 'categorical_y', 'matrix', 'fixed'):
        raise ValueError('Unknown sizing.profile')
    positive = ['item_width_in','item_height_in','plot_width_in','plot_height_in',
                'min_width_in','min_height_in','label_fontsize','label_gap_in']
    optional = ['max_width_in','max_height_in','width_in','height_in']
    for key in positive + optional:
        value = p[key]
        if key in optional and value is None:
            continue
        if isinstance(value,bool) or not isinstance(value,Real) or not math.isfinite(value) or value <= 0:
            raise ValueError(f'sizing.{key} must be finite and positive')
    angle = p['label_rotation']
    if isinstance(angle,bool) or not isinstance(angle,Real) or not math.isfinite(angle) or not 0 <= angle <= 90:
        raise ValueError('sizing.label_rotation must lie in 0..90')
    margins=p['margins_in']
    if not isinstance(margins,(list,tuple)) or len(margins)!=4 or any(
        isinstance(v,bool) or not isinstance(v,Real) or not math.isfinite(v) or v<0 for v in margins):
        raise ValueError('sizing.margins_in must contain four finite nonnegative inches')
    for key in ['table','x','y']:
        if p[key] is not None and (not isinstance(p[key],str) or not p[key].strip()):
            raise ValueError(f'sizing.{key} must be a nonempty name or null')
    return p


def _labels(tables, p, key, style):
    name=p['table']; column=p[key]
    column=style.get('columns',{}).get(column,column)
    if name not in tables or not column or column not in tables[name].columns:
        raise ValueError(f'Bind sizing.table and sizing.{key} to an existing table/column')
    series=tables[name][column]
    if series.empty or series.isna().any():
        raise ValueError('Sizing categories must be nonempty and contain no missing values')
    return [str(v) for v in series.drop_duplicates().tolist()]


def _extent(labels, p, style):
    from matplotlib.font_manager import FontProperties
    from matplotlib.textpath import TextToPath
    font=FontProperties(family=style.get('font_family','DejaVu Sans'),size=p['label_fontsize'])
    measure=TextToPath()
    sizes=[]
    for label in labels:
        lines=label.splitlines() or ['']
        widths=[measure.get_text_width_height_descent(line,font,False)[0]/72 for line in lines]
        sizes.append((max(widths,default=0),len(lines)*p['label_fontsize']*1.2/72))
    return sizes


def _limits(plan):
    for axis in ['width','height']:
        cap=plan['policy']['max_'+axis+'_in']
        if cap is not None and plan[axis+'_in']>cap+1e-9:
            raise ValueError(f'Required {axis} {plan[axis+"_in"]:.3f} in exceeds user limit {cap} in; '
                             'ask the author about layout. Do not shrink spacing/fonts or split panels automatically.')


def _geometry(plan):
    l,r,b,t=plan['margins_in'];w=plan['width_in'];h=plan['height_in']
    if w<=l+r or h<=b+t:
        raise ValueError('Canvas leaves no drawing area after margins')
    plan['rect']=[l/w,b/h,(w-l-r)/w,(h-b-t)/h]
    _limits(plan)
    return plan


def resolve_size(tables, style):
    """Resolve distinct category counts, text measurements, inch sizes and rect.

    style.sizing is template-local; call overrides merge into it explicitly.
    x/y are semantic column names mapped through style.columns if provided.
    Scatter sample count is never used as a canvas driver. profile=fixed keeps
    a domain/aspect-specific canvas. mode=replica preserves explicit dimensions.
    """
    p=validate_policy(style.get('sizing',{}))
    l,r,b,t=p['margins_in'];nx=ny=1
    if p['mode'] in ('fixed','replica') or p['profile']=='fixed':
        w=p['width_in'] if p['width_in'] is not None else style.get('width_in')
        h=p['height_in'] if p['height_in'] is not None else style.get('height_in')
        if w is None or h is None:
            raise ValueError('Fixed/replica sizing requires explicit width_in and height_in')
        for value in [w,h]:
            if isinstance(value,bool) or not isinstance(value,Real) or not math.isfinite(value) or value<=0:
                raise ValueError('Explicit dimensions must be finite positive inches')
    else:
        if p['profile']=='unbound':
            raise ValueError('Sizing profile is unbound; choose category direction, matrix or fixed before rendering')
        slot=p['item_width_in'];row=p['item_height_in']
        if p['profile'] in ('categorical_x','matrix'):
            labels=_labels(tables,p,'x',style);nx=len(labels)
            sizes=_extent(labels,p,style);angle=math.radians(p['label_rotation'])
            projected_w=max((a*math.cos(angle)+c*math.sin(angle) for a,c in sizes),default=0)
            projected_h=max((a*math.sin(angle)+c*math.cos(angle) for a,c in sizes),default=0)
            slot=max(slot,projected_w+p['label_gap_in'])
            b=max(b,projected_h+p['label_gap_in']+.3)
        if p['profile'] in ('categorical_y','matrix'):
            labels=_labels(tables,p,'y',style);ny=len(labels)
            sizes=_extent(labels,p,style)
            l=max(l,max((a for a,c in sizes),default=0)+p['label_gap_in']+.3)
            row=max(row,max((c for a,c in sizes),default=0)+p['label_gap_in'])
        plot_w=nx*slot if p['profile'] in ('categorical_x','matrix') else p['plot_width_in']
        plot_h=ny*row if p['profile'] in ('categorical_y','matrix') else p['plot_height_in']
        w=max(p['min_width_in'],l+r+plot_w)
        h=max(p['min_height_in'],b+t+plot_h)
        for key,required in [('width_in',w),('height_in',h)]:
            explicit=p[key]
            if explicit is not None and explicit<required-1e-9:
                raise ValueError(f'Explicit {key}={explicit} leaves less than required {required:.3f} in; '
                                 'adjust the declared policy or ask the author')
        w=p['width_in'] if p['width_in'] is not None else w
        h=p['height_in'] if p['height_in'] is not None else h
    return _geometry({'width_in':float(w),'height_in':float(h),'margins_in':[l,r,b,t],
                      'counts':{'x':nx,'y':ny},'policy':p,'mode':p['mode']})


def check_region(fig, rect, tables, style):
    """A composed panel never resizes its owner's figure; reject cramped slots."""
    plan=resolve_size(tables,style)
    actual_w=fig.get_figwidth()*rect[2];actual_h=fig.get_figheight()*rect[3]
    need_w=plan['width_in']-plan['margins_in'][0]-plan['margins_in'][1]
    need_h=plan['height_in']-plan['margins_in'][2]-plan['margins_in'][3]
    if actual_w+1e-9<need_w or actual_h+1e-9<need_h:
        raise ValueError(f'Panel region {actual_w:.3f}x{actual_h:.3f} in is smaller than required '
                         f'plot area {need_w:.3f}x{need_h:.3f} in; enlarge the outer layout or ask the author')
    return plan


def draw_figure(draw, tables, style):
    """Standalone shared wrapper -> (figure, handles, resolved plan).

    draw is the very same draw(fig, rect, tables, style) used in composition.
    Adaptive mode reserves extra outside text space using actual rendered bounds;
    plot area/spacing stay constant. Fixed/replica never silently change aspect.
    Export is explicitly owned by the caller. No table mutation or statistics.
    """
    import matplotlib.pyplot as plt
    plan=resolve_size(tables,style)
    fig=plt.figure(figsize=(plan['width_in'],plan['height_in']),dpi=style.get('dpi',100))
    try:
        for attempt in range(3):
            fig.clear();fig.set_size_inches(plan['width_in'],plan['height_in'])
            handles=draw(fig,plan['rect'],tables,style)
            fig.canvas.draw()
            box=fig.get_tightbbox(fig.canvas.get_renderer())
            if box is None:
                return fig,handles,plan
            extra=[max(0,-box.x0),max(0,box.x1-plan['width_in']),
                   max(0,-box.y0),max(0,box.y1-plan['height_in'])]
            if max(extra)<1e-5:
                return fig,handles,plan
            if plan['mode']!='adaptive' or plan['policy']['profile']=='fixed':
                raise ValueError('Text exceeds fixed/replica canvas; adjust explicit margins, preserving source aspect')
            if attempt==2:
                raise ValueError('Text still exceeds canvas after 3 bounded layout passes')
            extra=[v+.03 if v>0 else 0 for v in extra]
            plan['margins_in']=[a+c for a,c in zip(plan['margins_in'],extra)]
            plan['width_in']+=extra[0]+extra[1];plan['height_in']+=extra[2]+extra[3]
            _geometry(plan)
    except Exception:
        plt.close(fig)
        raise
