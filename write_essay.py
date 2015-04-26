import margin_leverage
import util
import Investor
import Market
import TaxRates
import plots
from datetime import datetime
import os
import shutil
import re
import math
from scipy.stats import norm

"""This file writes the full text of my essay about leveraged 
investing. It dynamically computes the results presented. The reason
I created a Python program for doing this is so that if I changed
the underlying code, I could rerun the program and thereby refresh
the paper's results. The essay is formatted for copying and pasting
into WordPress's editor, not as standalone HTML, so it looks weird
if just opened in the browser."""

REPLACE_STR_FRONT = "<REPLACE>"
REPLACE_STR_END = "</REPLACE>"

def write_essay(skeleton, outfile, prev_path, num_trials, 
                use_local_image_file_paths, use_multiprocessing):
    """The following are the markers in the text that indicate
    where to replace with output numbers."""

    # Get original text.
    output_text = skeleton.read()

    # Compute the results.
    margin_leverage.optimal_leverage_for_all_scenarios(num_trials, False, prev_path, use_multiprocessing=use_multiprocessing)

    """Read and parse the results."""
    # Get prefix for the default results files.
    default_broker_max_margin_to_assets_ratio = default_investor.broker_max_margin_to_assets_ratio
    file_prefix_for_default_MTA = margin_leverage.file_prefix_for_optimal_leverage_specific_scenario(default_broker_max_margin_to_assets_ratio)

    # Loop through scenarios, recording their results.
    all_scenarios = margin_leverage.get_all_scenarios_list()
    for scenario in all_scenarios:
        # Get scenario abbreviation
        abbrev = margin_leverage.scenario_to_folder_abbreviation(scenario)

        # Navigate to the right folder and paths
        folder_for_this_scenario = margin_leverage.dir_prefix_for_optimal_leverage_specific_scenario(scenario)
        path_to_folder_for_this_scenario = os.path.join(prev_path,folder_for_this_scenario)
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
        add_figures("optimal_leverage_graph", output_text, optimal_leverage_graph, prev_path, use_local_image_file_paths)
        # Now add other figures, for the default margin-to-assets amount
        for graph_type in ["hist_margin", "wealthtraj", "avgMTA", "indMTA", "carrcg"]:
            path_to_current_figure = "{}_{}.png".format(prefix_for_default_results_files, graph_type)
            add_figures(graph_type, output_text, path_to_current_figure, prev_path, use_local_image_file_paths)

        """Now scenario-specific content: Default scenario"""
        if scenario == "Default":
            (amount_better, percent_better) = how_much_better_is_margin_in_thousands_of_dollars(results_table_contents)
            output_text = output_text.replace(REPLACE_STR_FRONT + "margin_better_than_regular_thousands_of_dollars" + REPLACE_STR_END, amount_better)
            output_text = output_text.replace(REPLACE_STR_FRONT + "margin_better_than_regular_percent" + REPLACE_STR_END, percent_better)
        elif scenario == "No unemployment or inflation or taxes or black swans":
            no_unemployment_etc_results_table_contents = results_table_contents

    
    """Add default params and calculations using those params"""
    add_param_settings(output_text)
    add_theoretical_calculations(output_text, no_unemployment_etc_results_table_contents)

    # Add the date to the output file. Run this at the end because
    # the computations above may take days or weeks. :P
    cur_date = datetime.now().strftime("%d %b. %Y")
    output_text = output_text.replace(REPLACE_STR_FRONT + "date_of_last_update" + REPLACE_STR_END, cur_date)

    outfile.write(output_text)

def add_param_settings(output_text):
    add_investor_params(output_text)
    add_market_params(output_text)
    add_tax_params(output_text)

def add_investor_params(output_text):
    default_investor = Investor.Investor()
    for param in ["years_until_donate", 
                  "annual_real_income_growth_percent", 
                  "match_percent_from_401k",
                  "broker_max_margin_to_assets_ratio",
                  "monthly_probability_of_layoff",
                  "monthly_probability_find_work_after_laid_off"]:
        output_text = output_text.replace(REPLACE_STR_FRONT + param + REPLACE_STR_END, getattr(default_investor,param))
    initial_income_properly_formatted = "${:,}".format(default_investor.initial_annual_income_for_investing)
    output_text = output_text.replace(REPLACE_STR_FRONT + "initial_annual_income_for_investing" + REPLACE_STR_END, initial_income_properly_formatted)

