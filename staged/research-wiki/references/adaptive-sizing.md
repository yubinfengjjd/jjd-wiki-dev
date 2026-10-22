# 可复用函数的结构与尺寸适配

这里 n 是依据课题既定分组定义从实际数据识别的任意合法组数（正整数），不设固定数量白名单，不为每个 n 写分支或另建模板。agent 在做课题时自行绑定数据、识别 n，并按图型、标签、附属元素和版面要求编排尺寸、留白、配色和位置；每项宽/高等默认系数只是可覆盖初值。不得擅自改变研究分组含义来适应图形。作者已指定的样式/尺寸限制继续遵守；未指定时按既有单panel、可读字号和间距原则执行。

## 用途和边界

用于函数化、模板拆出和换数据。源图六组是示例，不是函数上限。分组/系列/标签/配色/布局和尺寸由输入及显式参数决定。统计逻辑维持原含义，缺失分析算法仍先问作者。

## 配置与可移植调用

research-wiki的config.json新增function_defaults.sizing，新Python scaffold-template读取它，写入spec.style.sizing，并复制rwiki/sizing.py为模板code/sizing.py、assets/function_render.py为code/render.py。原有配置缺此键时保留旧脚手架行为。R脚手架维持原语言，其agent须实现同等行为；本次执行辅助模块只为Python，不伪称R通过。

全局默认仅在建模板时快照；已存在模板不会随全局变化。调用--style的sizing对象按键覆盖模板快照。复制code/到课题后，绘图不依赖Wiki或全局config路径。无需安装公共包。

```python
from my_panel.panel import draw
from my_panel.sizing import draw_figure
style = {'font_family':'Arial', 'sizing':{
    'mode':'adaptive', 'profile':'categorical_x',
    'table':'values', 'x':'group', 'item_width_in':0.8,
    'max_width_in':None}}
fig, handles, plan = draw_figure(draw, tables, style)
fig.savefig('result.png', dpi=300)
```

draw(fig,rect,tables,style)只负责给定区域的内容，可返回axes/artists；图例、色标、边缘分布均需适配该区域。独立与render都用draw_figure包裹同一draw，不复制绘图逻辑。模板核心应让标签字号匹配sizing.label_fontsize/label_rotation，配色足够或显式报错，不静默模运算循环颜色。画布尺寸/留白不改变分析结果。

## 字段

mode: adaptive为换数据、fixed/replica使用显式width_in/height_in。profile: categorical_x按x的去重类别数扩宽；categorical_y按y去重类别数增高；matrix按x/y分别增长；fixed用于固定比例（例如不随样本量放大的散点）；unbound为待agent确认数据绑定，执行时报错。

table指spec.tables里的逻辑表名；x/y指类别列，支持style.columns语义列映射，禁止用总行数替代分组数。类别空值/空表须先处理并说明，不静默丢掉。item_width_in/item_height_in是每项最小英寸；plot_width_in/plot_height_in是非增长轴绘图区尺寸；margins_in依次左/右/下/上。min_width_in/min_height_in为整图最小值。width_in/height_in显式覆盖；adaptive覆盖小于必要空间时报错，fixed为作者明确指定的比例方案。

W=左右留白+n_x×每项宽度，H=上下留白+n_y×每项高度；单方向分类图非增长轴用plot_height_in或plot_width_in。label_fontsize/label_rotation/label_gap_in用于文字度量与空隙；长标签可增加单项宽、左/下留白。draw_figure用真实渲染边界补外部留白，最多3轮，保持绘图区的英寸尺寸不变；fixed/replica越界则报错，不改变原比例。字体缺字与各标签互相遮挡仍需实际查看和图型自身QA。

默认max_width_in/max_height_in=null，保持单panel与间距继续增长；只有作者明确指定尺寸上限，才启用上限。超限报所需和允许尺寸，先询问布局；不clamp、不自动分面、不缩字号或隐藏类别。数值字段为明确数值参数，不eval用户公式字符串。公式系数是可调初值，不代表所有图型均已视觉验证。

## 组合调用

组图画布由layout拥有。compose runner对声明sizing的模板调用check_region，以实际rect英寸检查所需绘图区，不resize整图；尺寸不足明确失败。直接组合时调用同一check_region。复杂色标/边缘结构还需其模板额外空间检查。旧模板未声明sizing时按旧入口运行，列为legacy而非自动适配通过。

## 复刻、复用与验证

源图回放使用example/style.json显式设置sizing.mode=replica及width_in/height_in，保持原图比例并核对数值/结构；换数据render默认adaptive，可用--style覆盖。两个验证分别记录，不能把自适应新比例套入复刻宽高比≤2%规则，也不能因为固定六组原图通过就认为任意组数可用。

分类图由agent选择不同于原图规模的若干组数及适当边界案例实际导出，不规定固定测试组数；记录n、宽高、轴/点/箱体数及每组物理间距；另测长标签、显式顺序/列映射、样本数改变不影响类别计数、配色不足、手动宽高、用户上限拒绝和不同cwd复制调用。横向图和矩阵覆盖对应维度。PNG目视/文字边界、PDF/SVG结构和作者签核分别记录。已有模板先盘点适配状态，经逐一授权和验证才迁移历史资产。
