import os
import yaml
import pandas as pd
import matplotlib.axes
import matplotlib.pyplot as plt
import numpy as np
from functools import reduce

from typing import Any, Dict, List, Optional, Tuple

from utils.config import REPO_ROOT


STATISTICAL_OPERATIONS = {
    'mean': lambda array: float(np.nanmean(array)),
    'median': lambda array: float(np.nanmedian(array)),
    'IQR': lambda array: float(np.nanquantile(array, 0.75) - np.nanquantile(array, 0.25))
}


def get_occlusion_traj_info_df(drop_idx: bool = True):
    target_path = os.path.join(REPO_ROOT, 'results', 'dataset_occlusion_simulation', 'results', 'trajectories_info.csv')
    assert os.path.exists(target_path)

    df = pd.read_csv(target_path)

    df_indices = ['idx', 'filename', 'agent_id']
    df.set_index(keys=df_indices, inplace=True)

    if drop_idx:
        df = df.droplevel('idx')

    df['idle'] = df['travelled_distance_Tobs_t0'] < 0.5
    df['occlusion_pattern'] = df['occlusion_pattern'].astype(str).str.rjust(8, '0')

    return df


def get_results_directory(
        experiment_name: str,
        dataset_used: Optional[str] = None,
        model_name: Optional[str] = None,
        split: str = 'test'
) -> str:
    """
    Will pick the first appropriate directory for <dataset_used> and <model_name> if they aren't provided.
    """

    root_results_path = os.path.join(REPO_ROOT, 'results', experiment_name, 'results')

    if dataset_used is None:
        dataset_used = sorted(os.listdir(root_results_path))[0]
    dataset_path = os.path.join(root_results_path, dataset_used)
    assert os.path.exists(dataset_path)

    if model_name is None:
        model_name = sorted(os.listdir(dataset_path))[-1]
    model_path = os.path.join(dataset_path, model_name)
    assert os.path.exists(model_path)

    target_path = os.path.join(model_path, split)
    assert os.path.exists(target_path)

    return os.path.abspath(target_path)


def get_all_results_directories() -> List[Dict]:
    root_results_path = os.path.join(REPO_ROOT, 'results')
    assert os.path.exists(root_results_path)
    experiment_names = sorted(os.listdir(root_results_path))

    def os_get_dirs(path): return [name for name in os.listdir(path) if os.path.isdir(os.path.join(path, name))]

    experiment_dicts = []
    for experiment_name in experiment_names:
        run_results_path = os.path.join(root_results_path, experiment_name, 'results')
        assert os.path.exists(run_results_path)
        for dataset_used in os_get_dirs(run_results_path):
            dataset_path = os.path.join(run_results_path, dataset_used)
            assert os.path.exists(dataset_path)
            for model_name in os_get_dirs(dataset_path):
                model_path = os.path.join(dataset_path, model_name)
                assert os.path.exists(model_path)
                for split in os_get_dirs(model_path):
                    split_path = os.path.join(model_path, split)
                    assert os.path.exists(split_path)

                    scores_file = os.path.join(split_path, 'prediction_scores.yml')
                    if os.path.exists(scores_file) and os.path.isfile(scores_file):
                        exp_dict = {
                            'experiment_name': experiment_name,
                            'dataset_used': dataset_used,
                            'model_name': model_name,
                            'split': split
                        }
                        experiment_dicts.append(exp_dict)

    return experiment_dicts


def get_perf_scores_df(
        experiment_name: str,
        dataset_used: Optional[str] = None,
        model_name: Optional[str] = None,
        split: str = 'test',
        drop_idx: bool = True
) -> pd.DataFrame:

    target_path = get_results_directory(
        experiment_name=experiment_name,
        dataset_used=dataset_used,
        model_name=model_name,
        split=split
    )
    target_path = os.path.join(target_path, 'prediction_scores.csv')
    assert os.path.exists(target_path)

    df = pd.read_csv(target_path)

    df_indices = ['idx', 'filename', 'agent_id']
    df.set_index(keys=df_indices, inplace=True)

    if drop_idx:
        df = df.droplevel('idx')

    return df


def get_perf_scores_dict(
        experiment_name: str,
        dataset_used: Optional[str] = None,
        model_name: Optional[str] = None,
        split: str = 'test'
) -> Dict:

    target_path = get_results_directory(
        experiment_name=experiment_name,
        dataset_used=dataset_used,
        model_name=model_name,
        split=split
    )
    target_path = os.path.join(target_path, 'prediction_scores.yml')
    assert os.path.exists(target_path)

    with open(target_path, 'r') as f:
        scores_dict = yaml.safe_load(f)

    return scores_dict