def add_market_params(output_text):
    # global variable
    output_text = output_text.replace(REPLACE_STR_FRONT + "trading_days_per_year" + REPLACE_STR_END, Market.TRADING_DAYS_PER_YEAR)

    # Now do default param values
    default_market = Market.Market()

    for param in ["annual_mu", "annual_sigma", 
                  "annual_margin_interest_rate", 
                  "inflation_rate", "medium_black_swan_prob", 
                  "annual_sigma_for_medium_black_swan",
                  "large_black_swan_prob", 
                  "annual_sigma_for_large_black_swan"]:
        output_text = output_text.replace(REPLACE_STR_FRONT + param + REPLACE_STR_END, getattr(default_market,param))

    for param in ["annual_mu", "annual_sigma", 
                  "annual_margin_interest_rate"]:
        param_as_percent = "{}%".format((round( 100*getattr(default_market,param) ,0)))
    output_text = output_text.replace(REPLACE_STR_FRONT + param + "_as_percent" + REPLACE_STR_END, param_as_percent)

def add_tax_params(output_text):
    default_taxes = TaxRates.TaxRates()
    for param in ["short_term_cap_gains_rate", 
                  "long_term_cap_gains_rate", "state_income_tax"]:
        output_text = output_text.replace(REPLACE_STR_FRONT + param + REPLACE_STR_END, getattr(default_taxes,param))

def add_theoretical_calculations(output_text, no_unemployment_etc_results_table_contents):
    default_investor = Investor.Investor()
    default_market = Market.Market()

    # some small calculations
    output_text = output_text.replace(REPLACE_STR_FRONT + "annual_mu/trading_days_per_year" + REPLACE_STR_END, 
                                      default_market.annual_mu/Market.TRADING_DAYS_PER_YEAR)
    output_text = output_text.replace(REPLACE_STR_FRONT + "annual_sigma/trading_days_per_year" + REPLACE_STR_END, 
                                      default_market.annual_sigma/Market.TRADING_DAYS_PER_YEAR)
    output_text = output_text.replace(REPLACE_STR_FRONT + "annual_sigma * sqrt(years_until_donate)" + REPLACE_STR_END, 
                                      round( default_market.annual_sigma * math.sqrt(default_investor.years_until_donate) ,2))

    # Theoretical vs. actual median
    theoretical_median = theoretical_median_PV_ignoring_complications()
    output_text = output_text.replace(REPLACE_STR_FRONT + "theoretical_median_PV_ignoring_complications" + REPLACE_STR_END, 
                                      util.format_as_dollar_string(theoretical_median))
    actual_median_string = parse_value_from_results_table(no_unemployment_etc_results_table_contents, "Regular","Median")
    actual_median = int(actual_median_string.replace("$","").replace(",",""))
    output_text = output_text.replace(REPLACE_STR_FRONT + "actual_median_ignoring_complications" + REPLACE_STR_END, 
                                      util.format_as_dollar_string(actual_median))

    # Theoretical vs. actual mean
    theoretical_mean = theoretical_median * math.exp(default_market.annual_sigma**2 * default_investor.years_until_donate/2)
    output_text = output_text.replace(REPLACE_STR_FRONT + "theoretical_mean_PV_ignoring_complications" + REPLACE_STR_END, 
                                      util.format_as_dollar_string(theoretical_mean))
    actual_mean_string = parse_value_from_results_table(no_unemployment_etc_results_table_contents, "Regular","Mean +/- stderr")
    actual_mean = get_mean_as_int_from_mean_plus_or_minus_stderr(actual_mean_string)
    output_text = output_text.replace(REPLACE_STR_FRONT + "actual_mean_ignoring_complications" + REPLACE_STR_END, 
                                      util.format_as_dollar_string(actual_mean))

    # sigma_{log(wealth)}
    actual_sigma_of_log_wealth = parse_value_from_results_table(no_unemployment_etc_results_table_contents, "Regular","&sigma;<sub>log(wealth)")
    output_text = output_text.replace(REPLACE_STR_FRONT + "actual_sigma_of_log_wealth" + REPLACE_STR_END, 
                                      actual_sigma_of_log_wealth)

    # Z-value threshold
    Z_value_threshold = default_investor.years_until_donate * (default_market.annual_margin_interest_rate - default_market.annual_mu) / default_market.annual_sigma
    output_text = output_text.replace(REPLACE_STR_FRONT + "Z_value_threshold" + REPLACE_STR_END, 
                                      round(Z_value_threshold,2))

    # Prob(Z <= threshold)
    prob_Z_leq_threshold = norm.cdf(Z_value_threshold)
    output_text = output_text.replace(REPLACE_STR_FRONT + "prob_Z_leq_threshold" + REPLACE_STR_END, 
                                      round(prob_Z_leq_threshold,2))

    # Prob(Z > threshold)
    prob_Z_gt_threshold = 1.0-prob_Z_leq_threshold
    output_text = output_text.replace(REPLACE_STR_FRONT + "prob_Z_gt_threshold" + REPLACE_STR_END, 
                                      round(prob_Z_gt_threshold,2))

    # Actual % times margin is better
    actual_percent_times_margin_is_better = parse_percent_times_margin_is_better(no_unemployment_etc_results_table_contents)
    output_text = output_text.replace(REPLACE_STR_FRONT + "actual_percent_times_margin_is_better" + REPLACE_STR_END, 
                                      actual_percent_times_margin_is_better)

