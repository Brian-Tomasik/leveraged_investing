from datetime import datetime
import os
import numpy

def create_timestamped_dir(prefix):
    # Create directory for results stamped with date/time to make it unique
    timestamp = datetime.now().strftime('%d_%H_%M')
    outdir_name = prefix + "_" + timestamp
    os.mkdir(outdir_name) # let it fail if dir already exists
    return outdir_name

def N_to_1_leverage_to_max_margin_to_assets_ratio(N_to_1_leverage):
    """
    Record our leverage amount in N:1 terms. 2:1 leverage means up to half
    of the assets can be loaned. 3:1 means up to 2/3 of them can be. So
    N:1 leverage means the max margin-to-assets ratio R is (N-1)/N.
    """
    return (N_to_1_leverage-1)/float(N_to_1_leverage)

def max_margin_to_assets_ratio_to_N_to_1_leverage(max_margin_to_assets_ratio):
    """
    Reverse the equation used for N_to_1_leverage_to_max_margin_to_assets_ratio .
    In particular:  R = (N-1)/N  ==>  RN = N-1  ==>  1 = N - RN
    ==>  1 = N(1-R)  ==>  N = 1/(1-R)
    """
    return 1/(1-max_margin_to_assets_ratio)

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

def probability_x_better_than_y(x_list, y_list):
    assert len(x_list) >= 0, "Empty list"
    assert len(x_list) == len(y_list), "Can't compare lists of different lengths"
    x_numpy = numpy.array(x_list)
    y_numpy = numpy.array(y_list)
    return float(sum(x_numpy > y_numpy)) / len(x_numpy)

def per_period_annuity_payment_of_principal(principal, num_payment_periods, 
                                            loan_interest_rate, pay_principal_throughout):
    """We want to pay some amount A every period such that we'll pay
    off the full principal P after N payment periods, using a loan 
    interest rate of R. The principal equals the expected value of
    future payments:
    
    P = A + A/(1+R) + A/(1+R)^2 + ... + A/(1+R)^(N-1)

    Define F = 1/(1+R). Then

    P/A = 1 + F + F^2 + ... + F^(N-1).

    Let S := 1 + F + F^2 + ... + F^(N-1). Then FS = F + F^2 + ... + F^N. So
    S - FS = 1 - F^N  ==>  S = (1-F^N)/(1-F). So

    P/A = (1-F^N)/(1-F),

    which means

    A/P = (1-F)/(1-F^N)  ==>  A = P * (1-F) / (1-F^N)
    This is the formula I've actually used in the code for this function
    because it's simple. But to show that it's equivalent to the ordinary
    annuity formula, see below.

    Replace what F actually equals:

    A = P * [1 - 1/(1+R)] / [1 - 1/(1+R)^N]
    A = P * [(1+R)/(1+R) - 1/(1+R)] / [1 - 1/(1+R)^N]
    A = P * [R/(1+R)] / [1 - 1/(1+R)^N]

    This is the formula for an annuity-due (a-with-umlauts N|R):
    https://en.wikipedia.org/wiki/Annuity_(finance_theory)#Annuity-due
    """
    if pay_principal_throughout:
        if num_payment_periods == 0:
            return principal # pay off the whole remaining balance if we're at the last pay period
        else:
            inverse_interest = 1/(1+loan_interest_rate)
            return principal * (1-inverse_interest) / (1-inverse_interest**num_payment_periods)
    else:
        return 0 # not paying principal now; just pay at the end