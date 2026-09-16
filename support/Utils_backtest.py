"""
回测结果分析模块

提供回测结果分析的完整功能，包括数据加载、回测报告分析、风险分析、模型性能分析等。
"""

import pandas as pd
import numpy as np
import plotly.graph_objects as go
from typing import Dict, Tuple, List
from qlib.contrib.report import analysis_position, analysis_model
from qlib.contrib.evaluate import risk_analysis
from qlib.contrib.eva.alpha import calc_ic
from scipy import stats as scipy_stats


# ==================== 工具函数 ====================

def calculate_drawdown_stats(returns: pd.Series) -> Dict:
    """计算回撤统计信息"""
    cum_returns = returns.cumsum()
    cum_max = cum_returns.cummax()
    drawdown = cum_returns - cum_max
    max_drawdown = drawdown.min()
    
    mdd_end = drawdown.idxmin()
    mdd_start = cum_returns.loc[:mdd_end].idxmax()
    
    if isinstance(mdd_start, str) and isinstance(mdd_end, str):
        from datetime import datetime
        start_date = datetime.strptime(mdd_start, '%Y-%m-%d')
        end_date = datetime.strptime(mdd_end, '%Y-%m-%d')
        duration = (end_date - start_date).days
    else:
        duration = (mdd_end - mdd_start).days if hasattr(mdd_end - mdd_start, 'days') else None
    
    return {
        '最大回撤': max_drawdown,
        '回撤起始日期': mdd_start,
        '回撤结束日期': mdd_end,
        '回撤持续天数': duration
    }


# ==================== 数据加载 ====================

def load_backtest_data(recorder, analysis_freq: str = "1day") -> Tuple[pd.DataFrame, Dict, pd.DataFrame]:
    """加载回测数据"""
    report_normal_df = recorder.load_object(f"portfolio_analysis/report_normal_{analysis_freq}.pkl")
    positions = recorder.load_object(f"portfolio_analysis/positions_normal_{analysis_freq}.pkl")
    analysis_df = recorder.load_object(f"portfolio_analysis/port_analysis_{analysis_freq}.pkl")
    return report_normal_df, positions, analysis_df


def get_backtest_data_info(report_normal_df: pd.DataFrame, positions: Dict, analysis_df: pd.DataFrame) -> Dict[str, pd.DataFrame]:
    """获取回测数据的基本信息"""
    report_info = pd.DataFrame({
        '属性': ['数据类型', '数据形状', '列名', '时间范围（开始）', '时间范围（结束）'],
        '值': [
            type(report_normal_df).__name__,
            f"{report_normal_df.shape[0]:,} × {report_normal_df.shape[1]}",
            ', '.join(report_normal_df.columns.tolist()),
            str(report_normal_df.index.min()),
            str(report_normal_df.index.max()),
        ]
    })
    report_info.set_index('属性', inplace=True)
    
    position_info = pd.DataFrame({
        '属性': ['数据类型', '持仓日期数量', '最早日期', '最晚日期'],
        '值': [
            type(positions).__name__,
            f"{len(positions):,}",
            str(min(positions.keys())),
            str(max(positions.keys())),
        ]
    })
    position_info.set_index('属性', inplace=True)
    
    analysis_info = pd.DataFrame({
        '属性': ['数据形状', '列名', '索引名称', '索引值数量'],
        '值': [
            f"{analysis_df.shape[0]:,} × {analysis_df.shape[1]}",
            ', '.join(analysis_df.columns.tolist()),
            ', '.join([str(name) for name in analysis_df.index.names if name is not None]) 
            if hasattr(analysis_df.index, 'names') and analysis_df.index.names 
            else str(type(analysis_df.index).__name__),
            f"{len(analysis_df.index):,}"
        ]
    })
    analysis_info.set_index('属性', inplace=True)
    
    return {'report_info': report_info, 'position_info': position_info, 'analysis_info': analysis_info}


# ==================== 回测报告分析 ====================

def extract_report_subplot(original_fig: go.Figure, yaxis_name: str, title: str, width: int = 1200, height: int = 600) -> go.Figure:
    """从report_graph的figure中提取指定子图"""
    subplot_traces = [trace for trace in original_fig.data if trace.yaxis == yaxis_name]
    fig = go.Figure(data=subplot_traces)
    fig.update_layout(
        width=width, height=height, title=title,
        xaxis=dict(type='category', tickangle=45, showline=True),
        yaxis=dict(zeroline=True, showline=True, showticklabels=True),
        hovermode='x unified',
        legend=dict(x=0.01, y=0.99, bordercolor="Black", borderwidth=1)
    )
    return fig