def print_occlusion_length_counts():
    dataframe = get_perf_scores_df('const_vel_occlusion_simulation', 'occlusion_simulation', 'untrained', 'test')
    print("last observed timestep\t| case count")
    for i in range(0, 7):
        mini_df = dataframe[dataframe['past_pred_length'] == i]
        print(f"{-i}\t\t\t| {len(mini_df)}")
    print(f"total\t\t\t| {len(dataframe)}")


def generate_performance_summary_df(
        experiments: List[Dict],
        metric_names: List,
        df_filter=None,
        operation: str = 'mean'
) -> pd.DataFrame:
    assert operation in STATISTICAL_OPERATIONS.keys()

    df_columns = ['experiment', 'dataset_used', 'n_measurements', 'model_name'] + metric_names
    performance_df = pd.DataFrame(columns=df_columns)

    for exp_dict in experiments:

        scores_df = get_perf_scores_df(
            experiment_name=exp_dict['experiment_name'],
            dataset_used=exp_dict['dataset_used'],
            model_name=exp_dict['model_name'],
            split=exp_dict['split']
        )

        if df_filter is not None:
            scores_df = df_filter(scores_df)

        scores_dict = {
            name: STATISTICAL_OPERATIONS[operation](scores_df[name])
            if name in scores_df.columns else pd.NA for name in metric_names
        }

        scores_dict['experiment'] = exp_dict['experiment_name']
        scores_dict['dataset_used'] = exp_dict['dataset_used']
        scores_dict['n_measurements'] = len(scores_df)
        scores_dict['model_name'] = exp_dict['model_name']

        performance_df.loc[len(performance_df)] = scores_dict

    return performance_df


def remove_k_sample_columns(df: pd.DataFrame) -> pd.DataFrame:
    keep_columns = [name for name in df.columns.tolist() if not name.startswith('K')]
    return df[keep_columns]


def difference_summary_df(
        summary_df: pd.DataFrame, base_experiment_name: str, mode: str = 'absolute'
) -> pd.DataFrame:
    assert mode in ['absolute', 'relative']
    assert base_experiment_name in summary_df['experiment'].to_list()
    assert (summary_df['experiment'] == base_experiment_name).sum() == 1

    diff_df = summary_df.copy()

    compare_columns = summary_df.columns[summary_df.dtypes == float]
    compare_row = diff_df.loc[diff_df['experiment'] == base_experiment_name, compare_columns].iloc[0]

    if mode == 'absolute':
        diff_df.loc[:, compare_columns] = diff_df.loc[:, compare_columns].subtract(compare_row)
    elif mode == 'relative':
        diff_df.loc[:, compare_columns] = diff_df.loc[:, compare_columns].div(compare_row)
        diff_df.loc[:, compare_columns] = diff_df.loc[:, compare_columns] - 1.0

    return diff_df


def pretty_print_difference_summary_df(
        summary_df: pd.DataFrame, base_experiment_name: str, mode: str = 'absolute'
) -> pd.DataFrame:
    diff_df = difference_summary_df(summary_df=summary_df, base_experiment_name=base_experiment_name, mode=mode)
    compare_columns = summary_df.columns[summary_df.dtypes == float]

    if mode == 'absolute':
        diff_df.loc[:, compare_columns] = diff_df.loc[:, compare_columns].applymap(
            lambda x: f" (+{x:.3f})" if x >= 0. else f" ({x:.3f})"
        )
    if mode == 'relative':
        diff_df.loc[:, compare_columns] = diff_df.loc[:, compare_columns] * 100
        diff_df.loc[:, compare_columns] = diff_df.loc[:, compare_columns].applymap(
            lambda x: f" (+{x:.3f}%)" if x >= 0. else f" ({x:.3f}%)"
        )

    out_df = summary_df.copy()
    out_df.loc[:, compare_columns] = out_df.loc[:, compare_columns].round(5).astype(str)
    out_df.loc[:, compare_columns] = out_df.loc[:, compare_columns] + diff_df.loc[:, compare_columns]

    return out_df


def reduce_by_unique_column_values(
        df: pd.DataFrame, column_name: str, operation: str = 'mean'
) -> pd.DataFrame:
    assert column_name in df.columns
    assert operation in ['mean', 'std', 'median']

    scores = df.columns.tolist()
    scores.remove(column_name)
    summary_df = pd.DataFrame(columns=['count', column_name] + scores)

    operation = eval(f"pd.DataFrame.{operation}")
    for col_value in sorted(df[column_name].unique()):

        mini_df = df[df[column_name] == col_value]

        row_dict = operation(mini_df[scores]).to_dict()
        row_dict['count'] = len(mini_df)
        row_dict[column_name] = col_value

        summary_df.loc[len(summary_df)] = row_dict
    return summary_df


