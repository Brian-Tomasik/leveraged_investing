import margin_leverage
import util
import Investor
import Market
import TaxRates
import BrokerageAccount
import plots
from datetime import datetime
import os
import shutil
import re
import math
from scipy.stats import norm
#from scipy.optimize import fsolve # don't need this anymore
import numpy
import time
import leveraged_etf_returns
import write_results

"""This file writes the full text of my essay about leveraged 
investing. It dynamically computes the results presented. The reason
I created a Python program for doing this is so that if I changed
the underlying code, I could rerun the program and thereby refresh
the paper's results. The essay is formatted for copying and pasting
into WordPress's editor, not as standalone HTML, so it looks weird
if just opened in the browser."""

REPLACE_STR_FRONT = "<REPLACE>"
REPLACE_STR_END = "</REPLACE>"
TIMESTAMP_FORMAT = '%Y%b%d_%Hh%Mm%Ss'
OPTIMISTIC_MU = .08
LEV_ETF_LEVERAGE_RATIO = 2.0
LEV_ETF_NUM_SAMPLES = 1
NUM_LEV_ETF_TRAJECTORIES_TO_SAVE_AS_FIGURES = 10

def write_essay(skeleton, outfile, cur_working_dir, num_trials, 
                use_local_image_file_paths, approx_num_simultaneous_processes,
                data_already_exists, timestamp):
    """The following are the markers in the text that indicate
    where to replace with output numbers."""

    # Get original text.
    output_text = skeleton.read()

    # Compute the results if they don't already exist.
    default_investor = Investor.Investor()
    if not data_already_exists:
        # run leveraged-ETF sim
        leveraged_etf_returns.sweep_variations(leveraged_etf_returns.FUNDS_AND_EXPENSE_RATIOS, 
                                               LEV_ETF_LEVERAGE_RATIO, LEV_ETF_NUM_SAMPLES,
                                               NUM_LEV_ETF_TRAJECTORIES_TO_SAVE_AS_FIGURES, 
                                               cur_working_dir)
        # run margin sim
        margin_leverage.optimal_leverage_for_all_scenarios(num_trials, False, cur_working_dir, 
                                                           approx_num_simultaneous_processes=approx_num_simultaneous_processes)

    """Read and parse the results for leveraged ETFs."""
    starting_balance_for_leveraged_ETF_sim = default_investor.initial_annual_income_for_investing / \
        leveraged_etf_returns.MONTHS_PER_YEAR
    output_text = output_text.replace(REPLACE_STR_FRONT + "starting_balance_for_leveraged_ETF_sim" + REPLACE_STR_END, 
                                      str(starting_balance_for_leveraged_ETF_sim))
    output_text = output_text.replace(REPLACE_STR_FRONT + "LEV_ETF_LEVERAGE_RATIO" + REPLACE_STR_END, 
                                      str(LEV_ETF_LEVERAGE_RATIO))
    for (key, val) in leveraged_etf_returns.FUNDS_AND_EXPENSE_RATIOS.iteritems():
        output_text = output_text.replace(REPLACE_STR_FRONT + "%s_ETF_expense_ratio" % key + REPLACE_STR_END, str(val))
    for scenario in leveraged_etf_returns.LEV_ETF_SCENARIOS.keys():
        abbrev = leveraged_etf_returns.LEV_ETF_SCENARIOS[scenario]
        folder = os.path.join(cur_working_dir,abbrev)
        results_table_file = write_results.results_table_file_name(os.path.join(folder,""))
        with open(results_table_file, "r") as results_table:
            results_table_contents = results_table.read()
            output_text = output_text.replace(REPLACE_STR_FRONT + \
                "{}_results_table".format(abbrev) + REPLACE_STR_END, results_table_contents)
        if scenario == "Match theory":
            output_text = leveraged_ETF_compare_against_theory(output_text,results_table_contents,
                                                               starting_balance_for_leveraged_ETF_sim)
        output_text = add_figures(plots.EXPECTED_UTILITY_GRAPH_PREFIX, output_text, \
            os.path.join(folder,"_%s.png" % plots.EXPECTED_UTILITY_GRAPH_PREFIX), \
            cur_working_dir, use_local_image_file_paths, abbrev, timestamp)
        output_text = add_figures(plots.EXPECTED_SATURATION_UTILITY_GRAPH_PREFIX, output_text, \
            os.path.join(folder,"_%s.png" % plots.EXPECTED_SATURATION_UTILITY_GRAPH_PREFIX), \
            cur_working_dir, use_local_image_file_paths, abbrev, timestamp)
        for iter_num in xrange(NUM_LEV_ETF_TRAJECTORIES_TO_SAVE_AS_FIGURES):
            output_text = add_figures("sample_traj%i" % iter_num, output_text, \
                os.path.join(folder,"_regularvslev_iter%i.png" % iter_num), 
                cur_working_dir, use_local_image_file_paths, abbrev, timestamp)

    """Read and parse the results for margin."""
    # Get prefix for the default results files.
    default_broker_max_margin_to_assets_ratio = default_investor.broker_max_margin_to_assets_ratio
    file_prefix_for_default_MTA = margin_leverage.file_prefix_for_optimal_leverage_specific_scenario(default_broker_max_margin_to_assets_ratio)

    # Loop through scenarios, recording their results.
    all_scenarios = margin_leverage.SCENARIOS.keys()
    for scenario in all_scenarios:
        # Get scenario abbreviation
        abbrev = margin_leverage.SCENARIOS[scenario]

        # Navigate to the right folder and paths
        folder_for_this_scenario = margin_leverage.dir_prefix_for_optimal_leverage_specific_scenario(scenario)
        path_to_folder_for_this_scenario = os.path.join(cur_working_dir,folder_for_this_scenario)
        optimal_leverage_graph = os.path.join(path_to_folder_for_this_scenario,plots.OPTIMAL_LEVERAGE_GRAPH_PREFIX + ".png")
        prefix_for_default_results_files = os.path.join(path_to_folder_for_this_scenario,file_prefix_for_default_MTA)

        # Read results table
        results_table_file = write_results.results_table_file_name(prefix_for_default_results_files)
        results_table_contents = None
        with open(results_table_file, "r") as results_table:
            results_table_contents = results_table.read()
            output_text = output_text.replace(REPLACE_STR_FRONT + "{}_results_table".format(abbrev) + REPLACE_STR_END, results_table_contents)
        
        """Next, possibly copy images to the HTML output folder
        if we need images for this scenario"""
        output_text = add_figures("optimal_leverage_graph", output_text, optimal_leverage_graph, 
                                  cur_working_dir, use_local_image_file_paths, abbrev, timestamp)
        # Now add other figures, for the default margin-to-assets amount
        for graph_type in ["bothhist", "wealthtraj", "avgMTA", "indMTA", "carrcg", "percdiff",
                           plots.EXPECTED_UTILITY_GRAPH_PREFIX,
                           plots.EXPECTED_SATURATION_UTILITY_GRAPH_PREFIX]:
            path_to_current_figure = "{}_{}.png".format(prefix_for_default_results_files, 
                                                        graph_type)
            output_text = add_figures(graph_type, output_text, path_to_current_figure, 
                                      cur_working_dir, use_local_image_file_paths, abbrev, timestamp)
        iter_num = 0
        next_attempted_figure_file = "%s_regularvsmar_iter%i.png" % \
            (prefix_for_default_results_files, iter_num)
        while os.path.exists(next_attempted_figure_file):
            output_text = add_figures("margin_sample_traj%i" % iter_num, output_text, \
                next_attempted_figure_file, 
                cur_working_dir, use_local_image_file_paths, abbrev, timestamp)
            iter_num += 1
            next_attempted_figure_file = "%s_regularvsmar_iter%i.png" % \
            (prefix_for_default_results_files, iter_num)

        """Now scenario-specific content: Default scenario"""
        if scenario == "Default":
            (amount_better_mean, percent_better_mean, margin_mean, regular_mean) = how_much_better_is_margin(results_table_contents, "Mean &plusmn; stderr")
            output_text = output_text.replace(REPLACE_STR_FRONT + "margin_mean_for_default_configuration" + REPLACE_STR_END, 
                                              util.format_as_dollar_string(margin_mean))
            output_text = output_text.replace(REPLACE_STR_FRONT + "regular_mean_for_default_configuration" + REPLACE_STR_END, 
                                              util.format_as_dollar_string(regular_mean))
            output_text = output_text.replace(REPLACE_STR_FRONT + "(margin_mean-initial_emergency_savings)/(regular_mean-initial_emergency_savings)" + REPLACE_STR_END, 
                                              str(round((margin_mean-default_investor.initial_emergency_savings)/(regular_mean-default_investor.initial_emergency_savings),2)))
            output_text = output_text.replace(REPLACE_STR_FRONT + "margin_better_than_regular" + REPLACE_STR_END, 
                                              util.format_as_dollar_string(amount_better_mean))
            output_text = output_text.replace(REPLACE_STR_FRONT + "margin_better_than_regular_per_year" + REPLACE_STR_END, 
                                              util.format_as_dollar_string(amount_better_mean/default_investor.years_until_donate))
            output_text = output_text.replace(REPLACE_STR_FRONT + "margin_better_than_regular_percent" + REPLACE_STR_END, 
                                              str(percent_better_mean))
            output_text = output_text.replace(REPLACE_STR_FRONT + "(1+margin_advantage)(1-long_term_cap_gains)" + REPLACE_STR_END, 
                                              str(round(margin_advantage_less_long_term_cap_gains(percent_better_mean),2)))
            (amount_better_median, percent_better_median, margin_median, regular_median) = how_much_better_is_margin(results_table_contents, "Median")
            output_text = output_text.replace(REPLACE_STR_FRONT + "margin_better_than_regular_median_percent" + REPLACE_STR_END, str(percent_better_median))
            # calculations for better expected sqrt_wealth
            (amount_better_expsqrtwealth, percent_better_expsqrtwealth, margin_expsqrt, regular_expsqrt) = how_much_better_is_margin(results_table_contents, 'E[&radic;<span style="text-decoration: overline">wealth</span>] &plusmn; stderr')
            output_text = output_text.replace(REPLACE_STR_FRONT + "margin_better_than_regular_expsqrtwealth_percent" + REPLACE_STR_END, 
                                              str(percent_better_expsqrtwealth))
            equiv_percent_increase_in_savings = round(((1+percent_better_expsqrtwealth/100.0)**2-1)*100.0,2)
            output_text = output_text.replace(REPLACE_STR_FRONT + "equiv_percent_increase_in_savings" + REPLACE_STR_END, 
                                              str(equiv_percent_increase_in_savings))
            equiv_fractional_increase_in_savings_plus_1 = round((1+percent_better_expsqrtwealth/100.0)**2,3)
            output_text = output_text.replace(REPLACE_STR_FRONT + "equiv_fractional_increase_in_savings_plus_1" + REPLACE_STR_END, 
                                              str(equiv_fractional_increase_in_savings_plus_1))
            fractional_increase_in_expsqrtwealth_plus_1 = round((1+percent_better_expsqrtwealth/100.0),3)
            output_text = output_text.replace(REPLACE_STR_FRONT + "fractional_increase_in_expsqrtwealth_plus_1" + REPLACE_STR_END, 
                                              str(fractional_increase_in_expsqrtwealth_plus_1))
            equiv_increase_in_savings = (equiv_percent_increase_in_savings/100.0) * default_investor.initial_annual_income_for_investing
            output_text = output_text.replace(REPLACE_STR_FRONT + "equiv_increase_in_savings" + REPLACE_STR_END, 
                                              util.format_as_dollar_string(equiv_increase_in_savings))

            output_text = output_text.replace(REPLACE_STR_FRONT + "margin_better_than_regular_expsqrtwealth_percent" + REPLACE_STR_END, str(percent_better_expsqrtwealth))
        elif scenario == "No unemployment or inflation or taxes or black swans, only paid in first month, don't taper off leverage toward end, voluntary max leverage equals broker max leverage, no emergency savings":
            output_text = add_theoretical_calculations_for_no_unemployment_etc(output_text, results_table_contents)

    """Add default params and calculations using those params"""
    output_text = output_text.replace(REPLACE_STR_FRONT + "num_trials" + REPLACE_STR_END, str(num_trials))
    output_text = add_param_settings_and_related_calculations(output_text)
    output_text = add_general_theoretical_calculations(output_text, cur_working_dir, timestamp,
                                                       use_local_image_file_paths)

    # Add the date to the output file. Run this at the end because
    # the computations above may take days or weeks. :P
    cur_datetime = datetime.now()
    cur_day_without_padding_zero = "{dt.day}".format(dt=cur_datetime)
    cur_month_and_year = cur_datetime.strftime("%b. %Y").replace("May.","May") # if month is May, don't use a . because it's not an abbreviation
    date_string = "%s %s" % (cur_day_without_padding_zero, cur_month_and_year)
    output_text = output_text.replace(REPLACE_STR_FRONT + "date_of_last_update" + \
        REPLACE_STR_END, date_string)

    # Done :) Write the final HTML
    outfile.write(output_text)

