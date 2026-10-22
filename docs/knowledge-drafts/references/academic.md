# 学术与教材来源库

整理日期：2026-10-22

## 使用说明

- `A` 编号用于论文、教材、专著和大学公开课程资料。
- 书目信息按通行出版信息整理；2026-10-22 未能联网逐条核验 DOI、页码和版本，标记 `NEEDS_REVIEW`。正式发布前应通过出版社、DOI 或大学课程页面复核。
- 学术来源用于定义、公式、假设和边界的背景说明，不用于证明某个策略未来有效，也不构成投资建议。
- 引用时优先指向原始论文、出版社页面或课程原始页面；不使用搜索结果链接、聚合转载或内容农场。

## 论文与教材

| ID | 作者与年份 | 标题 | 出版信息 | DOI / ISBN / URL | 支持的具体主张 | 批次 1 使用 |
| --- | --- | --- | --- | --- | --- | --- |
| A001 | Markowitz, H. (1952) | Portfolio Selection | The Journal of Finance, 7(1), 77–91 | DOI: 10.1111/j.1540-6261.1952.tb01525.x | 组合分散化、均值-方差框架；组合权重与相关性 | risk_portfolio |
| A002 | Sharpe, W. F. (1966) | Mutual Fund Performance | The Journal of Business, 39(1), 119–138 | DOI: 10.1086/294846 | 风险调整收益、夏普比率背景 | academy |
| A003 | Student (W. S. Gosset) (1908) | The Probable Error of a Mean | Biometrika, 6(1), 1–25 | DOI: 10.2307/2331554 | 小样本均值检验、t 分布 | statistics_ml |
| A004 | Hyndman, R. J., & Athanasopoulos, G. (2021) | Forecasting: Principles and Practice (3rd ed.) | OTexts | [OTexts FPP3](https://otexts.com/fpp3/) | 时间序列预测、评估、残差和交叉验证 | statistics_ml |
| A005 | Bergmeir, C., & Benítez, J. M. (2012) | On the use of cross-validation for time series predictor evaluation | Information Sciences, 191, 192–213 | DOI: 10.1016/j.ins.2011.12.028 | 时间序列交叉验证的适用条件与风险 | statistics_ml |
| A006 | Bailey, D. H., Borwein, J. M., López de Prado, M., & Zhu, Q. J. (2014) | Pseudo-Mathematics and Financial Charlatanism: The Effects of Backtest Overfitting on Out-of-Sample Performance | Notices of the American Mathematical Society, 61(5), 458–471 | DOI: 10.1090/noti1105 | 回测过拟合、样本外表现和试错次数 | quick_start, backtest |
| A007 | White, H. (2000) | A Reality Check for Data Snooping | Econometrica, 68(5), 1097–1126 | DOI: 10.1111/1468-0262.00152 | 数据窥探、多重检验和模型比较 | backtest |
| A008 | Lo, A. W., Mamaysky, H., & Wang, J. (2000) | Foundations of Technical Analysis: Computational Algorithms, Statistical Inference, and Empirical Implementation | The Journal of Finance, 55(4), 1705–1765 | DOI: 10.1111/0022-1082.00265 | 技术分析规则（包括移动平均）的计算与统计检验 | strategy |
| A009 | Casella, G., & Berger, R. L. (2002) | Statistical Inference (2nd ed.) | Duxbury | ISBN: 978-0534243128 | 样本与总体、方差、标准误、假设检验、置信区间 | risk_portfolio, statistics_ml, academy |
| A010 | James, G., Witten, D., Hastie, T., & Tibshirani, R. (2021) | An Introduction to Statistical Learning (2nd ed.) | Springer | DOI: 10.1007/978-1-0716-1418-1；[statlearning.com](https://www.statlearning.com/) | 线性回归、训练/测试误差、R²、基线、交叉验证 | statistics_ml |
| A011 | McKinney, W. (2010) | Data Structures for Statistical Computing in Python | Proceedings of the 9th Python in Science Conference, 56–61 | DOI: 10.25080/Majora-92bf1922-00a | pandas Series/DataFrame 的数据结构与计算 | 后续批次 |
| A012 | Harris, C. R., Millman, K. J., van der Walt, S. J., et al. (2020) | Array programming with NumPy | Nature, 585, 357–362 | DOI: 10.1038/s41586-020-2649-2 | NumPy 数组、向量化和数值计算 | 后续批次 |
| A013 | Elton, E. J., Gruber, M. J., Brown, S. J., & Goetzmann, W. N. (2014) | Modern Portfolio Theory and Investment Analysis (9th ed.) | Wiley | ISBN: 978-1118469941 | 组合理论、等权/逆波动率、再平衡和换手 | risk_portfolio |
| A014 | Magdon-Ismail, M., & Atiya, A. F. (2004) | Maximum Drawdown | Risk Magazine, 17(10), 99–102 | 出版信息按通行引用整理 | 最大回撤的定义、路径依赖和恢复 | 后续批次 |
| A015 | Harvey, C. R., Liu, Y., & Zhu, H. (2016) | ... and the Cross-Section of Expected Returns | The Review of Financial Studies, 29(1), 5–68 | DOI: 10.1093/rfs/hhv059 | 多重检验、因子研究和显著性阈值 | 后续批次 |
| A016 | López de Prado, M. (2018) | Advances in Financial Machine Learning | Wiley | ISBN: 978-1119482086 | 金融机器学习中的数据泄漏、时间切分、交叉验证和回测风险 | 后续批次 |
| A017 | Fama, E. F. (1970) | Efficient Capital Markets: A Review of Theory and Empirical Work | The Journal of Finance, 25(2), 383–417 | DOI: 10.2307/2325486 | 市场效率、策略收益解释的背景 | 后续批次 |
| A018 | Box, G. E. P. (1976) | Science and Statistics | Journal of the American Statistical Association, 71(356), 791–799 | DOI: 10.1080/01621459.1976.10480949 | 模型近似、过拟合和“所有模型都不完全正确”的认识论背景 | 后续批次 |
| A019 | Wooldridge, J. M. (2020) | Introductory Econometrics: A Modern Approach (7th ed.) | Cengage | ISBN: 978-1337558860 | 线性回归、假设检验、自相关和稳健标准误 | 后续批次 |
| A020 | Tsay, R. S. (2010) | Analysis of Financial Time Series (3rd ed.) | Wiley | ISBN: 978-0470414354 | 金融时间序列、自相关、波动率和非平稳性 | 后续批次 |
| A021 | Newey, W. K., & West, K. D. (1987) | A Simple, Positive Semi-Definite, Heteroskedasticity and Autocorrelation Consistent Covariance Matrix | Econometrica, 55(3), 703–708 | DOI: 10.2307/1913610 | 自相关/异方差下的标准误 | 后续批次 |
| A022 | Mandelbrot, B. (1963) | The Variation of Certain Speculative Prices | The Journal of Business, 36(4), 394–419 | DOI: 10.1086/294632 | 厚尾分布、波动聚集和正态假设的局限 | 后续批次 |
| A023 | Pedregosa, F., et al. (2011) | Scikit-learn: Machine Learning in Python | Journal of Machine Learning Research, 12, 2825–2830 | [JMLR](https://jmlr.org/papers/v12/pedregosa11a.html) | scikit-learn 的实现和评估工具 | 后续批次 |
| A024 | Efron, B., & Tibshirani, R. J. (1993) | An Introduction to the Bootstrap | Chapman & Hall | ISBN: 978-0412042317 | 抽样分布、标准误和重采样 | 后续批次 |
| A025 | Grinold, R. C., & Kahn, R. N. (2000) | Active Portfolio Management (2nd ed.) | McGraw-Hill | ISBN: 978-0070248823 | 主动组合管理、风险模型和权重约束 | 后续批次 |
| A026 | Bacon, C. R. (2008) | Practical Portfolio Performance Measurement and Attribution (2nd ed.) | Wiley | ISBN: 978-0470059289 | 收益、风险、回撤和绩效归因 | 后续批次 |
| A027 | Ang, A. (2014) | Asset Management: A Systematic Approach to Factor Investing | Oxford University Press | ISBN: 978-0199959327 | 资产配置、因子和组合风险 | 后续批次 |
| A028 | Hamilton, J. D. (1994) | Time Series Analysis | Princeton University Press | ISBN: 978-0691042893 | 时间序列、自相关、平稳性和模型 | 后续批次 |
| A029 | Wasserman, L. (2004) | All of Statistics: A Concise Course in Statistical Inference | Springer | ISBN: 978-0387402727 | 统计推断、抽样分布、假设检验和置信区间 | 后续批次 |

## 大学公开课程

| ID | 课程 | 机构 | 原始页面 | 支持的具体主张 | 核验状态 |
| --- | --- | --- | --- | --- | --- |
| A030 | 18.05 Introduction to Probability and Statistics | MIT OpenCourseWare | [MIT OCW 18.05](https://ocw.mit.edu/courses/18-05-introduction-to-probability-and-statistics-spring-2014/) | 概率、抽样分布、假设检验、置信区间 | NEEDS_REVIEW：页面未联网复核 |
| A031 | CS229 Machine Learning | Stanford University | [CS229](https://cs229.stanford.edu/) | 监督学习、线性回归、模型评估和过拟合 | NEEDS_REVIEW：页面未联网复核 |

## 批次 1 引用说明

- `quick_start` 使用 A006 说明回测过拟合和样本外表现。
- `strategy` 使用 A008 说明技术分析规则的计算和统计检验背景。
- `backtest` 使用 A006、A007 说明过拟合和数据窥探。
- `risk_portfolio` 使用 A001、A013、A009 说明组合、权重和统计口径。
- `statistics_ml` 使用 A003、A004、A005、A009、A010 说明 t 检验、时间序列切分和回归评估。
- `academy` 使用 A002、A009 说明夏普比率和样本方差。
- 其余来源用于后续批次；未在批次 1 文章中直接引用。

## 待复核事项

1. 所有 DOI、ISBN、页码、版次和作者列表需在正式发布前通过出版社、DOI 或图书馆目录复核。
2. `A014` 的《Maximum Drawdown》是 Risk Magazine 文章，引用格式和页码需确认；如无法核实，正式文章应改用教材中的最大回撤定义并标记来源。
3. `A030`、`A031` 的课程页面和讲义版本需确认；公开课程链接可能随学期调整。
4. 教材中的公式和符号可能与本项目实现不同（例如样本/总体分母、年化交易日数、无风险利率口径）；文章必须明确采用哪一种，并与 `docs/METHODOLOGY.md` 对齐。
