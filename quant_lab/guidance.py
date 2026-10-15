"""Source-aligned guides, tasks and course graph, independent of Streamlit."""

from dataclasses import dataclass
import math

from quant_lab.knowledge import KNOWLEDGE
from quant_lab.learning import LESSONS, lesson_experiment


@dataclass(frozen=True)
class Guide:
    purpose: str
    controls: tuple[tuple[str, str], ...]
    steps: tuple[str, ...]
    example: str
    errors: tuple[str, ...]
    topics: tuple[str, ...]
    next_page: str


GUIDES = {
    "市场数据": Guide("选择研究标的，核对基础资料与历史价格；用于描述已经发生的交易。",
        (("市场 / 股票（代码 / 名称）", "先选市场，可搜名称或代码；候选会填入规范代码。手动支持 SH/SZ/BJ/HK 标识。格式正确不证明仍上市。"),
         ("历史区间 / 价格口径", "设置日期和不复权、前复权、后复权；只使用实际返回交易日。"),
         ("加载真实历史日线", "联网获取并校验；错误会显示，不用演示图补充金融指标。"),
         ("立即更新历史日线 / 自动刷新", "手动绕过缓存，自动仅在市场页运行；核对成功时间与缓存状态。"),
         ("重新获取证券名称 / 更新股票候选目录", "名称和搜索目录独立更新；失败保留最近有效记录。"),
         ("K 线 / 价格与成交量图 / CSV", "K 线显示开高低收，柱形显示成交量，导出当前已验证日线。"),
         ("加入自选 / 移除所选 / 立即更新自选股", "管理最多 10 只股票；快照只是最近历史日线收盘参考。")),
        ("选择 A 股，搜索贵州茅台或输入 SH600519；港股示例 HK00700。", "选择至少一年的区间和价格口径，加载历史日线。", "核对名称、市场、币种、来源、交易日、成功获取时间、缓存状态和错误。", "阅读 K 线与成交量，再到策略实验室；缺少报价时钟或资料不完整时明确记为未知。"),
        "离线可复现：在 Quant Academy 看固定教学价格；联网后用自己的查询区间观察 600519。示例不保证上游随时可用，也不预设收益结果。",
        ("无网络：保留已验证缓存，检查错误与成功时间；没有有效数据时指标为空。", "名称不可用：点击重新获取名称，不据此断言证券不存在。", "日期为空或开始晚于结束：重新选择完整区间。", "名称目录不是当前上市资格验证，指数不属于股票研究范围。"),
        ("simple_return", "moving_average", "variance", "volatility"), "策略实验室"),
    "策略实验室": Guide("把假设转成只使用当日及此前价格的可检查信号。",
        (("策略类型", "单均线、双均线、趋势过滤，均使用内置规则。"), ("短周期（交易日） / 长周期（交易日）", "2 ≤ 短周期 < 长周期 ≤ 250；均线有预热期。"), ("收盘价 / 均线 / 信号图", "三角标记是收盘后信号，不是实际成交。")),
        ("先加载当前股票的历史日线。", "选双均线，先用 10/30 日；观察两条均线和收盘信号。", "只改一个窗口，比较信号敏感性；记录为何这样设置。", "去历史回测配置相同策略和成本，检验信号能否按规则成交。"),
        "固定课例：10、12、14 的 3 日均线为 12；调整窗口观察滞后。实际股票的信号必须以当前数据计算。",
        ("短周期不小于长周期：修正窗口。", "没有信号：检查样本是否足够预热；没有信号并非程序故障。", "不能把收盘后信号按同日收盘价执行。"), ("moving_average", "bias"), "历史回测"),
    "历史回测": Guide("在明确成交与成本假设下检验规则，比较基准及样本外结果。",
        (("策略类型 / 短周期 / 长周期", "与策略实验室相同的内置规则。"), ("成交与费用假设（均可调整）", "初始资金、整手数量、佣金、最低佣金、买卖附加费、滑点及 A 股简化涨跌停；都是研究假设。"), ("样本内比例", "较早区间用于参数研究，较晚区间评估。"), ("运行历史回测", "收盘信号最早下一交易日开盘模拟成交，估值与成交使用不复权价。"), ("净值图 / 交易与未成交记录 / 参数敏感性", "基准成本一致；敏感性只看样本内，黄色线后为样本外。"), ("保存本次实验与研究笔记 / 保存实验", "保存标题、假设、判断、参数、成本和两份输入快照；不是只存截图。")),
        ("先加载日线，设定可检验的均线假设。", "选择双均线 10/30、样本内比例 70%，核对市场对应成本。", "运行回测，比较策略、基准、样本内外和订单未成交原因。", "先解释回撤和成本，再填写研究标题、假设、学习笔记并保存实验。"),
        "无网络可复现：使用自动化测试的小样本验证次日开盘成交。软件真实研究需要先取得历史行情；不要预设某只股票回测一定盈利。",
        ("复权数据可生成信号，不能用作当时成交价。", "成交价读取失败时停止实验，不能混用缓存批次。", "无订单：检查预热、信号变化、整手数量和不可成交记录。", "反复看样本外后调参会污染测试集。"),
        ("drawdown", "sharpe", "volatility", "annual_return", "costs", "slippage", "bias"), "研究笔记"),
    "风险与组合": Guide("描述历史风险，并比较同市场同币种的数学组合。",
        (("单资产风险", "方差、标准差、波动率、回撤来自当前价格序列。"), ("组合股票代码（逗号分隔，2–4 只）", "仅当前市场、不重复代码；不会合并 CNY/HKD。"), ("组合权重训练比例 / 分析同市场组合", "较早共同交易日估计等权/逆波动权重，较晚区间测试。"), ("相关 / 协方差 / 权重 / 净值图", "日期内连接；数学日再平衡曲线未计调仓成本。")),
        ("加载一只股票，先读单资产波动与回撤。", "A 股示例输入 600519,000001，确认币种一致。", "保持训练比例 70%，分析组合，核对共同交易日和权重。", "比较样本外曲线与相关性，记录未计成本的限制。"),
        "离线课例 X=[1,2,3]、Y=[2,4,6] 的相关为 1；改 Y 中间值观察关系变化。真实组合依赖上游数据。",
        ("重复代码或跨市场：只保留 2–4 个同市场规范代码。", "共同交易日不足或零波动：不编造权重/相关。", "低历史相关不保证未来分散；每日调仓成本尚未建模。"),
        ("variance", "volatility", "drawdown", "correlation", "covariance"), "统计与机器学习"),
    "统计与机器学习": Guide("先检验历史收益均值，再检验简单线性模型的样本外预测误差；当前是回归研究，不是分类交易系统。",
        (("日收益率样本量 / 日均收益 / 年化波动 / p 值", "加载后自动统计，t 检验零假设是日均收益为 0；p 值不是上涨或盈利概率。"), ("机器学习训练比例", "55%–85%；按时间顺序分割，训练/测试边界隔一行，默认 70%。"), ("运行时间序列线性回归", "特征为 1/5 日收益、5/20 日均线比值减 1、成交量变化、10 日波动。标签为下一日收盘收益。"), ("MAE / 零收益基线 MAE / R² / 方向一致率", "比较平均误差、均值参考与方向，不等同交易收益。"), ("预测曲线 / 标准化系数 / 训练期交叉验证", "标准化仅拟合训练集；3 折带间隔时间序列验证，不随机混合未来样本。")),
        ("研究问题：只用今天收盘后可知信息，能否比每天预测零更准确地预测次日收盘收益？", "先选股票、至少一年历史区间和一致价格口径，加载日线。", "查看有效收益样本、均值和波动，核对 p 值假设。", "保持训练比例 70%，运行回归；至少需要 60 行有效特征，通常须 80 个以上交易日。", "先比较模型 MAE 与零收益基线，再看 R²、方向、训练期 CV 与测试图。", "检查特征日期与次日标签，另选未用过区间复核；预测不能按今日收盘价成交，需要另做执行和成本回测。"),
        "教学误差：实际 [1%,−1%]、预测 [0,0]，MAE=1%。实际 [1,3]、预测 [0,0] 时 R²=−4。联网案例不预设预测指标，图中实际与预测均对应 target_date。",
        ("有效特征不足：扩展区间，均线预热和缺失量价会减少样本。", "MAE 大于零基线或 R² 负值：这是有效失败结果，不删除或只汇报好区间。", "全量数据先标准化、随机划分、特征用未来收盘均会泄漏。", "方向一致率高不保证盈利；分类准确率不适合替代当前回归误差。", "自相关、厚尾、非平稳、反复试参数削弱检验；当前没有分类器、因子框架或自动交易转换。"),
        ("variance", "std", "correlation", "p_value", "mae", "r_squared", "bias"), "历史回测"),
    "AI 研究助手": Guide("用已有 DeepSeek 草拟有界研究假设并审阅本地证据，所有模型判断需复核。",
        (("DeepSeek API Key / 模型 / 回答模式", "本页集中配置，密钥只进会话或 Windows 凭据管理器。"), ("研究问题 / 生成 AI 假设", "显式按钮发送付费请求，JSON 输出经本地字段与参数验证。"), ("运行受控实验（内置策略）", "本地执行均线实验；没有 Key 也可用固定模板。"), ("让 AI 审阅实验 / 下载可复核研究报告", "审阅会付费，下载含本地证据、指纹和实际模型；示例代码只展示。")),
        ("先加载日线；已有 DeepSeek 配置直接共用。", "写可检验问题，再显式生成假设，检查假设、风险和周期。", "运行本地受控实验，独立核对数值。", "按需审阅或在“对话与辅导”选择教学辅导，核对摘要后发送。"),
        "无 Key 的可复现步骤：加载已有有效行情后运行固定双均线模板，阅读审计指纹并下载报告；离线知识和课程不需要模型。",
        ("无 Key/模型：本地课程与实验照常，模型按钮不可用。", "401/402/429：分别核对鉴权、账户余额和限频；无自动付费重试。", "JSON 不完整或周期无效：保留错误，手动重试。", "AI 文本不是计算事实，不能执行模型给出的代码。"),
        ("moving_average", "bias", "drawdown"), "研究笔记"),
    "Quant Academy": Guide("八节已有金融数学参数实验，固定教学样本可无网络运行。",
        (("选择课程", "选择收益、均线、方差、波动、回撤、夏普、相关或过拟合。"), ("Python 实现 / 调参数试一试", "代码供阅读，滑块运行内置函数；表格与结论不是行情。"), ("知识解释 / 向 AI 追问", "解释当前教学值，追问只准备草稿。")),
        ("选择最大回撤课程，先手算 100→120→90→100。", "调低点净值，观察回撤相对此前峰值如何变化。", "在新手使用指引的课程与练习中保存实验和答题记录。", "返回历史回测对照真实实验，检查样本与口径区别。"),
        "低点 90 时 100→120→90→100 的最大回撤为 −25%；把低点改为 120，再比较结果。",
        ("表格是教学样本，不能当作证券行情。", "没有 Key 也能使用全部离线内容。", "看过示例不等于完成课程；学习中心需保存实验并通过测验。"),
        ("simple_return", "volatility", "drawdown", "sharpe", "correlation"), "新手使用指引"),
    "研究笔记": Guide("保存和复算数据固定的研究档案，并管理私人学习笔记。",
        (("选择实验", "读取保存时的标的、名称、输入和假设，不用当前查询覆盖。"), ("导出 Markdown 研究报告 / 导出可复现研究包 ZIP", "ZIP 含不复权成交价、信号价、假设和指标。"), ("从存档数据重新计算", "核对存档 SHA-256 并用原始参数复算指纹。"), ("学习笔记标题 / 内容 / 保存手写学习笔记", "私人内容默认不附带 AI，与实验快照分别保存。")),
        ("在历史回测保存标题、假设和自己的判断。", "打开研究笔记，选择实验，核对数据时间、口径和成本。", "从存档数据重新计算，确认原指纹一致。", "导出 ZIP 后比较两份价格输入，记录下一次独立检验计划。"),
        "离线复现：已有归档实验可直接复算与导出；新实验需要先有有效行情。名称后来改变也不改写保存时名称。",
        ("无实验：先到历史回测运行并保存。", "快照校验或解压失败：显示错误，不用新行情代替归档。", "不要把 Key 粘贴进学习笔记，私人判断不是自动 AI 上下文。"),
        ("bias", "drawdown", "sharpe"), "新手使用指引"),
    "新手使用指引": Guide("在应用内完成从选股、研究到解释和保存的入门链，管理学习过程。",
        (("学习中心分区", "切换界面指南、入门任务、学习路径、课程与练习、学习进度。"), ("查看本页使用指南 / 返回研究任务", "原生导航帮助，保留当前研究数据与控件。"), ("新手模式 / 专业模式", "只改变提示，不影响金融计算。"), ("保存实验记录 / 提交课程测验", "明确操作后持久化教学记录，通过练习才标课程完成。"), ("重置学习进度", "显式确认后只清学习进度和测验，保留行情、研究档案、笔记、密钥。")),
        ("首次欢迎可开始或跳过，学习进度页可重新启动。", "按入门任务打开对应研究页，查看证据与完成条件。", "从相关术语进入课程，调参数、保存实验并答题。", "保存学习目标与私人笔记，重启后继续；返回按钮回到此前研究任务。"),
        "离线即可完成回撤交互实验与测验，退出重启后继续；需要真实行情的任务不会用教学数据自动完成。",
        ("计划中路径节点不能标为已完成课程。", "任务证据表示历史完成，不证明当前股票查询有效。", "进度保存失败会显示错误，不伪装完成。"),
        ("simple_return", "drawdown", "bias"), "市场数据"),
}