def leveraged_ETF_compare_against_theory(output_text, results_table_contents,starting_balance_for_leveraged_ETF_sim):
    default_investor = Investor.Investor()
    default_market = Market.Market()

    # Theoretical vs. actual median regular ETF
    theoretical_median_regular_ETF = starting_balance_for_leveraged_ETF_sim * \
        math.exp(-leveraged_etf_returns.FUNDS_AND_EXPENSE_RATIOS["regular"] * \
        default_investor.years_until_donate - \
        default_market.annual_sigma**2 * default_investor.years_until_donate/2)
    output_text = output_text.replace(REPLACE_STR_FRONT + "theoretical_median_regular_ETF" + REPLACE_STR_END, 
                                      util.format_as_dollar_string(theoretical_median_regular_ETF))
    actual_median_regular_ETF = parse_value_from_results_table(results_table_contents, "Regular","Median")
    output_text = output_text.replace(REPLACE_STR_FRONT + "actual_median_regular_ETF" + REPLACE_STR_END, 
                                      actual_median_regular_ETF)

    # Theoretical vs. actual mean regular ETF
    theoretical_mean_regular_ETF = starting_balance_for_leveraged_ETF_sim * \
        math.exp(-leveraged_etf_returns.FUNDS_AND_EXPENSE_RATIOS["regular"] * \
        default_investor.years_until_donate)
    output_text = output_text.replace(REPLACE_STR_FRONT + "theoretical_mean_regular_ETF" + REPLACE_STR_END, 
                                      util.format_as_dollar_string(theoretical_mean_regular_ETF))
    actual_mean_regular_ETF = parse_value_from_results_table(results_table_contents, "Regular","Mean &plusmn; stderr")
    output_text = output_text.replace(REPLACE_STR_FRONT + "actual_mean_regular_ETF" + REPLACE_STR_END, 
                                      actual_mean_regular_ETF)

    # Theoretical vs. actual median lev ETF
    theoretical_median_lev_ETF = starting_balance_for_leveraged_ETF_sim * math.exp( (default_market.annual_mu-default_market.annual_margin_interest_rate) * (LEV_ETF_LEVERAGE_RATIO-1.0) * default_investor.years_until_donate - leveraged_etf_returns.FUNDS_AND_EXPENSE_RATIOS["lev"] * default_investor.years_until_donate - LEV_ETF_LEVERAGE_RATIO**2 * default_market.annual_sigma**2 * default_investor.years_until_donate/2.0)
    output_text = output_text.replace(REPLACE_STR_FRONT + "theoretical_median_lev_ETF" + REPLACE_STR_END, 
                                      util.format_as_dollar_string(theoretical_median_lev_ETF))
    actual_median_lev_ETF = parse_value_from_results_table(results_table_contents, "Leveraged ETF","Median")
    output_text = output_text.replace(REPLACE_STR_FRONT + "actual_median_lev_ETF" + REPLACE_STR_END, 
                                      actual_median_lev_ETF)

    # Theoretical vs. actual mean lev ETF
    theoretical_mean_lev_ETF = starting_balance_for_leveraged_ETF_sim * math.exp( (default_market.annual_mu-default_market.annual_margin_interest_rate) * (LEV_ETF_LEVERAGE_RATIO-1.0) * default_investor.years_until_donate - leveraged_etf_returns.FUNDS_AND_EXPENSE_RATIOS["lev"] * default_investor.years_until_donate)
    output_text = output_text.replace(REPLACE_STR_FRONT + "theoretical_mean_lev_ETF" + REPLACE_STR_END, 
                                      util.format_as_dollar_string(theoretical_mean_lev_ETF))
    actual_mean_lev_ETF = parse_value_from_results_table(results_table_contents, "Leveraged ETF","Mean &plusmn; stderr")
    output_text = output_text.replace(REPLACE_STR_FRONT + "actual_mean_lev_ETF" + REPLACE_STR_END, 
                                      actual_mean_lev_ETF)

    return output_text