def analyze_cumulative_return(report_normal_df: pd.DataFrame) -> Dict[str, pd.DataFrame]:
    """分析累计收益"""
    cum_bench = report_normal_df['bench'].cumsum()
    cum_return_wo_cost = report_normal_df['return'].cumsum()
    cum_return_w_cost = (report_normal_df['return'] - report_normal_df['cost']).cumsum()
    
    cum_return_stats = pd.DataFrame({
        '指标': ['基准累计收益', '策略累计收益(不含成本)', '策略累计收益(含成本)', '交易成本影响'],
        '最终值': [cum_bench.iloc[-1], cum_return_wo_cost.iloc[-1], cum_return_w_cost.iloc[-1], 
                  cum_return_wo_cost.iloc[-1] - cum_return_w_cost.iloc[-1]],
        '百分比': [f"{cum_bench.iloc[-1]*100:.2f}%", f"{cum_return_wo_cost.iloc[-1]*100:.2f}%",
                  f"{cum_return_w_cost.iloc[-1]*100:.2f}%", f"{(cum_return_wo_cost.iloc[-1] - cum_return_w_cost.iloc[-1])*100:.2f}%"]
    })
    cum_return_stats.set_index('指标', inplace=True)
    return {'stats': cum_return_stats, 'cum_bench': cum_bench, 'cum_return_wo_cost': cum_return_wo_cost, 'cum_return_w_cost': cum_return_w_cost}


def analyze_drawdown(report_normal_df: pd.DataFrame, include_cost: bool = True) -> Dict:
    """分析回撤"""
    returns = report_normal_df['return'] - report_normal_df['cost'] if include_cost else report_normal_df['return']
    drawdown_stats = calculate_drawdown_stats(returns)
    drawdown_stats_df = pd.DataFrame({
        '指标': ['最大回撤', '回撤起始日期', '回撤结束日期', '回撤持续天数'],
        '数值': [drawdown_stats['最大回撤'], str(drawdown_stats['回撤起始日期']), 
                str(drawdown_stats['回撤结束日期']), f"{drawdown_stats['回撤持续天数']} 天" if drawdown_stats['回撤持续天数'] else "N/A"]
    })
    drawdown_stats_df.set_index('指标', inplace=True)
    return {'stats': drawdown_stats_df, 'drawdown_stats': drawdown_stats, 'label': '含成本' if include_cost else '不含成本'}


def compare_drawdown(report_normal_df: pd.DataFrame) -> pd.DataFrame:
    """对比含成本和不含成本的回撤"""
    dd_wo = analyze_drawdown(report_normal_df, include_cost=False)
    dd_w = analyze_drawdown(report_normal_df, include_cost=True)
    drawdown_comparison = pd.DataFrame({
        '指标': ['最大回撤', '回撤起始日期', '回撤结束日期', '回撤持续天数'],
        '不含成本': [f"{dd_wo['drawdown_stats']['最大回撤']:.4f}", str(dd_wo['drawdown_stats']['回撤起始日期']),
                    str(dd_wo['drawdown_stats']['回撤结束日期']), f"{dd_wo['drawdown_stats']['回撤持续天数']} 天" if dd_wo['drawdown_stats']['回撤持续天数'] else "N/A"],
        '含成本': [f"{dd_w['drawdown_stats']['最大回撤']:.4f}", str(dd_w['drawdown_stats']['回撤起始日期']),
                  str(dd_w['drawdown_stats']['回撤结束日期']), f"{dd_w['drawdown_stats']['回撤持续天数']} 天" if dd_w['drawdown_stats']['回撤持续天数'] else "N/A"],
        '差异': [f"{(dd_w['drawdown_stats']['最大回撤'] - dd_wo['drawdown_stats']['最大回撤']):.4f}", "-", "-",
                f"{(dd_w['drawdown_stats']['回撤持续天数'] - dd_wo['drawdown_stats']['回撤持续天数']) if (dd_w['drawdown_stats']['回撤持续天数'] and dd_wo['drawdown_stats']['回撤持续天数']) else 'N/A'} 天"]
    })
    drawdown_comparison.set_index('指标', inplace=True)
    return drawdown_comparison

