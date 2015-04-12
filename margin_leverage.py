import util
import Investor
import Market
import BrokerageAccount
import numpy
import math
from matplotlib import pyplot

# TODO: if lots of trading happens, consider counting trading fees

DAYS_PER_YEAR = 365
SATURDAY = 6
SUNDAY = 0

def one_run(investor,market,verbosity):
    days_from_start_to_donation_date = int(DAYS_PER_YEAR * investor.years_until_donate)
    regular_account = BrokerageAccount.BrokerageAccount(0,0,0,investor.max_margin_to_assets_ratio)
    margin_account = BrokerageAccount.BrokerageAccount(0,0,.5,investor.max_margin_to_assets_ratio)
    matched_401k_account = BrokerageAccount.BrokerageAccount(0,0,0,investor.max_margin_to_assets_ratio)
    interest_and_salary_every_num_days = 30
    interest_and_salary_every_fraction_of_year = float(interest_and_salary_every_num_days) / DAYS_PER_YEAR

    for day in range(days_from_start_to_donation_date):
        # Stock market changes on weekdays
        if (day % 7 != SATURDAY) and (day % 7 != SUNDAY):
            random_daily_return = market.random_daily_return()
            regular_account.update_asset_prices(random_daily_return)
            margin_account.update_asset_prices(random_daily_return)
            matched_401k_account.update_asset_prices(random_daily_return)

        # check if we should get paid and defray interest
        if day % interest_and_salary_every_num_days == 0:
            years_elapsed = day/DAYS_PER_YEAR
            pay = investor.current_annual_income(years_elapsed) * (float(interest_and_salary_every_num_days) / DAYS_PER_YEAR)
            
            if verbosity > 1:
                if day % 1000 == 0:
                    print "Day " + str(day) + ", year " + str(years_elapsed) ,

            # regular account just buys ETF
            regular_account.buy_ETF(pay, day)

            # matched 401k account buys ETF with employee and employer funds
            matched_401k_account.buy_ETF(pay * (1+investor.match_percent_from_401k/100.0), day)

            # The next steps are for the margin account. It
            # 1. pays interest
            # 2. pays some principal on loans
            # 3. pay margin calls, if any
            # 4. buys new ETF with the remaining $

            # 1. pay interest
            interest = margin_account.compute_interest(market.annual_margin_interest_rate,interest_and_salary_every_fraction_of_year)
            pay_after_interest = pay - interest
            if pay_after_interest <= 0:
                margin_account.margin += (interest - pay) # amount of interest remaining
                margin_account.margin_call_rebalance(day, investor.short_term_cap_gains_rate, investor.long_term_cap_gains_rate) # pay for the interest with equity
                print """I didn't think hard about this case, since it's rare, so check back if I ever enter it. It's also bad tax-wise to rebalance, so try to avoid doing this."""
                # if this happens, no money left to 2. pay principal, 3. pay margin calls if any, or 4. buy ETF
            else:
                # 2. pay some principal
                number_of_pay_periods_until_donation_date = (days_from_start_to_donation_date - day) / interest_and_salary_every_num_days
                amount_of_principal_to_repay = util.per_period_annuity_payment_of_principal(margin_account.margin, number_of_pay_periods_until_donation_date,market.annual_margin_interest_rate, investor.pay_principal_throughout)
                if amount_of_principal_to_repay > pay_after_interest:
                    margin_account.margin -= pay_after_interest
                    margin_account.margin_call_rebalance(day, investor.short_term_cap_gains_rate, investor.long_term_cap_gains_rate) # pay for the principal with equity
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
                        margin_account.margin_call_rebalance(day, investor.short_term_cap_gains_rate, investor.long_term_cap_gains_rate)
                    else:
                        # just pay off margin call
                        margin_account.margin -= amount_to_pay_for_margin_call
                        pay_after_interest_and_principal_and_margincall = pay_after_interest_and_principal - amount_to_pay_for_margin_call
                        # 4. buy some ETF
                        margin_account.buy_ETF(pay_after_interest_and_principal_and_margincall, day)

    # Now that we've donated, finish up
    margin_account.pay_off_all_margin(days_from_start_to_donation_date, investor.short_term_cap_gains_rate, investor.long_term_cap_gains_rate)

    # Return present values of the account balances
    return (market.present_value(regular_account.assets,investor.years_until_donate),
            market.present_value(margin_account.assets,investor.years_until_donate),
            market.present_value(matched_401k_account.assets,investor.years_until_donate))