@dataclass(frozen=True)
class Course:
    topic: str
    lesson: int
    prerequisites: tuple[str, ...]
    page: str
    quiz: str
    expected: float
    explanation: str


COURSES = {
    "simple_return": Course("simple_return", 0, (), "市场数据", "本金 200，先涨 10% 再跌 10%，最终本金是多少？（输入金额）", 198, "200×1.1×0.9=198；每期的基数发生变化。"),
    "moving_average": Course("moving_average", 1, ("simple_return",), "策略实验室", "收盘价 10、14、18 的 3 日均线是多少？", 14, "(10+14+18)/3=14，只有第三天收盘后才知道。"),
    "variance": Course("variance", 2, ("simple_return",), "风险与组合", "样本 1、3、5 的样本方差是多少？（分母 n−1）", 4, "均值 3；平方偏差 4+0+4，除以 2 得 4。"),
    "volatility": Course("volatility", 3, ("variance",), "风险与组合", "日收益标准差 2%，按 252 日近似年化，约为多少 %？（输入百分数，如 15.87）", 2*math.sqrt(252), "2×√252≈31.749%，前提是平方根年化近似适用。"),
    "drawdown": Course("drawdown", 4, ("simple_return",), "历史回测", "净值 100、80、90 的最大回撤是多少 %？（本软件用负数）", -20, "峰值始终是 100，最低 80/100−1=−20%；后来回升不能消除历史回撤。"),
    "sharpe": Course("sharpe", 5, ("volatility", "simple_return"), "历史回测", "两日收益 −1%、+1%，无风险收益 0，平均收益 0 且波动非零，夏普是多少？", 0, "分子为 0、分母非零，年化后仍为 0；两个样本只用于教学。"),
    "correlation": Course("correlation", 6, ("variance",), "风险与组合", "X=[1,2,3]，Y=[6,4,2]，相关系数是多少？", -1, "两者完全线性反向，相关为 −1；不代表因果。"),
    "bias": Course("bias", 7, ("moving_average",), "统计与机器学习", "看过测试集后反复选参，该测试集还独立吗？独立输入 1，不独立输入 0。", 0, "测试结果参与了决策；需要新的未使用样本，不能继续称它为独立样本外。"),
}