def margin_advantage_less_long_term_cap_gains(percent_better):
    default_tax_rates = TaxRates.TaxRates()
    return (1+percent_better/100.0)*(1-default_tax_rates.long_term_cap_gains_rate)

def add_param_settings_and_related_calculations(output_text):
    output_text = add_investor_params_and_calculations(output_text)
    output_text = add_market_params_and_calculations(output_text)
    output_text = add_tax_params(output_text)
    output_text = add_brokerage_params_and_calculations(output_text)
    return output_text

def add_investor_params_and_calculations(output_text):
    default_investor = Investor.Investor()
    for param in ["years_until_donate", 
                  "annual_real_income_growth_percent", 
                  "match_percent_from_401k",
                  "monthly_probability_of_layoff",
                  "monthly_probability_find_work_after_laid_off",
                  "initial_personal_max_margin_to_assets_relative_to_broker_max"]:
        output_text = output_text.replace(REPLACE_STR_FRONT + param + REPLACE_STR_END, 
                                          str(getattr(default_investor,param)))
    
    initial_annual_income_properly_formatted = util.format_as_dollar_string(default_investor.initial_annual_income_for_investing)
    output_text = output_text.replace(REPLACE_STR_FRONT + "initial_annual_income_for_investing" + REPLACE_STR_END, initial_annual_income_properly_formatted)

    output_text = output_text.replace(REPLACE_STR_FRONT + "initial_emergency_savings" + REPLACE_STR_END, \
        util.format_as_dollar_string(default_investor.initial_emergency_savings))

    broker_max_margin_to_assets_ratio_as_percent = int(round(default_investor.broker_max_margin_to_assets_ratio * 100.0,0))
    output_text = output_text.replace(REPLACE_STR_FRONT + "broker_max_margin_to_assets_ratio_as_percent" + REPLACE_STR_END, str(broker_max_margin_to_assets_ratio_as_percent))

    initial_personal_max_margin_to_assets_relative_to_broker_max_as_percent = int(round(default_investor.initial_personal_max_margin_to_assets_relative_to_broker_max * 100.0,0))
    output_text = output_text.replace(REPLACE_STR_FRONT + "initial_personal_max_margin_to_assets_relative_to_broker_max_as_percent" + REPLACE_STR_END, str(initial_personal_max_margin_to_assets_relative_to_broker_max_as_percent))
    

    yearly_income_at_end_of_investing_period = default_investor.initial_annual_income_for_investing * (1+default_investor.annual_real_income_growth_percent/100.0)**default_investor.years_until_donate
    output_text = output_text.replace(REPLACE_STR_FRONT + "yearly_income_at_end_of_investing_period" + REPLACE_STR_END, util.format_as_dollar_string(yearly_income_at_end_of_investing_period))

    assert default_investor.broker_max_margin_to_assets_ratio==.5, \
        "broker_max_margin_to_assets_ratio has changed, but the essay text still assumes '2X leverage' in many places. Change that."

    return output_text

def add_market_params_and_calculations(output_text):
    default_market = Market.Market()

    for param in ["annual_mu", "annual_sigma", 
                  "annual_margin_interest_rate", 
                  "inflation_rate", "medium_black_swan_prob", 
                  "annual_sigma_for_medium_black_swan",
                  "large_black_swan_prob", 
                  "annual_sigma_for_large_black_swan",
                  "trading_days_per_year"]:
        output_text = output_text.replace(REPLACE_STR_FRONT + param + REPLACE_STR_END, 
                                          str(getattr(default_market,param)))

    for param in ["annual_mu", "annual_sigma", 
                  "annual_margin_interest_rate", "inflation_rate"]:
        num_decimals = 1 if param == "annual_mu" else 0
        percent = round( 100.0*getattr(default_market,param) ,num_decimals)
        if param == "annual_sigma":
            percent = int(percent) # remove .0 from the end of the number
        param_as_percent = "{}%".format(percent)
        output_text = output_text.replace(REPLACE_STR_FRONT + param + "_as_percent" + REPLACE_STR_END, param_as_percent)

    # equity premium
    equity_premium = default_market.annual_mu - .015 # 1.5% is roughly the margin rate for Interactive Brokers in 2015
    equity_premium_as_percent = int(round(100*equity_premium,0))
    output_text = output_text.replace(REPLACE_STR_FRONT +"equity_premium_as_percent" + REPLACE_STR_END, str(equity_premium_as_percent))

    # Check that some params haven't changed because they're not parameterized in the HTML!
    assert default_market.annual_mu==.054, "Mu has changed, but the essay text still says \"ln(1 + .056) = .054\". Change that."
    assert default_market.trading_days_per_year==252, "Trading days per year have changed, but the essay text still uses 252 days per year for black-swan calculations. Change that."
    assert default_market.medium_black_swan_prob==.004 and default_market.annual_sigma_for_medium_black_swan==1.1 and default_market.large_black_swan_prob==.0001 and default_market.annual_sigma_for_large_black_swan==4.1, "Market params have changed relative to the skeleton HTML. That needs updating in the section Explanation of \"black swan\" probabilities"

    return output_text

