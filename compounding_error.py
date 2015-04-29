import util
import numpy
import math
import Market
from scipy.optimize import fsolve

def one_run_daily_rebalancing(years, leverage_ratio, amount_to_invest, 
                              market, funds_and_expense_ratios):
    num_days = int(round(market.trading_days_per_year * years,0))

    index_val = amount_to_invest
    lev_fund_val = amount_to_invest

    daily_interest_rate = market.annual_margin_interest_rate/market.trading_days_per_year
    index_daily_exp_ratio = funds_and_expense_ratios["index"]/market.trading_days_per_year
    lev_fund_daily_exp_ratio = funds_and_expense_ratios["lev"]/market.trading_days_per_year

    for day in xrange(num_days):
        today_return = market.random_daily_return(day)
        # dS = S (mu * delta_t + sigma * sqrt(delta_t) * random_Z - exp_ratio * delta_t)
        # (new S) = (old S) + dS
        index_val += index_val * (today_return-index_daily_exp_ratio)
        if index_val < 0:
            index_val = 0 # can't have negative return
        lev_fund_val += lev_fund_val * (leverage_ratio * today_return \
            - (leverage_ratio-1)*daily_interest_rate - \
            lev_fund_daily_exp_ratio)
        if lev_fund_val < 0:
            lev_fund_val = 0 # go bankrupt

    return (index_val, lev_fund_val)

def many_runs(years, leverage_ratio, num_samples, amount_to_invest,
              market):
    FUNDS_AND_EXPENSE_RATIOS = {"index":.001, "lev":.01}
    fund_types = FUNDS_AND_EXPENSE_RATIOS.keys()
    fund_arrays = dict()
    for type in fund_types:
        fund_arrays[type] = numpy.array([])

    # Get results
    for i in xrange(num_samples):
        output_values = one_run_daily_rebalancing(years, leverage_ratio, amount_to_invest, market, FUNDS_AND_EXPENSE_RATIOS)
        for i in range(len(fund_types)):
            fund_arrays[fund_types[i]] = numpy.append(fund_arrays[fund_types[i]], output_values[i])

    # Print results
    for type in fund_types:
        lev_ratio_for_this_type = 1 if type == fund_types[0] else leverage_ratio
        print "===Type: %s===" % type
        print "mean = %s" % util.format_as_dollar_string(numpy.mean(fund_arrays[type]))
        print "theoretical mean = %s" % \
            util.format_as_dollar_string(round(theoretical_expected_utility(
                years, lev_ratio_for_this_type, amount_to_invest, 
                market, FUNDS_AND_EXPENSE_RATIOS[type], 1.0),0))
        print "median = %s" % util.format_as_dollar_string(numpy.median(fund_arrays[type]))
        print "25th percentile = %s" % util.format_as_dollar_string(util.percentile(fund_arrays[type],.25))
        print "min = %s" % util.format_as_dollar_string(numpy.min(fund_arrays[type]))
        print "actual avg sqrt(wealth) = %s" % str(int(round(expected_utility(fund_arrays[type],.5),0)))
        print "theoretical expected sqrt(wealth) = %s" % \
            str(int(round(theoretical_expected_utility(
                years, lev_ratio_for_this_type, amount_to_invest, 
                market, FUNDS_AND_EXPENSE_RATIOS[type], .5),0)))
        print ""
    print "alpha where expected utilities are equal = %s" % \
        find_alpha_where_expected_utilities_are_equal(
            fund_arrays[fund_types[0]],fund_arrays[fund_types[1]])

def theoretical_expected_utility(years, leverage_ratio, amount_to_invest, 
                                market, annual_expense_ratio, alpha):
    """E[u(V_t)] = V_0^α exp{ [r + (μ-r)c]tα + [σ^2c^2/2] t(α^2-α) }."""
    return amount_to_invest**alpha * math.exp( 
        (market.annual_margin_interest_rate - annual_expense_ratio + \
            (market.annual_mu-market.annual_margin_interest_rate) \
            * leverage_ratio) * years * alpha + \
            (market.annual_sigma**2 * leverage_ratio**2 / 2) \
            * years * (alpha**2-alpha) )

def find_alpha_where_expected_utilities_are_equal(index_vals, lev_fund_vals):
    LOW_ALPHA = .01
    HIGH_ALPHA = 1
    if expected_utility(lev_fund_vals, LOW_ALPHA) > expected_utility(index_vals, LOW_ALPHA):
        return "lev fund is always better"
    elif expected_utility(lev_fund_vals, HIGH_ALPHA) < expected_utility(index_vals, HIGH_ALPHA):
        return "index is always better"
    else:
        # alpha where equal is between LOW_ALPHA and HIGH_ALPHA
        diff = lambda alpha: expected_utility(lev_fund_vals, alpha) - expected_utility(index_vals, alpha)
        GUESS = .5 # alpha in the middle of the extremes
        root_arr = fsolve(diff, GUESS)
        assert len(root_arr) == 1, "Root array has length other than 1."
        return str(round(root_arr[0],3))

def expected_utility(numpy_array_of_wealth_values, alpha):
    return numpy.mean(map(lambda wealth: wealth**alpha, numpy_array_of_wealth_values))

if __name__ == "__main__":
    YEARS = 1
    LEVERAGE_RATIO = 2
    NUM_SAMPLES = 1000000
    AMOUNT_TO_INVEST = 1000.0
    market = Market.Market()
    """exact trading days don't matter; it's just about how granular
    the price updates should be"""
    print many_runs(YEARS,LEVERAGE_RATIO,NUM_SAMPLES,
                    AMOUNT_TO_INVEST,market)