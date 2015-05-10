import util
import numpy
import math
import Market
import Investor
import TaxRates
import BrokerageAccount
import plots
from scipy.optimize import fsolve
import os
from os import path
import copy
import write_results
import margin_leverage
from random import Random

FUNDS_AND_EXPENSE_RATIOS = {"regular":.001, "lev":.01}
MODERATE_ANNUAL_FRACTION_OF_SHORT_TERM_CAP_GAINS = .1
HIGH_ANNUAL_FRACTION_OF_SHORT_TERM_CAP_GAINS = .5
MONTHS_PER_YEAR = 12

QUICK = False
if QUICK:
    LEV_ETF_SCENARIOS = {"Match theory":"ETF_match_theory"}
else:
    LEV_ETF_SCENARIOS = {"Match theory":"ETF_match_theory",
                         "Default":"ETF_default",
                         "Match theory, no expense ratios":"ETF_match_theory_no_exp_ratios",
                         "Default, no expense ratios":"ETF_default_no_exp_ratios",
                         "Default, moderate taxes":"ETF_default_moderate_taxes",
                         "Default, high taxes":"ETF_default_high_taxes",
                         "Default, 3X leverage":"ETF_default_3X",
                         "Default, 3X leverage, no expense ratios":"ETF_default_no_exp_ratios_3X"}

def one_run_daily_rebalancing(funds_and_expense_ratios, tax_rate, 
                              leverage_ratio, investor, market, iter_num,
                              outfilepath, randgenerator, num_trajectories_to_save_as_figures):
    investor.reset_employment_for_next_round()

    emergency_savings = dict()
    for type in funds_and_expense_ratios.keys():
        emergency_savings[type] = investor.initial_emergency_savings

    num_days = int(round(margin_leverage.DAYS_PER_YEAR * investor.years_until_donate,0))

    regular_val = 0
    lev_fund_val = 0

    daily_interest_rate = market.annual_margin_interest_rate/market.trading_days_per_year
    regular_daily_exp_ratio = funds_and_expense_ratios["regular"]/market.trading_days_per_year
    lev_fund_daily_exp_ratio = funds_and_expense_ratios["lev"]/market.trading_days_per_year

    historical_regular_values = []
    historical_lev_values = []
    num_times_randgenerator_was_called = 0

    PRINT_DEBUG_STUFF = False

    for day in xrange(num_days):
        if not util.day_is_weekend(day % margin_leverage.DAYS_PER_YEAR) and not util.day_is_holiday(day % margin_leverage.DAYS_PER_YEAR):
            # Update accounts to new daily return
            (today_return, num_times_randgenerator_was_called) = market.random_daily_return(
                day, randgenerator, num_times_randgenerator_was_called)
            if PRINT_DEBUG_STUFF and iter_num == 1:
                print "today return = %f" % today_return
            after_tax_today_return_for_lev_ETF_only = today_return * (1-tax_rate)
            # dS = S (mu * delta_t + sigma * sqrt(delta_t) * random_Z - exp_ratio * delta_t)
            # (new S) = (old S) + dS
            regular_val += regular_val * (today_return-regular_daily_exp_ratio)
            if regular_val < 0:
                regular_val = 0 # can't have negative return
            historical_regular_values.append(regular_val)
            lev_fund_val += lev_fund_val * (leverage_ratio * after_tax_today_return_for_lev_ETF_only \
                - (leverage_ratio-1)*daily_interest_rate - \
                lev_fund_daily_exp_ratio)
            if lev_fund_val < 0:
                lev_fund_val = 0 # go bankrupt
            historical_lev_values.append(lev_fund_val)

            # Update emergency savings
            for type in funds_and_expense_ratios.keys():
                emergency_savings[type] = max(0, emergency_savings[type] * (1+today_return))

        if day % margin_leverage.INTEREST_AND_SALARY_EVERY_NUM_DAYS == 0:
            years_elapsed = day/margin_leverage.DAYS_PER_YEAR # intentional int division
            pay = investor.current_annual_income(years_elapsed, day, market.inflation_rate) * \
                (float(margin_leverage.INTEREST_AND_SALARY_EVERY_NUM_DAYS) / margin_leverage.DAYS_PER_YEAR)
            regular_val += pay * (1-BrokerageAccount.FEE_PER_DOLLAR_TRADED)
            lev_fund_val += pay * (1-leverage_ratio*BrokerageAccount.FEE_PER_DOLLAR_TRADED)
            num_times_randgenerator_was_called = investor.randomly_update_employment_status_this_month(
                randgenerator, num_times_randgenerator_was_called)

        if PRINT_DEBUG_STUFF and iter_num == 1:
            print "Day %i, regular = %s, lev = %s, emerg_lev = %s" % (day, \
            util.format_as_dollar_string(regular_val), \
            util.format_as_dollar_string(lev_fund_val), \
            util.format_as_dollar_string(emergency_savings["lev"]))

    if iter_num < num_trajectories_to_save_as_figures:
        """
        DON'T DISCOUNT SO THAT GRAPHS ARE MORE COMPARABLE TO REAL ONES THAT YOU'D SEE....
        discounted_historical_regular_values = map(lambda wealth: \
            present_value(wealth, market.annual_mu, years), historical_regular_values)
        discounted_historical_lev_values = map(lambda wealth: \
            present_value(wealth, market.annual_mu, years), historical_lev_values)
        plots.graph_lev_ETF_and_underlying_trajectories(discounted_historical_regular_values, \
            discounted_historical_lev_values, outfilepath, iter_num)
        """
        plots.graph_lev_ETF_and_underlying_trajectories(historical_regular_values, \
            historical_lev_values, outfilepath, iter_num)

    return (market.present_value(regular_val+emergency_savings["regular"],
                                      investor.years_until_donate), 
            market.present_value(lev_fund_val+emergency_savings["lev"],
                                      investor.years_until_donate),
            num_times_randgenerator_was_called)

