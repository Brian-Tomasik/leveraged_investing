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
import time

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

def write_essay(skeleton, outfile, cur_working_dir, num_trials, 
                use_local_image_file_paths, approx_num_simultaneous_processes,
                data_already_exists, timestamp):
    """The following are the markers in the text that indicate
    where to replace with output numbers."""

    # Get original text.
    output_text = skeleton.read()

    # Compute the results if they don't already exist.
    if not data_already_exists:
        margin_leverage.optimal_leverage_for_all_scenarios(num_trials, False, cur_working_dir, 
                                                           approx_num_simultaneous_processes=approx_num_simultaneous_processes)

    """Read and parse the results."""
    # Get prefix for the default results files.
    default_investor = Investor.Investor()
    default_broker_max_margin_to_assets_ratio = default_investor.broker_max_margin_to_assets_ratio
    file_prefix_for_default_MTA = margin_leverage.file_prefix_for_optimal_leverage_specific_scenario(default_broker_max_margin_to_assets_ratio)

    # Loop through scenarios, recording their results.
    all_scenarios = margin_leverage.get_all_scenarios_list()
    for scenario in all_scenarios:
        # Get scenario abbreviation
        abbrev = margin_leverage.scenario_to_folder_abbreviation(scenario)

        # Navigate to the right folder and paths
        folder_for_this_scenario = margin_leverage.dir_prefix_for_optimal_leverage_specific_scenario(scenario)
        path_to_folder_for_this_scenario = os.path.join(cur_working_dir,folder_for_this_scenario)
        optimal_leverage_graph = os.path.join(path_to_folder_for_this_scenario,plots.optimal_leverage_graph_prefix() + ".png")
        prefix_for_default_results_files = os.path.join(path_to_folder_for_this_scenario,file_prefix_for_default_MTA)

        # Read results table
        results_table_file = margin_leverage.results_table_file_name(prefix_for_default_results_files)
        results_table_contents = None
        with open(results_table_file, "r") as results_table:
            results_table_contents = results_table.read()
            output_text = output_text.replace(REPLACE_STR_FRONT + "{}_results_table".format(abbrev) + REPLACE_STR_END, results_table_contents)
        
        """Next, possibly copy images to the HTML output folder
        if we need images for this scenario"""
        output_text = add_figures("optimal_leverage_graph", output_text, optimal_leverage_graph, 
                                  cur_working_dir, use_local_image_file_paths, abbrev, timestamp)
        # Now add other figures, for the default margin-to-assets amount
        for graph_type in ["hist_margin", "wealthtraj", "avgMTA", "indMTA", "carrcg"]:
            path_to_current_figure = "{}_{}.png".format(prefix_for_default_results_files, 
                                                        graph_type)
            output_text = add_figures(graph_type, output_text, path_to_current_figure, 
                                      cur_working_dir, use_local_image_file_paths, abbrev, timestamp)

        """Now scenario-specific content: Default scenario"""
        if scenario == "Default":
            (amount_better_mean, percent_better_mean) = how_much_better_is_margin_in_thousands_of_dollars(results_table_contents, "Mean &plusmn; stderr")
            output_text = output_text.replace(REPLACE_STR_FRONT + "margin_better_than_regular_thousands_of_dollars" + REPLACE_STR_END, str(amount_better_mean))
            output_text = output_text.replace(REPLACE_STR_FRONT + "margin_better_than_regular_percent" + REPLACE_STR_END, str(percent_better_mean))
            output_text = output_text.replace(REPLACE_STR_FRONT + "(1+margin_advantage)(1-long_term_cap_gains)" + REPLACE_STR_END, 
                                              str(round(margin_advantage_less_long_term_cap_gains(percent_better_mean),2)))
            (amount_better_median, percent_better_median) = how_much_better_is_margin_in_thousands_of_dollars(results_table_contents, "Median")
            output_text = output_text.replace(REPLACE_STR_FRONT + "margin_better_than_regular_median_percent" + REPLACE_STR_END, str(percent_better_median))
            (amount_better_EU, percent_better_EU) = how_much_better_is_margin_in_thousands_of_dollars(results_table_contents, "E[&radic;(wealth)] &plusmn; stderr")
            output_text = output_text.replace(REPLACE_STR_FRONT + "margin_better_than_regular_EU_percent" + REPLACE_STR_END, str(percent_better_EU))
        elif scenario == "No unemployment or inflation or taxes or black swans, only paid in first month":
            output_text = add_theoretical_calculations_for_no_unemployment_etc(output_text, results_table_contents)
        elif scenario == "No unemployment or inflation or taxes or black swans, only paid in first month, don't rebalance monthly":
            output_text = output_text.replace(REPLACE_STR_FRONT + "uitbfdontreb_percent_margin_better" + REPLACE_STR_END, parse_percent_times_margin_is_better(results_table_contents))
        elif scenario == "No unemployment or inflation or taxes or black swans, don't rebalance monthly":
            output_text = output_text.replace(REPLACE_STR_FRONT + "uitbdontreb_percent_margin_better" + REPLACE_STR_END, parse_percent_times_margin_is_better(results_table_contents))

    """Add default params and calculations using those params"""
    output_text = output_text.replace(REPLACE_STR_FRONT + "num_trials" + REPLACE_STR_END, str(num_trials))
    output_text = add_param_settings_and_related_calculations(output_text)
    output_text = add_general_theoretical_calculations(output_text)

    # Add the date to the output file. Run this at the end because
    # the computations above may take days or weeks. :P
    cur_date = datetime.now().strftime("%d %b. %Y")
    output_text = output_text.replace(REPLACE_STR_FRONT + "date_of_last_update" + REPLACE_STR_END, cur_date)

    # Done :) Write the final HTML
    outfile.write(output_text)

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
                  "monthly_probability_find_work_after_laid_off"]:
        output_text = output_text.replace(REPLACE_STR_FRONT + param + REPLACE_STR_END, 
                                          str(getattr(default_investor,param)))
    
    initial_annual_income_properly_formatted = "${:,}".format(default_investor.initial_annual_income_for_investing)
    output_text = output_text.replace(REPLACE_STR_FRONT + "initial_annual_income_for_investing" + REPLACE_STR_END, initial_annual_income_properly_formatted)

    broker_max_margin_to_assets_ratio_as_percent = int(round(default_investor.broker_max_margin_to_assets_ratio * 100,0))
    output_text = output_text.replace(REPLACE_STR_FRONT + "broker_max_margin_to_assets_ratio_as_percent" + REPLACE_STR_END, str(broker_max_margin_to_assets_ratio_as_percent))

    yearly_income_at_end_of_investing_period = default_investor.initial_annual_income_for_investing * (1+default_investor.annual_real_income_growth_percent/100.0)**default_investor.years_until_donate
    output_text = output_text.replace(REPLACE_STR_FRONT + "yearly_income_at_end_of_investing_period" + REPLACE_STR_END, util.format_as_dollar_string(yearly_income_at_end_of_investing_period))

    return output_text