def add_tax_params(output_text):
    default_tax_rates = TaxRates.TaxRates()
    for param in ["short_term_cap_gains_rate", 
                  "long_term_cap_gains_rate", "state_income_tax"]:
        output_text = output_text.replace(REPLACE_STR_FRONT + param + REPLACE_STR_END, 
                                          str(getattr(default_tax_rates,param)))
    return output_text

def add_brokerage_params_and_calculations(output_text):
    output_text = output_text.replace(REPLACE_STR_FRONT + "min_additional_purchase_amount" + REPLACE_STR_END, 
                                      str(BrokerageAccount.MIN_ADDITIONAL_PURCHASE_AMOUNT))

    output_text = output_text.replace(REPLACE_STR_FRONT + "fee_per_dollar_traded" + REPLACE_STR_END, str(BrokerageAccount.FEE_PER_DOLLAR_TRADED))

    default_investor = Investor.Investor()
    volunary_max_margin_to_assets = default_investor.broker_max_margin_to_assets_ratio * default_investor.initial_personal_max_margin_to_assets_relative_to_broker_max
    volunary_max_margin_to_assets_as_percent = int(round(100*volunary_max_margin_to_assets,0))
    output_text = output_text.replace(REPLACE_STR_FRONT + "volunary_max_margin_to_assets_as_percent" + REPLACE_STR_END, str(volunary_max_margin_to_assets_as_percent))

    # Example margin calculation
    """Let V be voluntary max margin-to-assets ratio. Given equity E, we want to 
    buy debt D such that D/(D+E) = V  ==>  D = DV + EV  ==>  D-DV = EV  ==>  
    D(1-V)=EV  ==>  D = EV/(1-V)"""
    example_loan_to_take_for_100_of_shares_equity = 100 * volunary_max_margin_to_assets / (1-volunary_max_margin_to_assets)
    assert util.abs_fractional_difference( example_loan_to_take_for_100_of_shares_equity / (example_loan_to_take_for_100_of_shares_equity+100) , 
                                          volunary_max_margin_to_assets) < .01, "My calculation here was wrong."
    output_text = output_text.replace(REPLACE_STR_FRONT + "example_loan_to_take_for_100_of_shares_equity" + REPLACE_STR_END, str(round(example_loan_to_take_for_100_of_shares_equity,2)))

    return output_text