def plot_results(account_values, num_samples):
    alpha_for_pyplot = .5
    num_bins = max(10, num_samples/10)
    for type in ["regular", "margin", "matched401k"]:
        median_value = util.percentile(account_values[type], .5)
        numpy_array = numpy.array(account_values[type])
        bin_min = min(numpy_array)
        bin_max = 4 * median_value # avoids having a distorted graph due to far-right skewed values
        graph_bins = numpy.linspace(bin_min, bin_max, num_bins)
        pyplot.hist(numpy_array, bins=graph_bins, alpha=alpha_for_pyplot, color="r")
        pyplot.title("Distribution of results for " + type + " investing")
        pyplot.xlabel("Present value of savings ($)")
        pyplot.ylabel("Frequency out of " + str(num_samples) + " runs")
        pyplot.show()

def print_means(account_values, years_until_donation_date):
    regular_mean = util.mean(account_values["regular"])
    margin_mean = util.mean(account_values["margin"])
    matched_401k_mean = util.mean(account_values["matched401k"])
    print ""
    print "Mean regular = ${:,}".format(int(regular_mean))
    print "Mean margin = ${:,}".format(int(margin_mean))
    print "Mean matched 401k = ${:,}".format(int(matched_401k_mean))
    print "Mean value per year of margin over regular = ${:,}".format(int((margin_mean-regular_mean)/years_until_donation_date))

def print_percentiles(account_values):
    for percentile in [0, 10, 25, 50, 75, 90, 100]:
        fractional_percentile = percentile/100.0
        print ""
        for type in ["regular", "margin", "matched401k"]:
            print str(percentile) + "th percentile " + type + " = ${:,}".format(int(util.percentile(account_values[type], fractional_percentile)))

def print_winner_for_each_percentile(account_values):
    index = 0
    sorted_regular_list = sorted(account_values["regular"])
    sorted_margin_list = sorted(account_values["margin"])
    assert len(sorted_regular_list) == len(sorted_margin_list), "Regular and margin lists not the same length"
    upper_index = len(sorted_regular_list) - 1
    print ""
    print "Margin vs. regular % at percentiles 0 to 100:"
    for percentile in range(100):
        index = int((percentile/100.0)*upper_index)
        print "{}%".format(int((100.0 * sorted_margin_list[index]) / sorted_regular_list[index])) ,

def run_samples(investor,market,verbosity,num_samples,outfile=None,plot_results=True):
    account_values = dict()
    account_types = ["regular", "margin", "matched401k"]
    for type in account_types:
        account_values[type] = []
    for sample in range(num_samples):
        (regular_val, margin_val, matched_401k_val) = one_run(investor,market,verbosity)
        account_values["regular"].append(regular_val)
        account_values["margin"].append(margin_val)
        account_values["matched401k"].append(matched_401k_val)
        if verbosity > 0:
            if sample % 2 == 0:
                print "Finished sample " + str(sample) ,

    if plot_results:
        plot_results(account_values, num_samples)
    print ""
    print_means(account_values, investor.years_until_donate)
    print_percentiles(account_values)
    print_winner_for_each_percentile(account_values)
    
    if outfile:
        write_file_table(account_values, account_types, outfile)