PATHS = {
    "金融基础": (("股票与证券市场", None), ("A 股与港股交易制度", None), ("价格与收益率", "simple_return"), ("风险和波动率", "volatility"), ("最大回撤", "drawdown"), ("风险收益与夏普", "sharpe"), ("组合先修：资产相关", "correlation"), ("投资组合", None), ("市场效率与交易策略", None), ("策略研究先修：回测偏差", "bias")),
    "数学与统计学": (("函数与对数", None), ("描述性统计", None), ("概率分布", None), ("方差与标准差", "variance"), ("协方差与相关系数", "correlation"), ("假设检验", None), ("线性回归", None), ("时间序列", None), ("最优化", None)),
    "Python 与计算机科学": (("Python 基础", None), ("NumPy", None), ("pandas 与移动平均", "moving_average"), ("数据清洗", None), ("数据可视化", None), ("数据库", None), ("API", None), ("回测系统与偏差", "bias"), ("自动化测试", None), ("软件架构", None)),
    "量化研究与机器学习": (("研究假设", None), ("技术指标", "moving_average"), ("信号设计", None), ("回测与偏差", "bias"), ("风险评估", "drawdown"), ("样本外测试", None), ("因子研究", None), ("机器学习建模", None), ("模型稳定性分析", None)),
}


