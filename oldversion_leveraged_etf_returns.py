import random
import math
import numpy
from InvestmentComparison import InvestmentComparison

# TODO: ADD TAXES to leveraged fund

# ~252 trading days per year: http://en.wikipedia.org/wiki/Trading_day
def one_run(params):
    """Run through one random simulated trajectory of the regular ETF and its leveraged counterpart"""
    total_days = int(params.years_held * params.trading_days_per_year)
    regular_price = params.initial_value
    leveraged_price = params.initial_value
    delta_t = 1.0/params.trading_days_per_year

    daily_returns_so_far = numpy.array([])

    for day in xrange(total_days):
        # update fund prices
        daily_return = params.annual_sigma * random.gauss(0,1) * math.sqrt(delta_t) + params.annual_mu * delta_t
        """This is GBM for stock; for an example of this equation, see the first equation 
        in section 7.1 of 'Path-dependence of Leveraged ETF returns', 
        http://www.math.nyu.edu/faculty/avellane/LeveragedETF20090515.pdf ; 
        remember that yearly_sigma = daily_sigma * sqrt(252), so given that delta_t = 1/252, 
        then daily_sigma = yearly_sigma * sqrt(delta_t)"""
        daily_returns_so_far = numpy.append(daily_returns_so_far, daily_return)

        regular_price = update_price_without_going_below_zero(regular_price,daily_return)
        leveraged_price = update_price_without_going_below_zero(leveraged_price, \
            params.leverage_ratio*daily_return - \
            ((params.leverage_ratio-1) * params.annual_leverage_interest_rate + \
            params.annual_leverage_expense_ratio) * delta_t) 
        """For the above line, see equation (1) in section 2.1 of "Path-dependence of Leveraged ETF returns", 
        http://www.math.nyu.edu/faculty/avellane/LeveragedETF20090515.pdf"""

        # Check prices against theoretical formula to make sure simulation is on track
        theoretical_value = formula_for_L_over_S_to_the_beta(params, numpy.var(daily_returns_so_far)*total_days)
        actual_value = (leveraged_price/params.initial_value) / (regular_price/params.initial_value)**params.leverage_ratio # dividing by initial_value cancels out, but I'm doing so for the sake of clarity, to align with the formula in the write-up
        frac_diff = abs_fractional_difference(theoretical_value, actual_value)
        assert frac_diff < .35, "Simulated value doesn't match theoretical value; fractional difference is " + str(frac_diff)
    return (regular_price,leveraged_price,numpy.var(daily_returns_so_far)*total_days)

def update_price_without_going_below_zero(prev_price, daily_return):
    """A stock can't be worth less than $0, so impose 0 as a lower limit as we update
    its price with today's return."""
    new_price = prev_price * (1+daily_return)
    return 0 if new_price < 0 else new_price

def formula_for_L_over_S_to_the_beta(params, realized_variance):
    """This formula comes from my write-up document. It's easily derived from equation (4) 
    in section 2.1 of "Path-dependence of Leveraged ETF returns ", 
    http://www.math.nyu.edu/faculty/avellane/LeveragedETF20090515.pdf"""
    return math.exp( .5 * (params.leverage_ratio - params.leverage_ratio**2) * realized_variance + params.years_held * ((1-params.leverage_ratio) * params.annual_leverage_interest_rate - params.annual_leverage_expense_ratio))

def formula_for_alpha(params,S_T,final_realized_variance):
    """alpha is defined in my write-up at 
    http://reducing-suffering.org/do-leveraged-etfs-have-higher-long-run-returns/
    and this formula comes from there. alpha is (L_t/L_0)/(S_T/S_0)"""
    USE_CONTINUOUS_COMPOUNDING = True
    if USE_CONTINUOUS_COMPOUNDING:
        mu = math.log(S_T/params.initial_value)/params.years_held # math.log is natural log
        """It's ok/good to use continuous compounding because mu is compounded daily, which is
        close enough to continuously."""
    else:
        mu = (S_T/params.initial_value)**(1.0/params.years_held) - 1
    return (math.exp( (params.leverage_ratio-1)*mu + .5 * (params.leverage_ratio - params.leverage_ratio**2)*final_realized_variance/params.years_held + (1-params.leverage_ratio)*params.annual_leverage_interest_rate - params.annual_leverage_expense_ratio ))**params.years_held