def add_general_theoretical_calculations(output_text, cur_working_dir, timestamp,
                                         use_local_image_file_paths):
    default_investor = Investor.Investor()
    default_market = Market.Market()

    # mean(V_t)/mean(S_t)
    broker_imposed_leverage_limit = util.max_margin_to_assets_ratio_to_N_to_1_leverage(default_investor.broker_max_margin_to_assets_ratio)
    mean_margin_over_mean_regular = math.exp( (default_market.annual_mu - default_market.annual_margin_interest_rate) \
        * (broker_imposed_leverage_limit-1) * default_investor.years_until_donate )
    output_text = output_text.replace(REPLACE_STR_FRONT + "mean_margin_over_mean_regular" + REPLACE_STR_END, 
                                      str(round(mean_margin_over_mean_regular,2)))
    output_text = output_text.replace(REPLACE_STR_FRONT + "mean_margin_over_mean_regular_percent_advantage" + REPLACE_STR_END, 
                                      str(round(100*(mean_margin_over_mean_regular-1),0)))
    output_text = output_text.replace(REPLACE_STR_FRONT + "$100K * mean(V_t)/mean(S_t)" + REPLACE_STR_END, 
                                      util.format_as_dollar_string(100*mean_margin_over_mean_regular))
    mean_margin_over_mean_regular_t_is_half = math.exp( (default_market.annual_mu - default_market.annual_margin_interest_rate) \
        * (broker_imposed_leverage_limit-1) * default_investor.years_until_donate/2 )
    output_text = output_text.replace(REPLACE_STR_FRONT + "mean_margin_over_mean_regular_t_is_half" + REPLACE_STR_END, 
                                      str(round(mean_margin_over_mean_regular_t_is_half,2)))

    # Daily mu and sigma
    output_text = output_text.replace(REPLACE_STR_FRONT + "annual_mu/trading_days_per_year" + REPLACE_STR_END, 
                                      str(util.round_decimal_to_given_num_of_sig_figs(default_market.annual_mu/default_market.trading_days_per_year,2)))
    output_text = output_text.replace(REPLACE_STR_FRONT + "annual_sigma/sqrt(trading_days_per_year)" + REPLACE_STR_END, 
                                      str(util.round_decimal_to_given_num_of_sig_figs( default_market.annual_sigma/math.sqrt(default_market.trading_days_per_year) ,2)))

    # Sigma for whole period
    output_text = output_text.replace(REPLACE_STR_FRONT + "annual_sigma * sqrt(years_until_donate)" + REPLACE_STR_END, 
                                      str(round( default_market.annual_sigma * math.sqrt(default_investor.years_until_donate) ,2)))

    # Prob(at least 1 large-scale black swan)
    prob_at_least_1_big_black_swan = 1.0-.9999**(default_investor.years_until_donate * default_market.trading_days_per_year)
    output_text = output_text.replace(REPLACE_STR_FRONT + "prob_at_least_1_big_black_swan" + REPLACE_STR_END, 
                                      str(round(prob_at_least_1_big_black_swan,2)))

    # Kelly optimal ratio
    Kelly_ratio = (default_market.annual_mu-default_market.annual_margin_interest_rate)/(default_market.annual_sigma**2)
    Kelly_ratio_as_percent = int(round( 100*Kelly_ratio ,0))
    output_text = output_text.replace(REPLACE_STR_FRONT + "Kelly_ratio_as_percent" + REPLACE_STR_END, 
                                      str(Kelly_ratio_as_percent))

    # Kelly optimal ratio if mu = .1
    Kelly_ratio_if_mu_is_10_percent = round( (.1-default_market.annual_margin_interest_rate)/(default_market.annual_sigma**2) ,2)
    output_text = output_text.replace(REPLACE_STR_FRONT + "Kelly_ratio_if_mu_is_10_percent" + REPLACE_STR_END, 
                                      str(Kelly_ratio_if_mu_is_10_percent))

    # c* values
    c_star_for_alpha_equals_one_half = c_star(.5)
    output_text = output_text.replace(REPLACE_STR_FRONT + "c_star_for_alpha_equals_one_half" + REPLACE_STR_END, 
                                      str(round(c_star_for_alpha_equals_one_half,2)))
    output_text = output_text.replace(REPLACE_STR_FRONT + "c_star_for_alpha_equals_three_fourths" + REPLACE_STR_END, 
                                      str(round(c_star(.75),2)))
    output_text = output_text.replace(REPLACE_STR_FRONT + "c_star_for_alpha_equals_one_fourth" + REPLACE_STR_END, 
                                      str(round(c_star(.25),2)))

    # curve of c* vs. alpha
    NUM_POINTS = 1000
    MIN_ALPHA = 0
    MAX_ALPHA = .85
    alpha_values = numpy.linspace(MIN_ALPHA,MAX_ALPHA,NUM_POINTS)
    c_star_values = map(c_star, alpha_values)
    fig_name = "c_star_vs_alpha_%s.png" % timestamp
    fig_name_including_path = os.path.join(cur_working_dir,fig_name)
    """plots.theoretical_optimal_leverage_based_on_risk_tolerance(fig_name_including_path,
        *throw_out_alphas_where_c_star_is_extreme(alpha_values,c_star_values))""" # no longer needed
    plots.theoretical_optimal_leverage_based_on_risk_tolerance(fig_name_including_path,
                                                               alpha_values,c_star_values)
    if use_local_image_file_paths:
        html_fig_path = fig_name
    else: # use WordPress path that will exist once we upload the file
        html_fig_path = get_WordPress_img_url_path(timestamp, fig_name)
    output_text = output_text.replace(REPLACE_STR_FRONT + "c_star_vs_alpha_fig" + REPLACE_STR_END, 
                                      html_fig_path)

    # curve of c* vs. alpha for more optimistic mu assumption
    optimistic_c_star_values = map(lambda alpha: c_star(alpha,OPTIMISTIC_MU), alpha_values)
    optimistic_fig_name = "optimistic_c_star_vs_alpha_%s.png" % timestamp
    optimistic_fig_name_including_path = os.path.join(cur_working_dir,optimistic_fig_name)
    plots.theoretical_optimal_leverage_based_on_risk_tolerance(optimistic_fig_name_including_path,
                                                               alpha_values,optimistic_c_star_values)
    if use_local_image_file_paths:
        html_fig_path_optimistic = optimistic_fig_name
    else: # use WordPress path that will exist once we upload the file
        html_fig_path_optimistic = get_WordPress_img_url_path(timestamp, optimistic_fig_name)
    output_text = output_text.replace(REPLACE_STR_FRONT + "optimistic_c_star_vs_alpha_fig" + REPLACE_STR_END, 
                                      html_fig_path_optimistic)

    output_text = output_text.replace(REPLACE_STR_FRONT + "optimistic_mu" + REPLACE_STR_END, 
                                      str(OPTIMISTIC_MU))
    """
    NO LONGER USED

    # second derivative equation, "x" and "y" values
    x_value_for_second_derivative = default_market.annual_sigma**2 * default_investor.years_until_donate * (.5**2-.5)
    output_text = output_text.replace(REPLACE_STR_FRONT + "x_value_for_second_derivative" + REPLACE_STR_END, 
                                      str(x_value_for_second_derivative))
    y_value_for_second_derivative = (default_market.annual_mu-default_market.annual_margin_interest_rate)*default_investor.years_until_donate*.5
    output_text = output_text.replace(REPLACE_STR_FRONT + "y_value_for_second_derivative" + REPLACE_STR_END, 
                                      str(y_value_for_second_derivative))
    full_equation_with_x_y_and_c = x_value_for_second_derivative + (c_star_for_alpha_equals_one_half * x_value_for_second_derivative + y_value_for_second_derivative)**2
    assert full_equation_with_x_y_and_c < 0, "Oops. The second derivative isn't negative anymore, so this isn't a max."
    output_text = output_text.replace(REPLACE_STR_FRONT + "full_equation_with_x_y_and_c" + REPLACE_STR_END, 
                                      str(round(full_equation_with_x_y_and_c,2)))
    """

    # When expense ratio is worth it for leveraged ETFs
    W = 1800
    REG_ETF_EXP_RATIO = 0.001
    LEV_ETF_EXP_RATIO = 0.01
    default_K_threshold = W * default_investor.years_until_donate / \
        ( math.exp( (default_market.annual_mu - default_market.annual_margin_interest_rate) * \
       (broker_imposed_leverage_limit - 1.0) * default_investor.years_until_donate ) * \
       ( math.exp(-REG_ETF_EXP_RATIO * default_investor.years_until_donate) - \
       math.exp(-LEV_ETF_EXP_RATIO * default_investor.years_until_donate) ) )
    output_text = output_text.replace(REPLACE_STR_FRONT + "default_K_threshold" + REPLACE_STR_END, 
                                      util.format_as_dollar_string(default_K_threshold))
    mu09_K_threshold = W * default_investor.years_until_donate / \
        ( math.exp( (.09 - default_market.annual_margin_interest_rate) * \
       (broker_imposed_leverage_limit - 1.0) * default_investor.years_until_donate ) * \
       ( math.exp(-REG_ETF_EXP_RATIO * default_investor.years_until_donate) - \
       math.exp(-LEV_ETF_EXP_RATIO * default_investor.years_until_donate) ) )
    output_text = output_text.replace(REPLACE_STR_FRONT + "mu09_K_threshold" + REPLACE_STR_END, 
                                      util.format_as_dollar_string(mu09_K_threshold))
    W500_K_threshold = 500 * default_investor.years_until_donate / \
        ( math.exp( (default_market.annual_mu - default_market.annual_margin_interest_rate) * \
       (broker_imposed_leverage_limit - 1.0) * default_investor.years_until_donate ) * \
       ( math.exp(-REG_ETF_EXP_RATIO * default_investor.years_until_donate) - \
       math.exp(-LEV_ETF_EXP_RATIO * default_investor.years_until_donate) ) )
    output_text = output_text.replace(REPLACE_STR_FRONT + "W500_K_threshold" + REPLACE_STR_END, 
                                      util.format_as_dollar_string(W500_K_threshold))
    W4000_K_threshold = 4000 * default_investor.years_until_donate / \
        ( math.exp( (default_market.annual_mu - default_market.annual_margin_interest_rate) * \
       (broker_imposed_leverage_limit - 1.0) * default_investor.years_until_donate ) * \
       ( math.exp(-REG_ETF_EXP_RATIO * default_investor.years_until_donate) - \
       math.exp(-LEV_ETF_EXP_RATIO * default_investor.years_until_donate) ) )
    output_text = output_text.replace(REPLACE_STR_FRONT + "W4000_K_threshold" + REPLACE_STR_END, 
                                      util.format_as_dollar_string(W4000_K_threshold))
    W1000_mu09_K_threshold = 1000 * default_investor.years_until_donate / \
        ( math.exp( (.09 - default_market.annual_margin_interest_rate) * \
       (broker_imposed_leverage_limit - 1.0) * default_investor.years_until_donate ) * \
       ( math.exp(-REG_ETF_EXP_RATIO * default_investor.years_until_donate) - \
       math.exp(-LEV_ETF_EXP_RATIO * default_investor.years_until_donate) ) )
    output_text = output_text.replace(REPLACE_STR_FRONT + "W1000_mu09_K_threshold" + REPLACE_STR_END, 
                                      util.format_as_dollar_string(W1000_mu09_K_threshold))
    levexpr005_K_threshold = W * default_investor.years_until_donate / \
        ( math.exp( (default_market.annual_mu - default_market.annual_margin_interest_rate) * \
       (broker_imposed_leverage_limit - 1.0) * default_investor.years_until_donate ) * \
       ( math.exp(-REG_ETF_EXP_RATIO * default_investor.years_until_donate) - \
       math.exp(-.005 * default_investor.years_until_donate) ) )
    output_text = output_text.replace(REPLACE_STR_FRONT + "levexpr005_K_threshold" + REPLACE_STR_END, 
                                      util.format_as_dollar_string(levexpr005_K_threshold))
    lev3X_K_threshold = W * default_investor.years_until_donate / \
        ( math.exp( (default_market.annual_mu - default_market.annual_margin_interest_rate) * \
       (3 - 1.0) * default_investor.years_until_donate ) * \
       ( math.exp(-REG_ETF_EXP_RATIO * default_investor.years_until_donate) - \
       math.exp(-LEV_ETF_EXP_RATIO * default_investor.years_until_donate) ) )
    output_text = output_text.replace(REPLACE_STR_FRONT + "lev3X_K_threshold" + REPLACE_STR_END, 
                                      util.format_as_dollar_string(lev3X_K_threshold))

    # When expense ratio is worth it for leveraged ETFs, including taxes
    W = 1800
    REG_ETF_EXP_RATIO = 0.001
    LEV_ETF_EXP_RATIO = 0.01
    default_F = .05
    default_R = .28
    default_K_threshold_with_taxes = W * default_investor.years_until_donate / \
        ( math.exp( (default_market.annual_mu-default_market.annual_margin_interest_rate) * \
        (broker_imposed_leverage_limit-1.0) * default_investor.years_until_donate \
        - REG_ETF_EXP_RATIO * default_investor.years_until_donate ) - math.exp( \
        (1.0-default_F * default_R) * \
        (default_market.annual_mu-default_market.annual_margin_interest_rate) * \
        (broker_imposed_leverage_limit-1.0) * default_investor.years_until_donate - \
        (default_F * default_R * default_market.annual_mu + LEV_ETF_EXP_RATIO) * \
        default_investor.years_until_donate ) )
    output_text = output_text.replace(REPLACE_STR_FRONT + "default_K_threshold_with_taxes" + REPLACE_STR_END, 
                                      util.format_as_dollar_string(default_K_threshold_with_taxes))
    R14_K_threshold_with_taxes = W * default_investor.years_until_donate / \
        ( math.exp( (default_market.annual_mu-default_market.annual_margin_interest_rate) * \
        (broker_imposed_leverage_limit-1.0) * default_investor.years_until_donate \
        - REG_ETF_EXP_RATIO * default_investor.years_until_donate ) - math.exp( \
        (1.0-default_F * .14) * \
        (default_market.annual_mu-default_market.annual_margin_interest_rate) * \
        (broker_imposed_leverage_limit-1.0) * default_investor.years_until_donate - \
        (default_F * .14 * default_market.annual_mu + LEV_ETF_EXP_RATIO) * \
        default_investor.years_until_donate ) )
    output_text = output_text.replace(REPLACE_STR_FRONT + "R14_K_threshold_with_taxes" + REPLACE_STR_END, 
                                      util.format_as_dollar_string(R14_K_threshold_with_taxes))
    F20_K_threshold_with_taxes = W * default_investor.years_until_donate / \
        ( math.exp( (default_market.annual_mu-default_market.annual_margin_interest_rate) * \
        (broker_imposed_leverage_limit-1.0) * default_investor.years_until_donate \
        - REG_ETF_EXP_RATIO * default_investor.years_until_donate ) - math.exp( \
        (1.0-.2 * default_R) * \
        (default_market.annual_mu-default_market.annual_margin_interest_rate) * \
        (broker_imposed_leverage_limit-1.0) * default_investor.years_until_donate - \
        (.2 * default_R * default_market.annual_mu + LEV_ETF_EXP_RATIO) * \
        default_investor.years_until_donate ) )
    output_text = output_text.replace(REPLACE_STR_FRONT + "F20_K_threshold_with_taxes" + REPLACE_STR_END, 
                                      util.format_as_dollar_string(F20_K_threshold_with_taxes))
    F20R14_K_threshold_with_taxes = W * default_investor.years_until_donate / \
        ( math.exp( (default_market.annual_mu-default_market.annual_margin_interest_rate) * \
        (broker_imposed_leverage_limit-1.0) * default_investor.years_until_donate \
        - REG_ETF_EXP_RATIO * default_investor.years_until_donate ) - math.exp( \
        (1.0-.2 * .14) * \
        (default_market.annual_mu-default_market.annual_margin_interest_rate) * \
        (broker_imposed_leverage_limit-1.0) * default_investor.years_until_donate - \
        (.2 * .14 * default_market.annual_mu + LEV_ETF_EXP_RATIO) * \
        default_investor.years_until_donate ) )
    output_text = output_text.replace(REPLACE_STR_FRONT + "F20R14_K_threshold_with_taxes" + REPLACE_STR_END, 
                                      util.format_as_dollar_string(F20R14_K_threshold_with_taxes))

    return output_text