def theoretical_median_PV_ignoring_complications():
    default_investor = Investor.Investor()
    default_market = Market.Market()
    initial_monthly_income = default_investor.initial_annual_income_for_investing / 12
    total_PV = 0.0
    for month in range(12 * default_investor.years_until_donate):
        cur_monthly_income = initial_monthly_income * (1+default_investor.annual_real_income_growth_percent/100.0)**month
        discounted_cur_monthly_income = cur_monthly_income * math.exp(- default_market.annual_mu * (month / 12.0))
        total_PV += discounted_cur_monthly_income
    return total_PV

def add_figures(graph_type, output_text, current_location_of_figure, 
                prev_path, use_local_image_file_paths):
    placeholder_string_for_figure = REPLACE_STR_FRONT + "{}_{}".format(abbrev,graph_type) + REPLACE_STR_END
    if re.match(placeholder_string_for_figure, output_text): # if yes, this figure appears in the HTML, so we should copy it and write the path to the figure
        # Copy the graph to be in the same folder as the essay HTML
        new_figure_file_name = "{}_{}.png".format(abbrev, graph_type)
        copy_destination_for_graph = os.path.join(prev_path,new_figure_file_name)
        shutil.copyfile(current_location_of_figure, copy_destination_for_graph)

        # Replace the path to the optimal-leverage graph in the HTML file
        if use_local_image_file_paths:
            replacement_graph_path = copy_destination_for_graph
        else: # use WordPress path that will exist once we upload the file
            now = datetime.now()
            year = now.strftime('%Y')
            month = now.strftime('%m')
            full_timestamp = now.strftime('%d%b%Y_%Hh%Mm%Ss')
            replacement_graph_path = "http://reducing-suffering.org/wp-content/uploads/{}/{}/{}_{}".format(year, month, full_timestamp, new_figure_file_name)
        output_text = output_text.replace(placeholder_string_for_figure, replacement_graph_path)

def how_much_better_is_margin_in_thousands_of_dollars(results_table_contents):
    margin_EV = get_mean_as_int_from_mean_plus_or_minus_stderr(parse_value_from_results_table(results_table_contents, "Margin", "Mean +/- stderr"))
    regular_EV = get_mean_as_int_from_mean_plus_or_minus_stderr(parse_value_from_results_table(results_table_contents, "Regular", "Mean +/- stderr"))
    diff_in_thousands_of_dollars = int(round( (margin_EV-regular_EV)/1000 ,0))
    percent_better = int(round( 100.0*(margin_EV-regular_EV)/regular_EV ,0))
    return (diff_in_thousands_of_dollars, percent_better)

def get_mean_as_int_from_mean_plus_or_minus_stderr(input_string):
    """Convert something like '$37,343 +/- $250' to 37343"""
    modified_string = input_string.replace("$","")
    modified_string = input_string.replace(",","")
    values = modified_string.split()
    return int(values[0])

def parse_value_from_results_table(results_table_contents, row_name, col_name):
    NUM_COLUMNS = 6
    regex_for_columns = "".join([" <td><i>(.+)</i></td>" for column in range(NUM_COLUMNS)])
    text = '<tr><td><i>{}</i></td>{}'.format(row_name, regex_for_columns)
    matches = re.match(text, results_table_contents)
    assert matches, "Didn't find a match for that row!"

    header_text = '<tr><td><i>Type</i></td>{}'.format(regex_for_columns)
    header_matches = re.match(header_text, results_table_contents)
    assert header_matches, "Didn't match the header!"

    cur_group_num = 1 # Start at 1 because group 0 has the whole match at once. From 1 on are the individual matches.
    while cur_group_num <= NUM_COLUMNS:
        cur_col_name = header_matches.group(cur_group_num)
        if col_name == cur_col_name:
            assert matches.group(cur_group_num), "This value is empty!"
            return matches.group(cur_group_num)
    raise Exception("No matching column found")

def parse_percent_times_margin_is_better(results_table_contents):
    matches = re.match(r"Margin is better than regular (\d+)% of the time",results_table_contents)
    assert matches, "Didn't find a match for % of times margin did better!"
    return matches.group(1)

if __name__ == "__main__":
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
        timestamp = datetime.now().strftime('%Y%b%d_%Hh%Mm%Ss')
        cur_folder = os.path.join(full_path_of_essays_dir,timestamp)
        os.mkdir(cur_folder) # should be unique because it's a timestamp accurate within seconds

        # Create the name of the current essay version.
        essay_path = os.path.join(cur_folder, "essay.html")

        # Write file.
        with open(essay_path, "w") as outfile:
            write_essay(skeleton, outfile, cur_folder, 1, True, False)