def analyze_turnover(report_normal_df: pd.DataFrame) -> pd.DataFrame:
    """分析换手率"""
    turnover = report_normal_df['turnover']
    turnover_stats = pd.DataFrame({
        '指标': ['平均换手率', '换手率中位数', '换手率标准差', '最大换手率', '最小换手率', '年化换手率'],
        '数值': [turnover.mean(), turnover.median(), turnover.std(), turnover.max(), turnover.min(), turnover.mean() * 252],
        '百分比': [f"{turnover.mean()*100:.2f}%", f"{turnover.median()*100:.2f}%", f"{turnover.std()*100:.2f}%",
                  f"{turnover.max()*100:.2f}%", f"{turnover.min()*100:.2f}%", f"{turnover.mean() * 252:.2f}倍"]
    })
    turnover_stats.set_index('指标', inplace=True)
    return turnover_stats


def calculate_monthly_turnover(report_normal_df: pd.DataFrame) -> pd.DataFrame:
    """计算每个月的换手率统计"""
    turnover = report_normal_df['turnover']
    
    # 确保索引是datetime类型
    if not isinstance(turnover.index, pd.DatetimeIndex):
        turnover.index = pd.to_datetime(turnover.index)
    
    # 按年月分组计算月度换手率
    monthly_turnover = []
    for (year, month), group in turnover.groupby([turnover.index.year, turnover.index.month]):
        date_str = f"{year}-{month:02d}"
        monthly_turnover.append({
            'Date': date_str,
            'Year': year,
            'Month': month,
            'Mean Turnover': group.mean(),
            'Median Turnover': group.median(),
            'Std Turnover': group.std(),
            'Max Turnover': group.max(),
            'Min Turnover': group.min(),
            'Sum Turnover': group.sum(),
            'Trading Days': len(group)
        })
    
    monthly_df = pd.DataFrame(monthly_turnover)
    monthly_df.set_index('Date', inplace=True)
    return monthly_df


# ==================== 风险分析 ====================

def analyze_risk_indicators(analysis_df: pd.DataFrame, report_normal_df: pd.DataFrame, show_notebook: bool = True) -> Tuple[List, pd.DataFrame]:
    """分析风险指标"""
    risk_fig_list = analysis_position.risk_analysis_graph(analysis_df, report_normal_df, show_notebook=show_notebook)
    risk_data = analysis_df.unstack()
    risk_data.columns = risk_data.columns.droplevel(0)
    risk_summary = pd.DataFrame({
        '风险类型': ['超额收益（不含成本）', '超额收益（含成本）'],
        '标准差': [risk_data.loc['excess_return_without_cost', 'std'], risk_data.loc['excess_return_with_cost', 'std']],
        '年化收益率': [risk_data.loc['excess_return_without_cost', 'annualized_return'], risk_data.loc['excess_return_with_cost', 'annualized_return']],
        '信息比率': [risk_data.loc['excess_return_without_cost', 'information_ratio'], risk_data.loc['excess_return_with_cost', 'information_ratio']],
        '最大回撤': [risk_data.loc['excess_return_without_cost', 'max_drawdown'], risk_data.loc['excess_return_with_cost', 'max_drawdown']]
    })
    risk_summary.set_index('风险类型', inplace=True)
    return risk_fig_list, risk_summary


def calculate_monthly_risk_indicators(report_df: pd.DataFrame) -> Dict[str, pd.DataFrame]:
    """计算月度风险指标（三种类型对比）"""
    monthly_risks = {'无成本': [], '含成本': [], '基准': []}
    for (year, month), group in report_df.groupby([report_df.index.year, report_df.index.month]):
        if len(group) < 3:
            continue
        date_str = f"{year}-{month:02d}"
        excess_wo_cost = group['return'] - group['bench']
        risk_wo_cost = risk_analysis(excess_wo_cost, freq='day')
        monthly_risks['无成本'].append({
            'date': date_str, 'annualized_return': risk_wo_cost.loc['annualized_return', 'risk'],
            'information_ratio': risk_wo_cost.loc['information_ratio', 'risk'],
            'max_drawdown': risk_wo_cost.loc['max_drawdown', 'risk'], 'std': risk_wo_cost.loc['std', 'risk'],
        })
        excess_w_cost = group['return'] - group['bench'] - group['cost']
        risk_w_cost = risk_analysis(excess_w_cost, freq='day')
        monthly_risks['含成本'].append({
            'date': date_str, 'annualized_return': risk_w_cost.loc['annualized_return', 'risk'],
            'information_ratio': risk_w_cost.loc['information_ratio', 'risk'],
            'max_drawdown': risk_w_cost.loc['max_drawdown', 'risk'], 'std': risk_w_cost.loc['std', 'risk'],
        })
        bench_risk = risk_analysis(group['bench'], freq='day')
        monthly_risks['基准'].append({
            'date': date_str, 'annualized_return': bench_risk.loc['annualized_return', 'risk'],
            'information_ratio': bench_risk.loc['information_ratio', 'risk'],
            'max_drawdown': bench_risk.loc['max_drawdown', 'risk'], 'std': bench_risk.loc['std', 'risk'],
        })
    monthly_dfs = {}
    for risk_type, risk_list in monthly_risks.items():
        df = pd.DataFrame(risk_list)
        df.set_index('date', inplace=True)
        monthly_dfs[risk_type] = df
    return monthly_dfs


