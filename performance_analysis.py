import argparse
import os.path
import pickle
import matplotlib.pyplot as plt
import pandas as pd
from utils.config import Config, REPO_ROOT
from data.sdd_dataloader import HDF5DatasetSDD
from utils.sdd_visualize import visualize_input_and_predictions
from utils.performance_analysis import \
    generate_performance_summary_df, \
    pretty_print_difference_summary_df, \
    make_box_plot_occlusion_lengths, \
    make_oac_histograms_figure, \
    get_perf_scores_df, \
    get_reference_indices, \
    get_all_results_directories, \
    get_df_filter, \
    perform_ttest, \
    remove_k_sample_columns, \
    scores_stats_df_per_occlusion_lengths


if __name__ == '__main__':
    # Script Controls #################################################################################################
    parser = argparse.ArgumentParser()
    parser.add_argument('--cfg', nargs='+', default=None)
    parser.add_argument('--perf_summary', action='store_true', default=False)
    parser.add_argument('--unit', type=str, default='m')        # 'm' | 'px'
    parser.add_argument('--sort_by', type=str, default='experiment')
    parser.add_argument('--filter', nargs='+', default=None)
    parser.add_argument('--boxplots', action='store_true', default=False)
    parser.add_argument('--stats_per_last_obs', action='store_true', default=False)
    parser.add_argument('--ttest', nargs='*', help='specify 0 or 2 arguments', type=int, default=None)
    parser.add_argument('--oac_histograms', action='store_true', default=False)
    parser.add_argument('--qual_compare', action='store_true', default=False)
    parser.add_argument('--instance_num', type=int, default=None)
    parser.add_argument('--identities', nargs='+', type=int, default=[])
    parser.add_argument('--qual_example', action='store_true', default=False)
    parser.add_argument('--comp_phase_1_2', action='store_true', default=False)
    parser.add_argument('--cv_wrong_map_rate', action='store_true', default=False)
    parser.add_argument('--save', action='store_true', default=False)
    parser.add_argument('--show', action='store_true', default=False)
    args = parser.parse_args()

    SHOW = args.show
    SAVE = args.save

    assert SAVE or SHOW
    assert args.unit in ['m', 'px']

    # Global Variables set up #########################################################################################
    pd.set_option('display.max_rows', 500)
    pd.set_option('display.max_columns', 500)
    pd.set_option('display.width', 200)
    pd.set_option('display.max_colwidth', 75)

    PERFORMANCE_ANALYSIS_DIRECTORY = os.path.join(REPO_ROOT, 'performance_analysis')
    os.makedirs(PERFORMANCE_ANALYSIS_DIRECTORY, exist_ok=True)

    UNIT = args.unit       # 'm' | 'px'
    EXPERIMENT_SEPARATOR = "\n\n\n\n" + "#" * 200 + "\n\n\n\n"

    DEFAULT_CFG = [
        'original_100',
        'original_101',
        'original_102',
        'original_103',
        'original_104',
        'occlusionformer_basis_bias_1',
        'occlusionformer_basis_bias_2',
        'occlusionformer_basis_bias_3',
        'occlusionformer_basis_bias_4',
        'occlusionformer_basis_bias_5',
    ]

    MIN_SCORES = ['min_ADE', 'min_FDE']
    MEAN_SCORES = ['mean_ADE', 'mean_FDE']
    PAST_MIN_SCORES = ['min_past_ADE', 'min_past_FDE']
    PAST_MEAN_SCORES = ['mean_past_ADE', 'mean_past_FDE']

    PRED_LENGTHS = ['past_pred_length', 'pred_length']
    OCCLUSION_MAP_SCORES = ['OAO', 'OAC', 'OAC_t0']

    if UNIT == 'px':

        px_name = lambda names_list: [f'{score_name}_px' for score_name in names_list]
        MIN_SCORES = px_name(MIN_SCORES)
        MEAN_SCORES = px_name(MEAN_SCORES)
        PAST_MIN_SCORES = px_name(PAST_MIN_SCORES)
        PAST_MEAN_SCORES = px_name(PAST_MEAN_SCORES)

    # Performance Summary #############################################################################################
    if args.perf_summary:
        print("\n\nPERFORMANCE SUMMARY:\n\n")

        experiment_names = args.cfg if args.cfg is not None else DEFAULT_CFG
        operation = 'mean'          # 'mean' | 'median' | 'IQR'
        sort_by = args.sort_by

        metric_names = (MIN_SCORES + MEAN_SCORES +
                        PAST_MIN_SCORES + PAST_MEAN_SCORES +
                        PRED_LENGTHS + OCCLUSION_MAP_SCORES)

        ref_index = get_reference_indices()

        exp_dicts = get_all_results_directories()
        exp_dicts = [exp_dict for exp_dict in exp_dicts if exp_dict['split'] in 'test']
        exp_dicts = [exp_dict for exp_dict in exp_dicts if exp_dict['experiment_name'] in experiment_names]

        df_filter = get_df_filter(ref_index=ref_index, filters=args.filter)

        all_perf_df = generate_performance_summary_df(
            experiments=exp_dicts, metric_names=metric_names, operation=operation, df_filter=df_filter
        )
        all_perf_df.sort_values(by=sort_by, inplace=True)

        if SHOW:

            if True:  # specify some dataset characteristics
                example_df = get_perf_scores_df(
                    experiment_name='const_vel_occlusion_simulation',
                    dataset_used='occlusion_simulation',
                    model_name='untrained',
                    split='test'
                )
                example_df = df_filter(example_df)

                print(f"Dataset Characteristics:")
                print(f"# instances\t\t: {len(example_df.index.unique(level='filename'))}")
                print(f"# trajectories\t\t: {len(example_df)}")
                print(f"# occlusion cases\t: {(example_df['past_pred_length'] != 0).sum()}")
                print("\n")

            print(f"Experiments Performance Summary ({operation}):")
            print(all_perf_df)

        if SAVE:
            base_experiment_names = []

            filename = "experiments_performance_summary.csv"
            filepath = os.path.join(PERFORMANCE_ANALYSIS_DIRECTORY, filename)
            print(f"saving dataframe to:\n{filepath}\n")
            all_perf_df.to_csv(filepath)

            for name in base_experiment_names:
                pretty_df = pretty_print_difference_summary_df(
                    summary_df=all_perf_df, base_experiment_name=name, mode='relative'
                )
                filename = f"experiments_performance_summary_relative_to_{name}.csv"
                filepath = os.path.join(PERFORMANCE_ANALYSIS_DIRECTORY, filename)
                print(f"saving dataframe to:\n{filepath}\n")
                pretty_df.to_csv(filepath)

        print(EXPERIMENT_SEPARATOR)

    # qualitative display of predictions ##############################################################################
    if args.qual_example:
        print("\n\nQUALITATIVE EXAMPLE:\n\n")

        experiment_names = args.cfg if args.cfg is not None else DEFAULT_CFG
        assert args.instance_num is not None

        instance_number, show_pred_ids = args.instance_num, args.identities     # int, List[int]

        imputed = False
        highlight_only_past_pred = True
        figsize = (14, 10)

        for experiment_name in experiment_names:
            # preparing the dataloader for the experiment
            # exp_df = get_perf_scores_df(experiment_name)
            config_exp = Config(experiment_name)
            dataloader_exp = HDF5DatasetSDD(config_exp, log=None, split='test') if not imputed else \
                HDF5DatasetSDD(Config('const_vel_occlusion_simulation_imputed'), log=None, split='test')

            # # investigating high OAO / OAC_t0 ratios
            # print(f"{exp_df['OAO']=}")
            # print(f"{exp_df['OAC_t0']=}")
            # mask = exp_df['OAO'] > exp_df['OAC_t0']
            # exp_df = exp_df[mask & exp_df['OAC_t0'] != 0.]
            # exp_df['OAO_by_OAC_t0'] = exp_df['OAO'] / exp_df['OAC_t0']
            # print(exp_df.sort_values('OAO_by_OAC_t0', ascending=False)[['OAO', 'OAC_t0', 'OAO_by_OAC_t0']])

            # retrieve the corresponding entry name and dataset index
            instance_name = f"{instance_number}".rjust(8, '0')
            instance_index = dataloader_exp.get_instance_idx(instance_num=instance_number)

            # mini_df = exp_df.loc[instance_number, instance_number, :]
            # mini_df = remove_k_sample_columns(mini_df)
            # print(f"Instance Dataframe:\n{mini_df}")
            show_agent_pred = []

            # preparing the figure
            fig, ax = plt.subplots(figsize=figsize)
            fig.canvas.manager.set_window_title(f"{experiment_name}_{instance_name}")

            checkpoint_name = config_exp.get_best_val_checkpoint_name()
            saved_preds_dir = os.path.join(
                config_exp.result_dir, dataloader_exp.dataset_name, checkpoint_name, 'test'
            )

            # retrieve the input data dict
            input_dict = dataloader_exp.__getitem__(instance_index)
            if 'map_homography' not in input_dict.keys():
                input_dict['map_homography'] = dataloader_exp.map_homography

            # retrieve the prediction data dict
            pred_file = os.path.join(saved_preds_dir, instance_name)
            print(f"{pred_file=}")
            assert os.path.exists(pred_file)
            with open(pred_file, 'rb') as f:
                pred_dict = pickle.load(f)
            pred_dict['map_homography'] = input_dict['map_homography']

            visualize_input_and_predictions(
                draw_ax=ax,
                data_dict=input_dict,
                pred_dict=pred_dict,
                show_rgb_map=True,
                show_gt_agent_ids=show_pred_ids,
                show_obs_agent_ids=None,
                show_pred_agent_ids=show_pred_ids,
                past_pred_alpha=0.5,
                future_pred_alpha=0.1 if highlight_only_past_pred else 0.5
            )
            ax.legend()
            ax.set_title(experiment_name)
            fig.subplots_adjust(wspace=0.10, hspace=0.0)
        plt.show()

        print(EXPERIMENT_SEPARATOR)

    # t-tests of score diff dependent on last observed timestep categories ############################################
    if args.ttest is not None:
        print("\n\nT-TESTS:\n\n")
        assert len(args.ttest) in {0, 2}
        assert args.cfg is not None
        experiment_names = args.cfg

        exp_dicts = get_all_results_directories()
        exp_dicts = [exp_dict for exp_dict in exp_dicts if exp_dict['split'] in ['test']]
        exp_dicts = [exp_dict for exp_dict in exp_dicts if exp_dict['experiment_name'] in experiment_names]
        # exp_dicts = [exp_dict for exp_dict in exp_dicts if exp_dict['dataset_used'] in ['fully_observed']]

        test_scores = MIN_SCORES + MEAN_SCORES

        ref_index = get_reference_indices()
        ref_past_pred_lengths = get_perf_scores_df(
            experiment_name='const_vel_occlusion_simulation',
            dataset_used='occlusion_simulation',
            model_name='untrained',
            split='test'
        )
        ref_past_pred_lengths = ref_past_pred_lengths.iloc[ref_past_pred_lengths.index.isin(ref_index)]
        ref_past_pred_lengths = ref_past_pred_lengths['past_pred_length']

        df_filter = get_df_filter(ref_index=ref_index, filters=args.filter)
        ref_past_pred_lengths = df_filter(ref_past_pred_lengths)

        if len(args.ttest) == 2:

            category_1, category_2 = args.ttest
            out_df_columns = [
                'experiment', 'dataset_used', 'test_score', 'n_1', 'mean_1', 's^2_1', 'n_2', 'mean_2', 's^2_2',
                't_stat', 'df', 'p_value', 't_critical', 'significant'
            ]

            category_1_index = ref_past_pred_lengths[ref_past_pred_lengths == category_1].index
            category_2_index = ref_past_pred_lengths[ref_past_pred_lengths == category_2].index

            out_df = pd.DataFrame(columns=out_df_columns)

            for exp_dict in exp_dicts:

                exp_name = exp_dict['experiment_name']
                dataset_used = exp_dict['dataset_used']
                model_name = exp_dict['model_name']
                split = exp_dict['split']

                experiment_df = get_perf_scores_df(
                    experiment_name=exp_name,
                    dataset_used=dataset_used,
                    model_name=model_name,
                    split=split
                )
                if df_filter is not None:
                    experiment_df = df_filter(experiment_df)

                for test_score in test_scores:

                    scores_1 = experiment_df.iloc[experiment_df.index.isin(category_1_index)][test_score]
                    scores_2 = experiment_df.iloc[experiment_df.index.isin(category_2_index)][test_score]
                    assert all(scores_1.index == category_1_index)
                    assert all(scores_2.index == category_2_index)

                    scores_1 = scores_1.values
                    scores_2 = scores_2.values

                    # import numpy as np
                    # example A:
                    # scores_1 = np.array([27.5, 21.0, 19.0, 23.6, 17.0, 17.9, 16.9, 20.1, 21.9, 22.6, 23.1, 19.6, 19.0, 21.7, 21.4])
                    # scores_2 = np.array([27.1, 22.0, 20.8, 23.4, 23.4, 23.5, 25.8, 22.0, 24.8, 20.2, 21.9, 22.1, 22.9, 20.5, 24.4])
                    # example B:
                    # scores_1 = np.array([17.2, 20.9, 22.6, 18.1, 21.7, 21.4, 23.5, 24.2, 14.7, 21.8])
                    # scores_2 = np.array([21.5, 22.8, 21.0, 23.0, 21.6, 23.6, 22.5, 20.7, 23.4, 21.8, 20.7, 21.7, 21.5, 22.5, 23.6, 21.5, 22.5, 23.5, 21.5, 21.8])
                    # example C:
                    # scores_1 = np.array([19.8, 20.4, 19.6, 17.8, 18.5, 18.9, 18.3, 18.9, 19.5, 22.0])
                    # scores_2 = np.array([28.2, 26.6, 20.1, 23.3, 25.2, 22.1, 17.7, 27.6, 20.6, 13.7, 23.2, 17.5, 20.6, 18.0, 23.9, 21.6, 24.3, 20.4, 24.0, 13.2])

                    is_significant, t_stat, p_val, df, t_crit = perform_ttest(array_a=scores_1, array_b=scores_2)

                    row_dict = {
                        'experiment': exp_name,
                        'dataset_used': dataset_used,
                        'n_1': len(scores_1),
                        'mean_1': scores_1.mean(),
                        's^2_1': scores_1.std(ddof=1)**2,
                        'n_2': len(scores_2),
                        'mean_2': scores_2.mean(),
                        's^2_2': scores_2.std(ddof=1)**2,
                        'test_score': test_score,
                        't_stat': t_stat,
                        'p_value': p_val,
                        'df': df,
                        't_critical': t_crit,
                        'significant': is_significant
                    }

                    out_df.loc[len(out_df)] = row_dict

            print(f"The goal of the t-tests is to evaluate whether performance metric scores differ significantly between "
                  f"different last-observation timestep categories.\nThe chosen last observation timestep categories for "
                  f"the following set of t-tests are ({category_1}, {category_2}):\n")

            for test_score in test_scores:
                print(f"{test_score}:")
                print(out_df[out_df['test_score'] == test_score])
                print("")

        else:

            # comparisons = [(1, cat_2) for cat_2 in range(2, 6)]
            comparisons = [(0, cat_2) for cat_2 in range(1, 7)]
            def comp_name(comp): return f"-{comp[0]}/-{comp[1]}"

            row_index_tuples = [(exp_dict['experiment_name'], exp_dict['dataset_used']) for exp_dict in exp_dicts]
            row_df_index = pd.MultiIndex.from_tuples(row_index_tuples, names=['experiment', 'dataset_used'])
            col_index_tuples = [(test_score, comp_name(comp)) for test_score in test_scores for comp in comparisons]
            col_df_index = pd.MultiIndex.from_tuples(col_index_tuples, names=['test_score', 'categories'])

            out_df = pd.DataFrame(index=row_df_index, columns=col_df_index)

            for exp_dict in exp_dicts:
                exp_name = exp_dict['experiment_name']
                dataset_used = exp_dict['dataset_used']
                model_name = exp_dict['model_name']
                split = exp_dict['split']

                experiment_df = get_perf_scores_df(
                    experiment_name=exp_name,
                    dataset_used=dataset_used,
                    model_name=model_name,
                    split=split
                )
                if df_filter is not None:
                    experiment_df = df_filter(experiment_df)

                for test_score in test_scores:

                    for comp in comparisons:
                        category_1, category_2 = comp

                        category_1_index = ref_past_pred_lengths[ref_past_pred_lengths == category_1].index
                        category_2_index = ref_past_pred_lengths[ref_past_pred_lengths == category_2].index

                        scores_1 = experiment_df.iloc[experiment_df.index.isin(category_1_index)][test_score]
                        scores_2 = experiment_df.iloc[experiment_df.index.isin(category_2_index)][test_score]
                        assert all(scores_1.index == category_1_index)
                        assert all(scores_2.index == category_2_index)

                        scores_1 = scores_1.values
                        scores_2 = scores_2.values

                        is_significant, t_stat, p_val, df, t_crit = perform_ttest(array_a=scores_1, array_b=scores_2)

                        out_df.loc[(exp_name, dataset_used), (test_score, comp_name(comp))] = is_significant

            print(out_df)

        print(EXPERIMENT_SEPARATOR)

    # score boxplots vs last observed timesteps #######################################################################
    if args.boxplots:
        print("\n\nBOXPLOTS:\n\n")
        assert args.cfg is not None
        experiment_names = args.cfg

        exp_dicts = get_all_results_directories()
        exp_dicts = [exp_dict for exp_dict in exp_dicts if exp_dict['split'] in ['test']]
        exp_dicts = [exp_dict for exp_dict in exp_dicts if exp_dict['experiment_name'] in experiment_names]
        # exp_dicts = [exp_dict for exp_dict in exp_dicts if exp_dict['dataset_used'] not in ['fully_observed']]
        # exp_dicts = [exp_dict for exp_dict in exp_dicts if exp_dict['dataset_used'] in ['fully_observed']]

        boxplot_scores = [
            'min_ADE', 'min_FDE',
            'mean_ADE', 'mean_FDE',
            'min_past_ADE', 'min_past_FDE',
            'mean_past_ADE', 'mean_past_FDE'
        ]
        ylims = [
            (0.0, 11), (0.0, 9),
            (0.0, 25), (0.0, 37),
            (0.0, None), (0.0, None),
            (0.0, None), (0.0, None),
        ]

        figsize = (9, 6)

        boxplot_experiments_together = True
        boxplot_experiments_individually = False

        ref_index = get_reference_indices()
        ref_past_pred_lengths = get_perf_scores_df(
            experiment_name='const_vel_occlusion_simulation',
            dataset_used='occlusion_simulation',
            model_name='untrained',
            split='test'
        )
        ref_past_pred_lengths = ref_past_pred_lengths.iloc[ref_past_pred_lengths.index.isin(ref_index)]
        ref_past_pred_lengths = ref_past_pred_lengths['past_pred_length']

        df_filter = get_df_filter(ref_index=ref_index, filters=args.filter)
        ref_past_pred_lengths = df_filter(ref_past_pred_lengths)

        # print(f"{ref_past_pred_lengths[ref_past_pred_lengths==6]=}")
        if boxplot_experiments_together:
            for plot_score, ylim in zip(boxplot_scores, ylims):
                fig, ax = plt.subplots(figsize=figsize)
                make_box_plot_occlusion_lengths(
                    draw_ax=ax,
                    experiments=exp_dicts,
                    plot_score=plot_score,
                    categorization=ref_past_pred_lengths,
                    df_filter=df_filter,
                    ylim=ylim,
                    legend=False
                )
                ax.set_title(f"{plot_score} vs. Last Observed timestep")

                if SAVE:
                    boxplot_directory = os.path.join(PERFORMANCE_ANALYSIS_DIRECTORY, 'boxplots')
                    os.makedirs(boxplot_directory, exist_ok=True)

                    filename = f"{plot_score}.png"
                    filepath = os.path.join(boxplot_directory, filename)
                    print(f"saving boxplot to:\n{filepath}\n")
                    plt.savefig(filepath, dpi=300, bbox_inches='tight')

        if boxplot_experiments_individually:
            for exp_dict in exp_dicts:
                for plot_score in boxplot_scores:
                    fig, ax = plt.subplots(figsize=figsize)
                    make_box_plot_occlusion_lengths(
                        draw_ax=ax,
                        experiments=[exp_dict],
                        plot_score=plot_score,
                        categorization=ref_past_pred_lengths
                    )
                    ax.set_title(f"{plot_score} vs. Last Observed timestep")

        if SHOW:
            plt.show()

        if SAVE:
            print("BOXPLOTS: no saving implementation (yet)!")

            # boxplot_directory = os.path.join(PERFORMANCE_ANALYSIS_DIRECTORY, 'boxplots')
            # os.makedirs(boxplot_directory, exist_ok=True)
            #
            # experiment_dir = os.path.join(boxplot_directory, <EXPERIMENT_NAME>)
            # os.makedirs(experiment_dir, exist_ok=True)
            #
            # filename = f"{<PLOT_SCORE>}.png"
            # filepath = os.path.join(experiment_dir, filename)
            # print(f"saving boxplot to:\n{filepath}\n")
            # plt.savefig(filepath, dpi=300, bbox_inches='tight')
            # plt.close()

        print(EXPERIMENT_SEPARATOR)

    if args.stats_per_last_obs:
        print("\n\nPERFORMANCE STATISTICS BY LAST OBSERVED TIMESTEP GROUPS\n\n")
        assert args.cfg is not None
        experiment_names = args.cfg

        exp_dicts = get_all_results_directories()
        exp_dicts = [exp_dict for exp_dict in exp_dicts if exp_dict['split'] in ['test']]
        exp_dicts = [exp_dict for exp_dict in exp_dicts if exp_dict['experiment_name'] in experiment_names]

        scores = ['min_ADE', 'min_FDE']
        operations = ['mean', 'median', 'IQR']

        ref_index = get_reference_indices()
        ref_past_pred_lengths = get_perf_scores_df(
            experiment_name='const_vel_occlusion_simulation',
            dataset_used='occlusion_simulation',
            model_name='untrained',
            split='test'
        )
        ref_past_pred_lengths = ref_past_pred_lengths.iloc[ref_past_pred_lengths.index.isin(ref_index)]
        ref_past_pred_lengths = ref_past_pred_lengths['past_pred_length']

        df_filter = get_df_filter(ref_index=ref_index, filters=args.filter)
        ref_past_pred_lengths = df_filter(ref_past_pred_lengths)

        for exp_dict in exp_dicts:

            print(f"{exp_dict['experiment_name']}:\n")

            summary_df = scores_stats_df_per_occlusion_lengths(
                exp_dict=exp_dict,
                scores=scores,
                operations=operations,
                categorization=ref_past_pred_lengths,
                df_filter=df_filter
            )
            print(summary_df)
            print("\n\n")

    # OAC histograms ##################################################################################################
    if args.oac_histograms:
        figsize = (16, 10)
        plot_score = 'OAC_t0'      # 'OAC', 'OAC_t0', 'OAO'
        as_percentage = False

        print(f"\n\n{plot_score} HISTOGRAMS:\n\n")

        experiment_names = args.cfg

        for experiment_name in experiment_names:
            fig = plt.figure(figsize=figsize)
            make_oac_histograms_figure(fig=fig, experiment_name=experiment_name, plot_score=plot_score)

        if SHOW:
            plt.show()

        if SAVE:
            print("OAC_histograms: no saving implementation (yet)!")

        print(EXPERIMENT_SEPARATOR)

    # map compliance vs generic performance ###########################################################################
    if False:
        # Learning with(out) the occlusion map: map compliance difference vs ADE/FDE scores difference
        # uninteresting results, no matter the map score / trajectory score combination
        # actually, maybe a (very slight trend)
        base_experiment = 'v2_difficult_occlusions_pre'
        compare_experiment = 'v2_difficult_occlusions_dist_map_w50_pre'
        x_score = 'OAC_t0'
        y_score = 'min_FDE'

        base_df = get_perf_scores_df(base_experiment)
        comp_df = get_perf_scores_df(compare_experiment)
        base_df = base_df[base_df['past_pred_length'] != 0]
        comp_df = comp_df[comp_df['past_pred_length'] != 0]

        compare_rows = get_comparable_rows(base_df=base_df, compare_df=comp_df)
        diff_df = comp_df.loc[compare_rows].sub(base_df.loc[compare_rows])

        xs = diff_df[x_score].to_numpy()
        ys = diff_df[y_score].to_numpy()

        fig, ax = plt.subplots()
        ax.scatter(xs, ys, marker='x', color='red', alpha=0.3)
        ax.set_xlabel(f"Delta {x_score}")
        ax.set_ylabel(f"Delta {y_score}")
        ax.set_title(f"{compare_experiment} vs {base_experiment}")
        plt.show()

        fig, ax = plt.subplots(4, 3)
        for i, y_score in enumerate(['min_FDE', 'min_ADE', 'mean_FDE', 'mean_ADE']):
            for j, x_score in enumerate(['OAO', 'OAC', 'OAC_t0']):
                xs = diff_df[x_score].to_numpy()
                ys = diff_df[y_score].to_numpy()
                ax[i, j].scatter(xs, ys, marker='x', color='red', alpha=0.3)
                if j == 0:
                    ax[i, j].set_ylabel(f"Delta {y_score}")
                if i == 3:
                    ax[i, j].set_xlabel(f"Delta {x_score}")
                # ax[i, j].set_title(f"{compare_experiment} vs {base_experiment}")
                ax[i, j].grid(axis='y')
        fig.suptitle(f"{compare_experiment} vs {base_experiment}")
        plt.show()

    if False:
        # Map compliance scores vs ADE/FDE scores heatmaps
        experiment_name = 'v2_difficult_occlusions_pre'
        experiment_name = 'v2_difficult_occlusions_dist_map_w50_pre'
        x_score = 'OAC_t0'
        y_score = 'min_FDE'

        exp_df = get_perf_scores_df(experiment_name)
        exp_df = exp_df[exp_df['past_pred_length'] != 0]
        exp_df = remove_k_sample_columns(exp_df)

        xs = exp_df[x_score].to_numpy()
        ys = exp_df[y_score].to_numpy()

        fig, ax = plt.subplots()
        ax.scatter(xs, ys, marker='x', color='red', alpha=0.3)
        ax.set_xlabel(f"{x_score}")
        ax.set_ylabel(f"{y_score}")
        ax.set_title(f"{experiment_name}")
        plt.show()

        fig, ax = plt.subplots(4, 3)
        for i, (y_score, vmax_value) in enumerate(zip(
                ['min_FDE', 'min_ADE', 'mean_FDE', 'mean_ADE'],
                [80, 80, 80, 80]
        )):
            for j, x_score in enumerate(['OAO', 'OAC', 'OAC_t0']):

                xs = exp_df[x_score].to_numpy()
                ys = exp_df[y_score].to_numpy()

                isnan_mask = np.isnan(xs)

                xs = xs[~isnan_mask]
                ys = ys[~isnan_mask]

                if False:
                    # scatter plot
                    ax[i, j].scatter(xs, ys, marker='x', color='red', alpha=0.3)
                else:
                    H, yedges, xedges = np.histogram2d(ys, xs, bins=[50, 20])
                    im = ax[i, j].pcolormesh(xedges, yedges, H, cmap='rainbow', vmin=0.0, vmax=vmax_value)

                    divider = mpl_toolkits.axes_grid1.make_axes_locatable(ax[i, j])
                    cax = divider.append_axes('right', size='2%', pad=0.02)

                    fig.colorbar(im, cax=cax, orientation='vertical')

                if j == 0:
                    ax[i, j].set_ylabel(f"{y_score}")
                if i == 3:
                    ax[i, j].set_xlabel(f"{x_score}")
                # ax[i, j].set_title(f"{compare_experiment} vs {base_experiment}")
                ax[i, j].grid(axis='y')
        fig.suptitle(f"{experiment_name}")
        plt.show()

    if False:
        import copy
        # OAO / OAC / OAC_t0 correlation
        experiment_name = 'v2_difficult_occlusions'
        mode = 'scatter'        # 'scatter' | 'heatmap'

        my_cmap = copy.copy(matplotlib.colormaps['rainbow'])  # copy the default cmap
        my_cmap.set_bad((0, 0, 0))

        hist_bins = 20
        d_bin = 1/(hist_bins-1)
        hist_range = np.array([0-d_bin/2, 1+d_bin/2])
        hist_range = [hist_range, hist_range]

        scores = ['OAO', 'OAC', 'OAC_t0']

        exp_df = get_perf_scores_df(experiment_name)
        exp_df = exp_df[exp_df['past_pred_length'] != 0]
        exp_df = remove_k_sample_columns(exp_df)

        fig, ax = plt.subplots(len(scores), len(scores))

        for i, x_score in enumerate(scores):
            for j, y_score in enumerate(scores):
                xs = exp_df[x_score].to_numpy()
                ys = exp_df[y_score].to_numpy()

                isnan_mask = np.logical_or(np.isnan(xs), np.isnan(ys))
                is_perfect_mask = np.logical_and(xs == 1.0, ys == 1.0)
                mask = np.logical_or(isnan_mask, is_perfect_mask)

                xs = xs[~isnan_mask]
                ys = ys[~isnan_mask]

                if mode == 'scatter':
                    ax[i, j].scatter(xs, ys, marker='x', color='red', alpha=0.1)
                elif mode == 'heatmap':
                    h, xedges, yedges, im = ax[i, j].hist2d(
                        xs, ys,
                        bins=hist_bins, range=hist_range, cmap=my_cmap, norm='log'
                    )

                    divider = mpl_toolkits.axes_grid1.make_axes_locatable(ax[i, j])
                    cax = divider.append_axes('right', size='2%', pad=0.02)
                    fig.colorbar(im, cax=cax, orientation='vertical')

                ax[i, j].set_aspect('equal', 'box')
                ax[i, j].set_xlabel(f"{x_score}")
                ax[i, j].set_ylabel(f"{y_score}")
        fig.suptitle(experiment_name)
        plt.show()

    if args.cv_wrong_map_rate:
        # evaluating the rate at which a Constant Velocity model fails to comply with the occlusion map
        cv_model_name = 'const_vel_occlusion_simulation'

        cv_perf_df = get_perf_scores_df(experiment_name=cv_model_name)
        cv_perf_df = cv_perf_df[cv_perf_df['past_pred_length'] > 0]

        failed_cv_oac_t0 = (cv_perf_df['OAC_t0'] == 0.)
        print(f"Out of all {len(failed_cv_oac_t0)} occluded cases,\n"
              f"the constant velocity model misplaced the current position of the agent as being "
              f"outside the occluded zone "
              f"{sum(failed_cv_oac_t0)} times ({sum(failed_cv_oac_t0)/len(failed_cv_oac_t0)*100:.2f}%)")

    if False:
        # evaluating insightfulness of the occlusion map between
        #   - occlusionformer_no_map
        #   - occlusionformer_with_occl_map
        # we are particularly interested in instances where a CV model performs poorly

        COMPARE_SCORES = OCCLUSION_MAP_SCORES
        COMPARE_SCORES = PAST_ADE_SCORES + PAST_FDE_SCORES
        COMPARE_SCORES = ADE_SCORES + FDE_SCORES
        cv_model_name = 'const_vel_occlusion_simulation'
        no_map_name = 'v2_occluded_pre'
        yes_map_name = 'v2_difficult_occlusions_dist_map_w50_pre'
        experiment_names = [yes_map_name, no_map_name, cv_model_name]

        perf_summary = generate_performance_summary_df(
            experiment_names=experiment_names, metric_names=DISTANCE_METRICS+PRED_LENGTHS+OCCLUSION_MAP_SCORES
        )
        perf_summary.sort_values(by='min_FDE', inplace=True)

        print(f"Performance summary:")
        print(perf_summary)

        cv_perf_df = get_perf_scores_df(experiment_name=cv_model_name)
        cv_perf_df = cv_perf_df[cv_perf_df['past_pred_length'] > 0]
        no_map_perf_df = get_perf_scores_df(experiment_name=no_map_name)
        no_map_perf_df = no_map_perf_df[no_map_perf_df['past_pred_length'] > 0]
        yes_map_perf_df = get_perf_scores_df(experiment_name=yes_map_name)
        yes_map_perf_df = yes_map_perf_df[yes_map_perf_df['past_pred_length'] > 0]

        print(len(cv_perf_df))
        print(len(no_map_perf_df))
        print(len(yes_map_perf_df))

        failed_cv_oac_t0 = (cv_perf_df['OAC_t0'] == 0.)
        print(f"Out of all {len(failed_cv_oac_t0)} occluded cases,\n"
              f"the constant velocity model misplaced the current position of the agent as being "
              f"outside the occluded zone "
              f"{sum(failed_cv_oac_t0)} times ({sum(failed_cv_oac_t0)/len(failed_cv_oac_t0)*100:.2f}%)")

        cv_perf_df = cv_perf_df[failed_cv_oac_t0]
        no_map_perf_df = no_map_perf_df[failed_cv_oac_t0]
        yes_map_perf_df = yes_map_perf_df[failed_cv_oac_t0]

        assert all(cv_perf_df.index == no_map_perf_df.index)
        assert all(cv_perf_df.index == yes_map_perf_df.index)

        # sample_rows = np.random.choice(cv_perf_df.index, 5, replace=False)
        # [print(sample) for sample in sample_rows]

        fig, ax = plt.subplots()
        boxplot_dict = {score_name: None for score_name in COMPARE_SCORES}
        for score_name in COMPARE_SCORES:
            diff = (yes_map_perf_df[score_name] - no_map_perf_df[score_name]).to_numpy()
            boxplot_dict[score_name] = diff

        ax.axhline(0, linestyle='--', color='k', alpha=0.1)  # horizontal line through y=0

        box_plot_xs = []
        box_plot_ys = []
        for k, v in boxplot_dict.items():
            box_plot_xs.append(k)
            box_plot_ys.append(v)

        bplot = ax.boxplot(box_plot_ys, positions=(range(len(box_plot_ys))))
        ax.set_xticklabels(box_plot_xs)

        plt.show()

    if args.comp_phase_1_2:

        raise NotImplementedError

        # checking the performance difference between phase 1 (model) and phase 2 (model + Dlow for diversity sampling)
        experiment_list = [
            OCCLUSIONFORMER_CAUSAL_ATTENTION_FULLY_OBSERVED_314,
            BASELINE_NO_POS_CONCAT,
            OCCLUSIONFORMER_CAUSAL_ATTENTION,
            OCCLUSIONFORMER_MOMENTARY,
            SDD_BASELINE_OCCLUSIONFORMER,
            OCCLUSIONFORMER_WITH_OCCL_MAP,
            OCCLUSIONFORMER_NO_MAP,
            OCCLUSIONFORMER_WITH_OCCL_MAP_IMPUTED,
            OCCLUSIONFORMER_IMPUTED,
            OCCLUSIONFORMER_CAUSAL_ATTENTION_FULLY_OBSERVED_162,
            OCCLUSIONFORMER_CAUSAL_ATTENTION_FULLY_OBSERVED,
        ]

        metric_names = ADE_SCORES + FDE_SCORES

        # list of experiment names (phase 1 and phase 2)
        phase_1_list = [f"{name}_pre" for name in experiment_list]
        phase_2_list = experiment_list

        # extracting the performance summaries
        perf_df_1 = generate_performance_summary_df(experiment_names=phase_1_list, metric_names=metric_names)
        perf_df_2 = generate_performance_summary_df(experiment_names=phase_2_list, metric_names=metric_names)

        experiment_id_columns = ['experiment', 'dataset_used']

        diff_df = perf_df_2[experiment_id_columns].copy()
        for metric_name in metric_names:
            diff_df[f"P1:{metric_name}"] = perf_df_1[metric_name]
            diff_df[f"P2:{metric_name}"] = perf_df_2[metric_name]
            diff_df[f"Delta:{metric_name}"] = perf_df_2[metric_name] - perf_df_1[metric_name]

        if SHOW:
            print(f"{diff_df}")
        if SAVE:
            print(f"Sorry, saving functionality not implemented for this performance evaluation...")
            raise NotImplementedError

    print(f"\n\nGoodbye!")