def add_market_params_and_calculations(output_text):
    # global variable
    output_text = output_text.replace(REPLACE_STR_FRONT + "trading_days_per_year" + REPLACE_STR_END, str(Market.TRADING_DAYS_PER_YEAR))

    # Now do default param values
    default_market = Market.Market()

    for param in ["annual_mu", "annual_sigma", 
                  "annual_margin_interest_rate", 
                  "inflation_rate", "medium_black_swan_prob", 
                  "annual_sigma_for_medium_black_swan",
                  "large_black_swan_prob", 
                  "annual_sigma_for_large_black_swan"]:
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
    assert Market.TRADING_DAYS_PER_YEAR==252, "Trading days per year have changed, but the essay text still uses 252 days per year for black-swan calculations. Change that."
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

    output_text = output_text.replace(REPLACE_STR_FRONT + "initial_personal_max_margin_to_assets_relative_to_broker_max_as_percent" + REPLACE_STR_END, 
                                      str(int(round(100*BrokerageAccount.INITIAL_PERSONAL_MAX_MARGIN_TO_ASSETS_RELATIVE_TO_BROKER_MAX,0))))

    default_investor = Investor.Investor()
    volunary_max_margin_to_assets = default_investor.broker_max_margin_to_assets_ratio * BrokerageAccount.INITIAL_PERSONAL_MAX_MARGIN_TO_ASSETS_RELATIVE_TO_BROKER_MAX
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

