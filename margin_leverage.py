import util
import Investor
import Market
import BrokerageAccount

DAYS_PER_YEAR = 365
SATURDAY = 6
SUNDAY = 0
MAX_MARGIN_TO_ASSETS_RATIO = .5

def one_run(investor,market,debug):
    days_from_start_to_retirement = DAYS_PER_YEAR * investor.years_until_retirement
    regular_account = BrokerageAccount.BrokerageAccount(0,0,0,MAX_MARGIN_TO_ASSETS_RATIO)
    margin_account = BrokerageAccount.BrokerageAccount(0,0,.5,MAX_MARGIN_TO_ASSETS_RATIO)
    matched_401k_account = BrokerageAccount.BrokerageAccount(0,0,0,MAX_MARGIN_TO_ASSETS_RATIO)
    interest_and_salary_every_num_days = 30
    interest_and_salary_every_fraction_of_year = float(interest_and_salary_every_num_days) / DAYS_PER_YEAR

    for day in range(days_from_start_to_retirement):
        # Stock market changes on weekdays
        if (day % 7 != SATURDAY) and (day % 7 != SUNDAY):
            random_daily_return = market.random_daily_return()
            regular_account.assets *= (1+random_daily_return)
            margin_account.assets *= (1+random_daily_return)
            matched_401k_account.assets *= (1+random_daily_return)

        # check if we should get paid and defray interest
        if day % interest_and_salary_every_num_days == 0:
            years_elapsed = day/DAYS_PER_YEAR
            pay = investor.current_annual_income(years_elapsed) * (float(interest_and_salary_every_num_days) / DAYS_PER_YEAR)
            
            if debug > 1:
                if day % 1000 == 0:
                    print "Day " + str(day) + ", year " + str(years_elapsed)

            # regular account just buys stock
            regular_account.buy_stock(pay)

            # matched 401k account buys stock with employee and employer funds
            matched_401k_account.buy_stock(pay * (1+investor.match_percent_from_401k/100.0))

            # The next steps are for the margin account. It
            # 1. pays interest
            # 2. pays some principal on loans
            # 3. pay margin calls, if any
            # 4. buys new stock with the remaining $

            # 1. pay interest
            interest = margin_account.compute_interest(market.annual_margin_interest_rate,interest_and_salary_every_fraction_of_year)
            pay_after_interest = pay - interest
            if pay_after_interest <= 0:
                margin_account.margin += (interest - pay) # amount of interest remaining
                margin_account.margin_call_rebalance() # pay for the interest with equity
                print """I didn't think hard about this case, since it's rare, so check back if I ever enter it. It's also bad tax-wise to rebalance, so try to avoid doing this."""
                # if this happens, no money left to 2. pay principal or 3. buy stock
            else:
                # 2. pay some principal
                number_of_pay_periods_until_retirement = (days_from_start_to_retirement - day) / interest_and_salary_every_num_days
                amount_of_principal_to_repay = util.per_period_annuity_payment_of_principal(margin_account.margin, number_of_pay_periods_until_retirement,market.annual_margin_interest_rate)
                if amount_of_principal_to_repay > pay_after_interest:
                    margin_account.margin -= pay_after_interest
                    margin_account.margin_call_rebalance() # pay for the principal with equity
                    print "WARNING: You're paying for principal with equity. This incurs tax costs and so should be minimized!"
                else:
                    margin_account.margin -= amount_of_principal_to_repay
                    pay_after_interest_and_principal = pay_after_interest - amount_of_principal_to_repay
                    # 3. pay margin calls, if any
                    amount_to_pay_for_margin_call = margin_account.debt_to_pay_off_for_margin_call()
                    if amount_to_pay_for_margin_call > pay_after_interest_and_principal:
                        # pay what we can
                        margin_account.margin -= pay_after_interest_and_principal
                        # use equity for the rest
                        margin_account.margin_call_rebalance()
                    else:
                        # just pay off margin call
                        margin_account.margin -= amount_to_pay_for_margin_call
                        pay_after_interest_and_principal_and_margincall = pay_after_interest_and_principal - amount_to_pay_for_margin_call
                        # 4. buy some stock
                        margin_account.buy_stock(pay_after_interest_and_principal_and_margincall)

    # Now that we're retired, finish up
    margin_account.pay_off_all_margin()

    # Return present values of the account balances
    return (market.present_value(regular_account.assets,investor.years_until_retirement),
            market.present_value(margin_account.assets,investor.years_until_retirement),
            market.present_value(matched_401k_account.assets,investor.years_until_retirement))

def run_samples(investor,market,debug,num_samples):
    regular_account_values = []
    margin_account_values = []
    matched_401k_values = []
    for sample in range(num_samples):
        (regular_val, margin_val, matched_401k_val) = one_run(investor,market,debug)
        regular_account_values.append(regular_val)
        margin_account_values.append(margin_val)
        matched_401k_values.append(matched_401k_val)
        if debug > 0:
            if sample % 10 == 0:
                print "Finished sample " + str(sample)

    print ""
    regular_mean = util.mean(regular_account_values)
    margin_mean = util.mean(margin_account_values)
    matched_401k_mean = util.mean(matched_401k_values)
    print "Mean regular = " + str(int(regular_mean))
    print "Mean margin = " + str(int(margin_mean))
    print "Mean matched 401k = " + str(int(matched_401k_mean))
    print "Mean value per year of margin over regular = " + str(int((margin_mean-regular_mean)/investor.years_until_retirement))
    print ""
    for percentile in [0, 10, 25, 50, 75, 90, 100]:
        fractional_percentile = percentile/100.0
        print str(percentile) + "th percentile regular = " + str(int(util.percentile(regular_account_values, fractional_percentile)))
        print str(percentile) + "th percentile margin = " + str(int(util.percentile(margin_account_values, fractional_percentile)))
        print str(percentile) + "th percentile matched 401k = " + str(int(util.percentile(matched_401k_values, fractional_percentile)))
        print ""

if __name__ == "__main__":
    investor = Investor.Investor(30, 6000, 2, 50)
    market = Market.Market(.054,.22,.015)
    #market = Market.Market(.054,.6,.015)
    run_samples(investor,market,1,200)