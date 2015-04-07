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

def per_period_annuity_payment_of_principal(principal, num_payment_periods, 
                                            loan_interest_rate):
    """We want to pay some amount A every period such that we'll pay
    off the full principal P after N payment periods, using a loan 
    interest rate of R. The principal equals the expected value of
    future payments:
    
    P = A + A/(1+R) + A/(1+R)^2 + ... + A/(1+R)^N

    Define F = 1/(1+R). Then

    P/A = 1 + F + F^2 + ... + F^N.

    Let S := 1 + F + F^2 + ... + F^N. Then FS = F + F^2 + ... + F^(N+1). So
    S - FS = 1 - F^(N+1)  ==>  S = (1-F^(N+1))/(1-F). So

    P/A = (1-F^(N+1))/(1-F),

    which means

    A/P = (1-F)/(1-F^(N+1))  ==>  A = P * (1-F) / (1-F^(N+1))
    """
    inverse_interest = 1/(1+loan_interest_rate)
    return principal * (1-inverse_interest) / (1-inverse_interest**(num_payment_periods))