def many_runs(funds_and_expense_ratios, tax_rate, leverage_ratio, num_samples,
              investor, market, outfilepath, num_trajectories_to_save_as_figures,
              use_seed_for_randomness=True):
    if use_seed_for_randomness:
        randgenerator = Random("seedy character")
    else:
        randgenerator = None

    fund_types = funds_and_expense_ratios.keys()
    fund_arrays = dict()
    for type in fund_types:
        fund_arrays[type] = numpy.array([])
    prev_num_times_randgenerator_was_called = -9999 # junk

    # Get results
    num_lev_bankruptcies = 0
    for i in xrange(num_samples):
        output_values = one_run_daily_rebalancing(funds_and_expense_ratios, 
                                                  tax_rate, leverage_ratio, 
                                                  investor, market, i,
                                                  outfilepath, randgenerator,
                                                  num_trajectories_to_save_as_figures)
        assert len(output_values) == len(fund_types)+1, "output_values is wrong size"
        num_times_randgenerator_was_called = output_values[-1]
        if i > 0:
            assert num_times_randgenerator_was_called == prev_num_times_randgenerator_was_called, \
                "randgenerator was called different numbers of times across runs :("
        prev_num_times_randgenerator_was_called = num_times_randgenerator_was_called
        for j in xrange(len(fund_types)):
            fund_arrays[fund_types[j]] = numpy.append(fund_arrays[fund_types[j]], 
                                                      output_values[j])
            num_lev_bankruptcies += 1 if output_values[1]==0 else 0
        if i % 1000 == 0:
            print "Done with run %i." % i

    # Plot results
    if outfilepath:
        plots.graph_expected_utility_vs_alpha(numpy.array(fund_arrays[fund_types[0]]), \
            numpy.array(fund_arrays[fund_types[1]]), outfilepath)
        plots.graph_expected_utility_vs_wealth_saturation_cutoff(numpy.array(fund_arrays[fund_types[0]]), \
            numpy.array(fund_arrays[fund_types[1]]), outfilepath, 4, 7)

    # Write results
    with open(write_results.results_table_file_name(outfilepath), "w") as outfile:
            write_results.write_file_table(fund_arrays, fund_types, 
                                           float(num_lev_bankruptcies)/num_samples, outfile)

    # Print results
    for type in fund_types:
        lev_ratio_for_this_type = 1 if type == fund_types[0] else leverage_ratio
        print "Type: %s" % type
        print "mean = %s" % util.format_as_dollar_string(numpy.mean(fund_arrays[type]))
        print "median = %s" % util.format_as_dollar_string(numpy.median(fund_arrays[type]))
        print "25th percentile = %s" % util.format_as_dollar_string(util.percentile(fund_arrays[type],.25))
        print "min = %s" % util.format_as_dollar_string(numpy.min(fund_arrays[type]))
        print ""
    """
    NOT NEEDED ANYMORE
    print "alpha where expected utilities are equal = %s" % \
        find_alpha_where_expected_utilities_are_equal(
            fund_arrays[fund_types[0]],fund_arrays[fund_types[1]])
    """
    print "randgenerator called %i times. Check that this is equal across variants!" % \
        num_times_randgenerator_was_called