def draw_boxplots(
        draw_ax: matplotlib.axes.Axes, df: pd.DataFrame, column_data: str, column_boxes: str
) -> None:
    assert column_data in df.columns
    assert column_boxes in df.columns

    box_names = sorted(df[column_boxes].unique())
    box_data = []

    for box_category in box_names:

        mini_df = df[(df[column_boxes] == box_category) & (pd.notna(df[column_boxes]))]

        scores = mini_df[column_data].to_numpy()
        box_data.append(scores)

    draw_ax.boxplot(box_data)
    draw_ax.set_xticklabels(box_names)


def performance_dataframes_comparison(
        base_df: pd.DataFrame, compare_df: pd.DataFrame
) -> pd.DataFrame:
    # removing rows that are not shared across base_df and comp_df
    keep_indices = base_df.index.intersection(compare_df.index)
    out_df = compare_df.sub(base_df)

    return out_df.loc[keep_indices, :]


def scatter_perf_gain_vs_perf_base(
        base_df: pd.DataFrame, comp_df: pd.DataFrame, col_name: str, relative: bool = True
) -> Tuple[matplotlib.figure.Figure, matplotlib.axes.Axes]:
    # maybe get rid of this function altogether...
    assert col_name in base_df.columns
    assert col_name in comp_df.columns

    keep_indices = base_df.index.intersection(comp_df.index)

    fig, ax = plt.subplots()
    diff = comp_df.loc[keep_indices, col_name].sub(base_df.loc[keep_indices, col_name])

    if relative:
        diff = diff.div(base_df.loc[keep_indices, col_name])

    ax.scatter(base_df.loc[keep_indices, col_name], diff, marker='x', alpha=0.5)

    return fig, ax


def scatter_performance_scores(
        draw_ax: matplotlib.axes.Axes,
        x_df: pd.DataFrame, x_score_name: str,
        y_df: pd.DataFrame, y_score_name: str,
        xlabel_prefix: Optional[str] = None,
        ylabel_prefix: Optional[str] = None
) -> None:
    assert x_score_name in x_df.columns
    assert y_score_name in y_df.columns

    keep_indices = x_df.index.intersection(y_df.index)
    xs = x_df.loc[keep_indices, x_score_name].to_numpy()
    ys = y_df.loc[keep_indices, y_score_name].to_numpy()

    draw_ax.scatter(xs, ys, marker='x', color='black', alpha=0.7)

    x_label = f"{xlabel_prefix} | {x_score_name}" if xlabel_prefix is not None else x_score_name
    y_label = f"{ylabel_prefix} | {y_score_name}" if ylabel_prefix is not None else y_score_name

    draw_ax.set_xlabel(x_label, loc='left')
    draw_ax.set_ylabel(y_label, loc='bottom')


def get_occluded_identities(df: pd.DataFrame, idx: int):
    print(df.loc[idx].index.get_level_values('agent_id').to_list())
    print(df.loc[idx])
    instance_df = df.loc[idx]
    if (instance_df['past_pred_length'] != 0).sum() != 0:   # if there are agents who we do have to predict over the past
        return instance_df[instance_df['past_pred_length'] != 0].index.get_level_values('agent_id').to_list()
        # return df[df['past_pred_length'] != 0].loc[idx].index.get_level_values('agent_id').to_list()
    else:
        return []


def get_comparable_rows(
        base_df: pd.DataFrame,
        compare_df: pd.DataFrame,
        n_max_agents: Optional[int] = None
):
    # identifying the rows the two dataframes have in common
    common_rows = base_df.index.intersection(compare_df.index)
    compare_rows = common_rows.copy()
    if n_max_agents is not None:
        # defining a filter to remove instances with agent count larger than <n_max_agents>
        row_indices_leq_n_max_agents = (common_rows.get_level_values('idx').value_counts() <= n_max_agents)
        row_indices_leq_n_max_agents = row_indices_leq_n_max_agents[row_indices_leq_n_max_agents].index
        # the multiindex of rows to use for comparison
        compare_rows = common_rows[common_rows.get_level_values('idx').isin(row_indices_leq_n_max_agents)]
    return compare_rows


def get_scores_dict_by_categories(
        exp_df: pd.DataFrame,
        score: str,
        categorization: str
):
    assert score in exp_df.columns
    assert categorization in exp_df.columns

    experiment_data_dict = {int(category): None for category in exp_df[categorization].unique()}
    for category in sorted(exp_df[categorization].unique()):
        mini_df = exp_df[
            (exp_df[categorization] == category) & (pd.notna(exp_df[score]))
            ]

        # print(f"{len(mini_df)=}")
        # print(f"{mini_df['min_ADE'].mean(), mini_df['min_FDE'].mean()=}")
        # print(f"{mini_df['mean_ADE'].mean(), mini_df['mean_FDE'].mean()=}")
        # mini_df = mini_df.sample(495)
        # print(f"{len(mini_df)=}")

        scores = mini_df[score].to_numpy()
        experiment_data_dict[int(category)] = scores

    return experiment_data_dict