def write_file_table(account_values, account_types, outfile):
    outfile.write("<table>\n")
    outfile.write("""<tr><td><i>Type</i></td> <td><i>Mean</i></td> <td><i>Median</i></td> <td><i>Min</i></td> <td><i>Max</i></td> <td><i>&sigma;<sub>log(wealth)</sub></i></td> </tr>\n""");
    for type in account_types:
        numpy_values = numpy.array(account_values[type])
        log_values = map(math.log, numpy_values)
        outfile.write("<tr><td><i>{}</i></td> <td>${:,}</td> <td>${:,}</td> <td>${:,}</td> <td>${:,}</td> <td>{:.2f}</td></tr>\n".format( 
            return_pretty_name_for_type(type), 
            int(util.mean(account_values[type])) , int(util.percentile(account_values[type], .5)) , 
            int(util.percentile(account_values[type], 0)) , int(util.percentile(account_values[type], 1)) ,
            numpy.std(log_values) ))
    outfile.write("</table>")

def return_pretty_name_for_type(type):
    if type == "regular":
        return "Regular"
    elif type == "margin":
        return "Margin"
    elif type == "matched401k":
        return "Regular+50% match"
    else:
        raise Exception("Given type not valid")

def sweep_scenarios():
    QUICK_TEST = False

    if QUICK_TEST:
        YEARS = 1
    else:
        YEARS = 30
    MU = .054
    SIGMA = .22
    INTEREST_RATE = .015
    STARTING_ANNUAL_INCOME = 30000
    INCOME_GROWTH_PERCENT = 2
    MATCH_FOR_401K = 50
    SHORT_TERM_CAP_GAINS = .28
    LONG_TERM_CAP_GAINS = .15
    PAY_PRINCIPAL_THROUGHOUT = True
    MAX_MARGIN_TO_ASSETS_RATIO = .5
    #NUM_TRIALS = 1000
    NUM_TRIALS = 10000
    VERBOSITY = 1
    PLOT_RESULTS = False

    with open("output\output.txt", "w") as outfile:
        outfile.write("Default scenario:\n")
        investor = Investor.Investor(YEARS, STARTING_ANNUAL_INCOME, 
                                     INCOME_GROWTH_PERCENT, MATCH_FOR_401K, 
                                     SHORT_TERM_CAP_GAINS, LONG_TERM_CAP_GAINS, 
                                     PAY_PRINCIPAL_THROUGHOUT, MAX_MARGIN_TO_ASSETS_RATIO)
        market = Market.Market(MU,SIGMA,INTEREST_RATE)
        run_samples(investor,market,VERBOSITY,NUM_TRIALS,outfile,PLOT_RESULTS)
        outfile.write("\n\n")

        outfile.write("Don't pay principal until end:\n")
        investor = Investor.Investor(YEARS, STARTING_ANNUAL_INCOME, 
                                     INCOME_GROWTH_PERCENT, MATCH_FOR_401K, 
                                     SHORT_TERM_CAP_GAINS, LONG_TERM_CAP_GAINS, 
                                     False, MAX_MARGIN_TO_ASSETS_RATIO)
        market = Market.Market(MU,SIGMA,INTEREST_RATE)
        run_samples(investor,market,VERBOSITY,NUM_TRIALS,outfile,PLOT_RESULTS)
        outfile.write("\n\n")

        outfile.write("3X leverage:\n")
        investor = Investor.Investor(YEARS, STARTING_ANNUAL_INCOME, 
                                     INCOME_GROWTH_PERCENT, MATCH_FOR_401K, 
                                     SHORT_TERM_CAP_GAINS, LONG_TERM_CAP_GAINS, 
                                     PAY_PRINCIPAL_THROUGHOUT, .67)
        market = Market.Market(MU,SIGMA,INTEREST_RATE)
        run_samples(investor,market,VERBOSITY,NUM_TRIALS,outfile,PLOT_RESULTS)
        outfile.write("\n\n")

if __name__ == "__main__":
    DO_SWEEP = True
    if DO_SWEEP:
        sweep_scenarios()
    else:
        investor = Investor.Investor(30, 30000, 2, 50, .28, .15, True, .67)
        #investor = Investor.Investor(1, 30000, 2, 50, .28, .15, True, .67)
        market = Market.Market(.054,.22,.015)
        #market = Market.Market(.054,.6,.015)
        run_samples(investor,market,1,1000)
        #run_samples(investor,market,1,2000)