def c_star(alpha, custom_mu=None):
    """c* is optimal leverage. alpha is as in utility(wealth) = wealth^alpha"""
    if custom_mu:
        market = Market.Market(annual_mu=custom_mu)
    else:
        market = Market.Market()
    return (market.annual_mu - market.annual_margin_interest_rate) / \
        ( market.annual_sigma**2 * (1-alpha) )

"""
DON'T NEED THIS ANYMORE

def throw_out_alphas_where_c_star_is_extreme(alpha_values, c_star_values):
    assert len(alpha_values) == len(c_star_values), "Arrays aren't the same size."
    assert len(c_star_values) > 5, "This might not work so well for small alpha arrays."
    middle_of_c_star_array = len(c_star_values)/2
    typical_c_star = c_star_values[middle_of_c_star_array]
    MULTIPLE_WHEN_TOO_EXTREME = 10
    non_extreme_alphas_and_c_stars = [(alpha, c_star) for (alpha, c_star) in zip(alpha_values, c_star_values) if abs(c_star) <= MULTIPLE_WHEN_TOO_EXTREME * abs(typical_c_star)]
    non_extreme_alphas = [alpha for (alpha, c_star) in non_extreme_alphas_and_c_stars]
    non_extreme_c_stars = [c_star for (alpha, c_star) in non_extreme_alphas_and_c_stars]
    return (non_extreme_alphas, non_extreme_c_stars)

def solve_deriv_wrt_c_equals_zero(alpha):
    deriv_with_this_alpha = lambda c : deriv_wrt_c(c,alpha)
    GUESS = 1.0
    solution = fsolve(deriv_with_this_alpha, GUESS)
    assert len(solution) == 1, "Solution array has length other than 1."
    return solution[0]

def deriv_wrt_c(c, alpha):
    default_investor = Investor.Investor()
    default_market = Market.Market()
    return math.exp( (default_market.annual_margin_interest_rate + (default_market.annual_mu-default_market.annual_margin_interest_rate) * c) * default_investor.years_until_donate * alpha + (default_market.annual_sigma**2 * c**2/2.0) * default_investor.years_until_donate * (alpha**2 - alpha) ) * ( (default_market.annual_mu-default_market.annual_margin_interest_rate) * default_investor.years_until_donate * alpha + c*default_market.annual_sigma**2 * default_investor.years_until_donate * (alpha**2 - alpha) )
"""