@dataclass(frozen=True)
class Task:
    title: str
    goal: str
    prerequisites: tuple[str, ...]
    steps: tuple[str, ...]
    condition: str
    error: str
    course: str
    page: str
    automatic: bool


TASKS = {
    "select_security": Task("1 · 找到并选择股票", "选择一个明确市场的证券身份。", (), ("先选 A 股或港股。", "搜索公司名称或代码选择候选，或手动输入带市场标识的代码。"), "实际发生选择/加载操作，代码规范且有可核对的基础资料；默认填入代码不算完成。", "代码位数不是身份验证；目录不保证当前可交易。", "simple_return", "市场数据", True),
    "load_history": Task("2 · 查看基本资料与历史行情", "核对名称和已经验证的历史日线。", ("select_security",), ("核对市场、公司名称、来源。", "选日期与口径，加载日线，确认返回非空且无校验/更新错误。"), "加载成功的非教学历史日线与名称；空数据、失败和演示图不计。", "名称资料失败应重试；不要断言证券不存在。", "simple_return", "市场数据", True),
    "read_chart": Task("3 · 认识 K 线、成交量与收益", "区分开高低收、数量和收益比例。", ("load_history",), ("在市场页对照表格观察一根 K 线和成交量柱。", "口头解释首尾价格收益，不将其当成含分红收益。", "回到这里明确确认。"), "有任务 2 的有效历史记录，用户明确确认已核对图表。", "K 线不表示下一天方向；演示图不是当前股票。", "simple_return", "市场数据", False),
    "read_quality": Task("4 · 核对更新时间与质量", "分清行情交易日、接收时间和缓存。", ("load_history",), ("阅读市场页数据更新状态和来源。", "检查最后交易日、成功获取时间、缓存/失败标志；精确报价时钟缺失时记为未知。", "回到这里确认，不将重绘时间当作行情时间。"), "有效历史任务记录加用户的明确核对确认。", "日线日期不是实时报价时间；自然日缺口不能直接判停牌。", "bias", "市场数据", False),
    "choose_strategy": Task("5 · 选择并理解策略", "把研究假设变成可复核规则。", ("read_chart",), ("进入策略实验室，选择均线/趋势规则。", "设有效短/长窗口，确认样本有足够预热期。", "解释为什么只能收盘后产生信号。"), "当前非教学行情上成功生成有可计算均线的有效策略信号。", "没有非零买入信号也可能是合法结果；不能同日收盘执行。", "moving_average", "策略实验室", True),
    "run_backtest": Task("6 · 完成一次历史回测", "用明确成本和执行假设检验规则。", ("choose_strategy",), ("历史回测选规则，核对整手、费用、滑点和市场。", "运行并查看基准、订单、样本内外。"), "非教学历史数据上的本地回测成功，保存有效审计指纹。", "失败、无结果不完成；高收益不是质量门槛。", "bias", "历史回测", True),
    "interpret_risk": Task("7 · 解释风险收益指标", "能够解释年化近似、最大回撤和夏普的边界。", ("run_backtest",), ("阅读回测年化收益、回撤和夏普。", "完成相关课程或明确确认已经能解释指标单位、假设和零波动情形。"), "有成功回测证据，用户明确确认理解；不是 AI 自动判定掌握。", "历史回撤不是未来损失上限，高夏普不保证盈利。", "drawdown", "历史回测", False),
    "save_research": Task("8 · 保存研究并记录判断", "保存可复现数据和自己的结论。", ("run_backtest",), ("填写研究标题、假设和自己的学习笔记。", "保存实验，在研究笔记查看或导出、复算。"), "实际保存实验成功且判断笔记非空，记录实验 ID 与审计指纹。", "只看结果或下载图片不算保存；私人判断默认不传给 AI。", "bias", "研究笔记", True),
}