def add_general_theoretical_calculations(output_text):
    default_investor = Investor.Investor()
    default_market = Market.Market()

    # Daily mu and sigma
    output_text = output_text.replace(REPLACE_STR_FRONT + "annual_mu/trading_days_per_year" + REPLACE_STR_END, 
                                      str(util.round_decimal_to_given_num_of_sig_figs(default_market.annual_mu/Market.TRADING_DAYS_PER_YEAR,2)))
    output_text = output_text.replace(REPLACE_STR_FRONT + "annual_sigma/sqrt(trading_days_per_year)" + REPLACE_STR_END, 
                                      str(util.round_decimal_to_given_num_of_sig_figs( default_market.annual_sigma/math.sqrt(Market.TRADING_DAYS_PER_YEAR) ,2)))

    # Sigma for whole period
    output_text = output_text.replace(REPLACE_STR_FRONT + "annual_sigma * sqrt(years_until_donate)" + REPLACE_STR_END, 
                                      str(round( default_market.annual_sigma * math.sqrt(default_investor.years_until_donate) ,2)))

    # Prob(at least 1 large-scale black swan)
    prob_at_least_1_big_black_swan = 1.0-.9999**(default_investor.years_until_donate * Market.TRADING_DAYS_PER_YEAR)
    output_text = output_text.replace(REPLACE_STR_FRONT + "prob_at_least_1_big_black_swan" + REPLACE_STR_END, 
                                      str(round(prob_at_least_1_big_black_swan,2)))

    # Kelly optimal ratio
    Kelly_ratio = (default_market.annual_mu-default_market.annual_margin_interest_rate)/(default_market.annual_sigma**2)
    Kelly_ratio_as_percent = int(round( 100*Kelly_ratio ,0))
    output_text = output_text.replace(REPLACE_STR_FRONT + "Kelly_ratio_as_percent" + REPLACE_STR_END, 
                                      str(Kelly_ratio_as_percent))
    return output_text

def add_theoretical_calculations_for_no_unemployment_etc(output_text, no_unemployment_etc_results_table_contents):
    default_investor = Investor.Investor()
    default_market = Market.Market()

    # Theoretical vs. actual median
    theoretical_median = default_investor.initial_annual_income_for_investing/12
    output_text = output_text.replace(REPLACE_STR_FRONT + "theoretical_median_PV_ignoring_complications" + REPLACE_STR_END, 
                                      util.format_as_dollar_string(theoretical_median))
    actual_median_string = parse_value_from_results_table(no_unemployment_etc_results_table_contents, "Regular","Median")
    actual_median = int(actual_median_string.replace("$","").replace(",",""))
    output_text = output_text.replace(REPLACE_STR_FRONT + "actual_median_ignoring_complications" + REPLACE_STR_END, 
                                      actual_median_string)

    # Theoretical vs. actual mean
    theoretical_mean = theoretical_median * math.exp(default_market.annual_sigma**2 * default_investor.years_until_donate/2)
    output_text = output_text.replace(REPLACE_STR_FRONT + "theoretical_mean_PV_ignoring_complications" + REPLACE_STR_END, 
                                      util.format_as_dollar_string(theoretical_mean))
    actual_mean_string = parse_value_from_results_table(no_unemployment_etc_results_table_contents, "Regular","Mean &plusmn; stderr")
    actual_mean = get_mean_as_int_from_mean_plus_or_minus_stderr(actual_mean_string)
    output_text = output_text.replace(REPLACE_STR_FRONT + "actual_mean_ignoring_complications" + REPLACE_STR_END, 
                                      util.format_as_dollar_string(actual_mean))

    # sigma_{log(wealth)}
    actual_sigma_of_log_wealth = parse_value_from_results_table(no_unemployment_etc_results_table_contents, "Regular","&sigma;<sub>log(wealth)</sub>")
    output_text = output_text.replace(REPLACE_STR_FRONT + "actual_sigma_of_log_wealth" + REPLACE_STR_END, 
                                      actual_sigma_of_log_wealth)

    # Z-value threshold
    Z_value_threshold = math.sqrt(default_investor.years_until_donate) * (default_market.annual_margin_interest_rate - default_market.annual_mu) / default_market.annual_sigma
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
    for month in range(12 * default_investor.years_until_donate):
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
        shutil.copyfile(current_location_of_figure, copy_destination_for_graph)

        # Replace the path to the optimal-leverage graph in the HTML file
        if use_local_image_file_paths:
            replacement_graph_path = copy_destination_for_graph
        else: # use WordPress path that will exist once we upload the file
            (year, month) = parse_year_and_month_from_timestamp(timestamp)
            replacement_graph_path = "http://reducing-suffering.org/wp-content/uploads/{}/{}/{}".format(year, month, new_figure_file_name)
        output_text = output_text.replace(placeholder_string_for_figure, replacement_graph_path)
    return output_text