def add_theoretical_calculations_for_no_unemployment_etc(output_text, no_unemployment_etc_results_table_contents):
    default_investor = Investor.Investor()
    default_market = Market.Market()

    # initial investment for the "no complications" runs
    one_month_pay = default_investor.initial_annual_income_for_investing/12
    output_text = output_text.replace(REPLACE_STR_FRONT + "one_month_pay" + REPLACE_STR_END, 
                                      util.format_as_dollar_string(one_month_pay))

    # Theoretical vs. actual median
    theoretical_median_PV_ignoring_complications = one_month_pay * math.exp(-default_market.annual_sigma**2*default_investor.years_until_donate/2)
    output_text = output_text.replace(REPLACE_STR_FRONT + "theoretical_median_PV_ignoring_complications" + REPLACE_STR_END, 
                                      util.format_as_dollar_string(theoretical_median_PV_ignoring_complications))
    actual_median_string = parse_value_from_results_table(no_unemployment_etc_results_table_contents, "Regular","Median")
    output_text = output_text.replace(REPLACE_STR_FRONT + "actual_median_ignoring_complications" + REPLACE_STR_END, 
                                      actual_median_string)

    # Theoretical vs. actual mean
    theoretical_mean_PV_ignoring_complications = one_month_pay
    output_text = output_text.replace(REPLACE_STR_FRONT + "theoretical_mean_PV_ignoring_complications" + REPLACE_STR_END, 
                                      util.format_as_dollar_string(theoretical_mean_PV_ignoring_complications))
    actual_mean_string = parse_value_from_results_table(no_unemployment_etc_results_table_contents, "Regular","Mean &plusmn; stderr")
    output_text = output_text.replace(REPLACE_STR_FRONT + "actual_mean_ignoring_complications" + REPLACE_STR_END, 
                                      actual_mean_string)

    # sigma_{ln(wealth)}
    actual_sigma_of_log_wealth = parse_value_from_results_table(no_unemployment_etc_results_table_contents, "Regular","&sigma;<sub>ln(wealth)</sub>")
    output_text = output_text.replace(REPLACE_STR_FRONT + "actual_sigma_of_log_wealth" + REPLACE_STR_END, 
                                      actual_sigma_of_log_wealth)

    # leverage amount, c
    broker_imposed_leverage_limit = util.max_margin_to_assets_ratio_to_N_to_1_leverage(default_investor.broker_max_margin_to_assets_ratio)
    output_text = output_text.replace(REPLACE_STR_FRONT + "broker_imposed_leverage_limit" + REPLACE_STR_END, 
                                      str(round(broker_imposed_leverage_limit,1)))

    # Theoretical vs. actual median for leveraged
    leveraged_theoretical_median_PV_ignoring_complications = one_month_pay *\
       math.exp( (default_market.annual_mu-default_market.annual_margin_interest_rate) * \
       (broker_imposed_leverage_limit-1.0) * default_investor.years_until_donate - \
       broker_imposed_leverage_limit**2 * default_market.annual_sigma**2 * \
       default_investor.years_until_donate/2)
    output_text = output_text.replace(REPLACE_STR_FRONT + "leveraged_theoretical_median_PV_ignoring_complications" + REPLACE_STR_END, 
                                      util.format_as_dollar_string(leveraged_theoretical_median_PV_ignoring_complications))
    leveraged_actual_median_string = parse_value_from_results_table(no_unemployment_etc_results_table_contents, "Margin","Median")
    output_text = output_text.replace(REPLACE_STR_FRONT + "leveraged_actual_median_ignoring_complications" + REPLACE_STR_END, 
                                      leveraged_actual_median_string)

    # Theoretical vs. actual mean for leveraged
    leveraged_theoretical_mean_PV_ignoring_complications = one_month_pay * \
        math.exp( (default_market.annual_mu-default_market.annual_margin_interest_rate) * \
       (broker_imposed_leverage_limit-1.0) * default_investor.years_until_donate )
    output_text = output_text.replace(REPLACE_STR_FRONT + "leveraged_theoretical_mean_PV_ignoring_complications" + REPLACE_STR_END, 
                                      util.format_as_dollar_string(leveraged_theoretical_mean_PV_ignoring_complications))
    leveraged_actual_mean_string = parse_value_from_results_table(no_unemployment_etc_results_table_contents, "Margin","Mean &plusmn; stderr")
    leveraged_actual_mean = get_mean_as_int_from_mean_plus_or_minus_stderr(leveraged_actual_mean_string)
    output_text = output_text.replace(REPLACE_STR_FRONT + "leveraged_actual_mean_ignoring_complications" + REPLACE_STR_END, 
                                      leveraged_actual_mean_string)

    # sigma_{ln(wealth)} for leveraged
    leveraged_theoretical_sigma_ln_wealth = broker_imposed_leverage_limit * \
        default_market.annual_sigma * math.sqrt(default_investor.years_until_donate)
    output_text = output_text.replace(REPLACE_STR_FRONT + "leveraged_theoretical_sigma_ln_wealth" + REPLACE_STR_END, 
                                      str(round(leveraged_theoretical_sigma_ln_wealth,2)))
    leveraged_actual_sigma_of_log_wealth = parse_value_from_results_table(no_unemployment_etc_results_table_contents, "Margin","&sigma;<sub>ln(wealth)</sub>")
    output_text = output_text.replace(REPLACE_STR_FRONT + "leveraged_actual_sigma_of_log_wealth" + REPLACE_STR_END, 
                                      leveraged_actual_sigma_of_log_wealth)


    # Z-value threshold
    Z_value_threshold = math.sqrt(default_investor.years_until_donate) * \
        ((broker_imposed_leverage_limit+1)*default_market.annual_sigma/2 - \
        (default_market.annual_mu - default_market.annual_margin_interest_rate) \
        / default_market.annual_sigma)
    output_text = output_text.replace(REPLACE_STR_FRONT + "Z_value_threshold" + REPLACE_STR_END, 
                                      str(round(Z_value_threshold,2)))

    # Prob(Z <= threshold)
    prob_Z_leq_threshold = norm.cdf(Z_value_threshold)
    output_text = output_text.replace(REPLACE_STR_FRONT + "prob_Z_leq_threshold" + REPLACE_STR_END, 
                                      str(round(prob_Z_leq_threshold,2)))

    # Prob(Z > threshold)
    prob_Z_gt_threshold = 1.0-prob_Z_leq_threshold
    output_text = output_text.replace(REPLACE_STR_FRONT + "prob_Z_gt_threshold" + REPLACE_STR_END, 
                                      str(round(prob_Z_gt_threshold,2)))

    # Actual % times margin is better
    actual_percent_times_margin_is_better = parse_percent_times_margin_is_better(no_unemployment_etc_results_table_contents)
    output_text = output_text.replace(REPLACE_STR_FRONT + "actual_percent_times_margin_is_better" + REPLACE_STR_END, 
                                      actual_percent_times_margin_is_better)
    return output_text

"""
NOT USING THIS ANYMORE...
def theoretical_median_PV_ignoring_complications():
    default_investor = Investor.Investor()
    default_market = Market.Market()
    initial_monthly_income = default_investor.initial_annual_income_for_investing / 12
    total_PV = 0.0
    for month in xrange(12 * default_investor.years_until_donate):
        cur_monthly_income = initial_monthly_income * (1+default_investor.annual_real_income_growth_percent/100.0)**math.floor(month/12)
        discounted_cur_monthly_income = cur_monthly_income * math.exp(- default_market.annual_mu * (month / 12.0))
        total_PV += discounted_cur_monthly_income
    return total_PV
"""