def get_occlusion_indices(split: str):
    cv_perf_df = get_perf_scores_df(
        experiment_name='const_vel_occlusion_simulation',
        dataset_used='occlusion_simulation',
        model_name='untrained',
        split=split
    )

    cv_perf_df = cv_perf_df[cv_perf_df['past_pred_length'] > 0]
    return cv_perf_df.index


def get_difficult_occlusion_indices(split: str):
    cv_perf_df = get_perf_scores_df(
        experiment_name='const_vel_occlusion_simulation',
        dataset_used='occlusion_simulation',
        model_name='untrained',
        split=split
    )

    cv_perf_df = cv_perf_df[cv_perf_df['past_pred_length'] > 0]
    cv_perf_df = cv_perf_df[cv_perf_df['OAC_t0'] == 0.]
    return cv_perf_df.index


def get_reference_indices():
    reference_dfs = [
        # <experiment_name>, <dataset_used>
        {'experiment_name': 'const_vel_fully_observed', 'dataset_used': 'fully_observed',
         'model_name': 'untrained'},
        {'experiment_name': 'const_vel_occlusion_simulation', 'dataset_used': 'occlusion_simulation',
         'model_name': 'untrained'},
        {'experiment_name': 'const_vel_occlusion_simulation_imputed', 'dataset_used': 'occlusion_simulation_imputed',
         'model_name': 'untrained'},
    ]  # the performance dataframes will be filtered by the intersection of the indices of the reference_dfs
    ref_indices = [
        get_perf_scores_df(**exp_dict, split='test').index for exp_dict in reference_dfs
    ]
    ref_index = reduce(lambda idx_a, idx_b: idx_a.intersection(idx_b), ref_indices)
    return ref_index


def get_df_filter(ref_index: pd.Index, filters: Optional[List[str]] = None):
    def ref_index_filter(df): return df.iloc[df.index.isin(ref_index)]

    def filter_(df, filter_df, level):
        return df.iloc[df.index.droplevel(level=level).isin(filter_df.index.droplevel(level=level))]

    filter_funcs = [ref_index_filter]

    if filters is not None:
        traj_info_df = get_occlusion_traj_info_df()
        ref_df_1 = get_perf_scores_df(
            experiment_name='const_vel_occlusion_simulation',
            dataset_used='occlusion_simulation',
            model_name='untrained',
            split='test'
        )
        ref_df_2 = get_perf_scores_df(
            experiment_name='const_vel_occlusion_simulation_imputed',
            dataset_used='occlusion_simulation_imputed',
            model_name='untrained',
            split='test'
        )
        ref_df = pd.DataFrame(None)
        ref_df['occl_OAC_t0'] = ref_df_1['OAC_t0']
        ref_df['occl_past_pred_length'] = ref_df_1['past_pred_length']
        ref_df['imp_OAC_t0'] = ref_df_2['OAC_t0']
        ref_df['imp_past_pred_length'] = ref_df_2['past_pred_length']

        ref_df = ref_df[ref_df['occl_past_pred_length'] == ref_df['imp_past_pred_length']]
        assert all(ref_df['occl_past_pred_length'] == ref_df['imp_past_pred_length'])

        filter_dict = {
            'occluded_ids': lambda df: filter_(df, ref_df[ref_df['occl_past_pred_length'] != 0], []),
            'fully_observed_ids': lambda df: filter_(df, ref_df[ref_df['occl_past_pred_length'] == 0], []),
            'difficult_dataset': lambda df: filter_(
                df, ref_df[(ref_df['occl_OAC_t0'] == 0.) & (ref_df['imp_OAC_t0'] == 0.)], ['agent_id']
            ),
            'difficult_occluded_ids': lambda df: filter_(
                df, ref_df[(ref_df['occl_OAC_t0'] == 0.) & (ref_df['imp_OAC_t0'] == 0.)], []
            ),
            'moving': lambda df: filter_(df, traj_info_df[~traj_info_df['idle']], []),
            'idle': lambda df: filter_(df, traj_info_df[traj_info_df['idle']], []),
        }

        assert all([filter_name in filter_dict.keys() for filter_name in filters])

        [filter_funcs.append(filter_dict[filter_name]) for filter_name in filters]

    return lambda df: reduce(lambda o, func: func(o), filter_funcs, df)