def analyze_monthly_risk(report_normal_df: pd.DataFrame, analysis_df: pd.DataFrame) -> Dict[str, pd.DataFrame]:
    """分析月度风险指标"""
    monthly_risk_dfs = calculate_monthly_risk_indicators(report_normal_df)
    ir_w_cost = monthly_risk_dfs['含成本']['information_ratio']
    best_month = ir_w_cost.idxmax()
    worst_month = ir_w_cost.idxmin()
    monthly_comparison = pd.DataFrame({
        '指标': ['信息比率', '年化收益率', '最大回撤', '标准差'],
        '最佳月份': [f"{monthly_risk_dfs['含成本'].loc[best_month, 'information_ratio']:.4f}",
                    f"{monthly_risk_dfs['含成本'].loc[best_month, 'annualized_return']:.4f}",
                    f"{monthly_risk_dfs['含成本'].loc[best_month, 'max_drawdown']:.4f}",
                    f"{monthly_risk_dfs['含成本'].loc[best_month, 'std']:.4f}"],
        '最差月份': [f"{monthly_risk_dfs['含成本'].loc[worst_month, 'information_ratio']:.4f}",
                    f"{monthly_risk_dfs['含成本'].loc[worst_month, 'annualized_return']:.4f}",
                    f"{monthly_risk_dfs['含成本'].loc[worst_month, 'max_drawdown']:.4f}",
                    f"{monthly_risk_dfs['含成本'].loc[worst_month, 'std']:.4f}"]
    })
    monthly_comparison['最佳月份名称'] = best_month
    monthly_comparison['最差月份名称'] = worst_month
    monthly_comparison.set_index('指标', inplace=True)
    
    stability_list = []
    for risk_type in ['无成本', '含成本', '基准']:
        df = monthly_risk_dfs[risk_type]
        ir = df['information_ratio']
        stability_list.append({
            '类型': risk_type, 'IR 均值': ir.mean(), 'IR 标准差': ir.std(),
            'IR 变异系数': ir.std() / ir.mean() if ir.mean() != 0 else 0,
            'IR > 0 的月份占比 (%)': (ir > 0).sum() / len(ir) * 100
        })
    stability_df = pd.DataFrame(stability_list)
    stability_df.set_index('类型', inplace=True)
    return {'monthly_dfs': monthly_risk_dfs, 'monthly_comparison': monthly_comparison, 'stability_analysis': stability_df}


def get_monthly_risk_summary(monthly_risk_dfs: Dict[str, pd.DataFrame]) -> Dict[str, pd.DataFrame]:
    """获取月度风险指标汇总"""
    metric_name_map = {'annualized_return': '年化收益率', 'information_ratio': '信息比率', 'max_drawdown': '最大回撤', 'std': '标准差'}
    summary_dict = {}
    for metric, metric_name in metric_name_map.items():
        metric_df = pd.DataFrame({
            '无成本': monthly_risk_dfs['无成本'][metric],
            '含成本': monthly_risk_dfs['含成本'][metric],
            '基准': monthly_risk_dfs['基准'][metric]
        })
        summary_dict[metric_name] = metric_df
    return summary_dict


# ==================== 模型性能分析 ====================