"""
NOT USED ANYMORE

def find_alpha_where_expected_utilities_are_equal(regular_vals, lev_fund_vals):
    LOW_ALPHA = .01
    HIGH_ALPHA = 1
    if expected_utility(lev_fund_vals, LOW_ALPHA) > expected_utility(regular_vals, LOW_ALPHA):
        return "lev fund is always better"
    elif expected_utility(lev_fund_vals, HIGH_ALPHA) < expected_utility(regular_vals, HIGH_ALPHA):
        return "regular is always better"
    else:
        # alpha where equal is between LOW_ALPHA and HIGH_ALPHA
        diff = lambda alpha: expected_utility(lev_fund_vals, alpha) - expected_utility(regular_vals, alpha)
        GUESS = .5 # alpha in the middle of the extremes
        root_arr = fsolve(diff, GUESS)
        assert len(root_arr) == 1, "Root array has length other than 1."
        return str(round(root_arr[0],3))

def expected_utility(numpy_array_of_wealth_values, alpha):
    return numpy.mean(map(lambda wealth: wealth**alpha, numpy_array_of_wealth_values))
"""

def sweep_variations(funds_and_expense_ratios, leverage_ratio, num_samples, 
                     num_trajectories_to_save_as_figures, outfilepath):
    for scenario in LEV_ETF_SCENARIOS.keys():
        dir = path.join(outfilepath, LEV_ETF_SCENARIOS[scenario])
        if not os.path.isdir(dir):
            os.mkdir(dir)
        tax_rate = 0
        funds_and_expense_ratios_to_use = copy.copy(funds_and_expense_ratios)
        leverage_ratio_to_use = leverage_ratio
        if "Match theory" in scenario:
            investor = Investor.Investor(monthly_probability_of_layoff=0,
                                         only_paid_in_first_month_of_sim=True,
                                         initial_emergency_savings=0)
            market = Market.Market(inflation_rate=0,medium_black_swan_prob=0,
                                   large_black_swan_prob=0)
        elif "Default" in scenario:
            market = Market.Market()
            investor = Investor.Investor()
        else:
            raise Exception("scenario type not supported")
        if "3X" in scenario:
            leverage_ratio_to_use = 3.0
        if "no expense ratios" in scenario:
            for key in funds_and_expense_ratios.keys():
                funds_and_expense_ratios_to_use[key] = 0
        if "taxes" in scenario:
            tax_rates = TaxRates.TaxRates()
            if "moderate taxes" in scenario:
                tax_rate = MODERATE_ANNUAL_FRACTION_OF_SHORT_TERM_CAP_GAINS * tax_rates.short_term_cap_gains_rate_plus_state()
            elif "high taxes" in scenario:
                tax_rate = HIGH_ANNUAL_FRACTION_OF_SHORT_TERM_CAP_GAINS * tax_rates.short_term_cap_gains_rate_plus_state()
        print "\n==Scenario: %s==" % scenario
        many_runs(funds_and_expense_ratios_to_use, tax_rate, leverage_ratio_to_use, num_samples,
                  investor, market, path.join(dir,""), num_trajectories_to_save_as_figures)

if __name__ == "__main__":
    leverage_ratio = 2.0
    num_samples = 2
    num_trajectories_to_save_as_figures = 1
    outfilepath = ""
    sweep_variations(FUNDS_AND_EXPENSE_RATIOS, leverage_ratio, num_samples,
                     num_trajectories_to_save_as_figures, outfilepath)