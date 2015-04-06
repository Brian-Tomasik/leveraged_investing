import random
import math
from InvestmentComparison import InvestmentComparison

# TODO: ADD TAXES to leveraged fund

# ~252 trading days per year: http://en.wikipedia.org/wiki/Trading_day
def one_run(params):
    """Run through one random simulated trajectory of the regular ETF and its leveraged counterpart"""
    total_days = int(params.years_held * params.trading_days_per_year)
    regular_price = params.initial_value
    leveraged_price = params.initial_value
    delta_t = 1.0/params.trading_days_per_year
    for day in range(total_days):
        # update fund prices
        daily_return = params.annual_sigma * random.gauss(0,1) * math.sqrt(delta_t) + params.annual_mu * delta_t #GBM for stock; for an example of this equation, see the first equation in section 7.1 of 'Path-dependence of Leveraged ETF returns', http://www.math.nyu.edu/faculty/avellane/LeveragedETF20090515.pdf; remember that yearly_sigma = daily_sigma * sqrt(252), so given that delta_t = 1/252, then daily_sigma = yearly_sigma * sqrt(delta_t)
        regular_price = regular_price * (1+daily_return)
        leveraged_price = leveraged_price * (1+params.leverage_ratio*daily_return - ((params.leverage_ratio-1) * params.annual_leverage_interest_rate + params.annual_leverage_expense_ratio) * delta_t) # see equation (1) in section 2.1 of "Path-dependence of Leveraged ETF returns", http://www.math.nyu.edu/faculty/avellane/LeveragedETF20090515.pdf

        # Check prices against theoretical formula to make sure simulation is on track
        theoretical_value = formula_for_L_over_S_to_the_beta(params)
        actual_value = (leveraged_price/params.initial_value) / (regular_price/params.initial_value)**2 # dividing by initial_value cancels out, but I'm doing so for the sake of clarity, to align with the formula in the write-up
        frac_diff = abs_fractional_difference(theoretical_value, actual_value)
        assert frac_diff < .35, "Simulated value doesn't match theoretical value; fractional difference is " + str(frac_diff)
    return (regular_price,leveraged_price)

def formula_for_L_over_S_to_the_beta(params):
    """This formula comes from my write-up document. It's easily derived from equation (4) in section 2.1 of "Path-dependence of Leveraged ETF returns", http://www.math.nyu.edu/faculty/avellane/LeveragedETF20090515.pdf"""
    return math.exp(params.years_held * (.5 * (params.leverage_ratio - params.leverage_ratio**2) * params.annual_sigma**2 + (1-params.leverage_ratio) * params.annual_leverage_interest_rate - params.annual_leverage_expense_ratio))

def formula_for_alpha(params,S_T):
    """alpha is defined in my write-up, and this formula comes from there. alpha is (L_t/L_0)/(S_T/S_0)"""
    Y = (S_T/params.initial_value)**(1.0/params.years_held) - 1
    return (math.exp((params.leverage_ratio-1)*Y + .5 * (params.leverage_ratio - params.leverage_ratio**2)*params.annual_sigma**2 + (1-params.leverage_ratio)*params.annual_leverage_interest_rate - params.annual_leverage_expense_ratio))**params.years_held

def run_trials(params,num_trials=1000,allowable_deviation_from_theory=1.0,debug=False):
    """Run through many simulated asset histories to accumulate aggregate performance distributional statistics"""
    regular_prices = []
    leveraged_prices = []
    num_prices_omitted = 0
    for trial in range(num_trials):
        # compute simulated prices
        regular_price,leveraged_price = one_run(params)
        
        # Check results against theory
        theoretical_alpha = formula_for_alpha(params,regular_price)
        actual_alpha = (leveraged_price/params.initial_value)/(regular_price/params.initial_value)
        frac_diff = abs_fractional_difference(theoretical_alpha, actual_alpha)
                
        # If deviation from theory isn't too big, add prices to our running lists of results
        if frac_diff > allowable_deviation_from_theory:
            num_prices_omitted += 1
            if debug:
                print "WARNING! Alpha deviates from theory by " + str(int(frac_diff * 100)) + "%: regular price = " + str(int(regular_price)) + " and leveraged price = " + str(int(leveraged_price))
        else:
            if debug:
                print "Alpha only deviates from theory by " + str(int(frac_diff * 100)) + "%: regular price = " + str(int(regular_price)) + " and leveraged price = " + str(int(leveraged_price))
            regular_prices.append(regular_price)
            leveraged_prices.append(leveraged_price)
        
        # Periodically print how many trials along we are
        if trial % 1000 == 0:
            percent_complete = 100 * float(trial)/num_trials
            print str(int(percent_complete)) + "% done"
    
    # Print results
    print ""
    print str(int(100 * num_prices_omitted/num_trials)) + "% of simulated values omitted due to deviating more than " + str(int(allowable_deviation_from_theory * 100)) + "% from theory."
    print "Mean regular = " + str(int(mean(regular_prices))) + "\tMean leveraged = " + str(int(mean(leveraged_prices)))
    print "0th percentile regular = " + str(int(percentile(regular_prices, 0))) + "\t0th percentile leveraged = " + str(int(percentile(leveraged_prices, 0)))
    print "25th percentile regular = " + str(int(percentile(regular_prices, .25))) + "\t25th percentile leveraged = " + str(int(percentile(leveraged_prices, .25)))
    print "50th percentile regular = " + str(int(percentile(regular_prices, .5))) + "\t50th percentile leveraged = " + str(int(percentile(leveraged_prices, .5)))
    print "75th percentile regular = " + str(int(percentile(regular_prices, .75))) + "\t75th percentile leveraged = " + str(int(percentile(leveraged_prices, .75)))
    print "100th percentile regular = " + str(int(percentile(regular_prices, 1))) + "\t100th percentile leveraged = " + str(int(percentile(leveraged_prices, 1)))
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
    index_of_value_to_return = int(len(list) * percentile_as_fraction)
    index_of_value_to_return = min(index_of_value_to_return, len(list)-1) # ensure that we don't go out of bounds
    return list[index_of_value_to_return]

if __name__ == "__main__":
    params = InvestmentComparison(years_held=1,trading_days_per_year=252,annual_mu=.056,annual_sigma=.22,leverage_ratio=2,initial_value=100,annual_leverage_interest_rate=.0137,annual_leverage_expense_ratio=.0089,)
    run_trials(params)