def analyze_ic(pred_label: pd.DataFrame, show_notebook: bool = True) -> Dict[str, pd.DataFrame]:
    """分析IC（信息系数）"""
    if show_notebook:
        analysis_position.score_ic_graph(pred_label)
    ic, rank_ic = calc_ic(pred_label['score'], pred_label['label'], date_col='datetime')
    
    ic_summary = pd.DataFrame({
        '指标类型': ['IC (Pearson)', 'IC (Pearson)', 'IC (Pearson)', 'IC (Pearson)',
                     'Rank IC (Spearman)', 'Rank IC (Spearman)', 'Rank IC (Spearman)', 'Rank IC (Spearman)'],
        '指标名称': ['均值', '标准差', 'ICIR (信息比率)', '胜率 (%)', '均值', '标准差', 'ICIR (信息比率)', '胜率 (%)'],
        '数值': [ic.mean(), ic.std(), ic.mean() / ic.std() if ic.std() > 0 else 0, (ic > 0).sum() / len(ic) * 100,
                rank_ic.mean(), rank_ic.std(), rank_ic.mean() / rank_ic.std() if rank_ic.std() > 0 else 0,
                (rank_ic > 0).sum() / len(rank_ic) * 100]
    })
    ic_summary_pivot = ic_summary.pivot_table(index='指标名称', columns='指标类型', values='数值')
    ic_summary_pivot = ic_summary_pivot.reindex(['均值', '标准差', 'ICIR (信息比率)', '胜率 (%)'])
    
    ic_dist_stats = pd.DataFrame({
        '统计指标': ['均值', '中位数', '标准差', '最小值', '最大值', '25%分位数', '75%分位数'],
        'IC (Pearson)': [ic.mean(), ic.median(), ic.std(), ic.min(), ic.max(), ic.quantile(0.25), ic.quantile(0.75)],
        'Rank IC (Spearman)': [rank_ic.mean(), rank_ic.median(), rank_ic.std(), rank_ic.min(), rank_ic.max(), rank_ic.quantile(0.25), rank_ic.quantile(0.75)]
    })
    ic_dist_stats.set_index('统计指标', inplace=True)
    
    ic_ts_stats = pd.DataFrame({
        '统计指标': ['均值', '中位数', '标准差', '最小值', '最大值', '25%分位数', '75%分位数', 'IC > 0 的占比 (%)'],
        'IC (Pearson)': [ic.mean(), ic.median(), ic.std(), ic.min(), ic.max(), ic.quantile(0.25), ic.quantile(0.75), (ic > 0).sum() / len(ic) * 100],
        'Rank IC (Spearman)': [rank_ic.mean(), rank_ic.median(), rank_ic.std(), rank_ic.min(), rank_ic.max(), rank_ic.quantile(0.25), rank_ic.quantile(0.75), (rank_ic > 0).sum() / len(rank_ic) * 100]
    })
    ic_ts_stats.set_index('统计指标', inplace=True)
    return {'ic': ic, 'rank_ic': rank_ic, 'summary': ic_summary_pivot, 'distribution': ic_dist_stats, 'time_series': ic_ts_stats}


def analyze_monthly_ic(ic: pd.Series) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """分析月度IC"""
    ic_df = pd.DataFrame({'IC': ic})
    ic_df.index = pd.to_datetime(ic_df.index)
    _index = ic_df.index.astype("str").str.replace("-", "").str.slice(0, 6)
    monthly_ic = ic_df['IC'].groupby(_index, group_keys=False).mean()
    monthly_ic.index = pd.MultiIndex.from_arrays([monthly_ic.index.str.slice(0, 4), monthly_ic.index.str.slice(4, 6)], names=["year", "month"])
    _month_list = pd.date_range(start=pd.Timestamp(f"{_index.min()[:4]}0101"), end=pd.Timestamp(f"{_index.max()[:4]}1231"), freq="ME")
    _years = [d.strftime("%Y%m%d")[:4] for d in _month_list]
    _months = [d.strftime("%Y%m%d")[4:6] for d in _month_list]
    fill_index = pd.MultiIndex.from_arrays([_years, _months], names=["year", "month"])
    monthly_ic_filled = monthly_ic.reindex(fill_index)
    monthly_ic_matrix = monthly_ic_filled.unstack()
    monthly_ic_summary = pd.DataFrame({
        '统计指标': ['月度IC均值', '月度IC标准差', '月度IC最小值', '月度IC最大值', 'IC > 0 的月份数', 'IC > 0 的月份占比 (%)'],
        '数值': [monthly_ic_filled.mean(), monthly_ic_filled.std(), monthly_ic_filled.min(), monthly_ic_filled.max(),
                (monthly_ic_filled > 0).sum(), (monthly_ic_filled > 0).sum() / len(monthly_ic_filled.dropna()) * 100]
    })
    monthly_ic_summary.set_index('统计指标', inplace=True)
    return monthly_ic_matrix, monthly_ic_summary