def add_figures(graph_type, output_text, current_location_of_figure, 
                cur_working_dir, use_local_image_file_paths, scenario_abbrev, timestamp):
    placeholder_string_for_figure = REPLACE_STR_FRONT + "{}_{}".format(scenario_abbrev,graph_type) + REPLACE_STR_END
    if re.search(".*{}.*".format(placeholder_string_for_figure), output_text): # if yes, this figure appears in the HTML, so we should copy it and write the path to the figure
        # Copy the graph to be in the same folder as the essay HTML
        new_figure_file_name = "{}_{}_{}.png".format(scenario_abbrev, graph_type, timestamp)
        copy_destination_for_graph = os.path.join(cur_working_dir,new_figure_file_name)
        if os.path.exists(current_location_of_figure):
            shutil.copyfile(current_location_of_figure, copy_destination_for_graph)
            # Replace the path to the optimal-leverage graph in the HTML file
            if use_local_image_file_paths:
                replacement_graph_path = copy_destination_for_graph
            else: # use WordPress path that will exist once we upload the file
                replacement_graph_path = get_WordPress_img_url_path(timestamp, new_figure_file_name)
            output_text = output_text.replace(placeholder_string_for_figure, replacement_graph_path)
    return output_text

def get_WordPress_img_url_path(timestamp, fig_name):
    (year, month) = parse_year_and_month_from_timestamp(timestamp)
    return "http://reducing-suffering.org/wp-content/uploads/{}/{}/{}".format(year, month, fig_name)

def parse_year_and_month_from_timestamp(timestamp):
    """Timestamp looks like 2015Apr26_23h09m36s. We want to parse out
    2015 (the year) and 04 (the month)."""
    parsed_time = time.strptime(timestamp, TIMESTAMP_FORMAT)
    year = time.strftime('%Y',parsed_time)
    month = time.strftime('%m',parsed_time)
    return (year, month)

def how_much_better_is_margin(results_table_contents, column_name):
    margin_val = get_mean_as_int_from_mean_plus_or_minus_stderr(parse_value_from_results_table(results_table_contents, "Margin", column_name))
    regular_val = get_mean_as_int_from_mean_plus_or_minus_stderr(parse_value_from_results_table(results_table_contents, "Regular", column_name))
    diff = margin_val-regular_val
    percent_better = round( 100.0*diff/regular_val ,1)
    return (diff, percent_better, float(margin_val), float(regular_val))

def get_mean_as_int_from_mean_plus_or_minus_stderr(input_string):
    """Convert something like '$37,343 &plusmn; $250' to 37343
    This also works for medians."""
    modified_string = input_string.replace("$","")
    modified_string = modified_string.replace(",","")
    values = modified_string.split()
    return int(values[0])

def parse_value_from_results_table(results_table_contents, row_name, column_name):
    NUM_COLUMNS = 6
    regex_for_header_columns = "".join([" <td><i>(.+)</i></td>" for column in xrange(NUM_COLUMNS)])
    regex_for_columns = regex_for_header_columns.replace("<i>","").replace("</i>","")

    text = '.*<tr><td><i>{}</i></td>{}.*'.format(row_name, regex_for_columns)
    matches = re.search(text, results_table_contents)
    assert matches, "Didn't find a match for that row!"

    header_text = '.*<tr><td><i>Type</i></td>{}.*'.format(regex_for_header_columns)
    header_matches = re.search(header_text, results_table_contents)
    assert header_matches, "Didn't match the header!"

    cur_group_num = 1 # Start at 1 because group 0 has the whole match at once. From 1 on are the individual matches.
    while cur_group_num <= NUM_COLUMNS:
        cur_col_name = header_matches.group(cur_group_num)
        if column_name == cur_col_name:
            assert matches.group(cur_group_num), "This value is empty!"
            return matches.group(cur_group_num)
        cur_group_num += 1
    raise Exception("No matching column found")

def parse_percent_times_margin_is_better(results_table_contents):
    matches = re.search(r".*Margin is better than regular (\d+(\.\d)?)% of the time.*",results_table_contents)
    assert matches, "Didn't find a match for % of times margin did better!"
    return matches.group(1)

if __name__ == "__main__":
    start_time = time.time()
    DATA_ALREADY_EXISTS_AND_HAS_THIS_TIMESTAMP = None
    #DATA_ALREADY_EXISTS_AND_HAS_THIS_TIMESTAMP = "2015May07_01h33m27s" # 100 trials of everything
    """if the above variable is non-None, it saves lots of computation and just computes the HTML 
    and copies the required figures from saved data"""
    data_already_exists = DATA_ALREADY_EXISTS_AND_HAS_THIS_TIMESTAMP is not None

    LOCAL_FILE_PATHS_IN_HTML = True

    # Open essay skeleton.
    SKELETON = "essay_skeleton.html"
    with open(SKELETON, "r") as skeleton:
        # Create essay directory if doesn't yet exist.
        ESSAYS_DIR_NAME = "essays"
        full_path_of_essays_dir = os.path.join(os.getcwd(), ESSAYS_DIR_NAME)
        if os.path.exists(full_path_of_essays_dir):
            assert os.path.isdir(full_path_of_essays_dir), "The path {} should be a folder for output essays".format(ESSAYS_DIR_NAME)
        else:
            os.mkdir(full_path_of_essays_dir)

        # Create a folder for the current essay version.
        if DATA_ALREADY_EXISTS_AND_HAS_THIS_TIMESTAMP:
            timestamp = DATA_ALREADY_EXISTS_AND_HAS_THIS_TIMESTAMP
        else:
            timestamp = datetime.now().strftime(TIMESTAMP_FORMAT)
        cur_folder = os.path.join(full_path_of_essays_dir,timestamp)
        if not DATA_ALREADY_EXISTS_AND_HAS_THIS_TIMESTAMP:
            os.mkdir(cur_folder) # should be unique because it's a timestamp accurate within seconds

        # Create the name of the current essay version.
        essay_path = os.path.join(cur_folder, "aaa_essay.html") # "aaa_" is to put it at the top of the file list

        # Write file.
        with open(essay_path, "w") as outfile:
            print """
==========
WARNING: If you're using saved data, all default values now, 
including NUM_TRIALS here, should be
_the same as when you ran the results being pointed to_
or else the params filled in to the output HTMl file will be wrong!
============
"""
            NUM_TRIALS = 1
            APPROX_NUM_SIMULTANEOUS_PROCESSES = 1
            #APPROX_NUM_SIMULTANEOUS_PROCESSES = 3
            write_essay(skeleton, outfile, cur_folder, NUM_TRIALS, LOCAL_FILE_PATHS_IN_HTML, 
                        APPROX_NUM_SIMULTANEOUS_PROCESSES, data_already_exists, timestamp)

        """Once this is finished, you should have a timestamped folder with an essay HTML file and
        a bunch of figures. Just bulk upload the figures to WordPress and copy-paste
        the HTML text into WordPress's text editor, and you're done!"""
    stop_time = time.time()
    print "\nStarted running at %s" % time.ctime(start_time)
    print "Finished running at %s" % time.ctime(stop_time)
    print "Hours elapsed = %f" % ((stop_time-start_time)/(60*60))