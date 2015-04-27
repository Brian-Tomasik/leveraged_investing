from datetime import datetime
import os
import numpy
import math

def format_as_dollar_string(float_or_int_amount):
    return "${:,}".format(int(round(float_or_int_amount,0)))

def create_timestamped_dir(prefix):
    # Create directory for results stamped with date/time to make it unique
    timestamp = datetime.now().strftime('%dd%Hh%Mm%Ss')
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

def stderr(numpy_array):
    return numpy.std(numpy_array) / math.sqrt(len(numpy_array))

def ratio_of_means_with_error_bars(numpy_array1, numpy_array2):
    """Take two arrays and compute (mean of first)/(mean of second)
    as well as the appropriate error bars for this ratio."""
    mean1 = numpy.mean(numpy_array1)
    mean2 = numpy.mean(numpy_array2)
    stderr1 = stderr(numpy_array1)
    stderr2 = stderr(numpy_array2)
    """
    "Uncertainties and Error Propagation - Part I of a manual on 
    Uncertainties, Graphing, and the Vernier Caliper" by Vern Lindberg
    http://www.rit.edu/cos/uphysics/uncertainties/Uncertaintiespart2.html says
    if z = x/y, then using standard deviations (and I'll assume, standard errors):
        error(z)/z = sqrt( (error(x)/x)^2 + (error(y)/y)^2 )
    """
    ratio = mean1/mean2
    if mean1 == 0:
        error_in_ratio = ratio * (stderr2/mean2)
        """
        The above evaluates to 0 if mean1==0 because then ratio==0, even though
        this isn't really right logically. The ratio could still have error even if
        mean1 == 0. The error in that case would be error(x)/(y+error(y)). I haven't figured
        out what the appropriate propagation-of-error formula is here, but fortunately,
        mean1 is almost never 0. That would mean 100% bankruptcy, which doesn't really
        happen given the parameter settings I have unless you were leveraged 50X or something.
        """
    else:
        error_in_ratio = abs(ratio) * math.sqrt( (stderr1/mean1)**2 + (stderr2/mean2)**2 )
    return (ratio, error_in_ratio)

def abs_fractional_difference(num1, num2):
    return abs((float(num1) - num2)/num2)

def round_decimal_to_given_num_of_sig_figs(decimal_less_than_1, sig_figs):
    """Inspired by http://stackoverflow.com/questions/3410976/how-to-round-a-number-to-significant-figures-in-python/3413529#3413529"""
    assert decimal_less_than_1 < 1.0, "This function is only built for decimals less than 1.0"
    this_many_zeros_after_decimal_before_first_digit = abs(int(math.floor(math.log10(decimal_less_than_1))) + 1)
    return round(decimal_less_than_1, this_many_zeros_after_decimal_before_first_digit+sig_figs)

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