def analyze_ic_normality(ic: pd.Series, rank_ic: pd.Series) -> pd.DataFrame:
    """分析IC分布的正态性"""
    ic_shapiro = scipy_stats.shapiro(ic.dropna())
    rank_ic_shapiro = scipy_stats.shapiro(rank_ic.dropna())
    normality_test = pd.DataFrame({
        '检验方法': ['Shapiro-Wilk检验'],
        'IC (Pearson)': [f"统计量={ic_shapiro.statistic:.4f}, p值={ic_shapiro.pvalue:.4f}"],
        'Rank IC (Spearman)': [f"统计量={rank_ic_shapiro.statistic:.4f}, p值={rank_ic_shapiro.pvalue:.4f}"]
    })
    normality_test.set_index('检验方法', inplace=True)
    return normality_test


def analyze_group_returns(pred_label: pd.DataFrame, n_groups: int = 5, show_notebook: bool = True) -> Tuple[List, Dict[str, pd.DataFrame]]:
    """分析分组收益"""
    model_fig_list = analysis_model.model_performance_graph(pred_label, show_notebook=show_notebook)
    pred_label_sorted = pred_label.sort_values('score', ascending=False)
    pred_label_drop = pred_label_sorted.dropna(subset=['score'])
    group_returns = {}
    for i in range(n_groups):
        group_name = f'Group{i+1}'
        group_data = pred_label_drop.groupby(level='datetime', group_keys=False).apply(
            lambda x: x.iloc[len(x)//n_groups*i : len(x)//n_groups*(i+1)]['label'].mean()
        )
        group_returns[group_name] = group_data
    group_returns_df = pd.DataFrame(group_returns)
    group_returns_df.index = pd.to_datetime(group_returns_df.index)
    group_returns_df['long-short'] = group_returns_df['Group1'] - group_returns_df['Group5']
    avg_return = pred_label.groupby(level='datetime', group_keys=False)['label'].mean()
    group_returns_df['long-average'] = group_returns_df['Group1'] - avg_return
    cum_group_returns = group_returns_df.cumsum()
    
    group_cum_stats = pd.DataFrame({
        '分组': ['Group1 (最高分)', 'Group2', 'Group3', 'Group4', 'Group5 (最低分)', 'Long-Short', 'Long-Average'],
        '最终累计收益': [cum_group_returns['Group1'].iloc[-1], cum_group_returns['Group2'].iloc[-1], cum_group_returns['Group3'].iloc[-1],
                        cum_group_returns['Group4'].iloc[-1], cum_group_returns['Group5'].iloc[-1], cum_group_returns['long-short'].iloc[-1],
                        cum_group_returns['long-average'].iloc[-1]],
        '日均收益': [group_returns_df['Group1'].mean(), group_returns_df['Group2'].mean(), group_returns_df['Group3'].mean(),
                    group_returns_df['Group4'].mean(), group_returns_df['Group5'].mean(), group_returns_df['long-short'].mean(),
                    group_returns_df['long-average'].mean()],
        '收益标准差': [group_returns_df['Group1'].std(), group_returns_df['Group2'].std(), group_returns_df['Group3'].std(),
                      group_returns_df['Group4'].std(), group_returns_df['Group5'].std(), group_returns_df['long-short'].std(),
                      group_returns_df['long-average'].std()]
    })
    group_cum_stats.set_index('分组', inplace=True)
    
    dist_stats = pd.DataFrame({
        '指标': ['均值', '中位数', '标准差', '最小值', '最大值', '25%分位数', '75%分位数'],
        'Long-Short': [group_returns_df['long-short'].mean(), group_returns_df['long-short'].median(), group_returns_df['long-short'].std(),
                      group_returns_df['long-short'].min(), group_returns_df['long-short'].max(), group_returns_df['long-short'].quantile(0.25),
                      group_returns_df['long-short'].quantile(0.75)],
        'Long-Average': [group_returns_df['long-average'].mean(), group_returns_df['long-average'].median(), group_returns_df['long-average'].std(),
                        group_returns_df['long-average'].min(), group_returns_df['long-average'].max(), group_returns_df['long-average'].quantile(0.25),
                        group_returns_df['long-average'].quantile(0.75)]
    })
    dist_stats.set_index('指标', inplace=True)
    return model_fig_list, {'cumulative_stats': group_cum_stats, 'distribution_stats': dist_stats, 'group_returns_df': group_returns_df}


def analyze_pred_autocorr(pred_label_df: pd.DataFrame, lag: int = 1) -> pd.DataFrame:
    """分析预测自相关性"""
    pred = pred_label_df['score'].copy()
    autocorr_results = []
    for stock in pred.index.get_level_values('instrument').unique():
        stock_pred = pred.xs(stock, level='instrument')
        if len(stock_pred) > lag:
            autocorr = stock_pred.autocorr(lag=lag)
            if not pd.isna(autocorr):
                autocorr_results.append({'stock': stock, 'autocorr': autocorr, 'length': len(stock_pred)})
    return pd.DataFrame(autocorr_results)


def analyze_pred_autocorr_stats(autocorr_df: pd.DataFrame) -> Dict[str, pd.DataFrame]:
    """分析预测自相关性的统计信息"""
    autocorr_stats = pd.DataFrame({
        '统计指标': ['均值', '中位数', '标准差', '最小值', '最大值', '25%分位数', '75%分位数'],
        '自相关性': [autocorr_df['autocorr'].mean(), autocorr_df['autocorr'].median(), autocorr_df['autocorr'].std(),
                    autocorr_df['autocorr'].min(), autocorr_df['autocorr'].max(), autocorr_df['autocorr'].quantile(0.25),
                    autocorr_df['autocorr'].quantile(0.75)]
    })
    autocorr_stats.set_index('统计指标', inplace=True)
    high_autocorr = (autocorr_df['autocorr'] > 0.7).sum()
    medium_autocorr = ((autocorr_df['autocorr'] >= 0.3) & (autocorr_df['autocorr'] <= 0.7)).sum()
    low_autocorr = (autocorr_df['autocorr'] < 0.3).sum()
    total_stocks = len(autocorr_df)
    autocorr_category = pd.DataFrame({
        '自相关性水平': ['高自相关 (>0.7)', '中等自相关 (0.3-0.7)', '低自相关 (<0.3)'],
        '股票数量': [high_autocorr, medium_autocorr, low_autocorr],
        '占比 (%)': [high_autocorr / total_stocks * 100, medium_autocorr / total_stocks * 100, low_autocorr / total_stocks * 100]
    })
    autocorr_category.set_index('自相关性水平', inplace=True)
    return {'stats': autocorr_stats, 'category': autocorr_category}


# ==================== 图表生成辅助函数 ====================

def generate_report_graph(report_normal_df: pd.DataFrame, show_notebook: bool = True) -> List:
    """生成回测报告图表"""
    return analysis_position.report_graph(report_normal_df, show_notebook=show_notebook)


def show_monthly_risk_charts(risk_fig_list: List):
    """展示月度风险分析图表"""
    print("【月度风险分析图表1：年化收益率】")
    risk_fig_list[1].update_layout(width=1200, height=600, title='月度年化收益率')
    risk_fig_list[1].show()
    print("\n【月度风险分析图表2：最大回撤】")
    risk_fig_list[2].update_layout(width=1200, height=600, title='月度最大回撤')
    risk_fig_list[2].show()
    print("\n【月度风险分析图表3：信息比率】")
    risk_fig_list[3].update_layout(width=1200, height=600, title='月度信息比率')
    risk_fig_list[3].show()
    print("\n【月度风险分析图表4：标准差】")
    risk_fig_list[4].update_layout(width=1200, height=600, title='月度标准差')
    risk_fig_list[4].show()


def show_monthly_risk_summary(monthly_risk_dfs: Dict[str, pd.DataFrame]) -> Dict[str, pd.DataFrame]:
    """获取月度风险分析汇总（返回字典供notebook显示）"""
    metric_name_map = {'annualized_return': '年化收益率', 'information_ratio': '信息比率', 'max_drawdown': '最大回撤', 'std': '标准差'}
    summary_dict = {}
    for metric, metric_name in metric_name_map.items():
        metric_df = pd.DataFrame({
            '无成本': monthly_risk_dfs['无成本'][metric],
            '含成本': monthly_risk_dfs['含成本'][metric],
            '基准': monthly_risk_dfs['基准'][metric]
        })
        summary_dict[metric_name] = metric_df
    return summary_dict