def course_experiment(course_id, parameter):
    course = COURSES[course_id]
    lesson = LESSONS[course.lesson]
    if not math.isfinite(float(parameter)) or not lesson.minimum <= parameter <= lesson.maximum:
        raise ValueError("教学参数超出课程范围。")
    return lesson_experiment(course.lesson, parameter)


def check_answer(course_id, value):
    expected = COURSES[course_id].expected
    try:
        answer = float(value)
    except (TypeError, ValueError):
        return False
    return math.isfinite(answer) and math.isclose(answer, expected, abs_tol=0.02, rel_tol=0)


def task_evidence_valid(task_id, evidence):
    """Evidence comes from successful app actions, not guessed widget defaults."""
    if task_id not in TASKS or not evidence:
        return False
    if task_id == "select_security":
        return bool(evidence.get("selected") and evidence.get("identity_known") and evidence.get("symbol"))
    if task_id == "load_history":
        return bool(evidence.get("history_valid") and evidence.get("company_name") and not evidence.get("demonstration"))
    if task_id == "choose_strategy":
        return bool(evidence.get("signals_valid") and evidence.get("data_fingerprint") and not evidence.get("demonstration"))
    if task_id == "run_backtest":
        return bool(evidence.get("audit_id") and evidence.get("backtest_success") and not evidence.get("demonstration"))
    if task_id == "save_research":
        return bool(evidence.get("experiment_id") and evidence.get("audit_id") and evidence.get("has_judgment") and not evidence.get("demonstration"))
    return evidence.get("confirmed") is True


def validate_catalog():
    for page, guide in GUIDES.items():
        assert guide.next_page in GUIDES and all(topic in KNOWLEDGE for topic in guide.topics), page
    for course in COURSES.values():
        assert course.topic in KNOWLEDGE and course.page in GUIDES
        assert all(prerequisite in COURSES for prerequisite in course.prerequisites)
    for nodes in PATHS.values():
        assert all(course is None or course in COURSES for _, course in nodes)
    for task in TASKS.values():
        assert task.course in COURSES and task.page in GUIDES
        assert all(prerequisite in TASKS for prerequisite in task.prerequisites)