def parse_year_and_month_from_timestamp(timestamp):
    """Timestamp looks like 2015Apr26_23h09m36s. We want to parse out
    2015 (the year) and 04 (the month)."""
    parsed_time = time.strptime(timestamp, TIMESTAMP_FORMAT)
    year = time.strftime('%Y',parsed_time)
    month = time.strftime('%m',parsed_time)
    return (year, month)

def how_much_better_is_margin_in_thousands_of_dollars(results_table_contents, column_name):
    margin_val = get_mean_as_int_from_mean_plus_or_minus_stderr(parse_value_from_results_table(results_table_contents, "Margin", column_name))
    regular_val = get_mean_as_int_from_mean_plus_or_minus_stderr(parse_value_from_results_table(results_table_contents, "Regular", column_name))
    diff_in_thousands_of_dollars = int(round( (margin_val-regular_val)/1000 ,0))
    percent_better = int(round( 100.0*(margin_val-regular_val)/regular_val ,0))
    return (diff_in_thousands_of_dollars, percent_better)

def get_mean_as_int_from_mean_plus_or_minus_stderr(input_string):
    """Convert something like '$37,343 &plusmn; $250' to 37343
    This also works for medians."""
    modified_string = input_string.replace("$","")
    modified_string = modified_string.replace(",","")
    values = modified_string.split()
    return int(values[0])

def parse_value_from_results_table(results_table_contents, row_name, column_name):
    NUM_COLUMNS = 6
    regex_for_header_columns = "".join([" <td><i>(.+)</i></td>" for column in range(NUM_COLUMNS)])
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
    DATA_ALREADY_EXISTS_AND_HAS_THIS_TIMESTAMP = None
    #DATA_ALREADY_EXISTS_AND_HAS_THIS_TIMESTAMP = "2015Apr26_23h09m36s"
    """if the above variable is non-None, it saves lots of computation and just computes the HTML 
    and copies the required figures from saved data"""
    data_already_exists = DATA_ALREADY_EXISTS_AND_HAS_THIS_TIMESTAMP is not None

    LOCAL_FILE_PATHS_IN_HTML = False

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
            NUM_TRIALS = 50
            #NUM_TRIALS = 1
            APPROX_NUM_SIMULTANEOUS_PROCESSES = 1
            #APPROX_NUM_SIMULTANEOUS_PROCESSES = 2
            write_essay(skeleton, outfile, cur_folder, NUM_TRIALS, LOCAL_FILE_PATHS_IN_HTML, 
                        APPROX_NUM_SIMULTANEOUS_PROCESSES, data_already_exists, timestamp)

        """Once this is finished, you should have a timestamped folder with an essay HTML file and
        a bunch of figures. Just bulk upload the figures to WordPress and copy-paste
        the HTML text into WordPress's text editor, and you're done!"""