def run_trials(params,num_trials=1000,allowable_deviation_from_theory=.05,debug=False):
    """Run through many simulated asset histories to accumulate aggregate performance distributional statistics"""
    regular_prices = []
    leveraged_prices = []
    num_prices_omitted = 0
    for trial in xrange(num_trials):
        # compute simulated prices
        regular_price,leveraged_price,final_realized_variance = one_run(params)
        
        # Check results against theory
        theoretical_alpha = formula_for_alpha(params,regular_price,final_realized_variance)
        actual_alpha = (leveraged_price/params.initial_value)/(regular_price/params.initial_value)
        frac_diff = abs_fractional_difference(theoretical_alpha, actual_alpha)
                
        # If deviation from theory isn't too big, add prices to our running lists of results
        if frac_diff > allowable_deviation_from_theory:
            num_prices_omitted += 1
            if debug:
                print "WARNING! Alpha deviates from theory by " + str(int(round(frac_diff * 100,0))) + "%: regular price = " + str(int(round(regular_price,0))) + " and leveraged price = " + str(int(round(leveraged_price,0)))
        else:
            if debug:
                print "Alpha only deviates from theory by " + str(int(round(frac_diff * 100,0))) + "%: regular price = " + str(int(round(regular_price,0))) + " and leveraged price = " + str(int(round(leveraged_price,0)))
            regular_prices.append(regular_price)
            leveraged_prices.append(leveraged_price)
        
        # Periodically print how many trials along we are
        if trial % 500 == 0:
            percent_complete = 100 * float(trial)/num_trials
            print str(int(round(percent_complete,0))) + "% done"
    
    # Print results
    print ""
    print str(round(100 * num_prices_omitted/num_trials,2)) + "% of simulated values omitted due to deviating more than " + str(round(allowable_deviation_from_theory * 100,2)) + "% from theory."
    print "Mean regular = " + str(int(round(mean(regular_prices),0))) + "\tMean leveraged = " + str(int(round(mean(leveraged_prices),0)))
    print "0th percentile regular = " + str(int(round(percentile(regular_prices, 0),0))) + "\t0th percentile leveraged = " + str(int(round(percentile(leveraged_prices, 0),0)))
    print "25th percentile regular = " + str(int(round(percentile(regular_prices, .25),0))) + "\t25th percentile leveraged = " + str(int(round(percentile(leveraged_prices, .25),0)))
    print "50th percentile regular = " + str(int(round(percentile(regular_prices, .5),0))) + "\t50th percentile leveraged = " + str(int(round(percentile(leveraged_prices, .5),0)))
    print "75th percentile regular = " + str(int(round(percentile(regular_prices, .75),0))) + "\t75th percentile leveraged = " + str(int(round(percentile(leveraged_prices, .75),0)))
    print "100th percentile regular = " + str(int(round(percentile(regular_prices, 1),0))) + "\t100th percentile leveraged = " + str(int(round(percentile(leveraged_prices, 1),0)))
    print ""

def abs_fractional_difference(num1, num2):
    return abs((float(num1) - num2)/num2)
    
def mean(list):
    assert len(list) > 0, "List is empty"
    return sum(list)/len(list)

def percentile(list, percentile_as_fraction):
    assert len(list) > 0, "List is empty"
    assert percentile_as_fraction >= 0 and percentile_as_fraction <= 1, "Percentile as fraction value isn't between 0 and 1"
    list.sort()
    index_of_value_to_return = int(round(len(list) * percentile_as_fraction,0))
    index_of_value_to_return = min(index_of_value_to_return, len(list)-1) # ensure that we don't go out of bounds
    return list[index_of_value_to_return]

if __name__ == "__main__":
    params = InvestmentComparison(years_held=1,trading_days_per_year=252,
                                  annual_mu=.054,annual_sigma=.22,leverage_ratio=2.0,
                                  initial_value=1000.0,annual_leverage_interest_rate=.03,
                                  annual_leverage_expense_ratio=.009)
    run_trials(params,num_trials=1000,allowable_deviation_from_theory=.01,debug=False)